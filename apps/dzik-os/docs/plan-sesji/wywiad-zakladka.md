# Plan sesji: zakładka „Wywiad” — wstępny i głęboki, wersje, przegląd, migracja (0.59.0)

**Gałąź:** `agent/wywiad-zakladka` (od `main` = 28cc50d po scaleniu #55;
jeden `[WRITER]` naraz).
**Rola:** jedyny piszący i integrator; recenzent: Codex. Właściciel 13.09:
„nie zatrzymuj pracy… jeśli nie znajdziesz błędów scalaj po każdym PR”.
**Źródło:** dokument właściciela „Zakładka Wywiad — dokument wdrożeniowy”
(13.09): najpierw diagnoza braku wywiadu, potem stała zakładka z dwoma
formularzami, wersjonowanie, przegląd trenera per wersja, pytania
warunkowe oceniane serwerowo, integracja konfiguratorów, migracja
ponawialna, 18 testów odbioru. „Nie uznawaj samego dodania zakładki za
ukończenie integracji.”

## Diagnoza (na podstawie kodu i danych, przed zmianą schematu)

Ustalone w kodzie (szczegóły z odnośnikami: `docs/WYWIAD.md` §1):

1. **Żadna ścieżka utworzenia klienta nie tworzy sesji wywiadu.**
   Zaproszenie trenera (`routers/clients.py:109-262`), aktywacja
   (`routers/auth.py:456-481`), skrypt operatora (`dodaj_klienta.py`),
   seed, importy (arkusze = tylko szablony/ćwiczenia) — sesję
   `OnboardingSession` tworzy wyłącznie klient przez
   `POST …/{onboarding|interview}/start` (`routers/onboarding.py:394-429`,
   `_require_client_self`). Samodzielnej rejestracji nie ma. Klient
   dodany ręcznie, który się nie zalogował, **zawsze** ma pusty wywiad,
   a trener nie ma jak go zainicjować ani poprosić.
2. **Widok trenera zależy od istnienia sesji**: `ClientDetail.tsx`
   `OnboardingTab` pokazuje „Klient nie zaczął jeszcze…” przy braku
   wiersza; nie rozróżnia „zaczął i przerwał”, „wypełnił ankietę
   `/ankieta` zamiast rozmowy” (ta pisze prosto do profilu, sesji nie
   tworzy), „nie mam dostępu”.
3. **Odmowa dostępu = błąd techniczny**: `_require_coach` (403) i
   `ResourceAccessDenied` (404 „Nie znaleziono”) lądują w tym samym
   `ErrorBox`; brak zgody `udostepnianie_trenerowi` wygląda jak awaria.
4. **Zgody wycinają pytania po cichu**: bez zgody zdrowotnej znika
   23 z 50 kroków wywiadu i 7 z 22 rozmowy (`allowed_domains`,
   `onboarding.py:138-151`); bez relacji ACTIVE — wszystkie wrażliwe.
5. **Zaproszenie na istniejące konto nie rejestruje zgód**
   (`clients.py:209`) → `consent_active=false` → obie zakładki w błędzie.
6. `_coach_id()` bierze dowolnego trenera (`.first()`); brak
   `UNIQUE(client_id, flow)` — po `COACH_APPROVED` `/start` otwiera
   drugą sesję. Odpowiedzi kluczowane po `session_id` → `client_id`
   (bez sierot; konto PENDING nie loguje się, więc nie ma odpowiedzi
   sprzed przyjęcia zaproszenia). Brak pola statusu na `User`, które
   ukrywałoby widok.

Wniosek: przyczyną „braku wywiadu” jest **brak wypełnienia w modelu,
w którym tylko klient może zacząć, plus nieodróżnialne stany widoku** —
nie utrata danych ani błędne powiązania. Istniejące odpowiedzi
(sesje rozmowy startowej i wywiadu) są wiarygodnie powiązane z klientem
i podlegają migracji do wersji.

## Decyzje projektowe

1. **Definicje pytań z istniejących scenariuszy**: `wywiad/definicje.py`
   buduje `InterviewDefinition` `wstepny` (22 kroki `onboarding_flow.STEPS`)
   i `gleboki` (50 kroków `interview_flow.DEEP_STEPS`) — `question_id`
   = dotychczasowy `step.id`, wersja definicji 1, typ, etykieta, sekcja
   (topic), reguła widoczności (`_triggered`/`deep_triggered` + zgoda
   domeny), reguła wymagalności (jawny zbiór pytań wymaganych per
   usługa: trening / żywienie / współpraca), walidator
   (`validate_answer`), opcje, klasyfikacja dostępu (`consent_domain`,
   `sensitive`). Pytania o ograniczenia dostają odpowiedzi
   `nie zgłaszam` / `tak` / `nie wiem` / `wolę omówić z trenerem`.
   Zmienione znaczenie pytania = nowa wersja definicji (mapowanie),
   nigdy reinterpretacja starych odpowiedzi.
2. **Wspólne fakty** (`client_fact_revisions`): odpowiedzi zasilające
   profil (`profile_field`) tworzą rewizję faktu z pochodzeniem
   (typ formularza, pytanie, autor, czas); wywiad głęboki pokazuje
   fakt ze wstępnego jako kontekst („We wstępnym wskazano: …”) i pyta
   o rozwinięcie — nie kopiuje. Korekta faktu = nowa rewizja widoczna
   w obu miejscach. Zapis do `profile_fields` jak dotąd (przez
   `apply_profile_fields`) — jedno źródło profilu.
3. **Szkic i wersje**: `interview_drafts` (klient, typ, rewizja,
   odpowiedzi, `entered_by`, `collection_mode` SELF / WSPOLNIE, autor
   aktualizacji), `interview_submissions` (niezmienna wersja: odpowiedzi
   z autorstwem per pytanie, wersja definicji, kto i kiedy przesłał,
   `migrated`), `interview_reviews` (wersja, trener, wynik REVIEWED /
   NEEDS_CLARIFICATION, notatka wewnętrzna — nigdy w API klienta),
   `clarification_requests` (wskazane pytania, komunikat, rozwiązanie).
   Statusy rozdzielone i wyliczane: `submission_status`
   (not_started/draft/submitted), `review_status` (not_reviewed/
   needs_clarification/reviewed — dla OSTATNIEJ przesłanej wersji),
   `freshness_status` (current/update_requested). Postęp = wymagane
   aktywne odpowiedziane / wymagane aktywne (0/0 → 100 %).
   `PATCH` szkicu wymaga rewizji (409 bez cichego nadpisania);
   autozapis potwierdza się odpowiedzią serwera; serwer sam ocenia
   widoczność i wymagalność; nieaktywna gałąź nie zasila konfiguratora,
   jej odpowiedzi zostają w szkicu do potwierdzenia po powrocie.
   Trener „Uzupełnia wspólnie” tym samym szkicem z `collection_mode`
   WSPOLNIE i `entered_by` = trener; klient to widzi.
4. **Przesłanie** (`POST …/przeslij`, rewizja + klucz idempotencji):
   walidacja wymaganych aktywnych (odpowiedź „nie wiem” liczy się jako
   odpowiedź, ale zostawia blokadę gotowości danych), nowa wersja +
   rewizje faktów + `PlanReviewTask` gdy zmieniły się fakty istotne dla
   aktywnego planu (cel, ograniczenia, alergie, dostępność, sprzęt) +
   `OutboxEvent` (jeden wpis trenera, dedup) — w jednej transakcji.
   Nowa wersja = `review_status` od nowa; poprzedni przegląd w historii.
   Publikacja zależnej wersji planu jest blokowana, gdy istnieje otwarte
   `PlanReviewTask` z nierozstrzygniętymi faktami (409
   `INTERVIEW_REVIEW_REQUIRED` w publikacji szkicu z 0.58.0). Plan
   aktywny nie jest przepisywany.
5. **Powiadomienia przez outbox** (`OutboxEvent`, typy
   INTERVIEW_SUBMITTED → trener, CLARIFICATION_REQUESTED → klient,
   INTERVIEW_REVIEWED → klient) z `dedup_key` per zdarzenie i odbiorca;
   kategoria `WYWIAD` z neutralnym push; autozapis bez powiadomień;
   przypomnienie = jawna akcja trenera (`…/przypomnij`, dedup dzienny);
   migracja niczego nie wysyła. Przejrzenie ≠ publikacja planu (osobne
   zdarzenia, 0.58.0).
6. **Migracja ponawialna** (`python -m dzik_os.migruj_wywiad --raport`
   / `--wykonaj` oraz idempotentne wywołanie przy starcie): raport
   liczb (klienci, sesje per typ/status, odpowiedzi, sesje bez
   relacji, duplikaty per klient+typ) bez treści odpowiedzi; sesje
   CLIENT_APPROVED/COACH_APPROVED → wersja historyczna (`migrated=True`,
   przegląd REVIEWED tylko gdy `coach_approved_by` istnieje —
   inaczej `not_reviewed`); IN_PROGRESS/SUMMARY_READY → szkic;
   ABANDONED → szkic oznaczony; wielokrotne sesje → najnowsza jako
   bieżąca, starsze jako wcześniejsze wersje; niejednoznaczne (brak
   relacji trener–klient) → lista do ręcznej weryfikacji, bez
   ujawniania. Stare tabele zostają (rozmowa startowa dalej działa
   jako alternatywny kanał; zatwierdzenie tworzy wersję).
7. **Widoki**: klient `/wywiad` = dwie karty (cel, postęp, statusy,
   data, przegląd) + formularz sekcjami (etykiety stałe, błędy przy
   polach, stan zapisu, objaśnienie sekcji) + podsumowanie (cele,
   ograniczenia, preferencje, do wyjaśnienia, do aktualizacji — każdy
   punkt wskazuje odpowiedź z datą i autorem) + prośby trenera;
   trener: zakładka „Wywiad” w karcie klienta z trzema odrębnymi
   stanami (pusto / brak dostępu z powodem / błąd pobierania z
   ponowieniem), Przejrzyj (odpowiedzi + historia), Poproś
   o uzupełnienie, Uzupełnij wspólnie, Oznacz jako przejrzane
   (nie „dopuszczenie”), notatki wewnętrzne, podpowiedzi do
   konfiguratorów; lista „Wywiady do przejrzenia” i filtry
   w liście klientów.
8. **Integracja konfiguratorów** (`GET …/wywiady/podpowiedzi`):
   deterministyczne mapowanie faktów → wejścia konfiguratora treningu
   (cel, dni, czas, sprzęt, doświadczenie) i kreatora dań (alergie
   jako ograniczenia — brak informacji ≠ zgoda; styl żywienia
   i warunki gotowania jako preferencje); kreator dań wstępnie
   zaznacza alergeny z jawną korektą trenera; szkic planu zapisuje
   `interview_submission_id` w treści (`_wywiad`). Bez LLM.
9. **Ścieżki tworzenia klienta**: karty formularzy istnieją dla
   każdego klienta bez wiersza w bazie (`not_started`); trener może
   zainicjować prośbę o wywiad. Przyczyna 5 (zaproszenie na istniejące
   konto bez deklaracji zgód) **nie jest „naprawiana” rejestrowaniem
   deklaracji za podmiot** — w tym systemie deklaracja bez potwierdzenia
   już autoryzuje trenera (`ConsentService.authorize`), więc byłoby to
   nadanie zgody bez udziału klienta (P7, KARTA). Zamiast tego stan jest
   jawny: trener widzi powód (konto przed aktywacją / brak zgód), klient
   widzi wyłączone kategorie i gdzie zgodę włączyć.

## Zamiar P0

- Migracja **31**, wersja **0.59.0**; `dzik_os/wywiad/{definicje,serwis,
  podsumowanie,migracja}.py`; `dzik_os/migruj_wywiad.py`;
  `routers/wywiady.py`; kategoria `WYWIAD`; outbox per typ zdarzenia;
  blokada publikacji przy otwartym `PlanReviewTask`; naprawa zgód dla
  zaproszeń na istniejące konto; macierz dostępu.
- Frontend: `pages/client/Wywiad.tsx` (nowa strona `/wywiad`),
  `pages/coach/WywiadTab.tsx` (karta klienta), lista do przejrzenia
  w `Clients.tsx`, podpowiedzi w `KreatorDan.tsx`, ekran zmian bez zmian.
- Testy: 18 scenariuszy odbioru jako testy API + migracja na
  syntetycznych sesjach + E2E (klient wypełnia i przesyła, trener
  przegląda i prosi o uzupełnienie).
- Dokumentacja: `docs/WYWIAD.md` (przyczyna, zmiany, testy,
  ograniczenia), CHANGELOG, STAN, RELEASE_STATUS, README, `.env.example`.

## Świadomie nie robię

- automatycznej oceny medycznej z tekstu; załączników jako wymogu;
  automatycznych przypomnień cyklicznych (bez konfiguracji);
  usuwania starych tabel rozmowy; e-maili; zmiany rozmowy startowej
  (zostaje alternatywnym kanałem zasilającym te same wersje).

## Rezerwacje

Migracja nr **31**, wersja **0.59.0**, pliki: `backend/dzik_os/wywiad/**`,
`dzik_os/migruj_wywiad.py`, `routers/wywiady.py`, `routers/onboarding.py`
(zatwierdzenie → wersja), `publikacja/serwis.py` (blokada), `notifications.py` (kategoria),
`frontend/src/pages/client/Wywiad.tsx`, `pages/coach/WywiadTab.tsx`,
`pages/coach/{ClientDetail,Clients,KreatorDan}.tsx`, `e2e/wywiad.spec.ts`,
`docs/WYWIAD.md`.

## Weryfikacja wykonana

Lokalnie 13.09 (przed PR gotowym do przeglądu): ruff czysto (nowe
moduły `dzik_os/wywiad/**`, `routers/wywiady.py`, `migruj_wywiad.py`,
zmienione pliki; 13 zastanych uwag w starych plikach bez zmian);
backend **1701 passed, 1 skipped** (+ naprawa: `DEFAULT 1/0` → `true/false`
w migracji 31 po strażniku przenośności; `test_aggregates` uzupełniony
o nową flagę); `test_wywiad_zakladka.py` **18 passed** (T1–T18);
`test_access_matrix.py` 8 passed z 16 nowymi wpisami; Core 275;
frontend tsc + build (89,5 kB / 120 kB) + test:helpers 140; E2E
Playwright **27 passed** (26 + `wywiad-zakladka.spec.ts`;
`wywiad.spec.ts` przeprowadzony przez nową zakładkę);
`e2e/test_a11y.mjs` czysto po poprawce (opcje odpowiedzi zawijają się
na 320 px — pierwszy przebieg wykrył 4 px poziomego scrolla);
`tools/spojnosc.py` 13/13. Przeklik na żywo (Pixel 7 + desktop 1280 px):
karty → formularz z autozapisem → przesłanie → lista trenera z odznaką →
Przejrzyj → Poproś o uzupełnienie → wpis klienta i prośba przy pytaniu.
Rozstrzygnięcie w trakcie: przyczyna 5 diagnozy (zgody dla istniejącego
konta) nie jest „naprawiana” po stronie bazy — stan jest jawny (decyzja
w §Decyzje pkt 9). CI i scalenie — po PR #56 (uzupełnię).

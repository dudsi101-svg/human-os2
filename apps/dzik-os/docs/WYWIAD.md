# Zakładka „Wywiad” (0.59.0) — raport wdrożenia

**Źródło:** dokument właściciela „Zakładka Wywiad — dokument wdrożeniowy”
(13.09.2026). Runda: gałąź `agent/wywiad-zakladka`, plan sesji
`docs/plan-sesji/wywiad-zakladka.md`, PR #56.

## 1. Diagnoza: dlaczego w karcie klienta „nie było wywiadu”

Ustalone z kodu i danych (bez zmiany schematu, przed implementacją):

| # | Przyczyna | Gdzie w kodzie (przed 0.59.0) | Skutek dla trenera |
|---|---|---|---|
| 1 | **Żadna ścieżka utworzenia klienta nie tworzy wywiadu.** Zaproszenie (`routers/clients.py`), aktywacja (`routers/auth.py`), skrypt `dodaj_klienta`, seed, importy arkuszy — nic nie zakłada sesji. `OnboardingSession` tworzył WYŁĄCZNIE klient przez `POST …/{onboarding\|interview}/start` (`_require_client_self`). | `routers/onboarding.py` (`/start`) | klient dodany ręcznie, który nie wypełnił rozmowy, ma pusty wywiad; trener nie mógł go zainicjować ani poprosić |
| 2 | **Widok zależał od istnienia wiersza sesji** i pokazywał jedno „Klient nie zaczął jeszcze…” dla trzech różnych stanów: nie wypełnił / zaczął i przerwał / wypełnił ankietę `/ankieta` (pisze do profilu, sesji nie tworzy). | `ClientDetail.tsx` `OnboardingTab` | brak rozróżnienia „nie wypełniono” od „zapisano, ale nie widać” |
| 3 | **Odmowa dostępu wyglądała jak awaria**: `_require_coach` (403) i `ResourceAccessDenied` (404) lądowały w tym samym `ErrorBox`; brak zgody współpracy = „Nie znaleziono”. | `routers/onboarding.py`, `ClientDetail.tsx` | trener nie wiedział, czy to brak zgody, czy błąd |
| 4 | **Zgody wycinały pytania po cichu**: bez zgody zdrowotnej znikało 23/50 kroków wywiadu i 7/22 rozmowy; bez relacji ACTIVE — wszystkie wrażliwe. | `allowed_domains()` | wywiad „krótszy” bez wyjaśnienia |
| 5 | **Zaproszenie na istniejące konto nie rejestruje deklaracji zgód** (świadoma decyzja RODO z fali P7: zgody nadaje tylko podmiot danych) → `consent_active=false` → obie zakładki w błędzie. | `routers/clients.py` (`new_account`) | stan poprawny prawnie, ale nieczytelny |
| 6 | `_coach_id()` brał dowolnego trenera (`.first()`); brak `UNIQUE(client_id, flow)` — po `COACH_APPROVED` `/start` otwierał drugą sesję. Odpowiedzi są kluczowane po `session_id → client_id` (bez sierot; konto PENDING nie loguje się, więc nie ma odpowiedzi sprzed aktywacji). | `routers/onboarding.py` | możliwe duplikaty sesji, nie utrata danych |

**Wniosek:** przyczyną „braku wywiadu” było **niewypełnienie w modelu,
w którym tylko klient może zacząć, plus nieodróżnialne stany widoku** —
nie utrata danych ani błędne powiązania. Istniejące odpowiedzi (sesje
rozmowy startowej i głębokiego wywiadu) są wiarygodnie powiązane
z klientem i zostały przeniesione do wersji (§6).

Rozstrzygnięcie punktu 5: **nie** rejestrujemy deklaracji zgód za
istniejące konto (byłoby to nadanie zgody bez udziału podmiotu — wbrew
`KARTA_WSPOLPRACY` i P7); zamiast tego stan jest jawny: trener widzi
„brak dostępu” z powodem, klient widzi, że pytania kategorii bez zgody
są wyłączone i gdzie zgodę włączyć.

## 2. Co się zmieniło

### Klient (`/wywiad`)
* Dwie stałe karty — **Wywiad wstępny** i **Wywiad głęboki** — dla
  każdego klienta od razu (bez wiersza w bazie = `not_started`): cel
  formularza, trzy ROZDZIELONE statusy (wypełnienie / przegląd /
  aktualność), postęp (wymagane aktywne), data ostatniej wersji, prośby
  trenera, historia wersji.
* Działania: **Rozpocznij / Kontynuuj / Aktualizuj odpowiedzi**,
  w formularzu **Zapisz szkic**, **Prześlij trenerowi** (albo
  **Aktualizuj odpowiedzi**, gdy jest już wersja).
* Formularz sekcjami (wstępny: cel, punkt wyjścia, trening, zdrowie
  i ograniczenia, odżywianie, codzienność, współpraca; głęboki:
  motywacja, historia treningowa, pogłębienie ograniczeń, regeneracja,
  historia odżywiania, organizacja, preferencje szczegółowe, pytania
  trenera). Etykiety stałe, błędy przy polu, stan zapisu potwierdzany
  odpowiedzią serwera („Zapisano ✓ hh:mm”), objaśnienie sekcji, kontekst
  z wywiadu wstępnego w głębokim („We wstępnym wskazano: …”).
* Pytania o ograniczenia mają odpowiedzi **Nie zgłaszam / Tak / Nie wiem /
  Wolę omówić z trenerem**; „Nie wiem” i „Wolę omówić” liczą się do
  postępu, ale zostają w podsumowaniu jako „Do wyjaśnienia z trenerem”
  (kompletność ≠ gotowość danych).
* Alergia, nietolerancja i preferencja to trzy różne pytania
  (`alergie_status`, `nietolerancje`, `wykluczenia_preferencje` obok
  dotychczasowego `alergie`).
* Podsumowanie deterministyczne: cele, ograniczenia, preferencje, do
  wyjaśnienia, do aktualizacji — każdy punkt wskazuje pytanie, wersję,
  autora i czas.
* Rozmowa krok po kroku (`/rozmowa`, `/wywiad/rozmowa`) pozostaje
  alternatywnym kanałem — zatwierdzona trafia do zakładki jako wersja.

### Trener (karta klienta → Wywiad; lista klientów)
* Trzy odrębne stany: **pusto** (klient nic nie wypełnił + „Poproś
  o wypełnienie” / „Uzupełnij wspólnie”), **brak dostępu z powodem**
  (konto przed aktywacją albo brak potwierdzonych zgód), **błąd
  pobierania z ponowieniem**.
* Działania: **Przejrzyj** (odpowiedzi sekcjami z autorstwem, ukryte
  = brak zgody na kategorię, wcześniejsze wersje), **Oznacz jako
  przejrzane** (potwierdzenie zapoznania się — nazwa celowo nie sugeruje
  dopuszczenia do treningu) z notatką wewnętrzną, **Poproś
  o uzupełnienie** (wskazane pytania + wiadomość), **Uzupełnij wspólnie**
  (ten sam formularz, `collection_mode=WSPOLNIE`, wpisy oznaczone jako
  trenera, klient je widzi i może poprawić), **Poproś o wypełnienie /
  Przypomnij o dokończeniu** (jawna akcja, jeden wpis dziennie).
* **Wymaga sprawdzenia**: zmiana faktów istotnych dla planu (cel,
  ograniczenia, alergie, dostępność, sprzęt) w nowej wersji tworzy
  zadanie per aktywny plan; publikacja zależnej wersji planu jest
  zablokowana (409 `INTERVIEW_REVIEW_REQUIRED`) do jawnego
  rozstrzygnięcia; plan aktywny NIE jest przepisywany.
* Lista **Wywiady do przejrzenia** (`GET /api/coach/wywiady/do-przegladu`),
  filtr i odznaka „wywiad do przejrzenia” na liście klientów
  (`flags.interview_to_review`), link z powiadomienia prosto do zakładki.
* **Podpowiedzi do konfiguratorów** (mapowanie deterministyczne z
  pochodzeniem): konfigurator treningu (cel, poziom, dni, sprzęt, zdrowie,
  mapa tygodnia), kreator dań (alergie jako ograniczenie + wstępne
  zaznaczenie alergenów do potwierdzenia; nietolerancje i wykluczenia
  jako preferencje; „brak informacji ≠ brak alergii” jako ostrzeżenie).

### Model danych (migracja 31, addytywna)
`interview_drafts` (jeden na klient+typ, rewizja, `dirty`,
`collection_mode`, autor), `interview_submissions` (niezmienna wersja:
odpowiedzi z autorstwem per pytanie, wersja definicji, `migrated`,
`source_session_id`), `interview_reviews` (per wersja, notatka
wewnętrzna), `clarification_requests`, `client_fact_revisions`
(append-only, pochodzenie), `plan_review_tasks`; zdarzenia
INTERVIEW_SUBMITTED / CLARIFICATION_REQUESTED / INTERVIEW_REVIEWED /
INTERVIEW_REMINDER w istniejącym `outbox_events`; kategoria powiadomień
`WYWIAD` (push bez treści zdrowotnych). Profil (`profile_fields`) nadal
jest zasilany tymi samymi kluczami — jedno źródło profilu.

### Definicje pytań (`dzik_os/wywiad/definicje.py`)
Zbudowane z istniejących scenariuszy: `question_id` = dotychczasowy
`step.id` (22 + 3 nowe we wstępnym, 50 w głębokim), wersja definicji 1,
typ, etykieta, sekcja, reguła widoczności (zgoda domeny + reguły
`_triggered`/`deep_triggered`), reguła wymagalności per usługa (trening /
żywienie / współpraca), walidator, opcje, klasa dostępu. Widoczność
i wymagalność liczy **serwer** po każdym zapisie; nieaktywna gałąź
zostaje w szkicu, ale nie wchodzi do wersji ani do faktów. Zmiana
znaczenia pytania = nowa wersja definicji, nigdy reinterpretacja.

## 3. API

| Operacja | Trasa |
|---|---|
| stany obu formularzy + dostęp z powodem | `GET /api/clients/{id}/wywiady` |
| definicja + odpowiedzi szkicu + fakty | `GET …/wywiady/{typ}/definicja` |
| zapis częściowy (rewizja; 409 `REVISION_CONFLICT`) | `PATCH …/wywiady/{typ}/szkic` |
| przesłanie (rewizja + `idempotency_key`; 422 `MISSING_ANSWERS` z listą) | `POST …/wywiady/{typ}/przeslij` |
| historia wersji z przeglądami | `GET …/wywiady/{typ}/historia` |
| podsumowanie / fakty / podpowiedzi (trener) | `GET …/wywiady/podsumowanie`, `…/fakty`, `…/podpowiedzi` |
| poproś o wypełnienie / przypomnij (trener; 409 gdy przesłany) | `POST …/wywiady/{typ}/przypomnij` |
| oznacz jako przejrzane / poproś o uzupełnienie | `POST /api/wywiady/zgloszenia/{id}/przeglad`, `…/doprecyzowania` |
| jedna wersja | `GET /api/wywiady/zgloszenia/{id}` |
| lista do przejrzenia; zadania sprawdzenia planu | `GET /api/coach/wywiady/do-przegladu`, `GET /api/wywiady/zadania`, `POST …/{id}/rozstrzygnij` |

Dostęp: klient — własne dane; trener — aktywna relacja (bez niej 404
z audytem) + zgoda współpracy; odpowiedzi domen bez zgody są **ukryte**
(`hidden`), nie „nieistniejące”. Notatki wewnętrzne nigdy w API klienta,
eksporcie ani push; treści odpowiedzi nie trafiają do audytu, logów ani
powiadomień.

## 4. Powiadomienia (outbox)

Przesłanie → jedno zdarzenie dla trenera; prośba o doprecyzowanie →
jedno dla klienta; przejrzenie → informacja dla klienta; przypomnienie →
jawna akcja trenera z dedup dziennym. Autozapis niczego nie wysyła.
Doręczenie od razu po commicie, ponowienie w pętli przypomnień (ten sam
mechanizm co publikacja planów, `dedup_key` per zdarzenie). Migracja nie
wysyła nic.

## 5. Testy (13.09.2026, lokalnie)

`backend/tests/test_wywiad_zakladka.py` — 18 scenariuszy odbioru:

| # | Scenariusz |
|---|---|
| 1 | każdy klient ma oba formularze od razu (`not_started`), bez wiersza w bazie |
| 2 | zapis częściowy = szkic, bez powiadomień |
| 3 | dwa urządzenia: 409 zamiast nadpisania |
| 4 | przesłanie bez wymaganych: lista braków; pominięcie ≠ odpowiedź; walidacja pól |
| 5 | przesłanie = niezmienna wersja + jeden wpis trenera; idempotencja; lista do przejrzenia; flaga |
| 6 | pytania warunkowe liczone serwerowo; nieaktywna gałąź nie wchodzi do wersji/faktów |
| 7 | postęp bez dzielenia przez zero; brak zgody = brak pytań (jawnie) |
| 8 | „nie wiem / wolę omówić” liczy się do postępu, zostaje „do wyjaśnienia” |
| 9 | przegląd per wersja; notatka wewnętrzna tylko dla trenera (API, eksport); nowa wersja = przegląd od nowa |
| 10 | doprecyzowanie: jeden wpis, statusy, zamknięcie kolejnym przesłaniem |
| 11 | uzupełnianie wspólne z autorstwem; trener bez trybu wspólnego = 422; ukrycie po cofnięciu zgody |
| 12 | zmiana faktu → zadanie sprawdzenia → 409 przy publikacji → rozstrzygnięcie → publikacja; plan nietknięty |
| 13 | podpowiedzi konfiguratorów z pochodzeniem; brak informacji ≠ zgoda |
| 14 | brak dostępu z powodem (aktywacja / zgody); brak relacji = 404; obcy klient = 404 |
| 15 | migracja syntetycznych sesji: wersje, przegląd tylko przy zatwierdzeniu trenera, szkice, ponawialność, raport bez treści, bez powiadomień |
| 16 | zatwierdzona rozmowa krok po kroku pojawia się jako wersja (+ przegląd z zatwierdzenia trenera) |
| 17 | przypomnienie jawne, jeden wpis dziennie, 409 dla przesłanego |
| 18 | outbox: awaria doręczenia → ponowienie bez duplikatu |

Macierz dostępu: 16 nowych wpisów (`tests/access_matrix.py`),
weryfikowane wykonaniem. E2E: `frontend/e2e/wywiad-zakladka.spec.ts`
(klient wypełnia z autozapisem, odświeżenie, przesłanie → trener widzi
odznakę, przegląda, prosi o uzupełnienie → klient ma jeden wpis i prośbę
przy pytaniu); `wywiad.spec.ts` (rozmowa krok po kroku przez zakładkę).
Wyniki bramek — sekcja „Weryfikacja wykonana” planu sesji.

## 6. Migracja istniejących danych

`python -m dzik_os.migruj_wywiad --raport` (liczby kontrolne, bez zapisu)
/ `--wykonaj` (ponawialnie); ta sama migracja idempotentnie przy każdym
starcie aplikacji (`lifespan`; błąd nie zatrzymuje startu, jest w
`/api/health` jako `wywiad_migracja_error`).

* sesje `CLIENT_APPROVED` / `COACH_APPROVED` → niezmienna wersja
  historyczna (`migrated=True`, `source_session_id`, autorstwo klienta,
  daty odpowiedzi i zatwierdzenia), przegląd `REVIEWED` **tylko** gdy
  `coach_approved_by` istnieje — inaczej `not_reviewed`;
* sesje `IN_PROGRESS` / `SUMMARY_READY` / `ABANDONED` → szkic
  (`collection_mode=MIGRACJA`, odpowiedzi zachowane); przy kilku —
  najnowsza, starsze w raporcie jako duplikaty;
* klienci bez odpowiedzi — nic (oba formularze `not_started`);
* niejednoznaczne (brak aktywnej relacji, brak konta) → lista do ręcznej
  weryfikacji (identyfikatory, bez treści);
* raport ma liczby przed/po i utworzone obiekty; nic nie jest usuwane;
  zero powiadomień i zdarzeń outboxu.

## 7. Ograniczenia i to, czego świadomie nie zrobiono

* **Pytania własne trenera** w sekcji „Pytania trenera” realizowane są
  przez prośby o doprecyzowanie (wiadomość + wskazane pytania), nie przez
  edytowalny słownik pytań per trener — kolejna runda.
* **Konfigurator treningu** dostaje podpowiedzi przez API
  (`…/podpowiedzi`) i kartę w zakładce; automatyczne wypełnianie
  formularza konfiguratora jedną akcją — jeszcze nie (kreator dań ma
  „Zaznacz alergeny z wywiadu”).
* **Zaproszenie na istniejące konto** nadal nie tworzy deklaracji zgód
  (decyzja RODO) — stan jest teraz jawny, nie naprawiony „siłą”.
* **Alergeny** rozpoznawane z tekstu odpowiedzi to dopasowanie słów
  kluczowych do listy kreatora — trener potwierdza ręcznie; opis spoza
  listy = ostrzeżenie, nie cicha zgoda.
* **Załączniki** (wyniki badań) i **przypomnienia cykliczne** — poza
  rundą; przypomnienie jest jawną akcją trenera.
* **Stare tabele rozmowy** zostają (kanał alternatywny); `UNIQUE
  (client_id, flow)` dla sesji rozmowy nie został dodany — duplikaty
  sesji rozmowy raportuje migracja.

## 8. Wywiad „Zapotrzebowanie kaloryczne” (0.62.0)

Trzeci typ `zapotrzebowanie` w tym samym mechanizmie (szkic, wersje,
przegląd, wspólnie). Pytania `zk_*` w `definicje.py` (4 sekcje, rodzaj
**NUMBER** z zakresem: wiek 14–100, wzrost 120–230 cm, masa 30–300 kg;
przecinek dziesiętny). Za flagą `DZIK_CALORIE_INTERVIEW_ENABLED`
(`routers/wywiady.typy_aktywne`).

**Wzór** (`wywiad/zapotrzebowanie.py`, bez AI): PPM = 10·m + 6,25·h −
5·wiek + 5 (M) / − 161 (K); PAL = baza z pracy (1,2 / 1,35 / 1,5 / 1,7)
+ treningi (0 / +0,05 / +0,15 / +0,25 / +0,35) + kroki (−0,05 … +0,1),
w [1,2; 1,9]; CPM = PPM × PAL; korekta pod cel (redukcja −10/−15/−20 %,
utrzymanie 0, masa +5/+10 %); wynik zaokrąglony do 10 kcal i nigdy
poniżej PPM (ostrzeżenie). Każdy krok ma wiersz podstawienia — trener
i klient widzą „skąd ta liczba”. Przykład kontrolny: K 70 kg / 170 cm /
30 lat, siedząca + 3–4 treningi → PPM 1452, PAL 1,35, CPM 1960; −15 % →
1670 kcal.

**Zapis:** `calorie_estimates` (migracja 33) — jedna wersja na
przesłanie (`submission_id` UNIQUE), wejścia i podstawienie zamrożone;
brak danych (np. masa poza zakresem) = brak szacunku, przesłanie ważne.

**Flaga zdrowotna:** pytanie `zk_zaburzenia` (domena zdrowie; bez zgody
nie jest zadawane) z `flag_options` „Tak / Nie wiem / Wolę omówić” →
`safety_flag` przesłania → `hidden_for_client`. Widok klienta
(`zapotrzebowanie_serwis.widok`) zwraca wtedy tylko `status="hidden"`
i komunikat — żadnej liczby na żadnym poziomie (test
`test_flaga_zdrowotna_klient_nie_dostaje_zadnej_liczby`). Trener widzi
pełne dane i po rozmowie odsłania (`POST …/odblokuj`, audyt
`CALORIE_ESTIMATE_UNHIDDEN`).

**API:** `GET /api/clients/{id}/zapotrzebowanie` (klient: swoje; trener:
relacja + zgody, dodatkowo `history`), `PUT …/nadpisanie` `{kcal|null,
reason}` (trener; 800–8000; powód obowiązkowy, widoczny dla klienta;
audyt `CALORIE_ESTIMATE_OVERRIDDEN`), `POST …/odblokuj` (trener). Obcy
trener: 404. Flaga wyłączona: 404 na typ i trasy.

**Interfejs:** `pages/wywiad/Zapotrzebowanie.tsx` (jedna karta, tryb
klient/trener): klient — Wywiad (po przesłaniu) i Dieta; trener — Wywiad
(nadpisz / wróć do wzoru / odsłoń / wspólnie) i Dieta; `PrzypiszDiete`
„Zaproponuj kcal” wypełnia pole kcal (i masę), nie przypisuje.

**Świadomie nie zrobiono:** data urodzenia (wiek w latach wystarcza,
mniej danych); automatyczne przeliczenie po nowym pomiarze masy (wynik
zmienia się tylko przez nową wersję wywiadu — świadoma decyzja klienta
albo trenera „wspólnie”); zasilanie profilu (`fact_key=None`, żeby masa
z wywiadu nie dublowała zakładki Pomiary).

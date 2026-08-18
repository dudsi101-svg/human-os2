# Changelog — Dzik OS

## 0.22.0 — 2026-08-18

Runda 14: **konwersacyjny onboarding** — rozmowa startowa zamiast ściany
formularza. Jedno pytanie na krok, z wyjaśnieniem PO CO jest potrzebne,
z możliwością pominięcia, powrotu, przerwania i wznowienia; na koniec
uporządkowane podsumowanie zatwierdzane NAJPIERW przez klienta, POTEM
przez trenera. Pełny opis architektury, schematu danych, promptów
systemowych w całości, zabezpieczeń przed wstrzyknięciem instrukcji,
minimalizacji danych, limitów kosztowych i planu wycofania migracji 17:
`docs/ONBOARDING_AI.md`.

**Cała funkcja działa end-to-end BEZ modelu językowego.** Tryb bez modelu
nie jest trybem awaryjnym drugiej kategorii — jest ścieżką domyślną,
w pełni przetestowaną, z tym samym kompletem pól. Model (gdy operator
skonfiguruje dostawcę, a klient wyrazi zgodę) może wyłącznie przygotować
**wersję roboczą podsumowania**.

* **Nowość — deterministyczny scenariusz rozmowy**
  (`onboarding_flow.py`): katalog kroków obejmujący cele, doświadczenie,
  dostępność, preferowane dni i godziny, sprzęt, ograniczenia, urazy,
  ból, sen, stres, żywienie, alergie, suplementację, preferencje
  komunikacji i informację o zgodach. Każdy krok niesie pytanie, „po co"
  i typ odpowiedzi; walidacja wyborów jest serwerowa (wartość spoza
  listy nigdy nie trafia do profilu).
* **Reguły adaptacji po stronie serwera** — brak sprzętu odsłania
  pytania o warianty domowe, zgłoszony uraz odsłania doprecyzowanie
  ograniczeń, początkujący dostaje pytanie o instruktaż techniki.
  Działają identycznie bez modelu. Pominięte pytanie **nie** odsłania
  kroków warunkowych (pominięcie niczego nie „odpowiada").
* **Dane wrażliwe zbierane tylko wtedy, gdy są potrzebne** — pytania
  zdrowotne powstają wyłącznie przy aktywnej zgodzie `dane_zdrowotne`,
  żywieniowe przy `zywienie_alergie`. Cofnięcie zgody w trakcie rozmowy
  natychmiast wycina dalsze pytania, chowa odpowiedzi przed trenerem
  i wyklucza te pola z zapisu do profilu (`skipped_fields`).
* **Objawy alarmowe** (ból w klatce, omdlenia, duszność, ostry ból po
  urazie, kołatanie serca, drętwienie/niedowład, nagły silny ból głowy):
  rozpoznaje je deterministyczna lista słów kluczowych — nie model —
  odporna na wielkość liter i brak polskich znaków. Reakcją jest spokojny
  komunikat kierujący do lekarza (112/999 przy nagłym przebiegu), bez
  diagnozy, bez nazywania przyczyny i bez straszenia; rozmowa nie jest
  przerywana, a trener dostaje wyraźny sygnał „wstrzymaj plan do
  konsultacji". Taka odpowiedź **nigdy nie jedzie do dostawcy modelu**.
* **Historia zamiast nadpisywania** (`onboarding_answers` append-only):
  poprawiona odpowiedź to nowa wersja, poprzednia zostaje. Sprzeczne
  odpowiedzi są widoczne dla trenera jako dane źródłowe z historią.
  Pominięcie zapisywane jest jawnie (`skipped`), a nie jako pusta
  wartość.
* **Przerwanie i wznowienie**: stan rozmowy (bieżący krok, odpowiedzi)
  żyje w bazie, nie w przeglądarce — nowe logowanie wraca dokładnie
  w to samo miejsce.
* **Warstwa modelu propose-only** (`onboarding_ai.py`): ścisły kontrakt
  wyjścia (Pydantic, `extra="forbid"`), biała lista pól wywiedziona ze
  scenariusza rozmowy, poziom pewności HIGH/MEDIUM/LOW per pole
  i wymuszone `needs_confirmation` dla MEDIUM/LOW — **niepewności nie da
  się ukryć**. Odpowiedź niezgodna ze schematem jest odrzucana
  (jedno ponowienie, potem tryb formularza) i nigdy nie ląduje
  w podsumowaniu ani w profilu. Wyjścia świadomie NIE naprawiamy.
* **Model nie publikuje planu ani diety** — pól planu i diety nie ma
  w białej liście, więc nie ma dokąd zapisać takiej propozycji
  (własność strukturalna, nie tylko zapis w promptcie).
* **Ochrona przed prompt injection** w czterech warstwach: wypowiedzi
  klienta wyłącznie jako WARTOŚCI w strukturze JSON (nigdy sklejane
  z instrukcją), jawne wygaszenie instrukcji z sekcji `DANE_KLIENTA`
  w promptcie systemowym, biała lista pól i walidacja wyjścia.
  Testy z czterema wektorami wstrzyknięcia (w tym próbą zamknięcia
  sekcji danych i podstawienia własnego JSON-a).
* **Minimalizacja zakresu**: do dostawcy jedzie wyłącznie lista
  `{pole, zagadnienie, pytanie, odpowiedź}` — bez identyfikatorów,
  e-maili, imion, nazwisk, bez odpowiedzi pominiętych i bez odpowiedzi
  z sygnałem alarmowym; wartości przycięte do limitu kroku, całość do
  `DZIK_AI_MAX_INPUT_CHARS`. Bez zgody `funkcje_ai` **nic** nie opuszcza
  serwera, a UI mówi to wprost (nie jako błąd techniczny).
* **Zgoda `funkcje_ai` objęła nowy cel przetwarzania** — opis kategorii
  rozszerzony o wersję roboczą podsumowania rozmowy startowej; wersja
  dokumentu zgód podbita do **2.1**, więc wcześniejsze zgody są
  oznaczone jako udzielone na starszą treść.
* **Dwie odrębne akceptacje**: klient zatwierdza podsumowanie (dopiero
  wtedy dane trafiają do profilu normalną, wersjonowaną ścieżką
  `CLIENT_DECLARED` — wspólny `profile_service.apply_profile_fields`,
  ten sam co formularz — oraz do celu głównego), trener zatwierdza je
  jako podstawę planu. Kolejność nie jest zamienna (`409`), a pola
  oznaczone niepewnością wymagają jawnego potwierdzenia przez trenera.
  Istniejący aktywny cel główny nie jest nadpisywany.
* **Suplementacja wyłącznie jako deklaracja klienta**
  (`suplementacja_deklaracja`, zgoda `zywienie_alergie`) — rozmowa nie
  tworzy planu suplementacji; ten powstaje wyłącznie w wersji planu
  diety, wprowadzony przez człowieka.
* **Ekran rozmowy** (`/rozmowa`): pasek postępu, „pomiń", „wróć",
  „przerwij i wróć później", podsumowanie do edycji i zatwierdzenia,
  jawna informacja skąd pochodzi każde pole i jaka jest jego pewność.
  Dostępność jak w P10: `aria-live` na zmianę kroku, fokus na nowym
  pytaniu, etykiety pól, `role="progressbar"` z wartością.
* **Integracja z ankietą startową**: `Intake` (`/ankieta`) **zostaje**
  jako pełnoprawny tryb awaryjny/alternatywny — obie drogi zapisują
  dokładnie te same pola profilu; ekran Dzisiaj proponuje wybór
  („Porozmawiajmy" / „Wolę formularz"), a oba ekrany linkują do siebie.
* **Widok trenera** (nowa zakładka „Rozmowa startowa" w karcie klienta):
  dane źródłowe z historią poprawek i oznaczeniem pominięć,
  podsumowanie, poziom niepewności per pole, pola do potwierdzenia,
  sygnał do konsultacji medycznej i przycisk zatwierdzenia.
* **Limity, timeouty i koszty**: `DZIK_AI_TIMEOUT_S` (20 s),
  `DZIK_AI_DAILY_CALLS_USER` (20), `DZIK_AI_DAILY_CALLS_GLOBAL` (500),
  `DZIK_AI_MAX_INPUT_CHARS` (6000); licznik wywołań i tokenów per
  użytkownik i dzień (`ai_usage_counters`), metryki w `/api/metrics`
  (`onboarding_ai_calls`, `_rejected`, `_fallback`, `_tokens_in`,
  `_tokens_out`, `onboarding_safety_flags`) — same liczby, nigdy treść.
  Logi (P9) niosą co najwyżej numer próby i kategorię odrzucenia —
  pełne rozmowy nigdy nie trafiają do logów technicznych.
* **Adapter dostawcy rozszerzony** (`ai_provider.py`): kontrakt
  `propose_json(...) -> AIJsonResponse | None` obok istniejącego
  `summarize_checkin`; domyślnie nadal `NullAIProvider` — bez klucza nic
  nie wychodzi, a UI podaje powód. Kontrakt jest w całości przetestowany
  na atrapie (poprawna odpowiedź, zły JSON, pole spoza listy, brak
  odpowiedzi, wyjątek).
* Eksport danych (`export_version` **1.4**) objął sesje rozmowy,
  wszystkie wersje odpowiedzi i podsumowanie oraz liczniki kosztów AI;
  usunięcie konta kasuje treść rozmów i liczniki.
* Migracja schematu nr **17** (cztery nowe tabele, zero ALTER-ów) —
  addytywna, z testem v1→17 i planem wycofania w `ONBOARDING_AI.md`.
* Testy: backend 413 → 460 (nowy `test_onboarding.py`: pełna rozmowa,
  przerwanie i wznowienie, sprzeczne odpowiedzi z zachowaną historią,
  pominięcia, reguły adaptacji, objawy alarmowe, brak i wycofanie zgody
  w trakcie, minimalizacja ładunku, prompt injection ×4, niedostępność
  dostawcy, błędny JSON, pole spoza białej listy, ukryta niepewność,
  limit dzienny, metryki bez treści, edycja podsumowania przez klienta,
  zatwierdzenie przez klienta i trenera, izolacja IDOR, migracja v1→17);
  frontend helpers 42 → 53 (`onboardingUtils`); Core 275 bez zmian.

## 0.21.0 — 2026-08-18

Powiadomienia i prawdziwe przypomnienia (P13): jeden spójny system dla
wszystkich kategorii i kanałów — przebudowa istniejących mechanizmów
(pętla przypomnień, pushe rozsiane po routerach), nie drugi równoległy.
Pełny opis modelu, strategii harmonogramu, zasad prywatności treści
i planu wycofania migracji 14: `docs/POWIADOMIENIA.md`.

* **Nowość — wspólny model powiadomienia** (`notifications`, migracja
  nr 14): kategoria (trening / suplement / harmonogram / raport /
  wiadomość / płatność / dokument / zmiana planu / konsultacja),
  odbiorca, kanały (centrum w aplikacji / push / e-mail), termin w UTC
  wyliczony w lokalnej strefie odbiorcy, statusy
  SCHEDULED/SENT/CANCELLED/SUPPRESSED z powodem tłumienia, **klucz
  idempotencji w bazie** (`UNIQUE(user_id, dedup_key)`) i źródło
  zdarzenia. Zastępuje dedup `_sent` w pamięci pętli — restart maszyny
  niczego nie duplikuje ani nie gubi (nadganianie do 30 min).
* **Przebudowa pętli przypomnień** (`reminder_loop`): planowanie
  dzisiejszych wystąpień (harmonogram z porą, jednorazowe przypomnienia
  trenera 08:00, płatności z dzisiejszym terminem) + doręczanie po
  terminie z bramkami PRZY WYSYŁCE: zadanie wykonane (trening
  odhaczony, raport wysłany, płatność opłacona) = przypomnienie nie
  wychodzi; wstrzymany element / odwołany slot = anulacja zaplanowanych
  wierszy (`cancel_source`).
* **Strefa czasowa per użytkownik**: nowa kolumna `users.timezone`
  (IANA) czytana przez przygotowany punkt rozszerzenia
  `dates.tz_for_user()` — steruje porami przypomnień i datami
  kalendarzowymi; DST rozstrzyga `zoneinfo` (testy na przejściu
  Europe/Warsaw). Zmiana w ustawieniach powiadomień.
* **Preferencje per kategoria × kanał** (`notification_preferences`;
  domyślnie push+centrum włączone, e-mail wyłączony) oraz
  **ciche godziny** (wyciszają push/e-mail, centrum zawsze dostaje
  wpis; zakres może przechodzić przez północ), **dni aktywne**
  przypomnień i **częstotliwość przypomnienia o raporcie**
  (codziennie vs raz w tygodniu — klucz idempotencji per dzień albo
  per tydzień ISO).
* **Dyskrecja na ekranie blokady**: push i e-mail niosą wyłącznie
  neutralny tytuł kategorii + „Masz nowe powiadomienie w Dzik OS" —
  nigdy dane zdrowotne, nazwy suplementów (SUPLEMENT ma celowo ogólny
  tytuł), kwoty, treści wiadomości ani tytuły dokumentów; klik prowadzi
  do właściwego ekranu (url per kategoria), a pełna treść jest w
  centrum po zalogowaniu. Istniejące pushe (wiadomości, raporty, plan,
  konsultacje, dokumenty) przepięte na wspólny system i zneutralizowane.
* **Nowość — centrum powiadomień w aplikacji** (`/powiadomienia`):
  lista z pełną treścią, przeczytane/nieprzeczytane (per sztuka
  i „oznacz wszystkie"), filtr kategorii, plakietka nieprzeczytanych
  w „Więcej"; **żywe aktualizacje przez SSE z P12** (zdarzenie
  `notification.new` w istniejącym kanale `/api/threads/events`).
  Na tym samym ekranie pełne ustawienia doręczeń.
* **Kontekstowe zachęty do push** (`PushContextPrompt`): zamiast prosić
  o zgodę od razu — karta z wyjaśnieniem korzyści na ekranie Dzisiaj
  (przypomnienia o harmonogramie) i w Wiadomościach (odpowiedzi
  trenera); systemowy dialog dopiero po świadomym „Włącz", „Nie teraz"
  zapamiętywane per kontekst.
* **Nowość — przypomnienie przed konsultacją**: rezerwacja slotu
  planuje powiadomienie 60 min przed startem; odwołanie terminu przez
  trenera lub zdjęcie rezerwacji anuluje je automatycznie.
* **E-mail jako opcjonalny kanał awaryjny**: per kategoria, przez
  istniejący adapter `notifications_provider` (domyślnie Null — nic nie
  wychodzi, dopóki operator nie skonfiguruje dostawcy); treść tak samo
  neutralna jak push.
* **Monitoring doręczeń** w `/api/metrics` (ADMIN): liczniki
  `notif_sent_center` / `notif_sent_push` / `notif_sent_email` /
  `notif_email_failures` / `notif_suppressed` — bez treści i bez metryk
  zaangażowania.
* Eksport danych (`export_version` 1.3) i usunięcie konta objęły
  powiadomienia, preferencje i ustawienia; zmiany ustawień audytowane
  bez treści (`NOTIFICATION_SETTINGS_CHANGED`).
* Migracja schematu nr 14 (trzy nowe tabele + `users.timezone`) —
  addytywna, z testem v1→14 i planem wycofania w POWIADOMIENIA.md.
* Testy: backend 335 → 357 (nowy `test_notifications.py`: strefa per
  użytkownik, DST Europe/Warsaw, duplikaty po restarcie, przestój
  i nadganianie, ciche godziny, dni aktywne, anulowanie terminu,
  zadanie wykonane / raport wysłany / płatność opłacona, wygasła
  subskrypcja, cofnięta zgoda, wiele urządzeń, url i neutralność per
  kategoria, preferencje, częstotliwość raportu, centrum, metryki,
  kanał e-mail); frontend helpers 36 → 42 (`notificationsUtils`:
  ciche godziny, dni aktywne, plakietka, scalanie SSE, wyłącznie
  wewnętrzne urle); Core 275 bez zmian.

## 0.20.0 — 2026-08-18

Runda 15: **wiarygodny moduł płatności** — jednoznaczne rozdzielenie
harmonogramu należności od faktycznie zarejestrowanych transakcji.
Pełny opis modelu, diagram stanów, zasady idempotencji, migracja z planem
wycofania i raport pojednania: `docs/PLATNOSCI.md`. System pozostaje
**ewidencją ręczną** (realna integracja operatora świadomie odłożona —
przygotowana wyłącznie architektura z testami kontraktu).

* **Rozdzielone modele**: należność/okres rozliczeniowy (`payment_records`,
  jak dotąd) vs append-only transakcje (`payment_transactions`: wpłata
  ręczna, wpłata operatora, zwrot, korekta, korekta odwracająca) +
  historia przejść statusu per rekord (`payment_status_changes`) + próby
  płatności i zdarzenia operatora (`payment_attempts`,
  `payment_provider_events`). Faktury: tylko pole referencji dokumentu
  zewnętrznego (`document_ref`) — bez generatora.
* **Kontrolowana maszyna stanów** (`payment_state.py`): PLANNED → PENDING
  → (IN_PROGRESS) → PAID / OVERDUE / FAILED / CANCELLED /
  PARTIALLY_REFUNDED / REFUNDED, z jawną tablicą dozwolonych przejść
  egzekwowaną w backendzie — nieprawidłowe przejście = 422.
* **Frontend nie ustawia „opłacona"**: ogólny endpoint `/status` przyjmuje
  wyłącznie statusy administracyjne (PENDING/OVERDUE/CANCELLED); statusy
  pieniężne wyłącznie przez dedykowane endpointy trenera-właściciela:
  `mark-paid` (kto i kiedy oznaczył — widoczne w UI obu paneli), `refund`
  (zwroty częściowe i pełne), `adjust` (korekta z obowiązkowym powodem),
  `transactions/{id}/reverse` (cofnięcie omyłki bez usuwania śladu).
  Wszystkie z idempotencją P11 (`idempotency_key`); podwójna wpłata bez
  klucza = 422 (PAID→PAID nie istnieje).
* **Kwoty w groszach + waluta przy każdej kwocie** (także zwroty/korekty);
  waluta operacji musi się zgadzać z walutą należności (422), sumy nigdy
  nie mieszają walut.
* **Architektura operatora (bez integracji)**: port
  `PaymentProviderPort` (podpis webhooka, parsowanie zdarzeń) +
  `NullPaymentProvider` + wspólne przetwarzanie
  `payment_events.process_webhook()` (idempotencja po `event_id`,
  powtórka=DUPLICATE, konflikt treści=CONFLICT, zła kolejność=STALE,
  PAID nigdy nie cofane, zły podpis odrzucany bez zapisu; przekierowanie
  przeglądarki niezaufane — żaden kod nie czyta parametrów powrotu).
  Endpoint HTTP webhooka celowo nie istnieje; instrukcja podłączenia
  prawdziwego operatora w `docs/PLATNOSCI.md` §7.
* **Przypomnienia o płatności** w pętli przypomnień: wyłącznie dla
  należności realnie wymagalnych (status sprawdzany w chwili wysyłki —
  zero przypomnień po opłaceniu), w dniu terminu i co 7 dni zaległości;
  treść neutralna bez kwot i nazw pakietów (ekran blokady).
* **Widok klienta** (Płatności): podział na należności i historię,
  wpisy transakcji (kto/kiedy oznaczył, zwroty, cofnięcia — przekreślone,
  nigdy usuwane).
* **Widok trenera** (karta klienta → Płatności): filtry
  zaległe/nadchodzące/opłacone, licznik zaległych, akcje wg stanu,
  rozwijana historia per rekord (przejścia + transakcje z możliwością
  cofnięcia). Nowy widok **„Pojednanie płatności"** (`/trener/rozliczenia`
  + `GET /api/payments/reconciliation`): należności vs zebrane/zwroty/
  korekty per okres, sumy per waluta, kolumna źródła (dziś adnotacje
  ręczne; format gotowy pod operatora).
* **Migracja schematu nr 15** (nr 14 zarezerwowany dla równoległej rundy):
  addytywna — statusy starych rekordów są podzbiorem nowego słownika
  (mapowanie tożsamościowe, zero utraty danych), `marked_at` uzupełnione
  z `paid_at`, nowe tabele startują puste (bez fabrykowania historii);
  plan wycofania w `docs/PLATNOSCI.md` §5.
* **Świadome zmiany starych testów**: `test_payments.py` i
  `test_e2e_paths.py` oznaczają płatność przez `mark-paid` (zamiast
  `/status PAID`); `test_idor.py` testuje IDOR statusem administracyjnym
  + `mark-paid` (schemat odrzuca „PAID" w `/status` zanim dojdzie do
  autoryzacji); stub `payment_records` dopisany do testu migracji v1.
* Testy: 335 → 365 backend (maszyna stanów, podwójna płatność
  z idempotencją i bez, zwrot częściowy/pełny/ponad stan, korekta
  + cofnięcie z pełnym śladem, różne waluty, kontrakt webhooka na Null
  — powtórka/zły podpis/zła kolejność/konflikt, IDOR wszystkich nowych
  endpointów, przypomnienia wg realnego statusu, migracja v1→v15
  z danymi płatności).

## 0.19.0 — 2026-08-18

Wspólne wyzwania i współpraca — **moduł PRYWATNY** (tylko-zaproszeni,
zero publicznych wyzwań). Pełny opis modelu, zasad prywatności, zgodności
z konstytucją Human OS (interpretacja rankingu opt-in), naliczania,
moderacji i planu wycofania migracji nr 16: `docs/WYZWANIA.md`.

* **Zgodność z konstytucją Human OS**: zakaz rankingowania ludzi jako
  mechanizmu domyślnego → ranking jest **opt-in per uczestnik i domyślnie
  WYŁĄCZONY** (obejmuje wyłącznie osoby z podwójnym opt-in:
  `share_result` + `ranking_opt_in`); domyślny widok = własny postęp
  względem celu + **zagregowany postęp grupy bez nazwisk**; wynik
  jednostkowy widoczny dla innych wyłącznie po świadomej decyzji
  uczestnika (ukrycie działa natychmiast); pseudonim per wyzwanie;
  trener nie widzi ukrytych wyników jednostkowych.
* **Model wyzwania** (migracja nr 16 — pięć nowych tabel, czysto
  addytywna, zero ALTER-ów): organizator, uczestnicy, cel, zasady,
  **wyłącznie neutralne jednostki wyniku** (`treningi`/`minuty`/
  `aktywnosci` — masa ciała odrzucana z jasnym komunikatem 422), daty
  start/koniec, **strefa czasowa wyzwania** (dzień wpisu liczony wg niej,
  nie wg strefy urządzenia), widoczność zawsze INVITE_ONLY, statusy
  DRAFT/ACTIVE/FINISHED/CANCELLED.
* **Rodzaje**: indywidualne (klient sam ze sobą — nikt inny go nie widzi,
  nawet trener), grupowe klientów tego samego trenera, prowadzone przez
  trenera. Zaproszenia wyłącznie do AKTYWNIE prowadzonych klientów.
* **Uczestnictwo dobrowolne**: zaproszenie → przyjęcie (z wyborem
  pseudonimu i ustawień widoczności) / odrzucenie; przed decyzją czytelne
  wyjaśnienie „kto zobaczy jaki wynik"; w każdej chwili: opuszczenie,
  ukrycie wyniku, wyłączenie rankingu, blokada uczestnika (obustronna
  niewidoczność), zgłoszenie do organizatora.
* **Dane zdrowotne nigdy w wyzwaniach**: moduł nie ma żadnej ścieżki do
  pomiarów, zdjęć, bólu, urazów, żywienia, raportów; jedyna integracja to
  licznik ukończonych treningów — wyłącznie z danych świadomie
  przeznaczonych do wyzwania (jawny wpis, jawne wskazanie treningu albo
  świadome „zaliczaj moje odhaczone treningi" przy dołączaniu).
* **Uczciwe liczenie**: idempotencja wpisów (`client_entry_id` +
  unikalność zgłoszonego treningu — powtórka zwraca `duplicate`, nie
  drugi wpis; auto-zaliczanie deduplikuje per dzień i wyklucza się
  wzajemnie z wpisami ręcznymi jawnym 409), korekty jako nowe wiersze z
  łańcuchem historii (nigdy nadpisanie), oznaczanie danych ręcznych,
  limit wpisów/dzień, walidacja zakresów, zamrożenie po zakończeniu.
* **Moderacja organizatora + audyt**: wyłącznie własne wyzwania
  (cudze = 404); usunięcie uczestnika, neutralizacja pseudonimu,
  czyszczenie notatek, oddalenie; zdarzenia `CHALLENGE_*` w łańcuchu
  audytu niosą wyłącznie identyfikatory i liczniki (nigdy aliasy,
  notatki, treści zgłoszeń).
* **Trwałe wycofanie udziału**: wpisy fizycznie usuwane, pseudonim
  anonimizowany, agregaty grupy trwale oznaczone „skorygowane"
  (integralność historii przez audyt, nie trzymanie danych osoby);
  usunięcie konta robi to samo dla wszystkich udziałów; eksport
  (export_version 1.3) zawiera udziały i wpisy użytkownika.
* **Nic nie wychodzi poza zamkniętą grupę**: publikowanie na zewnątrz NIE
  jest zaimplementowane — wymagałoby nowej kategorii zgody
  (docs/WYZWANIA.md §8).
* **Powiadomienia**: push przy zaproszeniu/zakończeniu/odwołaniu/
  zgłoszeniu — zawsze neutralne (bez tytułu wyzwania, aliasów, wyników);
  kanał push pozostaje opt-in przez zgodę `przypomnienia`; punkt
  integracji z przyszłym modelem preferencji P13 odnotowany w docs.
* **Frontend**: sekcja „Wyzwania" u klienta (`/wyzwania` — zaproszenia z
  wyjaśnieniem widoczności, lista z paskami postępu, szczegóły z wpisami/
  korektami/ustawieniami/blokadami, własne wyzwanie indywidualne) i u
  trenera (`/trener/wyzwania` — tworzenie, zaproszenia, cykl życia,
  uczestnicy, zgłoszenia z moderacją); linki w „Więcej"; dostępność
  wzorem P10 (etykiety `for`/`id`, `aria-pressed`, `aria-label` akcji,
  paski postępu `aria-hidden` z liczbami w tekście, karty na mobile).
* Testy: backend 335 → 355 (`test_challenges.py` — 20 testów: zaproszenie,
  odmowa, opuszczenie, ukrycie wyniku, 404 dla osób z zewnątrz i obcego
  trenera, korekta z historią, strefa czasowa wyzwania, zakończenie,
  blokada, wycofanie udziału, ranking podwójnego opt-in, idempotencja,
  auto-zaliczanie treningów, neutralny push/audyt, usunięcie konta,
  eksport; rozszerzony test migracji v1→…→16); frontend `npx tsc`,
  `npm run build`, `npm run test:helpers` (36) zielone.

## 0.18.0 — 2026-08-18

**Suplementacja jako część planu diety** — do tej pory suplementy istniały
wyłącznie jako gołe pozycje harmonogramu (nazwa + godzina), bez dawki, celu
i podstawy zalecenia w samym planie.

* Nowa sekcja **Suplementacja** w wersji planu żywieniowego: preparat, dawka,
  pora (i relacja do posiłku), cel, **podstawa zalecenia** (kto i na jakiej
  podstawie), opcjonalnie postać, okres i uwagi oraz znacznik „konsultowane
  ze specjalistą". Nazwa, dawka, pora, cel i podstawa są WYMAGANE — w planie
  nie może wylądować sama nazwa preparatu bez proweniencji.
* Bez migracji schematu: suplementacja jest częścią treści wersji planu
  (JSON), więc **każda zmiana dawki albo odstawienie preparatu zostaje
  w historii wersji** razem z powodem zmiany. Wersje sprzed tej rundy
  zwracają pustą listę (API normalizuje brakujący klucz).
* Nowa wersja planu **przenosi dotychczasową suplementację** do edytora —
  odstawienie preparatu musi być świadomym usunięciem pozycji, nigdy
  efektem ubocznym zapisania nowej wersji diety.
* `POST /api/nutrition/{plan_id}/supplements/reminders` — jednoklikowe
  przypomnienia w harmonogramie (kategoria SUPLEMENT) tworzone Z PLANU:
  dawka i sposób przyjmowania pochodzą z zapisanej pozycji, a nie z ręcznego
  przepisania, więc przypomnienie nie może rozjechać się z dietą. Wywołanie
  jest idempotentne (ta sama nazwa + godzina = pominięcie), a pozycja spoza
  bieżącej wersji planu jest odrzucana (422).
* Granice roli trenera: aplikacja niczego nie dobiera ani nie modyfikuje
  dawkowania — wyłącznie przechowuje zalecenie wprowadzone przez człowieka.
  Klient widzi przy suplementacji jednoznaczną informację, że suplementy nie
  są lekami, trener nie stawia diagnoz, a zmiany warto konsultować z lekarzem
  lub dietetykiem (zwłaszcza przy chorobach, lekach, ciąży i karmieniu).
  Trener przy edycji widzi zadeklarowane przez klienta alergie
  i nietolerancje.
* Audyt notuje fakt zmiany i LICZBĘ pozycji suplementacji — nigdy nazwy
  preparatów (nie powielamy danych zdrowotnych w dzienniku zdarzeń).
* Seed demo: plan „Redukcja 2300 kcal" ma teraz przykładową suplementację
  (witamina D3 z zaleceniem lekarza, kreatyna z zaleceniem trenera).
* Testy: 335 → 341 (walidacja kompletności wpisu, historia wersji przy
  zmianie suplementacji, audyt bez nazw preparatów, przypomnienia z planu
  + idempotencja, pozycja spoza planu, brak edycji przez klienta i izolacja
  cudzego planu).

## 0.17.0 — 2026-08-18

Runda czysto prezentacyjna: **responsywność, wygląd i dostępność**
(WCAG 2.2 AA jako punkt odniesienia) — zero zmian logiki biznesowej,
API i schematu bazy. Pełny opis, protokoły testów ręcznych i świadome
ograniczenia: `docs/DOSTEPNOSC.md`.

* **Responsywność**: formularze dwu-/trzykolumnowe schodzą do jednej
  kolumny poniżej 460 px (wyjątek `.field-row--keep` dla naprawdę
  krótkich par, np. kg × powtórzenia i porównywarki zdjęć); wszystkie
  tabele w kontenerze `.table-wrap` (kontrolowany poziomy scroll),
  a poniżej 620 px jako karty wierszy z etykietami danych
  (`data-label`); wiersze `.row` łamią się zamiast wypychać stronę
  w bok (koniec poziomego scrolla od 320 px — test e2e na
  320/375/768/1024); nowe breakpointy 700 px (stat/photo-grid
  4 kolumny) i 1200 px (szerszy panel trenera); ekran logowania na
  niskich ekranach (landscape telefonu) z mniejszym logo i układem od
  góry.
* **Rozmiary dotykowe i typografia**: przyciski min. 44 px (małe 44 px
  na ekranach dotykowych — `pointer: coarse`), linki nawigacji
  wypełniają cały pasek, checkboksy 20 px, suwaki z wyższym uchwytem;
  koniec tekstów poniżej 12 px (etykiety nawigacji z ~10,5 px → 12 px,
  podpisy suwaków i metadane wiadomości podniesione).
* **Kontrast**: obrysy elementów interaktywnych (`--border-strong`)
  podniesione do ~3:1 względem tła karty (WCAG 1.4.11); tekst
  przygaszony i kolory statusów ≥ 4,5:1 (wyliczenia w DOSTEPNOSC.md).
* **Jeden system ikon**: rozszerzony komponent `Icon` (~35 własnych SVG,
  opcjonalna dostępna nazwa `label`); emoji pełniące rolę ikon w UI
  zastąpione (nagłówki kart, skróty w „Więcej", załączniki, mikrofon,
  timer przerwy, pauza/wznów, ostrzeżenia, pobieranie…); emoji w
  treściach pisanych przez ludzi pozostają.
* **Semantyka**: skip-link „Przejdź do treści", landmarki `<main>` i
  `<nav aria-label>`, porządek nagłówków h1→h2→h3 bez przeskoków w całej
  aplikacji (nagłówki kart to teraz h2, `SectionLabel` to h3, sr-only h1
  na logowaniu), `html lang="pl"`, viewport bez blokady powiększania
  (było poprawnie — teraz pilnowane testem).
* **Formularze**: wszystkie pola z etykietami `for`/`id` albo
  `aria-label` (ok. 90 pól w 14 plikach); suwaki raportu z
  `aria-valuetext` i opisem skali; ocena raportu 1–5, dni tygodnia,
  filtry listy klientów i przełączniki archiwum jako przyciski z
  `aria-pressed` w nazwanych grupach; elementy rozwijane z
  `aria-expanded`.
* **Zakładki** (karta klienta, baza wiedzy trenera i klienta): wspólny
  komponent `Tabs`/`TabPanel` wg wzorca WAI-ARIA Tabs — role,
  `aria-selected`, roving tabindex, strzałki/Home/End.
* **Dynamiczne treści**: `role="status"`/`aria-live` dla spinnera,
  komunikatów sukcesu, banera aktualizacji PWA i stanu pobierania;
  `ErrorBox` pozostaje `role="alert"`; wykresy `Sparkline` z `role="img"`
  i generowaną alternatywą tekstową (zakres dat/wartości, ostatnia
  wartość), wykresy siły nazwane per ćwiczenie; paski postępu
  `aria-hidden` (liczby stoją obok); załączniki audio/wideo z
  dostępnymi nazwami.
* **Klawiatura i fokus**: globalny `:focus-visible` (obrys akcentu),
  pełna obsługa klawiaturą; modali własnych brak — natywne
  `confirm()`/`prompt()` (focus trap/Escape natywnie), odnotowane
  wymaganie dla przyszłych modali.
* **Ruch**: `prefers-reduced-motion` bez zmian (wyłącza animacje) —
  potwierdzone w rundzie.
* **Testy**: nowy `e2e/test_a11y.mjs` (Playwright + Chromium; axe-core
  wstrzykiwany, gdy dostępny w środowisku, plus własne asercje:
  skip-link, landmarki, etykiety pól, porządek nagłówków, brak
  poziomego scrolla na 4 szerokościach, rozmiary nawigacji, suwaki,
  wykresy, zakładki z klawiaturą, landscape logowania) — 40 kontroli
  zielonych; regresja `test_pwa_offline.mjs` zielona; backend 304 i
  Core 275 bez zmian.

## 0.16.0 — 2026-08-18

Wiadomości w czasie rzeczywistym i porządne nagrania głosowe. Pełny opis
architektury (transport, statusy, formaty audio, retencja, plan wycofania
migracji 13): `docs/WIADOMOSCI.md`.

* **Kanał czasu rzeczywistego (SSE)**: `GET /api/threads/events` —
  wybrane SSE zamiast WebSocketu (Bearer w nagłówku przez fetch — token
  NIGDY w query stringu; ten sam łańcuch middleware co reszta API:
  nagłówki P5, request id i model błędów P9, no-store; CSP connect-src
  'self' wystarcza; sw.js nie dotyka /api). Magistrala zdarzeń w pamięci
  procesu (`realtime.py`); zdarzenia: message.new / message.delivered /
  message.read / resync / session_expired + keepalive
  (`DZIK_SSE_KEEPALIVE_S`, domyślnie 25 s). **Każde doręczane zdarzenie
  przechodzi ponownie bramkę require_thread_party** (cofnięcie zgody
  odcina kanał trenera w locie), a ważność sesji jest sprawdzana W TRAKCIE
  strumienia — unieważniony token dostaje session_expired i czytelny
  powrót do logowania. Ograniczenie: jeden proces (fly:
  min_machines_running=1) — opisane w docs.
* **Reconnect + bezpieczny fallback**: frontendowy klient SSE
  (`realtime.ts`, fetch + własny parser strumienia) z wykładniczym
  backoffem 1→30 s; po 3 nieudanych próbach kontrolowany polling co 15 s
  WYŁĄCZNIE na otwartym i widocznym ekranie rozmowy, z powrotem na kanał
  gdy wróci. Lista wątków: odświeżanie liczników co 30 s na otwartym
  ekranie + przy powrocie do karty.
* **Statusy wiadomości** (migracja nr 13: `messages.delivered_at`,
  `messages.client_msg_id`, indeks porządku i częściowy indeks unikalny;
  addytywna, plan wycofania w docs): wysłana (potwierdzenie POST) →
  dostarczona (SSE/GET odbiorcy, na żywo z pokwitowaniem
  message.delivered) → przeczytana (otwarcie wątku lub
  `POST /threads/{id}/read` przy otwartym ekranie). Znaczniki
  monotoniczne, ustawia wyłącznie odbiorca; licznik nieprzeczytanych per
  wątek jak dotąd w `GET /api/threads`.
* **Deduplikacja i kolejność**: `client_msg_id` z urządzenia nadawcy
  (UUID) — ponowienie po utracie sieci zwraca istniejącą wiadomość
  (`duplicate: true`), unikalność per (wątek, autor, client_msg_id)
  także indeksem w bazie; stabilny porządek `(created_at, id)` po obu
  stronach; UI scala duplikaty i spóźnione zdarzenia
  (`messaging.ts::mergeMessage`).
* **Paginacja historii**: `?limit=50&before=<id>` + `has_more` i przycisk
  „Wczytaj starsze wiadomości"; kursor spoza wątku → 404; dociąganie
  starszych NIE znaczy przeczytania.
* **Szkic per wątek**: treść pola przeżywa utratę sieci, nawigację
  i przeładowanie (sessionStorage, czyszczony po wysłaniu); optymistyczny
  dymek „wysyłanie…" podmieniany potwierdzeniem serwera, a błąd wysyłki
  nie czyści formularza.
* **Nagrania głosowe naprawione**: format przez
  `MediaRecorder.isTypeSupported` (webm/opus → Chrome/Firefox/Android;
  audio/mp4 AAC → Safari/iOS ≥ 14.3), wysyłany RZECZYWISTY
  `recorder.mimeType` (typ bazowy, koniec ze sztywnym audio/webm),
  rozszerzenie wg typu; limit 3 min (auto-stop bez utraty nagrania)
  i 15 MB; odsłuch/nagraj ponownie/usuń przed wysłaniem; `track.stop()`
  na WSZYSTKICH ścieżkach mikrofonu po stopie, anulowaniu, błędzie
  i odmontowaniu; wszystkie Blob URL zwalniane. Logika wydzielona do
  testowalnego `audioCapture.ts` (wstrzykiwane getUserMedia/MediaRecorder).
* Backend audio bez zmian allowlisty (webm/m4a/mp3/ogg już wspierane —
  zweryfikowane magic bytes testami, w tym niezgodność zawartości i typ
  z parametrem kodeka = 415).
* **Prywatność**: treści rozmów i nagrania poza logami/metrykami/push
  (push nadal neutralne „Nowa wiadomość" — test); zdarzenia SSE nie są
  logowane; IDOR = 404 na wszystkich nowych ścieżkach. Retencja
  i usuwanie: anonimizacja wątków przy usunięciu konta zweryfikowana,
  osierocone głosówki trenera sprząta pętla plików-sierot — opis
  w `docs/WIADOMOSCI.md` §6.
* Testy: backend 304 → 323 (`test_messages_realtime.py` — wymiana dwóch
  użytkowników, duplikaty, kolejność, paginacja, IDOR, sesja na kanale,
  magistrala + przepełnienie, push bez treści, formaty audio; migracja
  v1→v13); frontend `npm run test:helpers` 10 → 29 (parser SSE, backoff,
  scalanie/porządek, szkice, wybór formatu, kontroler nagrywania —
  odmowa mikrofonu i odmontowanie w trakcie nagrania włącznie). Żywy
  strumień zweryfikowany uvicorn+curl (ograniczenie TestClienta w docs).

## 0.15.0 — 2026-08-18

Jakość raportów i zdjęć progresu: **koniec fałszywych danych z domyślnych
suwaków 3/5, pełny UX wysyłki zdjęć, idempotencja zapisu**.

* **Suwaki bez wartości domyślnej**: każde pytanie subiektywne raportu
  startuje PUSTE — użytkownik świadomie wybiera 1–5 (z opisem krańców:
  „1 = brak energii · 5 = pełna energia") albo oznacza pytanie jako
  „Pomijam" / „Nie dotyczy"; bez decyzji przy każdym pytaniu raportu nie
  da się wysłać. Model danych rozróżnia CZTERY stany odpowiedzi
  (`payload.scale_states`): brak odpowiedzi (brak klucza), świadoma
  wartość ANSWERED (w tym neutralne 3/5), świadome pominięcie SKIPPED,
  brak zastosowania NOT_APPLICABLE. Walidacja spójności w backendzie
  (ANSWERED wymaga wartości; SKIPPED/NOT_APPLICABLE jej zabrania; wartość
  bez stanu = 422). Stare raporty NIE są reinterpretowane — wiersze sprzed
  zmiany zostają, API oznacza je `scales_declared=false`, a UI trenera
  pokazuje notę „suwaki mogły pozostać na wartości domyślnej 3/5".
* **Idempotencja zapisu** (migracja nr 12, tabela `idempotency_keys`):
  pole `idempotency_key` w POST /api/checkins — powtórka tego samego
  żądania (podwójne kliknięcie, retry po utracie odpowiedzi sieci) zwraca
  zapisany wynik zamiast tworzyć rewizję; ten sam klucz z inną treścią =
  jawny 409. Przycisk wysyłki dodatkowo zablokowany na czas wysyłania.
  Klucze per użytkownik+operacja; usuwane przy usunięciu konta.
* **Wersja robocza formularza**: draft w localStorage per użytkownik +
  tydzień (pola, decyzje skal, klucz idempotencji) — przywracany po
  błędzie/zamknięciu karty; czyszczony po udanej wysyłce. Zdjęcia
  (obiekty File) świadomie poza draftem — z jawnym komunikatem.
* **Raport częściowy jako stan jawny**: `weekly_checkins.photos_expected`
  (migracja 12) — klient deklaruje liczbę zdjęć przy wysyłce; raport z
  mniejszą liczbą zapisanych jest oznaczony „częściowy · zdjęcia A/B"
  u klienta i trenera (`photos_complete` w API), do dokończenia przez
  nowy `POST /api/checkins/{id}/photos` (dopięcie brakujących po jednym
  albo świadome zamknięcie bez nich, `set_expected`). Po ocenie trenera
  zdjęcia raportu są zamrożone (409).
* **Pełny UX wysyłki zdjęć**: podgląd miniatur przed wysłaniem, obrót
  zgodny z orientacją EXIF, usuwanie i zmiana kolejności (↑/↓), opis typu
  ujęcia (przód/bok/tył/inne — kolumny `progress_photos.pose`/`position`,
  widoczne też u trenera i na liście zdjęć), pasek postępu per plik
  (upload przez XMLHttpRequest — `uploadFileWithProgress` w api.ts),
  anulowanie w trakcie, ponowienie wyłącznie nieudanych plików. Każde
  zdjęcie jest dopinane do raportu zaraz po udanym uploadzie — przerwanie
  sieci zostawia trwały, widoczny stan częściowy, nie sieroty.
* **Kompresja i EXIF po stronie klienta**: przed wysłaniem zdjęcie
  przechodzi przez createImageBitmap+canvas (maks. 2048 px, JPEG 0.85) —
  co naturalnie usuwa wszystkie metadane EXIF (w tym GPS) już na
  urządzeniu; backendowy strip z P4 (magic bytes, allowlista, limit
  strumieniowy, Pillow re-encode) zostaje jako druga warstwa i jedyna
  dla przeglądarek bez canvas (fallback = oryginał).
* **Korekta raportu**: bez zmian mechaniki (nowa rewizja, poprzednia
  treść w `checkin_revisions`, po ocenie 409) — ale dane skorygowane są
  teraz OZNACZONE: `corrected` w API, badge „skorygowany" u klienta
  i trenera.
* **Wykresy bez interpolacji dziur**: `seriesUtils.withGaps` wstawia
  przerwy w serie o znanym rytmie (samopoczucie — tygodnie bez raportu,
  dziennik kaloryczny — dni bez wpisu), a `Sparkline` renderuje segmenty
  z przerwaną linią zamiast łączyć przez dziurę; pominięte pytania nie
  generują punktów. Punkty samopoczucia niosą `declared` (false = raport
  sprzed rozróżniania stanów — nota o wiarygodności pod wykresem).
* **Prywatność zdjęć zweryfikowana**: zdarzenia audytu raportu/zdjęć
  niosą wyłącznie liczniki (`photos_attached`/`photos_expected`) — zero
  id i nazw plików (test); push bez zmian (neutralne wezwanie); logi
  strukturalne z P9 nadal wyłącznie z szablonami ścieżek.
* Testy: backend 304 → 316 (`test_checkin_quality.py`: cztery stany
  odpowiedzi, walidacja spójności, ścieżka legacy, idempotencja z 409
  i separacją per użytkownik, częściowy upload + dokończenie/zamknięcie,
  odmowy po ocenie/cudzy plik/cudzy raport, pose+kolejność, korekta
  z historią, flaga `declared` w monitoringu, brak wycieku zdjęć do
  audytu; migracja v1→v12 ze stubem `progress_photos`); frontend
  `npm run test:helpers` 7 → 14 (withGaps: dziury tygodniowe/dzienne,
  tolerancja 1,5×, przełom roku, daty niepoprawne).

## 0.14.0 — 2026-08-18

Przebudowa zgód i zgodności z RODO: **zgody granularne per kategoria
danych**, pełna informacja przy każdej zgodzie, kompletniejszy eksport
i usuwanie danych, pakiet dokumentacji RODO.

* **Katalog kategorii zgód** (`consent_catalog.py`, wersja dokumentu
  2.0): 10 odrębnych kategorii — prowadzenie konta, udostępnianie danych
  trenerowi, dane treningowe, komunikacja (wymagane, podstawa umowna)
  oraz dane zdrowotne, żywienie i alergie, zdjęcia progresu,
  przypomnienia/push, funkcje AI, marketing (opcjonalne zgody, art. 9
  dla wrażliwych). Każda kategoria niesie cel, zakres danych, odbiorców,
  okres przechowywania, informację o dobrowolności, sposób wycofania,
  podstawę prawną i wersję dokumentu. Zgody wymagane i opcjonalne nie
  są nigdy łączone; nie istnieje „zaakceptuj wszystko" dla niezależnych
  celów (jedyna decyzja grupowa: warunki jednej umowy o współpracę).
* **Autoryzacja per domena danych**: `resolve_client_access(domain=...)`
  — cofnięcie zgody jednej kategorii odbiera trenerowi dostęp tylko do
  niej (np. cofnięcie „żywienie i alergie" chowa dietę, dziennik
  kaloryczny i pola `alergie`/`preferencje_zywieniowe` profilu, nie
  ruszając planu treningowego). Pliki bramkowane wg kategorii zasobu
  (zdjęcie/dokument-DIETA/załącznik treningu/pozostałe). Agregat
  monitoringu wycina sekcje żywieniową i adherencji bez właściwych zgód.
  Historyczne zgody parasolowe (sprzed migracji) są honorowane w
  pierwotnym, pełnym zakresie — migracja niczego po cichu nie zawęża
  ani nie unieważnia (test).
* **Migracja nr 10**: `consents.category`, `legal_basis`, `source`,
  `denied_at` (czysto addytywna; plan wycofania w `ZGODY_MODEL.md` §7).
* **API zgód**: `GET /api/me/consents` zwraca katalog + historię z
  flagą aktualności wersji dokumentu; `POST /api/me/consents`
  {category, grantee_id}; nowy `POST /api/me/consents/decline` — jawna
  odmowa zgody opcjonalnej z historią (`denied_at`, zdarzenie
  CONSENT_DECLINED); cofnięcie `przypomnienia` usuwa wszystkie
  subskrypcje push; subskrypcja push rejestruje zgodę `przypomnienia`.
* **Zgoda klienta bramkuje funkcje AI**: `POST /api/checkins/{id}/
  ai-summary` wymaga aktywnej zgody `funkcje_ai` PODMIOTU danych —
  decyzja trenera nie zastępuje zgody klienta (dalej propose-only,
  domyślnie NullAIProvider).
* **Onboarding**: trener rejestruje ODRĘBNE deklaracje per kategoria
  (bez przypomnień/AI/marketingu — te tylko od klienta); klient przy
  pierwszym logowaniu potwierdza warunki wymagane i decyduje o każdej
  zgodzie wrażliwej osobno (Wyrażam zgodę / Odmawiam). Zachowane po P3:
  podpięcie istniejącego konta nie nadaje żadnej zgody.
* **Eksport** (JSON + Excel, export_version 1.2): dodane consult_slots,
  push_subscriptions (bez kluczy kryptograficznych subskrypcji),
  audit_receipts, schedule_completions; zgody z pełnym kontekstem
  kategorii/podstawy/wersji.
* **Usunięcie konta** — domknięte luki: usuwane subskrypcje push,
  odpinane sloty konsultacji (przyszłe wracają do puli), anonimizowane
  wolne teksty (cele, przypomnienia, harmonogram, komentarze i notatki
  bólu treningów, tytuły dokumentów, notatki płatności); ewidencja
  rozliczeń (kwoty/terminy/statusy) pozostaje — obowiązek podatkowy.
* **UI klienta**: nowy ekran zgód (onboarding) i karta „Prywatność
  i zgody" w Profilu — stan per kategoria, pełny opis (cel/zakres/
  odbiorcy/okres/wycofanie/wersja), historia decyzji, udzielanie i
  cofanie per kategoria; usunięte nieprawdziwe zdanie „dane nie są
  nikomu dalej przekazywane". Panel trenera: badge „ograniczone zgody"
  z listą brakujących kategorii.
* **Dokumentacja RODO** (docs/): `ZGODY_MODEL.md` (model + migracja +
  plan wycofania + decyzje administratora), `RODO_REJESTR_CZYNNOSCI.md`
  (rejestr czynności, administrator, procesorzy, retencja),
  `RODO_INCYDENTY.md` (proces obsługi incydentów), `RODO_DPIA.md`
  (wskazanie ws. DPIA), polityka prywatności v0.2 (prawdziwy opis
  hostingu Fly.io, adapterów Null poczty/AI, braku płatności online,
  self-hostowanych fontów, push, backupów i retencji; realizacja praw:
  eksport/poprawianie/usunięcie/anonimizacja/rozliczenia). Miejsca
  wymagające decyzji oznaczone „DECYZJA ADMINISTRATORA DANYCH" — to
  nie jest gwarancja prawna.
* Testy: 232 → 244 (nowe: `test_consent_categories.py` — odmowa,
  wersje dokumentu, bramka AI, push↔zgoda, onboarding per kategoria,
  zgoda parasolowa; przebudowane `test_consents.py` — utrata dostępu
  per kategoria; rozszerzone `test_privacy.py` — eksport, usunięcie z
  zachowaniem rozliczeń; migracja v1→v10). Świadomie zaktualizowane
  istniejące testy zbiorczego modelu zgód (szczegóły w ZGODY_MODEL.md).

## 0.13.0 — 2026-08-18

Obsługa błędów i obserwowalność: **koniec cichych awarii** (bez zmian
schematu bazy — zarezerwowana migracja nr 12 nie była potrzebna).
Szczegóły i progi alertowe: `docs/OBSERVABILITY.md`.

* Wspólny model błędów API: `{detail, code, request_id[, errors]}` —
  `detail` pozostaje bezpiecznym polskim komunikatem (kompatybilność
  z frontendem i testami), `code` to stabilny kod (`NOT_FOUND`,
  `VALIDATION_ERROR`, `RATE_LIMITED`…), `request_id` wraca też w nagłówku
  `X-Request-Id` każdej odpowiedzi. Globalne handlery FastAPI:
  `HTTPException`, `RequestValidationError` (422 z listą pól, celowo BEZ
  pydanticowego `input` — wartość mogłaby być daną zdrowotną) oraz
  `ErrorEnvelopeMiddleware` dla nieobsłużonych wyjątków (500 bez stack
  trace/SQL/komunikatów wewnętrznych; nagłówki bezpieczeństwa i no-store
  obejmują też 500). Handler `ResourceAccessDenied` z P3 bez zmian
  (nadal 404 + audyt ACCESS_DENIED, teraz też licznik w metrykach).
* Strukturalne logi backendu (stdout, JSON): request id, metoda + SZABLON
  ścieżki (`/api/clients/{client_id}/...` — nigdy surowe id), status, czas
  odpowiedzi, bezpieczny identyfikator użytkownika (id, nie e-mail).
  Redakcja obowiązkowa: zero danych zdrowotnych, treści wiadomości,
  e-maili, tokenów, endpointów push; wyjątki logowane jako typ + ramki
  stosu `plik:linia:funkcja` BEZ komunikatu (komunikaty ORM potrafią nieść
  parametry SQL). `print()` w push/pętli/seed/audycie zastąpione logiem
  strukturalnym; log e-maili nie zawiera już tematu wiadomości.
* Monitoring: `GET /api/metrics` (tylko ADMIN) — liczniki 2xx/4xx/5xx,
  percentyle czasu odpowiedzi p50/p95/p99 (okno 1000 żądań), błędy pętli
  przypomnień, nieudane pushe, nieobsłużone wyjątki, odmowy dostępu,
  awarie zapisu audytu. `GET /api/ready` (readiness: baza + zapisywalność
  katalogu uploadów, 503 gdy nie; bez sekretów) obok istniejącego
  `/api/health`. Progi alertowe opisane w `docs/OBSERVABILITY.md`
  (dokument + metryki, bez zewnętrznych integracji).
* Błędy JS frontendu: `POST /api/telemetry/frontend-errors` (dostępny bez
  logowania, rate limit 10/min/IP + 120/min globalnie + 5/min klientowo) —
  przyjmuje wyłącznie typ błędu, etykietę komponentu/trasy (id maskowane
  do `{id}`) i stos zredagowany do `plik.js:linia:kolumna`; serwer redaguje
  ponownie (defense in depth) i przechowuje tylko licznik + linię logu.
  Podpięte: globalny i per-trasa `ErrorBoundary` (koniec białego ekranu
  po awarii renderowania — czytelny ekran z „Spróbuj ponownie"),
  `window.onerror`, `unhandledrejection`.
* Frontend — koniec ukrytych `.catch(() => undefined)` (ok. 20 miejsc):
  sekcje pomocnicze (historia treningów, cele, zgody, zdjęcia, monitoring,
  statystyki trenera, pokwitowania, harmonogram, wersje planów, rekordy,
  wykresy siły) pokazują błąd z przyciskiem „Spróbuj ponownie" zamiast
  cicho znikać; nieobsłużone `await` w akcjach (cele, płatności, statusy,
  ocena raportu, weryfikacja audytu, eksporty) dostały obsługę błędów.
  Świadome wyjątki pozostały wyłącznie z komentarzem uzasadniającym
  (karty-podpowiedzi na „Dzisiaj", fail-open bramy zgód — egzekwowanie
  zgód i tak w backendzie, best-effort telemetrii/push/service workera).
* Klient API: timeout żądań 20 s (AbortController) z komunikatem po polsku,
  klasyfikacja offline/timeout/anulowanie (`ApiError.code`), anulowanie
  nieaktualnych żądań przy zmianie widoku/parametru (wątek wiadomości,
  karta klienta, miniatury i załączniki plików, wykresy — spóźniona
  odpowiedź nie nadpisze cudzych danych), 401 → powrót do logowania
  z jednorazowym komunikatem „sesja wygasła" na ekranie logowania.
  Błąd zapisu NIE czyści formularza (trening, cel, ocena raportu —
  komunikat przy formularzu, dane zostają).
* Backend — każdy `except: pass` przejrzany: świadome zignorowania mają
  komentarz uzasadniający (daty historyczne w monitoringu, uszkodzony JSON
  w eksporcie — pole zostaje w surowej postaci zamiast znikać, uszkodzone
  serie w rekordach); pętla przypomnień i push liczą błędy w metrykach.
* Testy: backend 232 → 250 (kształt modelu błędu dla 401/403/404/409/422/
  429/500, request id, redakcja logów i raportów JS, maskowanie ścieżek,
  metryki, readiness, rate limit telemetrii, IDOR w nowym kształcie);
  frontend: `npm run test:helpers` (Node, bez nowych zależności) — logika
  timeout/anulowanie/offline, redakcja stosu, maskowanie id w trasach,
  nazwy plików z Content-Disposition.

## 0.12.0 — 2026-08-18

Runda tożsamości: **zaproszenia z aktywacją konta, bezpieczny reset hasła
i MFA (TOTP)** — koniec hasła startowego widocznego dla trenera.

* **Zaproszenia zamiast hasła startowego**: trener podaje wyłącznie
  e-mail i imię; konto powstaje jako PENDING (bez żadnego hasła, login
  zablokowany), a klient otrzymuje jednorazowy link aktywacyjny
  (`/aktywacja#TOKEN` — token we fragmencie URL, poza logami serwera)
  i SAM ustawia hasło na ekranie aktywacji bez logowania. Token:
  `secrets.token_urlsafe(32)`, w bazie tylko hash SHA-256, ważny 7 dni,
  jednorazowy, anulowalny; ponowne wysłanie unieważnia poprzedni.
  Przepływ P3 dla istniejących kont (relacja bez auto-zgody) bez zmian.
* **Kompromis NullProvider (jawny)**: bez skonfigurowanego dostawcy
  e-mail link aktywacyjny wraca trenerowi w UI jako „link do
  przekazania”; ze skonfigurowanym dostawcą idzie wyłącznie e-mailem
  (trener go nie widzi) — opisane w PERMISSIONS.md.
* **Bezpieczny reset hasła**: `/reset-hasla` — żądanie z ogólnym
  komunikatem niezależnym od istnienia konta (bez enumeracji), limit
  prób per e-mail+IP, token hashowany (SHA-256) ważny 60 min,
  jednorazowy, nowszy unieważnia starszy; po resecie unieważnienie
  WSZYSTKICH sesji konta. Link wyłącznie e-mailem (przy NullProviderze
  reset wymaga skonfigurowanego dostawcy — świadomie bez linku w API).
* **MFA (TOTP RFC 6238)** w czystym Pythonie (stdlib hmac/struct, zero
  zależności): sekret base32 + URI `otpauth://` (tekst do przepisania /
  otwarcia w aplikacji), potwierdzenie kodem, logowanie dwuetapowe
  (wyzwanie 5 min, tylko hash w bazie), okno ±1 kroku z ochroną przed
  ponownym użyciem kodu (licznik ostatniego okna), limit prób i audyt
  nieudanych weryfikacji. **Obowiązkowe dla COACH/ADMIN**
  (`DZIK_MFA_REQUIRED_ROLES`): do pierwszej konfiguracji konto ma dostęp
  wyłącznie do ekranu konfiguracji MFA (403 `MFA_SETUP_REQUIRED`,
  wzorzec jak wymuszona zmiana hasła), wyłączenie zablokowane; dla
  CLIENT opcjonalne. WebAuthn/passkeys opisane w PERMISSIONS.md jako
  następny krok (świadomie nieimplementowane).
* **Kody odzyskiwania**: 10 jednorazowych kodów pokazywanych tylko raz
  (w bazie hashe), logowanie kodem audytowane z liczbą pozostałych,
  regeneracja za kodem TOTP unieważnia wszystkie stare.
* **Historia bezpieczeństwa konta**: `GET /api/auth/security-events`
  (logowania, nieudane MFA, resety, kody, zakończenia sesji — metadane
  bez tokenów) jako karta obok „Aktywnych sesji” (Profil / Więcej).
* **E-maile bez danych zdrowotnych**: naprawiony e-mail o niepokojącej
  obserwacji (wysyłał kategorię i pełną treść wpisu) — teraz neutralne
  wezwanie do panelu; treści zaproszeń/resetów projektowane bez PII
  zdrowotnego i potwierdzone testami.
* Migracja schematu nr 11 (kolumny `users.totp_*`, tabele
  `client_invitations`, `password_reset_tokens`, `mfa_recovery_codes`,
  `mfa_challenges`) — addytywna, plan wycofania w PERMISSIONS.md. Nowe
  ustawienia: `DZIK_INVITATION_TTL_DAYS`, `DZIK_RESET_TOKEN_TTL_MIN`,
  `DZIK_RESET_MAX_REQUESTS`, `DZIK_RESET_WINDOW_MIN`,
  `DZIK_MFA_REQUIRED_ROLES`, `DZIK_MFA_CHALLENGE_TTL_MIN`,
  `DZIK_PUBLIC_URL`.
* UI: ekran aktywacji, ekran resetu (żądanie + nowe hasło), krok MFA w
  logowaniu (kod TOTP/odzyskiwania), wymuszony ekran konfiguracji MFA
  (`/mfa`), karta MFA w Profilu klienta i w „Więcej” trenera/admina,
  formularz „Zaproś podopiecznego” bez pola hasła + status „oczekuje na
  aktywację” z ponowieniem/anulowaniem zaproszenia, link „Nie pamiętasz
  hasła?”.
* Konta demo seedu pozostają aktywne z hasłami z seedu (nowy przepływ
  dotyczy kont zakładanych przez UI/API); stare testy hasła startowego
  przepisane świadomie na przepływ zaproszeń (mechanizm
  `must_change_password` zachowany dla kont historycznych i nadal
  testowany).
* Testy: 232 → 256 (zaproszenia: ważne/wygasłe/ponowne
  użycie/anulowanie/ponowienie/izolacja trenerów/brak tokenu w audycie;
  reset: brak enumeracji, jednorazowość, wygaśnięcie, unieważnienie
  sesji, limit prób; MFA: wektor RFC, dobry/zły kod, okno czasowe,
  replay, kody odzyskiwania, wymuszenie dla trenera, opcjonalność dla
  klienta, sekrety poza audytem; historia bezpieczeństwa).

## 0.11.1 — 2026-08-18

* **Harmonogram kopii zapasowych (R-12, operacyjnie)**: nowy workflow
  `.github/workflows/fly-backup.yml` — codzienny backup na maszynie
  Fly.io (02:30 UTC) + uruchomienie na żądanie; archiwa na wolumenie
  `/data/backups` (retencja 14), bez pobierania danych do artefaktów
  GitHub Actions. Dokumentacja §4a zaktualizowana.

## 0.11.0 — 2026-08-18

Zamknięcie dwóch ryzyk z rejestru: R-12 (kopie zapasowe) i R-02 w części
plikowej (szyfrowanie at-rest uploadów).

* **Kopie zapasowe (R-12 — zamknięte)**: nowe narzędzie
  `python -m dzik_os.backup` tworzy jedno spójne, znakowane czasem
  archiwum `dzik-backup-<timestamp>.tar.gz`: główna baza przez sqlite3
  backup API (PostgreSQL: `pg_dump`, wykrywane z `DZIK_DATABASE_URL`),
  baza audytu Human OS (`audit.db`, też backup API) i katalog uploadów
  w postaci, w jakiej leży na dysku (czyli zaszyfrowanej). Retencja
  `DZIK_BACKUP_KEEP` (domyślnie 14), katalog `DZIK_BACKUP_DIR`
  (domyślnie `data/backups`). Odtwarzanie `--restore <archiwum>`
  z odmową nadpisania istniejących danych bez `--force`; po odtworzeniu
  łańcuch audytu jest weryfikowany (`verify_chain()`) i wynik jawnie
  raportowany. Pełny cykl backup → utrata danych → restore → weryfikacja
  łańcucha pokryty testem; harmonogram i snapshoty wolumenów Fly opisane
  w DEPLOYMENT §4a.
* **Szyfrowanie plików at-rest (R-02 — część plikowa zamknięta)**:
  uploady szyfrowane AES-256-GCM przy zapisie i deszyfrowane przy
  odczycie (`storage.py`), klucz z env `DZIK_FILE_KEY` (base64,
  32 bajty). Zaszyfrowane pliki mają nagłówek magiczny `DZIKENC1`;
  pliki wgrane przed włączeniem klucza czytane są wprost (kompatybilność
  wsteczna). Brak klucza = zachowanie dotychczasowe plus jedno
  ostrzeżenie w logu poza dev/test; zaszyfrowany plik bez klucza lub
  z błędnym kluczem to jawny błąd 500, błędny format klucza zatrzymuje
  start — tryby nigdy nie mieszają się po cichu. Klucz przechowywać
  OSOBNO od backupów (DEPLOYMENT §4b). Nowa zadeklarowana zależność
  backendu: `cryptography>=42,<47`. Otwarta pozostaje część bazodanowa
  R-02 (dysk szyfrowany / pgcrypto; wolumeny Fly szyfrowane blokowo).
* Testy: 97 → 115 (backup/restore/retencja, szyfrowanie — roundtrip,
  plik legacy, praca bez klucza; testy uploadów przechodzą w obu
  trybach przez sparametryzowaną fixture).

## 0.10.1 — 2026-08-18

Audyt i utwardzenie **całego systemu plików** (bez zmian schematu bazy).

* Naprawa pobierania z frontendu: wszystkie bezpośrednie linki do
  chronionych `/api/files/{id}` (PDF diety w Dieta, „Otwórz" w
  Dokumentach) zastąpione wspólnym `FileDownloadButton` — pobranie przez
  uwierzytelnione API do Blob, zapis/otwarcie klikiem w `<a>` (bez
  blokady popupów), poprawna nazwa z `Content-Disposition`, zawsze
  `URL.revokeObjectURL`; widoczne stany pobieranie/sukces/błąd/brak
  dostępu (także w `AuthAttachment`).
* Dieta: `document_id` (FK do `documents`) był wysyłany do frontendu
  jako rzekome id pliku — API zwraca teraz dodatkowo
  `document_file_id` (id pliku aktywnego dokumentu), a `document_id`
  jest walidowane przy tworzeniu wersji (dokument musi być ACTIVE i
  należeć do klienta planu).
* Upload: rozpoznawanie typu po ZAWARTOŚCI (magic bytes: PDF/PNG/JPEG/
  WEBP/MP4/WEBM/MP3/OGG) — niezgodność deklaracji z zawartością = 415
  (odrzuca m.in. `plik.pdf.exe`); limit rozmiaru egzekwowany
  strumieniowo; sanityzacja nazwy z wymuszonym kanonicznym rozszerzeniem;
  SVG i pliki wykonywalne poza allowlistą (jak dotąd) + potwierdzone
  testami.
* Zdjęcia (NOWE uploady image/*): usunięcie WSZYSTKICH metadanych EXIF
  (w tym GPS) z zachowaniem orientacji, dłuższy bok maks. 2560 px,
  rekompresja (jakość 85, Pillow). Istniejące pliki na dysku pozostają
  bez zmian (świadomie: bez retroaktywnego przetwarzania).
* Pobieranie: `Content-Disposition` wg RFC 5987 (sanityzowana nazwa),
  `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`;
  weryfikacja, że `storage_path` nie wychodzi poza katalog uploadów
  (path traversal = 404).
* Autoryzacja pobrania domknięta dla WSZYSTKICH ścieżek: właściciel;
  trener przez relację+zgodę (`resolve_client_access` — cofnięcie zgody
  odbiera dostęp też do ISTNIEJĄCYCH plików, test); załącznik wątku
  (klient zawsze, trener tylko przy AKTYWNEJ relacji); załącznik
  AKTYWNEGO wpisu bazy wiedzy dla aktywnie prowadzonych klientów
  (wcześniej klienci dostawali 404).
* Podpinanie plików walidowane wszędzie (`require_attachable_file`):
  wiadomości, zdjęcia raportu (limit 8 szt. / 60 MB łącznie, tylko
  obrazy własne), dokumenty (plik musi należeć do klienta), baza wiedzy
  (tylko plik własny trenera), wpisy treningowe — koniec z podpinaniem
  cudzych `file_id`.
* Pliki-sieroty: upload bez żadnej referencji po 24 h dostaje soft
  delete (`deleted_at`) i znika z dysku (pętla co godzinę + pierwszy
  przebieg po starcie; zdarzenie audytowe ORPHAN_FILES_CLEANED).
* Nowa zależność backendu: Pillow (>=10,<12). Nowe ustawienia:
  `DZIK_MAX_IMAGE_PX`, `DZIK_IMAGE_QUALITY`, `DZIK_MAX_CHECKIN_PHOTOS`,
  `DZIK_MAX_CHECKIN_PHOTOS_TOTAL_MB`, `DZIK_ORPHAN_FILE_TTL_H`.
* Testy: 113 → 134 (magic bytes, podwójne rozszerzenie, path traversal,
  EXIF, limity, cofnięta zgoda, wygasła relacja, baza wiedzy, sieroty,
  soft delete, nagłówki odpowiedzi).


## 0.10.0 — 2026-08-18

Runda bezpieczeństwa sesji: **serwerowe unieważnianie, rotacja tokenów,
ekran aktywnych sesji** (audyt wylogowania bez nagłówka autoryzacji).

* Naprawa audytowanej luki: wylogowanie szło gołym `fetch` bez nagłówka
  `Authorization`, więc serwer unieważniał co najwyżej sesję z ciasteczka
  (przy kilku kartach — potencjalnie cudzą kartę, nie bieżącą). Wszystkie
  operacje uwierzytelniania przechodzą teraz przez wspólnego klienta API
  (`api.ts`: `login`/`logout`/`changePassword`/`listSessions`/…); lokalne
  czyszczenie sesji działa też przy utracie połączenia (`finally`).
* Zmiana hasła = rotacja tokenu: serwer unieważnia WSZYSTKIE dotychczasowe
  sesje (z bieżącą włącznie) i wydaje nowy token — zero aktywnych starych
  tokenów; ponowne użycie unieważnionego tokenu to zawsze 401. Limit prób
  zmiany hasła (`password_change_rate_limiter`) analogiczny do logowania.
* Nowe endpointy: `GET /api/auth/sessions` (aktywne sesje: utworzona,
  ostatnie użycie, urządzenie, bieżąca oznaczona — bez tokenów/hashy),
  `POST /api/auth/sessions/{id}/revoke` (własna sesja; cudza = 404),
  `POST /api/auth/sessions/revoke-others`. Zdarzenia audytowe:
  SESSION_LOGGED_OUT, SESSION_REVOKED, SESSIONS_REVOKED, rozszerzone
  PASSWORD_CHANGED (forced/sessions_revoked/token_rotated — bez sekretów).
* `auth_sessions.last_used_at` (migracja nr 9, zapis z rozdzielczością
  ~5 min); w bazie nadal wyłącznie hash SHA-256 tokenu (potwierdzone
  testem i udokumentowane w PERMISSIONS.md, sekcja „Sesje i tokeny" —
  wraz ze świadomą decyzją o pozostaniu przy Bearer + sessionStorage
  i planem ewentualnej migracji na ciasteczka httpOnly z CSRF).
* UI: karta „Aktywne sesje" w Profilu klienta i w „Więcej"
  trenera/admina (zakończ wybraną / wyloguj z pozostałych urządzeń).
* Testy: 113 → 127 (wylogowanie Bearer i cookie, ponowne użycie
  unieważnionego tokenu, rotacja, wygaśnięcie, zakończenie sesji,
  izolacja cudzych sesji, limit prób, żądania równoległe, brak sekretów
  w audycie i bazie).

## 0.9.1 — 2026-08-18

Naprawa obsługi dat i stref czasowych w całej aplikacji.

* Błąd: daty kalendarzowe (`performed_on`, `logged_on`, `occurred_on`,
  `week_start`, `measured_at`...) liczone przez
  `new Date().toISOString().slice(0, 10)` (frontend) lub
  `datetime.now(UTC).date()` (backend) — rekord utworzony 18 sierpnia
  o 01:00 czasu polskiego trafiał do bazy z datą 17 sierpnia.
* Jeden wspólny moduł dat po obu stronach: `frontend/src/dates.ts`
  (`localToday()`, `mondayOfWeek()`, `localNowMinute()`, `parseApiDate()`,
  `plDate`/`plDateTime`/`WEEKDAYS` przeniesione z `api.ts`) i
  `backend/dzik_os/dates.py` (`local_today()`, `local_now()`,
  `local_now_minute()`, `tz_for_user()`); rozproszona logika usunięta
  (`todayIso`, `mondayOfCurrentWeek`, `_now_local` w konsultacjach).
* Przyjęty model dat: data kalendarzowa użytkownika = `YYYY-MM-DD`
  w strefie LOKALNEJ (frontend: strefa przeglądarki, backend: `DZIK_TZ`,
  domyślnie Europe/Warsaw); dokładny moment zdarzenia (`created_at`,
  `paid_at`, audyt) = pełny timestamp UTC (`now_iso()`), przeliczany do
  strefy dopiero przy prezentacji; termin konsultacji = naiwny lokalny
  `YYYY-MM-DDTHH:MM` porównywany wyłącznie z lokalnym „teraz".
  Szczegóły: docstring `dzik_os/dates.py` i sekcja „Konwencje dat"
  w `DATA_MODEL.md`.
* Naprawione porównania: flagi `checkin_overdue`/`payment_overdue`
  (lista klientów + dashboard trenera), status OVERDUE u klienta i na
  Dzisiaj, okno „nowego rekordu" (14 dni), zakresy monitoringu/adherencji/
  dziennika żywieniowego, `days_remaining` celu, ekran Dzisiaj
  (dzień tygodnia, harmonogram, przypomnienia), licznik nadchodzących
  konsultacji na dashboardzie (porównywał lokalny `starts_at` z czasem
  UTC) i filtr „nadchodzące" w konsultacjach trenera; `parseApiDate`
  parsuje `YYYY-MM-DD` jako lokalną północ (bez ryzyka przesunięcia dnia
  przy prezentacji).
* Architektura gotowa na strefę per użytkownik: `tz_for_user(user)`
  honoruje przyszłe pole `User.timezone` (dziś zawsze `DZIK_TZ`); bez UI
  i bez migracji schematu.
* Migracji danych historycznych NIE wykonano świadomie: po fakcie nie da
  się bezpiecznie odróżnić daty zapisanej błędnie (wpis z 00:00–02:00
  czasu polskiego) od poprawnej — przesuwanie rekordów hurtem
  uszkodziłoby dane wpisane w ciągu dnia (>95% przypadków).
* Testy: 113 → 128 (`tests/test_dates.py`: granica północy 00:30/01:00,
  czas letni/zimowy, obie zmiany DST, koniec miesiąca i roku, strefa
  z konfiguracji i per użytkownik, parsowanie dat z API). Logika
  `dates.ts` zweryfikowana skryptem Node z `TZ=Europe/Warsaw` (frontend
  nie ma infrastruktury testowej JS — ograniczenie opisane w raporcie).

## 0.9.0 — 2026-08-18

Runda 6b.7 specyfikacji: **terminarz konsultacji**.

* Tabela `consult_slots` (migracja nr 8): trener wystawia terminy
  (data+godzina, czas trwania), klient rezerwuje i odwołuje (do 12 h
  przed terminem; trener może odwołać w każdej chwili). Rezerwacje
  zawsze odwoływalne — bez kar i metryk za odwołania.
* Push przy rezerwacji/odwołaniu (obie strony), zdarzenia audytowe
  CONSULT_SLOT_CREATED/BOOKED/UNBOOKED/CANCELLED.
* UI: `/trener/konsultacje` (formularz + lista z odwołaniem, link w
  Więcej), `/konsultacje` u klienta (rezerwacje + wolne terminy, link w
  Więcej), karta „Najbliższa konsultacja" na Dzisiaj, licznik
  nadchodzących konsultacji na dashboardzie trenera.
* Izolacja: klient widzi wyłącznie terminy trenerów, którzy go aktywnie
  prowadzą; rezerwacja cudzego slotu = 404.
* Testy: 108 → 113.

## 0.8.0 — 2026-08-18

Runda 6b.6 specyfikacji: **strukturalny dziennik serii + wykresy siły**.

* `workout_entries.sets_json` (migracja nr 7): serie jako ciężar ×
  powtórzenia obok dotychczasowego tekstowego wyniku (kompatybilność
  wstecz — stare zapisy działają dalej).
* Logowanie treningu u klienta: szybkie wiersze serii (kg × powt.,
  „+ seria" kopiuje poprzednie wartości) + opcjonalna notatka tekstowa.
* Nowy endpoint `GET /clients/{id}/strength-series`: per ćwiczenie
  objętość dnia (suma kg×powt.) i najlepszy szacowany 1RM dnia (wzór
  Epleya — opisany w UI jako szacunek do obserwacji trendu, nie
  zalecenie obciążenia).
* Karta „Siła w czasie" (wybór ćwiczenia + dwa wykresy) na Postępach
  klienta i w Monitoringu trenera; rekordy osobiste liczą się teraz
  najpierw ze strukturalnych serii, potem z tekstu.
* Seed: treningi klienta A zapisane strukturalnie (progresja przysiadu
  95→105 kg widoczna na wykresie od pierwszego uruchomienia).
* Testy: 105 → 108.

## 0.7.0 — 2026-08-18

Runda 6b.5 specyfikacji: **powiadomienia push (PWA)**.

* Web Push z kluczami VAPID generowanymi automatycznie i trwałymi na
  wolumenie danych (zero sekretów w repo); tabela `push_subscriptions`
  (migracja nr 6), jawny opt-in w Profilu (klient) / Więcej (trener),
  wyłączane jednym przyciskiem; zdarzenia PUSH_SUBSCRIBED/UNSUBSCRIBED
  w audycie.
* Powiadomienia przy: nowej wiadomości (bez treści!), odpowiedzi trenera
  na raport, nowym raporcie od klienta (do trenera), nowej wersji planu.
* Pętla przypomnień (co 60 s, strefa DZIK_TZ): elementy harmonogramu z
  ustawioną porą + jednorazowe przypomnienia trenera o 08:00; dedup per
  dzień. Wymaga stale działającej maszyny — `min_machines_running = 1`
  w fly.toml (koszt: kilka USD/mies., opisany w komentarzu).
* Zasady: treść push nigdy nie zawiera danych zdrowotnych ani treści
  wiadomości; liczba wysłanych powiadomień nie jest metryką niczego.
* Testy: 100 → 105 (subskrypcje, triggery z podmienioną wysyłką,
  pętla przypomnień z dedupem).

## 0.6.0 — 2026-08-18

Runda 6a wg zatwierdzonej specyfikacji (docs/SPEC_NASTEPNE_RUNDY.md;
punkty 10–11 z listy propozycji świadomie poza zakresem).

* **Kopiowanie szablonu do klienta**: `POST /api/plans/{id}/copy-to/{client}`
  — bieżąca wersja szablonu staje się v1 nowego, NIEZALEŻNEGO planu
  klienta (późniejsza edycja szablonu nie zmienia planów klientów);
  w karcie klienta wybór „Z szablonu…" + „Kopiuj do klienta".
* **Porównywarka zdjęć „przed / po"**: zestawienie dwóch zdjęć sylwetki
  z wyborem dat (domyślnie najstarsze vs najnowsze) — u klienta na
  Postępach, u trenera w Monitoringu. Wyłącznie własna historia.
  Seed: dwa syntetyczne zdjęcia demo dla klienta A.
* **Timer przerw**: przy każdym ćwiczeniu z zapisaną przerwą przycisk ⏱
  odlicza czas (obsługa „120 s"/„2 min"/„90"), wibracja na koniec;
  czysto lokalny, niczego nie zapisuje.
* **Wywiad startowy** (`/ankieta`): strukturalna ankieta klienta (cel →
  cel główny, doświadczenie, dni, sprzęt, preferencje/alergie/kontuzje
  jako pola wrażliwe) zasilająca profil append-only z proweniencją
  CLIENT_DECLARED; baner-zaproszenie na Dzisiaj, dopóki profil pusty.
* Testy: 97 → 100 (kopiowanie szablonu: niezależność kopii, izolacja
  trenerów, blokada klienta).

## 0.5.2 — 2026-08-18

* **Powitanie na ekranie logowania**: pod logo ciepłe zaproszenie
  („Cześć, dobrze Cię widzieć! 💪 Zaloguj się — Twój plan, dieta i
  wiadomości od trenera czekają w jednym miejscu.").
* **PWA — świeża wersja przy każdym otwarciu**: nawigacje przełączone na
  network-first (cache tylko jako fallback offline) — użytkownik nie
  utknie już na starej wersji aplikacji do czasu kliknięcia banera;
  otwarcie/odświeżenie to naturalny moment aktualizacji, więc zasada
  „bez cichej podmiany kodu w trakcie sesji" pozostaje zachowana.
  Statyki nadal cache-first; /api nigdy nie jest cachowane. Cache
  podbity do v2.

## 0.5.1 — 2026-08-18

* **Duże logo na ekranie logowania**: pełna grafika marki (głowa dzika +
  wordmark „DZIK OS") w wysokiej rozdzielczości (900 px, spłaszczona
  paleta — 59 KB) zamiast małej ikonki z tekstem; napis „DZIK"
  przebarwiony na jasny wariant do ciemnego tła (czarny znikał na
  czarnym), „OS" pozostaje zielone. Znak nawigacji podbity do 512 px
  (ostrość na ekranach retina).
* **Symulowani klienci demo (C–E)** — panel trenera od razu pokazuje
  realną pracę: Marek Dziczek (raport czeka na ocenę + nieprzeczytana
  wiadomość), Anna Wilk (praca trenera wykonana: raport oceniony 4/5,
  odpowiedź w wątku, płatność opłacona, trend −2 kg), Piotr Zając
  (brak raportu, przeterminowana płatność, niepokojąca obserwacja
  kolana). Dashboard: 5 aktywnych klientów z pełnym przekrojem flag.

## 0.5.0 — 2026-08-18

* **Nowość — Rekordy osobiste i postęp od startu** (rywalizacja wyłącznie
  z własną historią, na życzenie użytkownika; zgodna z zasadą Human OS —
  żadnych porównań między ludźmi ani rankingów):
  `GET /api/clients/{id}/personal-records` liczy per ćwiczenie najlepszy
  własny ciężar (deterministyczny regex po tekstowych wynikach treningów,
  np. „3x8 @ 80kg"; wynik bez rozpoznawalnego ciężaru jest pomijany —
  zero zgadywania) z plakietką „nowy rekord!" gdy poprawiony w ostatnich
  14 dniach względem wcześniejszego własnego wyniku, oraz zmianę każdego
  pomiaru względem pierwszego zapisu („−4,2 kg od startu"). Karta
  „🏆 Rekordy osobiste" w Monitoringu klienta i w zakładce Monitoring
  trenera. Seed: 3 treningi klienta A z progresją przysiadu.
* Testy: 92 → 97.

## 0.4.1 — 2026-08-17

* **Logo**: zastąpiono wygenerowaną wcześniej prostą ikonę dzika docelową
  grafiką dostarczoną przez założyciela (szczegółowy maskotkowy portret
  głowy dzika + wordmark „DZIK OS"). Sama głowa (bez wordmarku, przycięta
  do kwadratu) jest teraz jedynym źródłem `Logo()` w UI oraz ikon PWA
  (`icon-192.png`/`icon-512.png` na ciemnym zaokrąglonym tle, favicon).

## 0.4.0 — 2026-08-17

Baza wiedzy trenera rozszerzona o know-how ćwiczeń i produktów, kompozytor
diety, ocena raportu i dashboard trenera; nowe logo z motywem dzika.

* **Nowość — logo z motywem dzika**: nowy znak (głowa dzika w profilu:
  ucho, ryj, kieł) zastępuje poprzedni abstrakcyjny zygzak — `Logo()`,
  ikony PWA (`icon.svg`/192/512) i favicon zaktualizowane.
* **Nowość — Baza ćwiczeń (know-how trenera)**: model `Exercise` z
  podziałem na partie mięśniowe (nogi/plecy/klatka/barki/ręce/brzuch/
  całe ciało/mobilność), techniką wykonania i efektem; CRUD trenera,
  broadcast do aktywnie prowadzonych klientów (ten sam wzorzec co Baza
  wiedzy) — nowa zakładka „Ćwiczenia" w panelu trenera i u klienta.
* **Nowość — Baza produktów z makro**: model `FoodProduct` (kcal/białko/
  tłuszcz/węglowodany na 100 g); zakładka „Produkty" z polem porcji (g),
  które na bieżąco przelicza kalorie i makro — po stronie trenera i
  klienta. Seed: ~40 typowych produktów w 8 kategoriach.
* **Nowość — Kompozytor diety** (propose-only): trener podaje cel kcal +
  makro i wybiera produkty z własnej bazy; `/api/coach/diet-suggestion`
  zwraca przejrzysty, deterministyczny podział celu na gramaturę wg
  dominującego makroskładnika każdego produktu (nigdy AI, nigdy
  automatyczna generacja diety) — wynik jest tylko sugestią do ręcznego
  wpisania w plan żywieniowy klienta, niczego nie zapisuje automatycznie.
* **Nowość — Ocena raportu przez trenera**: opcjonalna ocena 1-5 obok
  odpowiedzi na raport tygodniowy (`WeeklyCheckin.rating`) — dotyczy
  kompletności/jakości samego raportu, nie jest oceną osoby (zasada
  Human OS: system nie rankinguje ludzi); widoczna dla obu stron.
* **Nowość — Dashboard trenera**: `GET /api/coach/dashboard` agreguje
  metadane operacyjne (aktywni klienci, raporty do oceny, zaległe
  raporty/płatności, nieprzeczytane wiadomości, obserwacje) na górze
  listy klientów; nowa flaga i filtr „Raport do oceny".
* Migracja schematu nr 5 (`weekly_checkins.rating`, tabele `exercises`,
  `food_products`).
* Testy: 74 → 92 (ćwiczenia, produkty, kompozytor diety, ocena raportu,
  dashboard).

## 0.3.0 — 2026-08-17

Czytelność raportów, baza wiedzy, propozycje AI, aktualizacje PWA i
odświeżony design — na podstawie bezpośredniej informacji zwrotnej.

* **Raport tygodniowy w sekcjach**: formularz klienta i widok trenera
  podzielone na „Ciało", „Samopoczucie", „Ból/komentarz/pytania" —
  ocena raportu bez przewijania jednej długiej listy pól.
* **Nowość — podsumowanie AI raportu** (propose-only): przycisk w
  panelu trenera generuje streszczenie + szkic odpowiedzi do edycji;
  domyślnie `NullAIProvider` pokazuje jawny komunikat „wymaga
  konfiguracji" zamiast udawać działanie. Żadna odpowiedź nie trafia do
  klienta bez zatwierdzenia przez trenera.
* **Nowość — Baza wiedzy**: trener publikuje materiały (artykuł, link,
  plik) widoczne dla wszystkich aktywnie prowadzonych klientów; pełny
  CRUD (dodaj/edytuj/archiwizuj/przywróć), kategorie, przypinanie.
  Osobna oś uprawnień od danych zdrowotnych (to treść trenera, nie
  dane klienta) — patrz PERMISSIONS.md.
* **Nowość — aktualizacje PWA**: baner „Dostępna nowa wersja" zamiast
  cichej podmiany kodu aplikacji pod użytkownikiem w trakcie sesji;
  użytkownik sam decyduje, kiedy odświeżyć.
* **Design**: typografia Unbounded (nagłówki) + Inter (treść, cyfry
  tabelaryczne); warstwowe tło zamiast płaskich kart (surface staircase);
  delikatna poświata na kartach-bohaterach (trening dnia, cel); wykresy
  ze zanikającym wypełnieniem pod linią; mikrointerakcje (naciśnięcie
  przycisku, wejście karty) z pełnym poszanowaniem
  `prefers-reduced-motion`; wypełnione plakietki akcentu dla wyróżnień.
* Domyślny zakres trendów w Monitoringu skrócony z 90 do 30 dni —
  czytelniejszy, bardziej typowy okres.
* Migracja schematu nr 4 (`knowledge_items`) — bezpieczna dla istniejącej
  bazy.
* Testy: 65 → 74 backendu (275 Core bez zmian).

## 0.2.0 — 2026-08-17

Monitoring w czasie — na podstawie analizy rynku (`ANALIZA_RYNKU.md`) i
wniosku, że regularny monitoring pozwala wcześniej wychwycić niekorzystne
reakcje, a nie tylko śledzić postępy.

* **Nowość — Monitoring i postępy** (klient, `/postepy`) i zakładka
  **Monitoring** (trener): cel z odliczaniem dni, trendy pomiarów i
  samopoczucia (sen/energia/stres/głód/regeneracja z raportów), dziennik
  kaloryczny na tle celu z diety, realizacja harmonogramu per kategoria
  (pasek % zamiast surowych liczb), dziennik obserwacji.
* **Nowość — adherencja harmonogramu**: przycisk „Wykonane" na ekranie
  Dzisiaj dla każdego elementu harmonogramu (nie tylko treningu);
  idempotentne odhaczenie per dzień (`schedule_completions`).
* **Nowość — dziennik obserwacji** (`observations`): klient zgłasza
  samopoczucie lub reakcję (opcjonalnie powiązaną z suplementem/posiłkiem
  z harmonogramu), oznaczając wagę Informacja/Niepokojące. System **nigdy
  nie interpretuje ani nie diagnozuje** — wyłącznie zapisuje dosłownie i
  flaguje NIEPOKOJACE w panelu trenera (nowy filtr i badge na liście
  klientów) oraz — jeśli skonfigurowany dostawca — e-mailem.
* **Nowość — dziennik kaloryczny** (`daily_nutrition_logs`): szybki wpis
  kcal/wody na tle celu z aktywnej diety.
* **Nowość — eksport do Excela** (`/api/me/export.xlsx`, przycisk w
  Profilu): ten sam komplet danych co eksport JSON, jeden arkusz na
  tabelę.
* **Nowość — wiadomości głosowe**: nagrywanie w przeglądarce
  (MediaRecorder) i wysyłka jako załącznik; poprawiony też odbiór
  załączników dowolnego typu w wątku (wcześniej wszystko renderowało się
  jak obraz — PDF/wideo/audio wyświetlały się poprawnie po typie z
  serwera, nie po nazwie pliku).
* **Nowość — adapter powiadomień e-mail** (`notifications_provider.py`,
  wzorzec jak `payments_provider.py`): domyślnie `NullNotificationProvider`
  (nic nie wysyła, brak PII w logach); gotowy interfejs do podłączenia
  Resend/SendGrid/Mailgun/SMTP decyzją operatora.
* Migracja schematu nr 3 (trzy nowe tabele monitoringu) — bezpieczna dla
  istniejącej bazy (w tym produkcyjnej na Fly), testowana regresyjnie.
* Eksport JSON i procedura usunięcia danych objęły nowe tabele.
* Testy: 55 → 65 (adherencja, obserwacje z flagą, dziennik kaloryczny,
  eksport Excel, upload audio, migracja v1→v3).

## 0.1.1 — 2026-08-17

Runda poprawek po pełnym przekliku aplikacji + przygotowanie PaaS.

* **Naprawa**: eksport danych z poziomu Profilu pobiera plik JSON
  (wcześniej przycisk kończył się błędem po stronie przeglądarki).
* **Naprawa**: załącznik wysłany przez trenera w wiadomości jest widoczny
  dla klienta (dostęp dla stron wątku; osoby trzecie nadal 404) — test.
* **Bezpieczeństwo (R-06 zamknięte)**: konto założone przez trenera musi
  zmienić hasło startowe przy pierwszym logowaniu — blokada egzekwowana
  serwerowo (PASSWORD_CHANGE_REQUIRED), nowy ekran zmiany hasła, zmiana
  unieważnia pozostałe sesje (zdarzenie PASSWORD_CHANGED w audycie).
* **Zgody (R-05 zamknięte)**: klient przy pierwszym logowaniu jawnie
  potwierdza zgodę zarejestrowaną przy onboardingu (ekran „Twoje dane,
  Twoja zgoda"; CONSENT_CONFIRMED w łańcuchu audytu) albo odmawia;
  zgody nadawane samodzielnie są potwierdzone od razu.
* Migracja schematu nr 2 (`users.must_change_password`,
  `consents.confirmed_at`) — mechanizm migracji obsługuje istniejące bazy
  (ALTER) i świeże (stempel), z testem regresyjnym.
* Konfiguracja PaaS: `fly.toml` + instrukcja wdrożenia na Fly.io
  (darmowa subdomena z HTTPS; własna domena do dodania później).
* Testy: 50 → 55 (wymuszona zmiana hasła, potwierdzanie zgód, załączniki
  wątków, migracja v1→v2).

## 0.1.0 (MVP) — 2026-08-17

Pierwsze wydanie „Dzik OS — Panel Podopiecznego".

* Import fundamentów Human OS (`human-os@68fe1e4`) do `human-os2`
  (ADR-DZIK-003); regresja Core: 275 testów zielonych, zero zmian w Core.
* Backend FastAPI: uwierzytelnianie sesyjne (bcrypt, rate limiting),
  role COACH/CLIENT/ADMIN, relacje trener–klient, profil z wersjonowanymi
  polami i proweniencją, cele, plany treningowe i żywieniowe z
  niemutowalnymi wersjami (powód zmiany obowiązkowy), harmonogram z
  autorem zalecenia, raporty tygodniowe z rewizjami i odpowiedzią trenera,
  pomiary, wiadomości z załącznikami, dokumenty i zdjęcia (walidowany
  upload), płatności z adapterem operatora, zgody (decyzja w
  hos_engine.ConsentRegistry), eksport JSON, anonimizacja konta,
  audyt hash-chained (SQLiteEventStore) z pokwitowaniami.
* Frontend: mobile-first PWA po polsku (React+TS+Vite), aplikacja klienta
  (Dzisiaj/Plan/Dieta/Raport/Pomiary/Wiadomości/Płatności/Profil) i panel
  trenera (lista z flagami operacyjnymi, karta klienta z 8 zakładkami,
  szablony), panel admina (konta + weryfikacja łańcucha audytu).
* Dane demo (syntetyczne): trener, 2 klientów, admin, plany, dieta,
  raport, pomiary, wiadomości, dokument, płatności.
* Testy: 50 backend (izolacja, wersjonowanie, zgody, prywatność, uploady,
  płatności, audyt, E2E ścieżek) + 3 E2E przeglądarkowe (Playwright).
* Infrastruktura: Dockerfile, Docker Compose (PostgreSQL), .env.example,
  CI GitHub Actions (lint, testy Core i aplikacji, build frontendu).

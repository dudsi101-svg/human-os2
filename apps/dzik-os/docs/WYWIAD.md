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

## 8. Wywiad „Zapotrzebowanie kaloryczne” (0.62.0, wyrównany do specyfikacji 1.0 w 0.77.0)

Trzeci typ `zapotrzebowanie` w tym samym mechanizmie (szkic, wersje,
przegląd, wspólnie). Za flagą `DZIK_CALORIE_INTERVIEW_ENABLED`
(`routers/wywiady.typy_aktywne`). Źródło: specyfikacja właściciela
`docs/calorie-interview/wywiad_zapotrzebowanie_kaloryczne.md` (1.0
z 13.09.2026) i referencyjna implementacja wzorów `calorie_calc.py`;
rozbieżności między nimi wypisane w `docs/calorie-interview/PROGRESS.md`.

### 8.1 Pięć ekranów (`definicje.py`, `WERSJA_ZAPOTRZEBOWANIE = 2`)

23 pytania `zk_*` w pięciu sekcjach. Wersja definicji jest **osobna od
wspólnej `WERSJA`** wywiadu wstępnego i głębokiego — wyrównanie zmienia
tylko ten wywiad.

| Ekran | Pytania |
|---|---|
| Dane podstawowe | płeć, wiek (16–90), wzrost (130–230), masa (35–250), **% tkanki tłuszczowej** (3–60, opcjonalny) |
| Aktywność poza treningiem | cztery opisy (siedząca / lekka / umiarkowana / wysoka) albo **liczba kroków**, która je nadpisuje |
| Trening | siłowe/tydz. (0–7) + czas, cardio/tydz. (0–7) + czas i intensywność, staż (opcjonalny) |
| Cel | cel (redukcja / utrzymanie / masa / **rekompozycja**), tempo, masa docelowa, preferencja białka |
| Zdrowie i kontekst | ciąża/karmienie, choroby metaboliczne, zaburzenia odżywiania, leki, brak miesiączki (tylko kobiety), wolne pole |

Warunkowe: czas treningu po liczbie sesji, intensywność cardio po liczbie
sesji cardio, tempo przy redukcji i budowie masy, pytanie o miesiączkę przy
płci „kobieta”. Wszystkie pytania ekranu 5 są **dobrowolne**, każde ma
odpowiedź „wolę nie odpowiadać” (przy zaburzeniach odżywiania: „wolę
omówić z trenerem”) i każde jest za zgodą `DOMAIN_HEALTH` — szczegóły
dostępu w `PERMISSIONS.md`, kategorie danych w `DATA_PROCESSING_MAP.md`
i `RODO_DPIA.md` §3a.

**Szkic sprzed zmiany pytań:** odczyt (`serwis.odpowiedzi_szkicu` →
`definicje.odfiltruj_nieaktualne`) pomija odpowiedzi, których dzisiejsza
definicja nie przyjmie — pytanie zniknęło (`zk_praca`) albo wartość jest
spoza listy („Redukcja masy ciała”, kroki jako przedział). Przesłane
wersje zostają nietknięte.

### 8.2 Wzory (`wywiad/zapotrzebowanie.py`, bez AI)

* **PPM** — Mifflin-St Jeor zawsze: `10·m + 6,25·h − 5·wiek + 5 (M) / − 161 (K)`.
  Przy podanym % tłuszczu dodatkowo Katch-McArdle: `370 + 21,6 · masa
  beztłuszczowa`. Gdy oba są dostępne i różnią się o **więcej niż 10 %**,
  używany jest Katch-McArdle (nietypowy skład ciała to przypadek, w którym
  Mifflin myli się najbardziej); oba pokazywane trenerowi z różnicą.
* **CPM addytywnie**, nie jednym mnożnikiem PAL:
  `CPM = (PPM · mnożnik_NEAT + kcal_treningu_na_dzień) · 1,10`.
  NEAT: 1,20 / 1,35 / 1,50 / 1,70, a z kroków `1,20 + 0,04·(kroki/1000 − 4)`
  ograniczone do [1,15; 1,85]. Trening: `MET · masa · 0,0175` kcal/min
  (siłowy 5,0; cardio 4,0 / 7,0 / 10,0), sumowane i dzielone przez 7.
  Ostatnie 1,10 to **TEF** (termiczny efekt pożywienia, 10 %).
  Wynik pokazywany jako **zakres ±7 %** — NEAT to największe źródło błędu.
* **Cel kaloryczny** = CPM + korekta: redukcja −10 / −20 / −25 %,
  utrzymanie 0, masa +5 / +10 / +15 %, rekompozycja −5 %. Podłoga:
  `max(1,1 × PPM; 1200 kcal K / 1500 kcal M)` — naruszenie podnosi cel
  do granicy i zapala `DEFICYT_OGRANICZONY`.
* **Makro startowe** w gramach i procentach (białko 1,6–2,2 g/kg zależnie
  od celu i preferencji; przy redukcji z % tłuszczu > 30 liczone z masy
  docelowej albo ~LBM/0,75; tłuszcz 0,9–1,0 g/kg, nigdy poniżej 20 %
  kalorii; reszta to węglowodany).
* **Oczekiwane tempo**: `(CPM − cel) · 7 / 7700` kg/tydzień, pokazywane
  jako zakres zaokrąglony do 0,1 kg; przy budowie masy dodatkowo
  realistyczny przyrost mięśni ze stażu (< 1 roku 0,5–1 %/mies. masy
  ciała, 1–3 lata 0,25–0,5 %, > 3 lata < 0,25 %); przy podanej masie
  docelowej orientacyjny czas z zastrzeżeniem „w praktyce dłużej”.

Każdy krok ma wiersz podstawienia — trener i klient widzą „skąd ta liczba”.
Przykłady kontrolne ze specyfikacji §7 są testami
(`tests/test_zapotrzebowanie_silnik.py`): M 30 l./180/80 → PPM 1780;
K 25 l./165/60 → 1345; 80 kg przy 20 % tłuszczu → Katch 1752; 3 × 60 min
siłowy → 180 kcal/dzień i CPM 2548; szybka redukcja kobiety → cel 1480
z flagą `DEFICYT_OGRANICZONY`.

### 8.3 Flagi (specyfikacja §6.4)

`MALOLETNI` (< 18 — wynik liczony, ale klient go nie widzi),
`CIAZA_KARMIENIE` i `BRAK_MIESIACZKI` (deficyt wyłączony,
`DEFICYT_WYLACZONY`), `CHOROBA_METABOLICZNA` i `LEKI` (ostrzeżenie
o konsultacji lekarskiej dla trenera), `ZABURZENIA_ODZYWIANIA` (klient nie
widzi żadnych liczb), `DEFICYT_OGRANICZONY`, `BMI_SKRAJNE` (< 17 albo > 40).
Każda flaga ma opis dla trenera, a część także wersję dla klienta —
ostrzeżenia kierowane do trenera nie wychodzą do klienta.

**Zakres flagowania zaburzeń odżywiania jest szerszy niż w specyfikacji**
(decyzja właściciela z 14.09, potwierdzona przy wyrównaniu): liczby ukrywa
także „Nie wiem” i „Wolę omówić z trenerem”, nie tylko „Tak”. Powód jest
niesymetryczny: zawężenie do samego „Tak” odsłoniłoby liczby części
klientów już obsługiwanych na produkcji, a koszt pomyłki w jedną stronę
(klient z zaburzeniami widzi kalorie) jest nieporównanie wyższy niż
w drugą (klient bez zaburzeń czeka jedną rozmowę).

### 8.4 Zapis i dwa pokolenia wyników

`calorie_estimates` (migracja 33, rozszerzona migracją 42) — jedna wersja
na przesłanie (`submission_id` UNIQUE), wynik **zamrożony w chwili
liczenia** (`formulas_version`, specyfikacja §6.3): zmiana wzorów nie
zmienia historii. Brak danych (np. masa poza zakresem) = brak wyniku,
przesłanie i tak ważne.

* `formulas_version = "0.62.0-pal"` — wyniki sprzed wyrównania (PPM × PAL).
  **Nie są przeliczane** (decyzja właściciela z 14.09): nowy wzór wymaga
  rodzaju, czasu i intensywności treningu oraz % tłuszczu, których stare
  przesłania nie mają. Zostają jako historia; klient widzi zachętę do
  ponownego wypełnienia — bez blokady i bez ponaglania.
* `formulas_version = "2026-09-13.1"` — bilans 1.0. Dla zgodności wstecz
  `ppm` = użyte PPM, `cpm` = CPM, `kcal` = cel kaloryczny, `pal` = CPM/PPM
  (efektywny współczynnik aktywności — silnik 1.0 nie używa jednego
  mnożnika PAL; mnożnik NEAT jest w `neat_multiplier`).

Odpowiedzi zdrowotne **nie są kopiowane** do `inputs_json` — zostają
w wywiadzie, gdzie pilnuje ich zgoda domeny; skutek widać w `flags_json`.

### 8.5 API i interfejs

`GET /api/clients/{id}/zapotrzebowanie` (klient: swoje; trener: relacja
i zgody, dodatkowo `history` z masą i CPM w czasie), `PUT …/nadpisanie`
`{kcal|null, reason}` (trener; 800–8000; powód obowiązkowy, widoczny dla
klienta; audyt `CALORIE_ESTIMATE_OVERRIDDEN`), `POST …/odblokuj` (trener;
zdejmuje ukrycie z powodu zaburzeń odżywiania, **nie** z powodu
niepełnoletności). Obcy trener: 404. Flaga wyłączona: 404 na typ i trasy.

`pages/wywiad/Zapotrzebowanie.tsx` (jedna karta, tryb klient/trener):
klient — cztery kafelki ze specyfikacji §6.1 (spoczynek, cały dzień
z zakresem, cel, makro) plus tempo i zdanie „to punkt startowy”; trener —
to samo plus rozbicie CPM na składniki z podstawieniem, oba PPM z różnicą,
BMI, flagi, historia jako tabela, nadpisanie i odsłonięcie.
`PrzypiszDiete` → „Użyj w przypisaniu diety” wstawia kcal, masę i makro
jako preset „ręcznie” w gramach; nie przypisuje diety.

**Świadomie nie zrobiono:** data urodzenia (wiek wystarcza do wzoru, a to
mniej danych — decyzja właściciela); przeliczanie starych wyników;
automatyczne przeliczenie po nowym pomiarze masy (wynik zmienia się tylko
przez nową wersję wywiadu); zasilanie profilu (`fact_key=None`, żeby masa
z wywiadu nie dublowała zakładki Pomiary); P1 ze specyfikacji
(przypomnienie po zmianie masy > 3 kg lub po 8 tygodniach, wykres masy
i CPM) i P2 (kroki z zegarka jako integracja, adaptacja kalorii z ważeń).


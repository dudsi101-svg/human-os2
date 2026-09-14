# Plan sesji: rozgrzewka, rozciąganie i cardio z suwakami celów (0.73.0, migracja 39)

**Gałąź:** `agent/cardio-i-rozgrzewka` (od `main` = `bdb261c`, 0.71.0 — dni treningowe
scalone). **Rola:** podległa sesja pisząca wyznaczona przez integratora 14.09.2026 —
zlecenie 5 właściciela (czwarta tura 14.09: „rozgrzewka na 3 poziomach w 3 wariantach,
rozciąganie, ćwiczenia fitness na rowerku/bieżni/bieżni skos/steperze/wioślarzu z trzema
suwakami celów sumującymi się do całości, sugerującymi tętno, obciążenie, tempo i czas”),
pakiet `docs/zlecenia/` (`model-suwakow-cardio.md` + `PROMPT_writer_cardio-i-rozgrzewka.md`,
złożone w `PAKIET_ZLECEN_2026-09-14.md` §9).

**Uwaga o protokole jednego piszącego:** w chwili startu otwarty jest jeden PR `[WRITER]`
— #67 (`agent/landing-czerwony`, 0.72.0, czeka na decyzję właściciela). Integrator wyznaczył
tę sesję jawnie z wiedzą o nim (wyjątek integratora, jak przy 0.71.0). Sesja nie dotyka
plików tamtej gałęzi (`Landing.tsx`, `public_site.py`, style strony publicznej).

**Rezerwacje (KOORDYNACJA §0, sprawdzone na żywo 14.09 ok. 12:00 w `db.py`,
`CHANGELOG.md`, `STAN_PRZEKAZANIA.md` §2, `docs/zlecenia/README.md` i liście PR-ów):**

* **wersja 0.73.0** — `CHANGELOG.md` ma na górze 0.71.0; **0.72.0 = PR #67** (nie scalony).
  Sekcja 0.73.0 idzie NA GÓRĘ; jeśli #67 wejdzie później, integrator go przenumeruje
  (kontrola `changelog` wymaga wersji rosnących w kolejności scalania). Numer podbijam w
  `backend/pyproject.toml`, `backend/dzik_os/__init__.py`, `frontend/package.json`,
  `README.md`, `RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md` (kontrole `przekazanie`
  i `wersje dokumentów`). Pakiet mówił „kolejna wolna” — numer nadał integrator.
* **migracja 39** (addytywna): tabela `exercise_blocks` + pięć kolumn NULL w
  `workout_entries` (`duration_min`, `avg_hr`, `rpe`, `distance_km`, `machine`). Ostatni
  wpis w `db.py` = **38** (dni treningowe), 37 = powitanie — ciąg bez luk. Pakiet mówił
  „38+” — skorygowane.
* **`export_version`** w `routers/privacy.py` jest dziś **„2.0”** — podbijam na **„2.1”**
  (eksport `workout_entries` zyskuje pięć pól; nowej tabeli klienta nie dokładam — bloki są
  broadcastem trenera jak `Exercise`) i poprawiam siedem testów (`grep export_version`:
  `test_dni_treningowe.py:411`, `test_habits.py:134`, `test_onboarding.py:948`,
  `test_postepy_api.py:294`, `test_powitanie.py:47`, `test_zapotrzebowanie_api.py:223`).
* **Porty E2E:** 8110/8111 (integrator), katalog `/tmp/dzik-e2e-8110`; przy zajętych 8112/8113.

**Pliki współdzielone (zmieniam jawnie, tylko własne sekcje):** `models.py` (nowa klasa na
końcu + kolumny `WorkoutEntry`), `db.py` (wpis 39), `main.py` (dwa routery), `schemas.py`
(`ExerciseIn`, `WorkoutEntryIn`), `publikacja/elementy.py` (allow-list pól), `wiedza/slad.py`
(jednostki + `slady_cardio`), `wiedza/reguly.py` (`H_CARDIO`), `routers/plans.py` (ślad przy
wersji, zapis pól cardio w dzienniku, odczyt), `publikacja/serwis.py` (ślad przy publikacji),
`routers/privacy.py` (`export_version`), `exercise_catalog.py` (nowe wpisy), `seed.py` (dzień
C klienta A), `tests/access_matrix.py`, `types.ts`, `Plan.tsx`, `Today.tsx`, `PlanEditor.tsx`,
`SzkicPlanu.tsx`, `Templates.tsx`, `Progress.tsx` (metryka tętna spoczynkowego), `package.json`
(`test:helpers`), `CHANGELOG.md`, `RELEASE_STATUS.md`, `PERMISSIONS.md`, `BAZA_CWICZEN.md`,
`KONFIGURATOR.md`, `WIEDZA.md`, `RISK_REGISTER.md`, `INSTRUKCJA_TRENERA.md`,
`INSTRUKCJA_KLIENTA.md`, `IMPORT_BAZ.md`, `STAN_PRZEKAZANIA.md` §1/§2, `docs/zlecenia/README.md`.

**Pliki nowe:** `backend/dzik_os/cardio/{__init__,model,urzadzenia,stale,bloki_wbudowane}.py`,
`backend/dzik_os/routers/{cardio,exercise_blocks}.py`, `backend/tests/{test_cardio_model,
test_cardio_api,test_exercise_blocks}.py`, `frontend/src/{suwaki.ts,pozycje.tsx}`,
`frontend/src/pages/coach/{CardioPanel,BlokiTab}.tsx`, `frontend/scripts/test-suwaki.mjs`
(+ `tsconfig.suwaki.json`), `frontend/e2e/{cardio,rozgrzewka}.spec.ts`,
`docs/cardio/{00_rozpoznanie,PROGRESS}.md`, ten plan.

## Cel

Trener układa w planie trzy nowe rodzaje pozycji — blok rozgrzewki (3 poziomy × 3 warianty),
blok rozciągania (3 warianty) i cardio na urządzeniu z trzema sprzężonymi suwakami celów
(Redukcja / Wydolność / Regeneracja), z których deterministyczny silnik (Seiler 3 strefy +
Karvonen + Tanaka + Fatmax + interwały pod VO2max) proponuje zakres tętna, RPE, test mowy,
czas, strukturę i „zacznij od…” na urządzeniu; klient widzi to na „Dzisiaj” i w Planie,
wybiera urządzenie z listy dozwolonych i zapisuje wykonanie (czas, RPE, tętno, dystans).
Propose-only: propozycja powstaje wyłącznie u trenera, przechodzi przez bramkę zdrowotną
i trafia do klienta dopiero w opublikowanej wersji planu. Zero AI, zero rankingów, zero
automatycznej progresji.

## Test INTENDED_PURPOSE §2/§3 (etap 0 — wykonany przed kodem)

* **Co jest daną zdrowotną:** odpowiedzi bramki zdrowotnej (objawy alarmowe, choroba, ciąża,
  uraz, rehabilitacja, **leki wpływające na tętno**), wiek, tętno spoczynkowe, tętno średnie
  z treningu — domena `dane_zdrowotne` (`DOMAIN_HEALTH`). Blok zdrowotny jest używany **tylko
  do kwalifikacji propozycji u trenera** i nie jest zapisywany w planie, śladzie ani audycie
  (jak konfigurator K1). Wiek i tętno spoczynkowe są czytane z istniejących źródeł (ostatni
  szacunek kaloryczny, pomiar `resting_hr`) **tylko gdy trener ma dostęp do domeny
  zdrowotnej**; bez dostępu silnik liczy w trybie „tylko RPE + test mowy” — nic nie wycieka
  i nic nie udaje, że wie.
* **Co nie jest werdyktem medycznym:** zakres tętna to *struktura sesji dla trenera*
  wyliczona z wzoru populacyjnego (Tanaka ±10 ud./min) i przedstawiona **zawsze jako
  zakres**, obok równoprawnego RPE i testu mowy; komunikaty mówią „propozycja, trener
  decyduje”, „to nie porada medyczna”; przy `urgent_stop` silnik nie liczy nic i kieruje do
  pomocy doraźnej (istniejąca treść `H_HEALTH_GATE`); przy `needs_review` propozycja jest
  widoczna wyłącznie trenerowi z ostrzeżeniem; przy lekach wpływających na tętno tętno w
  ud./min nie jest podawane (tylko %/RPE). Nic nie diagnozuje, nie monitoruje choroby, nie
  proponuje leków. Zgodność z §2 bez wątpliwości — **bez pytania do foundera**; pozycje [C]
  modelu idą do trenera (lista w `docs/cardio/PROGRESS.md`).
* **Zgoda:** odczyt wieku/tętna spoczynkowego i zapis `avg_hr` w dzienniku przechodzą przez
  istniejące bramki (`resolve_client_access` z `DOMAIN_HEALTH` przy odczycie prefillów przez
  trenera; dziennik klienta w `DOMAIN_TRAINING` jak dotąd — `avg_hr` to wpis własny klienta
  o sobie). Bez nowej bramki zgód (prompt §8 pyt. 7, domyślne).

## Decyzje projektowe (prompt §3 + wykonawcze)

1. **Rodzaje pozycji:** `kind ∈ {strength (brak klucza), warmup_block, stretch_block, cardio}`
   jako opcjonalny klucz pozycji `exercises[]` w tym samym JSON — stare plany bez zmian.
2. **Bloki = byty katalogowe trenera** (`ExerciseBlock`: `kind` WARMUP/STRETCH, `level`,
   `variant` G/D/C, `name`, `duration_min`, `items_json`, `source`, `status` ACTIVE/ARCHIVED).
   Wbudowany zestaw 9 rozgrzewek + 3 rozciągania (`bloki_wbudowane.py`, treść z §5 promptu,
   `source="wbudowany — do przeglądu trenera"`) ładowany idempotentnie przez
   `POST /api/coach/exercise-blocks/load-builtin`. Pozycja `warmup_block`/`stretch_block`
   w planie niesie `block_id` (miękkie) **i migawkę `block`** (nazwa, poziom, wariant, czas,
   lista pozycji z dawką) — archiwizacja bloku nie psuje planów.
3. **Cardio = pozycja `kind: "cardio"`** z `cardio: {machines[], goal_mix{redukcja,
   wydolnosc, regeneracja}, level, prescription{...}, trace{...}, model_version:
   "cardio_model_v1", overridden_by_coach[]}`. Trener wskazuje dozwolone urządzenia, klient
   wybiera w dniu treningu (zapis w `WorkoutEntry.machine`).
4. **Silnik = czyste funkcje** `cardio/model.py` (mieszanie, kotwice, struktura wg poziomu,
   HRmax/HRR, MET) + `cardio/urzadzenia.py` (tabela §5 modelu) + `cardio/stale.py` (kotwice,
   MET-y, źródło i pewność [A]/[B]/[C] w komentarzach). Suma wag ≠ 1 (tolerancja 0,01) → 422,
   bez cichej normalizacji. Wynik zawsze zakresem ±5 % HRmax.
5. **Bramka zdrowotna przed propozycją:** `konfigurator.zdrowie.ocen_zdrowie` 1:1 + pole
   `hr_medication` (leki wpływające na tętno → `hr_mode = "rpe_only"`, `hr_bpm_range = null`).
   `urgent_stop` → brak propozycji; `needs_input` → pytania; `needs_review` → propozycja
   z ostrzeżeniem widoczna tylko trenerowi. Blok zdrowotny nie jest zapisywany.
6. **Ślad `H_CARDIO`** zapisywany przy zapisie wersji planu (`POST /api/plans`,
   `POST /api/plans/{id}/versions`) i przy publikacji szkicu — w tej samej transakcji co
   wersja; `target_type="cardio_prescription"`, `target_id="d{di}:e{ei}"`; fakty: wagi,
   poziom, źródło HRmax, kotwice, struktura, wersja modelu, zastrzeżenia. Nowe jednostki
   w `slad.JEDNOSTKI`: `bpm`, `percent_hrmax`, `percent_hrr`, `rpe`, `kcal`, `percent`.
7. **Klient:** wspólny renderer `pozycje.tsx` (Dzisiaj + Plan): rozgrzewka/rozciąganie jako
   rozwijana lista pozycji z dawką (odhaczana jako całość — bez serii); cardio: trzy paski
   wag, wybór urządzenia, „zacznij od…”, zakres tętna **i** RPE + test mowy, czas, struktura
   interwałów z timerem (przeniesiony `RestTimer`), jedno zdanie o bilansie energii,
   „Dlaczego?”. Dziennik w Planie: dla cardio pola czas/RPE/tętno/dystans/urządzenie zamiast
   serii; historia pokazuje wpisy cardio osobno (bez kg).
8. **Trener:** `PlanEditor.tsx` — w dniu „+ Rozgrzewka” / „+ Rozciąganie” (wybór bloku),
   „+ Cardio” → `CardioPanel.tsx` (React.lazy): trzy `input[type=range]` sprzężone helperem
   `suwaki.ts` (`przesun(wagi, indeks, nowa, zablokowane)` — zabiera pozostałym proporcjonalnie,
   kłódka, zaokrąglenie do 5 %, suma zawsze 100), poziom, urządzenia, bramka zdrowotna,
   „Policz propozycję” → tabela + ostrzeżenia + edytowalne liczby + „Wstaw do dnia”.
   Zakładka **„Bloki”** w Szablonach: lista, „Dodaj wbudowane”, archiwizacja, prosta edycja.
9. **Rekordy pomijają cardio** (wpis bez serii nie tworzy `ExerciseRecord`); agregaty tygodnia
   liczą sesję jak dotąd.
10. **Zero AI, zero rankingów, zero progresji tydzień do tygodnia.** Bez flagi (jak 0.63.0,
    0.71.0 — nowe funkcje mają być widoczne); treści oznaczone „do przeglądu trenera”.

## Przyjęte domyślne odpowiedzi na pytania §8 promptu (właściciel nie odpowiedział)

| # | Pytanie | Przyjęte |
|---|---|---|
| 1 | Trzeci cel | **Regeneracja (baza tlenowa)** |
| 2 | Nazwa celu 1 w UI | **„Redukcja (wydatek energii)”** + zdanie o bilansie energii |
| 3 | Warianty rozgrzewki | **góra / dół / całe ciało** (G/D/C), 3 poziomy |
| 4 | Rozciąganie | **3 warianty G/D/C, bez poziomów, po treningu (5–8 min)** |
| 5 | Urządzenie | **trener wskazuje listę dozwolonych, klient wybiera w dniu treningu** |
| 6 | Przegląd treści | **tak** — bloki, nowe wpisy katalogu i tabela urządzeń oznaczone „do przeglądu trenera” (`source`/`review_reason`), lista w `docs/cardio/PROGRESS.md` |
| 7 | Tętno spoczynkowe | **tak, opcjonalne, bez migracji** — pomiar `kind="resting_hr"` (ud./min) w Pomiarach klienta; silnik używa Karvonena, gdy jest |

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą; linie z promptu zweryfikowane 14.09 na `bdb261c`) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 | `models.py` 246–298 (`TrainingPlanVersion`, `WorkoutEntry`), 444–466 (metryki), 780–845 (`Exercise`); `schemas.py` 68–140; `elementy.py` 44–46 (allow-list); `slad.py` 32–45 (jednostki), 205–215 (`slad_wersji_trenera`); `reguly.py` 49–63; `zdrowie.py` (cały); `konfigurator.py` (podglad/zapisz); `plans.py` 146–200/330–460; `serwis.py` 290–305; `privacy.py` 76–90/371; `seed.py` 220–300; `exercise_catalog.py` (14 CARDIO, 14 MOBILNOSC); `today.py` 45–95; `Plan.tsx`, `Today.tsx` 175–212, `PlanEditor.tsx` 200–520, `SzkicPlanu.tsx` 400–440, `Templates.tsx` 26–60, `PanelPostepow.tsx`, `Dlaczego.tsx`, `dni-treningowe.spec.ts`, `playwright.config.ts` | ten plan + `docs/cardio/00_rozpoznanie.md` | — | tysiące |
| 1 silnik | `model-suwakow-cardio.md` §3–§6 | `cardio/model.py`, `urzadzenia.py`, `stale.py`; `tests/test_cardio_model.py` (5 przykładów kontrolnych, sufit początkującego, brak wieku → tylko RPE, Karvonen, beta-blokery → `hr_bpm_range=None`, determinizm, suma ≠ 1) | pytest modułu | dziesiątki tys. |
| 2 model + migracja 39 | `db.py` 1526–1553 (wzorzec 37/38) | `ExerciseBlock`, kolumny `WorkoutEntry`, `bloki_wbudowane.py`, ~9 wpisów rozciągania + 2 cardio w katalogu, seed dnia C | `test_migracje_przenosnosc`, `test_db_migracje`, testy katalogu | dziesiątki tys. |
| 3 API + publikacja | `habits.py`/`plan_weekdays.py` (wzorzec CLIENT_SCOPED), `exercises.py` (CRUD broadcast) | `routers/cardio.py` (`POST /api/clients/{client_id}/cardio/podglad` COACH + relacja; `GET /api/cardio/katalog`), `routers/exercise_blocks.py`, `schemas`, `elementy.py`, `slad.py`/`reguly.py`, `plans.py`, `serwis.py`, macierz, `privacy.py` 2.1; `tests/test_cardio_api.py`, `tests/test_exercise_blocks.py` | pytest API, macierz, bramka | setki tys. |
| 4 UI trenera | `PlanEditor.tsx`, `Templates.tsx`, `Checkin.tsx` 586–622 (skala z `aria-pressed`) | `suwaki.ts` + `test-suwaki.mjs`, `CardioPanel.tsx` (lazy), `BlokiTab.tsx`, zmiany w `PlanEditor.tsx`/`SzkicPlanu.tsx`/`Templates.tsx`/`types.ts` | `tsc`, build (budżet 120 kB), `test:helpers`, obejrzenie | setki tys. (największy koszt) |
| 5 UI klienta + dziennik | `Plan.tsx`, `Today.tsx`, `Progress.tsx` | `pozycje.tsx`, zmiany w `Plan.tsx`/`Today.tsx`/`Progress.tsx`; E2E `cardio.spec.ts`, `rozgrzewka.spec.ts` | E2E ×2 + `nawyki dni-treningowe`, a11y, PWA, przeklik ze zrzutami | setki tys. |
| 6 zamknięcie | — | CHANGELOG 0.73.0, RELEASE_STATUS, PERMISSIONS, BAZA_CWICZEN, KONFIGURATOR, WIEDZA, RISK_REGISTER, INSTRUKCJE, IMPORT_BAZ, STAN_PRZEKAZANIA, `docs/zlecenia/README.md`, `docs/cardio/PROGRESS.md` (lista do przeglądu trenera + [C]) | pełny pytest, ruff, Core 275, `spojnosc.py`, mutacje ×2, 3 recenzentów, scalenie `main` | dziesiątki tys. |

**Największy koszt:** etap 4 (panel z suwakami + bloki w edytorze). Taniej bez utraty
informacji: suwaki jako natywne `input[type=range]` z `aria-valuetext`, jeden wspólny
renderer pozycji dla Dzisiaj/Planu, panel cardio i zakładka „Bloki” za `React.lazy`
(budżet 120 kB). **Bezpiecznik: 3× plan.** Jeśli przekroczony, tnę w kolejności z promptu:
najpierw sekcja „Cardio” w Postępach (historia cardio zostaje w „Ostatnich treningach”
w Planie), potem edycja bloków w zakładce „Bloki” (tylko wbudowane + archiwizacja), nigdy
bramka zdrowotna ani ślad. Przegląd: 3 recenzentów wsadowo (bezpieczeństwo/zgody/dane
zdrowotne/IDOR; model suwaków i wzory wobec `model-suwakow-cardio.md`; testy/UX/treść/
dokumenty), P0/P1 naprawione przed przekazaniem, P2 do `docs/cardio/PROGRESS.md`.

## Czego nie dotykam

Core Human OS; konfigurator K1 (`konfigurator/silnik.py`, `eksport.py` — tylko notka w
`KONFIGURATOR.md`); `knowledge_graph`; biblioteka v2 (`exercise_catalog_v2.py`,
`import_exercises.py` — nowe wpisy idą do v1); import szablonów z pliku (`IMPORT_BAZ.md` §3.1
— wpis w „Ograniczenia”); integracje/AI/klucz szyfrowania; kasowanie czegokolwiek; pliki
gałęzi #67; istniejące plany demo poza dniem C klienta A (v2).

## Czego świadomie nie robię

Automatyczna progresja cardio; testy progowe/FTP/HRV; import z zegarków; rankingi; AI;
zmiana K1; nowe pytanie w wywiadzie (leki wpływające na tętno = pole bramki w panelu trenera,
nie wpis w `interview_flow`/`HINT_AREAS`); pole `pattern="ROZCIAGANIE"` (nowe wpisy
rozciągania statycznego dostają `pattern="MOBILNOSC"` + tag — bez zmiany kontraktu
słownika); sekcja „Cardio” w zakładce Postępy (moduł za flagą; pierwsza pozycja do cięcia
z promptu — historia cardio w „Ostatnich treningach” w Planie).

## Odstępstwa od promptu (uzupełniane w trakcie)

1. **Jedna reprezentacja bloków:** prompt §3.1 wprowadza `kind: warmup_block/stretch_block`
   jako rodzaje pozycji, a §3.2 dodatkowo `warmup_block_id`/`cooldown_block_id` na poziomie
   dnia. Implementuję **tylko pozycje** (`kind` + `block_id` + migawka `block` w
   `exercises[]`) — jedna droga w `elementy.py`, walidacji i UI; kolejność pozycji ustawia
   rozgrzewkę na początku, rozciąganie na końcu.
2. **Stałe modelu w `cardio/stale.py`** (Python), nie `dane/stale.json` — bez nowego katalogu
   danych w `package-data` (strażnik `test_pakietowanie`), ta sama treść i komentarze źródeł.
3. **Bez nowego pytania wywiadu** o leki wpływające na tętno — pole `hr_medication` w bloku
   zdrowotnym panelu trenera (jak pola `health{}` konfiguratora); `HINT_AREAS` nietknięte.
4. **Wiek i tętno spoczynkowe** — prefill po stronie serwera z ostatniego szacunku
   kalorycznego (`CalorieEstimate.inputs_json.wiek`) i ostatniego pomiaru `resting_hr`,
   wyłącznie przy dostępie trenera do `DOMAIN_HEALTH`; trener może wpisać ręcznie; brak →
   tryb „tylko RPE”.
5. **Postępy-cardio** wycięte zgodnie z kolejnością cięcia z promptu (patrz wyżej).
6. **`SzkicPlanu.tsx`** (szkice 0.58.0): nowe rodzaje pozycji są zachowywane przez
   `elementy.py` i pokazywane jako pozycje tylko do odczytu z odznaką (rozgrzewka /
   rozciąganie / cardio); dodawanie ich w szkicu — przez `PlanEditor` (nowa wersja) albo
   przyszła runda.

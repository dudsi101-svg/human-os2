# Plan sesji: bloki jak szablony — aeroby jako trzeci rodzaj bloku, przypisanie szablonu + bloków (0.76.0, migracja 41)

**Gałąź:** `agent/bloki-jak-szablony` (od `main` = `4e516e1`, 0.75.1). **Rola:** podległa
sesja pisząca wyznaczona przez integratora 14.09.2026 na polecenie właściciela:

> „Chciałbym żebyś z bloków gdzie jest rozgrzewka, aeroby i rozciąganie (sprawdź zresztą
> czy to jest, jeśli nie to uzupełnij) można było również korzystać jak z szablonów, tylko
> żeby można było dodać jednocześnie szablon treningowy i szablon z bloku, a nawet dwa.”

**Protokół:** w chwili startu (14.09, sprawdzone przez `list_pull_requests`) **nie ma
żadnego otwartego PR-a** — tym bardziej `[WRITER]`. Praca wyłącznie w worktree
`/home/user/wt/bloki`. `docs/ZASADY_pracy_agentow.md` wskazany w poleceniu **nie istnieje w
repozytorium** (sprawdzone `find`) — obowiązują `/AGENTS.md`, `KARTA_WSPOLPRACY.md`,
`KOORDYNACJA.md` §0 i `STAN_PRZEKAZANIA.md`.

## Rezerwacje (KOORDYNACJA §0, sprawdzone na żywo 14.09 na `4e516e1`)

* **Wersja 0.76.0** — `CHANGELOG.md` ma na górze 0.75.1; sekcja 0.76.0 idzie NA GÓRĘ.
  Podbicie w `backend/pyproject.toml`, `backend/dzik_os/__init__.py`, `frontend/package.json`,
  `README.md`, `docs/RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md` (§1 nagłówek + §2 tabela
  gałęzi), `docs/zlecenia/README.md` (wiersz 10).
* **Migracja 41** (addytywna): `ALTER TABLE exercise_blocks ADD COLUMN cardio_json TEXT`
  (NULL dla rozgrzewki/rozciągania). Ostatni wpis w `db.py` = **40** (motyw) — ciąg bez luk.
  Wycofanie = ignorowanie kolumny.
* **`export_version` bez zmian („2.1”)** — eksport klienta (`routers/privacy.py`) zrzuca
  `content_json` wersji planu generycznie; pozycja cardio z bloku ma dokładnie kształt
  pozycji `kind: "cardio"` z 0.73.0 (+ opcjonalne `block_id`/`block`, które eksport i tak
  przenosi jako część JSON-a). Bloki (`exercise_blocks`) to katalog trenera, nie dane
  klienta — nie wchodzą do eksportu (jak `Exercise`).
* **Porty E2E:** 8140/8141, `DZIK_E2E_DIR=/tmp/dzik-e2e-8140`.

## Rozpoznanie (stan zastany, zweryfikowany w kodzie 14.09)

* `ExerciseBlock` (`models.py:2168`): `kind` WARMUP/STRETCH, `level` NULL dla STRETCH,
  **`variant VARCHAR(4) NOT NULL`** (migracja 39). 12 wbudowanych (`cardio/bloki_wbudowane.py`),
  ładowanie idempotentne po `(kind, level, variant)` (`cardio/bloki.py::zaladuj_wbudowane`),
  migawka `migawka(row)`. Router `/api/coach/exercise-blocks` (GET, POST, load-builtin,
  GET/PUT/{id}, POST {id}/status). **Bloków aerobowych nie ma** — polecenie „sprawdź, jeśli
  nie ma, uzupełnij” = dodać.
* Cardio = pozycja planu `kind: "cardio"` z `CardioIn` (`schemas.py:164`), liczone w
  `CardioPanel.tsx` per klient; w szablonie panel odmawia (`clientId === null`), więc szablon
  nigdy nie ma cardio. Silnik `cardio/model.py::propozycja` działa bez wieku (`hrmax_source
  "none"`, tylko %HRmax + RPE + test mowy) — to jest tryb presetu bloku.
* `POST /api/plans/{template_id}/copy-to/{client_id}` (`routers/plans.py:213`) — bez ciała,
  kopia `content_json` 1:1, **bez** `slady_cardio` i bez walidacji `exercise_id` (luka 5).
  UI: `ClientDetail.tsx` `PlanTab` — `<select aria-label="Wybierz szablon planu">` + „Kopiuj do
  klienta”.
* Renderowanie u klienta: `Plan.tsx`/`Today.tsx` wybierają renderer po `rodzajPozycji(ex)`
  — pozycja `kind: "cardio"` z `block_id` trafi do `PozycjaCardio` bez zmian w tych plikach;
  nagłówek „z bloku” dokładam w `pozycje.tsx`.
* Testy: `test_exercise_blocks.py` (12), `test_template_copy.py` (3, bez ciała),
  `access_matrix.py` (copy-to = CLIENT_SCOPED), E2E `rozgrzewka.spec.ts` („12 bloków”).
  `test_a11y.mjs` leży w `apps/dzik-os/e2e/` (nie we `frontend/e2e/`), kroki 7/7a/7b/8 dla
  trenera na 1024/320 px; CI odpala go w obu motywach (`DZIK_THEME`).

## Decyzje projektowe (wykonawcze, do potwierdzenia przez właściciela)

1. **`kind = CARDIO`** jako trzeci rodzaj bloku. `level` obowiązkowy jak WARMUP. **`variant`
   nie dotyczy** — kolumna jest `NOT NULL` (migracja 39), a zmiana nullowalności w SQLite
   wymaga przebudowy tabeli (bez precedensu w `db.py`, ryzyko na produkcji). Dlatego w bazie
   blok CARDIO ma `variant = ""` (pusty napis), a **API zwraca `variant: null`** i migawka
   w planie też `null`. To odstępstwo od „NULL w kolumnie” z polecenia — semantyka API
   zgodna, schemat bez przebudowy.
2. **Cel** (`goal`) bloku CARDIO żyje w `cardio_json.goal_mix` (bez nowej kolumny); w
   liście/etykiecie pokazujemy cel dominujący (`goal`, `goal_label` w odpowiedzi API).
   Klucz idempotencji wbudowanych: `(kind, level, variant)` dla WARMUP/STRETCH,
   `(kind, level, goal)` dla CARDIO — `klucz()` rozszerzone, `zaladuj_wbudowane` bez zmiany
   kontraktu (`created/skipped/ids`).
3. **`cardio_json`** = pełny obiekt `CardioIn` policzony silnikiem **bez danych klienta**
   (`age=None`, `resting_hr=None`, `weight_kg=None` → kotwice RPE + %HRmax, bez ud./min),
   `trace.source = "blok"`, `model_version` bieżący. Urządzenia domyślne: rowerek, bieżnia,
   wioślarz (3 z 5 w `urzadzenia.py`). `items_json` = 1–3 pozycje opisowe generowane z
   propozycji („Rowerek / Bieżnia / Wioślarz — 25 min, RPE 2–3, test mowy: pełne zdania”),
   `catalog=False` (bez `exercise_id`).
4. **Wbudowane bloki CARDIO: 9** = 3 cele × 3 poziomy, wagi wg `model-suwakow-cardio.md` §4:
   regeneracja `(0, 0, 1)` → ~60 % HRmax, ciągła 25 min (początkujący 20); wydolność
   `(0, 1, 0)` → interwały wg poziomu 8×1/1, 6×2/2, 4×4/3 (16/24/28 min); redukcja
   `(0.6, 0.1, 0.3)` → ~69 % HRmax, ciągła 40 min (początkujący 30). Liczby liczy silnik —
   nic nie jest wpisane ręcznie; treść „do przeglądu trenera” jak pozostałe bloki.
   Razem 21 wbudowanych (9 WARMUP + 9 CARDIO + 3 STRETCH).
5. **Trener może tworzyć/edytować własny blok CARDIO** w Szablonach → Bloki: podaje cel
   (jeden z trzech), poziom, urządzenia; `cardio_json` liczy serwer tym samym silnikiem
   (`BlockIn.goal`, `BlockIn.machines`), pozycje opisowe generowane, gdy trener ich nie wpisał.
   Suwaków w formularzu bloku nie ma — preset to jeden dominujący cel (decyzja domyślna,
   pytanie do właściciela).
6. **Pozycja planu z bloku CARDIO** = `kind: "cardio"`, `cardio` = kopia `cardio_json`,
   `block_id` (miękkie) + `block` migawka (`BlockSnapshotIn.kind` dopuszcza CARDIO, `variant`
   opcjonalne). Kolejność w dniu: rozgrzewka na początek, cardio po siłowych (przed
   rozciąganiem), rozciąganie na koniec. Trener może nadpisać liczby przez CardioPanel po
   przypisaniu — bez zmian w panelu.
7. **W edytorze szablonu** (`clientId === null`) przycisk **„+ Cardio z bloku”** wstawia blok
   bez klienta; stary „+ Cardio” dalej odmawia w szablonie. W planie klienta obie drogi.
8. **`copy-to` z opcjonalnym ciałem** `{"blocks": [id…]}` (0–3, maks. jeden na rodzaj; cudzy/
   nieistniejący → 404, zarchiwizowany → 422, duplikat rodzaju → 422 po polsku). Bez ciała =
   odpowiedź i zachowanie jak dziś (`{id, version_id, version_no}`); z blokami odpowiedź
   dokłada `blocks_applied: {added: {warmup, cardio, stretch}, skipped_days: [...]}` — dzień,
   który już ma blok danego rodzaju z szablonu, nie jest dublowany. Dodatkowo (luka 5)
   `copy-to` zawsze woła `slady_cardio` i walidację `exercise_id` (jak `create_plan`).
9. **Osobna trasa** `POST /api/clients/{client_id}/plans/from-blocks` `{title, days:[{name,
   weekday?}] (1–7), blocks (1–3), reason?}` → plan v1, każdy dzień = wybrane bloki. Jedna
   trasa z opcjonalnym `template_id` byłaby czystsza w API, ale `copy-to` ma dziś inny kształt
   ścieżki i test bez ciała musi przejść bez zmian — dwie trasy, wspólna logika
   (`cardio/bloki.py::zloz_bloki_do_dni`, `wczytaj_bloki_do_planu`).
10. **Walidacja `exercise_id` przy `copy-to`:** id sprawdzane z surowego JSON-a (bez
    przepisywania treści przez `PlanDayIn`), tylko pozycje siłowe najwyższego poziomu (jak
    `_validate_exercise_refs`). Szablon z ćwiczeniem zarchiwizowanym po zapisie → 422 z listą
    id — ten sam próg, co przy nowej wersji planu (precedens 0.73.0).
11. **Ślad H_CARDIO** dla każdej wstawionej pozycji cardio (z bloku też) — `slady_cardio` na
    gotowym `content` w tej samej transakcji co wersja; `fakty_sladu` bez zmian (źródło „blok”
    zostaje w `trace`, nie w faktach — test `test_fakty_sladu_bez_danych_zdrowotnych` nietknięty).
12. **UI trenera:** karta **„Przypisz plan”** w `PlanTab` (`ClientDetail.tsx`) zastępuje
    „Z szablonu…”: `fieldset`/`legend`, wybór „szablon treningowy” albo „bez szablonu — tylko
    bloki”, trzy `<select>` (Rozgrzewka / Aeroby (cardio) / Rozciąganie) z blokami ACTIVE i
    etykietą „poziom · wariant/cel · ≈min”, opcja „bez”; brak bloków rodzaju → komunikat jak w
    `WyborBloku`; „tylko bloki” → tytuł + liczba dni 1–7 („Dzień 1…”); podsumowanie przed
    wysłaniem; `role="status"` po sukcesie z `blocks_applied`. Zero literałów kolorów.
13. **Czyste funkcje frontendu** w `src/bloki.ts` (`pozycjaZBloku`, `wstawDoDnia`,
    `etykietaBloku`, `podsumowaniePrzypisania`) + `scripts/test-bloki.mjs` w `test:helpers`.

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|
| 0 | ten plan, push, draft PR `[WRITER]` | PR widoczny | 1 |
| 1 | CARDIO: `models.py` (`cardio_json`, docstring), `db.py` (41), `bloki_wbudowane.py` (RODZAJE, ETYKIETY, 9 presetów przez silnik, `klucz`), `bloki.py` (ładowanie, migawka, `pozycja_z_bloku`, `zbuduj_cardio_json`), `schemas.py` (`BlockSnapshotIn`, walidator), `routers/exercise_blocks.py` (`BlockIn.goal/machines`, `_out` z `cardio`/`goal`), `copy-to` ślad + walidacja; frontend `types.ts`, `bloki.ts`, `PlanEditor.tsx` („+ Cardio z bloku”, `WyborBloku` CARDIO), `BlokiTab.tsx`, `pozycje.tsx` | backend testy (12→21, CRUD CARDIO), `tsc`, `build` | 5 |
| 2 | `copy-to` z `blocks`, `from-blocks`, `access_matrix.py`, `PERMISSIONS.md`, karta „Przypisz plan” w `ClientDetail.tsx` | testy API (1/2/3 bloki, 422/404, brak dublowania, ślad, IDOR, 403), `tsc`, `build` | 5 |
| 3 | testy migracji 41 (stara baza), `test-bloki.mjs`, E2E `bloki-jak-szablony.spec.ts`, `rozgrzewka.spec.ts` 12→21, krok a11y, dokumenty (CHANGELOG, INSTRUKCJE, cardio/PROGRESS, E2E.md, STAN, RELEASE_STATUS, zlecenia/README, `docs/bloki-jak-szablony/PROGRESS.md`), bramki | wszystkie bramki z liczbami | 4 |

Bezpiecznik: 3 × 15 = 45 jednostek; przekroczenie = raport i stop.

## Czego nie robię

* Nie zmieniam silnika `cardio/model.py` ani kotwic w `stale.py` (presety to wywołania silnika).
* Nie dotykam `CardioPanel.tsx` (odmowa w szablonie zostaje — „+ Cardio z bloku” obok).
* Nie zmieniam `export_version`, nie ruszam Core (`hos_engine/`, `tests/`).
* Nie dokładam bloków do 26 wbudowanych schematów (`plan_templates_data.py`) — bloki dokłada
  się przy przypisaniu (to jest sens polecenia), nie w treści schematu.
* Nie przebudowuję kolumny `variant` (patrz decyzja 1).
* Bez nowych ekranów u klienta; bez AI; bez zmian w dzienniku cardio (`Plan.tsx`).

## Pliki współdzielone (zmieniam jawnie, tylko własne sekcje)

`models.py` (kolumna + docstring `ExerciseBlock`), `db.py` (wpis 41), `schemas.py`
(`BlockSnapshotIn`, `ExerciseIn._rodzaj_spojny`), `routers/plans.py` (`copy-to`, nowa trasa,
pomocnik walidacji id), `routers/exercise_blocks.py`, `cardio/bloki.py`, `cardio/bloki_wbudowane.py`,
`tests/access_matrix.py`, `tests/test_exercise_blocks.py`, `types.ts`, `PlanEditor.tsx`,
`BlokiTab.tsx`, `ClientDetail.tsx`, `pozycje.tsx`, `package.json` (wersja + `test:helpers`),
`e2e/rozgrzewka.spec.ts`, `e2e/test_a11y.mjs`, `CHANGELOG.md`, `PERMISSIONS.md`,
`INSTRUKCJA_TRENERA.md`, `INSTRUKCJA_KLIENTA.md`, `docs/cardio/PROGRESS.md`, `docs/E2E.md`,
`STAN_PRZEKAZANIA.md`, `RELEASE_STATUS.md`, `README.md`, `docs/zlecenia/README.md`.

**Pliki nowe:** `frontend/src/bloki.ts`, `frontend/scripts/test-bloki.mjs`,
`frontend/scripts/tsconfig.bloki.json`, `frontend/e2e/bloki-jak-szablony.spec.ts`,
`backend/tests/test_bloki_jak_szablony.py`, `docs/bloki-jak-szablony/PROGRESS.md`, ten plan.

## Odstępstwa od planu

(uzupełniane w trakcie)

## Plan kontra rzeczywistość

(uzupełniane na końcu)

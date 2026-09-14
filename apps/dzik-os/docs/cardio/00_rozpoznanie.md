# Rozpoznanie (etap 0) — rozgrzewka, rozciąganie i cardio z suwakami (0.73.0)

Weryfikacja linii z promptu (`PAKIET_ZLECEN_2026-09-14.md` §9, tabela §2 i §2a) na
`main` = `bdb261c` (0.71.0), 14.09.2026:

* `models.py`: `Exercise` l. 780–845 (`muscle_group` z MOBILNOSC/CARDIO, `level`,
  `pattern`, `source_ref`, `review_reason`); `WorkoutEntry` l. 284–298 — **bez pól czasu,
  tętna, RPE, dystansu** (potwierdzone); `MetricDefinition`/`Measurement` l. 444–466
  (`kind` dowolny tekst → metryka `resting_hr` bez migracji).
* `exercise_catalog.py`: 155 wpisów, 14 CARDIO + 14 MOBILNOSC (lista nazw zweryfikowana:
  wszystkie pozycje bloków z §5 promptu istnieją poza siedmioma rozciąganiami statycznymi
  i dwoma cardio „na parametry” — dodane w tej rundzie, katalog = 164). Katalog jest
  seedowany do bazy trenera (`seed.py` l. 224) — nie ma osobnego `load-builtin` dla ćwiczeń
  (prompt mylił z produktami).
* `schemas.py` l. 68–101: `ExerciseIn` (wszystko tekst, bez rodzaju), `PlanDayIn`;
  `WorkoutSetIn.warmup`/`unit` (0.66.0), `WorkoutEntryIn` l. 126–134.
* `publikacja/elementy.py` l. 44–46: allow-list pól pozycji — pole spoza listy **znika ze
  szkicu bez błędu** (potwierdzone w kodzie `_sprawdz_pola` → `BladOperacji` przy `set`,
  a `replace` też odrzuca; dopisane `kind`, `block_id`, `block`, `cardio`).
* `wiedza/slad.py` l. 32–45: `JEDNOSTKI` (nieznana jednostka → `inconsistent_data` w
  `reguly.sprawdz`); l. 205–215 `slad_wersji_trenera` wołany z `routers/plans.py` l. 178
  i `publikacja/serwis.py` l. 301 — **ślad `H_CARDIO` dołożony w obu miejscach** (ta sama
  transakcja co wersja) plus `create_plan` (nowy plan klienta z cardio).
* `wiedza/reguly.py` l. 49–63 (`H_LAYOUT`/`H_VOLUME`) i `renderuj` — reguła `H_CARDIO`
  z tekstem „Decyzja / Co na nią wpłynęło / Kiedy to się zmieni”; `resolver.py` jest
  generyczny wobec `target_type` (bez zmian).
* `konfigurator/zdrowie.py::ocen_zdrowie` — reużyte 1:1; pytanie o leki wpływające na tętno
  jako dodatkowe pole `hr_medication` w bloku `health{}` (brak = `needs_input`).
* `coach_hints.HINT_AREAS` — **nietknięte** (bez nowego pytania wywiadu; odstępstwo 3 planu).
* `konfigurator/eksport.py` l. 54–60 — `warmup_minutes` nadal wyrzucany; K1 nietknięty,
  notka w `KONFIGURATOR.md`.
* `plan_templates_data.py` TPL-025/026 — pseudo-dzień „Wytyczne tygodnia” zostaje (stare
  kopie planów bez zmian); zamiana na blok + pozycję cardio = kolejna runda.
* `routers/privacy.py` l. 76–90 `_rows` serializuje wszystkie kolumny modelu → nowe pola
  `workout_entries` wchodzą do eksportu bez osobnego kodu; `export_version` 2.0 → 2.1;
  usuwanie konta l. 549–553 zeruje `comment` wpisów (pola liczbowe cardio zostają jak serie).
* `routers/postepy.py` — bez zmian (sekcja Cardio w Postępach wycięta wg kolejności cięcia);
  `postepy/serwis.py` l. 62 pomija wpisy bez `sets_json` → cardio nie tworzy rekordów.
* `routers/today.py` l. 45–95 — `workout.day` niesie pełną treść dnia, więc frontend
  renderuje nowe rodzaje bez zmian API.
* `db.py`: ostatni wpis **38**; 37 = powitanie; migracja **39** addytywna.
  `tests/test_exercises_extended.py::test_migration_19…` stubuje tabele dla ALTER-ów —
  dołożony stub `workout_entries` (wzorzec z 0.70.0 dla `users`).
* Frontend: `Plan.tsx` (lokalny `RestTimer` → przeniesiony do `pozycje.tsx`), `Today.tsx`
  l. 175–212, `PlanEditor.tsx` l. 200–520 (`addFromLibrary`, przyciski dnia l. 455–470),
  `SzkicPlanu.tsx` l. 405–440, `Templates.tsx` l. 26–60 (zakładki), `ClientDetail.tsx`
  l. 632–640 (PlanTab), `Checkin.tsx` l. 586–622 (skala z `aria-pressed` — wzorzec
  przycisków tak/nie w bramce), `Progress.tsx` l. 102–110 (`KIND_LABELS`), brak
  `input[type=range]` w `src/` (`.scale-row` CSS l. 226–231 reużyty przez suwaki).
* E2E: `playwright.config.ts` — `DZIK_E2E_PORT` / `DZIK_E2E_PORT_POSTEPY`; projekt `telefon`
  uruchamia wszystkie specy poza `postepy`; a11y/PWA startują własny serwer na losowym porcie.

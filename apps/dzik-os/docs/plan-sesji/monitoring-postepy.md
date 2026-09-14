# Plan sesji: zakładka Monitoring / Postępy (0.66.0, migracja 36)

**Gałąź:** `agent/monitoring-postepy` (scalona z `main` 387ba65 = 0.63.0). **Rola:** aktywny
piszący — prompt właściciela `docs/monitoring-tab/PROMPT_agent_monitoring.md`, specyfikacja
`instrukcja_zakladka_monitoring.md`, rozpoznanie etapu 0 `00_rozpoznanie.md` (STOP zdjęty
14.09: właściciel zaakceptował trzy decyzje — flaga rozgrzewki i jednostka w serii, tożsamość
ćwiczenia po znormalizowanej nazwie z raportem bliźniaków, nowy silnik zastępuje
`personal-records`/`strength-series`).
**Rezerwacje (KOORDYNACJA §0):** wersja **0.66.0**, migracja **36** (nawyki 34, biblioteka diet
35, strona publiczna 0.65.0 bez migracji). Pliki współdzielone: `models.py`, `db.py`, `main.py`,
`schemas.py`, `config.py`, `types.ts`, `App.tsx`, `components.tsx` (Nav), `CHANGELOG`,
`STAN_PRZEKAZANIA`. Budżet właściciela: ≤ 1 mln tokenów, ≤ 8 agentów (3 recenzentów + 1
weryfikator na końcu; reszta pracy jednym piszącym, bez pętli „agent na znalezisko”).

## Cel
Zakładka `/monitoring` (klient: „Postępy”, trener: „Monitoring”) w miejscu „Raportu”;
raport przechodzi do „Więcej” (z przekierowaniem `/raport`); „Postępy” z „Więcej” stają się
sekcjami Konsekwencja/Sylwetka. Trzy osie: Forma (rekordy, e1RM, tonaż) → Konsekwencja
(frekwencja, seria tygodni, dieta) → Sylwetka (waga średnia 7 dni, obwody, zdjęcia). Wszystko za
flagą `monitoring_tab_enabled` (env `DZIK_MONITORING_TAB_ENABLED`, domyślnie wyłączona).

## Decyzje projektowe (dopasowanie §11 do istniejących modeli)
* **Seria**: `WorkoutSetIn` + `warmup: bool = False`, `unit: "kg"|"lb"` normalizowane do kg
  przy zapisie (`weight_kg` zostaje jedynym polem w bazie; `warmup` zapisywany w `sets_json`).
  Serie historyczne = robocze (`warmup=False`).
* **Ćwiczenie**: tożsamość = `exercise_key` (nazwa: małe litery, pojedyncze spacje, bez
  końcowych znaków interpunkcyjnych). Brak FK do `Exercise` — `WorkoutEntry.exercise_name`
  jest tekstem; grupa mięśniowa przez dopasowanie nazwy do bazy ćwiczeń trenera (`INNE` gdy
  brak). Backfill raportuje bliźniaki (klucze różniące się tylko diakrytyką/wielkością liter
  w oryginale) do decyzji trenera, nie scala.
* **Rekordy**: tabela `exercise_records` (typ WEIGHT/REPS_AT_WEIGHT/SET_VOLUME/SESSION_VOLUME/
  E1RM, `value`, `secondary_value`, `set_ref` = `entry_id:index`, `achieved_on`,
  `previous_value`, `superseded_at`); tabela agregatów `training_week_aggregates` (tydzień ISO:
  tonaż, serie per grupa, sesje, zaplanowane). Przeliczenie per ćwiczenie przy zapisie sesji
  (jedyna ścieżka zapisu dziś: `POST /clients/{id}/workouts`) i w backfillu
  `python -m dzik_os.recalculate_progress [--client ID]` (idempotentny).
* **Silnik** `dzik_os/postepy/rekordy.py`: czyste funkcje, wejście = lista serii z datą i
  identyfikatorem, wyjście = lista rekordów z historią; wszystkie reguły §8.1–8.2 (pierwsze
  wykonanie nie jest rekordem, E1RM tylko r ≤ 10, rozgrzewka wykluczona, masa ciała w=0 →
  tylko REPS_AT_WEIGHT, wyrównanie = „wyrównany” bez nowego wpisu, cofnięcie po usunięciu).
  `dzik_os/postepy/waga.py`: średnia krocząca 7 dni (min. 3 pomiary), trend z regresji 28 dni
  (≥ 14 dni i ≥ 6 pomiarów), zaokrąglenie 0,1.
* **Flaga zdrowotna**: `CalorieEstimate.hidden_for_client` ostatniego szacunku
  (`zk_zaburzenia`) → dla roli klient `/monitoring/body` = 404, `summary` bez wagi; filtrowanie
  serwerowe, test integracyjny „brak pola `weight` na żadnym poziomie” PRZED implementacją.
* **Stare endpointy** `personal-records`/`strength-series` zostają jako cienkie odczyty z
  nowych tabel (jedno źródło prawdy) — bez zmian kontraktu dla starych kart.
* **Nawigacja**: Nav i trasy warunkowo po `features.monitoring_tab` z `/api/me`; `/raport` →
  `Navigate replace` do `/wiecej/raport` (SPA nie zna 301; przekierowanie w routerze).
  Przy wyłączonej fladze: Nav, trasy i „Więcej” identyczne jak dziś (test E2E).

## Etapy → czytam → wytwarzam → weryfikacja → nakład

| Etap | Czytam | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 1 silnik | spec §8–9, `records.py` | `postepy/rekordy.py`, `postepy/waga.py` | 8 + 3 testy jednostkowe z §14 | dziesiątki tys. |
| 2 model + migracja 36 | `models.py`, `db.py` (wzór 34) | `ExerciseRecord`, `TrainingWeekAggregate`, `WorkoutSetIn.warmup/unit`, przeliczanie przy zapisie | przenośność, pakietowanie, test zapisu sesji | dziesiątki tys. |
| 3 backfill | `seed.py` | `dzik_os/recalculate_progress.py` | test podwójnego uruchomienia | dziesiątki tys. |
| 4 API | `authz.py`, `monitoring.py` | `routers/postepy.py`: summary, records, training, body, clients, clients/{id}; stare endpointy na nowych tabelach | testy: flaga zdrowotna (najpierw), 403/404 obcego trenera, liczba zapytań, macierz dostępu | setki tys. |
| 5–6 UI | `Progress.tsx`, `components.tsx`, `ClientDetail.tsx` | `pages/postepy/*` (klient §6, trener §7), typy | tsc, build, E2E, a11y | setki tys. (największy) |
| 7 nawigacja | `App.tsx`, `Nav`, `More.tsx` | trasa, etykiety per rola, przekierowanie, flaga | E2E flaga włączona/wyłączona | dziesiątki tys. |
| 8 zamknięcie | — | CHANGELOG, RELEASE_STATUS, PERMISSIONS, INSTRUKCJE, STAN_PRZEKAZANIA; 3 recenzentów + 1 weryfikator; raport | pełny pytest, spójność, CI | dziesiątki tys. |

**Największy koszt:** UI (dwa widoki, wykresy). Taniej bez utraty dokładności: jeden komponent
`PanelPostepow` dla klienta i trenera (jak `PanelNawykow`), wykresy na istniejących
`Sparkline`/prostych SVG, dane z jednego `GET /monitoring/summary` + sekcje leniwie.
Bezpiecznik: 3× plan → stop i raport.

## Świadomie nie robię (§5 spec)
Rekordów TIME/DISTANCE (tabela ma `record_type`, więc da się dodać), porównań między
klientami, wniosków AI, eksportu PDF, push o rekordzie (tylko w aplikacji, jedno na sesję),
zmian w logice „Raportu”, backfillu na kopii produkcyjnej (wymaga dostępu — raport z seedu).

## Bramki
ruff; pełny pytest (SQLite; PostgreSQL w CI); Core 275; `tools/spojnosc.py`; tsc + build
(budżet JS); test:helpers; E2E `postepy.spec.ts` (klient: kafelki, rekordy, sekcje; trener:
lista sygnałów, widok klienta; flaga wyłączona = stara nawigacja); a11y; PWA offline.
Nie scalam bez zielonego CI; scalam po #66 i #67 (rezerwacje).

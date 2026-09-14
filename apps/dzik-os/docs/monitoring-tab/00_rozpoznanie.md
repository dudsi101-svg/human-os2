# Zakładka Monitoring / Postępy — etap 0: rozpoznanie (STOP przed etapem 1)

Gałąź `agent/monitoring-postepy` (0.63.0, migracja 34). Materiały właściciela:
`PROMPT_agent_monitoring.md`, `instrukcja_zakladka_monitoring.md` (w tym katalogu).
Rozpoznanie wyłącznie z odczytów (`grep` + odczyt celowany), bez zmian w kodzie.

## Istniejące modele (nazwy faktyczne, nie z §11 specyfikacji)

| Pojęcie ze specyfikacji | W repo | Uwagi |
|---|---|---|
| Sesja treningowa | `WorkoutSession` (`models.py:263`): `client_id`, `performed_on`, `comment`, `pain_note` | brak pola „plan zrealizowany/nie” poza wpisami |
| Seria | `WorkoutEntry.sets_json` (`models.py:289`) = lista `{weight_kg, reps}` (`schemas.WorkoutSetIn`, `schemas.py:115`) + tekstowe `result` („3x8 @ 80kg”) | **brak flagi rozgrzewki, „nieukończona”, „z asekuracją”; brak jednostki (zawsze kg)** |
| Ćwiczenie w sesji | `WorkoutEntry.exercise_name` (tekst) + `exercise_index` — bez klucza obcego do bazy ćwiczeń | **wariant istnieje tylko jako inna nazwa**; katalog `Exercise` (`models.py:774`: `name`, `muscle_group`, `equipment`, `muscles_primary/secondary`) nie ma pojęcia wariantu ani powiązania z wpisami sesji |
| Pomiary ciała | `Measurement` (`models.py:449`): `kind` (weight/waist/…), `value`, `unit`, `measured_at` | istnieje, z jednostką |
| Zdjęcia | `ProgressPhoto` (`models.py:497`) + `StoredFile` (autoryzacja przy pobraniu pliku, id `HOS-FIL-…`) | zgodne z §10.2 (dostęp per plik, id niegadalne) |
| Rekordy | **istnieją**: `routers/records.py` — `GET /clients/{id}/personal-records` (maks. ciężar z `sets_json` albo z tekstu), `GET …/strength-series` (objętość i e1RM Epleya per dzień), runda 0.28/0.34 | liczone w locie, bez tabeli, bez historii, bez reguły „pierwsze wykonanie nie jest rekordem” |
| Dziennik żywieniowy | `DailyNutritionLog` (adherence dnia) | źródło dla „realizacja diety” (§6.4) |
| Frekwencja/plan | `ScheduleItem` + `ScheduleCompletion` | źródło „wykonane / zaplanowane” |
| Zakładka „Raport” | `/raport` = `pages/client/Checkin.tsx`; „Postępy” w „Więcej” = `pages/client/Progress*` (do potwierdzenia nazwy) | migracja nawigacji §13 |
| Flaga `ZABURZENIA_ODZYWIANIA` | **nie istnieje** — powstaje w rundzie 0.62.0 (wywiad kaloryczny, `agent/wywiad-zapotrzebowanie`) | Monitoring zależy od tej rundy |

## Braki blokujące reguły §8.2 (sygnał STOP z promptu właściciela)

1. **§8.2.4 — flaga serii rozgrzewkowej**: brak. Proponuję dodać do `WorkoutSetIn`
   pola `warmup: bool = False` (i `unit: "kg"|"lb"` z normalizacją do kg przy zapisie,
   §8.2.6) oraz przełącznik „rozgrzewka” w dzienniku serii klienta; stare wpisy = `False`.
2. **§8.2.5 — wariant ćwiczenia**: brak modelu. Proponuję tożsamość rekordu = znormalizowana
   nazwa ćwiczenia (małe litery, bez podwójnych spacji) bez scalania; backfill raportuje
   „podejrzane bliźniaki” (nazwy różniące się tylko wielkością liter/spacjami) do decyzji
   trenera, nie scala ich automatycznie.
3. **§10.1 — flaga zdrowotna**: zależność od rundy 0.62.0 (wywiad kaloryczny) — test
   integracyjny flagi piszę po jej powstaniu; kolejność scalania: 0.62.0 przed 0.63.0.

## Decyzje właściciela wymagane przed etapem 1

- [ ] Zgoda na pola `warmup`/`unit` w serii (zmiana modelu danych dziennika, migracja
  addytywna, stare serie traktowane jako robocze).
- [ ] Zgoda na tożsamość ćwiczenia po nazwie (bez modelu wariantów) + raport bliźniaków.
- [ ] Potwierdzenie, że dotychczasowe `personal-records`/`strength-series` mają zostać
  zastąpione nowym silnikiem (jedno źródło prawdy), a nie działać obok.

## Plan etapów (po decyzjach) — nakład

| Etap | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|
| 1 silnik rekordów | `dzik_os/postepy/rekordy.py`: czyste funkcje, reguły 8.1/8.2 | 8 testów jednostkowych z §14 | setki tys. |
| 2 model + migracja 34 | `exercise_record` (superseded_at), `progress_aggregate` (tonaż tygodnia, serie/grupa) | przenośność, pakietowanie | dziesiątki tys. |
| 3 backfill | `python -m dzik_os.recalculate_progress [--client]` idempotentny | test podwójnego uruchomienia | dziesiątki tys. |
| 4 API | `/api/monitoring/*` z §12 + waga (§9) | test flagi PRZED implementacją, 403 dla obcego trenera, N+1 | setki tys. (największy koszt) |
| 5–6 UI | klient §6.1–6.5, trener §7.1–7.2 | `tsc`, E2E, a11y | setki tys. |
| 7 nawigacja | `/monitoring`, „Raport” do „Więcej”, przekierowanie `/raport`, flaga `monitoring_tab_enabled` | E2E przy fladze wyłączonej = bez zmian | dziesiątki tys. |

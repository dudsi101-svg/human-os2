# Zakładka Postępy / Monitoring — stan prac i sprawy otwarte (0.66.0)

Uzupełnienie `instrukcja_zakladka_monitoring.md` (specyfikacja),
`PROMPT_agent_monitoring.md` (prompt) i `00_rozpoznanie.md` (etap 0).
Plan i realizacja: `docs/plan-sesji/monitoring-postepy.md`.

## Co działa (PR #61, migracja 36, flaga `DZIK_MONITORING_TAB_ENABLED`)

Silnik rekordów i wagi, model + migracja, backfill, API
`/api/monitoring/*`, wspólny panel klienta/trenera, lista sygnałów
trenera, nawigacja za flagą, testy (24 backend, E2E z flagą i bez,
a11y, PWA). Opis w `CHANGELOG.md` 0.66.0.

## Rozbieżności ze specyfikacją (świadome, do decyzji właściciela)

| # | Specyfikacja | Zrobione | Dlaczego |
|---|---|---|---|
| 1 | §10.2: obcy trener → **403** | **404** („Nie znaleziono”) | polityka całej aplikacji od P3 (IDOR): nie ujawniamy istnienia klienta; test API przyjmuje 403 albo 404, żeby zmiana polityki nie wymagała zmiany testu |
| 2 | §9 przykład: klient ważący się raz w tygodniu widzi średnią | średnia 7-dniowa wymaga **≥ 3 pomiarów w oknie 7 dni** (§6.1 „min. 3 pomiary”) — przy ważeniu raz w tygodniu kafelek pokazuje „za mało pomiarów”, trend z 28 dni liczy się dopiero przy ≥ 6 pomiarach | §6.1 i §9 są ze sobą sprzeczne; wybrałem regułę liczbową, bo chroni przed „średnią” z jednego pomiaru; UI mówi wprost, ile pomiarów brakuje |
| 3 | §8.1 REPS_AT_WEIGHT | rekord powtórzeń tylko, gdy ten sam ciężar był już wcześniej wykonywany (pierwsze wykonanie przy nowym ciężarze = punkt odniesienia) | spójne z zasadą „pierwsza sesja nie jest rekordem”; inaczej każda zmiana ciężaru dawałaby „rekord” |
| 4 | §8.2 cofnięcie rekordu po edycji/usunięciu sesji | przeliczenie **przy zapisie** sesji i w backfillu; endpointów edycji/usuwania sesji **nie ma** w aplikacji | nie dodaję nowych ścieżek zapisu poza zakresem; gdy powstaną, wywołują `postepy.serwis.przelicz_klienta` |
| 5 | §12 backfill na kopii produkcji przed włączeniem | raport z seedu (1 klient z sesjami — A, 3 sesje, 0 bliźniaków); na produkcji do wykonania **po włączeniu flagi**: `python -m dzik_os.recalculate_progress --json` na maszynie Fly | z tego środowiska nie ma dostępu do produkcji (i nie eksportujemy danych klientów) |
| 6 | §7 nawigacja trenera | trener dostaje **szóstą** pozycję „Monitoring” (Klienci, Szablony, Wiedza, Monitoring, Wiadomości, Więcej) | spec nie mówi, co usunąć; szerokość 320 px sprawdzona (a11y: obszar dotykowy ≥ 44 px) |
| 7 | §6.4 realizacja diety | procent dni z zapisanym dziennikiem (`kcal` ≠ null) z 28 dni — tylko gdy klient ma aktywną dietę | brak w danych innego sygnału „realizacji” niż wpis dziennika |
| 8 | §7.1 progi | progi w zapytaniu (`?dni_bez_treningu=…`), **nie zapisywane** per trener | brak modelu ustawień trenera; zapis to osobna, mała runda, jeśli właściciel chce |
| 9 | §12 „records paginowane” | `/api/monitoring/records` zwraca całość (wstęga ≤ 5, lista ćwiczeń, archiwum) | przy dziesiątkach ćwiczeń odpowiedź jest mała; paginacja, gdy pojawi się realny klient z setkami ćwiczeń |
| 10 | status sesji `PARTIAL` | liczy się jak wykonana (do tygodnia, frekwencji, tonażu); `SKIPPED` nie liczy się | interfejs zapisuje dziś tylko `DONE`; czy `PARTIAL` ma liczyć się „za pół” — decyzja właściciela |
| 11 | §6.4 „najdłuższa seria” | liczona w oknie 12 tygodni (jak wykres), nie z całej historii | jedna ścieżka danych; historyczna seria wymaga osobnego zapytania po wszystkich agregatach |
| 12 | §7.2 zmiany planu „na tle tonażu” | lista dat pod wykresem tonażu, nie znaczniki na wykresie; notatki trenera jako lista pod wagą | prostszy SVG bez biblioteki wykresów; znaczniki na osi czasu — kolejna iteracja |

## Włączenie na produkcji (kolejność)

1. `DZIK_MONITORING_TAB_ENABLED=true` w `fly.toml` (`[env]`) albo jako
   sekret; deploy.
2. Na maszynie: `python -m dzik_os.recalculate_progress --json` —
   jednorazowo; wynik (liczba rekordów, tygodni, lista bliźniaków)
   zachować w notatce z wdrożenia.
3. Sprawdzić u klienta z flagą zdrowotną (jeśli jest), że `/monitoring`
   nie pokazuje „Sylwetki” ani trendu wagi.
4. Wyłączenie = usunięcie flagi; dane w tabelach z migracji 36 zostają
   (nieużywane).

## Świadomie poza zakresem (§5 spec)

Rekordy TIME/DISTANCE (kolumna `record_type` gotowa), porównania między
klientami, wnioski AI, eksport PDF, push o rekordzie (tylko w aplikacji),
zmiany w logice raportu tygodniowego, zapis progów per trener.

## Znaleziska P2 z przeglądu PR #61 (do rozważenia, nie blokują)

Przegląd: 3 recenzentów (backend, frontend, dane/dokumenty/CI). P0 (1) i P1 (14)
naprawione w tej samej rundzie; poniżej to, co zostało świadomie.

* `postepy/serwis.py` — `grupy_miesniowe` czyta bazę ćwiczeń **wszystkich**
  trenerów (pierwsza nazwa wygrywa); etykieta grupy może pochodzić z katalogu
  innego trenera. Bez wycieku danych; ograniczyć do trenerów klienta.
* `po_zapisie_sesji` robi pełne skany historii klienta (sesje + wpisy) przy
  każdym zapisie; wynik ograniczony do dotkniętych ćwiczeń/tygodnia, odczyt nie.
* `recalculate_progress` — jedna transakcja na wszystkich klientów (przerwanie
  cofa całość); `ExerciseRecord.id` zmienia się przy każdym przeliczeniu — nie
  traktować jako stabilnego odnośnika; backfill bez zdarzenia audytu.
* `routers/records.py` — dzień z samymi seriami > 10 powt. daje `e1rm_kg: 0.0`
  (wcześniej wartość) na starym wykresie siły; filtry `incomplete`/`assisted`
  między `personal-records` a `strength-series` niejednolite.
* Test `< 300 ms` dla 2 lat historii — ryzyko niestabilności na wolnym runnerze.
* Frontend: `PhotoCompare` wstawia `h2` wewnątrz sekcji „Sylwetka”; wyjaśnienie
  e1RM dostępne w treści (dopisek), pełna definicja tylko w `title`; konto z
  rolami COACH+CLIENT ma dwie trasy `/monitoring` (wygrywa klientowa);
  `features` w sesji odświeżają się przy logowaniu / `me` — wyłączenie flagi
  widać po ponownym zalogowaniu (do tego czasu 404 z komunikatem).
* Playwright: `PORT+1` bez sprawdzenia, czy wolny.
* a11y chodzi z włączoną flagą — stara strona „Monitoring i postępy” i stara
  nawigacja (stan produkcji do włączenia) nie mają już pokrycia a11y poza `h1`.
* `docs/INSTRUKCJA_*` używają cudzysłowów `„…"` (zamykający prosty) — konwencja
  tych plików, niespójna z CHANGELOG/PROGRESS (`„…”`).

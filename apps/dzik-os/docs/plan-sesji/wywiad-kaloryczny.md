# Plan sesji: wywiad „Zapotrzebowanie kaloryczne” wg specyfikacji właściciela 1.0 (0.77.0, migracja 42)

**Gałąź:** `agent/wywiad-kaloryczny` (od `main` = `4e516e1`, 0.75.1).
**Rola:** podległa sesja pisząca, wyznaczona przez integratora na polecenie właściciela
z 14.09.2026 („pracuj, aż rozwiążesz wszystkie zadania”). Katalog roboczy:
`/home/user/wt/wywiad-kal2` (osobny `git worktree`).
**Wersja:** 0.77.0. **Migracja:** 42 (addytywna).

**Protokół jednego piszącego (`KOORDYNACJA.md` §0, zarządzenie właściciela z 14.09):**
reguła „jeden PR `[WRITER]` naraz” nie obowiązuje, dopóki piszący jest jeden. Równolegle
trwa runda `agent/bloki-jak-szablony` (0.76.0, migracja 41, PR #79) — **scala się PRZED
tą gałęzią**. Po jej scaleniu dociągam `main` i pilnuję, żeby sekcja 0.77.0 w CHANGELOG-u
została **nad** 0.76.0 (kontrola `changelog` wymaga wersji nierosnąco w kolejności).

## Cel (słowami właściciela, spec 1.0 z 13.09)

> Nowy wywiad […] zbiera dane potrzebne do policzenia zapotrzebowania energetycznego
> klienta i wylicza **bilans kaloryczny**: podstawową przemianę materii (PPM), całkowitą
> przemianę materii (CPM), cel kaloryczny po uwzględnieniu celu sylwetkowego oraz
> proponowane makro.

Materiał źródłowy w drzewie (`docs/calorie-interview/`, dołączony do tego commitu):
`wywiad_zapotrzebowanie_kaloryczne.md` (specyfikacja 1.0, 239 linii),
`calorie_calc.py` (referencyjna implementacja wzorów, 120 linii),
`01_rozpoznanie_spec_v1.md` (rozpoznanie luk spec vs. 0.62.0, zatwierdzone jako PR #71).

## Decyzje właściciela — obowiązujące, nie do reinterpretacji

Przyjęte przez integratora na podstawie §5 rozpoznania. Zapisuję je tutaj, bo Karta
współpracy §I mówi, że czego nie ma w repozytorium, tego dla następnej sesji nie ma.

1. **Ekran 5 (zdrowie) wchodzi w pełnym kształcie ze specyfikacji** (ciąża/karmienie,
   choroby metaboliczne, leki, brak miesiączki, wolne pole). Warunki: wszystkie pytania
   **opcjonalne**, każde z odpowiedzią „wolę nie odpowiadać”, dostęp trenera przez
   istniejącą zgodę **`DOMAIN_HEALTH`** (brak zgody = trener nie widzi odpowiedzi, tylko
   informację, że wywiad zawiera dane zdrowotne — zgód się nie obchodzi), wpisy
   w `docs/DATA_PROCESSING_MAP.md` i `docs/RODO_DPIA.md`. Klient zawsze widzi swoje
   odpowiedzi.
2. **Reguła ukrywania liczb zostaje szersza niż w spec:** „nie wiem” i „wolę omówić
   z trenerem” dalej ukrywają wynik kaloryczny (dziś tak jest — nie zawężam do samego
   „tak”). Uzasadnienie w `docs/WYWIAD.md` i `PROGRESS.md`: zawężenie odsłoniłoby liczby
   części klientów już obsługiwanych na produkcji, a koszt błędu jest niesymetryczny.
3. **Stare wyniki 0.62.0 zostają jako historia** z `formulas_version = "0.62.0-pal"`; nie
   przeliczam ich (brak danych wejściowych: rodzaj/czas/intensywność treningu, % tłuszczu).
   Nowy wynik dopiero przy nowym przesłaniu; klient widzi zachętę do ponownego wypełnienia
   — bez nachalności i bez blokady.
4. **Zostajemy przy wieku** (bez daty urodzenia — mniej danych). Zakres 16–90 wg spec,
   flaga `MALOLETNI` z wieku < 18.
5. **Monitoring (`routers/postepy.py`) dalej reaguje na `ZABURZENIA_ODZYWIANIA`** (ukrycie
   trendu wagi) — zachowuję tę pochodną przy przejściu na `flags[]`. `MALOLETNI` **nie**
   ukrywa trendu wagi (flaga informacyjna dla trenera).
6. **Minimalne kcal 1200 (K) / 1500 (M)** wg spec, bez zmian; poniżej progu — twarda flaga
   i komunikat, że plan wymaga konsultacji.
7. **Przy rozbieżności spec vs `calorie_calc.py`: `calorie_calc.py` rozstrzyga liczby,
   spec rozstrzyga teksty i układ ekranów.** Każdą rozbieżność wypisuję
   w `docs/calorie-interview/PROGRESS.md`.

## Rozpoznanie własne (stan `main` `4e516e1`, z liniami)

* **Silnik dzisiaj:** `backend/dzik_os/wywiad/zapotrzebowanie.py` (247 linii) — PPM Mifflin
  zgodny ze spec, dalej PAL addytywny (praca 1,2/1,35/1,5/1,7 + treningi 0…+0,35 + kroki
  −0,05…+0,1, clamp 1,2–1,9), korekty −10/−15/−20 i +5/+10, podłoga = PPM, zaokrąglenie do
  10 kcal, `podstawienie` jako gotowe wiersze tekstu. Nie ma: Katch-McArdle, TEF, MET,
  zakresu ±7 %, makra, tempa kg/tydz., flag (jeden bool), BMI.
* **Serwis bazy:** `wywiad/zapotrzebowanie_serwis.py` — `przelicz_po_przeslaniu` (wywołanie
  z `wywiad/serwis.py:394`), `widok(est, viewer=…)` z filtrem serwerowym, `nadpisz`
  (audyt `CALORIE_ESTIMATE_OVERRIDDEN`), `odblokuj` (`CALORIE_ESTIMATE_UNHIDDEN`).
  Nadpisanie i odblokowanie **zostają bez zmian semantycznych** — to już jest w spec §6.2.
* **Model:** `models.py:2028` `CalorieEstimate` (migracja 33): `inputs_json`, `ppm`, `pal`,
  `cpm`, `korekta_pct`, `kcal`, `podstawienie_json`, `ostrzezenia_json`,
  `hidden_for_client`, `unhidden_*`, `override_*`. Brak `formulas_version`.
* **Definicje pytań:** `wywiad/definicje.py:338–420` — 4 sekcje, 11 pytań `zk_*`, rodzaj
  `KIND_NUMBER` z `zakres`, pytania warunkowe przez `_zapotrzebowanie_triggered`,
  `flag_options` → `serwis._flaga_bezpieczenstwa` → `InterviewSubmission.safety_flag`.
  `WERSJA = 1` jest **wspólna dla trzech typów wywiadu** — podbicie dotknie też wstępnego
  i głębokiego (sprawdzić skutki w `test_wywiad_zakladka.py`; jeśli wspólna wersja miałaby
  unieważnić cudze przesłania, dokładam osobną wersję per definicja — decyzja w etapie 3).
* **Monitoring:** `routers/postepy.py:93` `_flaga_zdrowotna` czyta `est.hidden_for_client`
  (zostaje), `:399–404` buduje `cele` z `inputs_json["cel"]` i porównuje z `"redukcja"`
  (`:453`). **Znalezisko:** silnik 0.62.0 zapisuje tam etykietę „Redukcja masy ciała”, więc
  sygnał `goal_mismatch` nigdy nie zapala się na produkcji; zielony test
  (`test_postepy_api.py:46`) wstawia wiersz ręcznie z wartością `"redukcja"`, której kod
  nie produkuje. Naprawiam przy okazji (kod celu w `inputs_json` + zgodność wstecz
  z etykietą), bo i tak zmieniam kształt tego pola — zgłoszone w PROGRESS.
* **Eksport RODO:** `routers/privacy.py:360` zrzuca `calorie_estimates` **generycznie**
  (`_rows` = wszystkie kolumny tabeli). Nowe kolumny wejdą do eksportu same →
  **`export_version` zostaje „2.1”** (kształt eksportu się nie zmienia, zmienia się liczba
  kolumn zrzucanej tabeli — tak samo jak przy migracjach 34/36/38). Dokładam test, że nowe
  pola faktycznie są w eksporcie.
* **Front:** `frontend/src/pages/wywiad/Zapotrzebowanie.tsx` (170 linii, jedna karta,
  tryb klient/trener) używana w `client/Wywiad.tsx:70`, `client/Nutrition.tsx:62`,
  `coach/WywiadTab.tsx:81`, `coach/ClientDetail.tsx:840` (zakładka Dieta) oraz
  `coach/PrzypiszDiete.tsx:428` (`ZaproponujKcal`). Typy: `types.ts:1926–1960`.
* **Testy:** `test_zapotrzebowanie_silnik.py` (101 l.), `test_zapotrzebowanie_api.py`
  (283 l.), `test_wywiad_zakladka.py` (658 l., liczby pytań), `test_postepy_api.py`
  (300 l.), `access_matrix.py:244–246`, E2E `frontend/e2e/zapotrzebowanie.spec.ts`
  (1670 → 1800 kcal).

## Rezerwacje (sprawdzone na żywo 14.09, PR-y otwarte: tylko #79)

| Zasób | Rezerwacja |
|---|---|
| Wersja | **0.77.0** (0.76.0 = runda bloków, PR #79) |
| Migracja | **42** (41 = runda bloków) |
| `export_version` | **zostaje „2.1”** (uzasadnienie wyżej) |
| Porty E2E | 8150 / 8151, `DZIK_E2E_DIR=/tmp/dzik-e2e-8150` |
| Gałąź | `agent/wywiad-kaloryczny`, PR `[WRITER]` do `main` |

**Pliki współdzielone z rundą bloków — moje sekcje:** `db.py` wpis 42 **na końcu**;
`models.py` wyłącznie `CalorieEstimate`; `schemas.py` — nic (runda bloków rusza bloki/cardio);
`tests/access_matrix.py` — wyłącznie wiersze `/zapotrzebowanie`; `types.ts` — wyłącznie blok
„Zapotrzebowanie kaloryczne”; `ClientDetail.tsx` — wyłącznie zakładka Wywiad/Dieta (NIE karta
„Przypisz plan”); CHANGELOG / STAN / RELEASE_STATUS — własne sekcje na górze.
**Nie dotykam:** `routers/plans.py`, `routers/exercise_blocks.py`, `PlanEditor.tsx`,
`pozycje.tsx`, `hos_engine/`, `tests/` w korzeniu (275 testów).

## Etapy (bramka po każdym; commit i push po każdym, także przy bramkach w toku)

| # | Etap | Nakład | Co powstaje |
|---|---|---|---|
| 0 | plan sesji + materiał źródłowy właściciela | mały | ten plik, `docs/calorie-interview/*` |
| 1 | **silnik** 1:1 z `calorie_calc.py` | średni | PPM Mifflin + Katch, `ppm_used`/`ppm_source`, NEAT (opis albo kroki), kcal treningu z MET, TEF, `cpm_min/max` (±7 %), cel kaloryczny z podłogą, tempo i czas, makro, flagi, `formulas_version`; testy z kryteriów akceptacji spec §7 i z `__main__` referencji jako wektory |
| 2 | **model + migracja 42 + API** | średni | 15 kolumn addytywnie, `formulas_version="0.62.0-pal"` dla istniejących wierszy, zapis wyniku, widok klienta/trenera, bramka `DOMAIN_HEALTH` na odpowiedzi zdrowotne, flagi w odpowiedzi, `access_matrix`, `PERMISSIONS.md` |
| 3 | **definicje pytań** | średni | 5 ekranów wg spec §4, pytania warunkowe, `definition_version` podbity, stare `zk_*` odfiltrowane przy odczycie, wersjonowanie szkiców (409) nietknięte |
| 4 | **UI** | duży | widok klienta „Bilans kaloryczny” (§6.1) i trenera (§6.2, rozbicie CPM z podstawieniem), makro, flagi, komunikat przy ukryciu; dwa motywy (tokeny), 320 px, a11y |
| 5 | **testy i dokumenty** | duży | przepisane 4 pliki testów + E2E, kryteria akceptacji §7 jako testy, CHANGELOG 0.77.0, `WYWIAD.md`, `DATA_PROCESSING_MAP.md`, `RODO_DPIA.md`, `PERMISSIONS.md`, instrukcje trenera i klienta, `E2E.md`, STAN §1+§2, RELEASE_STATUS, `zlecenia/README.md`, `docs/calorie-interview/PROGRESS.md` |

## Czego NIE robię (świadomie poza zakresem tej rundy)

* **P1 ze spec §7:** przypomnienie o ponownym wypełnieniu po zmianie masy > 3 kg lub po
  8 tygodniach; wykres masy i CPM w czasie. (Zachęta do ponownego wypełnienia z decyzji 3
  wchodzi — ale jako statyczny komunikat przy wyniku `0.62.0-pal`, nie jako mechanizm
  przypomnień.)
* **P2 ze spec §3/§7:** import kroków z zegarka (pole „kroki” przygotowane), adaptacja
  kalorii z ważeń.
* Przeliczanie starych wyników (decyzja 3), data urodzenia (decyzja 4).
* Edytowalne w bazie szablony wywiadów (rozpoznanie §3 — definicje zostają w kodzie).
* `hos_engine/` i `tests/` w korzeniu — poza zasięgiem pracy aplikacyjnej.

## Bramki

```bash
ruff check apps/dzik-os/backend apps/dzik-os/tools      # liczy się BRAK NOWYCH błędów
cd apps/dzik-os/backend && PYTHONPATH=. python -m pytest -q
cd apps/dzik-os && python3 tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py ; python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
cd apps/dzik-os/frontend && npx tsc --noEmit -p . && npm run build && npm run test:helpers
DZIK_E2E_PORT=8150 DZIK_E2E_DIR=/tmp/dzik-e2e-8150 npx playwright test zapotrzebowanie --project=telefon
cd apps/dzik-os && NODE_PATH=<worktree>/apps/dzik-os/frontend/node_modules node e2e/test_a11y.mjs   # + DZIK_THEME=czerwony
```

Budżet frontu: 120 kB gzip. **Nigdy `git add -A`, gdy działają narzędzia mutacyjne** —
mutują pliki; po nich drzewo ma być czyste poza moimi zmianami.

## Odstępstwa od planu

(uzupełniane w trakcie rundy)

## Plan kontra rzeczywistość

(uzupełniane na koniec rundy — co trwało dłużej, co okazało się inne niż w rozpoznaniu)

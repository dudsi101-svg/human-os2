# Rozpoznanie: specyfikacja „Zapotrzebowanie kaloryczne” 1.0 (13.09) vs. implementacja 0.62.0

> Etap 0 przyszłej rundy „wyrównanie wywiadu kalorycznego do specyfikacji właściciela”
> (paczka z 14.09: `docs/calorie-interview/wywiad_zapotrzebowanie_kaloryczne.md`,
> `calorie_calc.py`). Tylko odczyt kodu na `main` 0.67.0; żadnej zmiany w kodzie.
> **Runda czeka na decyzje właściciela z §5** — bez nich nie da się zaplanować migracji
> ani zakresu danych zdrowotnych.

## 1. Sedno

Wywiad 0.62.0 (`wywiad/zapotrzebowanie.py`, flaga `DZIK_CALORIE_INTERVIEW_ENABLED`, na
produkcji włączona) liczy **CPM = PPM × PAL** (praca + treningi + kroki, clamp 1,2–1,9),
korekty −10/−15/−20 % i +5/+10 %, podłoga „nie poniżej PPM”. Spec 1.0 żąda **CPM
addytywnego**: `PPM · NEAT + trening z MET + TEF 10 %`, zakres ±7 %, Katch-McArdle przy
% tłuszczu, korekty −10/−20/−25 % i +5/+10/+15 %, rekompozycja −5 %, podłoga
`max(PPM·1,1; 1200 K / 1500 M)`, makro startowe w gramach, tempo kg/tydzień, siedem flag.
To zmiana pytań (5 ekranów, ~20 pól zamiast 11), silnika, modelu (migracja) i testów.

## 2. Tabela luk (spec → stan → gdzie → różnica)

| Element spec | Stan | Gdzie | Różnica |
|---|---|---|---|
| E1 płeć | jest | `wywiad/definicje.py:366` | etykiety PL zamiast `F/M` |
| E1 data urodzenia, wiek 16–90, flaga < 18 | brak | `zk_wiek` (`definicje.py:368`, zakres 14–100) | zbierany wiek w latach (decyzja „mniej danych”, `WYWIAD.md` §8); brak obsługi małoletniego |
| E1 wzrost / masa | częściowo | `definicje.py:370-374` | zakresy 120–230 / 30–300 vs 130–230 / 35–250 |
| E1 % tkanki tłuszczowej | brak | — | brak pytania i LBM |
| E2 NEAT 4 opcje | częściowo | `zk_praca`, `PRACA` (`zapotrzebowanie.py:28-33`) | mnożniki 1,20/1,35/1,50/1,70 zgodne, ale wchodzą do PAL; inne opisy |
| E2 kroki (liczba nadpisuje) | częściowo | `zk_kroki`, `KROKI` (`:43-49`) | 4 przedziały + „Nie wiem” → korekta PAL; brak wzoru `1,20 + 0,04·(kroki/1000 − 4)` |
| E3 trening (rodzaj, sesje, minuty, intensywność, staż) | brak | `zk_treningi` (jedno pytanie o przedział) | brak wejść do MET |
| E4 cel (4) | częściowo | `CELE` (`:52-55`) | brak rekompozycji |
| E4 tempo | częściowo | `TEMPO_*` (`:57-65`) | −10/−15/−20 vs −10/−20/−25; +5/+10 vs +5/+10/+15 |
| E4 masa docelowa, preferencja białka | brak | — | — |
| E5 sześć pytań zdrowotnych | częściowo | `zk_zaburzenia` (`definicje.py:395-401`, `DOMAIN_HEALTH`, `sensitive`) | tylko zaburzenia odżywiania (4 opcje); brak ciąży, chorób, leków, miesiączki, wolnego pola |
| 5.1 Mifflin | jest | `zapotrzebowanie.py:126-131` | identyczny |
| 5.1 Katch + reguła 10 % | brak | — | — |
| 5.2 CPM addytywny, TEF, ±7 % | brak | `:134-152, 202` | PAL |
| 5.3 podłoga i `DEFICYT_OGRANICZONY` | częściowo | `:70-71, 206-211` | podłoga = PPM, ostrzeżenie tekstowe |
| 5.3 `DEFICYT_WYLACZONY` | brak | — | — |
| 5.4 tempo, staż, czas do celu | brak | — | — |
| 5.5 makro | brak | makro liczy tylko moduł diety (`routers/diet.py:102-118`) | wywiad nie zwraca makra |
| 6.1 widok klienta | częściowo | `pages/wywiad/Zapotrzebowanie.tsx:86-101` | brak zakresu CPM, makra, tempa |
| 6.2 widok trenera (oba PPM, rozbicie, flagi) | brak | `Zapotrzebowanie.tsx:103-165` | jest podstawienie krok po kroku |
| 6.2 historia | częściowo | `routers/zapotrzebowanie.py:41-44` | jedna linia „v1 — 1670 kcal” |
| 6.2 „Użyj w przypisaniu diety” | częściowo | `PrzypiszDiete.tsx:200, 423-437` | przenosi kcal i masę, nie makro/wykluczenia |
| 6.2 nadpisanie z powodem | **jest** | `zapotrzebowanie_serwis.py:107-126` | kolumny `override_*`, audyt `CALORIE_ESTIMATE_OVERRIDDEN` |
| 6.3 zapis wersjonowany | częściowo | `CalorieEstimate` (`models.py:2007-2035`, migracja 33) | `version_no`, wejścia i podstawienie zamrożone; **brak `formulas_version`** |
| 6.4 lista flag | brak | jeden bool `hidden_for_client` | — |
| 6.4 ukrycie liczb przy zaburzeniach | jest (surowiej) | `zapotrzebowanie_serwis.py:58, 94-104` | klient dostaje `status="hidden"`, zero pól |
| 6.4 zakres flagowania | szerszy niż spec | `definicje.py:400` | ukrywa też „Nie wiem” i „Wolę omówić z trenerem”; trener może odblokować (`POST …/odblokuj`) |
| 6.4 MALOLETNI, CIĄŻA, CHOROBA, LEKI, MIESIĄCZKA, BMI | brak | — | BMI nieliczone |
| P1 przypomnienie (> 3 kg / 8 tyg.), wykres masy i CPM | brak | Monitoring ma trend wagi | — |
| Kryteria akceptacji 1780 / 1345 | wzór zgodny | — | pozostałe (1752, 180, 2548, 1480) — brak |

## 3. Odpowiedź na pytanie otwarte spec §8

**Wersjonowanie wywiadów: jest** (`InterviewSubmission` z `version_no`, `definition_version`,
`UniqueConstraint(client_id, typ, version_no)`; `InterviewDraft` z `revision` i 409 przy
konflikcie; `definicje.WERSJA`). **Szablonów edytowalnych w bazie: nie ma** — definicje
pytań są w kodzie (`definicje.DEFINICJE`), nowy wywiad = nowy typ w `TYPY` +
`wywiady.typy_aktywne`. Brakuje jednej osi: wersji wzoru (`formulas_version`).

## 4. Zakres migracji i testów

- Ostatnia migracja: **36**. Następna wolna: **37 — ale zarezerwowana dla „dni treningowych”**
  (`docs/zlecenia/README.md`); ta runda dostałaby **38** (po dniach treningowych).
- `calorie_estimates`: dodać `formulas_version`, `ppm_mifflin`, `ppm_katch`, `ppm_used`,
  `ppm_source`, `neat_multiplier`, `training_kcal_day`, `tef`, `cpm_min`, `cpm_max`,
  `target_kcal`, `macro_json`, `flags_json`, `expected_weekly_change_kg`, `bmi`; stare
  kolumny zostają (historia). Istniejące wiersze: `formulas_version = "0.62.0-pal"`.
- `interview_submissions.definition_version` / szkice ze starymi `zk_*` (odfiltrować przy odczycie).
- Testy do przepisania: `test_zapotrzebowanie_silnik.py` (6 z 10), `test_zapotrzebowanie_api.py`
  (7 z 12), `test_wywiad_zakladka.py` (liczby pytań), `access_matrix.py`, `test_postepy_api.py`
  (flaga), E2E `zapotrzebowanie.spec.ts` (≈ 1670 / 1800 kcal).

## 5. Decyzje właściciela (blokują rundę)

1. **Dane szczególnej kategorii.** Ekran 5 dokłada 5 pytań zdrowotnych (ciąża, choroby
   metaboliczne, leki, brak miesiączki, wolne pole) i 6 nowych flag widocznych trenerowi.
   Decyzja z `WYWIAD.md` §8 obejmuje dziś tylko liczbę kcal i jedną flagę pochodną. Czy
   nowe pytania i flagi wchodzą (zgoda `DOMAIN_HEALTH`, wpis w `DATA_PROCESSING_MAP.md` /
   `RODO_DPIA.md`), czy ekran 5 zostaje w dzisiejszym kształcie (jedno pytanie)?
2. **Zakres flagowania.** Dziś liczby ukrywają też odpowiedzi „Nie wiem” i „Wolę omówić
   z trenerem”; spec flaguje tylko „tak”. Zawężenie odsłoni liczby części klientów na
   produkcji. Zostawić szerszą regułę (proponuję) czy wyrównać do spec?
3. **Stare wywiady 0.62.0 nie dają się przeliczyć** nowym wzorem (brak rodzaju/czasu/
   intensywności treningu, % tłuszczu, daty urodzenia). Proponuję: zostają jako historia
   z `formulas_version = "0.62.0-pal"`, nowy wynik tylko przy nowym przesłaniu; klient
   dostaje prośbę o ponowne wypełnienie. Zgoda?
4. **Data urodzenia zamiast wieku** — odwraca decyzję „mniej danych” z 0.62.0 (wiek
   wystarcza do wzoru; data potrzebna tylko do flagi < 18 i przypomnień). Proponuję: zostać
   przy wieku, flaga `MALOLETNI` z wieku (< 18), zakres 16–90 wg spec.
5. **Flaga zdrowotna a Monitoring 0.66.0**: `hidden_for_client` czyta też `routers/postepy.py`
   (ukrywa trend wagi). Nowe `flags[]` muszą zachować tę pochodną — potwierdzenie, że
   Monitoring ma dalej reagować na ZABURZENIA_ODZYWIANIA (i czy także na MALOLETNI?).
6. **Kolejność rund**: dni treningowe (migracja 37, prompt nadal nieprzesłany) przed tą
   rundą (migracja 38)? Jeśli prompt dni treningowych nie nadejdzie, tę rundę można
   puścić pierwszą z migracją 37 — wymaga zmiany rezerwacji w `docs/zlecenia/README.md`.
7. Minimalne kcal 1200 K / 1500 M — spec zostawia dietetykowi; przyjąć bez zmian?

## 6. Szacunek (po decyzjach)

Silnik (czysta funkcja 1:1 z `calorie_calc.py` + testy kryteriów akceptacji): mały.
Definicje pytań + walidacja + szkice/wersje: średni. Migracja 37/38 + serwis + API
(flagi, widoki klient/trener, „Użyj w przypisaniu diety” z makro): średni. Front (5 ekranów,
dwa widoki bilansu, historia): duży. Dokumentacja RODO/PERMISSIONS/WYWIAD §8: mały.
Największy koszt: front + przepisanie 13 testów. Razem: jedna pełna runda (porównywalna
z 0.62.0 + 0.66.0 razem), bez P1 (przypomnienia, wykres).

# Plan sesji: wymiany produktów v2 — grupy pokrewne, zgodność funkcji w posiłku, bramka „nie pogarsza”, przycisk dla roli NONE (0.69.0 — propozycja, patrz Rezerwacje)

> Szkic właściciela (`docs/zlecenia/plan-sesji_wymiany-produktow.md`) uzupełniony przez sesję
> piszącą 14.09 — pola sprawdzone na żywo.

**Warunek startu:** `agent/biblioteka-diet` scalona do `main` (PR #66, `cbfa893`, 14.09 — spełniony). Bez tego STOP.
**Gałąź:** `agent/wymiany-produktow` (od `main` = `cbfa893`, po 0.64.0). **Rola:** aktywny
piszący — polecenie właściciela z 14.09.2026 („przycisk wymiany produktu w zakładce Dieta
nie działa; trzeba powiązać pokrewne grupy towarowe, by makro i funkcja w posiłku się
zgadzały”), plik `PROMPT_writer_wymiany-produktow.md` (diagnoza z pomiarem, rozpoznanie,
decyzje, tabela powiązań).
**Rezerwacje (KOORDYNACJA §0):** wersja **0.69.0** (propozycja wg kolejności scalania z `docs/zlecenia/README.md`: 0.66.0 = Postępy PR #61, 0.67.0 = ukryj kreator PR #68, 0.68.0 = dni treningowe/migracja 37 — jeśli tamta runda nie wystartuje przed scaleniem tej, biorę 0.68.0 i wpisuję tu i w §2; 0.65.0 zarezerwowane dla strony publicznej PR #67); migracja **brak**
(plik danych + logika; jeśli okaże się potrzebna kolumna — kolejny wolny numer, wpisany tu
i w `STAN_PRZEKAZANIA.md` §2). Pliki współdzielone: `dieta/silnik.py`, `dieta/serwis.py`,
`dieta/seed.py`, `routers/diet.py`, `dieta/dane/` (nowy `grupy_pokrewne.json`),
`pyproject.toml`/`package-data`, `types.ts` (typy diety), `DietaSzablon.tsx`, panel szablonów
trenera, `CHANGELOG.md`.

## Co robimy

1. **Pomiar przed** (skrypt w `tools/` albo test-strażnik) — odsetek składników bez kandydata
   przy 1600/2000/2600 kcal na `main` po bibliotece (oczekiwane ~11 % przy 2000).
2. **Dane:** `grupy_pokrewne.json` z tabelą z promptu (§5), walidowany, w `package-data`;
   **korelacja katalogu trenera** (§5a promptu): `tools/koreluj_katalog.py` → CSV propozycji
   do przeglądu właściciela; zatwierdzone wiersze → `produkty_z_katalogu.csv` w seedzie.
3. **Silnik:** `swap_candidates` v2 — poziom 1 (ta sama grupa) + poziom 2 (grupa pokrewna);
   funkcja w posiłku = rola makro dominująca + `cooking_tags` (pusty = wildcard) + limity
   porcji; bramka posiłku „w tolerancji ALBO nie pogarsza”; `tier`, `meal_delta`, statystyka
   odrzuceń z powodami.
4. **Rola NONE:** przycisk i wymiana 1:1 wagowo w tej samej grupie; `swappable` efektywne
   przy odczycie (stare migawki bez przepisywania).
5. **API/UI:** GET `/swaps` z `reason`/`rejected`/`tier`/`meal_delta`; arkusz klienta
   z etykietą poziomu, deltą i 5 komunikatami pustej listy; panel trenera — tabela powiązań
   tylko do odczytu; historia wymian z poziomem.
6. **Pomiar po** + test-strażnik pokrycia z progiem wpisanym z pomiaru.

## Decyzje projektowe (właściciel 14.09 + wykonawcze)

* `TOL_MEAL`/`TOL_DAY` bez zmian (test stałych). Bramka „nie pogarsza” działa tylko
  na ścieżce wymiany.
* Alergeny/wykluczenia/„nie lubię” filtrowane **przed** poziomem 2 — poziom 2 nie może
  przemycić alergenu (test).
* Powiązania to **propozycja do przeglądu trenera/dietetyka** (`status`, `reviewed_by`);
  pary (?) domyślnie `enabled: false`.
* Silnik przestaje być 1:1 z prototypem w `swap_candidates` — jawnie w docstringu,
  `PROGRESS.md`, CHANGELOG.
* POST nadal liczy kandydatów serwerowo; blokady trenera bez zmian.
* Zero AI; wynik deterministyczny (test).
* Plan z kreatora (`NutritionPlan`) poza zakresem (kreator ukrywa zlecenie 3); katalog
  `FoodProduct` **nie** jest źródłem kandydatów w czasie działania — tylko przez
  przeglądany import do `DietProduct`.

## Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie + pomiar przed | linie z promptu (`silnik.py` 361–396, `serwis.py` 252–270, `routers/diet.py` 325–423, `seed.py` ~234, `DietaSzablon.tsx` 37–108, testy l. 152/194/231), stan po bibliotece | `docs/diet-module/wymiany_v2_rozpoznanie.md` z tabelą pomiaru + ten plan | skrypt pomiaru uruchomiony, liczby w pliku | dziesiątki tys. |
| 1 dane | `produkty.csv` (grupy, słowniki tagów/alergenów), `subst_maps.json`, `food_catalog_data.FOOD_ROWS_ALL` | `grupy_pokrewne.json`, `dieta/grupy.py`, `tools/koreluj_katalog.py` + `docs/diet-module/katalog_korelacja_propozycja.csv` (do przeglądu właściciela), wpis `package-data` | `test_pakietowanie`, test walidacji pliku (grupy istnieją, symetria, brak duplikatów), `test_koreluj_katalog.py` | setki tys. |
| 2 silnik | `silnik.py`, `check`, limity v1.1 | `swap_candidates` v2 + statystyka odrzuceń | `test_dieta_silnik.py` (aktualizacja złotej listy z powodem; nowe przypadki), determinizm | setki tys. |
| 3 serwis + API + seed | `serwis.py`, `routers/diet.py`, `seed.py`, `dieta_out` | `reason`/`rejected`/`tier`/`meal_delta`, `swappable` efektywne, `tier` w historii | `test_dieta_api.py`, `test_dieta_poprawki.py`, macierz dostępu (bez nowych tras) | setki tys. |
| 4 UI | `DietaSzablon.tsx`, `types.ts`, panel szablonów, historia wymian trenera | arkusz v2, komunikaty, tabela powiązań RO, E2E na składniku pustym na `main` | `tsc`, build (budżet), `test:helpers`, E2E `dieta-szablon.spec.ts`, obejrzenie przez serwer E2E | setki tys. (największy koszt) |
| 5a import zatwierdzonych | CSV z decyzjami właściciela | `dieta/dane/produkty_z_katalogu.csv` (tylko TAK), seed po głównym CSV, test integralności | pytest; jeśli przegląd nie zdąży — osobny mały PR po scaleniu | dziesiątki tys. |
| 5 pomiar po + strażnik | — | `tests/test_dieta_wymiany_pokrycie.py` (próg z pomiaru + margines, z datą) | pytest; tabela przed/po | dziesiątki tys. |
| 6 zamknięcie | — | CHANGELOG 0.69.0 (albo kolejna wolna), PROGRESS.md, instrukcja szablonów, INSTRUKCJE, BAZA_PRODUKTOW, RELEASE_STATUS, STAN_PRZEKAZANIA | pełny pytest, ruff z korzenia, spójność, mutacje, CI | dziesiątki tys. |

**Największy koszt:** etap 2 (silnik) i 4 (UI). Taniej bez utraty informacji: jedna
ścieżka liczenia kandydatów dla GET i POST (żadnej drugiej implementacji), komunikaty pustej
listy jako słownik `reason → tekst` w jednym miejscu, tabela powiązań RO jako zwykła tabela
z JSON-a (bez formularza). Bezpiecznik: 3× plan. Przegląd: 3 recenzentów wsadowo
(alergeny/wykluczenia/bezpieczeństwo, poprawność silnika i determinizm, testy/UX/treść).

## Czego nie dotykam

`TOL_MEAL`/`TOL_DAY`, `fit_*`, `enforce_groups`, `docs/diet-module/engine.py`, katalog
kreatora (`FoodProduct`, `food_catalog*`), `NutritionPlan`/`Nutrition.tsx`, migawki
istniejących przypisań (żadnego przepisywania danych), Core Human OS.

## Czego świadomie nie robię

Re-fit pozostałych składników po wymianie (v3), edycja powiązań w UI, przycisk wymiany
w planie z kreatora, zmiana tolerancji.

## Odstępstwa od planu

* Zakres `min/max_factor` składnika nie przeniesiony na kandydata (pomiar: 6/108 vs 3/108
  przy 2000 kcal; NONE 51/124 vs 3/124) — zostały twarde limity v1.1.
* Tabela powiązań w panelu bez nowej trasy (w `GET /api/diet/products`).
* Etap 5a (import zatwierdzonych wierszy) po przeglądzie CSV przez właściciela — osobny PR.
* Bramka „nie pogarsza” z luzem 5 kcal / 0,5 g (przegląd: literalna reguła odrzucała wymiany
  neutralne za zaokrąglenie gramatury) — właściciel może cofnąć jedną stałą.

## Weryfikacja wykonana

Pomiar przed/po (`tools/pomiar_wymian.py`, Standard v1, P/C/F z 108): 1600 kcal 20 → 7,
2000 kcal 12 → 3, 2600 kcal 18 → 9; NONE 2000 kcal: bez przycisku → 3/124 pustych.
Bramki: ruff, testy diety (87: silnik 26, API, poprawki, seed, grupy 7, korelacja 6,
strażnik 5, pakietowanie, macierz), tsc, build, E2E `dieta-szablon.spec.ts` (klient B:
kurczak → indyk, brokuł → warzywo z tej samej grupy 1:1 z deltą posiłku, awokado (dzień 2)
→ grupa pokrewna; trener: historia z poziomami). Uruchomienie przez serwer E2E — patrz PR.

## Plan kontra rzeczywistość (zasady v2 §5)

Etapy 0–5 wg planu; 5a (import) odłożony do przeglądu CSV. Największy koszt: silnik
(sita, powody, ranking) i dopasowanie E2E — zgodnie z planem. Usprawnienie: pomiar jako
narzędzie + strażnik z progiem z pomiaru zamiast „0 pustych list”. Przegląd: 3 recenzentów
wsadowo — P0/P1: `swappable` efektywne nadpisywało jawne `false` trenera (naprawione: tylko NONE),
gramatura z klienta omijała limity porcji (naprawione), CSV: białko serwatkowe bez alergenu
`mleko` (naprawione), bramka odrzucała wymiany neutralne za setne grama (luz — interpretacja
do potwierdzenia), docs „do 5” vs `n=3` (poprawione); P2 w PROGRESS. Lekcja: `git add -A`
w czasie działania narzędzi mutacyjnych zacommitowało mutację `sheet_import.py` (cofnięte).

## Odpowiedzi na pytania §9 promptu (domyślne, o ile właściciel nie zmieni)

1. CSV propozycji przegląda wstępnie właściciel, alergeny potwierdza trener.
2. Powiązania (?) wyłączone (`enabled: false`) do przeglądu trenera.
3. Bramka „nie pogarsza” (wymiana w posiłku poza tolerancją dozwolona, gdy nie pogarsza).
4. Warzywa `NONE` wymieniane 1:1 wagowo.

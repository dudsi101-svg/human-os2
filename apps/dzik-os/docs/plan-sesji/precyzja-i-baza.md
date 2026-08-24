# Plan sesji: precyzja gramatur + baza ×5

**Gałąź:** `agent/precyzja-i-baza` (od `main` = `f238242`)
**Rola:** aktywny piszący (feedback właściciela z produkcji, 24.08:
„kompozycje wyglądają dużo lepiej, brak jednak precyzji; powiększ
pięciokrotnie bazę składników")
**Cel:** dwie rzeczy z jednego zgłoszenia.

## Zamiar

1. **Precyzja kuchenna gramatur.** Kreator sypie wartościami typu
   „316,4 g" — nieodmierzalne. Zaokrąglanie praktyczne w `_pozycja`:
   <100 g → do 5 g, ≥100 g → do 10 g; produkt z jednostką → najpierw
   pół-jednostki („2 jajka", „1,5 kromki"), gramy z jednostek. Makra
   liczone z gramatury PO zaokrągleniu — sumy dnia uczciwe, dryf
   pojedynczego posiłku znikomy (test tolerancji zostaje).
2. **Baza składników ×5:** 410 → ~2000+ pozycji w tych samych 16
   kategoriach, w nowym pliku `food_catalog_data_ext.py` (doklejanym do
   `FOOD_ROWS`) — wartości uśrednione z tabel żywieniowych, markowo
   neutralne, konwencja nazw i not identyczna. Test spójności danych:
   liczność ≥2000, unikalność znormalizowanych nazw, zgodność
   kcal ≈ 4B+9T+4W w tolerancji, sensowne porcje.
3. Etykieta przycisku bez liczby na sztywno („Dograj wbudowaną bazę
   produktów") + liczność w komunikacie wyniku.

## Mój obszar

- `backend/dzik_os/diet_wizard.py` (zaokrąglanie),
  `backend/dzik_os/food_catalog_data.py` (doklejenie ext),
  `backend/dzik_os/food_catalog_data_ext.py` (nowy);
- `backend/tests/test_diet_wizard.py`, `backend/tests/
  test_food_catalog_data.py` (nowy — spójność bazy);
- `frontend/src/pages/coach/Knowledge.tsx` (etykieta);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- endpointów, modeli, migracji; mechaniki doboru (tylko zaokrąglenie
  wyjścia); Core.

## Rezerwacje

- **Wersja: 0.48.0.** **Migracja: brak.**

## Świadomie nie robię

- nie dodaję produktów markowych (katalog jest markowo neutralny —
  zasada z BAZA_PRODUKTOW.md zostaje);
- nie ruszam wartości istniejących 410 pozycji.

## Weryfikacja (wypełnione 24.08)

- **Odstępstwo od planu, jawne:** `FOOD_ROWS` NIE jest doklejane — seed
  demo i round-trip CSV (limit importu 1000 wierszy) zakładają pierwotne
  410 pozycji (3 testy czerwone przy doklejeniu). Pełna baza idzie nową
  stałą `FOOD_ROWS_ALL` (= 410 + ext), używaną przez load-builtin
  i dopełnianie kreatora; seed bez zmian.
- Baza: **2058 pozycji łącznie** (ext 1648), zero duplikatów po
  znormalizowanej nazwie (dwie partie autorskie odrzucone w całości jako
  kolizje — czyszczenie regeneracją pliku + filtr antykolizyjny przy
  generowaniu ostatnich partii).
- Pełne bramki z korzenia: ruff czysto (po `--fix` 2×RUF100);
  backend **809 zaliczonych, 1 pominięty** (w tym 5 nowych testów
  spójności bazy i 19 kreatora); Core 275; spójność 10 kontroli;
  mutacje 17/17; mutacje bezpieczeństwa 9/9; frontend tsc+build,
  helpers, E2E 15/15.
- Uruchomienie na żywo (uvicorn :8148, seed, `DZIK_MFA_REQUIRED_ROLES=""`;
  co uruchomiłem i co zobaczyłem): login trenera demo →
  `POST /coach/food-products/load-builtin` → **added=1649, skipped=409**,
  katalog total **2058**; `POST /coach/diet-wizard` (2200 kcal, 30/25/45,
  4 posiłki, 2 dni) → **wszystkie gramatury kuchenne** (kontrola
  programowa: sztuki wielokrotnością 0,5; gramy %5 poniżej 100 g, %10
  powyżej; zero odstępstw), dni 2324/2167 kcal, **0 ostrzeżeń** na
  pełnej bazie, sugestie przyrządzenia obecne.
- Test kcal↔makra ujawnił i uwzględnił dwie konwencje tabel (błonnik
  w węglowodanach albo netto — widełki C±błonnik) oraz energię spoza
  makr (alkohol, poliole — lista wyłączeń po nazwie).

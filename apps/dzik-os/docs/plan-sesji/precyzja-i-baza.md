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

## Weryfikacja (do wypełnienia)

- pełne bramki; test spójności nowej bazy; uruchomienie na żywo:
  gramatury odmierzalne (5/10 g, pół-jednostki), makra dnia w celu,
  load-builtin dogrywa powiększoną bazę.

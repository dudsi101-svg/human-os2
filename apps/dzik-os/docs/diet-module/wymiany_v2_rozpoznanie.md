# Wymiany produktów v2 — rozpoznanie etapu 0 i pomiar „przed” (14.09.2026)

Gałąź `agent/wymiany-produktow` od `main` `cbfa893` (0.64.0, biblioteka diet scalona —
warunek startu z promptu spełniony). Linie z promptu (`docs/zlecenia/PROMPT_writer_wymiany-produktow.md`
§3) zweryfikowane na tym `main`:

| Co | Gdzie (po bibliotece) | Uwaga |
|---|---|---|
| `TOL_MEAL`/`TOL_DAY` | `dieta/silnik.py` l. 38–39 | bez zmian w tej rundzie (test stałych l. ~189) |
| limity porcji v1.1 | `silnik.py` l. 92–104 (`fill_defaults`) | mięso/ryby ≤ 300 g, jajka ≤ 4, tłuszcz `round_step` 1 |
| `check` | `silnik.py` l. 194 | |
| `swap_candidates` | `silnik.py` l. 385–420 | bramka absolutna `check(...) → continue` l. 414–416; ta sama grupa l. 395; przecięcie tagów l. 399–401; `per <= 0 → continue` l. 402–404 |
| `kandydaci_wymiany` | `dieta/serwis.py` l. 290–308 | „nie lubię” filtrowane po nazwie (`_wykluczony` l. 193), po silniku |
| `posilek_silnika` | `serwis.py` l. 278–287 | |
| `swappable` w seedzie | `dieta/seed.py` l. 324 (`role in ("P","C","F")`) | szablony JSON nie mają pola `swappable` (0 wystąpień) |
| `swappable` w wyjściu | `serwis.py` l. 49 (migawka), l. 203 (`skladnik_out`) | |
| API wymian | `routers/diet.py` l. 326 (GET), 353 (POST), 405 (PATCH) | |
| Produkty | `dieta/dane/produkty.csv` — 181 wierszy | kolumny: `substitution_group`, `cooking_tags`, `allergens`, `diet_exclusions`, `default_scaling` |
| Szablon Standard v1 | `dieta/dane/szablony/template_standard_v1.json` (7 dni, 28 posiłków, 232 składniki, 108 z rolą P/C/F, 124 `NONE`) | |
| Katalog trenera | `food_catalog_data.FOOD_ROWS_ALL` — 2058 pozycji, 16 kategorii (`FoodRow`: name, category, kcal, protein, fat, carbs, fiber, portion_g, unit_name, unit_grams, note) | bez grup, tagów, alergenów |

## Pomiar „przed” (`tools/pomiar_wymian.py`, `main` po bibliotece, bez wykluczeń)

| szablon | kcal | posiłki nie-OK | składników (P/C/F) bez kandydata |
|---|---|---|---|
| template_standard_v1 | 1600 | 4/28 | **20 z 108 (19 %)** |
| template_standard_v1 | 2000 | 0/28 | **12 z 108 (11 %)** |
| template_standard_v1 | 2600 | 2/28 | **18 z 108 (17 %)** |

Przy 2000 kcal 12 pustych list to: jajko kurze ×6 (grupa `jajka` ma 2 produkty, ale
białko jaja ma inne tagi/makro), białko jaja ×2, awokado (singleton `tłuszcz_roślinny`),
tuńczyk z puszki (tagi bez przecięcia z rybami surowymi), szynka z indyka (`wędlina`, 2
produkty, drugi odpada tolerancją), ciecierzyca z puszki (strączki: kandydaci wypadają
poza tolerancję). Przy 1600/2600 kcal dochodzą posiłki OSTRZEŻENIE — tam bramka absolutna
zabija każdego kandydata (przyczyna nr 1 z promptu). Składniki `NONE` (124): przy obecnej
regule 2 bez kandydata, ale **żaden nie ma przycisku** (`swappable` = tylko P/C/F).

Pomiar powtarzany tym samym skryptem po zmianie (etap 5) — tabela przed/po w CHANGELOG.

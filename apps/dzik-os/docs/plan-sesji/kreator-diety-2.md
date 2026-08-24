# Plan sesji: kreator diety v2 — prawdziwe katalogi, prawdziwe posiłki

**Gałąź:** `agent/kreator-diety-2` (od `main` = `fa03727`)
**Rola:** aktywny piszący i integrator (zgłoszenie właściciela z produkcji,
24.08, ze zrzutami ekranu)
**Cel:** naprawić trzy problemy, które pierwszy prawdziwy przebieg
kreatora na telefonie właściciela obnażył bezlitośnie.

## Diagnoza (ze zrzutów z produkcji, nie z założeń)

Katalog produktów jest **per-trener**; baza 409 pozycji należy do konta
demo. Prawdziwe konto trenera ma własny, ubogi katalog (kategorie spoza
mapy slotów, niemal wyłącznie produkty węglowodanowe). Skutki widoczne
na zrzutach:

1. każdy slot × każdy dzień = 3 ostrzeżenia → **ściana 28 żółtych
   boxów** zamiast jednej zbiorczej informacji;
2. solver nie miał źródeł białka i tłuszczu → posiłki z **jednego
   produktu** (wafle ryżowe…), 1168 kcal vs cel 2200, B 24 g vs 165;
3. posiłki nawet na bogatym katalogu są 2–3-składnikowe — liczą makra,
   ale nie komponują jak dietetyk.

## Zamiar

1. **Wbudowana baza jednym kliknięciem.**
   `POST /coach/food-products/load-builtin` — idempotentne dogranie
   409 pozycji z `food_catalog_data` do katalogu zalogowanego trenera
   (pomija istniejące po znormalizowanej nazwie; zwraca {added,
   skipped}). Przycisk w zakładce Produkty + podpowiedź w Kreatorze,
   gdy pokrycie makro jest słabe.
2. **Dopełnianie z wbudowanej bazy w kreatorze.** Gdy w katalogu
   trenera brakuje źródła danego makro dla slotu, kandydat dobierany
   jest z wbudowanej bazy i **jawnie oznaczany** (`source: "builtin"`,
   w UI znaczek „z wbudowanej bazy") — propozycja nigdy nie jest
   kaleka, a trener widzi, czego nie ma u siebie. Kolejność puli:
   katalog trenera (dopasowany do slotu) → wbudowana (dopasowana) →
   katalog trenera (pełny).
3. **Kompozycja wg wzorców uznanych diet** (śródziemnomorska / DASH —
   wzorce o najlepszych dowodach, nie moda):
   * każdy slot ma szablon składu: źródło białka + węgli + tłuszczu
     (solver 3×3 jak dotąd) **plus dodatki**: warzywa do obiadu
     i kolacji (~200 g / ~150 g), owoc do śniadań i przekąsek
     (~100–120 g) — stała, rozsądna porcja, której makra odejmują się
     od celów slotu PRZED solverem, więc sumy dalej trafiają cel;
   * rotacja obiadowego białka premiuje ryby i strączkowe (obecność
     w puli co najmniej raz na tydzień przy dostępności) — zgodnie
     z zaleceniami wzorca śródziemnomorskiego;
   * wynik: posiłki 3–5-składnikowe z sensowną sugestią przyrządzenia.
4. **Ostrzeżenia zbiorcze.** Deduplikacja po (slot, problem) z licznikiem
   dni — trzy czytelne zdania zamiast 28 boxów; do tego jedno zalecenie
   naprawy („dodaj wbudowaną bazę / uzupełnij źródła białka").
5. **Odporność na cudze kategorie:** porównanie kategorii bez
   wielkości liter/spacji; produkt o nieznanej kategorii nadal działa
   jako źródło makro (klasyfikacja po dominującym makro).

## Mój obszar

- `backend/dzik_os/diet_wizard.py` (v2), `backend/dzik_os/routers/
  food_catalog.py` (endpoint load-builtin + rozszerzenie diet-wizard);
- `backend/tests/test_diet_wizard.py`, `backend/tests/
  test_food_catalog.py` (dopiski);
- `frontend/src/pages/coach/Knowledge.tsx` (przycisk, znaczki,
  zbiorcze ostrzeżenia), `frontend/src/types.ts`;
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- modeli/migracji (load-builtin używa istniejącej tabeli), seeda, Core;
- dostawcy AI (0.45.0) i pozostałych funkcji.

## Rezerwacje

- **Wersja: 0.46.0** (ostatnia: 0.45.0). **Migracja: brak.**

## Świadomie nie robię

- nie podpinam „diet z nazwy" (keto/paleo/IF) jako presetów — wzorce
  śródziemnomorski/DASH wchodzą jako **zasady kompozycji**, nie
  marketingowe etykiety; presety nazwane to osobna decyzja produktowa;
- nie liczę mikroskładników (witamin/minerałów) — poza zakresem danych
  katalogu;
- nie zmieniam zakresu „propose-only".

## Weryfikacja (do wypełnienia)

- pełne bramki z frontendem i E2E;
- uruchomienie na żywo w DWÓCH scenariuszach: (a) ubogi katalog jak na
  zrzutach właściciela — propozycja ma być pełna dzięki dopełnieniu
  z wbudowanej bazy, z jawnym oznaczeniem i zbiorczym ostrzeżeniem;
  (b) bogaty katalog — posiłki 3–5-składnikowe z warzywami/owocami,
  makra w punkt jak w 0.44.0.

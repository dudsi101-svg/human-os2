# Plan sesji: kreator diety

**Gałąź:** `agent/kreator-diety` (od `main` = `1ca995b`)
**Rola:** aktywny piszący i integrator (polecenie właściciela: rozbudowa
sekcji Dieta — katalog do 200 pozycji + kreator diety)
**Cel:** kreator tygodniowej propozycji diety na bazie istniejącego
katalogu produktów i istniejącej mechaniki sugestii porcji.

## Stan zastany (zwiad, nie założenia)

* Katalog produktów ma **409 pozycji w 16 kategoriach**
  (`food_catalog_data.py`) — cel „do 200 najpopularniejszych" jest
  przekroczony ponad dwukrotnie; pokrycie klasyków sprawdzone wyrywkowo
  (24/25 trafień, „jajko" to wariant nazwy w kategorii Jaja). Zamiast
  dosypywać pozycje, robię kontrolę braków i uzupełniam tylko realne luki.
* `POST /coach/diet-suggestion` już rozkłada gramaturę produktów na cele
  makro (podział wg dominującego makro) — kreator buduje na tym wzorcu.
* `NutritionPlanVersion.content_json` definiuje kształt
  `{"kcal","protein_g","fat_g","carbs_g","sections","meals":[{"name",
  "description","swaps"}]}` — wynik kreatora ma być zgodny z tym
  kształtem, żeby trener jednym ruchem tworzył z propozycji prawdziwy
  plan przez istniejące `POST /nutrition`.

## Zamiar

**Backend — `POST /coach/diet-wizard`** (w `routers/food_catalog.py`,
obok `diet_suggestion`; bez migracji — heurystyki w kodzie):

Wejście: `target_kcal`; `macro_percent {protein, fat, carbs}` (suma
100±1; przeliczenie na gramy 4/9/4 kcal/g); `meals_per_day` (2–6);
`days` (1–7 — dzień albo tydzień); preferencje (`excluded_categories`,
`excluded_product_ids`, `preferred_product_ids`);
`max_prep_minutes` na posiłek (opcjonalny budżet czasu).

Logika: sloty posiłków wg liczby (Śniadanie/II śniadanie/Obiad/
Podwieczorek/Kolacja/Przekąska) z wagami kcal; pula = ACTIVE produkty
trenera minus wykluczenia; dobór per slot wg dopasowania kategorii do
pory dnia i dominującego makro; gramatura jak w `diet_suggestion`;
zmienność między dniami przez deterministyczną rotację puli (te same
wejścia → ta sama propozycja); szacunek czasu przygotowania per
kategoria (max składników + montaż) i filtr budżetu czasu; sugestia
przyrządzenia jako tekst regułowy z kategorii składników. Braki są
ostrzeżeniami, nigdy wyjątkami (wzorzec `diet_suggestion`).

Wyjście: dni → posiłki → pozycje (produkt, gramy, sztuki, makro),
sumy posiłku/dnia/średnia tygodnia vs cel, `prep_minutes`
i `prep_suggestion` per posiłek, `warnings`,
`nutrition_plan_content` gotowe pod `POST /nutrition`.

Granica roli (Human OS): kreator PROPONUJE — trener zatwierdza,
edytuje i tworzy plan świadomie; nic nie zapisuje się samo.

**Frontend** — panel „Kreator diety" w zakładce żywieniowej trenera
(`pages/coach/Knowledge.tsx`, obok istniejącej Sugestii): formularz
(kcal, suwaki/pola % makro z kontrolą sumy, posiłki/dzień, dni,
wykluczenia kategorii, budżet czasu) → wynik per dzień → przycisk
„Utwórz plan żywieniowy" (wybór klienta + istniejące `POST /nutrition`).

**Kontrola braków katalogu:** porównanie z listą ~40 klasyków; dopisanie
wyłącznie brakujących do `food_catalog_data.py` (spodziewane: 0–5).

## Mój obszar

- `backend/dzik_os/routers/food_catalog.py` (+ schemat wejścia),
  ewentualnie `backend/dzik_os/diet_wizard.py` (logika osobno, jeśli
  urośnie);
- `backend/dzik_os/food_catalog_data.py` (tylko realne luki);
- `backend/tests/test_diet_wizard.py` (nowy);
- `frontend/src/pages/coach/Knowledge.tsx` (+ typy, helper);
- `docs/CHANGELOG.md`, `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- modeli i migracji (kształt `content_json` już pasuje);
- istniejącej Sugestii diety (zostaje jako szybkie narzędzie);
- Core Human OS; OCR; AI (kreator jest w 100% regułowy — bez klucza).

## Rezerwacje

- **Wersja: 0.44.0** (ostatnia: 0.43.1). **Migracja: brak.**

## Świadomie nie robię

- nie liczę zapotrzebowania kalorycznego klienta (BMR/TDEE) — cel kcal
  podaje trener; automat sugerujący kalorie to decyzja produktowa
  z osobnym ryzykiem (dane zdrowotne);
- nie dobieram diety „pod jednostki chorobowe" — poza zakresem i poza
  kompetencją narzędzia;
- nie generuję przepisów AI — sugestie przyrządzenia są regułowe.

## Weryfikacja (do wypełnienia)

- pełne bramki §5 z frontendem i E2E;
- uruchomienie na żywo: wygenerowanie tygodniowej propozycji przez API
  i utworzenie z niej planu żywieniowego dla klienta demo — obejrzane,
  nie „sprawdzone".

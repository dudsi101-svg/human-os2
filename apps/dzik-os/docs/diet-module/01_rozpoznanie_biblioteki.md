# Rozpoznanie (etap 0) — biblioteka szablonów z paczki 14.09

* `dieta/seed.py`: `wczytaj_produkty_csv` (te same kolumny co `baza_produktow.csv` z paczki),
  `zaseeduj_produkty` (po `name_pl`), `waliduj_szablon` (struktura; sprawdzić tolerancję na nowe
  klucze `audit`/`derived_from`/`sodium_note`/`supplements_note`/`allergens`), `zaimportuj_szablon`
  (istniejąca (profil, odsłona) → bez zmian — do rozszerzenia o podmianę po hashu), `zaseeduj`.
* `dieta/silnik.py` `fill_defaults` (l. 80–112): brak trzech reguł v1.1 (300 g mięsa/ryb, 4 jajka,
  `round_step` 1 g dla tłuszczów LINIOWY). Reszta 1:1 (test `test_stale_silnika_identyczne_z_prototypem`
  czyta stałe z `docs/diet-module/engine.py` przez AST — po podmianie pliku nadal działa).
* Modele: `DietTemplateWeek` (bez notatek/hash), `DietTemplateMeal` (bez alergenów), `DietProduct`
  (wszystkie kolumny CSV są). Migracja 32 = moduł; ostatnia w `db.py` = 34 (nawyki, gałąź równoległa).
* API: `POST /api/diet/weeks/import` (DRAFT, walidacja jak seed), sweep/publish istnieją.
* Frontend: slot drukowany surowo (`DietaSzablon.tsx:80`, `PrzypiszDiete.tsx:184/323/399`) —
  potrzebny `SLOT_LABEL`; posiłki renderowane z listy (dowolna liczba).
* Testy: `test_dieta_seed` (142/1/7×28 — do aktualizacji na 181/45/1295), `test_dieta_silnik`
  (golden dzień 1 i cały tydzień, sweep 131/133, reguły).
* Paczka vs repo: produkty nadzbiór (39 nowych, 0 zmian); `template_standard_v1.json` i golden
  po audycie różnią się od repo; `engine.py` różni się wyłącznie trzema regułami limitów.

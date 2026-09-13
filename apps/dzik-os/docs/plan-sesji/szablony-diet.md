# Plan sesji: szablony diet ze skalowaniem (0.60.0)

**Gałąź:** `agent/szablony-diet` (od `main` = 80deb80 po scaleniu #56; jeden
`[WRITER]` naraz). **Rola:** jedyny piszący i integrator; Codex recenzuje.
**Źródło:** zadanie właściciela 13.09 + `docs/diet-module/` (instrukcja v1.1,
`engine.py`, `baza_produktow.csv`, `template_standard_v1.json`, golden
`szablon_standard_v1_2000kcal.md`). Rozpoznanie: `docs/diet-module/00_rozpoznanie.md`.

## Zamiar

Etapy 0–6 z zadania, każdy z testami; stan po etapie w
`docs/diet-module/PROGRESS.md`. Cały moduł za flagą
`DZIK_DIET_TEMPLATES_ENABLED` (domyślnie wyłączony; dev/test włączony).
Stary kreator (kulinaria, nutrition_templates, nutrition) nietknięty.

## Decyzje

1. Pakiet `dzik_os/dieta/`: `silnik.py` (port `engine.py` 1:1, czyste funkcje,
   produkty jako parametr), `dane/` (CSV + JSON z pakietu, `package-data`),
   `seed.py` (idempotentny, mapowanie po `name_pl`, brak = błąd), `serwis.py`
   (cele makro, presety, wykluczenia, migawka, wymiany, walidacja).
2. Tabele (migracja 32, addytywna, prefiks `diet_`): `diet_products`,
   `diet_profiles`, `diet_template_weeks`, `diet_template_days`,
   `diet_template_meals`, `diet_template_ingredients`, `diet_assigned`,
   `diet_swap_events`. `computed_plan` = migawka JSON; `overrides` JSON.
3. API `/api/diet/...` (klasy dostępu w macierzy): profile, szablon,
   preview, assign, assigned/current, swaps, PATCH assigned; 404 gdy flaga
   wyłączona. Trener tylko własny klient (`resolve_client_access`,
   domena żywienie); klient tylko własna dieta.
4. Reguła `group`: opcja silnika `enforce_groups` (domyślnie włączona w
   aplikacji); test golden dnia 1 niezależny od opcji; test „cały tydzień
   golden” z opcją wyłączoną dowodzi portu 1:1.
5. UI: trener — przepływ „Przypisz dietę” w zakładce Dieta karty klienta
   (nowy komponent), podgląd tygodnia, edycja gramatur, blokada przy
   `POZA_TOLERANCJĄ` z checkboxem; klient — sekcja w ekranie Dieta
   (dzień, przepisy, wymiany P1); panel szablonów pod `/trener/szablony-diet`
   (CRUD minimalny + sweep + import JSON + publikacja ≥ 95 % OK).

## Rezerwacje

Migracja **32**, wersja **0.60.0**, pliki: `backend/dzik_os/dieta/**`,
`routers/diet.py`, `config.py` (flaga), `models.py`, `db.py`,
`tests/test_dieta_*.py`, `frontend/src/pages/coach/PrzypiszDiete.tsx`,
`pages/coach/SzablonyDiet.tsx`, `pages/client/Nutrition.tsx`,
`pages/coach/ClientDetail.tsx`, `docs/diet-module/*`.

## Weryfikacja wykonana

(uzupełnię po rundzie)

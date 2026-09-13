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
4. Reguła `group`: opcja silnika `enforce_groups` (domyślnie WYŁĄCZONA —
   wynik identyczny z referencją i złotym plikiem; API przyjmuje
   `enforce_groups=true`, interfejs trenera jej nie włącza — decyzja
   właściciela, pytanie otwarte w PROGRESS.md); test golden dnia 1
   niezależny od opcji; test „cały tydzień golden” z opcją wyłączoną
   dowodzi portu 1:1.
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

- Backend: `ruff check` na nowych plikach czysty; `pytest` — 1730 passed,
  1 skipped (w tym 28 nowych: seed 5, silnik 12, API 11); pokrycie
  `dzik_os/dieta/silnik.py` 98 % (próg z zadania: 90 %).
- Złoty test: dzień 1 i cały tydzień (161 składników) przy 2000 kcal
  identyczne z `szablon_standard_v1_2000kcal.md`; sweep 1400–3200 co 50:
  131/133 dni OK (próg ≥ 131).
- Core: 275 testów zielone. `tools/spojnosc.py`: 13/13.
- Frontend: `tsc --noEmit` czysty; `vite build` 89,5 kB gzip (budżet
  120 kB); `test:helpers` 140; `e2e/test_a11y.mjs` — wszystkie kontrole
  dostępności/responsywności przeszły.
- E2E Playwright (projekt „telefon”): pełny zestaw zielony, w tym nowy
  `dieta-szablon.spec.ts` (trener: profil → odsłona → 2200 kcal → podgląd →
  korekta gramatury → przypisanie; klient: dzień z gramaturami → wymiana
  kurczaka na indyka; trener: historia wymian).
- Odchylenie znalezione przez E2E i naprawione: przycisk odsłony z zakresem
  kcal nie łamał wiersza i poszerzał układ telefonu do 423 px, przez co
  Playwright trafiał w sąsiednią kartę / dolną nawigację (przycisk
  zawija się teraz, `PrzypiszDiete.tsx`).
- Przegląd kodu przed scaleniem (13.09): 45 uwag zdeduplikowanych i
  sklasyfikowanych bez agentów; P0/P1 poprawione i pokryte testami
  (`tests/test_dieta_poprawki.py` 10, stałe silnika 3), P2 w PROGRESS.md.
  Po poprawkach: backend `pytest` pełny zielony, E2E 28/28, `tsc`/build OK.
- Flaga: `DZIK_DIET_TEMPLATES_ENABLED=false` → trasy `/api/diet/*` zwracają
  404, `health.features.diet_templates=false`, interfejs nie pokazuje
  wejść (test `test_dieta_api.py::test_flaga_wylaczona_daje_404_na_calym_module`); w dev/test/E2E
  włączona.

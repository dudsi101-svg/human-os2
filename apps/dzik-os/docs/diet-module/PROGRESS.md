# PROGRESS — moduł „Szablony diet ze skalowaniem”

Stan po etapach (aktualizowany po każdym etapie). Wersja docelowa 0.60.0,
gałąź `agent/szablony-diet`.

## Etap 0 — rozpoznanie: zrobione
`00_rozpoznanie.md`. Decyzje: pakiet `dzik_os/dieta/`, migracja 32, flaga
`DZIK_DIET_TEMPLATES_ENABLED`, stary kreator nietknięty.

## Etap 1 — model danych i seed: zrobione
* Tabele `diet_products`, `diet_profiles`, `diet_template_weeks`, `diet_template_days`,
  `diet_template_meals`, `diet_template_ingredients`, `diet_assigned`, `diet_swap_events`
  (migracja 32, addytywna, SQL przenośny na PostgreSQL). Modele w `dzik_os/models.py`.
* `TemplateIngredient.unit_size` ze specyfikacji = `unit_g` + `unit_step` (jak w `engine.py`);
  `group` → kolumna `group_name` (słowo zarezerwowane w SQL). NULL = domyślne klasy.
* `Product.kcal_100` = `4·P + 9·F + 4·W` zaokrąglone do 0,1 — dokładnie wartość kolumny CSV
  (golden był liczony na tej wartości; zaokrąglenie do 0,01 dawało 681 vs 682 kcal w chili);
  `kcal_usda`, `source`, `source_id`, `source_desc` zachowane.
* Seed `dzik_os/dieta/seed.py` (`python -m dzik_os.dieta.seed`): CSV i JSON z pakietu
  (`package-data`), produkty po `name_pl`, odsłona po (profil, wariant); brak produktu = `ValueError`.
  Uruchamiany też przy starcie aplikacji, gdy flaga włączona (etap 3).
* Testy: `tests/test_dieta_seed.py` (5): 142 produkty, 7 dni, 28 posiłków, ponowny seed bez duplikatów,
  każdy składnik wskazuje produkt, kcal z makro, błąd przy nieznanym produkcie, kształt z bazy = JSON.

## Etap 2 — silnik: zrobione
* `dzik_os/dieta/silnik.py` = port 1:1 `engine.py` (te same stałe, kolejność kroków, przebiegi 6/3/12);
  różnice wyłącznie techniczne (produkty jako parametr, NaN → "", assert → ValueError).
* **Golden**: cały tydzień Standard v1 przy 2000 kcal (7 dni, 28 posiłków, 161 składników, statusy,
  sumy) identyczny z `szablon_standard_v1_2000kcal.md`; sweep 1400–3200: 131/133 dni OK,
  77/532 posiłków z flagą — jak w raporcie prototypu. Wymiany: kurczak → indyk 155 g / schab 150 g /
  polędwiczka 170 g; skyr z `lactose` → pusta lista (jak golden).
* **Reguła `group`** (kryterium akceptacji): referencja jej NIE wymusza (golden: racuchy jajko ×1,0
  vs mąka ×0,75; naleśniki płatki ×0,7 / jajko ×1,0 / mleko ×0,85). Dopisana jako jawna opcja
  `enforce_groups_` (domyślnie **wyłączona** = wynik referencyjny): współczynnik grupy = średnia
  ważona kcal, przycięta do przecięcia zakresów, a przy składniku DYSKRETNY — z jego liczby
  jednostek; członkowie grupy nie są potem zaokrąglani do `round_step` (inaczej współczynniki
  by się rozjechały) i pomijani w dostrojeniu dnia. Z regułą sweep daje **129/133** dni OK
  (kryterium ≥ 131 spełnia tryb referencyjny). **Pytanie do człowieka:** czy włączyć regułę
  domyślnie w aplikacji (koszt: 2 dni więcej poza tolerancją), czy zostawić jako opcję
  podglądu (obecnie: parametr `enforce_groups` w `preview`/`assign`, domyślnie false).
* Test „zakres nigdy nieprzekroczony” dowodzi tego PRZED zaokrągleniem (monkeypatch
  `round_practical`); po zaokrągleniu dopuszczalne odchylenie < 1 krok (tak działa referencja).
* Pokrycie `silnik.py`: 98 % (pytest-cov lokalnie; CI nie mierzy pokrycia — nie dodaję zależności).

## Etap 3 — API: zrobione
Router `dzik_os/routers/diet.py` (prefiks `/api/diet`, 404 gdy flaga wyłączona; `features.diet_templates`
w `/api/health`; seed przy starcie aplikacji, gdy flaga włączona):

| Metoda i trasa | Kto | Co |
|---|---|---|
| `GET /profiles` | trener/admin | profile z liczbą opublikowanych odsłon i listą odsłon |
| `GET /templates/{week_id}` | trener/admin | podgląd odsłony bez gramatur |
| `GET /templates/{week_id}/meals?slot=` | trener/admin | biblioteka posiłków profilu (ten sam slot) do zamiany |
| `POST /templates/{week_id}/preview` | trener/admin | pełny wynik silnika; `macro.mode` profile / per_kg / manual; `exclusions`; `overrides` (korekty gramatur „day:meal:ingredient”); `meal_replacements`; `enforce_groups` — bez zapisu; kcal poza zakresem = ostrzeżenie; manual ≠ kcal ±3 % = 422 |
| `POST /assign` | trener, własny klient (relacja + zgoda żywienie) | migawka + overrides; dzień POZA_TOLERANCJĄ → 409 `DAY_OUT_OF_TOLERANCE`, chyba że `accept_warnings` (fakt zapisany w `overrides.accepted_warnings/accepted_days`); poprzednia dieta → ARCHIVED, `version` +1; tylko odsłony PUBLISHED |
| `GET /assigned/current` | klient | własna dieta (migawka + korekty) |
| `GET /clients/{client_id}/current` | klient / trener z dostępem | dieta + historia wersji + historia wymian |
| `GET /assigned/{id}/swaps?day=&meal=&ingredient=` | właściciel / trener | 1–3 kandydatów (`swap_candidates`, wykluczenia klienta, `swappable`, blokada trenera) |
| `POST /assigned/{id}/swaps` | właściciel / trener | produkt musi być kandydatem; gramatura z klienta walidowana tolerancją posiłku (422), bez niej — gramatura silnika; `SwapEvent` + override |
| `PATCH /assigned/{id}` | trener | korekta gramatury (dzień przeliczony), zamiana posiłku z biblioteki (ten sam slot, przeskalowany do celu posiłku), `swaps_enabled` |
| `GET /products`, `POST /products` (ADMIN) | | baza produktów; nowy produkt tylko admin z `source` (kcal z makro) |
| `POST/PUT /profiles…`, `POST/PUT /weeks…`, `GET /weeks/{id}/full`, `POST /weeks/{id}/days/{n}/meals`, `PUT/DELETE /meals/{id}`, `POST /meals/{id}/ingredients`, `PUT/DELETE /ingredients/{id}` | trener/admin | panel szablonów (etap 6, backend) |
| `POST /weeks/{id}/sweep`, `/publish`, `/unpublish`, `POST /weeks/import` | trener/admin | sweep 1400–3200 (flagi per posiłek, brakujące dni), publikacja ≥ 95 % dni OK (409 `SWEEP_BELOW_THRESHOLD`), import JSON jako DRAFT |

Decyzje: `client_id` w ciele `assign` (jak w zadaniu) → klasa dostępu COACH_ONLY w macierzy, a
własność klienta sprawdza `resolve_client_access` (test: obcy trener 404, klient 403). Panel
szablonów dostępny dla roli COACH lub ADMIN (szablony nie są danymi klientów; admin nadal nie
sięga po diety klientów — test). Powiadomień o przypisaniu nie wysyłam (poza zakresem zadania;
łatwa okazja: wpis „Trener przypisał dietę” przez outbox jak w 0.58.0 — propozycja, nie zrobione).
Testy: `tests/test_dieta_api.py` (11) + 27 wpisów macierzy dostępu weryfikowanych wykonaniem.

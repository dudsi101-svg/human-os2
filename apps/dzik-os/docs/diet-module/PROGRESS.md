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

## Etap 4 — UI trenera: zrobione
`frontend/src/pages/coach/PrzypiszDiete.tsx`, wpięty w zakładkę Dieta karty klienta
(`ClientDetail.tsx`, widoczny tylko, gdy `GET /api/diet/profiles` odpowiada 200 — flaga).
Przepływ §9: kafelki profili (tylko z opublikowanymi odsłonami) → odsłony z podglądem posiłków
tygodnia → cel (kcal, preset z profilu / na kg / ręcznie, masa ciała, wykluczenia: alergeny +
nielubiane produkty) → „Przelicz tydzień” → karty dni z sumą i kolorowym statusem, posiłki ze
statusem i odchyleniem, „Zamień na inny posiłek” (biblioteka tego profilu, ten sam slot,
przeliczenie na żywo), edycja gramatur inline (debounce 700 ms → `preview` z `overrides`) →
„Przypisz” z potwierdzeniem; blokada przy dniu POZA_TOLERANCJĄ z checkboxem „przypisz mimo
ostrzeżeń” (serwer zapisuje `accepted_warnings/accepted_days` w overrides). Karta przypisanej
diety (`PrzypisanaDietaTrenera`): dzień po dniu, korekty, historia wymian klienta, blokada wymian.
Nie zrobione (poza P0): edycja gramatur po przypisaniu w UI (API `PATCH` istnieje i jest
przetestowane) — propozycja na kolejną rundę.

## Etap 5 — UI klienta: zrobione (P0 + P1)
`frontend/src/pages/client/DietaSzablon.tsx` w ekranie Dieta: dzień (zakładki D1–D7), posiłki
z gramaturami (dyskretne „2 szt. (~110 g)”), makro posiłku i dnia, przepis rozwijany; P1:
„↔ wymień” przy składniku `swappable` → arkusz 1–3 zamienników z gramaturą policzoną przez
serwer → zapis; brak kandydatów → „Brak bezpiecznego zamiennika, napisz do trenera” z linkiem
do wiadomości; blokada trenera pokazana jako komunikat. Trener widzi historię wymian w karcie.

## Etap 6 — panel szablonów: zrobione (minimalny)
`/trener/szablony-diet` (`SzablonyDiet.tsx`, link z ekranu Szablony → Dieta): profile (dodanie),
odsłony (dodanie, edycja dni → posiłki → składniki z wyborem produktu z bazy i polami reguł:
rola, klasa, g/szt, grupa; usuwanie), „Testuj skalowanie” (sweep 1400–3200, dni OK, flagi per
posiłek, brakujące dni), publikacja tylko przy ≥ 95 % dni OK (serwer 409 poniżej progu),
cofnięcie publikacji, import odsłony z JSON. Nie ma jeszcze: edycji istniejącego składnika /
posiłku w miejscu (API `PUT` istnieje), edycji profilu, dodawania produktu (API admina istnieje).

## Odstępstwa od specyfikacji i decyzje techniczne
* Reguła `group` nie jest wymuszana domyślnie (referencja jej nie wymusza; z regułą sweep
  129/133) — opcja `enforce_groups`; **pytanie do człowieka**.
* Tolerancje z §6.2 (±4 g B, ±3 g T, ±8 g W posiłku) zostały w kodzie zastąpione wartościami
  z §4a.3 i `engine.py` (±5/±4/±10 g, ±8 % lub ±40 kcal) — zgodnie z zadaniem (stałe z `engine.py`).
* `unit_size` ze specyfikacji = `unit_g` + `unit_step` (jak w prototypie); `group` → `group_name`.
* `client_id` w ciele `assign` (jak w zadaniu), własność sprawdzana serwerowo; klasa dostępu w
  macierzy: COACH_ONLY + testy „obcy trener 404 / klient 403”.
* Panel szablonów dla roli COACH lub ADMIN (aplikacja nie ma roli „dietetyk”); produkt dodaje
  wyłącznie ADMIN z jawnym `source`.
* Powiadomienie klienta o przypisaniu diety — nie wysyłane (propozycja: outbox jak w 0.58.0).
* Wartości produktów: surowe (USDA SR Legacy, 11 pozycji MANUAL_PL „do weryfikacji”) — bez
  mnożników zmiany masy po obróbce (pytanie otwarte §11 spec).
* E2E: przyciski nisko na długiej karcie klikane z `force` (kontrola „stable” Playwrighta daje
  fałszywy wynik w emulacji telefonu; prostokąt elementu jest stały — sprawdzone pomiarem).

## Pytania otwarte do człowieka
1. Włączyć regułę `group` domyślnie (koszt: 129 zamiast 131 dni OK w sweepie)?
2. Kiedy włączyć `DZIK_DIET_TEMPLATES_ENABLED` na produkcji (sekret Fly)? Dziś: wyłączone.
3. Kto i kiedy dostarcza kolejne profile/odsłony (wymagane P0: 3 profile × 5 odsłon) —
   panel i import JSON są gotowe; w repo jest 1 odsłona.
4. Czy klient ma limit wymian na posiłek (spec §11)? Dziś: bez limitu, z historią.
5. Dodać produkty bezlaktozowe do grupy `nabiał_chudy` (golden wskazuje brak zamiennika skyru).

## Jak uruchomić
```
cd apps/dzik-os/backend && DZIK_DIET_TEMPLATES_ENABLED=true python -m dzik_os.dieta.seed   # migracje + seed
python -m pytest tests/test_dieta_seed.py tests/test_dieta_silnik.py tests/test_dieta_api.py
cd ../frontend && npm run build && DZIK_E2E_PORT=8098 npx playwright test e2e/dieta-szablon.spec.ts
```
Aplikacja z flagą (`.env`: `DZIK_DIET_TEMPLATES_ENABLED=true`) seeduje dane przy starcie.

## Propozycje (nie zrobione, poza zakresem)
* Wpis w centrum powiadomień klienta „Trener przypisał dietę” przez outbox.
* Lista zakupów z migawki (dane są w `computed_plan`).
* Statystyki wymian (tabela `diet_swap_events` już je zbiera).

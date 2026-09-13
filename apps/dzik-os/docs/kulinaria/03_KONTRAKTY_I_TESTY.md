# Kontrakty i testy

## Minimalny kontrakt danych

`DietConfiguration`: user_id, revision, age_scope, health_routing_status, animal_policy, pattern_id, pattern_version, carb_policy, carb_limit_g|null, carb_basis|null, meal_count, meal_preferences, cuisines, excluded_ingredients, allergens, available_equipment, max_active_minutes, max_total_minutes, budget, pantry_ids, batch_cooking, targets_ref i targets_revision. Cele pochodzą z odrębnego modułu, nie z tekstu LLM.

`Ingredient`: id i version, external_food_id, external_source, composition, allergens z tri-state known/unknown/not_applicable, animal_origin, food_groups, nutrition_per_100g, carb_definition, edible_fraction, state, density_if_needed, database_quality. Woda i przyprawy także istnieją w recepturze; niektóre mogą mieć zerową energię, ale nie zerowy wpływ technologiczny.

`Recipe`: id, revision, status, name, family, cuisine, meal_slots, servings, ingredient_lines, steps, total_minutes, active_minutes, equipment, portion_variants, culinary_constraints, substitutions, nutrition_status, nutrition_snapshot, validation, storage_policy_id. Linie składników mają state, amount, unit, role, edible_mass_basis i referencję konkretnego produktu. Receptury demonstracyjne używają gramów; mapowanie do bazy następuje przed publikacją.

`RecipeVariant`: odrębne ID lub revision, powiązanie z recepturą, wszystkie zmiany składników i metody, wynik testu. Nie wystarczy zachować starej etykiety vegan po dodaniu jogurtu mlecznego. Warianty S/M/L mają gotowe ilości lub zatwierdzone regulatory, nie dowolne skalowanie każdego składnika.

`DailyMenu`: date, meals z recipe_id/revision/variant_id i portion_count, nutrient_totals z definicjami i kompletnością, hard_validation, deviations, reasons, status. Statusy: ready, limited, needs_input, needs_review, infeasible, nutrition_unverified. Błąd alergii lub nieznany skład przy wymaganej kontroli nigdy nie daje ready lub limited.

`DecisionTrace`: właściciel i plan/revision, target meal/portion/ingredient, rule_id/version, fakty i preferencje rzeczywiście użyte, wybrana receptura, outcome oraz odnośniki Wiedzy. Zachowaj zgodność z wcześniejszym pakietem Wiedza. Brak danych nie pozwala odtworzyć historycznego powodu.

## Kolejność silnika

```
validate_input_and_medical_route()
compile_profile_intersection()  // jawny wariant, bez zgadywania
reject_conflicting_targets()
filter_published_recipes_by_hard_constraints()
expand_only_validated_portion_variants()
compute_nutrients_from_versioned_products()
drop_unknown_required_nutrients_and_unsafe_variants()
select_daily_combinations_within_target_bounds()
rank_feasible_combinations_by_preferences_and_week_context()
validate_week_quality_variety_and_storage()
persist_menu_and_trace_atomically()
```

MVP może korzystać z programowania całkowitoliczbowego lub ograniczonego przeszukiwania. Kandydaci są dyskretnymi wariantami dań. Dla każdego slotu wybierz dokładnie jeden wariant; zakazy są ograniczeniami twardymi. Maksymalny czas obliczeń np. 5 sekund to ustawienie techniczne, nie reguła dietetyczna. Po przekroczeniu limitu pokaż wynik tylko jeśli pełny walidator go zaakceptował; w innym przypadku status i propozycję zmniejszenia ograniczeń. Nie przedstawiaj timeoutu jako dowodu matematycznej niewykonalności.

Kolejność dopuszczalnych propozycji przy konflikcie: inny przepis → dozwolona porcja → inny rozkład posiłków w zadanych granicach → pytanie o zmianę preferencji miękkiej. Alergie i zalecenia pozostają nienaruszone. Zmiana liczby posiłków lub diety wymaga akceptacji.

## API i kontrola wersji

- `generateMenu(config, horizon)` zwraca status, plan|null, constraints_report i trace_refs.
- `previewRecipeSwap(planId, revision, mealId, recipeVariantId)` zwraca różnice bez mutacji.
- `confirmRecipeSwap(previewId, expectedRevision)` ponownie sprawdza uprawnienia, rewizję i ograniczenia; konflikt 409.
- `calculateRecipeNutrition(recipeRevision, foodVersions)` jest deterministyczne i nie wywołuje LLM.
- `publishRecipe(recipeRevision)` wymaga kompletnych danych i zatwierdzeń kuchennych oraz dietetycznych.

Nie cache’uj prywatnych menu i alergii w publicznym CDN. Zapis i trace muszą być atomowe lub spięte outboxem. Audyt zawiera kody decyzji, nie pełny wywiad medyczny w logach.

## Przypadki akceptacyjne

| ID | Przypadek | Wynik |
|---|---|---|
| D01 | Wegański profil i miód lub żelatyna | Odrzucenie składnika |
| D02 | Paleo classic i makaron pszenny | Odrzucenie; nie zmieniaj definicji paleo |
| D03 | Keto i makro 45% węglowodanów | Jawny konflikt konfiguracji |
| D04 | Keto bez definicji węglowodanów | needs_input |
| D05 | Europejskie available carbs i błonnik | Brak ponownego odejmowania błonnika |
| D06 | Poliole o nieznanym rodzaju | Nie odejmuj automatycznie całej masy |
| D07 | Przepis low carb jako jedyny dowód keto dnia | Blokada etykiety zgodności bez sumy dnia |
| D08 | Alergia i sos o nieznanym składzie | Brak ready, potrzeba danych |
| D09 | Zamiana tofu na orzechy przy alergii | Odrzucenie niezależnie od makro |
| D10 | Wegański jogurt zamieniony na mleczny | Ponowny filtr profilu; odrzucenie |
| D11 | Zwiększenie płatków bez płynu | Naruszenie sprzężenia receptury |
| D12 | 70 g oliwy dodane tylko dla makro | Odrzucenie wariantu poza zatwierdzonym zakresem |
| D13 | Makaron zastąpiony cukinią 1 do 1 | Wymagany osobny przetestowany wariant |
| D14 | Gulasz bez sosu po optymalizacji | Naruszenie rodziny dania |
| D15 | 2,4 jajka bez zatwierdzonego sposobu ważenia | Wariant niewykonalny w UI; wybór innej porcji |
| D16 | Surowy produkt z danymi ugotowanego | Odrzucenie mapowania |
| D17 | Brak B12 w danych produktu | Unknown, nie zero ani potwierdzenie pokrycia |
| D18 | Nieznana fortyfikacja napoju | Brak deklaracji wartości dodanych witamin |
| D19 | 6 posiłków z jedną dużą porcją każdy | Ponowna kontrola bilansu i preferencji wielkości |
| D20 | Brak odpowiedniej liczby dań po filtrach | Konflikt biblioteki, bez przypadkowych produktów |
| D21 | Ten sam przepis codziennie bez zgody | Kara różnorodności i alternatywy |
| D22 | Powtarzalne śniadania zaakceptowane | Preferencja może nadpisać miękką karę |
| D23 | Gotowanie na tydzień bez mrożenia i polityki | Brak automatycznego planowania resztek |
| D24 | Zmiana porcji o dużej skali | Kontrola naczynia, czasu i wydajności |
| D25 | LLM podaje kalorie bez bazy | Odrzucenie danych |
| D26 | Przepis draft | Niewidoczny w produkcyjnym solverze |
| D27 | Nietolerowana ostrość | Inny zatwierdzony wariant smakowy |
| D28 | Cukrzyca lub SGLT2 przy keto | needs_review, bez porad o zmianie leków |
| D29 | Konflikt podczas równoczesnej zamiany | 409; zachowana poprzednia wersja menu |
| D30 | Nieudane wyszukiwanie w limicie czasu | Timeout, nie fałszywy dowód infeasible |
| D31 | Bilans makro poprawny, brak danych mikro | Jawny nutrition_unverified dla pełnej oceny |
| D32 | Wegańska i śródziemnomorska | Poprawne przecięcie, bez arbitralnego konfliktu |

## Test kuchenny i odbiór

Przygotuj recepturę bazową i skrajne dopuszczalne porcje. Zapisz rzeczywistą wydajność, czas, przydatność instrukcji, naczynia, ocenę tekstury i smaku oraz błędy. Ocenę dietetyczną i dane produktów wykonaj osobno. Smak 1–5 jest opinią, nie gwarancją; nie może nadpisać alergii lub złego bilansu.

Porównaj nowy i stary generator na tych samych profilach, bez ujawniania oceniającym źródła propozycji. Mierz odsetek dań rozpoznawalnych i wykonalnych, potrzebę ręcznych poprawek, ocenę smaku po ugotowaniu oraz zgodność ilościową. Nie raportuj takich wyników przed przeprowadzeniem testu.

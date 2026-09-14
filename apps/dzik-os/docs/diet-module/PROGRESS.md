# PROGRESS — moduł „Szablony diet ze skalowaniem”

Stan po etapach (aktualizowany po każdym etapie). Wersja 0.60.0 (gałąź
`agent/szablony-diet`), rozszerzenie 0.64.0 (gałąź `agent/biblioteka-diet`) —
sekcja na dole.

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
  sumy) identyczny z `szablon_standard_v1_2000kcal.md`; sweep zakresu odsłony (do 0.63: 1400–3200): 131/133 dni OK,
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
| `POST /templates/{week_id}/preview` | trener/admin | pełny wynik silnika; `macro.mode` profile / per_kg / manual; `exclusions`; `overrides` (korekty gramatur „day:meal:ingredient”, walidowane: klucz musi istnieć w planie, produkt w bazie, 0–5000 g); `meal_replacements` (posiłek z tego profilu, z opublikowanej albo tej samej odsłony, niepusty); `enforce_groups` — bez zapisu; kcal poza zakresem = ostrzeżenie; manual ≠ kcal ±3 % = ostrzeżenie (§6.4), tydzień liczony na kcal z gramów makro; każdy błąd definicji szablonu (pusty posiłek, cel ≤ 0 kcal) = 422 z komunikatem |
| `POST /assign` | trener, własny klient (relacja + zgoda żywienie) | migawka + overrides; dzień POZA_TOLERANCJĄ → 409 `DAY_OUT_OF_TOLERANCE`, chyba że `accept_warnings` (fakt zapisany w `overrides.accepted_warnings/accepted_days`); poprzednia dieta → ARCHIVED, `version` +1; tylko odsłony PUBLISHED |
| `GET /assigned/current` | klient | własna dieta (migawka + korekty) |
| `GET /clients/{client_id}/current` | klient / trener z dostępem | dieta + historia wersji + historia wymian |
| `GET /assigned/{id}/swaps?day=&meal=&ingredient=` | właściciel / trener | 1–3 kandydatów (`swap_candidates` + wykluczenia klienta także po nazwie produktu, `swappable`, blokada trenera globalna i per posiłek, wersja ARCHIVED = zablokowane) |
| `POST /assigned/{id}/swaps` | właściciel / trener (zgoda `write`) | tylko wersja ACTIVE (409); produkt musi być kandydatem; gramatura z klienta walidowana tolerancją posiłku (422), bez niej — gramatura silnika; `SwapEvent` + override; po zmianie produktu DYSKRETNEGO klient widzi gramy (sztuki starego produktu znikają) |
| `PATCH /assigned/{id}` | trener (zgoda `write`) | tylko wersja ACTIVE (409); korekta gramatury (klucz musi istnieć w migawce → 404; dzień i podsumowanie przeliczone), zamiana posiłku z biblioteki (ten sam slot i profil, opublikowana odsłona; względem MIGAWKI, więc działa też dla slotu zamienionego po raz kolejny), `swaps_enabled`, `meal_swaps_enabled` (blokada wymian w jednym posiłku, §7.3) |
| `GET /products`, `POST /products` (ADMIN) | | baza produktów; nowy produkt tylko admin z `source` (kcal z makro) |
| `POST/PUT /profiles…`, `POST/PUT /weeks…`, `GET /weeks/{id}/full`, `POST /weeks/{id}/days/{n}/meals`, `PUT/DELETE /meals/{id}`, `POST /meals/{id}/ingredients`, `PUT/DELETE /ingredients/{id}` | trener/admin (klasa `COACH_OR_ADMIN` w macierzy) | panel szablonów (etap 6, backend); odsłona: `kcal_min ≤ base_kcal ≤ kcal_max`; składnik: DYSKRETNY (jawny albo domyślny produktu) wymaga `unit_g`, `swappable` domyślnie wg roli P/C/F (§7.3) |
| `POST /weeks/{id}/sweep`, `/publish`, `/unpublish`, `POST /weeks/import` | trener/admin | sweep zakresu odsłony (do 0.63: 1400–3200) (flagi per posiłek, brakujące dni), publikacja ≥ 95 % dni OK (409 `SWEEP_BELOW_THRESHOLD`), import JSON jako DRAFT — struktura walidowana (`seed.waliduj_szablon`: te same reguły co panel, unikalne dni 1–7, klasy, role, zakresy, limity rozmiaru) |

Decyzje: `client_id` w ciele `assign` (jak w zadaniu) → klasa dostępu COACH_ONLY w macierzy, a
własność klienta sprawdza `resolve_client_access` (test: obcy trener 404, klient 403). Panel
szablonów dostępny dla roli COACH lub ADMIN — klasa `COACH_OR_ADMIN` w macierzy (szablony nie są
danymi klientów; admin nadal nie sięga po diety klientów — test). Zapisy w diecie klienta
(`PATCH`, `POST swaps`) wymagają zgody w trybie `write` i wersji ACTIVE. Powiadomień o
przypisaniu nie wysyłam (poza zakresem zadania; łatwa okazja: wpis „Trener przypisał dietę”
przez outbox jak w 0.58.0 — propozycja, nie zrobione). RODO: `diet_assigned` i
`diet_swap_events` w eksporcie „moje dane” i usuwane przy usunięciu konta.
Testy: `tests/test_dieta_api.py` (11), `tests/test_dieta_poprawki.py` (10) + 27 wpisów macierzy
dostępu weryfikowanych wykonaniem.

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
diety (`PrzypisanaDietaTrenera`): dzień po dniu, korekty, historia wymian klienta, blokada wymian
globalna i per posiłek. Podgląd: odpowiedź starszego żądania nigdy nie nadpisuje nowszej (licznik
żądań), pole gramatury przyjmuje przecinek, a pusty wpis nie wysyła 0 g.
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
rola, klasa, g/szt, grupa; usuwanie), „Testuj skalowanie” (sweep zakresu odsłony (do 0.63: 1400–3200), dni OK, flagi per
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
* E2E: test włącza `prefers-reduced-motion` (aplikacja wyłącza wtedy płynne przewijanie i
  animacje kart), a przyciski nisko na długiej karcie przewija na środek ekranu. Pierwotny
  „niestabilny element” miał inną przyczynę: przycisk odsłony z zakresem kcal nie łamał wiersza
  i poszerzał układ telefonu do 423 px, przez co Playwright trafiał w sąsiednią kartę / dolną
  nawigację — naprawione zawijaniem (`PrzypiszDiete.tsx`).
* Preset ręczny: suma kcal z makro ≠ cel ±3 % = OSTRZEŻENIE (§6.4), a cel kcal tygodnia wynika
  z gramów makro (inaczej posiłki nie mają spójnego celu) — wcześniej 422, poprawione po przeglądzie.
* Migawka niesie `round_step` / `unit_g` / `unit_step` składników, więc kandydaci wymiany liczą
  się tak jak w referencji (jawny `round_step` z panelu, nie domyślny klasy).

## Przegląd kodu po etapach (13.09) — wynik i rozliczenie
Przegląd PR #57 uruchomiłem jako workflow wieloagentowy (6 recenzentów × 3 weryfikatorów na
uwagę) PRZED otrzymaniem `ZASADY_budzet_agentow.md`; po jego otrzymaniu przerwałem go w
trakcie weryfikacji (39 agentów, ok. 14,8 mln nowych tokenów kontekstu + 0,36 mln tokenów
odpowiedzi; 131 mln tokenów odczytów z pamięci podręcznej) — **przekroczenie limitu 1 mln / 8
agentów**, rozliczone w odpowiedzi do właściciela. Uwagi zdeduplikowałem i sklasyfikowałem sam,
bez agentów; P0/P1 poprawione i pokryte testami (`tests/test_dieta_poprawki.py`,
`tests/test_dieta_silnik.py`), P2 poniżej.

**P0 (blokowały scalenie) — poprawione:** zapisy trenera w diecie klienta (`PATCH`, `POST swaps`)
przy zgodzie tylko-do-odczytu; wymiany i korekty w wersji ARCHIVED; posiłek zastępczy z innego
profilu / ze szkicu / pusty; druga zamiana tego samego slotu → 500; `overrides` bez walidacji
(tekst, ujemne, 1e12 g, nieznany produkt) → 500 albo bezsensowna migawka; preset `per_kg` bez
g/kg → 500; kcal 500–1000 → liczba zespolona w silniku → 500; pusty dzień / posiłek bez
składników / `round_step` 0 → ZeroDivision → 500; import JSON (duplikat dnia, `macro_pct` z 2
pozycji, nieznana klasa, obiekt zamiast tekstu) → 500 lub błędne dane; `diet_assigned` /
`diet_swap_events` poza eksportem i usuwaniem konta (RODO).

**P1 — poprawione:** seed wywracał start aplikacji po zmianie nazwy produktu w CSV (rozpoznanie
po `id` lub nazwie); kandydaci wymiany ignorowali wykluczenia po nazwie produktu, a pusty napis
w wykluczeniach zerował wszystkie wymiany; jawny `round_step` z panelu nie trafiał do migawki;
po wymianie produktu DYSKRETNEGO „sztuki” liczone jednostką starego produktu; korekta pod
nieistniejący składnik zapisywana jako martwy wpis; DYSKRETNY z domyślnej klasy produktu bez
`unit_g` przechodził; `kcal_min > kcal_max`; `summary` planu nieprzeliczane po korektach;
preset ręczny blokował zamiast ostrzegać (§6.4); składnik NONE z panelu domyślnie wymienialny
(§7.3); brak blokady wymian per posiłek (§7.3); macierz dostępu opisywała panel jako
COACH_ONLY; reguła `group` w drugiej pętli mogła przekroczyć `max_factor`; testy nieczułe na
stałe z §4a.3/§6.3 (dodane); frontend: wyścig odpowiedzi podglądu, połykanie błędów w widoku
klienta, znikający błąd blokady wymian, podwójne kliknięcia (wymiana, panel), fałszywe „brak
posiłków” przy błędzie sieci, wyścig przy przełączaniu odsłon, sprzeczny komunikat „Trener nie
dodał planu”, dialog bez nazwy dostępnej, panel niedostępny w UI dla roli ADMIN, pole gramatury
bez przecinka.

**P2 (bez weryfikacji, do listy):**
1. Trailer `Co-Authored-By` z nazwą modelu w commitach vs reguła KOORDYNACJA.md („bez nazw
   modeli AI w treści commita”) — ta sama praktyka w 156 commitach na `main`; decyzja
   właściciela: zmienić regułę albo trailer.
2. Docstring reguły `group` i plan sesji mówiły „aplikacja włącza” — poprawione na stan
   faktyczny (opcja, domyślnie wyłączona); pytanie otwarte nr 1 pozostaje.
3. Edycja odsłony PUBLISHED (dodanie posiłku/składnika) nie cofa publikacji ani nie wymusza
   ponownego sweepu — propozycja: automatyczny powrót do DRAFT po edycji.
4. `overrides.product` w podglądzie nie jest ograniczony do grupy zamienników (trener może wpisać
   dowolny produkt z bazy) — świadomie: to korekta trenera, nie wymiana klienta.
5. Brak limitu rozmiaru ciała żądania importu poza limitami struktury (7 dni × 12 posiłków ×
   40 składników).

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
python -m pytest tests/test_dieta_seed.py tests/test_dieta_silnik.py tests/test_dieta_api.py tests/test_dieta_poprawki.py
cd ../frontend && npm run build && DZIK_E2E_PORT=8098 npx playwright test e2e/dieta-szablon.spec.ts
```
Aplikacja z flagą (`.env`: `DZIK_DIET_TEMPLATES_ENABLED=true`) seeduje dane przy starcie.

## Propozycje (nie zrobione, poza zakresem)
* Wpis w centrum powiadomień klienta „Trener przypisał dietę” przez outbox.
* Lista zakupów z migawki (dane są w `computed_plan`).
* Statystyki wymian (tabela `diet_swap_events` już je zbiera).


---

# Biblioteka po audycie 14.09 (0.64.0, gałąź `agent/biblioteka-diet`, migracja 35)

Plan: `docs/plan-sesji/biblioteka-diet.md`; rozpoznanie paczki:
`01_rozpoznanie_biblioteki.md`; raport źródłowy: `raport_audytu_biblioteki.md`.

| Etap | Stan | Dowód |
|---|---|---|
| 0 rozpoznanie | ✅ | `01_rozpoznanie_biblioteki.md` |
| 1 silnik v1.1 | ✅ | `silnik.fill_defaults` (3 reguły), `engine.py`/golden z paczki, `test_dieta_silnik` 15 |
| 2 model + migracja 35 + dane + seed | ✅ | kolumny notatek/`source_hash`/`allergens`, 45 JSON + CSV 181 w `dieta/dane`, import zastępujący po skrócie, `test_dieta_seed` 7 (w tym podmiana bez ruszania migawek, sweep 45 odsłon) |
| 3 API + UI | ✅ | `notatki_odslony`, `allergens` w posiłku (silnik → API), `slotLabel`, `NotatkiOdslony` (trener + klient), sweep zakresu odsłony, E2E „Sportowa 5 slotów” |
| 4 zamknięcie | ✅ | CHANGELOG 0.64.0, RELEASE_STATUS, STAN_PRZEKAZANIA; przegląd 3 recenzentów (niżej); scalenie po #65 |

## Decyzje i odstępstwa od planu
* **Sweep w zakresie odsłony** (nie stałe 1400–3200): audyt sprawdzał każdy
  szablon w jego `kcal_min`–`kcal_max` (Masa 2200–4000 nie da się policzyć przy
  1400 kcal — cel posiłku ujemny). Stała była błędem 0.60.0 widocznym dopiero
  przy profilach o innym zakresie.
* **Testy odniesienia**: liczby w `test_dieta_api`/`test_dieta_poprawki` (kcal dnia
  2027 → 2000,3; kurczak 160 → 165 g; 142 → 181 produktów; kandydaci + krewetki;
  skyr bez laktozy ma zamienniki) to zmiana danych referencyjnych po audycie, nie
  asercje dopasowane do wyniku — golden z paczki potwierdza silnik 1:1.
* Fixture API testów wybiera jawnie „Standard zbilansowana / odsłona 1” (przy 9
  profilach kolejność listy nie jest gwarancją).
* Import testowy w panelu używa nowego profilu („Standard (import testowy)”),
  bo odsłony 1–5 Standardu są już zajęte przez bibliotekę.
* `_usun_tresc` kasuje jawnie składniki → posiłki → dni (brak relacji ORM;
  unit-of-work kasował dni przed posiłkami → naruszenie klucza obcego).

## Pytania otwarte (dla właściciela)
1. Etykiety „obiad I / obiad II” dla profilu Sportowa — czy wolisz „obiad” i
   „drugi obiad”?
2. Notatki o suplementacji z biblioteki są pokazywane klientowi (jako treść
   autora). Jeśli mają być tylko dla trenera — jedna linia w `DietaSzablon`.
3. Poprzednie pytania 1–4 z 0.60.0 bez zmian; pytanie 5 (produkty bezlaktozowe)
   zamknięte przez bazę 181.

## Przegląd kodu 0.64.0 (3 recenzentów wsadowo, zasady v2 §3)

**P1 naprawione:** (1) uwagi o suplementacji z dawkami trafiały do klienta jako treść
systemowa bez autora-człowieka (R-10) → API klienta zwraca tylko uwagę o sodzie; trener
widzi całość i przenosi świadomie; (2) seed podmieniał po cichu odsłony edytowane w panelu →
znacznik `source_hash = "panel"` w 7 endpointach edycji, seed pomija i raportuje
`szablony_pominiete`, odsłona sprzed 0.64.0 (bez skrótu) podmieniana z ostrzeżeniem w logu;
(3) import bez limitów `audit`/`supplements_note`/`allergens` → limity + `kcal_min ≤ base ≤
kcal_max`; (4) test podmiany nie tworzył przypisanej diety → test API z migawką, wymianą i
zamianą posiłku; (5) brak testów jednostkowych reguł v1.1 → 3 testy + test alergenów;
(6) alergeny obiecane trenerowi, a renderowane tylko u klienta → podgląd, przeliczony tydzień,
panel; (7) `derived_from` jako slug pliku → „Standard zbilansowana, odsłona 1”; (8) „flag
x/19” przy sweepie zakresu → `kcal_points` z serwera.
**P2 naprawione:** alergeny statyczne po wymianie → liczone ze składników (silnik i korekty);
sprawdzenie produktów przed `_usun_tresc`; odświeżenie `name` przy podmianie, rozjazd
`macro_pct` pliku z profilem = błąd; brzeg zakresu sweepu domykany `kcal_max`; `<select>`
slotu z etykietą; komunikat notatek jako `section` z tytułem i zastrzeżeniem na górze;
odznaki alergenów zamiast wygaszonego tekstu; stała `KCAL_D1_2000` i komentarze przy
zmianach referencyjnych; nazwa testu skyru; test 403 klienta na `/templates` i brak
`audit_json`/`source_hash` w odpowiedziach.
**Po CI (backend-postgres > 45 min):** każdy test startował aplikację na świeżej bazie
i importował 45 odsłon (SQLite 1,5 s/test, PostgreSQL wielokrotnie więcej — job „wisiał”).
Naprawa: `DZIK_DIET_SEED_ON_STARTUP=false` w conftest (testy diety seedują jawnie, ścieżkę
startową sprawdza `test_start_aplikacji_seeduje_biblioteke` i E2E) oraz import wsadowy
(4 flushe na odsłonę zamiast ~200). Wniosek do zasad: seed przy starcie liczyć „× liczba
testów”, zanim trafi do `main.py`.
**P2 odnotowane:** notatki nie są w migawce (klient z wcześniej przypisaną dietą po podmianie
widzi nowe notatki przy starym planie) — do rozważenia kopiowanie do migawki; współbieżny
seed na dwóch maszynach Fly przy rolling deploy → `IntegrityError` i rollback jednej
(dane bezpieczne, jeden start zgłosi błąd); `INSTRUKCJA_TRENERA/KLIENTA` nie opisują modułu
szablonów diet (od 0.60.0) — do uzupełnienia przed włączeniem flagi na produkcji;
`test_powtorny_seed_nie_dubluje` częściowo dubluje test główny; typografia cudzysłowu w
`types.ts:1667`.

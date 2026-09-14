# PROMPT dla sesji piszącej — „Wymiany produktów” (przycisk ↔ wymień w zakładce Dieta ma dawać zamienniki: grupy pokrewne + zgodność makro i funkcji w posiłku)

> Skopiuj ten plik w całości jako pierwszą wiadomość do sesji piszącej.
> Rozpoznanie kodu i **pomiar** są już wykonane (sekcje 2–3) — nie powtarzaj ich
> od zera, tylko **zweryfikuj** linie i **powtórz pomiar** własnym skryptem
> przed zmianą i po niej (to jest dowód rundy, nie testy).

---

Przeczytaj kolejno: `/AGENTS.md`, `/CLAUDE.md`,
`apps/dzik-os/docs/KARTA_WSPOLPRACY.md`, `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
`apps/dzik-os/docs/KOORDYNACJA.md`, `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`,
a potem `apps/dzik-os/docs/diet-module/PROGRESS.md` i
`apps/dzik-os/docs/diet-module/instrukcja_szablony_diet.md`.

**Rola:** aktywny piszący (wyznaczony przez właściciela tą wiadomością).
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core (`hos_engine/`, `tests/` w korzeniu)
jest nietykalny — 275 testów Core musi zostać zielone.

**WARUNEK STARTU:** gałąź `agent/biblioteka-diet` (0.64.0, migracja 35, 181
produktów, silnik v1.1) musi być **scalona do `main`** zanim odgałęzisz to zadanie.
Powód: ona zmienia `dieta/silnik.py`, `dieta/dane/produkty.csv` i seed — czyli
dokładnie pliki tej rundy; równoległa praca = pewny konflikt znaczeniowy (STOP wg
karty). Sama biblioteka zmniejsza już odsetek składników bez zamiennika z **31 %
do 11 %** (pomiar niżej) — to jest pierwszy krok naprawy i **nie wymaga kodu**.
Jeśli PR biblioteki nie jest scalony: zgłoś to właścicielowi i nie zaczynaj.

**Gałąź:** `agent/wymiany-produktow` od aktualnego `main` (po scaleniu biblioteki).
Pierwszy commit wyłącznie `apps/dzik-os/docs/plan-sesji/wymiany-produktow.md`
(szkic w `plan-sesji_wymiany-produktow.md` obok tego promptu — uzupełnij rezerwacje
sprawdzone na żywo). Po pushu od razu draft PR `[WRITER] Wymiany produktów`.
Dopiero potem kod.

**Rezerwacje (sprawdź w `db.py`, `CHANGELOG.md` i tabeli §2 `STAN_PRZEKAZANIA.md`
tuż przed zmianą):** proponowana **wersja wg kolejności scalania z `README.md` tego katalogu**
(numer wersji musi rosnąć w kolejności scalania — kontrola `changelog`). **Migracja:
brak** w wariancie rekomendowanym (powiązania grup jako plik danych ładowany przez
silnik; bez nowych kolumn). Jeśli w trakcie okaże się potrzebna (np. kolumna na
produkcie) — weź kolejny wolny numer i odnotuj w planie i w §2; nie zgaduj.

Nie rozwiązuj konfliktów automatycznie, nie rób force-pusha, commituj po polsku,
bez nazw modeli AI w treści commita. Nie scalaj własnego PR-a.

---

## 1. Problem (słowami właściciela, 14.09.2026)

> Klient w zakładce Dieta przy elementach składowych posiłków ma przycisk, który
> powinien dawać mu szansę na wymianę jakiegoś produktu. Teraz to nie działa.
> Żeby to uruchomić, trzeba powiązać pokrewne grupy towarowe, by makro i funkcja
> w posiłku się zgadzały.

## 2. Diagnoza — co naprawdę jest zepsute (zmierzone, nie oszacowane)

Przycisk **jest podpięty od końca do końca** i dla części składników działa (E2E
`dieta-szablon.spec.ts` dowodzi: kurczak → indyk). Zepsuta jest **podaż kandydatów**,
z czterech niezależnych przyczyn. Kolejność wg wagi:

| # | Przyczyna | Skala (Standard v1, 2000 kcal, `main` 0.63.0) | Gdzie |
|---|---|---|---|
| 1 | **Bramka tolerancji posiłku jest absolutna.** Kandydat przechodzi tylko, gdy posiłek *po* wymianie mieści się w `TOL_MEAL` (±8 %/40 kcal, P ±5 g, F ±4 g, C ±10 g) — tym samym `check()`, którym posiłek już był oceniony. **Posiłek, który już jest OSTRZEŻENIE/POZA ZAKRESEM, nigdy nie dostanie kandydata** — czyli wymiana jest martwa dokładnie tam, gdzie klient jej najbardziej potrzebuje. | 25 z 34 pustych list (21 w posiłkach już poza tolerancją) | `backend/dzik_os/dieta/silnik.py` l. 361–396 (`swap_candidates`), bramka l. ~390 |
| 2 | **Przycisk nie jest renderowany dla składników z rolą `NONE`** (warzywa, przyprawy, dodatki), bo `swappable` domyślnie = `role in ("P","C","F")`. To **124 z 232** składników szablonu — klient nie może zamienić brokułu na kalafior, choć oba są w `warzywa_gotowane`. | 124/232 składników bez przycisku | `backend/dzik_os/dieta/seed.py` l. ~234; `DietaSzablon.tsx` l. 89–92 (cztery warunki AND: `swappable && swaps_enabled && !swaps_locked && class !== "STAŁY"`) |
| 3 | **Grupy-singletony** — produkt sam w swojej `substitution_group` nigdy nie ma kandydata. | `main`: 8 singletonów (Jogurt grecki 10 %, Hummus, Płatki owsiane, Awokado, Gorzka czekolada, Bulion, WPC 80, Szynka z indyka); po bibliotece: 3 (Jogurt grecki 10 %, Awokado, Gorzka czekolada) | `dieta/dane/produkty.csv` kolumna `substitution_group` |
| 4 | **Zgodność „funkcji” = tylko twarde przecięcie `cooking_tags`**; brak przecięcia = odpad (np. tuńczyk z puszki vs ryby surowe w `ryba_chuda`). Nie ma pojęcia „grupy pokrewnej” — kandydat musi być z **dokładnie tej samej** grupy (`q.substitution_group != p.substitution_group → continue`). | 1 z 34 na `main`, ale to jest bariera dla całego pomysłu właściciela | `silnik.py` l. ~372 (A) i ~378 (B) |

**Pomiar (silnik + prawdziwe dane seeda, składniki z rolą P/C/F = 108):**

| Stan | posiłki nie-OK | składników bez ŻADNEGO kandydata |
|---|---|---|
| `main` 0.63.0, 1600 kcal | 5/28 | 27 |
| `main` 0.63.0, 2000 kcal | 6/28 | **34 (31 %)** |
| `main` 0.63.0, 2600 kcal | 3/28 | 31 |
| po `agent/biblioteka-diet` (181 produktów, silnik v1.1), 2000 kcal | 0/28 | **12 (11 %)** |

Wnioski: (a) scalenie biblioteki to pierwszy, bezkodowy krok; (b) resztę załatwia
przebudowa `swap_candidates` + dane powiązań grup + przycisk dla roli `NONE`.

**Ważne rozróżnienie (nie pomyl):** `docs/diet-module/PROGRESS.md` pyta „włączyć
regułę `group` domyślnie?”. To jest `DietTemplateIngredient.group_name`
(wspólny współczynnik skalowania ciasta/marynaty — `enforce_groups`, `silnik.py`
l. 194–239), **nie** grupa zamienników. Włączenie jej nie da ani jednego kandydata.
Grupa zamienników to `DietProduct.substitution_group` (`models.py` l. ~1847).

**Drugi przepływ diety — decyzja właściciela 14.09 (druga tura):** kreator diety
schodzi na bok („wymaga wielkiej pracy, możemy go ukryć”) — ukrycie to osobne, małe
zlecenie 3 (`PROMPT_writer_ukryj-kreator.md`). Plan z kreatora (`NutritionPlan`,
`Nutrition.tsx` l. 65–215) ma „zamienniki” jako **tekst** (`m.swaps`, l. 140) bez
przycisku i to zadanie go nie dotyka. **Klient jest na diecie z szablonu** — pytanie 1
z §9 jest rozstrzygnięte. Natomiast **katalog pojedynczych produktów trenera zostaje
i staje się źródłem nowych zamienników** — patrz §5a.

## 3. Rozpoznanie — fakty z kodu (zweryfikuj linie po scaleniu biblioteki)

| Co | Gdzie |
|---|---|
| Przycisk i arkusz wymiany u klienta | `frontend/src/pages/client/DietaSzablon.tsx` l. 37–57 (`otworz` → `GET /api/diet/assigned/{id}/swaps?day&meal&ingredient`; `wymien` → `POST …/swaps`), l. 89–92 (warunki przycisku), l. 104–108 (stany: „Szukam…”, `blocked`, „Brak bezpiecznego zamiennika, napisz do trenera”) |
| Typy | `frontend/src/types.ts` l. 1696–1735 (`DietIngredientOut`, `DietMealOut`, `DietSwapCandidate {product, product_id, grams, macros}`) |
| API wymian | `backend/dzik_os/routers/diet.py` l. 325–349 (GET kandydaci + `blokada`), l. 352–400 (POST: kandydaci liczeni ponownie serwerowo, `to_product_id` musi być na liście → inaczej 422; gramatura walidowana `TOL_MEAL`; zapis `overrides_json["ingredients"]["day:meal:ing"]` + `DietSwapEvent` + audyt `DIET_SWAP`), l. 403–423 (PATCH `swaps_enabled`, `meal_swaps_enabled`) |
| Serwis | `backend/dzik_os/dieta/serwis.py` l. 252–270 (`kandydaci_wymiany`: `posilek_silnika` z migawki po korektach, wykluczenia alergenów/diet/„nie lubię” po nazwie), l. 31–37 (`produkt_silnika`: `substitution_group` → `""` gdy brak) |
| Silnik (kopia 1:1 prototypu `docs/diet-module/engine.py`) | `backend/dzik_os/dieta/silnik.py`: `TOL_MEAL`/`TOL_DAY` l. 38–39, `check` l. 183–188, `swap_candidates` l. 361–396; na gałęzi biblioteki dodatkowo limity porcji (mięso/ryby 300 g, jajka ≤4, tłuszcz krok 1 g) l. ~89–108 i `alergeny()` l. ~253 |
| Model produktu | `models.py` l. 1836–1862 `DietProduct` (`category`, `substitution_group`, makra/100 g, `cooking_tags` CSV z `*` jako wildcard, `allergens`, `diet_exclusions`, `default_scaling`, `source*`); rola makro jest **per składnik** (`DietTemplateIngredient.macro_role`, `group_name`, `swappable` l. 1940–1947), nie per produkt |
| Dane | `backend/dzik_os/dieta/dane/produkty.csv` (po bibliotece 181 wierszy, 40 grup; lista grup i członków niżej), `dane/szablon_standard_v1.json` (7 dni, 28 posiłków, 232 składniki), po bibliotece `dane/szablony/*.json` (45 odsłon) i `dane/biblioteka_index.json`; `docs/diet-module/subst_maps.json` (mapa 1:1 bez laktozy/glutenu użyta **offline** do generowania odsłon — nie jest w runtime) |
| Testy do świadomej aktualizacji | `backend/tests/test_dieta_silnik.py` l. 152 (`test_swap_candidates_nie_wyprowadza_poza_tolerancje_i_skyr_bez_laktozy_pusty` — złota lista `[Pierś z indyka, Schab, Polędwiczka] / [155,150,170]` **i pusta lista dla skyru bez laktozy zapisana jako poprawne zachowanie** — po bibliotece skyr bez laktozy istnieje, więc ten przypadek zmienia sens), l. 189 (`test_stale_silnika_identyczne_z_prototypem` — **nie zmieniaj `TOL_MEAL`/`TOL_DAY`**), l. 209; `backend/tests/test_dieta_api.py` l. 194 (`candidates == []` i `blocked is None` dla laktozy), l. 231; `test_dieta_poprawki.py` l. 65, 229, 248; E2E `frontend/e2e/dieta-szablon.spec.ts` l. 23–60 (jedyny ćwiczony składnik: kurczak → indyk) |
| Flaga | `DZIK_DIET_TEMPLATES_ENABLED` — produkcja `true` (`fly.toml` l. 37), testy w `conftest.py`; `routers/diet.py` l. 53–55 `wymagaj_modulu()` |
| Prototyp referencyjny | `docs/diet-module/engine.py` — po tej rundzie **silnik przestaje być 1:1 z prototypem w `swap_candidates`**: odnotuj to w `docs/diet-module/PROGRESS.md` i w docstringu funkcji (nie udawaj zgodności) |

**Grupy zamienników po bibliotece (181 produktów, 40 grup) — do tabeli powiązań:**
białko_chude (7: pierś kurczaka/indyka, polędwiczka, schab, krewetki, stek, wątróbka);
białko_mielone (2); białko_proszek (2); białko_roślinne (3: tofu, tempeh, seitan);
białko_tłuste (2: udo kurczaka, kiełbasa drobiowa); dodatek_tłuszczowy (4: śmietana 18 %,
oliwki, mleczko kokosowe, śmietanka bez laktozy); jajka (2); kasza_ryż (9); kiszonki (2);
makaron (4); mleko (4); mąka (4); nabiał_chudy (15, w tym 8 bez laktozy);
nabiał_tłusty (1: jogurt grecki 10 %); nasiona (4); orzechy (3); orzechy_pasty (2: masło
orzechowe, tahini); owoce (8); owoce_jagodowe (4); pasta_smarowanie (2: hummus, serek
śmietankowy light); pieczywo (7); pomidory_przetwory (3); przyprawa (16); płatki (5);
płyn (2: buliony); ryba_chuda (4, w tym tuńczyk z puszki); ryba_tłusta (5, w tym łosoś
wędzony, sardynki); ser (7); skrobiowe (2: ziemniak, batat); sos (5); strączki (5);
słodycze (1: gorzka czekolada); słodzik (5: miód, dżem, daktyle, rodzynki, syrop klonowy);
tłuszcz (4: masło, oliwa, rzepakowy, skwarki); tłuszcz_roślinny (1: awokado);
warzywa_aromat (2: cebula, por); warzywa_gotowane (12); warzywa_liściaste (3);
warzywa_surowe (6); wędlina (2).

## 4. Decyzje projektowe (propose-only → właściciel zatwierdził kierunek tą wiadomością)

1. **Dwa poziomy zamienników.** Poziom 1 = ta sama `substitution_group` (jak dziś).
   Poziom 2 = **grupa pokrewna** z nowego pliku danych
   `backend/dzik_os/dieta/dane/grupy_pokrewne.json` (symetryczne pary + krótki powód
   po polsku + `source`). Kandydaci poziomu 1 zawsze przed poziomem 2; w UI etykieta
   „z tej samej grupy” / „grupa pokrewna: kasza_ryż”.
2. **„Funkcja w posiłku” = trzy sprawdzenia, nie jedno:**
   * **rola makro** — dla składnika z rolą P/C/F kandydat musi mieć **dominujące
     makro zgodne z rolą** (udział kcal z tego makro największy; dla P wystarczy
     `protein_100 ≥ 15 g`, bo nabiał chudy ma dużo wody); poziom 2 bez wyjątków,
     poziom 1 jak dotąd (`per > 0`);
   * **metoda przygotowania** — `cooking_tags` muszą się przecinać; `*` i **pusty**
     zestaw tagów traktuj jako wildcard (dziś pusty = odpad); na poziomie 2 wildcard
     kandydata **nie** wystarcza — musi przeciąć tagi składnika, chyba że składnik
     sam ma `*`;
   * **klasa i limity porcji** — gramatura kandydata mieści się w
     `min_factor..max_factor` składnika (po limitach v1.1: mięso/ryby ≤ 300 g,
     jajka ≤ 4) i jest zaokrąglona `round_step`; poza zakresem = odpad z powodem.
3. **Bramka posiłku „nie pogarsza” zamiast absolutnej.** Kandydat przechodzi, gdy
   posiłek po wymianie **mieści się w `TOL_MEAL`** ALBO gdy **żadne odchylenie
   (kcal, P, F, C) nie jest większe co do modułu niż przed wymianą** (a więc
   w posiłku już poza tolerancją wymiana neutralna lub poprawiająca jest
   dozwolona). `TOL_MEAL`/`TOL_DAY` **bez zmian** (test stałych). Odpowiedź niesie
   `meal_delta` (kcal/P/F/C po − przed) do pokazania klientowi.
4. **Rola `NONE` dostaje przycisk.** Składniki `NONE` (warzywa, przyprawy,
   kiszonki, dodatki) są wymienialne **na poziomie 1** (ta sama grupa), gramatura
   **1:1 wagowo** (funkcja = objętość/smak, nie makro), a potem ta sama bramka
   posiłku. `swappable` w seedzie: `True` dla P/C/F i dla `NONE`, gdy grupa ma ≥ 2
   produkty; `STAŁY` nadal bez przycisku (warunek frontu zostaje). **Istniejące
   przypisania mają `swappable` w migawce** — nie przepisuj migawek; policz
   `swappable` efektywnie przy odczycie (`dieta_out`) tą samą regułą, żeby
   przypisania sprzed rundy też dostały przycisk.
5. **Puste listy mają powód.** GET zwraca `reason` ∈ {`SINGLETON` (grupa bez innych
   produktów i bez grup pokrewnych), `EXCLUDED` (wszystko odpadło przez alergeny/
   wykluczenia/„nie lubię”), `FUNCTION` (nic nie pasuje metodą/rolą), `TOLERANCE`
   (kandydaci istnieją, ale każdy pogarsza posiłek), `PORTION`} + liczby odrzuconych
   per powód. Front pokazuje właściwy komunikat po polsku (np. „Zamienniki są, ale
   każdy zepsułby makra tego posiłku — poproś trenera o korektę posiłku”) zamiast
   jednego „Brak bezpiecznego zamiennika”. To jest zasada „nic nie udaje, że działa”.
6. **Ranking:** poziom (1 przed 2) → suma |Δ| posiłku po wymianie → odległość
   makro produktu (jak dziś). Limit `n` bez zmian; front pokazuje maks. 5.
7. **Bezpieczeństwo bez zmian:** POST nadal liczy kandydatów serwerowo i odrzuca
   `to_product_id` spoza listy (422); blokady trenera (`swaps_enabled`,
   `swaps_locked`, ARCHIVED) bez zmian; wykluczenia alergenów **przed** grupami
   pokrewnymi (poziom 2 nie może przemycić alergenu).
8. **Dane powiązań są propozycją do przeglądu trenera/dietetyka.** Plik
   `grupy_pokrewne.json` ma pole `status: "PROPOZYCJA"` i `reviewed_by: null`;
   panel szablonów pokazuje tabelę powiązań **tylko do odczytu** (edycja = osobna
   runda). Nie wymyślaj powiązań spoza tabeli w §5 bez zapisania powodu.
9. **Silnik przestaje być 1:1 z prototypem** w `swap_candidates` — zapisz to w
   `PROGRESS.md`, docstringu i CHANGELOG; pozostałe funkcje (skalowanie, `check`,
   `fit_*`) bez zmian.
10. **Zero AI.** Dobór kandydatów jest regułowy i deterministyczny (test).

## 5. Tabela powiązań grup — punkt startowy dla `grupy_pokrewne.json`

Pary symetryczne. Kolumna „funkcja” to powód, który trafia do pliku. Powiązania
oznaczone (?) wymagają decyzji właściciela/trenera — w v1 wpisz je z
`status: "PROPOZYCJA_NIEPEWNA"` i **domyślnie wyłączone** (`enabled: false`).

| Grupa A | Grupa B | Funkcja / powód |
|---|---|---|
| białko_chude | białko_tłuste | to samo danie główne, inne mięso; tolerancja rozstrzygnie tłuszcz |
| białko_chude | białko_mielone | ta sama rola P w obiedzie |
| białko_chude | ryba_chuda | białko obiadowe, obróbka termiczna |
| białko_chude | białko_roślinne | tofu/tempeh/seitan jako białko dania |
| ryba_chuda | ryba_tłusta | ryba za rybę; F rozstrzyga bramka |
| białko_tłuste | ryba_tłusta | białko z tłuszczem |
| białko_mielone | białko_roślinne (?) | tempeh/tofu kruszone |
| strączki | białko_roślinne | białko roślinne w daniu |
| strączki | kasza_ryż | C w obiedzie (soczewica ↔ kasza) |
| kasza_ryż | makaron | dodatek skrobiowy |
| kasza_ryż | skrobiowe | dodatek skrobiowy |
| makaron | skrobiowe | dodatek skrobiowy |
| płatki | kasza_ryż | owsianka ↔ jaglanka; `cooking_tags` rozstrzyga |
| pieczywo | płatki (?) | śniadanie C — funkcja różna (kanapka vs miska) |
| mąka | płatki (?) | placki/naleśniki |
| nabiał_chudy | nabiał_tłusty | jogurt za jogurt |
| nabiał_chudy | białko_proszek | P w koktajlu/misce |
| nabiał_chudy | mleko | nabiał płynny |
| nabiał_chudy | jajka | P śniadaniowe |
| jajka | białko_roślinne | tofucznica |
| jajka | wędlina | P w kanapce |
| wędlina | białko_chude | plaster mięsa ↔ pieczone mięso |
| wędlina | ser | dodatek białkowy do pieczywa |
| ser | nabiał_tłusty | tłusty nabiał |
| ser | pasta_smarowanie | smarowidło/dodatek do pieczywa |
| pasta_smarowanie | orzechy_pasty | smarowidło |
| pasta_smarowanie | nabiał_chudy | serek wiejski jako smarowidło |
| tłuszcz | tłuszcz_roślinny | tłuszcz dodany (oliwa ↔ awokado) |
| tłuszcz | dodatek_tłuszczowy | F w daniu |
| tłuszcz | orzechy_pasty | F do miski/kanapki |
| orzechy | nasiona | F w misce/sałatce |
| orzechy | orzechy_pasty | F |
| orzechy | tłuszcz_roślinny | F |
| słodycze | orzechy | przekąska F/C |
| słodycze | słodzik (?) | słodka przekąska |
| słodzik | owoce | słodzenie (daktyle, rodzynki ↔ owoc) |
| owoce | owoce_jagodowe | owoc za owoc |
| warzywa_gotowane | warzywa_surowe | warzywo za warzywo (`cooking_tags`) |
| warzywa_gotowane | warzywa_liściaste | warzywo |
| warzywa_surowe | warzywa_liściaste | warzywo surowe |
| warzywa_surowe | kiszonki | dodatek surowy/kwaśny |
| warzywa_gotowane | warzywa_aromat | warzywo do duszenia |
| sos | pomidory_przetwory | baza sosu |
| sos | przyprawa | doprawienie |
| mleko | białko_proszek (?) | koktajl |

Bez powiązań (zostają singletonami poziomu 2 → `reason: SINGLETON`): `płyn`,
`kiszonki`↔inne poza warzywami surowymi, `przyprawa`↔inne poza sosem.

## 5a. Katalog produktów trenera jako źródło zamienników (decyzja właściciela 14.09)

Właściciel: *„mamy dostęp do listy pojedynczych produktów, które można by skorelować
z tymi, co chcemy wymieniać w szablonie”*. Fakty:

* Katalog: `FoodProduct` (`models.py` l. 841–865) — per trener (`coach_id`), wgrywany
  przyciskiem `POST /api/coach/food-products/load-builtin` (`routers/food_catalog.py`
  l. 561) z wbudowanej listy `food_catalog_data.FOOD_ROWS_ALL` (**2058 pozycji**,
  16 kategorii: Mięso i drób 226, Warzywa 226, Nabiał 183, Ryby 154, Owoce 146, Zboża
  i pieczywo 133, Przyprawy i dodatki 124, Przekąski 116, Kasze/ryż/makarony 104,
  Napoje 93, Strączkowe 76, Orzechy 74, Odżywki 66, Tłuszcze 47, Jaja 31, Dania gotowe
  259). Pola: nazwa, kategoria, kcal/P/F/C/błonnik na 100 g, porcja, jednostka
  sztukowa, źródło. **Brak:** `substitution_group`, `cooking_tags`, `allergens`,
  `diet_exclusions` — czyli dokładnie tego, na czym stoi bezpieczeństwo wymian.
* Dlatego **nie robimy złączenia w czasie działania** (silnik nie może brać
  kandydatów z tabeli, która nie zna alergenów i jest edytowalna per trener).
  Korelacja to **jednorazowe, przeglądane przez człowieka wzbogacenie katalogu diet**
  (`DietProduct`), a silnik po tej rundzie nadal działa wyłącznie na `DietProduct`.

**Mechanizm (propose-only, trzy kroki):**

1. **Narzędzie korelacji** `apps/dzik-os/tools/koreluj_katalog.py` — bez bazy, czyta
   `FOOD_ROWS_ALL` i `dieta/dane/produkty.csv`, pisze
   `docs/diet-module/katalog_korelacja_propozycja.csv` z kolumnami:
   `name, category, kcal_100, protein_100, fat_100, carbs_100, fiber_100,
   proposed_group, confidence (WYSOKA|ŚREDNIA|NISKA), method (DUPLIKAT|SŁOWO_KLUCZOWE|
   KATEGORIA), proposed_cooking_tags, proposed_allergens, proposed_diet_exclusions,
   default_scaling, reason, decision (puste → właściciel/trener wpisuje TAK/NIE)`.
   Reguły (deterministyczne, w kodzie z testem):
   * **DUPLIKAT** — znormalizowana nazwa (`normalize_name` z `food_catalog`) pokrywa
     się z istniejącym `name_pl` → pomiń (nie dubluj produktu w innej grupie).
   * **SŁOWO_KLUCZOWE** → ŚREDNIA: np. „mielon” → `białko_mielone`; „szynka|wędlina|
     kiełbasa|polędwica wędzona” → `wędlina`; „udo|skrzydł|karkówka|boczek|kaczka|gęś”
     → `białko_tłuste`; „łosoś|makrela|śledź|sardynk|pstrąg|halibut” → `ryba_tłusta`;
     „ser|mozzarella|feta|parmezan|gouda|camembert” → `ser`; „mleko|napój sojowy|owsiany|
     migdałowy” → `mleko`; „śmietan” → `dodatek_tłuszczowy`; „płatk|musli|granola” →
     `płatki`; „mąk” → `mąka`; „makaron” → `makaron`; „ziemniak|batat” → `skrobiowe`;
     „kiszon” → `kiszonki`; „sałata|szpinak|rukola|jarmuż|roszponka” →
     `warzywa_liściaste`; „cebul|por|czosnek” → `warzywa_aromat`; „pomidor|ogórek|
     papryka|rzodkiew|seler naciowy” → `warzywa_surowe`; „borów|malin|truskaw|jagod|
     porzecz|jeżyn” → `owoce_jagodowe`; „suszon|daktyl|rodzynk|miód|dżem|syrop” →
     `słodzik`; „tofu|tempeh|seitan” → `białko_roślinne`; „hummus” →
     `pasta_smarowanie`; „masło orzechowe|pasta|tahini” → `orzechy_pasty`; „nasion|
     pestk|siemi|chia|słonecznik|sezam” → `nasiona`; „awokado” → `tłuszcz_roślinny`;
     „odżywka białkowa|WPC|WPI|izolat” → `białko_proszek`; „ketchup|musztarda|sos” →
     `sos`; „passata|koncentrat|pomidory z puszki” → `pomidory_przetwory`.
   * **KATEGORIA** → NISKA (domyślna grupa kategorii): Mięso i drób → `białko_chude`;
     Ryby → `ryba_chuda`; Jaja → `jajka`; Nabiał → `nabiał_chudy` (`nabiał_tłusty`, gdy
     tłuszcz ≥ 5 g/100 g); Zboża i pieczywo → `pieczywo`; Kasze/ryż/makarony →
     `kasza_ryż`; Warzywa → `warzywa_gotowane`; Owoce → `owoce`; Strączkowe →
     `strączki`; Orzechy → `orzechy`; Tłuszcze → `tłuszcz`; Przyprawy i dodatki →
     `przyprawa`. **Dania gotowe, Napoje (poza mlekami), Odżywki (poza białkiem),
     Przekąski i słodycze → `decision: NIE` z góry** (nie są zamiennikami składnika
     szablonu; rozstrzyga człowiek, jeśli chce inaczej).
   * `proposed_cooking_tags` = najczęstszy zestaw tagów **grupy docelowej** w
     `produkty.csv` (nie wymyślaj nowych tagów; słownik tagów odczytaj z pliku).
   * `proposed_allergens` / `proposed_diet_exclusions` — słownik **wyłącznie** z
     istniejącego CSV (np. `milk`, `lactose`, `gluten`, `eggs`, `fish`, `nuts`, `soy`,
     `meat`, …; sprawdź dokładne tokeny), heurystyki po nazwie i kategorii; każdy
     wiersz z pustym alergenem w kategorii, gdzie alergen jest typowy (Nabiał, Zboża,
     Ryby, Orzechy, Jaja, Strączkowe/soja), dostaje `confidence: NISKA`.
   * `default_scaling` = jak w grupie docelowej (`LINIOWY`/`DYSKRETNY`/`STAŁY`).
2. **Przegląd człowieka:** właściciel/trener wypełnia `decision` w CSV (TAK/NIE, może
   poprawić grupę i alergeny). To jest dokument do zlecenia zwrotnego — writer **nie
   zatwierdza sam** wierszy NISKA. Wiersze `WYSOKA`/`ŚREDNIA` bez alergenów do
   uzupełnienia można zaproponować jako `TAK` (właściciel potwierdza jednym słowem).
3. **Import zatwierdzonych:** `dieta/dane/produkty_z_katalogu.csv` (te same kolumny
   co `produkty.csv`, `source = "katalog_trenera"`, `source_id` = nazwa wbudowana,
   `source_desc` = wiersz propozycji) ładowany przez `dieta/seed.py` **po** głównym
   CSV, idempotentnie po `name_pl`; osobny plik = brak konfliktu z biblioteką
   i jawne pochodzenie; wpis w `package-data`. Test integralności jak dla głównego
   CSV (unikalność po znormalizowanej nazwie, zakresy, kcal↔makra, grupa istnieje,
   tokeny alergenów ze słownika).

**Bezpieczeństwo:** wiersz bez decyzji TAK nigdy nie trafia do seeda; wiersz z alergenem
„do uzupełnienia” nie może być zaimportowany (test), bo filtr alergenów wymian musi
pozostać kompletny. Pomiar po imporcie: ile z 12 pustych list (po bibliotece) znika
dzięki katalogowi, a ile dzięki grupom pokrewnym — osobno w tabeli CHANGELOG.

**Kolejność w rundzie:** narzędzie i CSV propozycji powstają w etapie 1 (dane), żeby
właściciel mógł przeglądać równolegle z pracą nad silnikiem; import zatwierdzonych
wierszy to ostatni etap przed zamknięciem (albo osobny, malutki PR, jeśli przegląd
potrwa dłużej niż runda — nie blokuj scalenia silnika na przeglądzie CSV).

## 6. Co dokładnie zbudować

### Backend
* `dieta/dane/grupy_pokrewne.json` (schemat: `{"version": 1, "status": "PROPOZYCJA",
  "reviewed_by": null, "links": [{"a": "...", "b": "...", "reason": "...", "enabled":
  true, "status": "PROPOZYCJA"}]}`) + `dieta/grupy.py` (ładowanie, walidacja: obie grupy
  istnieją w `produkty.csv`, brak duplikatów, symetria) + wpis w `package-data`
  (**strażnik `tests/test_pakietowanie.py` — lekcja 0.57.1**).
* `silnik.py`: `swap_candidates(meal_result, ing_index, products, exclusions, n,
  related=None, current_dev=None)` wg §4 pkt 1–6, zwracająca `{product, grams, macros,
  tier, meal_delta}` + osobno statystykę odrzuceń `{reason: count}` (druga funkcja
  `swap_candidates_z_powodami` albo tuple — jedna zasada: ta sama ścieżka dla GET
  i POST).
* `serwis.py::kandydaci_wymiany` — przekazuje powiązania i bieżące odchylenie
  posiłku; `dieta_out` — `swappable` efektywne (§4 pkt 4).
* `routers/diet.py` GET `/swaps` → `{candidates: [{…, tier, meal_delta}], blocked,
  reason, rejected: {…}}`; POST bez zmian kontraktu poza tym, że akceptuje kandydata
  z listy (poziom 1 lub 2) i zapisuje `tier` w `DietSwapEvent`/override (`kind:
  "swap"`, pole `tier` w JSON — bez migracji, jeśli override/event trzymają JSON;
  sprawdź).
* `seed.py`: `swappable` wg §4 pkt 4 (idempotentnie — seed po `name_pl`, nie
  przepisuje istniejących migawek).
* **Korelacja katalogu (§5a):** `tools/koreluj_katalog.py` + test reguł
  (`backend/tests/test_koreluj_katalog.py`: duplikat pomijany, słowo kluczowe przed
  kategorią, kategorie NIE z góry, tagi z grupy docelowej, tokeny ze słownika),
  `dieta/dane/produkty_z_katalogu.csv` (tylko wiersze TAK), seed po głównym CSV,
  `package-data`, test integralności.
* **Pomiar jako test-strażnik:** `tests/test_dieta_wymiany_pokrycie.py` — dla
  Standard v1 przy 1600/2000/2600 kcal liczy odsetek składników wymienialnych bez
  kandydata i porównuje z progiem **wpisanym z pomiaru po zmianie + margines**
  (komentarz z liczbą i datą pomiaru; nie „≤ 0”, bo to kłamstwo, i nie 50 %, bo to
  ozdoba). Osobno: żaden kandydat nie pogarsza posiłku (własność z §4 pkt 3),
  poziom 2 nigdy nie przemyca alergenu, wynik deterministyczny.

### Frontend
* `DietaSzablon.tsx`: przycisk także dla `NONE` (wg `swappable` z serwera); arkusz:
  etykieta poziomu, `meal_delta` po polsku („posiłek: −12 kcal, białko +1 g”), lista
  do 5; komunikat pusty wg `reason` (5 wariantów po polsku); link do wiadomości
  zostaje przy `TOLERANCE`/`SINGLETON`.
* `types.ts`: `DietSwapCandidate` + `tier`, `meal_delta`; odpowiedź GET + `reason`,
  `rejected`.
* Panel trenera (`pages/coach/SzablonyDiet.tsx` albo `DietTemplates.tsx` — sprawdź,
  który jest żywy po bibliotece): karta „Grupy pokrewne (propozycja do przeglądu)”
  tylko do odczytu; historia wymian klienta pokazuje poziom.

### Testy
* Aktualizacja świadoma: `test_dieta_silnik.py` l. 152 (nowa złota lista z powodem
  w commicie; przypadek „skyr bez laktozy” → **niepusty** po bibliotece, sprawdź, że
  kandydat jest `lactose`-free), `test_dieta_api.py` l. 194 (analogicznie).
* Nowe: poziom 2 działa (płatki owsiane → kasza jaglana / płatki jaglane),
  `NONE` (brokuł → kalafior 1:1), „nie pogarsza” w posiłku poza tolerancją,
  `reason` dla każdego z 5 przypadków, wildcard pustych tagów, POST odrzuca produkt
  spoza listy także na poziomie 2, alergen nie przechodzi poziomem 2, blokady trenera
  bez zmian, `swappable` efektywne dla starej migawki.
* E2E `dieta-szablon.spec.ts`: dołóż scenariusz na składniku, który na `main` nie
  miał kandydata (wybierz z pomiaru, np. „Płatki owsiane” albo warzywo `NONE`) —
  klient widzi etykietę poziomu i deltę posiłku, wymienia, trener widzi poziom
  w historii.

### Dokumentacja (etap zamknięcia)
`CHANGELOG.md` 0.67.0 (z liczbami: przed/po), `docs/diet-module/PROGRESS.md`
(rozdział „Wymiany v2”: pomiar, odejście od 1:1 z prototypem, pytania otwarte),
`docs/diet-module/instrukcja_szablony_diet.md` (jak działa wymiana, poziomy,
powody), `INSTRUKCJA_KLIENTA.md` (Dieta → wymiana), `INSTRUKCJA_TRENERA.md`
(grupy pokrewne, jak zgłosić poprawkę), `BAZA_PRODUKTOW.md` (dwa nowe pliki danych: powiązania grup i produkty z katalogu, z pochodzeniem),
`RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`, plan sesji.

## 7. Czego świadomie NIE robimy

* Nie zmieniamy `TOL_MEAL`/`TOL_DAY` ani skalowania (`fit_*`, `enforce_groups`).
* Nie przeliczamy pozostałych składników posiłku po wymianie (re-fit) — to zmienia
  model korekt (jedna korekta = jeden składnik); zapisz jako pytanie na v3.
* Nie dodajemy przycisku wymiany do planu z kreatora/kompozytora (`NutritionPlan`)
  — inny katalog, bez grup; osobna decyzja (pytanie 1).
* Nie edytujemy powiązań w UI — tylko odczyt; nie „włączamy reguły `group`”.
* Nie dotykamy `docs/diet-module/engine.py` (prototyp zostaje historyczny).
* Nie robimy złączenia silnika z `FoodProduct` w czasie działania i nie importujemy
  do katalogu diet ani jednego wiersza bez decyzji TAK człowieka.

## 8. Weryfikacja przed przekazaniem (z korzenia repozytorium)

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Plus: **pomiar przed/po** tym samym skryptem (tabela w CHANGELOG i PROGRESS) i
**uruchomienie** (`ZASADA_URUCHOMIENIA.md`): przez serwer E2E jako klient B z
przypisaną dietą kliknij ↔ wymień na składniku, który na `main` dawał pustą listę,
zobacz etykietę poziomu i deltę, wymień, zrób zrzut; potem jako trener obejrzyj
historię. W raporcie napisz, CO KLIKNĄŁEŚ I CO ZOBACZYŁEŚ. Przegląd: 3 recenzentów
wsadowo (bezpieczeństwo/alergeny/wykluczenia, poprawność silnika i determinizm,
testy/UX/treść), P0/P1 przed przekazaniem, P2 do `PROGRESS.md`. Bezpiecznik: 3× plan.

## 9. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)

1. ~~Szablon czy kreator?~~ **Rozstrzygnięte 14.09:** klient na diecie z szablonu;
   kreator ukrywamy (zlecenie 3); katalog produktów zostaje jako źródło zamienników
   (§5a). Pytanie zastępcze: kto przegląda CSV propozycji — właściciel czy trener
   Łukasz? *Domyślnie: właściciel wstępnie, trener potwierdza alergeny.*
2. Powiązania oznaczone (?) w §5 — włączyć od razu czy zostawić wyłączone do
   przeglądu trenera? *Domyślnie: wyłączone.*
3. Czy wymiana w posiłku już poza tolerancją ma być dozwolona, gdy **nie pogarsza**
   (rekomendacja), czy tylko gdy **poprawia**? *Domyślnie: nie pogarsza.*
4. Warzywa `NONE` 1:1 wagowo — zgoda? (alternatywa: izokalorycznie, ale 100 g ogórka
   ↔ 25 g kukurydzy nie jest wymianą, której klient oczekuje). *Domyślnie: 1:1.*

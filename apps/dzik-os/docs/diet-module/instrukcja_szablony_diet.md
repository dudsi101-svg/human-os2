# Instrukcja poprawy modułu diety — konto trenerskie

Wersja 1.1 · 13.09.2026 · Status: po prototypie silnika i pierwszego szablonu

---

## 1. Problem

Konfigurator diet nie działa i nie jest wart naprawy. Trener nie ma dziś sposobu, żeby szybko przypisać klientowi dobrą, kompletną dietę: musi tworzyć osobny jadłospis dla każdej kaloryczności, a klient nie ma żadnej swobody w wymianie produktów, których nie lubi lub nie ma pod ręką. Efekt: diety powstają wolno, powtarzają się, a klienci porzucają je przy pierwszym niewygodnym składniku.

## 2. Decyzja

**Rezygnujemy z konfiguratora.** Cały wysiłek idzie w dwie rzeczy:

1. **Bibliotekę szablonów** — gotowe, smaczne, tygodniowe jadłospisy pokrywające najczęstsze potrzeby.
2. **Silnik skalowania** — jeden szablon przelicza się na dowolną kaloryczność i makro bez utraty sensu przepisu.

Do tego jedna funkcja po stronie klienta: **wymiana produktu jednym kliknięciem** na 1–3 zamienniki o podobnych właściwościach.

## 3. Cele

| Cel | Miara sukcesu |
|---|---|
| Trener przypisuje pełną dietę w < 3 minuty | czas od wyboru klienta do przypisania |
| Jeden szablon obsługuje zakres 1400–3200 kcal | brak konieczności tworzenia diet per kcal |
| Wynik po skalowaniu mieści się w tolerancji | dzień: ±3 % kcal, ±5 g B, ±5 g T, ±10 g W |
| Klient sam rozwiązuje "nie lubię / nie mam" | ≥ 70 % wymian bez udziału trenera |
| Biblioteka odpowiada na główne potrzeby | 8 profili × 5 odsłon tygodnia w v1 |

## 4. Poza zakresem (nie robimy w v1)

- Naprawa lub przebudowa konfiguratora — zastępujemy go szablonami.
- Generowanie przepisów przez AI — biblioteka jest kuratorowana ręcznie, jakość smaku to jej główna wartość.
- Lista zakupów i integracja ze sklepami — osobna inicjatywa po v1.
- Automatyczne wyliczanie zapotrzebowania klienta (TDEE) — trener podaje kcal i makro; kalkulator jest prostym dodatkiem, nie warunkiem.
- Rozliczanie mikroskładników (witaminy, minerały) — tylko kcal + B/T/W + błonnik informacyjnie.

---

## 4a. Zmiany po prototypie (v1.1)

Silnik został zaimplementowany (`engine.py`) i przetestowany na pierwszym pełnym tygodniu (`template_standard_v1.json`) w zakresie 1400–3200 kcal. Prototyp wymusił pięć korekt względem v1.0:

1. **Makro posiłku ≠ makro dnia.** Narzucanie każdemu posiłkowi proporcji dnia (25/30/45) niszczyło przepisy — przekąska z jogurtem i orzechami nigdy nie ma proporcji obiadu. Teraz cel makro posiłku = jego własny profil bazowy × (cel dnia / suma bazowa dnia). Zachowuje charakter przepisu, a dzień trafia w cel.
2. **Kcal liczone z makro (4/9/4)**, nie z wartości USDA. Dwie miary nie mogą zgadzać się jednocześnie; wartość USDA zostaje w bazie jako `kcal_usda` (referencja).
3. **Tolerancja posiłku:** ±8 % **lub ±40 kcal** (większe z dwóch) — przy przekąsce 300 kcal ±24 kcal jest nie do trafienia z bananem na sztuki. Makro posiłku: ±5 g B, ±4 g T, ±10 g W.
4. **Dwa przebiegi dnia + dostrojenie.** Po pierwszym przeliczeniu reszta dnia rozkładana jest na wszystkie posiłki proporcjonalnie do udziałów, potem posiłek elastyczny domyka różnicę, a na końcu silnik przesuwa pojedyncze kroki zaokrąglenia (5 g) na składnikach LINIOWY z rolą.
5. **Tłuszcze dodawane w małych ilościach** (oliwa 5–15 g, orzechy, masło orzechowe) mogą rosnąć do **3×** bazy — nadal praktyczne, a bez tego wysokie kaloryczności nie domykają tłuszczu.

6. **Krok zaokrąglenia tłuszczów = 1 g** (oleje, orzechy, nasiona). Przy kroku 5 g dwa gramy oliwy stawały się pięcioma — na redukcji z 56 g tłuszczu dziennie to 8 % błędu z jednego składnika i główna przyczyna flag.

Wynik po poprawkach 1–6 (6 szablonów, 1300–3200 kcal): 0 dni poza tolerancją (Standard 1: jeden), 7–11 % posiłków z flagą — patrz `raport_walidacji_szablonow.md`.

Dodatkowe kryteria jakości szablonu wyniesione z autorstwa 6 tygodni:
- dzień bazowy w granicach ±10 g każdego makro od celu, nie tylko ±5 % kcal;
- tłuszcz rozłożony między posiłki — każdy niesie ≥ 10 % tłuszczu dnia; posiłek z tłustą rybą wymaga chudej reszty dnia rozłożonej równo, nie jednego chudego posiłku;
- tłusta ryba lub tłuste mięso nigdy nie jest jedynym składnikiem z rolą P w posiłku (silnik dodając białko dodaje tłuszcz);
- strączki dostają rolę C, gdy w posiłku jest inne źródło białka, i rolę P tylko wtedy, gdy są jedynym źródłem.

## 5. Biblioteka szablonów

### 5.1 Struktura

```
Profil diety (np. "Redukcja wysokobiałkowa")
 └── Odsłona tygodnia 1–5 (różne zestawy posiłków, ten sam profil)
      └── Dzień 1–7
           └── Posiłek (slot, udział % kcal dnia)
                └── Składnik (produkt, gramatura bazowa, reguły skalowania)
```

Każdy szablon ma **kaloryczność bazową** (domyślnie 2000 kcal) i **zakres ważności** (np. 1400–3200 kcal). Poza zakresem silnik ostrzega, ale nie blokuje.

### 5.2 Profile (stan biblioteki: 9 profili × 5 odsłon = 45 tygodni, wszystkie przetestowane)

| # | Profil | Dla kogo | B/T/W % kcal | Baza | Zakres kcal | Posiłków/dzień | Pochodzenie |
|---|---|---|---|---|---|---|---|
| 1 | Standard zbilansowana | ogół klientów | 25/30/45 | 2000 | 1400–3200 | 4 | autorskie |
| 2 | Redukcja wysokobiałkowa | odchudzanie z treningiem siłowym | 35/25/40 | 2000 | 1300–2800 | 4 | autorskie (odsłona 2 z jadłospisów Łukasza) |
| 3 | Sportowa wysokobiałkowa | klienci trenujący, wg jadłospisów Łukasza | 30/22/48 | 2600 | 2000–3600 | **5** (dwa obiady) | rotacja z opcji Łukasza |
| 4 | Masa / budowa | nadwyżka kaloryczna | 25/25/50 | 3000 | 2200–4000 | 4 | pochodna Standard |
| 5 | Niskowęglowodanowa | preferencja low-carb | 30/45/25 | 2000 | 1400–3000 | 4 | autorskie (pule) |
| 6 | Wegetariańska | bez mięsa i ryb | 22/30/48 | 2000 | 1400–3200 | 4 | autorskie (pule) |
| 7 | Wegańska | bez produktów odzwierzęcych | 20/30/50 | 2000 | 1400–3200 | 4 | autorskie (pule) |
| 8 | Bezlaktozowa | nietolerancja laktozy | 25/30/45 | 2000 | 1400–3200 | 4 | pochodna Standard (mapa zamienników) |
| 9 | Bezglutenowa | celiakia / nietolerancja | 25/30/45 | 2000 | 1400–3200 | 4 | pochodna Standard (mapa zamienników) |

Pliki: `template_<profil>_v<n>.json` (seed), `szablon_<profil>_v<n>_<kcal>kcal.md` (podgląd), `biblioteka_index.json` (spis), `raport_walidacji_szablonow.md` (wyniki). Profile pochodne mają `derived_from` w JSON.

**Konsekwencja dla UI:** profil Sportowa ma 5 slotów (`śniadanie, przekąska, obiad_1, obiad_2, kolacja`). Widok dnia klienta i trenera musi renderować dowolną liczbę slotów z szablonu, nie sztywne 4.

### 5.3 Kryteria jakości szablonu

Szablon jest gotowy do publikacji, gdy:

- każdy posiłek ma pełny przepis (składniki, kroki, czas przygotowania),
- każdy składnik ma przypisany produkt z bazy z wartościami na 100 g,
- każdy składnik ma klasę skalowania i zakres (patrz 6.3),
- dzień bazowy mieści się w tolerancji makro profilu,
- przynajmniej 2 posiłki w tygodniu są "na wynos" (praca / szkoła),
- kolacje i śniadania powtarzają się maks. 2× w tygodniu w jednej odsłonie,
- odsłony 1–5 nie dublują więcej niż 30 % posiłków między sobą,
- test skalowania na 1400, 2000, 2600, 3200 kcal przechodzi bez flag "poza zakresem".

---

## 6. Silnik skalowania

### 6.1 Wejście

- szablon (profil + odsłona),
- cel: kcal/dzień oraz B, T, W w gramach (albo w % kcal — silnik przelicza na gramy),
- opcjonalnie: masa ciała klienta (do presetów typu 2 g B/kg), wykluczenia (alergeny, nielubiane produkty).

### 6.2 Algorytm (5 kroków)

**Krok 1 — Rozdział kcal na posiłki.**
Każdy posiłek w szablonie ma udział % kcal dnia (np. śniadanie 25 %, obiad 35 %, przekąska 15 %, kolacja 25 %). Cel kcal posiłku = cel dnia × udział. Makro celu rozkładamy tym samym udziałem. Skalujemy **każdy posiłek osobno**, nie cały dzień jednym mnożnikiem — inaczej błędy się kumulują w jednym miejscu.

**Krok 2 — Skalowanie wstępne.**
`k = kcal_cel_posiłku / kcal_baza_posiłku`. Każdy składnik mnożymy przez `k` **zgodnie z jego klasą** (6.3). Przykład: 120 g kurczaka przy 2000 kcal → 180 g przy 3000 kcal (k = 1,5).

**Krok 3 — Dopasowanie makro.**
Po kroku 2 kcal się zgadzają, ale makro zwykle nie (klient chce więcej białka, niż daje proporcjonalne skalowanie). Silnik iteruje (maks. 5 przebiegów):

1. policz odchylenie B, T, W posiłku od celu,
2. białko koryguj wyłącznie składnikami z rolą `P`, węglowodany rolą `C`, tłuszcz rolą `F`,
3. każdy krok korekty ograniczony przez `min_factor` / `max_factor` składnika,
4. jeśli po 5 przebiegach odchylenie > tolerancja posiłku → flaga (krok 5).

Prosta implementacja: dla każdej roli rozdziel brakujące gramy makro proporcjonalnie na składniki tej roli, przeliczając przez zawartość na 100 g. Nie potrzeba solvera — wystarczy pętla.

**Krok 4 — Zaokrąglenie do praktycznych ilości.**
Każdy składnik ma `round_step`: mięso/kasza 5 g, nabiał 10 g, oleje 1 g (≈ ¼ łyżeczki), produkty dyskretne do 0,5 lub 1 szt. Zaokrąglamy **po** dopasowaniu makro, nigdy w trakcie.

**Krok 5 — Kontrola i decyzja.**
Przeliczamy kcal i makro z zaokrąglonych gramatur. Tolerancje:

| Poziom | kcal | Białko | Tłuszcz | Węgle |
|---|---|---|---|---|
| Posiłek | ±8 % | ±4 g | ±3 g | ±8 g |
| Dzień | ±3 % | ±5 g | ±5 g | ±10 g |

Jeśli posiłek nie mieści się w tolerancji lub którykolwiek składnik zatrzymał się na granicy zakresu → status `POZA_ZAKRESEM` i silnik proponuje **wariant zastępczy** (6.5). Jeśli dzień jest poza tolerancją mimo poprawnych posiłków → silnik przesuwa brakujące kcal do posiłku z flagą `elastyczny` (zwykle przekąska).

### 6.3 Klasy skalowania składników

| Klasa | Przykłady | Zachowanie | Domyślny zakres |
|---|---|---|---|
| `LINIOWY` | mięso, ryby, kasza, ryż, makaron, płatki, nabiał, strączki | mnoży się przez `k` w całości | 0,5–2,0× bazy |
| `DYSKRETNY` | jajka, kromki, tortilla, banan, jogurt w kubku | mnoży się, potem zaokrągla do `unit_size` (1 lub 0,5 szt.) | zakres w sztukach, np. 1–4 jajka |
| `TŁUMIONY` | warzywa, sałata, sosy, śmietana do zupy, tłuszcz do smażenia | mnoży się przez `k^0,5` (rośnie wolniej) | 0,7–1,5× bazy |
| `STAŁY` | przyprawy, zioła, woda, ocet, cytryna, bulion | nie skaluje się | — |

Każdy składnik dodatkowo ma:

- `macro_role`: `P` / `C` / `F` / `NONE` — którym makro może sterować (np. oliwa = `F`, ryż = `C`, pierś = `P`, brokuł = `NONE`),
- `min_factor`, `max_factor` — nadpisują domyślny zakres klasy, gdy przepis tego wymaga (np. ciasto naleśnikowe: mąka i mleko muszą skalować się razem — patrz `group`),
- `group` (opcjonalnie) — składniki w tej samej grupie skalują się identycznym współczynnikiem (ciasto, marynata, sos).

**Zasada nadrzędna:** jeśli składnik ma ustawiony zakres i został zatrzymany na granicy, silnik **nie przekracza** go — woli oflagować posiłek niż zaproponować 450 g ryżu.

### 6.4 Presety makro dla trenera

Trener wpisuje kcal i wybiera preset lub podaje gramy ręcznie:

- **z profilu** — makro % szablonu,
- **na kg masy ciała** — np. B 2,0 g/kg, T 1,0 g/kg, reszta W (wymaga masy ciała),
- **ręcznie** — B/T/W w gramach; silnik ostrzega, gdy suma kcal z makro ≠ cel ±3 %.

### 6.5 Warianty zastępcze posiłku

Gdy posiłek dostaje `POZA_ZAKRESEM`, silnik szuka w bibliotece posiłku, który:

1. ma ten sam slot (śniadanie / obiad …) i pasuje do profilu diety (tagi: wege, bezglutenowe itd.),
2. po przeskalowaniu do celu mieści się w tolerancji **bez** flag,
3. jest najbliższy oryginałowi pod względem tagów kuchni (np. "azjatyckie", "na wynos", "≤ 15 min"),
4. nie narusza wykluczeń klienta.

Trener widzi propozycję z porównaniem makro i zatwierdza lub wybiera inną. Do publikacji nie może trafić dzień z nierozwiązaną flagą.

---

## 7. Wymiana produktu przez klienta (v2, 0.69.0)

### 7.1 Zachowanie

1. Klient klika „↔ wymień” przy składniku — także przy warzywach i dodatkach
   (rola NONE), jeśli grupa zamienników ma ≥ 2 produkty; składniki STAŁE bez przycisku.
2. Widzi do **5 zamienników** z etykietą poziomu: **„z tej samej grupy”** (poziom 1,
   ta sama `substitution_group`) albo **„grupa pokrewna: …”** (poziom 2, z tabeli
   powiązań `dieta/dane/grupy_pokrewne.json`; powód powiązania w dymku).
3. Przy każdym zamienniku: gramatura policzona przez serwer (zachowanie roli makro;
   dla NONE 1:1 wagowo) i **delta posiłku** po polsku („posiłek: −12 kcal, białko +1 g”).
4. Po wyborze posiłek się przelicza; serwer zapisuje wymianę z poziomem.

### 7.2 Dobór zamienników (sita w tej kolejności, każde odrzucenie liczone z powodem)

1. **Wykluczenia** klienta (alergeny, wykluczenia dietetyczne, „nie lubię” po nazwie)
   — **przed** poziomem 2: grupa pokrewna nie może przemycić alergenu.
2. **Funkcja w posiłku:** metoda przygotowania (`cooking_tags` muszą się przecinać;
   `*` i pusty zestaw tagów = wildcard; na poziomie 2 wildcard kandydata nie wystarcza)
   i rola makro (kandydat musi dostarczać makro roli; na poziomie 2 dominujące makro
   zgodne z rolą, dla P wystarczy ≥ 15 g białka/100 g).
3. **Limity porcji** v1.1: ≤ 300 g surowego mięsa/ryby, ≤ 4 jajka.
4. **Bramka posiłku „w tolerancji ALBO nie pogarsza”:** posiłek po wymianie mieści się
   w `TOL_MEAL` **albo** żadne odchylenie (kcal, P, F, C) nie jest większe niż przed
   wymianą — w posiłku już poza tolerancją wymiana neutralna lub poprawiająca jest
   dozwolona. `TOL_MEAL`/`TOL_DAY` bez zmian.

Ranking: poziom (1 przed 2) → suma |Δ| posiłku po wymianie → odległość makro produktu.
Wynik deterministyczny.

**Pusta lista ma powód** (`reason`): `SINGLETON` (grupa bez innych produktów i bez grup
pokrewnych), `EXCLUDED` (wszystko odpadło przez wykluczenia), `FUNCTION` (nic nie pasuje
metodą/rolą), `PORTION` (porcja poza limitem), `TOLERANCE` (kandydaci istnieją, ale
każdy pogarsza posiłek). Interfejs pokazuje właściwy komunikat po polsku.

### 7.3 Uprawnienia trenera

- domyślnie wymiany włączone dla składników z rolą `P`/`C`/`F` oraz `NONE` z grupą
  ≥ 2 produktów (liczone przy odczycie — także dla przypisań sprzed 0.69.0),
- trener może zablokować wymiany globalnie dla klienta lub dla konkretnego posiłku,
- trener widzi historię wymian klienta (co, kiedy, na co, **z jakiego poziomu**),
- tabela grup pokrewnych w panelu szablonów **tylko do odczytu** (status PROPOZYCJA,
  pary „?” wyłączone) — poprawki przez właściciela, edycja z panelu to osobna runda.

### 7.4 Katalog trenera jako źródło zamienników (§5a zlecenia)

Katalog pojedynczych produktów (`FoodProduct`, 2058 pozycji) **nie** jest źródłem
kandydatów w czasie działania (brak grup, tagów, alergenów). Narzędzie
`tools/koreluj_katalog.py` generuje CSV propozycji do przeglądu człowieka
(`docs/diet-module/katalog_korelacja_propozycja.csv`); tylko wiersze z decyzją TAK
trafiają do `dieta/dane/produkty_z_katalogu.csv` (osobny plik, jawne pochodzenie,
seed po głównym CSV). Wiersz bez uzupełnionego alergenu nie może być zaimportowany.

---

## 8. Model danych (minimum)

```
Product
  id, name, kcal_100, protein_100, fat_100, carbs_100, fiber_100
  category, allergens[], diet_tags[] (wege, bezglut, bezlakt…)
  substitution_group, cooking_tags[]

DietProfile
  id, name, description, base_macro_pct {P,F,C}, diet_tags[]

TemplateWeek            (odsłona)
  id, profile_id, variant_no (1–5), base_kcal, kcal_min, kcal_max, status

TemplateDay
  id, week_id, day_no (1–7)

TemplateMeal
  id, day_id, slot, name, kcal_share_pct, flexible (bool)
  recipe_steps, prep_minutes, tags[]

TemplateIngredient
  id, meal_id, product_id, base_grams
  scaling_class (LINIOWY|DYSKRETNY|TŁUMIONY|STAŁY)
  macro_role (P|C|F|NONE), min_factor, max_factor, round_step
  unit_size (dla DYSKRETNY), group (opcjonalnie), swappable (bool)

AssignedDiet
  id, client_id, trainer_id, week_id
  target_kcal, target_P, target_F, target_C, body_weight (opc.)
  computed_plan (snapshot JSON po skalowaniu), overrides JSON
  created_at, version

SwapEvent
  id, assigned_diet_id, meal_id, ingredient_id
  from_product_id, to_product_id, from_grams, to_grams, created_at
```

`computed_plan` jest **migawką** — późniejsza edycja szablonu nie zmienia już przypisanych diet. Ponowne przypisanie tworzy nową wersję.

---

## 9. Przepływ trenera (UI)

1. Klient → "Przypisz dietę".
2. Wybór profilu (8 kafelków) → wybór odsłony (1–5, podgląd listy posiłków tygodnia).
3. Cel: kcal + preset makro (lub ręcznie) + opcjonalnie masa ciała i wykluczenia.
4. Podgląd tygodnia: każdy dzień z sumą kcal/makro i kolorowym statusem (OK / ostrzeżenie / poza zakresem). Posiłki z flagą mają przycisk "Zamień na wariant".
5. Ręczna edycja gramatur dowolnego składnika (silnik przelicza na żywo, pokazuje wpływ).
6. "Przypisz" → dieta widoczna u klienta.

---

## 10. Wymagania i priorytety

### P0 — bez tego nie wdrażamy
- [ ] Baza produktów z wartościami na 100 g, `substitution_group` i tagami.
- [ ] Model szablonów (sekcja 8) + panel wprowadzania szablonów dla dietetyka/admina.
- [ ] Silnik: kroki 1–5, klasy skalowania, tolerancje, flagi.
- [ ] Przepływ trenera (sekcja 9) z podglądem i ręczną korektą.
- [ ] Minimum 3 profile × 5 odsłon opublikowanych i przetestowanych na 4 kalorycznościach.
- [ ] Widok klienta: jadłospis dnia z przepisami i gramaturami.

### P1 — zaraz po wdrożeniu
- [ ] Wymiana produktu przez klienta (sekcja 7).
- [ ] Warianty zastępcze posiłku (6.5) — w P0 trener zamienia posiłek ręcznie z listy.
- [ ] Pozostałe 5 profili.
- [ ] Preset makro "na kg masy ciała".

### P2 — projektujemy pod to, nie budujemy
- Lista zakupów z przypisanej diety.
- Statystyki: najczęściej wymieniane produkty → sygnał do poprawy szablonów.
- Rotacja odsłon (co tydzień automatycznie kolejna z 5).

### Kryteria akceptacji silnika (do testów automatycznych)

- Dla każdego opublikowanego szablonu i każdej kaloryczności z zakresu (krok 100 kcal) wynik dnia mieści się w tolerancji dnia albo zawiera wyłącznie flagi z dostępnym wariantem.
- Składnik `STAŁY` nigdy nie zmienia gramatury.
- Składnik `DYSKRETNY` zawsze ma wielokrotność `unit_size`.
- Żaden składnik nie wychodzi poza `min_factor`–`max_factor`.
- Składniki w tej samej `group` mają identyczny współczynnik końcowy.
- Wymiana produktu nigdy nie wyprowadza posiłku poza tolerancję posiłku.
- Skalowanie 2000 → 3000 kcal składnika `LINIOWY` bez korekty makro daje dokładnie ×1,5 przed zaokrągleniem.

---

## 11. Otwarte pytania

| Pytanie | Kto odpowiada | Blokuje? |
|---|---|---|
| Skąd baza produktów: własna, USDA, Open Food Facts, licencjonowana polska? | produkt / prawnik | tak |
| Kto autoruje 40 tygodniowych szablonów (8 × 5) i w jakim czasie? Dietetyk na etacie czy zlecenie? | biznes | tak |
| Czy tolerancje z 6.2 są akceptowalne dla trenerów, czy potrzebują ustawienia per klient? | 3–5 trenerów testowych | nie |
| Czy klient może wymieniać składniki bez limitu, czy np. maks. 2 na posiłek? | produkt | nie |
| Wartości na 100 g produktu surowego czy gotowanego? (musi być jednolicie — rekomendacja: surowe, z mnożnikami dla zmiany masy) | dietetyk | tak |

---

## 12. Fazowanie

1. **Faza A (fundament):** baza produktów, model szablonów, silnik + testy automatyczne, panel wprowadzania szablonów. Równolegle dietetyk pisze pierwsze 3 profile.
2. **Faza B (trener):** przepływ przypisania, podgląd, ręczna korekta, widok klienta. Pilotaż z kilkoma trenerami.
3. **Faza C (klient):** wymiany produktów, warianty zastępcze, kolejne profile.
4. **Faza D:** lista zakupów, statystyki wymian, rotacja odsłon.

Faza A jest największa i najmniej widoczna — ale bez poprawnych reguł skalowania na składnikach cała reszta produkuje śmieci. Nie skracać jej kosztem testów.

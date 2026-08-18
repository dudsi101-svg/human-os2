# Baza ćwiczeń — model, słownik mięśni, zasady opisów

Dokument opisuje rozbudowaną bazę ćwiczeń Dzik OS (wersja 0.22.0):
model danych, **kontrakt słownika partii mięśniowych** (wspólny z
planowanym rysunkiem sylwetki), zasady pisania opisów, API filtrów,
sposób układania planu treningowego z bazy oraz plan wycofania
migracji nr 19.

Od 0.28.0 dochodzi **auto-uzupełnianie tabeli parametrów z wklejonego
opisu** (§10) wraz z proweniencją wpisu i planem wycofania migracji
nr 22.

## 1. Czym baza ćwiczeń jest, a czym nie jest

Baza ćwiczeń to **know-how trenera**: własność trenera, widoczna dla
jego aktywnie prowadzonych klientów (broadcast — ten sam wzorzec co
baza wiedzy i baza produktów). To **nie są dane zdrowotne klienta**,
więc nie przechodzi przez `resolve_client_access`.

Granice roli (Konstytucja Human OS):

* baza opisuje **wykonanie ćwiczenia**, nie leczy i nie diagnozuje —
  żaden wpis nie twierdzi, że ćwiczenie coś „naprawia”, „leczy” ani
  „koryguje wadę”;
* uwagi bezpieczeństwa **kierują do konsultacji ze specjalistą** przy
  bólu, urazie lub wątpliwościach — nie oceniają stanu zdrowia;
* aplikacja **nie dobiera ćwiczeń automatycznie**. Katalog jest
  materiałem, z którego wybiera człowiek. Wyszukiwarka w edytorze planu
  podpowiada wyniki wyszukiwania, ale nie tworzy ani nie zmienia planu
  samodzielnie.

## 2. Model danych (`Exercise`)

Pola sprzed rozbudowy (bez zmian, **zgodność wsteczna**):

| pole | typ | uwagi |
| --- | --- | --- |
| `name` | `VARCHAR(300)` | nazwa |
| `muscle_group` | `VARCHAR(30)` | zgrubna grupa do widoku listy: `NOGI, PLECY, KLATKA, BARKI, RECE, BRZUCH, CALE_CIALO, MOBILNOSC, CARDIO, INNE` (`CARDIO` dodane w 0.22.0) |
| `how_to` | `TEXT` | skrócony opis; **pole zgodności wstecznej** |
| `benefit`, `equipment`, `video_url`, `status` | | jak dotąd |

Pola dodane migracją nr 19 — **wszystkie NULLable**, żaden backfill nie
jest potrzebny:

| pole | typ w bazie | reprezentacja w API |
| --- | --- | --- |
| `muscles_primary` | `TEXT` (CSV kluczy) | `string[]` |
| `muscles_secondary` | `TEXT` (CSV kluczy) | `string[]` |
| `level` | `VARCHAR(30)` | `POCZATKUJACY / SREDNIOZAAWANSOWANY / ZAAWANSOWANY` |
| `pattern` | `VARCHAR(30)` | wzorzec ruchu (niżej) |
| `steps_json` | `TEXT` (JSON) | `steps: string[]` — kroki techniki |
| `mistakes_json` | `TEXT` (JSON) | `mistakes: string[]` |
| `cues_json` | `TEXT` (JSON) | `cues: string[]` |
| `safety` | `TEXT` | uwagi bezpieczeństwa |
| `easier` / `harder` | `TEXT` | warianty łatwiejszy / trudniejszy |
| `tempo_hint` | `VARCHAR(200)` | np. `3010` |
| `breathing` | `VARCHAR(400)` | wzorzec oddechu |

Listy trzymamy jako JSON w kolumnie tekstowej: to treść opisowa, po
której nie zadajemy zapytań — osobne tabele byłyby kosztem bez zysku.

**Zgodność wsteczna jest wymogiem, nie życzeniem**: ćwiczenie zapisane
przed rozbudową (tylko `how_to`) wraca z API z pustymi listami i
`null`-ami, a widok szczegółu pokazuje wtedy `how_to` zamiast sekcji
„Technika — krok po kroku”. Test:
`tests/test_exercises_extended.py::test_backward_compatible_exercise_without_new_fields`.

## 3. SŁOWNIK PARTII MIĘŚNIOWYCH — kontrakt

Te 21 kluczy to **kontrakt** wspólny dla backendu
(`dzik_os/muscles.py::MUSCLE_LABELS`), frontendu
(`frontend/src/types.ts::MUSCLE_LABELS`) i **rysunku sylwetki, który
powstanie w kolejnej rundzie**. Klucze nie mogą być zmieniane ani
usuwane bez migracji danych; dokładanie nowych jest bezpieczne.

| klucz | etykieta |
| --- | --- |
| `KLATKA_PIERSIOWA` | klatka piersiowa |
| `NAJSZERSZY_GRZBIETU` | najszerszy grzbietu |
| `CZWOROBOCZNY` | czworoboczny |
| `ROMBOIDALNE` | romboidalne |
| `PROSTOWNIKI_GRZBIETU` | prostowniki grzbietu |
| `BARK_PRZEDNI` | bark przedni |
| `BARK_BOCZNY` | bark boczny |
| `BARK_TYLNY` | bark tylny |
| `BICEPS` | biceps |
| `TRICEPS` | triceps |
| `PRZEDRAMIE` | przedramię |
| `BRZUCH_PROSTY` | brzuch prosty |
| `BRZUCH_SKOSNY` | brzuch skośny |
| `MIESNIE_GLEBOKIE` | mięśnie głębokie |
| `POSLADKI` | pośladki |
| `CZWOROGLOWY_UDA` | czworogłowy uda |
| `DWUGLOWY_UDA` | dwugłowy uda |
| `PRZYWODZICIELE` | przywodziciele |
| `ODWODZICIELE` | odwodziciele |
| `LYDKA` | łydka |
| `ZGINACZE_BIODRA` | zginacze biodra |

Walidacja jest **serwerowa**: nieznany klucz w `muscles_primary` lub
`muscles_secondary` → **422**. To samo dotyczy `level` i `pattern`.
Aktualny słownik można pobrać z API: `GET /api/exercise-dictionaries`
(zwraca `muscles`, `levels`, `patterns`, `muscle_groups`).

**Dla rysunku sylwetki (kolejna runda)**: w karcie ćwiczenia (u klienta
i u trenera) zostawiono znacznik
`{/* MIEJSCE NA RYSUNEK MIĘŚNI (kolejna runda) */}` bezpośrednio nad
sekcją „Pracujące mięśnie” w `frontend/src/components.tsx`
(`ExerciseDetail`). Komponent rysunku dostanie dokładnie te klucze —
`item.muscles_primary` i `item.muscles_secondary`.

### Wzorce ruchu (`pattern`)

`PRZYSIAD, ZAWIAS_BIODROWY, WYPYCHANIE_POZIOME, WYPYCHANIE_PIONOWE,
PRZYCIAGANIE_POZIOME, PRZYCIAGANIE_PIONOWE, WYKROK, NOSZENIE, ROTACJA,
ANTYROTACJA, IZOLACJA, CARDIO, MOBILNOSC`.

### Poziomy (`level`)

`POCZATKUJACY, SREDNIOZAAWANSOWANY, ZAAWANSOWANY`.

## 4. Zasady opisów (katalog i wpisy trenera)

Katalog startowy (`dzik_os/exercise_catalog.py`, **155 ćwiczeń**) trzyma
się tych samych reguł, których oczekujemy od trenera:

1. **Kroki techniki: 3–6 punktów.** Ustawienie → ruch → zakończenie.
   Każdy krok to jedno zdanie w trybie rozkazującym („Ustaw…”,
   „Zejdź…”).
2. **Błędy: 2–4 pozycje.** Konkretny, obserwowalny objaw („kolana
   uciekające do środka”), nie ogólnik („zła technika”).
3. **Wskazówki („cue”): 1–3.** Krótkie hasła, które klient może sobie
   powtórzyć w trakcie serii („odepchnij podłogę”).
4. **Bezpieczeństwo.** Co zabezpieczyć przed serią + zdanie kierujące do
   specjalisty przy bólu lub urazie. **Bez** twierdzeń o leczeniu.
5. **Warianty.** Zawsze łatwiejszy i trudniejszy — ćwiczenie ma być
   skalowalne, a nie „dla wybranych”.
6. **Mięśnie.** `primary` = mięśnie, dla których robimy to ćwiczenie;
   `secondary` = realnie współpracujące. Bez wypełniania listy „na
   zapas”.
7. **Język trenera.** Konkret, bez lania wody, bez marketingu.

Pokrycie katalogu: sztanga, hantle, kettlebell, maszyny i wyciągi, masa
własna ciała, gumy oporowe, dom bez sprzętu, core, mobilność i
rozgrzewka, cardio.

## 5. API

### Lista i szczegół

* `GET /api/coach/exercises` — baza trenera (własna, wszystkie statusy
  albo `status=ACTIVE|ARCHIVED`).
* `GET /api/coach/exercises/{id}` — szczegół (404 dla cudzego).
* `GET /api/me/exercises` — baza trenerów, którzy **aktywnie prowadzą**
  klienta; tylko `ACTIVE`.
* `GET /api/me/exercises/{id}` — karta ćwiczenia dla klienta; 404 gdy
  brak aktywnej relacji albo ćwiczenie jest zarchiwizowane.
* `GET /api/exercise-dictionaries` — słowniki (kontrakt).

### Filtry (te same dla obu list)

| parametr | znaczenie |
| --- | --- |
| `q` | fragment nazwy lub sprzętu; **odporny na polskie znaki** (`wioslowanie` = `wiosłowanie`) |
| `muscle` | klucz ze słownika; dopasowanie po `primary` **lub** `secondary` |
| `muscle_group` | zgrubna grupa (widok listy) |
| `equipment` | fragment nazwy sprzętu |
| `level`, `pattern` | wartości słownikowe |
| `limit` (domyślnie 60, maks. 200), `offset` | paginacja |

Odpowiedź: `{"items": [...], "total": n, "limit": n, "offset": n,
"has_more": bool}`. Frontend realizuje „pokaż więcej”, doklejając
kolejne strony.

Nieznana wartość `muscle` / `level` / `pattern` / `muscle_group` →
**422** (żadnego cichego ignorowania filtra).

Filtrowanie i wyszukiwanie liczy aplikacja (nie SQL `LIKE`), bo
normalizacja polskich znaków musi być identyczna wszędzie —
`dzik_os/muscles.py::fold()`. Przy skali katalogu (setki pozycji na
trenera) to świadomy wybór poprawności nad mikrooptymalizacją; gdyby
baza urosła o rząd wielkości, właściwym krokiem jest kolumna z
znormalizowaną nazwą i indeks, a nie zmiana semantyki filtra.

## 6. Plan treningowy układany z bazy

### Wyszukiwarka w edytorze planu

`frontend/src/pages/coach/PlanEditor.tsx` ma przy każdym dniu przycisk
**„Wybierz z bazy ćwiczeń”**: pasek filtrów (ten sam komponent co w
bazie), lista wyników z nazwą, partiami, sprzętem i poziomem oraz licznik
wyników czytany przez `aria-live`. Kliknięcie w wynik dodaje ćwiczenie do
dnia i **nie zamyka wyszukiwarki** — można dodać kilka pozycji pod rząd.

Uzupełnianie pól: nazwa i `exercise_id` zawsze; `tempo` z `tempo_hint`,
komentarz z pierwszej wskazówki, link do wideo z karty — **wyłącznie gdy
pole jest puste**. Wartości wpisane przez trenera nigdy nie są
nadpisywane.

**Ręczne wpisanie nazwy zostaje pełnoprawną ścieżką** (przycisk
„+ ćwiczenie (wpisz ręcznie)”). Aplikacja nie zamyka trenera w
katalogu. Ręczna zmiana nazwy pozycji odpina `exercise_id` — link nie
może wskazywać czegoś innego, niż mówi nazwa.

### Kontrakt `exercise_id`

`exercise_id` żyje w **treści wersji planu** (JSON w `content_json`) —
bez migracji, ten sam wzorzec co suplementacja w diecie.

* **Walidacja serwerowa** (`routers/plans.py::_validate_exercise_refs`,
  wywoływana przy tworzeniu planu i każdej nowej wersji): identyfikator
  musi wskazywać **ćwiczenie tego trenera** o statusie **ACTIVE**;
  cudzy, nieistniejący albo zarchiwizowany → **422**.
* **Miękkie odniesienie.** Nazwa i parametry są zapisane w planie, więc
  archiwizacja ćwiczenia **nie psuje istniejących planów** — znika
  wyłącznie link do karty techniki. Plan wyświetla się normalnie.
* **Stare wersje planów bez `exercise_id`** działają bez zmian (pole
  jest opcjonalne i domyślnie `null`).
* **Widoczność dla klienta** rządzi się dotychczasową zasadą broadcastu:
  karta jest dostępna tylko przy aktywnej relacji z trenerem i tylko dla
  ćwiczeń `ACTIVE`. Link w planie nie omija tej reguły — pobiera kartę
  przez `GET /api/me/exercises/{id}`.

Klient widzi technikę wprost z planu (`pages/client/Plan.tsx`) i z
ekranu „Dzisiaj” (`pages/client/Today.tsx`) — rozwijana sekcja
`ExerciseTechniqueLink`. Gdy ćwiczenia już nie ma, sekcja informuje o tym
neutralnie i odsyła do trenera.

## 7. Dane demo

Seed ładuje pełny katalog (155 ćwiczeń, bez duplikatów nazw) **przed**
planami, a każda pozycja planów i szablonów w seedzie jest podpięta przez
`exercise_id` do istniejącego, aktywnego ćwiczenia. Demo pokazuje
docelowy przepływ „plan układany z bazy”, a nie luźne nazwy
(test: `test_seeded_plans_and_templates_are_linked_to_library`).

## 8. Migracja nr 19 i plan wycofania

Migracja nr 19 (`db.py::MIGRATIONS`) to **12 addytywnych `ALTER TABLE
… ADD COLUMN`** na tabeli `exercises`. Nie zmienia żadnej istniejącej
kolumny, nie usuwa danych, nie wymaga backfillu.

**Plan wycofania (rollback):**

1. **Kod bez danych.** Wycofanie samego wydania aplikacji jest
   bezpieczne bez ruszania bazy: starsza wersja czyta wyłącznie kolumny
   sprzed migracji, a nowe kolumny po prostu ignoruje (SQLAlchemy mapuje
   je tylko wtedy, gdy model je zna). Nadmiarowe kolumny w SQLite i
   PostgreSQL nie przeszkadzają.
2. **Dane pozostają.** Rekomendowane wycofanie to **zostawienie kolumn
   na miejscu** — są NULLable i nic nie kosztują. Ponowne wdrożenie
   odzyskuje pełny opis bez utraty pracy trenera.
3. **Twarde cofnięcie schematu** (tylko awaryjnie): usuń wiersz
   `version = 19` z `schema_migrations` i dopiero wtedy kolumny
   (`ALTER TABLE exercises DROP COLUMN …` — PostgreSQL; w SQLite
   wymagane przepisanie tabeli). **To niszczy opisy** (kroki, błędy,
   wskazówki, mięśnie) — rób kopię zapasową (`backup.py`) przed
   operacją.
4. **Treść planów** (`exercise_id` w `content_json`) **nie jest objęta
   migracją** i przetrwa każde cofnięcie schematu; starsza wersja
   aplikacji zignoruje nieznane pole.

Test migracji na starej bazie:
`tests/test_exercises_extended.py::test_migration_19_adds_nullable_columns_to_existing_database`
(sprawdza też, że każda nowa kolumna jest NULLable, a istniejący wiersz
przetrwał bez zmian). Ścieżkę v1 → wszystkie migracje pokrywa
`tests/test_password_and_confirmation.py::test_migrations_apply_to_existing_v1_database`.

## 9. Dostępność

Zgodnie z rundą P10: każde pole filtrów i edytora ma etykietę powiązaną
`for`/`id`, listy w edytorze (kroki/błędy/wskazówki) mają etykiety
pozycji dla czytników ekranu i opisane przyciski „Usuń”, wybór mięśni to
grupa checkboxów w `fieldset`/`legend`, wyniki wyszukiwarki w edytorze
planu to lista przycisków (pełna obsługa klawiatury), a liczba wyników
jest ogłaszana przez `aria-live="polite"`.

## 10. Auto-uzupełnianie tabeli z wklejonego opisu (od 0.28.0)

Trener wkleja jednolity opis ćwiczenia (własne notatki, fragment
książki, tekst przepisany ze zdjęcia), klika **„Uzupełnij z opisu”** i
dostaje **propozycję** pól tabeli do zatwierdzenia. Przy bazie rzędu
150 pozycji to różnica między wieczorem przepisywania a kilkoma
minutami poprawek.

### 10.1 Zasada nadrzędna: nigdy nie zgadujemy

Pole, którego nie da się odczytać jednoznacznie, **zostaje puste** i
trafia na jawną listę „nie udało się odczytać”. Pięć pustych pól jest
lepsze niż jedno wymyślone: wymyślona wartość wygląda w bazie dokładnie
tak samo jak wartość wpisana ręcznie, więc raz wpuszczona nie daje się
już odróżnić od prawdy.

Z tej zasady wynikają decyzje, które na pierwszy rzut oka wyglądają na
braki funkcji, a są celowe:

* **nie mapujemy rozmyto** („czworogłowy” ≈ „czworoboczny” to odległość
  edycyjna 5 — a to dwa różne mięśnie). Nazwa spoza słownika po prostu
  nie trafia do wyniku;
* **„barki” bez określenia aktonu nie są mapowane** — słownik ma trzy
  osobne klucze (`BARK_PRZEDNI`, `BARK_BOCZNY`, `BARK_TYLNY`) i żaden z
  nich nie jest „domyślny”. Rozpoznajemy dopiero „przedni akton”, „bark
  boczny”, „naramienny tylny” itd.;
* **„podstawowe ćwiczenie” to nie poziom `POCZATKUJACY`** — słownik
  poziomów rozpoznaje wyłącznie słowa, które są nazwą poziomu wprost
  („początkujący”, „średniozaawansowany”, „zaawansowany”);
* **czterocyfrowy ciąg bez słowa „tempo” nie jest tempem** („2026” w
  notatce to rok). Zapis rozdzielony (`3-0-1-0`) jest jednoznaczny i
  wystarcza sam;
* **nazwa ćwiczenia to pierwsza linia tytułowa**, nie pierwsze zdanie
  akapitu — kandydat zakończony kropką jest odrzucany.

### 10.2 Co i po czym rozpoznaje silnik lokalny

Silnik lokalny (`backend/dzik_os/exercise_parser.py`) jest czystą
funkcją: `parse_description(text) -> ParseResult`. Nie ma we/wy, nie
dotyka bazy, nie wysyła niczego na zewnątrz. **Działa zawsze — bez
klucza i bez internetu.**

Odporność na polskie znaki i wielkość liter daje ten sam
`muscles.fold()`, którego używa wyszukiwarka bazy — „POŚLADKI”,
„pośladków” i „posladki” znaczą to samo. Wyrażenia w słownikach są
zapisane **rdzeniami** (`posladk`), a dopasowanie dokleja końcówkę
fleksyjną i pilnuje początku wyrazu (dlatego `rotacj` nie trafia w
środek „antyrotacji”, a `zaawansowan` — w środek
„średniozaawansowany”). Rdzenie dłuższe wygrywają z krótszymi i są
wymazywane z tekstu roboczego, więc „biceps uda” nie rozpada się na
„biceps”, a „trójgłowy łydki” — na „trójgłowy”.

| pole | po czym rozpoznajemy |
| --- | --- |
| `name` | sekcja „Nazwa/Ćwiczenie” albo pierwsza linia tytułowa (≤120 znaków, bez kropki kończącej zdanie) — zawsze **do potwierdzenia** |
| `muscles_primary` / `muscles_secondary` | słownik synonimów (§10.3) + markery podziału (§10.4) |
| `level` | „początkujący”, „średniozaawansowany”, „zaawansowany” (sekcja „Poziom/Zaawansowanie” ma pierwszeństwo) |
| `pattern` | „przysiad”, „martwy ciąg”/„zawias biodrowy”, „wiosłowanie”, „podciąganie”, „wykrok”, „spacer farmera”, „antyrotacja”, „rotacja”, „izolacja”, „cardio”, „mobilność”, „rozciąganie”… Dla „wyciskania” rozstrzyga drugi rdzeń: „leżąc”/„ławka” → poziome, „nad głowę”/„żołnierskie” → pionowe |
| `equipment` | sztanga, hantle, kettlebell, guma oporowa, maszyna, wyciąg, drążek, ławka, TRX, masa własna ciała, orbitrek, bieżnia, rower, piłka lekarska, skrzynia |
| `steps` | sekcja „Wykonanie / Technika / Przebieg / Kroki / Jak wykonać / Sposób wykonania”: lista numerowana lub punktowana → jedna pozycja na punkt; akapit → podział na zdania. Bez sekcji bierzemy wyłącznie jawną listę punktowaną |
| `mistakes` | „Najczęstsze błędy”, „Typowe błędy”, „Czego unikać”, „Uwaga na”, „Błędy” |
| `cues` | „Wskazówki”, „Wskazówka”, „Cue”, „Cues” |
| `safety` | „Bezpieczeństwo”, „Uwagi bezpieczeństwa”, „Przeciwwskazania”, „Uwaga”; awaryjnie zdania z „przeciwwskazan…”, „przy bólu”, „nie wykonuj” |
| `easier` | „Wariant łatwiejszy”, „Regresja”; awaryjnie zdania z „łatwiejsz…”, „regresj…” |
| `harder` | „Wariant trudniejszy”, „Progresja”; awaryjnie zdania z „trudniejsz…”, „progresj…” |
| `tempo_hint` | `3010` albo `3-0-1-0` — czterocyfrowy zapis tylko wtedy, gdy w tekście pada słowo „tempo” |
| `breathing` | „Oddech”, „Oddychanie”; awaryjnie zdania z „wdech”, „wydech”, „oddech” |
| `benefit` | „Efekt”, „Co to daje”, „Korzyści”, „Cel ćwiczenia” |

Nagłówkiem sekcji jest **wyłącznie** linia będąca samą nazwą sekcji
(„Wykonanie”, „- Najczęstsze błędy”) albo nazwą zakończoną dwukropkiem
(„Tempo: 3010”). Zwykłe zdanie, w którym pada słowo „tempo”, nagłówkiem
nie jest — inaczej opis rozsypywałby się na przypadkowe sekcje.

Awaryjne czytanie „po zdaniach” bierze **maksymalnie dwa zdania**:
dłuższy fragment znaczy, że opis nie jest podzielony i lepiej zostawić
pole puste, niż wkleić do niego pół tekstu.

### 10.3 Słownik synonimów partii mięśniowych

Kontrakt: słownik **nie ma prawa** wskazać klucza spoza
`muscles.MUSCLE_LABELS` — sprawdza to asercja przy imporcie modułu
(`_assert_dictionaries`) i osobny test. Rdzenie zapisujemy bez polskich
znaków i bez odmiany.

| klucz | rozpoznawane rdzenie |
| --- | --- |
| `KLATKA_PIERSIOWA` | klatka piersiow, klatk, piersiow, pectoral, chest |
| `NAJSZERSZY_GRZBIETU` | najszersz, latissimus, plec |
| `CZWOROBOCZNY` | czworoboczn, kaptur, trapez, trapezius |
| `ROMBOIDALNE` | romboidaln, równoległoboczn, rhomboid |
| `PROSTOWNIKI_GRZBIETU` | prostownik grzbietu, prostowniki pleców, erector, przykręgosłupow |
| `BARK_PRZEDNI` | bark przedni, przedni akton, akton przedni, naramienny przedni, przednia głowa barku |
| `BARK_BOCZNY` | bark boczny, boczny akton, akton boczny/środkowy, naramienny boczny |
| `BARK_TYLNY` | bark tylny, tylny akton, akton tylny, naramienny tylny, tylna głowa barku |
| `BICEPS` | biceps, dwugłowy ramienia/ramion |
| `TRICEPS` | triceps, trójgłowy ramienia/ramion |
| `PRZEDRAMIE` | przedrami, forearm |
| `BRZUCH_PROSTY` | prosty brzucha, brzuch prosty, brzuch, brzuszn, rectus abdominis |
| `BRZUCH_SKOSNY` | skośn, oblique |
| `MIESNIE_GLEBOKIE` | core, mięśnie głębokie, głębokie, stabilizacj, stabilizator, poprzeczny brzucha, transversus, gorset |
| `POSLADKI` | pośladk, gluteus, glute |
| `CZWOROGLOWY_UDA` | czworogłow, quadriceps, quad, przód uda, przednia część uda |
| `DWUGLOWY_UDA` | dwugłowy uda, **biceps uda**, hamstring, tył uda, tylna część uda, kulszowo-goleniow |
| `PRZYWODZICIELE` | przywodziciel, adductor, wewnętrzna część uda |
| `ODWODZICIELE` | odwodziciel, abductor |
| `LYDKA` | łydk, brzuchat, płaszczkowat, trójgłowy łydki, calf |
| `ZGINACZE_BIODRA` | zginacz biodra, zginacze bioder, biodrowo-lędźwiow, iliopsoas, psoas |

### 10.4 Podział na mięśnie główne i pomocnicze

Podział robią **markery w tekście**, nie heurystyka:

* główne: „mięśnie główne”, „główne mięśnie”, „mięśnie docelowe”,
  „partie główne”, „pracują głównie”, „angażuje głównie”, „przede
  wszystkim”, „mięśnie pierwszorzędowe”;
* pomocnicze: „mięśnie pomocnicze”, „mięśnie wspomagające”,
  „wspomagająco”, „pomocniczo”, „dodatkowo angażuje”, „dodatkowo
  pracują”, „stabilizująco”, „wtórnie”, „drugorzędowe”.

Mięsień trafia do kubełka ostatniego markera stojącego **przed** nim w
tekście; przed pierwszym markerem — do głównych. Ten sam mięsień nie
może być główny i pomocniczy naraz (wygrywa pierwsze wskazanie).

**Gdy w tekście nie ma markera pomocniczych, wszystko trafia do
głównych i cały podział jest oznaczony jako „do potwierdzenia”.**
Dzielenie listy na oko (np. dwa pierwsze główne, reszta pomocnicze)
byłoby zgadywaniem.

### 10.5 Dwa tryby i RÓŻNICA W BRAMKOWANIU ZGÓD względem OCR

| | tryb lokalny | tryb rozszerzony |
| --- | --- | --- |
| kiedy | **zawsze** | gdy operator skonfigurował dostawcę modelu i limity nie są wyczerpane |
| co robi | deterministyczny parser (§10.2) | model wyciąga strukturę dokładniej, zwłaszcza z tekstu ciągłego bez nagłówków |
| co wychodzi na zewnątrz | **nic** | wyłącznie wklejony tekst opisu |
| przy porażce | — | jedno ponowienie, potem wynik lokalny z jawnym powodem |

Przełączanie jest **automatyczne** (`exercise_parser_ai.resolve_mode`) —
kod wywołujący nie ma żadnego przełącznika, a front tylko pokazuje, który
tryb zadziałał i dlaczego.

**Bramką NIE jest zgoda `funkcje_ai` podmiotu danych — i to jest
świadoma różnica względem OCR.** Tryb rozszerzony OCR wymaga zgody
`funkcje_ai` **klienta**, bo na zdjęciu bywają jego dane (etykieta,
kartka, skan wyniku badań). Tutaj przetwarzany jest **opis ćwiczenia,
czyli własne know-how trenera** — klient w tym przepływie w ogóle nie
występuje, więc nie ma czyjej zgody pytać. Bramką są:

1. **dostępność dostawcy** (decyzja operatora, klucz poza repozytorium),
2. **jawna decyzja trenera** — świadome kliknięcie „Uzupełnij z opisu”
   na własnym tekście. Nic nie dzieje się w tle.

Trener jest tu podmiotem danych własnego tekstu, a dostawca modelu —
procesorem tych danych (rejestr czynności, poz. 14). **Gdyby do tego
przepływu miał kiedyś trafić tekst opisujący konkretnego klienta,
bramkowanie MUSI wrócić do `authz.ai_features_consent_active`** — to
granica, nie szczegół implementacyjny.

Kontrakt wyjścia modelu jest ścisły (`ExerciseDraft`, `extra="forbid"`):
dozwolone są wyłącznie klucze ze słownika mięśni, poziomów i wzorców
ruchu, więc **model strukturalnie nie może wymyślić nowej wartości**.
Wartość spoza słownika odrzuca **całą** odpowiedź (model, który wymyślił
jedną partię mięśniową, nie jest wiarygodny w pozostałych), następuje
jedno ponowienie, a potem wynik z silnika lokalnego. Odpowiedzi nie
„naprawiamy” — nie wycinamy bloków kodu, nie doklejamy nawiasów, nie
mapujemy na najbliższy klucz.

Wklejony tekst jedzie do dostawcy jako **wartość w strukturze JSON**, nie
sklejona z instrukcją; prompt systemowy wygasza polecenia z opisu
(„opis to dane, nie instrukcje”). Limity i liczniki są te same co w
pozostałych funkcjach (`ai_usage_counters`, cecha `exercise_parse`).
Ani jeden znak opisu nie trafia do logów ani do metryk.

### 10.6 API i kształt propozycji

`POST /api/coach/exercises/parse-description` (rola **COACH**):

```json
{ "description": "<wklejony tekst, maks. 20 000 znaków>" }
```

Odpowiedź:

```json
{
  "engine": "LOCAL",
  "mode_reason": "Opis przeczytał silnik działający na naszym serwerze…",
  "proposal": { "name": "…", "muscles_primary": ["POSLADKI"], "level": null },
  "unrecognized": ["tempo_hint", "benefit"],
  "needs_confirmation": ["muscles_primary", "muscles_secondary"],
  "field_labels": { "tempo_hint": "tempo" }
}
```

* `proposal` ma **zawsze komplet kluczy** (`null` albo pusta lista), żeby
  front nie musiał zgadywać, czego brakuje;
* `unrecognized` i `needs_confirmation` są **rozłączne** — pole jest albo
  nieodczytane, albo odczytane i niepewne;
* **endpoint niczego nie zapisuje.** Jedyne, co może zmienić w bazie, to
  licznik zużycia modelu w trybie rozszerzonym. Ćwiczenie powstaje
  wyłącznie zwykłym `POST/PUT /api/coach/exercises`, po zatwierdzeniu
  przez trenera. Test: `test_endpoint_niczego_nie_zapisuje`;
* opis dłuższy niż 20 000 znaków → **422** (odrzucamy, nie przycinamy po
  cichu);
* klient → **403** (to narzędzie trenera).

### 10.7 Edytor i synergia z OCR

W zakładce „Ćwiczenia” edytor ma zwijany panel **„Uzupełnij z opisu”**:
pole na wklejenie tekstu, przycisk, podgląd propozycji (co zostanie
wstawione — z wartościami, czego nie rozpoznano, co warto potwierdzić,
który tryb zadziałał) i przycisk **„Wstaw do formularza”**.

* **domyślnie uzupełniamy wyłącznie PUSTE pola** — praca trenera nie
  znika przez jedno kliknięcie. Nadpisanie wypełnionych pól to osobny,
  świadomy przełącznik;
* lista złożona z samych pustych wierszy (edytor list trzyma jeden pusty
  wiersz „na start”) liczy się jako pusta;
* po wstawieniu trener normalnie edytuje i zapisuje — propozycja nie
  jest zapisem;
* **synergia z OCR**: przycisk „Przepisz ze zdjęcia” otwiera **istniejący**
  komponent `OcrCapture` (żadnego drugiego mechanizmu OCR nie budujemy).
  Zatwierdzony tekst dokleja się na końcu pola opisu (nigdy nie kasuje
  tego, co już tam jest). Ścieżka: zdjęcie kartki lub strony z książki →
  tekst → wypełniona tabela;
* dostępność jak w rundzie P10: etykiety powiązane `for`/`id`, pojawienie
  się propozycji ogłasza `aria-live="polite"` (tryb, liczba pól do
  wstawienia, liczba braków i liczba pól do potwierdzenia).

Czysta logika scalania mieszka w `frontend/src/exerciseParser.ts` i jest
testowana w Node (`scripts/test-exercise-parser.mjs`).

### 10.8 Proweniencja wpisu i migracja nr 22

Migracja nr 22 dokłada do tabeli `exercises` dwie kolumny, obie
**NULLable**, bez backfillu:

| pole | wartości |
| --- | --- |
| `source_kind` | `MANUAL` / `TEXT_PARSED` / `AI_ASSISTED`; **NULL = ćwiczenie sprzed migracji** (nie wiemy — świadomie nie udajemy `MANUAL`) |
| `source_engine` | `LOCAL` / `EXTENDED` — **nigdy nazwa dostawcy modelu**; NULL, gdy wpis nie powstał z opisu |

Walidacja serwerowa: wartość spoza słownika → 422; `source_engine` bez
`source_kind` (albo przy `MANUAL`) → 422, bo to proweniencja, która nie
trzyma się kupy. Zwykła edycja ćwiczenia **nie kasuje** proweniencji
zapisanej wcześniej (front odsyła ją z powrotem).

> **Numeracja:** numer 21 jest zarezerwowany dla równoległej rundy —
> luka w `MIGRATIONS` jest świadoma i niczego nie psuje (`run_migrations`
> stosuje brakujące numery w kolejności).

**Plan wycofania (rollback):**

1. **Kod bez danych.** Wycofanie samego wydania jest bezpieczne bez
   ruszania bazy: starsza wersja aplikacji nie zna tych kolumn i po
   prostu ich nie czyta. Nadmiarowe kolumny w SQLite i PostgreSQL nie
   przeszkadzają.
2. **Dane pozostają.** Rekomendowane wycofanie to zostawienie kolumn na
   miejscu — są NULLable i nic nie kosztują.
3. **Twarde cofnięcie schematu** (tylko awaryjnie): usuń wiersz
   `version = 22` z `schema_migrations`, dopiero potem kolumny
   (`ALTER TABLE exercises DROP COLUMN …` — PostgreSQL; w SQLite
   wymagane przepisanie tabeli). Traci się wtedy **wyłącznie
   proweniencję**; opisy ćwiczeń pozostają nietknięte. Kopia zapasowa
   (`backup.py`) przed operacją jak zwykle.

Testy: `tests/test_exercise_parser.py::test_migracja_22_dodaje_nullable_kolumny_do_starej_bazy`
oraz ścieżka v1 → wszystkie migracje w
`tests/test_password_and_confirmation.py::test_migrations_apply_to_existing_v1_database`.

### 10.9 Znane ograniczenia

* **Tekst ciągły bez nagłówków w trybie lokalnym daje mniej pól.** Bez
  sekcji „Wykonanie”, „Najczęstsze błędy”, „Wskazówki” te listy zostają
  puste (bierzemy wyłącznie jawną listę punktowaną), a nazwa nie jest
  odczytywana, jeśli pierwsza linia jest zdaniem. Mięśnie, poziom,
  wzorzec ruchu i sprzęt czytamy z tekstu ciągłego normalnie. To jest
  dokładnie ten przypadek, w którym pomaga tryb rozszerzony.
* **„Barki” bez aktonu** i inne terminy zbiorcze nie są mapowane (§10.1).
* **Nie czytamy `muscle_group`** (zgrubna grupa do widoku listy) ani
  `video_url` — grupę trener wybiera z listy rozwijanej, link wkleja sam.
* **Parser nie ocenia treści.** Nie sprawdza, czy opis jest sensowny
  treningowo, nie poprawia stylu i nie wykrywa porad medycznych —
  odpowiedzialność merytoryczna zostaje po stronie trenera (§1).
* **Jeden opis = jedno ćwiczenie.** Wklejenie całego rozdziału z pięcioma
  ćwiczeniami da jedną, pomieszaną propozycję.

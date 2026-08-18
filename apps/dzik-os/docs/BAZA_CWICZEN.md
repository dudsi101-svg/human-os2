# Baza ćwiczeń — model, słownik mięśni, zasady opisów

Dokument opisuje rozbudowaną bazę ćwiczeń Dzik OS (wersja 0.22.0):
model danych, **kontrakt słownika partii mięśniowych** (wspólny z
planowanym rysunkiem sylwetki), zasady pisania opisów, API filtrów,
sposób układania planu treningowego z bazy oraz plan wycofania
migracji nr 19.

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

# Baza produktów spożywczych

Dokument opisuje pochodzenie danych w katalogu produktów, zasadę
przybliżenia, API wyszukiwania i stronicowania, format CSV importu/eksportu
oraz plan wycofania migracji nr 18.

Kod: `backend/dzik_os/food_catalog_data.py` (dane katalogu),
`backend/dzik_os/routers/food_catalog.py` (API),
`frontend/src/foodUtils.ts` + `frontend/src/FoodCatalog.tsx` (widok).

## 1. Pochodzenie i status danych

* Wartości pochodzą z **ogólnodostępnych tabel wartości odżywczych** i są
  **uśrednione** dla produktów dostępnych w Polsce. W bazie zapisujemy to
  wprost w kolumnie `source`: „tabele wartości odżywczych, wartości
  uśrednione”.
* Katalog jest **markowo neutralny**: nazwy są generyczne („Ser żółty typu
  gouda”, „Odżywka białkowa WPC (proszek)”). Nie ma nazw producentów ani
  nazw handlowych — wpisanie konkretnej marki zmieniłoby katalog w reklamę
  i uzależniło wartości od jednej etykiety.
* Katalog jest **opisowy, nie oceniający**. Nie zawiera twierdzeń
  zdrowotnych ani rekomendacji („zdrowe”, „unikaj”, „polecane”). Produkt to
  liczby i uwagi techniczne; o zastosowaniu decyduje trener wspólnie z
  podopiecznym.
* Tam, gdzie obróbka istotnie zmienia wartości (ryż, makaron, kasza,
  strączki, mięso), stan jest rozróżniony w nazwie **i** w kolumnie `note`
  („wartości dla produktu suchego (przed ugotowaniem)” / „…ugotowanego” /
  „…dania gotowego do spożycia”).

### Zasada przybliżenia (widoczna w interfejsie)

Każda odpowiedź API katalogu, kalkulatora porcji i kompozytora diety niesie
pole `disclaimer` o treści:

> Wartości odżywcze są przybliżone i uśrednione — realne zależą od marki,
> partii, obróbki i sposobu przygotowania. Traktuj je jako punkt wyjścia do
> oszacowania, nie jako pomiar.

Interfejs pokazuje ten tekst **przy katalogu i przy kalkulatorze porcji**
(`FoodDisclaimer` w `frontend/src/FoodCatalog.tsx`). To jest świadoma
decyzja: uczciwość danych ma być widoczna dla użytkownika, a nie schowana w
dokumentacji technicznej. Frontend ma własny, identyczny tekst zapasowy
(`FOOD_APPROXIMATION_HINT`) na wypadek starszej odpowiedzi API — źródłem
prawdy pozostaje backend.

## 2. Zakres katalogu (seed)

409 pozycji w 16 kategoriach:

| Kategoria | Pozycji |
| --- | --- |
| Mięso i drób | 40 |
| Ryby i owoce morza | 27 |
| Jaja | 9 |
| Nabiał | 39 |
| Zboża i pieczywo | 32 |
| Kasze, ryż i makarony | 28 |
| Warzywa | 46 |
| Owoce | 34 |
| Rośliny strączkowe | 19 |
| Orzechy i nasiona | 20 |
| Tłuszcze i oleje | 15 |
| Przekąski i słodycze | 24 |
| Napoje | 20 |
| Odżywki i suplementy | 15 |
| Dania gotowe i fast food | 22 |
| Przyprawy i dodatki | 19 |

Katalog trafia do bazy jako produkty **trenera demo** (broadcast, ten sam
wzorzec co ćwiczenia i baza wiedzy). Każdy trener ma własny, odizolowany
katalog — patrz `PERMISSIONS.md`.

## 3. Model danych (migracja nr 18)

Migracja nr 18 dokłada do `food_products` pięć kolumn, wszystkie **NULLable**
i wszystkie opcjonalne w API:

| Kolumna | Typ | Znaczenie |
| --- | --- | --- |
| `fiber_100g` | FLOAT | błonnik na 100 g; `NULL` = brak danych (**nie** zero) |
| `unit_name` | VARCHAR(60) | nazwa jednostki sztukowej („kromka”, „jajko M (bez skorupki)”) |
| `unit_grams` | FLOAT | ile waży jedna sztuka; sensowne wyłącznie w parze z `unit_name` |
| `source` | VARCHAR(200) | skąd pochodzą wartości |
| `note` | VARCHAR(300) | uwagi („wartości dla produktu ugotowanego”, „bez dodatku cukru”) |

**Zgodność wsteczna.** Produkty utworzone przed migracją działają bez zmian:
nowe pola są puste, a nie wyzerowane (0 g błonnika to twierdzenie, brak
danych — nie). Żądanie `POST/PUT /api/coach/food-products` w starym
kształcie (bez nowych pól) nadal przechodzi. Test:
`tests/test_food_catalog_extended.py::test_migration_18_adds_columns_to_old_database`
oraz `…::test_create_product_with_new_fields_and_backward_compatibility`.

### Plan wycofania migracji nr 18

Migracja jest czysto addytywna, więc wycofanie nie wymaga przenoszenia
danych:

1. Usunąć krotkę `(18, …)` z `MIGRATIONS` w `backend/dzik_os/db.py` oraz
   pięć pól z `FoodProduct` (`models.py`), `FoodProductIn` (`schemas.py`)
   i `_out()`/`_apply_input()` (`routers/food_catalog.py`).
2. Usunąć endpointy `/api/food-products/portion`,
   `/api/coach/food-products/import`, `/api/coach/food-products/export`
   oraz moduł `food_catalog_data.py` (seed wraca do krótkiej listy krotek).
3. W bazie: `DELETE FROM schema_migrations WHERE version = 18`. Kolumn
   **nie trzeba** usuwać — SQLite pozostawi je jako nieużywane i nikt ich
   nie czyta. Jeśli mimo to mają zniknąć, w SQLite ≥ 3.35 działa
   `ALTER TABLE food_products DROP COLUMN <nazwa>` dla każdej z pięciu.
4. Wycofanie **nie usuwa produktów** — traci się wyłącznie błonnik,
   jednostki sztukowe, źródła i uwagi. Wcześniejszy eksport CSV (punkt 5)
   zachowuje te dane poza aplikacją.

## 4. API: wyszukiwanie, filtrowanie, stronicowanie

`GET /api/coach/food-products` (trener, własny katalog) oraz
`GET /api/me/food-products` (klient, AKTYWNE produkty trenerów z aktywną
relacją) przyjmują te same parametry:

| Parametr | Domyślnie | Znaczenie |
| --- | --- | --- |
| `q` | — | fragment nazwy; bez uwzględniania wielkości liter i polskich znaków |
| `category` | — | dokładna nazwa kategorii |
| `sort` | `name` | `name` (A→Z), `kcal` (malejąco), `protein` (malejąco) |
| `limit` | 50 (max 500) | rozmiar strony |
| `offset` | 0 | przesunięcie strony |
| `status` | `ACTIVE` | tylko trener: `ACTIVE` / `ARCHIVED` / `ALL` |

Odpowiedź: `{items, total, limit, offset, has_more, categories, disclaimer}`.
`categories` liczone są z **całego** katalogu (przed filtrami), bo służą do
zbudowania listy filtra. Widok ładuje 30 pozycji i dokłada kolejne przez
„Pokaż więcej” — 400+ rekordów nigdy nie trafia do przeglądarki naraz.

**Dopasowanie nazw.** Zapytanie i nazwa są normalizowane: małe litery,
`ą→a, ć→c, ę→e, ł→l, ń→n, ó→o, ś→s, ż→z, ź→z` plus rozkład NFKD. Dzięki temu
„losos”, „ŁOSOŚ” i „Losos” trafiają w „Łosoś, surowy”. Gdy dopasowanie
ścisłe nie da nic, robimy **drugi przebieg luźny**: pasuje produkt, którego
któreś słowo (min. 4 znaki) jest fragmentem zapytania — tak „lososiowy”
znajduje „Łosoś”. Dwa osobne przebiegi (zamiast jednego luźnego) są celowe:
normalne wyszukiwanie nie ma zwracać szumu.

**Kompromis wydajnościowy.** Filtr nazwy i sortowanie działają w Pythonie,
bo SQLite nie usuwa znaków diakrytycznych w SQL. Przy katalogu rzędu setek
pozycji na trenera to nieodczuwalne; gdyby katalogi urosły o rząd
wielkości, właściwym krokiem jest kolumna ze znormalizowaną nazwą +
indeks, a nie porzucenie odporności na polskie znaki.

## 5. Kalkulator porcji

`POST /api/food-products/portion` (każdy zalogowany, w granicach widoczności
produktu — patrz `PERMISSIONS.md`):

```json
{"product_id": "HOS-FOD-…", "grams": 200}
{"product_id": "HOS-FOD-…", "units": 2}
```

* `grams` **albo** `units` — podanie obu naraz to 422 (wynik ma być
  jednoznaczny); pominięcie obu liczy typową porcję produktu, a gdy jej nie
  ma — 100 g.
* `units` wymaga `unit_grams` na produkcie (inaczej 422 z nazwą produktu):
  „2 jajka” = 2 × 50 g = 100 g.
* Odpowiedź: `grams`, `units`, `unit_name`, `kcal` (całkowite),
  `protein_g`/`fat_g`/`carbs_g`/`fiber_g` (0,1 g), `note`, `source`,
  `disclaimer`. `fiber_g` to `null`, gdy produkt nie deklaruje błonnika.

Ta sama arytmetyka żyje w `frontend/src/foodUtils.ts`
(`computePortion`, `unitsToGrams`, `gramsToUnits`) i to ona zasila widok —
panel trenera i panel klienta liczą identycznie. Zaokrąglenia: kalorie do
pełnych, makro do 0,1 g. Więcej miejsc po przecinku sugerowałoby precyzję,
której te dane nie mają.

## 6. Format CSV (import i eksport)

`GET /api/coach/food-products/export` zwraca cały katalog trenera jako CSV
(UTF-8 z BOM, przecinek jako separator, nazwa pliku
`dzik-os-produkty.csv`). Eksport obejmuje też produkty zarchiwizowane.

Nagłówek i kolejność kolumn:

```
nazwa,kategoria,kcal_100g,bialko_100g,tluszcz_100g,wegle_100g,blonnik_100g,porcja_g,jednostka,jednostka_g,zrodlo,uwagi
```

| Kolumna | Wymagana | Zakres / uwagi |
| --- | --- | --- |
| `nazwa` | tak | do 300 znaków; klucz dopasowania przy imporcie |
| `kategoria` | nie | do 80 znaków; puste → `Inne` |
| `kcal_100g` | tak | 0–900 |
| `bialko_100g` | tak | 0–100 |
| `tluszcz_100g` | tak | 0–100 |
| `wegle_100g` | tak | 0–100 |
| `blonnik_100g` | nie | 0–100; puste → brak danych |
| `porcja_g` | nie | 0–5000 |
| `jednostka` | nie | do 60 znaków; wymaga `jednostka_g` |
| `jednostka_g` | nie | 0–5000 |
| `zrodlo` | nie | do 200 znaków |
| `uwagi` | nie | do 300 znaków |

`POST /api/coach/food-products/import` (pole `file`, multipart):

* Akceptuje separator `,` **albo** `;` (wykrywany z pierwszej linii) i
  przecinek dziesiętny — pliki z polskiego arkusza kalkulacyjnego działają
  bez konwersji. Kodowanie: UTF-8, opcjonalny BOM.
* **Limit 1000 wierszy** na plik; nadmiar jest pomijany z wpisem w raporcie.
* **Brak wymaganych kolumn** = 422 dla całego pliku (nie da się go sensownie
  odczytać). Nieznane kolumny są ignorowane i wypisane w
  `unknown_columns`.
* Błąd w wierszu **nie przerywa importu**. Raport:
  `{created, updated, skipped, errors: [{row, field, message}], unknown_columns}`.
  `row` liczy od 1 dla nagłówka, więc pierwszy wiersz danych to 2.
* **Upsert po nazwie w obrębie katalogu trenera** (dopasowanie
  znormalizowane, jak w wyszukiwarce). Powtórzona nazwa w jednym pliku =
  wiersz pominięty z opisem — plik nie tworzy duplikatów.
* **Izolacja trenerów**: import dotyka wyłącznie produktów zalogowanego
  trenera. Wiersz o nazwie identycznej z produktem innego trenera tworzy
  **nowy** produkt importującego i nie modyfikuje cudzego
  (`test_csv_import_never_touches_another_coach_catalog`). Eksport w drugą
  stronę zawiera wyłącznie własne produkty.
* Eksport → import do własnego katalogu jest **idempotentny**: 0 nowych,
  reszta zaktualizowana identycznymi wartościami
  (`test_csv_export_then_import_is_idempotent`).

Oba działania są audytowane (`FOOD_CATALOG_EXPORTED`, `FOOD_CATALOG_IMPORTED`)
bez treści produktów — w zdarzeniu są tylko liczniki.

### Dlaczego CSV, a nie własny format

Prawo wyjścia (Human OS: portability i exit) wymaga formatu, który da się
otworzyć bez tej aplikacji. CSV otwiera każdy arkusz kalkulacyjny; trener
może trzymać katalog u siebie, przenieść go do innego narzędzia albo wrócić
z nim po przerwie. Dlatego eksport nie jest niczym bramkowany i obejmuje
komplet danych, także archiwum.

## 7. Testy

`backend/tests/test_food_catalog_extended.py` (33 testy): migracja nr 18 na
starej bazie, rozmiar katalogu i brak duplikatów, obecność `source` i
jednostek, `disclaimer` w odpowiedziach, wyszukiwanie z polskimi znakami i
przebieg luźny, filtr kategorii, stronicowanie i `has_more`, sortowanie,
kalkulator porcji (gramy, sztuki, błonnik, przypadki błędne, widoczność
klienta i 404 dla cudzego produktu), import CSV (poprawny, z błędami,
średnik i przecinek dziesiętny, wiersze krótsze/dłuższe od nagłówka,
duplikaty w pliku, pusty plik, rola),
eksport CSV (nagłówek, izolacja, idempotentny obieg) i walidacja zakresów.

`frontend/scripts/test-food-utils.mjs` (13 testów, `npm run test:helpers`):
normalizacja nazw, dopasowanie zapytania, przeliczenia gram↔sztuka,
odporność na złe dane wejściowe, błonnik jako brak danych vs. zadeklarowane
zero, formatowanie porcji.

Zmiana w istniejących testach: `tests/test_food_products.py` nie zakłada już,
że cały katalog przychodzi w jednej odpowiedzi — produkty wyszukuje przez
`?q=`, a test klienta sprawdza rozmiar strony i `total` zamiast długości
listy.

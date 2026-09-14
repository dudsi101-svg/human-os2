# Zakładka „Monitoring" / „Postępy" — specyfikacja

Wersja 1.0 · 13.09.2026 · Moduł: nawigacja główna (klient + trener) · Status: do przeglądu

---

## 1. Cel

Zastąpić zakładkę **„Raport"** nową zakładką postępów, przenieść do niej treść **„Postępy"** z zakładki „Więcej" i rozbudować ją o postęp treningowy oraz rekordy. Zakładka ma być głównym miejscem, do którego klient wraca między treningami, a trener — miejscem wczesnego wykrywania klientów, którzy wypadają z rytmu.

Dotychczasowa treść zakładki „Raport" przechodzi do „Więcej" bez zmian funkcjonalnych.

## 2. Nazewnictwo (decyzja projektowa)

Ta sama zakładka, różna etykieta zależnie od roli:

| Rola | Etykieta w nawigacji | Uzasadnienie |
|---|---|---|
| Klient | **Postępy** | „Monitoring" po stronie klienta czyta się jako nadzór i obniża chęć wchodzenia w zakładkę |
| Trener | **Monitoring** | trener faktycznie monitoruje portfel klientów |

Route wspólny: `/monitoring`. Etykieta i domyślna sekcja zależą od roli, nie od osobnego modułu.

## 3. Cele i miary

| Cel | Miara |
|---|---|
| Zakładka jest odwiedzana regularnie | ≥ 3 wejścia/tydzień na aktywnego klienta |
| Rekord jest zauważany | ≥ 60 % nowych PR obejrzanych w ciągu 48 h |
| Trener wcześniej łapie odpady | mediana czasu od 10 dni bez treningu do kontaktu trenera < 48 h |
| Zastój wagi nie wypycha z aplikacji | brak spadku wejść w tygodniach bez zmiany wagi |

## 4. Kluczowa zasada projektowa: trzy niezależne osie postępu

Jeśli zakładka opiera się na wadze, to przy dwutygodniowym zastoju — a zastoje są normą — zaczyna demotywować. Dlatego zawsze widoczne są trzy osie, z których prawie zawsze przynajmniej jedna rośnie:

1. **Forma** — rekordy, szacowany 1RM, tonaż
2. **Sylwetka** — waga (średnia krocząca), obwody, zdjęcia
3. **Konsekwencja** — frekwencja, seria tygodni, realizacja diety

Kolejność sekcji w widoku klienta: **Forma → Konsekwencja → Sylwetka**. Sylwetka jest najniżej celowo — jest najbardziej opóźniona i najbardziej zaszumiona.

## 5. Poza zakresem (v1)

- Rekordy w ćwiczeniach mierzonych czasem lub dystansem (cardio, plank) — projektuj tabelę rekordów tak, by dało się dodać typ `TIME` / `DISTANCE`.
- Porównania między klientami, rankingi, elementy społecznościowe. **Nie dodawać** — w kontekście treningowym podnoszą ryzyko u części klientów i nie są celem produktu.
- Automatyczne wnioski trenerskie generowane przez model („zwiększ objętość na plecy").
- Eksport PDF postępów (P1, osobna specyfikacja).
- Integracje z zegarkami.

---

## 6. Widok klienta

### 6.1 Nagłówek tygodnia

Trzy kafelki, zawsze na górze, zawsze w tej samej kolejności:

| Kafelek | Treść | Gdy brak danych |
|---|---|---|
| Treningi | `2 / 3` w tym tygodniu + kropki dni | „Brak zaplanowanych treningów" |
| Konsekwencja | seria tygodni z wykonanym planem, np. `5 tygodni` | „Zacznij serię" |
| Trend wagi | `−0,4 kg/tydz` na podstawie regresji z 28 dni | „Za mało pomiarów (min. 3 w 14 dniach)" |

Kafelek wagi nie pokazuje się wcale, jeśli klient ma flagę ograniczającą (sekcja 10.1).

### 6.2 Sekcja „Rekordy"

**Górna wstęga:** rekordy z ostatnich 30 dni, najnowsze pierwsze, maksymalnie 5, z datą i wartością poprzednią („85 kg → 90 kg, +5 kg, 12 dni od poprzedniego").

**Poniżej:** lista ćwiczeń posortowana malejąco po dacie ostatniego wykonania. Dla każdego: aktualny rekord ciężaru, szacowany 1RM, data ustanowienia, mikro-wykres 1RM z ostatnich 6 miesięcy.

Ćwiczenia niewykonywane od ponad 90 dni w zwijanej sekcji „Archiwum".

### 6.3 Sekcja „Trening"

- Tonaż tygodniowy (suma ciężar × powtórzenia) — słupki, 12 tygodni, z linią średniej 4-tygodniowej
- Liczba serii na grupę mięśniową w tygodniu — słupki poziome, z zaznaczeniem tygodnia poprzedniego dla porównania
- Kalendarz aktywności — heatmapa 12 tygodni

### 6.4 Sekcja „Konsekwencja"

- Frekwencja: wykonane / zaplanowane, ostatnie 8 tygodni
- Najdłuższa seria vs aktualna seria
- Realizacja diety, jeśli moduł diety jest aktywny dla klienta (odsetek dni z odhaczonym jadłospisem)

### 6.5 Sekcja „Sylwetka"

- **Waga:** surowe pomiary jako szare punkty, średnia krocząca 7 dni jako linia. Liczba pokazywana klientowi to **zawsze średnia**, nigdy ostatni pomiar. Trend w kg/tydzień z regresji liniowej po średniej z 28 dni.
- **Obwody:** wybrane przez klienta 2–4 miary, wykresy liniowe, wartość bieżąca i różnica od pierwszego pomiaru
- **Zdjęcia:** siatka po dacie, tryb porównania dwóch dat obok siebie

## 7. Widok trenera

### 7.1 Ekran wejściowy — lista klientów z sygnałami

Tabela klientów sortowana domyślnie po priorytecie sygnału. Sygnały (konfigurowalne progi, wartości domyślne):

| Sygnał | Warunek domyślny | Waga |
|---|---|---|
| Brak treningu | 10 dni bez zapisanej sesji | wysoka |
| Frekwencja spada | < 50 % planu w 2 kolejnych tygodniach | wysoka |
| Brak ważeń | 14 dni bez pomiaru | średnia |
| Spadek tonażu | −25 % wobec średniej 4-tygodniowej | średnia |
| Cel rozjeżdża się z trendem | cel redukcja, trend +0,2 kg/tydz przez 21 dni | średnia |
| Nowy rekord | PR w ostatnich 7 dniach | informacyjna (powód do kontaktu pozytywnego) |

Kolumny: klient, ostatnia aktywność, frekwencja 4 tyg., trend wagi, sygnały.

### 7.2 Widok pojedynczego klienta

Ten sam układ co widok klienta (sekcje 6.2–6.5), plus:
- pełne dane liczbowe niezależnie od flag klienta (filtrowanie dotyczy tylko roli klienta)
- surowe pomiary wagi bez wygładzania, przełącznik „pokaż średnią"
- notatki trenera przypięte do dat
- historia zmian planu treningowego nałożona na wykres tonażu

---

## 8. Mechanika rekordów

To najbardziej motywująca i najłatwiejsza do zepsucia część zakładki. Definicje muszą być jednoznaczne.

### 8.1 Typy rekordów

| Typ | Definicja |
|---|---|
| `WEIGHT` | największy ciężar, przy którym wykonano ≥ 1 powtórzenie |
| `REPS_AT_WEIGHT` | najwięcej powtórzeń przy dokładnie tym samym ciężarze |
| `SET_VOLUME` | maksimum ciężar × powtórzenia w jednej serii |
| `SESSION_VOLUME` | maksymalny tonaż tego ćwiczenia w jednej sesji |
| `E1RM` | szacowany ciężar maksymalny, wzór Epleya: `w × (1 + r / 30)` |

### 8.2 Zasady liczenia i zabezpieczenia

1. **Pierwsze wykonanie ćwiczenia nie jest rekordem.** Rekord ogłaszamy dopiero, gdy istnieje co najmniej jedna wcześniejsza sesja z tym ćwiczeniem. Bez tego pierwszy trening generuje kilkanaście fałszywych PR i cała sekcja traci wiarygodność.
2. **`E1RM` liczymy tylko dla `r ≤ 10`.** Powyżej wzór Epleya rozjeżdża się na tyle, że nie wolno na jego podstawie ogłaszać rekordu. Serie 12+ powtórzeń nadal wchodzą do rekordów objętościowych.
3. W UI `E1RM` zawsze oznaczony jako **szacowany**, z jednozdaniowym wyjaśnieniem po najechaniu/dotknięciu.
4. Serie oznaczone jako rozgrzewkowe, nieukończone lub wykonane z asekuracją są wykluczone ze wszystkich typów rekordów.
5. **Wariant ćwiczenia = osobne ćwiczenie.** Wyciskanie sztangą, hantlami i na maszynie mają rozdzielne rekordy. Jeśli w bazie nie ma rozróżnienia wariantów, nie scalaj ich sztucznie — zgłoś to zamiast obchodzić.
6. Jednostki normalizowane do kilogramów przy zapisie, nie przy wyświetlaniu.
7. Ćwiczenia z masą ciała: `w` = obciążenie dodatkowe. Przy `w = 0` liczymy wyłącznie `REPS_AT_WEIGHT`; `WEIGHT` i `E1RM` nie mają sensu i nie są pokazywane.
8. Rekord wyrównany (ta sama wartość) **nie jest** nowym rekordem, ale jest widoczny jako „wyrównany" bez powiadomienia.
9. Ręczna korekta serii przez klienta lub trenera musi wywołać przeliczenie rekordów dla tego ćwiczenia — łącznie z **cofnięciem** rekordu, jeśli usunięto serię, która go ustanowiła.

### 8.3 Powiadomienie o rekordzie

Powiadomienie po zapisaniu sesji, maksymalnie **jedno na sesję**, zbiorcze („3 nowe rekordy w tym treningu"). Bez powiadomień push w v1 — tylko wewnątrz aplikacji i w widoku trenera.

## 9. Mechanika wagi

- Średnia krocząca 7 dni; okno wymaga **min. 3 pomiarów**, inaczej punkt nie jest liczony.
- Trend: regresja liniowa po średniej kroczącej z 28 dni, wynik w kg/tydzień, zaokrąglony do 0,1.
- Trend pokazywany dopiero przy ≥ 14 dniach danych i ≥ 6 pomiarach. Wcześniej: „Zbieramy dane — trend pojawi się po dwóch tygodniach".
- Klientowi nigdy nie pokazujemy pojedynczego ostatniego pomiaru jako „Twojej wagi".

## 10. Bezpieczeństwo i prywatność

### 10.1 Flagi zdrowotne

Wywiad kaloryczny zawiera flagę `ZABURZENIA_ODZYWIANIA` (specyfikacja `wywiad_zapotrzebowanie_kaloryczne.md`, sekcja 6.4). Ta sama zasada obowiązuje tutaj:

- dla roli klient z tą flagą odpowiedź API **nie zawiera** żadnych danych wagowych, obwodowych ani kalorycznych,
- filtrowanie **po stronie serwera**, nie ukrywanie w UI,
- sekcja „Sylwetka" nie renderuje się, kafelek trendu wagi znika, a nie pokazuje pustego stanu,
- widok trenera pozostaje pełny,
- test integracyjny: odpowiedź API dla klienta z flagą nie zawiera pola `weight` na żadnym poziomie zagnieżdżenia.

### 10.2 Zdjęcia postępów

- Dostęp wyłącznie dla właściciela i przypisanego trenera, autoryzacja sprawdzana przy każdym żądaniu pliku, nie tylko przy listowaniu.
- Adresy plików niegadalne (UUID, nie sekwencja).
- Usunięcie zdjęcia usuwa plik, nie tylko rekord.

---

## 11. Model danych

Agent ma **najpierw rozpoznać istniejące modele** sesji treningowych, serii, ćwiczeń, pomiarów ciała i zdjęć. Poniższe nazwy są propozycją do dopasowania, nie nakazem tworzenia duplikatów.

### 11.1 Nowa tabela `exercise_record`

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | UUID | |
| `client_id` | FK | |
| `exercise_id` | FK | wariant = osobne ćwiczenie |
| `record_type` | enum | `WEIGHT`, `REPS_AT_WEIGHT`, `SET_VOLUME`, `SESSION_VOLUME`, `E1RM` |
| `value` | numeric | w kg lub powtórzeniach |
| `secondary_value` | numeric, null | np. ciężar przy `REPS_AT_WEIGHT` |
| `set_id` | FK, null | seria, która ustanowiła rekord |
| `achieved_at` | timestamp | |
| `previous_value` | numeric, null | do pokazania skoku |
| `superseded_at` | timestamp, null | historia zamiast nadpisywania |

Historia rekordów jest zachowywana (`superseded_at`), nie nadpisywana — inaczej nie da się pokazać krzywej progresu ani cofnąć błędnego wpisu.

### 11.2 Agregaty

Tonaż tygodniowy i serie na grupę mięśniową liczone jako agregat wyliczany przy zapisie sesji i zapisywany w tabeli pomocniczej, nie liczony od zera przy każdym wejściu w zakładkę. Wymagane polecenie `recalculate_progress --client=<id>` do przeliczenia po zmianach w danych lub w regułach.

### 11.3 Backfill

Jednorazowe zadanie liczące rekordy i agregaty z całej dotychczasowej historii. Musi być idempotentne i uruchamialne na pojedynczym kliencie. Uruchomienie na kopii produkcyjnej i porównanie liczby wykrytych PR z ręcznym przeglądem 3 klientów przed wdrożeniem.

## 12. API

| Endpoint | Rola | Zwraca |
|---|---|---|
| `GET /monitoring/summary` | klient, trener | kafelki nagłówka, filtrowane wg roli i flag |
| `GET /monitoring/records` | klient, trener | rekordy, paginowane, z historią na żądanie |
| `GET /monitoring/training?range=12w` | klient, trener | tonaż, serie/grupa, kalendarz |
| `GET /monitoring/body` | klient, trener | waga, obwody, zdjęcia — **404 dla klienta z flagą**, nie pusta odpowiedź |
| `GET /monitoring/clients` | trener | lista z sygnałami, sortowana |
| `GET /monitoring/clients/{id}` | trener | pełne dane pojedynczego klienta |

Wszystkie endpointy sprawdzają relację trener–klient po stronie serwera. Trener bez przypisania do klienta dostaje 403, nie pustą listę.

## 13. Migracja nawigacji

1. Nowa zakładka `/monitoring` w pozycji zajmowanej dotąd przez „Raport".
2. Treść „Raport" przeniesiona do „Więcej" jako pozycja listy, bez zmian funkcjonalnych. Stary route `/raport` → przekierowanie 301 do nowej lokalizacji, nie usunięcie (istniejące linki w mailach i zakładkach przeglądarki).
3. Pozycja „Postępy" znika z „Więcej"; jej dotychczasowa zawartość staje się sekcjami 6.4–6.5.
4. Cała zakładka za feature flagą `monitoring_tab_enabled`, domyślnie wyłączoną. Przy wyłączonej fladze nawigacja wygląda jak dziś.
5. Kolejność wdrożenia: włączyć flagę dla konta trenera → 3 klientów testowych → wszyscy.

## 14. Testy

**Jednostkowe — rekordy:**
- pierwsze wykonanie ćwiczenia nie generuje rekordu
- drugie wykonanie z większym ciężarem generuje dokładnie jeden rekord `WEIGHT`
- seria 12 powtórzeń nie generuje `E1RM`, ale generuje `SET_VOLUME`
- wyrównanie rekordu nie tworzy nowego wpisu i nie wywołuje powiadomienia
- usunięcie serii ustanawiającej rekord cofa rekord do poprzedniej wartości
- seria rozgrzewkowa jest ignorowana we wszystkich typach
- ćwiczenie z masą ciała bez obciążenia nie generuje `WEIGHT` ani `E1RM`
- ten sam ciężar w funtach i kilogramach daje jeden rekord, nie dwa

**Jednostkowe — waga:**
- 2 pomiary w oknie 7 dni → brak punktu średniej
- trend przy 10 dniach danych → komunikat zamiast liczby
- pojedynczy skok o 2 kg nie zmienia trendu o więcej niż 0,2 kg/tydz

**Integracyjne:**
- klient z flagą `ZABURZENIA_ODZYWIANIA`: odpowiedź `/monitoring/summary` i `/monitoring/body` nie zawiera pola `weight` na żadnym poziomie
- trener bez przypisania: 403 na `/monitoring/clients/{id}`
- backfill uruchomiony dwukrotnie daje identyczny stan tabeli rekordów
- `/raport` przekierowuje, nie zwraca 404

**Wydajnościowe:**
- `/monitoring/summary` dla klienta z 2 latami historii poniżej 300 ms
- `/monitoring/clients` dla 100 klientów bez zapytań N+1 (test liczby zapytań)

## 15. Ryzyka

| Ryzyko | Przeciwdziałanie |
|---|---|
| Fałszywe rekordy z pierwszych treningów podważają wiarygodność sekcji | reguła 8.2.1 + backfill przed włączeniem flagi |
| Zakładka demotywuje w zastoju | trzy osie postępu, waga najniżej, średnia zamiast surowego pomiaru |
| Klient z zaburzeniami odżywiania dostaje ekran pełen liczb | filtrowanie serwerowe + test integracyjny |
| Wolne zapytania przy długiej historii | agregaty materializowane, testy liczby zapytań |
| Trener przestaje przeglądać listę, bo wszyscy mają sygnały | progi konfigurowalne, sortowanie po priorytecie, sygnał pozytywny (PR) obok negatywnych |

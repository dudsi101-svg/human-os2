# Import bazy danych z pliku — dokładna struktura

Dokument opisuje **format plików**, które aplikacja przyjmuje w panelu
trenera: bazę ćwiczeń i bazę szablonów treningowych. Jeśli przygotowujesz
bazę na zewnątrz (arkusz, eksport z innego narzędzia, praca kogoś innego) —
to jest specyfikacja, którą trzeba spełnić.

Kontrakt kolumn żyje w kodzie (`backend/dzik_os/sheet_import.py`), a ten
dokument i wzór do pobrania w aplikacji są z niego wyprowadzone. Endpoint
`GET /api/coach/exercises/import-schema` zwraca dokładnie to samo w JSON-ie,
więc opis w aplikacji nie może rozjechać się z tym, co realnie przyjmuje
import.

**Szukasz instrukcji dla osoby przygotowującej dane, a nie specyfikacji?**
Jest osobny, krótszy dokument bez żargonu: `docs/INSTRUKCJA_PLIK_DANYCH.md`.

---

## 1. Zasady wspólne dla obu baz

**Format pliku.** `.csv` (kodowanie **UTF-8**; w Excelu „CSV UTF-8”) albo
`.xlsx`/`.xlsm`. Przy CSV separator kolumn wykrywamy sami — przecinek,
średnik i tabulator działają tak samo. W XLSX czytamy **pierwszy arkusz**.

**Nagłówek.** Pierwszy wiersz to nazwy kolumn. **Kolejność kolumn jest
dowolna.** Wielkość liter, polskie znaki, spacje i myślniki w nagłówku nie
mają znaczenia: `Mięśnie główne`, `MIESNIE GLOWNE` i `miesnie_glowne` to ta
sama kolumna. Kolumn spoza listy nie czytamy — ich nazwy trafiają do
raportu, żeby literówka w nagłówku była widoczna, a nie cicha.

**Limity.** Do **2000 wierszy** danych i **5 MB** na plik. Większą bazę
podziel na części — nadmiar jest raportowany, nigdy cicho ucinany.

**Puste komórki.** Pusta komórka znaczy „nie mam tej informacji”, a **nigdy
„usuń to, co jest w bazie”**. Żaden tryb importu nie kasuje danych pustą
komórką.

**Próba przed zapisem.** Każdy import ma dwa kroki: „Pokaż, co się zmieni”
(nic się nie zapisuje) i dopiero potem „Zaimportuj”. Raport podaje, ile
pozycji powstanie, ile się zmieni, ile jest bez zmian i **które wiersze
odpadły oraz dlaczego** (numer wiersza + nazwa kolumny).

**Brak zgadywania.** Wartość spoza słownika nie trafia do bazy w postaci
„najbliższej”: albo wiersz jest pomijany z podaniem przyczyny (kolumny
wymagane), albo pole zostaje puste, a wartość ląduje w raporcie.

**Idempotencja.** Wgranie tego samego pliku drugi raz kończy się zerem
utworzonych i zerem zmienionych pozycji.

**Izolacja.** Import zawsze idzie do bazy **zalogowanego trenera**. Bazy
różnych trenerów są rozłączne — nic nie „wycieka” między kontami.

**Droga w obie strony.** Przycisk „Pobierz to, co mam teraz” eksportuje bazę
w **dokładnie tym samym formacie**, który przyjmuje import. Masowa poprawka
to jeden cykl: pobierz → popraw w arkuszu → wgraj z powrotem.

---

## 2. Baza ćwiczeń

Jeden wiersz = jedno ćwiczenie.

Endpointy: `POST /api/coach/exercises/import-file?dry_run=&mode=`,
`GET /api/coach/exercises/import-example` (wzór),
`GET /api/coach/exercises/export-file` (eksport),
`GET /api/coach/exercises/import-schema` (kontrakt w JSON).

### 2.1. Kolumny

| kolumna | wymagana | co wpisać | przykład | inne akceptowane nagłówki |
|---|---|---|---|---|
| `nazwa` | **tak** | Nazwa ćwiczenia | Wyciskanie sztangi na ławce płaskiej | `name`, `cwiczenie` |
| `grupa` | **tak** | Grupa mięśniowa (słownik) | KLATKA | `kategoria`, `muscle_group` |
| `opis` | **tak** | Opis wykonania (technika) | Połóż się na ławce, chwyt nieco szerszy niż barki... | `how_to`, `wykonanie`, `technika` |
| `nazwa_en` | nie | Nazwa angielska | Barbell bench press | `name_en`, `nazwa_ang` |
| `efekt` | nie | Co daje to ćwiczenie | Siła i masa klatki piersiowej | `benefit`, `korzysc` |
| `sprzet` | nie | Potrzebny sprzęt | sztanga, ławka płaska | `equipment`, `wyposazenie` |
| `poziom` | nie | Poziom trudności (słownik) | SREDNIOZAAWANSOWANY | `level`, `trudnosc` |
| `wzorzec` | nie | Wzorzec ruchu (słownik) | WYPYCHANIE_POZIOME | `pattern`, `wzorzec_ruchu` |
| `miesnie_glowne` | nie | Mięśnie główne (słownik, po przecinku) | KLATKA_PIERSIOWA | `muscles_primary`, `miesnie_pierwszorzedowe` |
| `miesnie_pomocnicze` | nie | Mięśnie pomocnicze (słownik, po przecinku) | TRICEPS,BARK_PRZEDNI | `muscles_secondary`, `miesnie_wspomagajace` |
| `kroki` | nie | Kroki techniki, rozdzielone „\|” | Ustaw łopatki\|Opuść sztangę do klatki\|Wypchnij | `steps`, `kroki_techniki` |
| `bledy` | nie | Najczęstsze błędy, rozdzielone „\|” | Odbijanie od klatki\|Uniesione barki | `mistakes`, `bledy_techniczne` |
| `wskazowki` | nie | Wskazówki trenerskie, rozdzielone „\|” | Wbij stopy w podłogę\|Łokcie pod kątem 45° | `cues`, `cue` |
| `bezpieczenstwo` | nie | Uwagi bezpieczeństwa | Przy bólu barku przerwij i skonsultuj się ze specjalistą. | `safety`, `uwagi_bezpieczenstwa` |
| `latwiej` | nie | Wersja łatwiejsza | Wyciskanie hantlami | `easier`, `regresja` |
| `trudniej` | nie | Wersja trudniejsza | Wyciskanie z pauzą | `harder`, `progresja` |
| `tempo` | nie | Sugerowane tempo | 3-1-1-0 | `tempo_hint`, `tempo_ruchu` |
| `oddech` | nie | Sposób oddychania | Wdech przy opuszczaniu, wydech przy wypychaniu | `breathing` |
| `tagi` | nie | Etykiety, rozdzielone „\|” | wielostawowe\|siłowe | `tags`, `etykiety` |
| `wideo_url` | nie | Link do nagrania | https://... | `video_url`, `wideo`, `film` |
| `zrodlo` | nie | Skąd pochodzi pozycja (proweniencja) | Biblioteka własna, 2026-08 | `source_ref`, `source` |

### 2.2. Listy w jednej komórce

Kolumny `kroki`, `bledy`, `wskazowki` i `tagi` mieszczą listę — elementy
rozdzielamy **pionową kreską** `|`:

```
Ustaw łopatki|Opuść sztangę do klatki|Wypchnij nad sobą
```

Pionowa kreska, bo przecinek i średnik są już zajęte przez sam format CSV.

Kolumny `miesnie_glowne` i `miesnie_pomocnicze` rozdzielamy **przecinkiem**
(nazwy partii przecinka nie zawierają):

```
KLATKA_PIERSIOWA,TRICEPS,BARK_PRZEDNI
```

### 2.3. Co się dzieje z ćwiczeniem, które już mam

Dopasowanie idzie po nazwie (bez wielkości liter, bez polskich znaków, bez
nadmiarowych spacji) i obejmuje też pozycje **zarchiwizowane** — inaczej
import robiłby duplikat czegoś, co świadomie schowałeś.

* **Tryb „Uzupełnij puste pola”** (`mode=UZUPELNIJ`, domyślny) — wypełnia
  wyłącznie te pola, które w bazie są **puste**. Twój opis techniki napisany
  pod konkretne ćwiczenie **nie zostanie nadpisany**.
* **Tryb „Zastąp danymi z pliku”** (`mode=ZASTAP`) — nadpisuje także pola
  wypełnione, ale **tylko wartościami niepustymi** z pliku.

Nowe pozycje dostają proweniencję: `source_kind = IMPORTED` i `source_ref` =
nazwa pliku (albo wartość z kolumny `zrodlo`, jeśli ją podasz). Istniejące
pozycje **nie** dostają nazwy pliku — nie pochodzą z niego.

### 2.4. Kiedy wiersz odpada

* brak `nazwa`, albo nazwa dłuższa niż 300 znaków,
* nazwa powtórzona w tym samym pliku (druga i kolejne),
* `grupa` spoza słownika,
* **nowe** ćwiczenie bez `grupa` albo bez `opis`.

Wiersz, który odpadł, nie zatrzymuje importu — reszta pliku wchodzi dalej.
Nierozpoznany `poziom` lub `wzorzec` **nie** odrzuca wiersza: pole zostaje
puste, a wartość trafia do ostrzeżeń.

---

## 3. Szablony treningowe

Jeden wiersz = **jedno ćwiczenie w jednym dniu jednego szablonu**. Wiersze
grupuje kolumna `szablon`; w obrębie szablonu grupuje je `dzien`.

Endpointy: `POST /api/coach/plan-templates/import-file?dry_run=`,
`GET /api/coach/plan-templates/import-example`,
`GET /api/coach/plan-templates/export-file`,
`GET /api/coach/plan-templates/import-schema`.

### 3.1. Kolumny

| kolumna | wymagana | co wpisać | przykład | inne akceptowane nagłówki |
|---|---|---|---|---|
| `szablon` | **tak** | Nazwa szablonu (grupuje wiersze) | FBW 3x w tygodniu | `template`, `plan`, `nazwa_szablonu` |
| `dzien` | **tak** | Nazwa dnia treningowego | Dzień A — całe ciało | `day`, `trening`, `nazwa_dnia` |
| `cwiczenie` | **tak** | Nazwa ćwiczenia | Przysiad ze sztangą z tyłu | `exercise`, `nazwa` |
| `dzien_nr` | nie | Kolejność dnia w szablonie (liczba) | 1 | `day_no`, `nr_dnia`, `kolejnosc_dnia` |
| `dzien_tygodnia` | nie | Dzień tygodnia 1–7 (1 = poniedziałek) | 1 | `weekday`, `dzien_tyg` |
| `pozycja` | nie | Kolejność ćwiczenia w dniu (liczba) | 1 | `order`, `lp`, `nr` |
| `serie` | nie | Liczba serii (tekst — dopuszczalne „3–4”) | 4 | `sets` |
| `powtorzenia` | nie | Powtórzenia (tekst — dopuszczalne „8–10”) | 8-10 | `reps`, `powt` |
| `ciezar` | nie | Obciążenie (tekst — dopuszczalne „RPE 8”, „bw”) | RPE 8 | `weight`, `obciazenie` |
| `tempo` | nie | Tempo ruchu | 3-1-1-0 | `tempo_ruchu` |
| `przerwa` | nie | Przerwa między seriami | 120 s | `rest`, `odpoczynek` |
| `komentarz` | nie | Uwaga trenera do pozycji | Ostatnia seria do 2 powtórzeń zapasu | `comment`, `uwagi`, `notatka` |
| `wideo_url` | nie | Link do nagrania dla tej pozycji | https://... | `video_url`, `wideo`, `film` |

### 3.2. Kolejność

Dni układamy według `dzien_nr`, a pozycje w dniu według `pozycja`. Jeśli tych
kolumn nie ma — obowiązuje kolejność wierszy w pliku. Limity: **14 dni** na
szablon, **40 pozycji** na dzień.

### 3.3. Powiązanie z bazą ćwiczeń

Nazwę z kolumny `cwiczenie` dopasowujemy do Twojej **aktywnej** bazy ćwiczeń
i zapisujemy miękkie odniesienie do karty ćwiczenia (`exercise_id`) — ten sam
kontrakt, co przy ręcznym układaniu planu. **Brak dopasowania nie jest
błędem**: pozycja wchodzi do szablonu z samą nazwą, a jej nazwa trafia do
raportu, żebyś wiedział, co warto dodać do bazy.

Wniosek praktyczny: **najpierw importuj ćwiczenia, potem szablony** — wtedy
pozycje od razu mają karty.

### 3.4. Co się dzieje z szablonem, który już mam

Szablon o tej samej nazwie **nie jest nadpisywany**. Dostaje **nową wersję** z
powodem wskazującym plik źródłowy; poprzednie wersje zostają w historii
(zasada z konstytucji Human OS: brak cichego nadpisywania). Szablon o
**identycznej treści** nie dostaje pustej wersji „bo import”.

Szablony nie są przypisane do żadnego klienta, więc import nie dotyka planów
prowadzonych osób i nie wymaga ich zgód. Przypisanie do klienta to osobna,
świadoma czynność (kopiowanie szablonu do klienta).

### 3.5. Kiedy wiersz odpada

* brak `szablon`, `dzien` albo `cwiczenie`,
* przekroczony limit dni lub pozycji w dniu.

Zbyt długie wartości pól opisowych (`komentarz` itd.) nie odrzucają wiersza —
są przycinane do limitu, z ostrzeżeniem w raporcie.

---

## 4. Słowniki (wartości zamknięte)

W kolumnach słownikowych przyjmujemy **klucz** albo **polską etykietę** —
wielkość liter i polskie znaki nie mają znaczenia. Nic poza tym: „łatwe” nie
zostanie zamienione na „POCZATKUJACY”.

### 4.1. `grupa` — zgrubna grupa mięśniowa

`NOGI`, `PLECY`, `KLATKA`, `BARKI`, `RECE`, `BRZUCH`, `CALE_CIALO`, `MOBILNOSC`, `CARDIO`, `INNE`

### 4.2. `poziom`

`POCZATKUJACY` (początkujący), `SREDNIOZAAWANSOWANY` (średniozaawansowany), `ZAAWANSOWANY` (zaawansowany)

### 4.3. `wzorzec` — wzorzec ruchu

`PRZYSIAD` (przysiad), `ZAWIAS_BIODROWY` (zawias biodrowy), `WYPYCHANIE_POZIOME` (wypychanie poziome), `WYPYCHANIE_PIONOWE` (wypychanie pionowe), `PRZYCIAGANIE_POZIOME` (przyciąganie poziome), `PRZYCIAGANIE_PIONOWE` (przyciąganie pionowe), `WYKROK` (wykrok), `NOSZENIE` (noszenie), `ROTACJA` (rotacja), `ANTYROTACJA` (antyrotacja), `IZOLACJA` (izolacja), `CARDIO` (cardio), `MOBILNOSC` (mobilność)

### 4.4. `miesnie_glowne` / `miesnie_pomocnicze`

To ten sam słownik, z którego korzysta rysunek pracujących mięśni na karcie
ćwiczenia.

`KLATKA_PIERSIOWA` (klatka piersiowa), `NAJSZERSZY_GRZBIETU` (najszerszy grzbietu), `CZWOROBOCZNY` (czworoboczny), `ROMBOIDALNE` (romboidalne), `PROSTOWNIKI_GRZBIETU` (prostowniki grzbietu), `BARK_PRZEDNI` (bark przedni), `BARK_BOCZNY` (bark boczny), `BARK_TYLNY` (bark tylny), `BICEPS` (biceps), `TRICEPS` (triceps), `PRZEDRAMIE` (przedramię), `BRZUCH_PROSTY` (brzuch prosty), `BRZUCH_SKOSNY` (brzuch skośny), `MIESNIE_GLEBOKIE` (mięśnie głębokie), `POSLADKI` (pośladki), `CZWOROGLOWY_UDA` (czworogłowy uda), `DWUGLOWY_UDA` (dwugłowy uda), `PRZYWODZICIELE` (przywodziciele), `ODWODZICIELE` (odwodziciele), `LYDKA` (łydka), `ZGINACZE_BIODRA` (zginacze biodra)

Poza kluczami i etykietami rozpoznajemy też formy anatomiczne, które zna
parser opisów („mięsień piersiowy większy”, „przednia część mięśnia
naramiennego”). **Nazwy zbiorcze są odrzucane, nie zgadywane**: „góra ciała”,
„nogi” czy „core” trafiają do raportu jako nierozpoznane, a pole zostaje
puste. Ta sama partia w obu listach naraz nie ma sensu — pierwszeństwo ma
lista mięśni głównych.

---

## 5. Najkrótsza droga do sprawdzenia pliku

1. W panelu trenera: **Baza wiedzy → Ćwiczenia → Importuj bazę ćwiczeń z
   pliku** (szablony: **Szablony planów → Importuj szablony z pliku**).
2. **Pobierz wzór pliku** — nagłówek jest wtedy na pewno poprawny.
3. Wgraj plik i kliknij **„Pokaż, co się zmieni”**. Nic się jeszcze nie
   zapisuje.
4. Przeczytaj raport: liczby, nieznane kolumny, nierozpoznane wartości,
   wiersze, które odpadły.
5. Dopiero **„Zaimportuj do mojej bazy”** zapisuje.

Jeśli raport pokazuje same błędy — plik jest w złym formacie albo w złym
kodowaniu; zapisz go z arkusza ponownie jako „CSV UTF-8” lub `.xlsx`.

---

## 6. Ślad w audycie

Zapis (nie próba) zostawia zdarzenie w łańcuchu audytu:
`EXERCISES_IMPORTED` / `PLAN_TEMPLATES_IMPORTED` oraz `EXERCISES_EXPORTED` /
`PLAN_TEMPLATES_EXPORTED` przy eksporcie. Payload zawiera wyłącznie nazwę
pliku, tryb i liczby — nigdy treści wierszy i nigdy danych klienta.

## 7. Wycofanie

Import nie zmienia schematu bazy (żadnej migracji), więc nie ma czego
cofać na poziomie struktury. Skutki danych cofa się normalnymi narzędziami
panelu: ćwiczenie archiwizuje się (nie kasuje), a szablon wraca do
poprzedniej wersji przez historię wersji — obie ścieżki zostawiają ślad w
audycie.

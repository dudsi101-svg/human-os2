# Jak przygotować plik z bazą danych do Dzik OS

Instrukcja dla osoby, która przygotowuje dane. Nie trzeba nic wiedzieć
o aplikacji — wystarczy arkusz kalkulacyjny (Excel, Arkusze Google,
LibreOffice).

Są dwa osobne pliki: **ćwiczenia** i **szablony treningowe**. Można zrobić
tylko jeden z nich.

---

## Zasady wspólne (dotyczą obu plików)

1. **Jeden arkusz, jedna tabela.** Dane zaczynają się od pierwszego wiersza
   — bez tytułów, logo i pustych wierszy nad tabelą.
2. **Pierwszy wiersz to nazwy kolumn.** Kolejność kolumn jest dowolna.
   Można pominąć kolumny nieobowiązkowe.
3. **Nazwy kolumn można pisać naturalnie.** `Mięśnie główne`, `MIESNIE
   GLOWNE` i `miesnie_glowne` to dla aplikacji to samo. Wielkość liter,
   polskie znaki, spacje i myślniki nie mają znaczenia.
4. **Kolumny, których nie ma na liście, są pomijane** — nie psują pliku, ale
   ich zawartość nie trafi do aplikacji. Aplikacja wypisze ich nazwy, żeby
   było widać literówkę w nagłówku.
5. **Format zapisu:** `.xlsx` (zwykły plik Excela) albo `.csv` **w kodowaniu
   UTF-8** (w Excelu: „Zapisz jako → CSV UTF-8"). Zły format kodowania to
   najczęstsza przyczyna krzaków zamiast polskich znaków.
6. **Limity:** do 2000 wierszy i 5 MB na plik. Większą bazę dzielimy na
   części.
7. **Pusta komórka jest w porządku** i znaczy „nie mam tej informacji".
   Nigdy nie kasuje tego, co już jest w aplikacji. Nie trzeba wpisywać
   „brak", „-" ani „nie dotyczy" — lepiej zostawić puste.
8. **Nie wymyślamy wartości słownikowych.** Jeśli czegoś nie wiadomo,
   zostawiamy puste. Aplikacja nie zgadnie i nie podstawi „czegoś
   podobnego" — wypisze, czego nie rozpoznała.

---

## PLIK 1 — Ćwiczenia

Jeden wiersz = jedno ćwiczenie.

### Kolumny obowiązkowe

| Kolumna | Co wpisać |
|---|---|
| `nazwa` | Nazwa ćwiczenia, np. `Wyciskanie sztangi na ławce płaskiej`. Musi być niepowtarzalna w pliku. |
| `grupa` | Jedna wartość z listy: `NOGI`, `PLECY`, `KLATKA`, `BARKI`, `RECE`, `BRZUCH`, `CALE_CIALO`, `MOBILNOSC`, `CARDIO`, `INNE` |
| `opis` | Opis wykonania własnymi słowami — co robi ćwiczący. |

Wiersz bez którejś z tych trzech rzeczy nie zostanie zaimportowany
(aplikacja poda numer wiersza i przyczynę).

### Kolumny nieobowiązkowe

| Kolumna | Co wpisać |
|---|---|
| `nazwa_en` | Nazwa angielska, np. `Barbell bench press`. Pomaga w wyszukiwaniu. |
| `efekt` | Po co się to robi, np. `Siła i masa klatki piersiowej`. |
| `sprzet` | Czego potrzeba, np. `sztanga, ławka płaska`. |
| `poziom` | `POCZATKUJACY`, `SREDNIOZAAWANSOWANY` albo `ZAAWANSOWANY` |
| `wzorzec` | Wzorzec ruchu — lista niżej |
| `miesnie_glowne` | Partie, które pracują najmocniej — lista niżej, **po przecinku** |
| `miesnie_pomocnicze` | Partie wspomagające — ta sama lista, po przecinku |
| `kroki` | Technika krok po kroku, **rozdzielona pionową kreską `|`** |
| `bledy` | Najczęstsze błędy, też przez `|` |
| `wskazowki` | Wskazówki trenerskie, też przez `|` |
| `bezpieczenstwo` | Na co uważać, kiedy przerwać |
| `latwiej` | Wersja łatwiejsza, np. `Wyciskanie hantlami` |
| `trudniej` | Wersja trudniejsza, np. `Wyciskanie z pauzą` |
| `tempo` | Sugerowane tempo, np. `3-1-1-0` |
| `oddech` | Sposób oddychania |
| `tagi` | Etykiety przez `|`, np. `wielostawowe\|siłowe` |
| `wideo_url` | Link do nagrania |
| `zrodlo` | Skąd pochodzi pozycja, np. `Biblioteka własna 2026` |

### Przykład (trzy pierwsze kolumny + kilka opcjonalnych)

| nazwa | grupa | opis | poziom | wzorzec | miesnie_glowne | kroki |
|---|---|---|---|---|---|---|
| Wyciskanie sztangi na ławce płaskiej | KLATKA | Wyciskanie sztangi leżąc | SREDNIOZAAWANSOWANY | WYPYCHANIE_POZIOME | KLATKA_PIERSIOWA | Ustaw łopatki\|Opuść sztangę\|Wypchnij |
| Martwy ciąg klasyczny | NOGI | Podniesienie sztangi z podłogi | ZAAWANSOWANY | ZAWIAS_BIODROWY | DWUGLOWY_UDA, POSLADKI | Chwyć sztangę\|Wyprostuj biodra |
| Podciąganie nachwytem | PLECY | Podciąganie na drążku | ZAAWANSOWANY | PRZYCIAGANIE_PIONOWE | NAJSZERSZY_GRZBIETU | Zawiśnij\|Podciągnij brodę nad drążek |

---

## PLIK 2 — Szablony treningowe

Jeden wiersz = **jedno ćwiczenie, w jednym dniu, w jednym szablonie**.
Szablon o trzech dniach po pięć ćwiczeń to 15 wierszy.

### Kolumny obowiązkowe

| Kolumna | Co wpisać |
|---|---|
| `szablon` | Nazwa szablonu, np. `FBW 3x w tygodniu`. Powtarza się w każdym wierszu tego szablonu — to ona wiersze grupuje. |
| `dzien` | Nazwa dnia, np. `Dzień A — całe ciało`. Powtarza się w każdym wierszu tego dnia. |
| `cwiczenie` | Nazwa ćwiczenia. |

### Kolumny nieobowiązkowe

| Kolumna | Co wpisać |
|---|---|
| `dzien_nr` | Kolejność dnia: `1`, `2`, `3`… |
| `dzien_tygodnia` | `1`–`7`, gdzie `1` = poniedziałek |
| `pozycja` | Kolejność ćwiczenia w dniu: `1`, `2`, `3`… |
| `serie` | Może być tekst: `4` albo `3-4` |
| `powtorzenia` | Może być tekst: `8-10`, `do upadku` |
| `ciezar` | Może być tekst: `60 kg`, `RPE 8`, `masa ciała` |
| `tempo` | np. `3-1-1-0` |
| `przerwa` | np. `120 s` |
| `komentarz` | Uwaga do tej pozycji |
| `wideo_url` | Link do nagrania dla tej pozycji |

Jeśli nie ma `dzien_nr` i `pozycja`, obowiązuje **kolejność wierszy w
pliku** — wtedy trzeba je po prostu ustawić w dobrej kolejności.

### Przykład

| szablon | dzien | dzien_nr | pozycja | cwiczenie | serie | powtorzenia | przerwa |
|---|---|---|---|---|---|---|---|
| FBW 3x w tygodniu | Dzień A | 1 | 1 | Przysiad ze sztangą z tyłu | 4 | 6-8 | 150 s |
| FBW 3x w tygodniu | Dzień A | 1 | 2 | Wyciskanie sztangi na ławce płaskiej | 4 | 8-10 | 120 s |
| FBW 3x w tygodniu | Dzień B | 2 | 1 | Martwy ciąg klasyczny | 3 | 5 | 180 s |

### Ważne przy szablonach

Nazwy z kolumny `cwiczenie` aplikacja **dopasuje do bazy ćwiczeń** i podepnie
kartę ćwiczenia (technika, błędy, rysunek mięśni). Dlatego:

* **najpierw wgrywamy plik z ćwiczeniami, potem plik z szablonami**;
* nazwy w obu plikach powinny brzmieć **tak samo** (wielkość liter i polskie
  znaki nie mają znaczenia, ale `Przysiad ze sztangą` i `Przysiady ze
  sztangą z tyłu` to dla aplikacji dwie różne rzeczy);
* ćwiczenie, którego nie ma w bazie, **i tak wejdzie do szablonu** — tylko
  bez karty. Aplikacja wypisze takie nazwy w raporcie.

---

## Listy wartości do skopiowania

### `wzorzec` — wzorzec ruchu

`PRZYSIAD`, `ZAWIAS_BIODROWY`, `WYPYCHANIE_POZIOME`, `WYPYCHANIE_PIONOWE`,
`PRZYCIAGANIE_POZIOME`, `PRZYCIAGANIE_PIONOWE`, `WYKROK`, `NOSZENIE`,
`ROTACJA`, `ANTYROTACJA`, `IZOLACJA`, `CARDIO`, `MOBILNOSC`

### `miesnie_glowne` / `miesnie_pomocnicze` — partie mięśniowe

`KLATKA_PIERSIOWA`, `NAJSZERSZY_GRZBIETU`, `CZWOROBOCZNY`, `ROMBOIDALNE`,
`PROSTOWNIKI_GRZBIETU`, `BARK_PRZEDNI`, `BARK_BOCZNY`, `BARK_TYLNY`,
`BICEPS`, `TRICEPS`, `PRZEDRAMIE`, `BRZUCH_PROSTY`, `BRZUCH_SKOSNY`,
`MIESNIE_GLEBOKIE`, `POSLADKI`, `CZWOROGLOWY_UDA`, `DWUGLOWY_UDA`,
`PRZYWODZICIELE`, `ODWODZICIELE`, `LYDKA`, `ZGINACZE_BIODRA`

**Można też pisać po polsku** — `klatka piersiowa`, `bark przedni`,
`czworogłowy uda` — aplikacja to rozumie. Rozpozna również nazwy anatomiczne
(`mięsień piersiowy większy`, `przednia część mięśnia naramiennego`).

**Czego NIE rozpozna:** nazw zbiorczych — `nogi`, `góra ciała`, `core`,
`plecy`. Takie wpisy zostaną wypisane w raporcie, a pole zostanie puste.
Lepiej wtedy wypisać konkretne partie albo zostawić kolumnę pustą.

---

## Zanim wyślesz plik — pięć rzeczy do sprawdzenia

1. Pierwszy wiersz to nazwy kolumn (nie tytuł tabeli).
2. Trzy obowiązkowe kolumny są wypełnione w **każdym** wierszu.
3. `grupa`, `poziom` i `wzorzec` mają wartości z list wyżej (albo są puste).
4. Nazwy ćwiczeń się nie powtarzają.
5. Plik jest zapisany jako `.xlsx` albo `.csv` **UTF-8**.

Nie trzeba być pewnym, że wszystko jest idealnie. W aplikacji import ma dwa
kroki: **„Pokaż, co się zmieni"** niczego nie zapisuje, tylko wypisuje raport
— co powstanie, co się zmieni, które wiersze odpadły i dlaczego (z numerem
wiersza i nazwą kolumny). Dopiero drugie kliknięcie zapisuje. Plik można
poprawiać i wgrywać dowolną liczbę razy — wgranie tego samego pliku drugi raz
nic nie zmienia.

W aplikacji jest też przycisk **„Pobierz wzór pliku"** — gotowy nagłówek
z jednym przykładowym wierszem. Najprościej zacząć od niego.

---

Specyfikacja techniczna tego samego formatu (dla programisty):
`docs/IMPORT_BAZ.md`.

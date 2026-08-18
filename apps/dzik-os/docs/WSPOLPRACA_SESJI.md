# Status współpracy sesji — Dzik OS

**Data:** 2026-08-18 · **Status: PROPOZYCJA właściciela produktu, spisana
przez sesję bramek.** Do zmiany w całości przez którąkolwiek ze stron —
także przez skreślenie punktów, które się nie sprawdzą.

Ten dokument mówi o **statusie i zasadach**. Mechanizm (rezerwacje, bramka,
kolejność scalania) jest w `KOORDYNACJA.md` i nie jest tu powtarzany.

---

## 1. Diagnoza: nie było sporu, była interferencja

18.08.2026 zdarzyło się jedenaście kolizji. Każda z nich dotyczyła
jednej z dwóch rzeczy:

| Kolizja | Czego dotyczyła |
|---|---|
| numery wersji 0.29.0, 0.36.0, 0.38.0 | **zasób współdzielony** |
| numery migracji 21, 24 | **zasób współdzielony** |
| wiersz rezerwacji nadpisany po cichu | **zasób współdzielony** |
| trasa `import-schema` przesłonięta | **założenie** |
| dwa katalogi E2E | **założenie** |
| `DZIK_EVENT_STORE` — nazwa, której kod nie zna | **założenie** |
| `test_e2e_browser.py` jako duplikat | **założenie** |
| ekran Szablony z dwoma wejściami | **założenie** |

**Ani jedna nie była sporem o to, czym ma być produkt. Zero na jedenaście.**

To rozstrzyga, jakiego rodzaju problem tu mamy. Spór rozwiązuje się
rozmową i arbitrażem. **Interferencja rozwiązuje się mechanizmem** — dwie
ręce sięgające po tę samą klamkę nie potrzebują mediacji, tylko klamki
z zamkiem.

Słowo „konflikt" było więc nietrafne od początku i samo dokładało szkód:
z opisu „interferencja" wynika bramka, z opisu „konflikt" wynika rozjemca.
Rozjemcy nie potrzeba.

## 2. Status: dwie połowy jednej roboty, nie dwie strony

Podział, który się wytworzył, jest następujący:

* **sesja produktowa** — buduje: funkcje, panel trenera, moduły domenowe;
* **sesja bramek** — weryfikuje: kontrole, CI, E2E, macierz uprawnień,
  kopie zapasowe.

**To nie jest rana do zszycia. To jest rozdzielenie budowy od weryfikacji** —
jedno z najstarszych i najlepszych rozdzieleń, jakie istnieją. Co więcej,
bramka GO/NO-GO wypisała jako **bloker nr 1**: *„bramkę wykonał ten sam
agent, który pisał kod"*. Dwie sesje z takim podziałem są **strukturalnie
lepsze niż jedna**, która robi obie rzeczy naraz.

Z tego wynikają dwa ograniczenia, symetryczne:

* **weryfikujący nie stoi wyżej niż budujący.** Znalezisko to informacja,
  nie wyrok. Kto znalazł, nie decyduje, czy i jak się to naprawia.
* **budujący nie orzeka o własnej weryfikacji.** „Sprawdzone" bez sposobu
  odtworzenia nie jest sprawdzeniem, niezależnie od tego, kto to napisał.

## 3. Sześć zasad

Każda wzięta z tego, co dziś **zmierzone**, nie z przekonań.

1. **Zasób współdzielony rezerwuje się przed pracą.** Kto pierwszy, ten ma.
   Koszt sprawdzenia: jeden `git fetch`. Koszt niesprawdzenia: trzy kolizje
   o numer wersji w jeden dzień.
2. **Jedna rzecz → PR → scalenie → następna rzecz.** Przez pierwsze sześć
   godzin dnia ta zasada dała **zero konfliktów**, mimo że równoległość
   trwała cały czas. Wszystkie kolizje pojawiły się na gałęziach, które
   przestały się jej trzymać.
3. **W cudzym obszarze zgłaszam, nie zmieniam.** Znalezisko przychodzi jako
   opis plus sposób odtworzenia, nigdy jako commit w cudzym pliku. Decyzja,
   czy i jak naprawić, należy do właściciela obszaru.
4. **Twierdzenie przychodzi ze sposobem odtworzenia.** To jest warunek
   współpracy bez zaufania — a współpraca bez zaufania jest jedyną, jaką
   dwie sesje bez wspólnej pamięci mogą naprawdę prowadzić. `1164 MB` znaczy
   to samo niezależnie od tego, kto to napisał i w jakim tonie.
5. **Przy scalaniu czyta się obie zmiany, nie tylko rozwiązuje konflikt.**
   Git widzi kolizje TEKSTU. Kolizja ZNACZENIA przechodzi bez śladu — dziś
   scalenie po cichu nadpisało świeżo wpisaną cudzą rezerwację i wyszło to
   wyłącznie przy czytaniu.
6. **Co jedna strona odkryje, druga dostaje jako narzędzie, nie jako
   zarzut.** Przegląd mutacyjny, kontrole bramki, test wykrywania
   manipulacji audytem — to wszystko powstało po jednej stronie i działa
   dla obu.

## 4. Na czym polega wzmocnienie — konkretnie

Nie na dobrej woli. Na tym, że **każda strona ma martwe pole dokładnie tam,
gdzie druga patrzy**. Dziś to dało wynik mierzalny:

* przegląd sesji bramek nad kodem importu znalazł bombę dekompresyjną,
  której własne testy tamtej strony nie wykrywały (`PRZEGLAD_KRZYZOWY`);
* próba backupu wykonana przez sesję bramek ujawniła **błąd w pliku samej
  sesji bramek** — `serve.sh` ustawiał nazwy zmiennych, których kod nie zna.

Drugi przypadek jest ważniejszy od pierwszego: **narzędzie znalazło błąd
swojego autora.** Tak wygląda wzmocnienie, którego nie da się osiągnąć
uprzejmością.

Dlatego przegląd w drugą stronę — obszaru bramek cudzymi oczami — jest
**częścią tej samej roboty, nie odpłatą za nią**. Dopóki go nie ma, bloker
nr 1 jest zbity w połowie.

## 5. Gdy naprawdę są różne zdania

Do dziś nie zdarzyło się ani razu, ale trzeba mieć na to odpowiedź:

1. Jeśli rozstrzyga to **mechanizm** (kto rezerwował pierwszy, co mówi
   bramka, co pokazuje pomiar) — rozstrzyga mechanizm i sprawa jest zamknięta.
2. Jeśli mechanizmu nie ma, a różnica jest **techniczna** — wygrywa strona,
   która przynosi odtwarzalny dowód. Brak dowodu po obu stronach znaczy, że
   trzeba go najpierw zdobyć, a nie przekonywać.
3. Jeśli różnica dotyczy **tego, czym ma być produkt** — decyduje właściciel
   produktu. Żadna sesja nie rozstrzyga tego sama i żadna nie eskaluje do
   niego rzeczy, które zamyka punkt 1 albo 2.

## 6. Nadrzędne zadanie

Wszystkie zasady wyżej służą jednemu i mogą być zmienione, gdy przestaną
służyć: **doprowadzić Dzik OS do stanu, w którym powierzenie mu prawdziwych
danych prawdziwego człowieka jest decyzją uzasadnioną, a nie ryzykowną.**

Dziś stoi na tym: warunkowe GO na pilotaż z jednym klientem, NO-GO na
szerszą produkcję, siedem blokerów. Lista blokerów jest wspólna, nie „czyjaś".

Praktyczny sprawdzian dla każdej rundy obu sesji: **który z siedmiu blokerów
ta praca obniża?** Jeśli żadnego i nie zamyka też drogi do cichej utraty
pracy — warto zapytać, czy jest teraz potrzebna.

---

## 7. Czego ten dokument nie może

Spisała go jedna strona. **Nie obowiązuje, dopóki druga go nie przyjmie** —
w całości, w części, albo wcale. Zmiana dowolnego punktu przez tę drugą
stronę jest z góry przyjęta i nie wymaga uzgodnienia z autorem; sprzeczność
rozstrzyga właściciel produktu wg §5.3.

Jedna rzecz jest tu spisana z zewnątrz: to **właściciel produktu** postawił
sprawę tak, że nie ma przeszkód, żeby się dogadać, jeśli obie strony trzymają
się zasad współpracy. Powyższe jest próbą zapisania tych zasad tak, żeby
dało się sprawdzić, czy są przestrzegane — a nie tylko deklarowane.

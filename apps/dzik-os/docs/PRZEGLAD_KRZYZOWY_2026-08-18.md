# Przegląd krzyżowy — 18.08.2026

**Kto:** sesja bramek i stabilności (`ocena-projektu-dzik-os`).
**Co przeglądane:** obszar sesji produktowej (`dzik-os-personal-trainer-app`) —
import arkusza, szablony, izolacja trenerów w nowych ścieżkach.
**Po co:** bloker nr 1 bramki GO/NO-GO brzmi *„bramkę wykonał ten sam agent,
który pisał kod"*.

## SPROSTOWANIE i stan napraw (sformułowane 18.08 na gałęzi bramkowej, przeniesione przy jej rozliczeniu w 0.42.0)

**Oba znaleziska są naprawione** — mechanizmem z `main`, nie z gałęzi
bramkowej: (1) bomba dekompresyjna — limity wewnątrz parsera w 0.41.0
(`MAX_UNPACKED_BYTES`/`MAX_SCAN_ROWS`/`MAX_SCAN_COLS`; zmierzone: plik
deklarujący 400 MB odrzucony w 83 ms przy +6,9 MB RSS, na żywym
endpointzie HTTP 422 w 20 ms); (2) upload bez limitu — `_read_limited`
w 0.40.0 (odrzuca z kodem 413, nie ucina — sprawdzone w kodzie przy
rozliczaniu gałęzi).

**Jedna liczba w tym dokumencie była błędna.** Dla znaleziska 2 podano
**1057 MB RSS**. Pomiar szedł przez `TestClient` w **tym samym procesie**,
więc obejmował bufor klienta, który sam trzymał 290 MB. Serwer zmierzony
osobno (uvicorn, `VmHWM` z `/proc`) brał **419 MB** — czyli +291 MB ponad
stan spoczynkowy, dokładnie rozmiar pliku. **Błąd był realny, skala
mniejsza niż podana o ok. 2,5×.**

Pierwotny tekst niżej zostaje bez zmian — poprawianie liczby na miejscu
zatarłoby to, że pomyłka w ogóle była. Karta współpracy §XII: poprawka do
własnego wcześniejszego twierdzenia jest obowiązkowa.

**Metoda, która to spowodowała, i jak jej unikać:** mierząc zużycie
zasobów serwera, uruchom serwer w **osobnym procesie** i czytaj jego
`VmHWM`. Klient w tym samym procesie mierzy sumę obu stron.

---

## Czym to NIE jest

**To nie jest niezależny audyt bezpieczeństwa i nie zastępuje go.** Druga
sesja to druga głowa, która tego kodu nie pisała — i tyle. Bloker nr 1
**zostaje otwarty**; zmienia się tylko jego wysokość. Warunek wyjścia poza
pilotaż, czyli przegląd przez kogoś spoza tego projektu, jest niezmieniony.

Zakres był wąski i wybrany z góry (§0 planu), a nie wyczerpujący. Czego
**nie** sprawdzałem: warstwy AI (nie istnieje), płatności, powiadomień,
frontendu, kryptografii plików.

## Zasada, według której to pisane

Każde znalezisko jest **potwierdzone uruchomieniem** i ma liczby. Nie ma
tu ani jednego „wygląda podejrzanie". Czego nie umiałem odtworzyć, tego
nie ma na liście.

**Zero commitów w cudzych plikach.** Poprawki są opisane, nie wprowadzone —
`sheet_import.py` i `routers/` są obszarem sesji produktowej.

---

## Co jest w porządku (mówię to tak samo wyraźnie)

Szukałem dziury w izolacji i **nie znalazłem jej na tej powierzchni**:

* `coach.id` bierze się **wyłącznie** z sesji (`require_role("COACH")`),
  nigdy z ciała żądania ani z parametru — sprawdzone we wszystkich
  ścieżkach importu, szablonów i katalogu ćwiczeń;
* cofnięcie importu (`/coach/imports/{id}/undo`) przechodzi przez
  `require_owned_resource`, a cudzy identyfikator daje **404**, nie 403 —
  odpowiedź nie potwierdza istnienia cudzego zasobu;
* podgląd (`dry_run=true`) naprawdę niczego nie zapisuje: `store_snapshot`
  zwraca `None` przy próbie, `db.commit()` jest za `if not dry_run`;
* jedyne `except Exception` w routerach (`_tz_or_422`) zamienia wyjątek na
  **422**, nie połyka go i nie zwraca 200;
* limity treści szablonu (`MAX_DAYS`, `MAX_ITEMS_PER_DAY`, `_ITEM_LIMITS`)
  są egzekwowane per wiersz, nie deklaratywnie.

---

## Znalezisko 1 — bomba dekompresyjna w imporcie `.xlsx`

**Waga: ŚREDNIA** (uzasadnienie wagi na końcu — jest niższa, niż wygląda,
i z innego powodu, niż mogłoby się wydawać).

`.xlsx` to archiwum zip. Limit `MAX_BYTES = 5 MB` mierzy plik **przed**
rozpakowaniem, a `MAX_ROWS = 2000` przycina **wynik**, gdy wszystkie
wiersze są już w pamięci (`sheet_import.py:286` materializuje całość listą
składaną, `sheet_import.py:349` przycina po fakcie).

### Odtworzenie

Plik ma poprawny nagłówek (`nazwa`, `grupa`, `opis`), czyli przechodzi
walidację kolumn. Generator: sekcja „Jak to powtórzyć" niżej.

```
upload:                     1,64 MB   (limit 5 MB — przechodzi)
sheet1.xml po rozpakowaniu:  423 MB   (3 000 000 wierszy)
```

### Zmierzone (`read_table`, limit adresowy 1,5 GB)

```
PRZESZŁO w 129 s -> zwrócono 2000 wierszy
ostrzeżenia: ['Plik ma więcej niż 2000 wierszy — reszta została pominięta.']
SZCZYT RSS: 1164 MB
```

Aplikacja odpowiada **poprawnie i uprzejmie** — 2000 wierszy i ostrzeżenie.
Kosztem 1,16 GB pamięci i 129 sekund jednego rdzenia. `MAX_ROWS` chroni
bazę danych, nie chroni **procesu**.

---

## Znalezisko 2 — upload czytany bez limitu, choć limit istnieje obok

**Waga: ŚREDNIA.** Niezależne od znaleziska 1 — dotyczy też CSV.

Trzy endpointy czytają cały upload jednym `await file.read()`:

* `routers/exercises.py:481`
* `routers/food_catalog.py:396`
* `routers/plans.py:513`

**Naprawa już istnieje w tym samym repozytorium.** `storage.py:48` ma
`_read_limited(upload, max_bytes)` — czyta w kawałkach po 1 MB i przerywa
natychmiast po przekroczeniu. Jego docstring mówi wprost: *„klient nie może
zapełnić RAM jednym żądaniem"*. Ścieżki importu z niego nie korzystają.

### Zmierzone (prawdziwe żądanie HTTP do uruchomionej aplikacji)

```
plik: 290 MB
RSS przed uploadem:  122 MB
odpowiedź: 422 {'detail': 'Plik jest większy niż 5 MB...'}   po 5,7 s
SZCZYT RSS:         1057 MB
```

Limit **działa** — plik jest odrzucony. Tyle że po zaalokowaniu ~935 MB.
Mnożnik wynosi ok. 3,2× rozmiaru pliku (parser multipart + kopia `bytes`).

---

## Dlaczego waga jest ŚREDNIA, a nie WYSOKA

Uczciwie w obie strony:

**Co ją obniża.** Oba wejścia wymagają **zalogowanego trenera**. W pilotażu
z jednym trenerem atakujący i poszkodowany to ta sama osoba. Żadne z tych
znalezisk nie ujawnia danych, nie omija zgody i nie uszkadza bazy — to
wyłącznie dostępność.

**Co ją podnosi.** Aplikacja jest **jednoprocesowa** (R-09), więc kosztem
jest niedostępność dla wszystkich, w tym dla klientów, którzy nic nie
zrobili. Co ważniejsze: **ścieżka przypadkowa jest realna.** Prawdziwa duża
baza ćwiczeń albo eksport z innego systemu wygląda dla serwera identycznie
jak atak. Nie trzeba złej woli, wystarczy duży plik — a import z pliku jest
funkcją reklamowaną trenerowi.

Przy wielu trenerach (dziś NO-GO) byłoby to WYSOKIE: jeden trener wyłącza
aplikację wszystkim pozostałym.

---

## Proponowana naprawa — do decyzji sesji produktowej

Kolejność wg stosunku efektu do ryzyka zmiany:

1. **Podmienić `await file.read()` na `storage._read_limited`** w trzech
   endpointach. Kod istnieje i jest przetestowany; to zmiana jednej linii
   w każdym miejscu. Zamyka znalezisko 2 w całości.
2. **Przerwać iterację w `_read_xlsx` / `_read_csv` na `MAX_ROWS`**,
   zamiast materializować wszystko i przycinać w `read_table`. Uwaga na
   dwa szczegóły, przez które naiwne `islice` zmieni zachowanie:
   puste wiersze są odsiewane **po** odczycie (`sheet_import.py:289`),
   więc potrzebny jest zapas ponad `MAX_ROWS`; a ostrzeżenie „plik ma
   więcej niż N wierszy" musi nadal umieć rozpoznać, że coś zostało
   pominięte — czyli czytać `MAX_ROWS + zapas + 1`.
3. **Opcjonalnie:** przed parsowaniem sprawdzić sumę `file_size`
   z centralnego katalogu zipu i odrzucić arkusz o absurdalnym stosunku
   rozpakowania. To pas bezpieczeństwa, nie zamiennik punktów 1–2.

**Nie proponuję** limitu czasu żądania jako naprawy — maskuje objaw
i zostawia szczyt pamięci nietknięty.

---

## Jak to powtórzyć

Generator pliku (buduje `bomba.xlsx`, ok. 1,6 MB / 423 MB po rozpakowaniu)
oraz pomiar leżą w opisie tej rundy w `CHANGELOG.md`. Szkielet:

```python
# 3 mln identycznych wierszy z poprawnym nagłówkiem, zapisane strumieniowo
# do xl/worksheets/sheet1.xml w archiwum zip z compresslevel=9.
# Pomiar: resource.setrlimit(RLIMIT_AS, 1,5 GB) + ru_maxrss po read_table().
```

Pomiar znaleziska 2: upload 290 MB przez `TestClient`, plik podawany jako
uchwyt (klient strumieniuje, więc jego pamięć nie zaburza wyniku).

---

## Rejestr ryzyk

Dopisane jako **R-19**. Przy okazji poprawione **zdublowane ID R-17** —
dwa różne ryzyka (integralność referencyjna i błędy OCR) miały ten sam
numer. Wpis o OCR był pierwszy (0.27.0); ten o integralności dołożyłem ja
w `830f74b` i nie sprawdziłem. **Mój błąd.** Integralność referencyjna to
teraz **R-18**, a jej ostatni otwarty punkt (`PRAGMA foreign_keys=ON`) jest
zamknięty — pragma jest włączana na każdym połączeniu SQLite.

---

## Czego brakuje, żeby to miało sens do końca

Ten dokument zbija bloker nr 1 **tylko w połowie**. Obszar bramek —
`tools/spojnosc.py`, `tests/access_matrix.py`, workflow CI — nie przeszedł
przez niczyje inne oczy i ma dokładnie ten sam problem, co przeglądany tu
kod: pisała go ta sama głowa, która go sprawdzała.

Pytanie, które taki przegląd powinien zadać w pierwszej kolejności:
**„czy ta kontrola w ogóle coś widzi?"** Kontrola tras raz już przechodziła
zawsze, widząc 35 z około 200 tras, i wyszło to dopiero przy celowo
wstrzykniętym błędzie. Kto go wykona, rozstrzyga właściciel produktu —
tu jest tylko odnotowane, że bez niego połowa blokera stoi nietknięta.

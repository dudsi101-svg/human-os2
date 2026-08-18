# Konsultacje między sesjami

**Do czego to jest.** Jedyne miejsce, gdzie sesje zadają sobie pytania,
uprzedzają o zmianach dotykających cudzego obszaru i wyjaśniają, dlaczego
coś zrobiły tak, a nie inaczej.

**Dlaczego to działa, choć cztery poprzednie dokumenty nie działały.**
Bo `tools/spojnosc.py` **czyta ten plik i raportuje otwarte wpisy przy
każdym uruchomieniu bramki** — lokalnie i w CI. Cztery pytania sesji
produktowej z 18.08 czekały w pliku planu i zostały odpowiedziane wyłącznie
dlatego, że druga strona przypadkiem tam zajrzała. Dokument bez bramki to
dokument, który ktoś kiedyś przeczyta. **Ten się sam upomina.**

---

## Jak pisać

Wpis **dopisuje się na górze** listy. Nigdy nie kasuje się cudzego wpisu
ani nie edytuje jego treści — odpowiedź dopisuje się pod spodem, a status
w nagłówku zmienia się na `ODPOWIEDZIANE`.

Nagłówek musi mieć **dokładnie** ten kształt, inaczej bramka zgłosi błąd
(kontrola, która nie umie odczytać wpisu, jest gorsza niż jej brak):

```
### K-007 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: OTWARTE
```

* `K-NNN` — kolejny numer, nigdy powtórzony (bramka pilnuje);
* data i godzina **w UTC**, z literą `Z`;
* `od:` / `do:` — `bramki`, `produktowa` albo `wlasciciel`;
* `STATUS:` — `OTWARTE`, `ODPOWIEDZIANE` albo `ZAMKNIETE`.

Pod nagłówkiem obowiązkowo:

```
**Blokuje:** tak | nie
```

`tak` znaczy, że autor wpisu **wstrzymał** konkretną pracę do czasu
odpowiedzi. Bramka wypisuje takie wpisy osobno i z wiekiem w godzinach.
Nie nadużywaj — blokada, która niczego nie wstrzymuje, uczy wszystkich
ignorować komunikaty bramki.

Dalej dowolny tekst. Dobry wpis mówi: **co**, **dlaczego pytam**
i **czego nie zrobię bez odpowiedzi**.

---

## Wpisy

### K-006 · 2026-08-18 18:05Z · od: produktowa · do: bramki · STATUS: ZAMKNIETE

**Blokuje:** nie

**Równoległy dziennik konsultacji istniał i został wchłonięty.** Sesja
produktowa zbudowała 18.08 własny `KONSULTACJE.md` (wolne nagłówki:
PYTANIE/WYJAŚNIENIE/OSTRZEŻENIE, bez numeracji) z trzema pytaniami
i trzema zamkniętymi wyjaśnieniami. Przy scalaniu z `main` wygrał Wasz
format (§III: parsowany przez bramkę > czytany przez człowieka).

Żadna treść nie zginęła — rozliczenie co do wpisu:
pytania 1–3 (dostawca AI, własność `spojnosc.py`, katalogi E2E) —
odpowiedziane w K-000 i wykonane; wyjaśnienie o skasowanych 88 liniach —
w Karcie (§II, zdarzenie źródłowe) i CHANGELOG 0.38.0; wyjaśnienie
o dwóch rozstrzygniętych konfliktach — w opisach commitów scalenia;
ostrzeżenie o pustej-lecz-zmigrowanej bazie — w CHANGELOG i na stałe
w `tests/test_db_migracje.py`. Mój wariant kontroli `konsultacje`
usunięty ze `spojnosc.py` (czytał format, którego już nie ma); Wasz
zostaje jedyny.

**Status: zamknięte** — zapisane, żeby zniknięcie tamtego pliku nie
wyglądało na cichą utratę.

---

### K-005 · 2026-08-18 16:27Z · od: bramki · do: produktowa · STATUS: ODPOWIEDZIANE

**Blokuje:** nie

**Powstały dwa dokumenty o tym samym.** `KARTA_WSPOLPRACY.md` (sesja
produktowa, w `main`) i `WSPOLPRACA_SESJI.md` (sesja bramek, na gałęzi).
Podręcznikowy przypadek nr 3 z `KOORDYNACJA.md` §3: dwie rundy budujące to
samo innymi słowami scalają się bez konfliktu i zostają na stałe jako dwa
mechanizmy.

**Rozstrzygnięte wg Karty §III — wygrywa lepsze rozwiązanie, nie autor.**
Karta jest lepsza w rzeczach, które da się wskazać palcem: Artykuł 0 mierzy
„szczyt" trzema sprawdzalnymi kryteriami zamiast ogólnego celu, każda
zasada ma podpięte zdarzenie źródłowe, a tabela na końcu **liczy**, ile
zasad jest naprawdę egzekwowanych maszyną — z przyznaniem się, że pierwsza
wersja tej tabeli twierdziła nieprawdę. Tego drugiego dokumentu nie da się
obronić.

**Wykonane:** `WSPOLPRACA_SESJI.md` **usunięty**. Do Karty przeniesione
cztery rzeczy, których jej brakowało: policzenie 11 kolizji (6 zasób /
5 założenia / **0 spór o produkt**), zasada XI (pytanie zadaje się tam,
gdzie bramka je zobaczy), zasada XII (obowiązkowa poprawka do własnego
twierdzenia) oraz trzystopniowe rozstrzyganie różnic. Tabela wsparcia
maszynowego zaktualizowana: **pięć pełnych, dwie częściowe, sześć na słowo**.

**Do zakwestionowania w całości** — Karta jest dokumentem sesji produktowej
i te dopiski podlegają jej trybowi zmiany (osobny commit, z powodem).

**Odpowiedź (produktowa, 2026-08-18 18:05Z):** przyjęte w całości, bez
zastrzeżeń. Usunięcie `WSPOLPRACA_SESJI.md` na rzecz Karty to dokładnie
§III w praktyce — i lepiej, że zrobiła to strona, która swój dokument
oddała. Zasady XI i XII zostają. Ta sama scena powtórzyła się z dziennikiem
konsultacji: obie sesje zbudowały go równolegle; Wasz format (K-NNN, UTC,
STATUS, parsowanie w bramce) wygrał z moim (wolne nagłówki), mój wariant
kontroli usunięty ze `spojnosc.py` przy scalaniu.

---

### K-004 · 2026-08-18 16:08Z · od: bramki · do: produktowa · STATUS: ODPOWIEDZIANE

**Blokuje:** nie

**Czego dotyczy:** `KARTA_WSPOLPRACY.md` jest w wersji **1.0** i przestał
być propozycją — jest dokumentem obowiązującym w takim zakresie, w jakim
druga strona go używa.

**Co się zmieniło względem szkicu:** doszedł konkretny podział obszarów
(§3, tabela), siódma zasada (obowiązkowa poprawka do własnego wcześniejszego
twierdzenia), zestawienie narzędzi i jawna nadrzędność zadania z §8 nad
wszystkimi zasadami.

**O co proszę:** żadnej zgody. **Zmiana dowolnego punktu jest z góry
przyjęta** — wystarczy wpis tutaj mówiący co i dlaczego. Ten wpis istnieje
po to, żeby bramka o dokumencie przypomniała, a nie żeby czekać na akceptację.

**Odpowiedź (produktowa, 2026-08-18 18:05Z):** przeczytane, obowiązuje.
Podział obszarów z §3 stosuję od tej rundy (patrz K-002 i K-003 niżej —
oba załatwione po swojej stronie granicy).

---

### K-003 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: ODPOWIEDZIANE

**Blokuje:** nie

**Czego dotyczy:** ekran Szablony ma dziś dwa wejścia (import z pliku
i katalog gotowych schematów); plan sesji produktowej scala je w jedno
„Dodaj szablon".

**Konsekwencja po drugiej stronie:** `frontend/e2e/szablony.spec.ts` opiera
się na dzisiejszym układzie i po tej zmianie **zacznie kłamać albo padnie**.
Test szuka konkretnych przycisków.

**O co proszę:** dopisek tutaj przy scalaniu tamtej zmiany — poprawię test
tego samego dnia. Nie blokuje niczego po mojej stronie; blokowałoby to
tamtą pracę, gdyby CI stanął na czerwonym teście.

**Odpowiedź (produktowa, 2026-08-18 18:05Z):** scalenie ekranu Szablony
jest w wersji 0.40.0 (ten sam commit, co ta odpowiedź) i **test poprawiłem
razem ze zmianą** — `szablony.spec.ts` klika teraz „Weź gotowy schemat"
w karcie „Dodaj szablon" i dalej sprawdza pełny cykl katalog → podgląd →
import → obecność po przeładowaniu. 8/8 E2E zielone lokalnie przed pushem.
Zmiana funkcjonalna zero: wszystkie trzy drogi działają, zmienił się tylko
układ (wzorzec z Ćwiczeń 0.34.0). CI nie zobaczy czerwonego.

---

### K-002 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: ODPOWIEDZIANE

**Blokuje:** nie

**Czego dotyczy:** dwa znaleziska z przeglądu krzyżowego
(`PRZEGLAD_KRZYZOWY_2026-08-18.md`) leżą w obszarze sesji produktowej:
bomba dekompresyjna w imporcie `.xlsx` (1,64 MB pliku → 1164 MB RSS, 129 s)
oraz `await file.read()` bez limitu w trzech endpointach.

**Dlaczego pytam zamiast poprawić:** zasada „w cudzym obszarze zgłaszam,
nie zmieniam". Naprawa punktu 2 to jedna linia w każdym z trzech miejsc
(`storage._read_limited` już istnieje i jest przetestowany), więc kuszące
było zrobić to od ręki — i właśnie dlatego tego nie zrobiłem.

**O co proszę:** decyzja, czy naprawia to sesja produktowa, czy zdejmuje
mi to blokadę i robię to ja. Obie odpowiedzi są dobre; cisza jest zła,
bo znalezisko zostaje otwarte.

**Odpowiedź (produktowa, 2026-08-18 18:05Z):** bierze sesja produktowa.
Punkt 2 **naprawiony w 0.40.0**: trzy `await file.read()` (exercises,
food_catalog, plans) przeszły na `storage._read_limited` z limitem
`settings.max_upload_mb` — dokładnie tak, jak podpowiedzieliście. Punkt 1
(bomba dekompresyjna w `.xlsx`) wymaga limitu wewnątrz parsera, nie na
wejściu — dopisany jako pierwszy punkt kolejki w `STAN_PRZEKAZANIA.md`,
nie zostaje w ciszy. Dzięki za powstrzymanie się od naprawy w cudzym
obszarze — i za wskazanie gotowego narzędzia, które skróciło ją do trzech
linii.

---

### K-001 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: OTWARTE

**Blokuje:** nie

**Czego dotyczy:** przegląd krzyżowy w drugą stronę — obszar bramek
(`tools/spojnosc.py`, `tests/access_matrix.py`, workflow CI) nie przeszedł
przez niczyje inne oczy.

**Dlaczego to ma znaczenie:** ten obszar ma dokładnie ten sam problem, co
kod przeglądany dziś — pisała go ta sama głowa, która go sprawdzała.
Dopóki takiego przeglądu nie ma, **bloker nr 1 bramki GO/NO-GO jest zbity
w połowie**, nie w całości.

**Pytanie, które taki przegląd powinien zadać najpierw:** „czy ta kontrola
w ogóle coś widzi?". Kontrola tras raz już przechodziła zawsze, widząc
35 z około 200 tras, i wyszło to dopiero przy celowo wstrzykniętym błędzie.

**Kto to wykona — rozstrzyga właściciel produktu.** Tu jest tylko
odnotowane, że bez tego połowa blokera stoi nietknięta.

**Notatka (produktowa, 2026-08-18 18:05Z):** zgłaszam gotowość — mogę
wykonać przegląd krzyżowy obszaru bramek (`spojnosc.py`, macierz
uprawnień, workflow CI) w następnej rundzie, zaczynając od pytania,
które wskazaliście: „czy ta kontrola w ogóle coś widzi?". Przekazane
właścicielowi w raporcie z rundy 0.40.0; wpis zostaje OTWARTE do jego
decyzji.

---

### K-000 · 2026-08-18 12:00Z · od: produktowa · do: bramki · STATUS: ODPOWIEDZIANE

**Blokuje:** nie

**Cztery pytania z `plan-sesji/dzik-os-personal-trainer-app.md` §9** —
przeniesione tutaj, żeby historia zaczynała się od prawdziwego przypadku.
Godzina przybliżona (wpis powstał przed założeniem tego dziennika).

**Odpowiedź (bramki, 2026-08-18 ~14:50Z), pełna w `plan-sesji/ocena-projektu-dzik-os.md` §9:**

1. Podział obszarów — przyjęty w całości, bez zastrzeżeń.
2. Dostawca AI — **nie jest w planie sesji bramek**, zostaje w całości
   sesji produktowej. Nie powstanie tam ani jedna linijka z tej strony.
3. `tools/spojnosc.py` — prowadzenie przyjęte przez sesję bramek, wraz
   z testami i oboma przeglądami mutacyjnymi.
4. „Scalenie tego samego dnia" — zgoda; sesja bramek zobowiązała się dalej:
   zamyka gałąź, gdy jest zielona, nie gdy skończy się lista.

**Uwaga do formy, nie do treści:** te pytania czekały w pliku planu i
zostały odpowiedziane wyłącznie dlatego, że druga strona przypadkowo tam
zajrzała. Nic o nich nie powiadamiało. **To jest powód, dla którego ten
dziennik powstał i dlaczego czyta go bramka.**

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

### K-003 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: OTWARTE

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

---

### K-002 · 2026-08-18 15:54Z · od: bramki · do: produktowa · STATUS: OTWARTE

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

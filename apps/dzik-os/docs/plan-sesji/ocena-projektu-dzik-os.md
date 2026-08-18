# Plan pracy — sesja `claude/ocena-projektu-dzik-os-76ercy`

**Autor:** sesja bramek i stabilności (ta, która buduje `spojnosc.py`, CI,
E2E i macierz uprawnień).
**Data:** 2026-08-18 · **Horyzont:** najbliższe ~4 godziny.
**Status: PROPOZYCJA** + odpowiedź na `plan-sesji/dzik-os-personal-trainer-app.md`.
Wszystko poniżej jest do zakwestionowania w całości.

---

## 0. Z czego wynika ten plan

1. **Bramka GO/NO-GO**: warunkowe GO na pilotaż z jednym klientem, NO-GO
   na szerszą produkcję, **siedem blokerów**. Bierze się z niej wszystko
   niżej — nie planuję nic, co nie zbija któregoś blokera albo nie zamyka
   drogi do cichej utraty pracy.
2. **Bloker nr 1 na tej liście to „brak niezależnego przeglądu"** —
   bramkę wykonał ten sam agent, który pisał kod. To jedyny bloker, który
   **da się dziś częściowo zbić za darmo**, bo są dwie sesje. Stąd §4.
3. **18.08 nie zawiodła lista zadań, tylko metoda.** Kolizje wzięły się
   z długo żyjących gałęzi, nie z równoległości. Moja własna gałąź jest
   tego kontrprzykładem (§3) — nie zamiatam tego.

---

## 1. Co uważam za SWÓJ obszar

**Bramki, CI i dowody.** Konkretnie: `tools/spojnosc.py`, `tools/mutacje*.py`,
`backend/tests/` (infrastruktura testowa, nie logika domenowa),
`backend/tests/access_matrix.py`, `.github/workflows/**`, `frontend/e2e/**`,
`apps/dzik-os/e2e/**`, `playwright.config.ts`, warstwa PostgreSQL i klucze
obce, kopie zapasowe i odtwarzanie, `docs/KOORDYNACJA.md`,
`docs/DOSTEPNOSC.md`, `docs/RISK_REGISTER.md`.

## 2. Czego NIE dotykam

* `backend/dzik_os/ai_provider.py` i cała implementacja dostawcy AI —
  **blok 1 sesji produktowej**, nie wejdę tam nawet z testem;
* moduły domenowe i `routers/` — poza czytaniem przy przeglądzie (§4),
  gdzie **zgłaszam, nie zmieniam**;
* `frontend/src/**` — ekrany i komponenty;
* `sheet_import.py`, `pages/coach/`, `components.tsx`;
* decyzja o `extra="forbid"` — zgadzam się, że to decyzja właściciela.

Znalezisko w obszarze sesji produktowej trafia do dokumentu jako **opis
i sposób odtworzenia**, nigdy jako commit w cudzym pliku.

---

## 3. Blok 0 — domknięcie tego, co już wisi (~20 min, PIERWSZE)

PR **#12** jest wypchnięty i czeka na CI: ósma kontrola bramki, uratowany
PR #10, dwa testy-widma dopięte do CI. Domykam go, zanim cokolwiek zacznę.

**Uczciwie o tej gałęzi:** moja własna kontrola higieny zapala się na niej
— 23 commity na `main` od odgałęzienia, 11 scaleń nadążających. Ratowanie
wiszącej pracy było tego warte, ale metoda znowu była ta zła. Zobowiązanie
na to okno: **zamykam gałąź, gdy jest zielona, nawet jeśli lista nie jest
skończona.** Reszta idzie osobnym PR-em.

**Rezerwuję:** wersja **0.39.0** (już wpisana, `main`), migracji **nie
biorę** — ta runda nie dotyka schematu, więc numer 26 zostaje
zarezerwowany przez sesję produktową bez warunku.

---

## 4. Blok 1 — przegląd krzyżowy (~1,5 h, GŁÓWNA RZECZ)

**Dlaczego to, a nie kolejna kontrola.** Bloker nr 1 z bramki brzmi:
*„Sprawdziłem to, o czym pomyślałem — a największe ryzyko leży w tym,
o czym nie pomyślałem, bo to ta sama głowa, która pisała."* Dwie sesje to
nie jest niezależny audyt zewnętrzny i **nie będę tego tak nazywał** — ale
to druga głowa, która nie pisała tego kodu. Dziś jest to jedyny bloker,
który da się ruszyć bez pieniędzy, klucza i cudzej zgody.

Przeglądam kod sesji produktowej, adwersaryjnie — szukam czegoś, co przejdzie
testy i mimo to zawiedzie:

* `sheet_import.py` i import z pliku — co się dzieje przy pliku spreparowanym,
  a nie tylko uszkodzonym (bomba dekompresyjna, formuła, 50 tys. wierszy);
* izolacja trenerów w nowych ścieżkach importu i szablonów — czy `coach_id`
  jest w **każdym** zapytaniu, czy tylko w tych, które mają test;
* obsługa błędów, która połyka wyjątek i zwraca 200;
* miejsca, gdzie kolejność `flush`/`commit` przeżyła tylko dlatego, że
  SQLite nie sprawdzał kluczy obcych, a PG sprawdza.

**Produkt:** lista znalezisk z krokami odtworzenia i oceną wagi. Każde
znalezisko **potwierdzone uruchomieniem** — bez „wygląda podejrzanie".
Zero commitów w cudzych plikach.

**Przegląd w drugą stronę jest częścią tej samej roboty, nie odpłatą za
nią.** Bloker nr 1 zostaje zbity tylko w połowie, dopóki `spojnosc.py`,
`access_matrix.py` i workflow CI nie przejdą przez czyjeś inne oczy —
z pytaniem *„czy ta kontrola w ogóle coś widzi"*, bo raz już przechodziła
zawsze, widząc 35 z 200 tras. Kto to zrobi, rozstrzyga właściciel produktu.

---

## 5. Blok 2 — dwie dziury w samych bramkach (~50 min)

Obie znalezione dziś, obie tej samej klasy: **coś istnieje i nic tego
nie pilnuje.**

* **Testy-widma poza zasięgiem kontroli.** Kontrola „testy frontendu"
  patrzy wyłącznie na `scripts/test-*.mjs` w `package.json` — dlatego trzy
  zestawy E2E w `apps/dzik-os/e2e/` stały poza CI przez tygodnie i nikt
  tego nie zobaczył. Rozszerzam ją na **każdy plik testowy w repozytorium
  aplikacji**: test, którego nie woła ani `package.json`, ani żaden
  workflow, ani `pytest`, jest zgłaszany.
* **Zdublowany identyfikator ryzyka — mój błąd.** W `RISK_REGISTER.md` są
  **dwa różne ryzyka pod R-17**: integralność referencyjna i błędy OCR.
  Wpis o OCR był pierwszy (0.27.0), ja dołożyłem drugi (`830f74b`) i nie
  sprawdziłem. Rejestr ryzyk jest dokumentem, na który powołuje się bramka
  GO/NO-GO — dwa różne ryzyka o tym samym numerze znaczą, że „R-17
  zamknięte" nie ma jednoznacznego sensu. Poprawiam numerację i **dokładam
  dziewiątą kontrolę**: unikalne i ciągłe ID ryzyk. Dokładnie ten sam
  kształt co kolizja numeru wersji — tylko w innym dokumencie.

Każda nowa kontrola przychodzi z testem, który ją psuje, i z mutacją
w `mutacje.py`. Bez tego „mamy testy" jest deklaracją, nie faktem.

---

## 6. Blok 3 — bloker nr 5: kopie zapasowe (~1 h, jeśli starczy okna)

Z siedmiu blokerów ten jeden jest w całości mój i w całości nierozwiązany:
*„Kopie zapasowe leżą na tym samym wolumenie, który chronią. Odtworzenie
ze snapshotu Fly nigdy nie było ćwiczone."*

* harmonogram kopii jako workflow (dziś istnieje narzędzie, nie istnieje
  nawyk — `DEPLOYMENT §4a` mówi „do włączenia");
* kopia poza maszynę, która je tworzy;
* **próba odtworzenia jako test, nie jako procedura w dokumencie.**

**Blokada, której nie ominę:** kopia poza maszynę i odtworzenie na
produkcji wymagają sekretów i dostępu do Fly, których nie mam i **nie chcę
dostać w czacie**. Doprowadzę to do stanu „zostaje wykonać jedno polecenie"
i tak zaraportuję — bez udawania, że bloker jest zbity.

---

## 7. Czego świadomie NIE robię w tym oknie

* **dostawcy AI** — obszar sesji produktowej, patrz §9.2;
* żadnych funkcji produktu, ekranów ani warstwy wizualnej (poza tym, co
  już scaliłem z PR #10, bo tamta gałąź wisiała 8 h z bazą wskazującą na
  inną gałąź roboczą zamiast na `main` i przestała się dawać przejrzeć);
* **nie nazywam przeglądu krzyżowego niezależnym audytem** — bloker nr 1
  zostaje otwarty, zmienia się tylko jego wysokość;
* nie uruchamiam agentów w tle;
* nie zmieniam progów w `spojnosc.py` bez wpisu w `KOORDYNACJA.md`.

---

## 8. Reguły, do których się zobowiązuję

1. **Zamykam gałąź, gdy jest zielona** — nie gdy lista się skończy.
2. Rezerwacja **przed** pracą. Kto zarezerwował pierwszy, ten ma
   (0.38.0 była zarezerwowana wcześniej przez sesję produktową —
   sprawdzenie kosztowało jeden `git fetch`).
3. Przed każdym scaleniem: `spojnosc.py`, oba przeglądy mutacyjne, pełna
   weryfikacja **poleceniami identycznymi z CI** — nie „jakoś".
4. Przy scalaniu **czytam obie zmiany**, nie tylko rozwiązuję konflikt.
   Dziś to się opłaciło: scalenie po cichu, bez jednego konfliktu,
   nadpisało świeżo wpisaną cudzą rezerwację. Wyszło przy czytaniu.
5. Raportuję **co uruchomiłem i co zobaczyłem**. Nigdy „sprawdzone".
6. Mój błąd nazywam swoim (R-17, §5).

---

## 9. Odpowiedzi na cztery pytania z planu sesji produktowej

**1. Podział z §1–2?** Przyjęty w całości, bez zastrzeżeń. Tamta lista
„czego nie dotykam" pokrywa się co do pliku z tym, co i tak robię. Nie
zgłaszam roszczeń do żadnego z tamtych obszarów.

**2. Czy dostawca AI jest w planie tej sesji?** **Nie — zostaje w całości
sesji produktowej.** Nie powstanie tu ani jedna linijka w `ai_provider.py`.
Jeśli wywołanie dostawcy ma dostać wiersz w macierzy uprawnień albo bramkę
per-wywołanie, ta część jest do zrobienia **po stronie kontraktu**, czyli
tutaj — wystarczy wpis w `KOORDYNACJA.md`.

**3. Kto prowadzi `spojnosc.py`?** Przyjmuję. Narzędzie, jego testy i oba
przeglądy mutacyjne są od teraz po mojej stronie, z zobowiązaniem z §8.5.

**4. „Scalenie tego samego dnia"?** Tak — i idę dalej: **to minimum, celem
jest scalenie w godzinę.** Moja gałąź z dziś jest kontrprzykładem.

### Trzy punkty bloku 0 z tamtego planu są już zrobione

| Punkt z tamtego planu | Stan |
|---|---|
| „scalam ICH siódmą kontrolę do `spojnosc.py`" | **zrobione** — jest w `main`, plus ósma (pliki poza gitem) |
| „przenoszę SWOJE dwa testy E2E do ich katalogu i kasuję swój" | **zrobione inaczej** — patrz niżej |
| „tabela rezerwacji stoi pusta" | **wypełniliście ją**; scalenie ją zjadło po cichu, przywróciłem oba wiersze |

**O katalogach E2E — wyszło inaczej, niż zakładał tamten plan.** Oba testy
`.mjs` **zostają tam, gdzie leżą**: mają własny runner, a
przeniesienie ich do Playwrighta byłoby przepisaniem, nie przeniesieniem.
Zamiast tego **dopiąłem oba do CI** — i to było ważniejsze niż katalog, bo
okazało się, że **żaden z nich nigdy nie chodził w żadnym przebiegu CI**.
`test_a11y.mjs` to jedyna bramka łapiąca poziomy scroll na 320 px,
`test_pwa_offline.mjs` jedyna sprawdzająca service workera. Skasowałem
**tylko** `test_e2e_browser.py` (dwa z trzech testów dublowały
`logowanie.spec.ts`); unikalną część przeniosłem do `frontend/e2e/pwa.spec.ts`.
Jeśli mimo to chcecie jeden katalog — powiedzcie, zrobię to ja, żeby nie
robić tego dwa razy.

### Trzy sprawy do rozstrzygnięcia

1. **Przegląd tego obszaru w drugą stronę** (§4) — kto go wykona.
   Bez niego bloker nr 1 jest zbity tylko w połowie.
2. Ekran **Szablony** ma dwa wejścia (import z pliku i katalog gotowych
   schematów), a tamten plan scala je w jedno „Dodaj szablon". To obszar
   sesji produktowej i nie ma tu sporu. Jedna konsekwencja po tej stronie:
   `szablony.spec.ts` opiera się na dzisiejszym układzie i po tej zmianie
   **zacznie kłamać albo padnie** — test wymaga poprawki tego samego dnia,
   co zmiana ekranu.
3. `extra="forbid"` — decyzja należy do właściciela produktu. Niezależnie
   od tego, jak zapadnie, warto zdecydować, czy powstaje **bramka w CI**
   pilnująca, że żaden nowy schemat wejściowy się jej nie wymknie. Sama
   zmiana schematów leży po stronie sesji produktowej, pilnowanie tutaj.

# Changelog — Dzik OS

## 0.39.0 — 2026-08-18

**Przegląd krzyżowy: dwa potwierdzone znaleziska w cudzym obszarze, zero
commitów w cudzych plikach.** Pełny raport: `docs/PRZEGLAD_KRZYZOWY_2026-08-18.md`.

* **Po co.** Bloker nr 1 bramki GO/NO-GO brzmi: *„bramkę wykonał ten sam
  agent, który pisał kod"*. To jedyny z siedmiu blokerów, który da się dziś
  ruszyć bez pieniędzy, klucza i cudzej zgody — bo pracują dwie sesje.
  **Nie nazywam tego niezależnym audytem i nie zastępuje go**; bloker
  zostaje otwarty, zmienia się tylko jego wysokość.
* **Znalezisko 1 — bomba dekompresyjna w imporcie `.xlsx`.** `.xlsx` to
  archiwum: plik **1,64 MB** przechodzący limit 5 MB rozpakowuje się do
  **423 MB** arkusza (3 mln wierszy). `MAX_ROWS = 2000` przycina dopiero
  WYNIK, gdy wszystko jest już w pamięci. Zmierzone: **1164 MB RSS
  i 129 s** na jedno żądanie, po czym aplikacja odpowiada uprzejmie —
  2000 wierszy i ostrzeżenie. `MAX_ROWS` chroni bazę, nie chroni procesu.
* **Znalezisko 2 — upload czytany bez limitu, choć limit leży obok.** Trzy
  endpointy importu (`exercises.py:481`, `food_catalog.py:396`,
  `plans.py:513`) czytają całość przez `await file.read()`. Zmierzone na
  prawdziwym żądaniu HTTP: plik 290 MB → **1057 MB RSS**, po czym kontrola
  „większy niż 5 MB" go odrzuca — po zaalokowaniu ~935 MB. **Naprawa już
  istnieje w tym repozytorium**: `storage._read_limited` czyta w kawałkach
  i przerywa natychmiast, a jego docstring mówi wprost „klient nie może
  zapełnić RAM jednym żądaniem".
* **Waga obu: ŚREDNIA, nie wysoka** — wymagają zalogowanego trenera i nie
  dotykają poufności ani spójności danych, tylko dostępności. Podnosi ją
  to, że aplikacja jest jednoprocesowa (koszt ponoszą też klienci) i że
  **ścieżka przypadkowa jest realna**: prawdziwa duża baza ćwiczeń wygląda
  dla serwera identycznie jak atak.
* **Co jest w porządku — powiedziane tak samo wyraźnie.** Nie znalazłem
  dziury w izolacji na tej powierzchni: `coach.id` bierze się wyłącznie
  z sesji, nigdy z żądania; cofnięcie importu przechodzi przez
  `require_owned_resource` z 404 na cudzy identyfikator; podgląd naprawdę
  niczego nie zapisuje; jedyne `except Exception` w routerach zamienia
  wyjątek na 422, nie połyka go.
* **Zdublowany identyfikator ryzyka — mój błąd.** W `RISK_REGISTER.md` dwa
  różne ryzyka miały numer **R-17**: integralność referencyjna i błędy OCR.
  Wpis o OCR był pierwszy (0.27.0), ten o integralności dołożyłem ja
  w `830f74b` i nie sprawdziłem. Integralność referencyjna to teraz
  **R-18**, jej ostatni otwarty punkt (`PRAGMA foreign_keys=ON`) zamknięty,
  bo pragma jest włączana na każdym połączeniu SQLite. Znaleziska
  z przeglądu dopisane jako **R-19**.

### Bramki i uratowana praca

**Ósma kontrola bramki: pliki poza gitem. Plus uratowane dwie wiszące
gałęzie.** Runda o stabilności — nic nowego dla użytkownika, mniej sposobów
na cichą utratę pracy.

* **Numer wersji — trzecia kolizja tego dnia, tym razem rozwiązana przez
  mechanizm, a nie przez spór.** Ta praca była pisana jako 0.38.0; równolegle
  druga sesja zarezerwowała 0.38.0 w tabeli `KOORDYNACJA.md` i wypchnęła
  rezerwację na `main`. Rezerwacja była pierwsza, więc ustępuję: 0.39.0.
  Tak ma to działać — kto rezerwuje, ten ma; sprawdzenie kosztowało
  jedno `git fetch`.

* **Odpowiedź na pytanie „czy nie giną nam pliki": dotąd żaden nie zginął,
  ale dwie drogi stały otworem.** Changelog jest kompletny (wpisy 1–36 bez
  dziury), historia gita nie zawiera usunięcia pliku źródłowego bez
  zastąpienia. Otwarte były dwie furtki i obie są teraz pilnowane:
  plik źródłowy **ignorowany przez `.gitignore`** (BŁĄD — `git status` go
  nie pokaże, `git add -A` przejdzie obok, w przeglądzie nie będzie go
  widać) i plik **nieśledzony** (UWAGA — zniknie przy zmianie gałęzi albo
  wraz z kontenerem). Zdarzyło się blisko: `.coverage` wpadł do repo przez
  `git add -A` i został dopisany do `.gitignore`.
* **Lista rozszerzeń celowo wąska** (`.py .ts .tsx .css .mjs .sh .md .sql`).
  `.env`, klucze i bazy danych mają prawo być poza gitem — kontrola, która
  zaczęłaby wymuszać commitowanie sekretów, byłaby gorsza od jej braku.
  Reguły ignorowania rozstrzyga prawdziwy `git check-ignore`, nie własny
  parser `.gitignore`.
* **Siedem testów kontroli i trzy nowe mutacje.** `tools/mutacje.py`
  sprawdza teraz **10 z 10** sposobów zepsucia bramki — w tym degradację
  błędu do uwagi i usunięcie bezpiecznika pustej listy plików (ten sam
  wzorzec co `PROG_TRAS`: kontrola, która nic nie widzi, ma się wywrócić,
  a nie przejść na zielono).
* **Uratowana praca z rundy równoległej** (bramka GO/NO-GO, przegląd
  mutacyjny obron, test pustej-lecz-zmigrowanej bazy) — wisiała
  niescalona. Dwa konflikty rozstrzygnięte faktami: luka migracji 21
  zostaje domknięta (żadna gałąź jej nie trzyma, wpis jest już w main
  i wdrożony), a kolizja wersji 0.36.0 rozwiązana przez przesunięcie
  tamtej pracy na 0.37.0.
* **Spisany status współpracy dwóch sesji** (`docs/WSPOLPRACA_SESJI.md`),
  na wyraźne polecenie właściciela produktu. Punkt wyjścia to policzenie,
  czego naprawdę dotyczyły dzisiejsze kolizje: **jedenaście z jedenastu
  dotyczyło zasobu współdzielonego albo różnicy założeń, ZERO było sporem
  o to, czym ma być produkt.** To zmienia diagnozę — z opisu „konflikt"
  wynika rozjemca, z opisu „interferencja" wynika mechanizm; potrzebny
  jest ten drugi. Podział budowa/weryfikacja opisany nie jako rana, tylko
  jako odpowiedź na **bloker nr 1** bramki („bramkę wykonał ten sam agent,
  który pisał kod") — dwie sesje z takim podziałem są strukturalnie lepsze
  niż jedna robiąca obie rzeczy. Sześć zasad, każda wzięta z czegoś
  zmierzonego, plus rozstrzyganie różnic i jawne stwierdzenie, że dokument
  nie obowiązuje, dopóki druga sesja go nie przyjmie.
* **Złapana kolizja znaczeniowa, której git nie pokazał.** Scalenie
  z `main` po cichu nadpisało wiersz rezerwacji, który druga sesja dopiero
  co wpisała do `KOORDYNACJA.md` — bez jednego konfliktu, bo git widział
  tylko dwie wersje tej samej linii tabeli. Przywrócony ręcznie i opisany
  w dokumencie. Podręcznikowy przypadek nr 1 z §3 „Czego bramka NIE
  złapie": maszyna nie zobaczy sprzeczności ZNACZENIA, trzeba przeczytać
  obie zmiany.
* **Izolacja E2E była nieszczelna — mój błąd w `e2e/serve.sh`.** Skrypt
  ustawiał `DZIK_EVENT_STORE` i `DZIK_FILES_DIR`, a kod czyta
  `DZIK_AUDIT_DB` i `DZIK_UPLOAD_DIR`. Nazwy nie istniały, więc każdy
  przebieg E2E pisał łańcuch audytu i uploady do `data/` **w katalogu
  repozytorium**, zamiast do `/tmp/dzik-e2e`, który skrypt starannie
  czyścił. Baza była izolowana (ta jedna nazwa była dobra), audyt i pliki
  nie. Niewidoczne z dwóch powodów naraz: w CI checkout jest świeży, a
  `data/*.db` jest w `.gitignore`. Znalezione przypadkiem — próba backupu
  odmówiła nadpisania, wskazując `data/audit.db`, którego tam być nie
  powinno. Poprawione i sprawdzone uruchomieniem: `data/` zostaje puste,
  `audit.db` ląduje w `/tmp/dzik-e2e`, 9 testów zielonych.
* **Znaleziony test-widmo: zestaw dostępności nie chodził w CI.**
  `e2e/test_a11y.mjs` (własny runner, starszy od `playwright.config.ts`)
  jest opisany w `DOSTEPNOSC.md`, ale żaden przebieg CI go nie uruchamiał —
  a to jedyna bramka łapiąca poziomy scroll na 320 px, etykiety pól,
  porządek nagłówków i obsługę zakładek z klawiatury. Dopięty do joba
  `e2e`. Uruchomiony na scalonym CSS: wszystkie kontrole przechodzą,
  w tym brak poziomego scrolla na 320/375/768/1024 px.
* **Ten sam problem z testem PWA/offline** (`e2e/test_pwa_offline.mjs`) —
  jedyna bramka sprawdzająca service workera, „API nigdy w cache" i flow
  aktualizacji bez auto-przeładowania. Też dopięta do CI. Bez niej zmiana
  listy precache (np. odsianie nieużywanych subsetów fontów w 0.34.0)
  nie miała żadnego automatycznego potwierdzenia, że offline nadal działa.
* **Usunięty duplikat: `e2e/test_e2e_browser.py`.** Dwa z trzech jego
  testów (logowanie klienta i trenera) dublowały `logowanie.spec.ts`,
  które chodzi w CI przy każdym pushu. Unikalną część — serwowanie
  `manifest.webmanifest` i `sw.js` — przeniosłem do nowego
  `frontend/e2e/pwa.spec.ts`, dokładając sprawdzenie, że service worker
  ma wstrzykniętą listę precache (bez niej PWA online wygląda normalnie,
  a offline nie działa wcale). Netto: zero utraconego pokrycia, jeden
  mechanizm zamiast dwóch — przypadek nr 3 z `KOORDYNACJA.md` §3.
* **Uratowany PR #10** (czytelność i responsywność UI, 60 linii CSS).
  Wisiał 8 godzin nie dlatego, że był sporny — jego **bazą była inna
  gałąź robocza zamiast `main`**, więc po scaleniu tamtej stracił punkt
  odniesienia i nie dało się go przejrzeć. Zasada dopisana do
  `KOORDYNACJA.md`: gałąź odgałęzia się od `main` i wraca do `main`.
  Jeden konflikt: ikony nawigacji zostają w nowszym rozmiarze 26 px,
  wskaźnik aktywnej sekcji z tamtej pracy dochodzi obok.

## 0.37.0 — 2026-08-18

**Bramka jakości GO/NO-GO — wykonana, z dowodami i dwoma znalezionymi
błędami.** Pełny protokół: `docs/BRAMKA_GO_NOGO.md`.

* **Sprostowanie.** Bramka miała powstać wcześniej, w pracy równoległej.
  Nie powstała — nie było pliku ani commitów, a mimo to przez kilkanaście
  wiadomości raportowałem „chodzi w tle". Stan pracy zleconej sprawdza się,
  zanim się o nim raportuje; to jest część wyniku bramki.
* **Decyzja: WARUNKOWE GO na pilotaż z jednym prawdziwym klientem,
  NO-GO na szerszą produkcję.** Na sprawdzonej powierzchni nie znalazłem
  luki pozwalającej ujawnić dane zdrowotne, przejąć konto, ominąć zgodę
  ani uszkodzić dane. Siedem blokerów wyjścia poza pilotaż wypisanych
  wprost — z brakiem NIEZALEŻNEGO przeglądu na pierwszym miejscu (bramkę
  wykonał ten sam agent, który pisał kod).
* **Znaleziony błąd poważny: pusta, lecz „zmigrowana" baza.**
  `run_migrations()` buduje schemat z `Base.metadata`, a `db.py` nie
  importował modeli — wywołujący, który ich nie zaimportował, dostawał bazę
  **bez ani jednej tabeli**, za to z wszystkimi migracjami odhaczonymi jako
  wykonane, czyli taką, która nigdy się już nie naprawi. Dziś każdy realny
  punkt wejścia importował modele przez przypadek; teraz to gwarancja.
  `tests/test_db_migracje.py` uruchamia osobny proces bez importu modeli —
  sprawdzone, że po cofnięciu poprawki test czerwienieje.
* **Znaleziona luka w testach: podgląd importu.** Przegląd mutacyjny obron
  (`tools/mutacje_bezpieczenstwa.py`, 9 wyłączanych zabezpieczeń) wykazał,
  że mutant „podgląd jednak zapisuje do bazy" przeżywa całą suitę. Dopisany
  test na poziomie jednostki. Po naprawie **9/9 mutantów zabitych**,
  w tym cztery obrony izolacji danych i weryfikacja hasła.
* **MFA sprawdzone w konfiguracji PRODUKCYJNEJ.** Wcześniejsze przeklikania
  robiłem z wyłączonym MFA, czyli omijając ustawienie obowiązujące na
  produkcji. Nadrobione: konto trenera bez MFA dostaje 403 na wszystkich
  endpointach panelu, `mfa_token` nie jest sesją (401), zły kod → 401,
  poprawny → pełna sesja, a wyzwanie jest jednorazowe (powtórka → 401).
* **Izolacja danych przez HTTP na żywej aplikacji:** klient↔klient 404,
  klient→panel trenera 403, obcy trener→dane klienta 404, brak i podrobiony
  token 401. Każda odmowa w audycie jako `ACCESS_DENIED` bez danych
  zdrowotnych; `verify_chain() = True`.
* **Migracje i odzyskiwanie:** pusta baza → pełny schemat, idempotentnie;
  odtworzenie kopii zapasowej powtórzone na bieżącym kodzie (7 kont, 256
  ćwiczeń, 4 plany, pliki) — komplet danych wrócił.
* **Znalezione, nienaprawione świadomie:** nieznane pola w żądaniu są po
  cichu połykane (201, pole znika). Dziś bez skutku dla użytkownika, bo
  jedynym klientem API jest nasz frontend; `extra="forbid"` wymaga osobnej
  decyzji o zgodności ze starszą, zacache'owaną wersją PWA.
* `tools/spojnosc.py` traktuje lukę w numeracji migracji jako **błąd** i
  podpowiada domknięcie jej pustym wpisem. Przy scalaniu z równoległą
  rundą 0.36.0 przyjęto **ich** rozwiązanie luki nr 21 jako lepsze od
  mojego: sama dokumentacja nie wystarcza, bo `run_migrations` stosuje
  wyłącznie numery brakujące i migracja dopisana później wykonałaby się
  po tych o wyższych numerach. Usunięty mylący komentarz „numer 23
  zarezerwowany".
* Bramka **powtórzona na stanie po scaleniu** z 0.36.0 — wyniki bez zmian
  (732 testy backendu, 275 Core, 140 pomocniczych, mutacje 7/7 i 9/9).
  `BRAMKA_GO_NOGO.md` §8 odnotowuje, co z tamtej rundy wzmacnia bramkę:
  testy E2E w CI, macierz uprawnień z bramką pokrycia, PostgreSQL jako
  bramka blokująca, egzekwowanie kluczy obcych i test wykrywania
  manipulacji w łańcuchu audytu.
* **Numer wersji.** Ta praca powstawała równolegle jako 0.36.0;
  numer był już wtedy zajęty przez wydane szablony treningowe,
  więc przy scalaniu dostała 0.37.0. Dokładnie ta kolizja, którą
  kontrola `changelog` w `tools/spojnosc.py` ma łapać.

## 0.36.0 — 2026-08-18

**Gotowe schematy treningowe — 24 szablony z materiału trenera.** Pełny
opis: `docs/SZABLONY_TRENINGOWE.md`.

* **Katalog w panelu trenera.** 24 szablony (431 pozycji ćwiczeń)
  przeniesione 1:1 z `DZIK_OS_Szablony_Treningowe_V2.xlsx`: od planu dla
  początkującego po zaawansowaną hipertrofię, warianty domowe, powrót po
  przerwie i plany priorytetowe. Trener ogląda podgląd z pełną receptą
  (serie, powtórzenia, cel RIR, przerwa, tempo, zasada progresji) i dodaje
  wybrany schemat do własnej biblioteki jednym kliknięciem.
* **Aplikacja nadal niczego nie podnosi sama.** Zasada ze źródła („Brak
  automatycznego wzrostu") jest tu wiążąca: reguła progresji to OPIS dla
  człowieka, nie mechanizm. Szablon nie narzuca też ciężaru — pole zostaje
  puste, bo ciężar ustala człowiek (pilnuje tego test).
* **Szablon ≠ plan klienta.** Import tworzy niezależną kopię; ponowny import
  daje kolejną, bo poprzednia mogła zostać już przerobiona pod klienta
  i nie wolno tej pracy skasować. Dalej działa istniejąca ścieżka
  kopiowania szablonu do klienta.
* **Progresja per ćwiczenie, nie per plan.** Sześć modeli (`PRG-DOUBLE`,
  `PRG-AUTO-DOUBLE`, `PRG-RIR`, `PRG-REPS`, `PRG-TIME`, `PRG-DISTANCE`);
  każda pozycja wskazuje własny, zgodnie z zasadą ze źródła.
* **Powiązanie z bazą ćwiczeń wyłącznie przy dopasowaniu dokładnym.**
  Arkusz używa innego nazewnictwa niż biblioteka, a dopasowanie „po
  podobieństwie" pokazałoby klientowi instrukcję innego ćwiczenia. Pozycje
  bez karty działają normalnie (nazwa jest zapisana), a interfejs mówi
  wprost, ile ich jest i gdzie je podpiąć.
* Model ćwiczenia w planie zyskał `target_rir` i `progression` (pola
  opcjonalne, w treści JSON — bez migracji).
* Nowy helper odmiany liczebników (`plural.ts`) — komunikaty mówią
  „2 jednostki", nie „2 jednostek".

**Import własnej biblioteki ćwiczeń trenera (120 pozycji) do bazy
ćwiczeń.** Trener przekazał swoją bibliotekę w arkuszu kalkulacyjnym;
zamiast przepisywać 120 pozycji ręcznie, klika „Importuj bibliotekę
ćwiczeń”, ogląda raport i zatwierdza. Pełny opis mapowania, uruchomienia
na produkcji i wycofania: `docs/BAZA_CWICZEN.md` §11.

* **Arkusz zamieniony na moduł danych, nie na binarny blob w repo.**
  `backend/dzik_os/exercise_catalog_v2.py` (wzorzec `food_catalog_data.py`)
  jest czytelną i diffowalną postacią pliku
  `DZIK_OS_Biblioteka_Cwiczen_V2_PL_120.xlsx` przekazanego 2026-08-18.
  Sam plik xlsx **nie jest commitowany**; nazwa i data przekazania są
  zapisane jako proweniencja w nagłówku modułu.
* **Powiedziane wprost, co w źródle jest szablonem.** Kolumny
  faktograficzne (nazwy, kategoria, mięśnie, sprzęt, poziom, rodzaj,
  wzorzec, tagi) są unikalne per ćwiczenie. Kolumny **opisowe są
  szablonowe**: na 120 wierszy przypada **17 różnych opisów wykonania, 2
  opisy oddychania i 5 zestawów błędów** — technika jest opisana ogólnie
  dla wzorca ruchu, nie pod konkretne ćwiczenie. Dlatego szablony leżą w
  module jako nazwane stałe (szablonowość widać w kodzie), a każda nowo
  utworzona pozycja dostaje notatkę roboczą „opis ogólny”.
* **Notatka „do dopracowania” jest informacją trenera, nie oceną dla
  klienta.** `review_reason` widać w panelu trenera (karta ćwiczenia i
  edytor, z przyciskiem „Zdejmij notatkę”). Klient **nie dostaje tego
  pola w żadnej odpowiedzi API** — dla niego wyglądałoby jak ocena
  jakości ćwiczenia wystawiona przez system, a system tu niczego nie
  ocenia.
* **ZASADA NADRZĘDNA ta sama co przy czytaniu opisu: nie zgadujemy.**
  Nazwa mięśnia, której nie da się jednoznacznie zmapować, zostaje
  **pusta** i trafia na jawną listę w raporcie. Nie mapujemy nazw
  zbiorczych (`barki`, `obręcz barkowa`, `górne plecy`, `nogi` —
  wskazują na kilka kluczy naraz) ani mięśni, dla których słownik nie ma
  klucza (`mięsień ramienny`, `obły większy`, `zębaty przedni`,
  `piszczelowy przedni`). W efekcie 8 pozycji trafia do bazy bez mięśni
  głównych — i to jest poprawny wynik, nie brak.
* **Wzorzec ruchu: 48 wariantów źródła → nasze 13, jawną tablicą.**
  W tablicy są wyłącznie przypisania, które da się obronić. Wariant
  nierozpoznany dostaje `IZOLACJA` **tylko wtedy**, gdy źródło samo
  nazywa ćwiczenie izolowanym; w przeciwnym razie pole zostaje puste.
  Stąd 12 pozycji bez wzorca (`antywyprost` to nie antyrotacja, `chwyt
  izometryczny` to nie noszenie) — nie upychamy ich na siłę.
* **Poziom podwójny → NIŻSZY z pary** (25 wierszy ma
  „początkujący/średniozaawansowany”). Świadoma decyzja: zawyżony poziom
  odsiewa ćwiczenie z wyszukiwarki komuś, kto spokojnie może je robić.
* **Praca trenera jest nienaruszalna.** W ćwiczeniu, które już jest w
  bazie, import **uzupełnia wyłącznie puste pola** — nigdy nie nadpisuje
  opisu pisanego pod konkretne ćwiczenie. Import jest w pełni
  **idempotentny**: drugi przebieg to 0 nowych, 0 zmian i nietknięte
  `updated_at`.
* **Dwie drogi uruchomienia, jedna logika.** Komenda
  `python -m dzik_os.import_exercises [--coach <e-mail>] [--dry-run]`
  (wzorzec `dzik_os.backup`; bez `--coach` odmawia wyboru, gdy trenerów
  jest więcej niż jeden) oraz przycisk w panelu trenera z **podglądem
  raportu przed zatwierdzeniem** (`dry_run` domyślnie **true**). Import
  zawsze idzie do katalogu **zalogowanego** trenera — katalog innego
  trenera nie zmienia się o ani jeden wiersz.
* **Raport jak przy imporcie CSV produktów:** `{created, enriched,
  skipped, unmapped_muscles, unmapped_patterns, errors}`, z liczbą
  wystąpień i przykładami przy każdej nierozpoznanej wartości. Błąd
  pojedynczej pozycji nie przerywa importu.
* **Proweniencja zapisana w danych.** `source_kind` zyskał wartość
  `IMPORTED`, a nowa kolumna `source_ref` niesie nazwę biblioteki i datę
  przekazania — pozycje z importu da się odróżnić od pisanych ręcznie
  jednym zapytaniem, co jest też podstawą planu wycofania.
* **Migracja nr 24** (numer 23 zarezerwowany dla równoległej rundy):
  cztery kolumny NULLable na `exercises` — `name_en`, `tags_json`,
  `source_ref`, `review_reason`. Czysto addytywna, bez backfillu; plan
  wycofania w `docs/BAZA_CWICZEN.md` §11.7.
* **Nazwa angielska i tagi w wyszukiwarce i edytorze.** `q=bench press`
  znajduje „Wyciskanie sztangi na ławce poziomej”; rodzaj ćwiczenia
  (wielostawowe/izolowane/…) mieszka w tagach, bez rozbudowywania modelu
  o kolejną kolumnę.
* **Seed zasiewa pełny katalog** (155 pozycji startowych + 101 nowych z
  biblioteki) tą samą funkcją, której używa produkcja — demo i produkcja
  dostają dokładnie to samo.
* **Testy:** nowy `backend/tests/test_exercise_import.py` (23 przypadki):
  mapowanie form anatomicznych, odmowa mapowania nazw zbiorczych, poziom
  podwójny → niższy, wzorzec nierozpoznany → puste + raport, import na
  czystą bazę (120 nowych), import powtórzony (pełna idempotencja wraz z
  `updated_at`), uzupełnianie wyłącznie pustych pól, izolacja trenerów,
  `--dry-run` niczego nie zapisuje, klient nie widzi notatki roboczej,
  odmowa wyboru trenera w komendzie. Do tego 6 testów czystej logiki
  raportu po stronie frontendu (`npm run test:helpers`).

## 0.35.1 — 2026-08-18

**Przegląd mutacyjny bramki spójności — i dwie luki, które znalazł.**

Bramka z 0.35.0 miała testy wstrzykujące błąd. Pytanie, czy te testy
faktycznie coś pilnują, wymaga odwrócenia próby: **zepsuć kontrolę i
sprawdzić, czy testy się zaczerwienią**. `tools/mutacje.py` robi to
automatycznie — psuje `spojnosc.py` na siedem sposobów, po każdym
uruchamia testy i przywraca oryginał.

* **Luka 1: próg `PROG_TRAS` nie był chroniony.** Usunięcie
  zabezpieczenia, które ma nie dopuścić do cichej śmierci kontroli tras,
  nie wywracało ani jednego testu. Dopisany
  `test_prog_tras_zapala_sie_gdy_kontrola_widzi_za_malo`.
* **Luka 2: kontrola dokumentów bez testu.** Zamiana jej w atrapę
  przechodziła bez śladu. Dopisany
  `test_wykrywa_martwy_odnosnik_do_dokumentu` (porównuje przyrost uwag, bo
  kopia repozytorium z natury nie ma wszystkich dokumentów).
* Po naprawie: **7 z 7 mutacji wykrytych**, 9 testów bramki.
* `apps/dzik-os/tools` objęte lintem w CI — katalog był poza kontrolą
  jakości, a leży w nim narzędzie pilnujące jakości.
* `KOORDYNACJA.md` §1 opisuje przegląd mutacyjny i jego wynik. Zasada:
  dokładając kontrolę, dołóż test, który ją psuje — i uruchom przegląd,
  żeby sprawdzić, czy ten test cokolwiek znaczy.

## 0.35.0 — 2026-08-18

**Porządki: bramka przeciw kolizjom między równoległymi rundami.**
Pełny opis mechanizmu, rezerwacji zasobów globalnych i tego, czego bramka
NIE złapie: `docs/KOORDYNACJA.md`.

* **Problem, który to rozwiązuje.** Rundy bywają rozwijane równolegle, w
  osobnych kopiach repozytorium; każda widzi kod sprzed swojego startu i
  nie wie, co robią pozostałe. Git wykrywa kolizje **tekstu** — kolizje
  **znaczenia** przechodzą przez scalenie bez jednego konfliktu.
* **`tools/spojnosc.py` — sześć kontroli, każda z prawdziwego błędu:**
  powtórzony numer migracji (zdarzyło się przy nr 24), ta sama wersja w
  CHANGELOG-u przydzielona dwa razy (0.29.0), **trasa statyczna
  przesłonięta przez wcześniejszą parametryzowaną** (`import-schema` w
  0.32.0 — kod poprawny, funkcja nieosiągalna), router bez
  `include_router`, plik `scripts/test-*.mjs` spoza `test:helpers` (czyli
  test, który nigdy się nie uruchamia), martwy odnośnik do dokumentu.
* **Bramka w CI** (`dzik-os-ci.yml`) — kolizja nie ma jak przejść
  niezauważona, nawet gdy nikt o niej nie pamięta.
* **Kontrola, która sama nie zgnije.** Pierwsza wersja kontroli tras
  widziała **35 z około 200 tras** (ta wersja FastAPI nie spłaszcza
  dołączonych routerów do `app.routes`) i przechodziła zawsze. Wyszło to
  dopiero przy próbie z celowo wstrzykniętym błędem. Stąd dwa
  zabezpieczenia: `PROG_TRAS` wywraca kontrolę, gdy widzi podejrzanie mało
  tras, a `tests/test_spojnosc.py` **wstrzykuje każdy z tych błędów** i
  sprawdza, że kontrola się zapala — oraz że przy poprawnej kolejności
  milczy.
* **Rezerwacja zasobów globalnych** (numer migracji, numer wersji, lista
  plików) w tabeli w `KOORDYNACJA.md` — do wypełnienia PRZED pracą.
* **Wypisane wprost, czego bramka nie złapie:** sprzeczności logicznej
  między rundami (realny przypadek: jedna filtrowała płatności po
  `PENDING`, druga wprowadziła `OVERDUE` — scalenie po cichu wyłączyło
  przypomnienia o zaległościach), testu sprawdzającego nieaktualne
  założenie, dublującego się pomysłu. Przy scalaniu **czyta się obie
  zmiany**; bramka zdejmuje część mechaniczną, nie zastępuje czytania.
* **Brief dla pracy równoległej** — jeden zestaw ograniczeń w jednym
  miejscu, łącznie z wymogiem raportowania, **co uruchomiono i co widać**.
* Testy: 7 nowych (`tests/test_spojnosc.py`), w tym próba z wstrzykniętym
  błędem dla każdej kontroli.

## 0.34.0 — 2026-08-18

**Jedno „Dodaj do bazy" zamiast czterech paneli + zasada uruchomienia.**

* **Zakładka Ćwiczenia przestała witać gąszczem.** Były tam cztery
  niezależne drogi dodania pozycji: dwie rozwijane karty importu na samej
  górze (gotowa biblioteka, plik) plus formularz i odczyt z opisu/zdjęcia
  schowane gdzie indziej. Każda z osobna sensowna, razem — ściana.
  Teraz jest jedna karta z jednym pytaniem, które trener naprawdę ma w
  głowie: **„skąd bierzesz to ćwiczenie?"** — *Wpiszę sam · Mam opis lub
  zdjęcie · Mam plik z bazą · Weź gotową bibliotekę*. Widoczna jest
  wyłącznie wybrana droga.
* **Nic nie zostało usunięte ani zmienione funkcjonalnie.** Wszystkie
  cztery drogi działają jak dotąd, łącznie z podglądem przed zapisem,
  cofaniem importu i wzorem pliku. Zmieniło się tylko to, że nie widać ich
  naraz. `SheetImportPanel` i `LibraryImport` dostały tryb `embedded`
  (bez własnej ramki i „Rozwiń"), a `DescriptionAssist` — `defaultOpen`,
  żeby wybór „mam opis lub zdjęcie" nie kazał klikać drugi raz w to samo.
* **Zasada uruchomienia** (`docs/ZASADA_URUCHOMIENIA.md`, ustalona przez
  właściciela produktu): zupełnie nowa funkcja nie jest gotowa, dopóki nie
  została **uruchomiona w działającej aplikacji** i obejrzana. Przechodzące
  testy są warunkiem wstępnym, nie dowodem. Dokument podaje, co konkretnie
  jest dowodem dla każdego rodzaju zmiany (ekran, endpoint, komenda,
  ścieżka nieodwracalna, integracja) i wymaga wpisania do raportu **co
  zostało kliknięte i co widać** — a gdy czegoś sprawdzić się nie da,
  powiedzenia tego wprost. Odnośnik z `README.md`.
* **Przeklik tej rundy** (zgodnie z powyższą zasadą): jedna karta „Dodaj do
  bazy" na ekranie, zero starych kart importu; wybór „mam plik" pokazuje
  pole pliku i wzór, a podgląd zwraca raport; przełączenie na „gotową
  bibliotekę" chowa panel plikowy; „wpiszę sam" otwiera pusty formularz ze
  zwiniętym odczytem; „mam opis lub zdjęcie" otwiera formularz z odczytem
  już rozwiniętym i dostępnym zdjęciem; zapis obiema drogami kończy się
  201 i pozycja jest odnajdywalna na liście. Bez błędów JS.

## 0.33.0 — 2026-08-18

**Nic nie ginie bezpowrotnie: punkt przywracania dla importu + sprawdzona
procedura odtworzenia kopii zapasowej.** Pełny opis pięciu warstw
odzyskiwania i uczciwa lista tego, czego odzyskać się nie da:
`docs/ODZYSKIWANIE.md`.

* **Zamknięta realna dziura.** Plany i diety mają niemutowalną historię
  wersji, ale **ćwiczenia jej nie mają**. Import w trybie `ZASTAP`
  (dodany w 0.32.0) nadpisywał opis techniki napisany przez trenera i nie
  było jak go odzyskać — jeden zły plik kasował pracę na zawsze. Migawka
  zdejmowana PRZED zapisem zamyka tę dziurę.
* **„Cofnij ten import".** Nowa tabela `import_snapshots` (migracja nr 25,
  czysto addytywna) trzyma stan sprzed importu wyłącznie tych pozycji,
  których import dotknął. `POST /api/coach/imports/{id}/undo` przywraca:
  pozycje zmienione wracają pole po polu, pozycje **utworzone** zostają
  **zarchiwizowane, nigdy usunięte**, a szablon wraca przez **nową wersję**
  z dawną treścią — historia, łącznie z samym importem i jego cofnięciem,
  zostaje w całości.
* **Cofnięcie jest jednorazowe i ograniczone do 20 ostatnich importów.**
  Starsza migawka przywracałaby stan sprzed późniejszych, świadomych zmian
  trenera, o których nic nie wie — to byłaby cicha strata, nie ratunek.
* **Kontrakt pilnowany przez kod.** `_assert_snapshot_covers_import()`
  wywraca import modułu, jeśli import zapisuje pole, którego migawka nie
  obejmuje. Dołożenie kolumny nie może po cichu wyłączyć dla niej cofania.
* **Interfejs mówi, co zrobi cofnięcie, PRZED kliknięciem** („3 pozycje
  wrócą do wartości sprzed importu; 2 nowe zostaną zarchiwizowane — nie
  usunięte; można to zrobić tylko raz"). Panel importu ma też listę
  ostatnich importów z przyciskiem „Cofnij" i oznaczeniem już cofniętych.
  Podgląd i import bez zmian **nie tworzą** punktu przywracania — przycisk
  się wtedy nie pojawia, bo obiecywałby coś, czego nie ma.
* **Procedura odtworzenia kopii zapasowej — przećwiczona, nie
  zadeklarowana.** Na pełnej bazie (7 kont, 256 ćwiczeń, 4 plany, pliki
  uploadów) skasowano bazę, audyt i uploady, po czym odtworzono je z
  archiwum: komplet danych zgodny ze stanem sprzed skasowania, skasowany
  plik uploadu z powrotem na dysku, `verify_chain() = True`.
* **Nazwana słabość, której nie ukrywamy:** archiwa kopii zapasowych leżą
  na tym samym wolumenie, który mają chronić. Przy utracie wolumenu zostaje
  wyłącznie snapshot Fly, którego odtworzenia jeszcze nie ćwiczyliśmy.
  Wyniesienie kopii poza Fly czeka na decyzję o dostawcy magazynu.
* Audyt: `IMPORT_UNDONE` (identyfikator migawki, rodzaj, plik, tryb i
  liczby — nigdy treść wierszy).
* Testy: 10 nowych po stronie backendu i 5 nowych testów pomocniczych
  frontendu, w tym jawny test odwracalności trybu `ZASTAP` pole po polu.

## 0.32.0 — 2026-08-18

**Import własnej bazy danych z pliku — ćwiczenia i szablony treningowe.**
Trener przygotowuje bazę tam, gdzie mu wygodnie (arkusz, eksport z innego
narzędzia, czyjaś praca) i wgrywa ją do aplikacji. Pełna specyfikacja
formatu — kolumny, słowniki, limity, reguły — jest w `docs/IMPORT_BAZ.md`.

* **Dwie bazy, jeden mechanizm.** `backend/dzik_os/sheet_import.py` czyta
  **CSV (UTF-8) i XLSX**, wykrywa separator, normalizuje nagłówki (wielkość
  liter, polskie znaki, spacje i myślniki nie mają znaczenia) i przyjmuje
  wypisane aliasy kolumn (`name`, `how_to`, `weekday`…). Kolejność kolumn
  jest dowolna; kolumn spoza kontraktu nie czytamy, ale ich **nazwy trafiają
  do raportu** — literówka w nagłówku ma być widoczna, a nie cicha.
* **Ćwiczenia:** 21 kolumn, 3 wymagane (`nazwa`, `grupa`, `opis`).
  Dopasowanie do istniejącej pozycji po znormalizowanej nazwie, także wśród
  **zarchiwizowanych** — inaczej import robiłby duplikat czegoś świadomie
  schowanego. Dwa tryby: `UZUPELNIJ` (domyślny — wypełnia wyłącznie puste
  pola, opis techniki trenera zostaje nietknięty) i `ZASTAP`. **Pusta
  komórka nigdy nie kasuje danych — w obu trybach.**
* **Szablony treningowe:** jeden wiersz = jedno ćwiczenie w jednym dniu
  jednego szablonu; grupowanie po kolumnie `szablon`, kolejność z
  `dzien_nr`/`pozycja` albo z kolejności w pliku. Nazwy ćwiczeń są
  **dopasowywane do aktywnej bazy trenera** i zapisywane jako miękkie
  odniesienie `exercise_id` — ten sam kontrakt, co przy ręcznym układaniu
  planu. Brak dopasowania **nie jest błędem**: pozycja wchodzi z samą nazwą
  i trafia na listę w raporcie.
* **Historia jest nienaruszalna.** Szablon o tej samej nazwie nie jest
  nadpisywany — dostaje **nową wersję** z powodem wskazującym plik, a
  poprzednie wersje zostają. Szablon o identycznej treści nie dostaje pustej
  wersji „bo import”.
* **Próba przed zapisem i brak zgadywania** — te same reguły, co przy OCR,
  czytaniu opisu i imporcie gotowej biblioteki. `dry_run=true` (domyślne)
  **nie dotyka ani jednego obiektu sesji**. Wartość spoza zamkniętego
  słownika albo pomija wiersz z podaniem przyczyny (kolumny wymagane), albo
  zostawia pole puste i ląduje w raporcie. Nazwa zbiorcza („góra ciała”) jest
  odrzucana, nie zaokrąglana do najbliższej partii.
* **Podróż w obie strony.** `GET .../export-file` eksportuje bazę w
  **dokładnie tym formacie**, który przyjmuje import (prawo wyjścia + masowa
  edycja: pobierz → popraw w arkuszu → wgraj). Testy pilnują, że eksport
  wgrany z powrotem daje **zero zmian**. Jest też wzór pliku do pobrania —
  i test, że sam wzór przechodzi import bez błędu.
* **Interfejs.** Wspólny `SheetImportPanel` (`frontend/src/components.tsx`)
  w panelu trenera: Baza wiedzy → Ćwiczenia oraz Szablony planów. Opis
  kolumn i słowników w aplikacji buduje się z `GET .../import-schema`, czyli
  z tego samego kontraktu, który wykonuje import — nie ma jak się rozjechać.
  Zły format, zbyt duży i pusty plik są odrzucane **przed wysyłką**, z
  nazwaniem przyczyny.
* **Bez migracji.** Zero zmian w schemacie bazy — import korzysta z
  istniejących kolumn (m.in. proweniencji z migracji nr 22 i 24). Nowe
  pozycje dostają `source_kind = IMPORTED` i nazwę pliku w `source_ref`;
  **istniejące pozycje nazwy pliku nie dostają** — nie pochodzą z niego, a
  doklejanie jej psułoby idempotencję.
* **Audyt.** `EXERCISES_IMPORTED` / `PLAN_TEMPLATES_IMPORTED` oraz
  `EXERCISES_EXPORTED` / `PLAN_TEMPLATES_EXPORTED`; payload zawiera nazwę
  pliku, tryb i liczby — nigdy treści wierszy.
* Testy: 26 nowych po stronie backendu (`tests/test_sheet_import.py`) i 11
  nowych testów pomocniczych frontendu (`scripts/test-sheet-import.mjs`).

## 0.31.0 — 2026-08-18

**Import własnej biblioteki ćwiczeń trenera (120 pozycji) do bazy
ćwiczeń.** Trener przekazał swoją bibliotekę w arkuszu kalkulacyjnym;
zamiast przepisywać 120 pozycji ręcznie, klika „Importuj bibliotekę
ćwiczeń”, ogląda raport i zatwierdza. Pełny opis mapowania, uruchomienia
na produkcji i wycofania: `docs/BAZA_CWICZEN.md` §11.

* **Arkusz zamieniony na moduł danych, nie na binarny blob w repo.**
  `backend/dzik_os/exercise_catalog_v2.py` (wzorzec `food_catalog_data.py`)
  jest czytelną i diffowalną postacią pliku
  `DZIK_OS_Biblioteka_Cwiczen_V2_PL_120.xlsx` przekazanego 2026-08-18.
  Sam plik xlsx **nie jest commitowany**; nazwa i data przekazania są
  zapisane jako proweniencja w nagłówku modułu.
* **Powiedziane wprost, co w źródle jest szablonem.** Kolumny
  faktograficzne (nazwy, kategoria, mięśnie, sprzęt, poziom, rodzaj,
  wzorzec, tagi) są unikalne per ćwiczenie. Kolumny **opisowe są
  szablonowe**: na 120 wierszy przypada **17 różnych opisów wykonania, 2
  opisy oddychania i 5 zestawów błędów** — technika jest opisana ogólnie
  dla wzorca ruchu, nie pod konkretne ćwiczenie. Dlatego szablony leżą w
  module jako nazwane stałe (szablonowość widać w kodzie), a każda nowo
  utworzona pozycja dostaje notatkę roboczą „opis ogólny”.
* **Notatka „do dopracowania” jest informacją trenera, nie oceną dla
  klienta.** `review_reason` widać w panelu trenera (karta ćwiczenia i
  edytor, z przyciskiem „Zdejmij notatkę”). Klient **nie dostaje tego
  pola w żadnej odpowiedzi API** — dla niego wyglądałoby jak ocena
  jakości ćwiczenia wystawiona przez system, a system tu niczego nie
  ocenia.
* **ZASADA NADRZĘDNA ta sama co przy czytaniu opisu: nie zgadujemy.**
  Nazwa mięśnia, której nie da się jednoznacznie zmapować, zostaje
  **pusta** i trafia na jawną listę w raporcie. Nie mapujemy nazw
  zbiorczych (`barki`, `obręcz barkowa`, `górne plecy`, `nogi` —
  wskazują na kilka kluczy naraz) ani mięśni, dla których słownik nie ma
  klucza (`mięsień ramienny`, `obły większy`, `zębaty przedni`,
  `piszczelowy przedni`). W efekcie 8 pozycji trafia do bazy bez mięśni
  głównych — i to jest poprawny wynik, nie brak.
* **Wzorzec ruchu: 48 wariantów źródła → nasze 13, jawną tablicą.**
  W tablicy są wyłącznie przypisania, które da się obronić. Wariant
  nierozpoznany dostaje `IZOLACJA` **tylko wtedy**, gdy źródło samo
  nazywa ćwiczenie izolowanym; w przeciwnym razie pole zostaje puste.
  Stąd 12 pozycji bez wzorca (`antywyprost` to nie antyrotacja, `chwyt
  izometryczny` to nie noszenie) — nie upychamy ich na siłę.
* **Poziom podwójny → NIŻSZY z pary** (25 wierszy ma
  „początkujący/średniozaawansowany”). Świadoma decyzja: zawyżony poziom
  odsiewa ćwiczenie z wyszukiwarki komuś, kto spokojnie może je robić.
* **Praca trenera jest nienaruszalna.** W ćwiczeniu, które już jest w
  bazie, import **uzupełnia wyłącznie puste pola** — nigdy nie nadpisuje
  opisu pisanego pod konkretne ćwiczenie. Import jest w pełni
  **idempotentny**: drugi przebieg to 0 nowych, 0 zmian i nietknięte
  `updated_at`.
* **Dwie drogi uruchomienia, jedna logika.** Komenda
  `python -m dzik_os.import_exercises [--coach <e-mail>] [--dry-run]`
  (wzorzec `dzik_os.backup`; bez `--coach` odmawia wyboru, gdy trenerów
  jest więcej niż jeden) oraz przycisk w panelu trenera z **podglądem
  raportu przed zatwierdzeniem** (`dry_run` domyślnie **true**). Import
  zawsze idzie do katalogu **zalogowanego** trenera — katalog innego
  trenera nie zmienia się o ani jeden wiersz.
* **Raport jak przy imporcie CSV produktów:** `{created, enriched,
  skipped, unmapped_muscles, unmapped_patterns, errors}`, z liczbą
  wystąpień i przykładami przy każdej nierozpoznanej wartości. Błąd
  pojedynczej pozycji nie przerywa importu.
* **Proweniencja zapisana w danych.** `source_kind` zyskał wartość
  `IMPORTED`, a nowa kolumna `source_ref` niesie nazwę biblioteki i datę
  przekazania — pozycje z importu da się odróżnić od pisanych ręcznie
  jednym zapytaniem, co jest też podstawą planu wycofania.
* **Migracja nr 24** (numer 23 zarezerwowany dla równoległej rundy):
  cztery kolumny NULLable na `exercises` — `name_en`, `tags_json`,
  `source_ref`, `review_reason`. Czysto addytywna, bez backfillu; plan
  wycofania w `docs/BAZA_CWICZEN.md` §11.7.
* **Nazwa angielska i tagi w wyszukiwarce i edytorze.** `q=bench press`
  znajduje „Wyciskanie sztangi na ławce poziomej”; rodzaj ćwiczenia
  (wielostawowe/izolowane/…) mieszka w tagach, bez rozbudowywania modelu
  o kolejną kolumnę.
* **Seed zasiewa pełny katalog** (155 pozycji startowych + 101 nowych z
  biblioteki) tą samą funkcją, której używa produkcja — demo i produkcja
  dostają dokładnie to samo.
* **Testy:** nowy `backend/tests/test_exercise_import.py` (23 przypadki):
  mapowanie form anatomicznych, odmowa mapowania nazw zbiorczych, poziom
  podwójny → niższy, wzorzec nierozpoznany → puste + raport, import na
  czystą bazę (120 nowych), import powtórzony (pełna idempotencja wraz z
  `updated_at`), uzupełnianie wyłącznie pustych pól, izolacja trenerów,
  `--dry-run` niczego nie zapisuje, klient nie widzi notatki roboczej,
  odmowa wyboru trenera w komendzie. Do tego 6 testów czystej logiki
  raportu po stronie frontendu (`npm run test:helpers`).
## 0.30.0 — 2026-08-18

**Asystent trenera: wspólna warstwa + pierwsze zadanie „szkic planu z
własnej bazy ćwiczeń".** Architektura, rejestr zadań, zamknięte słowniki,
bramkowanie zgód, granica „asystent proponuje, trener decyduje", płynność
i plan wycofania migracji nr 23: `docs/ASYSTENT_TRENERA.md`.

* **Jedna warstwa zamiast wywołania modelu w każdym oknie**
  (`backend/dzik_os/coach_assistant.py`). Zadanie to **deskryptor**
  (klucz, schemat wejścia, schemat wyjścia, prompt systemowy, czy wolno
  użyć danych klienta, limit, ścieżka lokalna). Dołożenie kolejnego
  zadania (progresja planu, opis szablonu) to dopisanie deskryptora —
  bez dotykania routera, kolejki, magistrali, liczników i proweniencji.
  Dzięki temu jest jedno miejsce walidacji, jedno miejsce sprawdzania
  zgód i jedno miejsce do audytu.
* **Zamknięte słowniki.** Model wskazuje wyłącznie `exercise_id` z bazy
  TEGO trenera (status ACTIVE — ten sam kontrakt co
  `_validate_exercise_refs`), a nazwy, tempo i linki bierze aplikacja
  z bazy. Identyfikator spoza słownika odrzuca **całą** odpowiedź: jedno
  ponowienie, potem jawny komunikat z listą niepoprawnych wartości.
  **Nigdy nie podmieniamy po cichu na „najbliższe" ćwiczenie** — to
  byłoby zgadywanie decyzji trenera na planie żywego człowieka.
* **Asystent NIE podaje kilogramów.** W schemacie wyjścia nie ma pola na
  ciężar (granica strukturalna, nie tylko zapis w promptcie), a jednostka
  masy przemycona w innym polu odrzuca całą odpowiedź. Proponowane są
  serie, zakresy powtórzeń, tempo i przerwa; obciążenie zostaje decyzją
  trenera — napisane wprost w interfejsie i w docs.
* **Nic nie zapisuje się samo.** Żaden endpoint asystenta nie tworzy
  planu ani wersji planu (potwierdzone testem liczącym wersje). Wynik to
  propozycja obok edytora; zapis idzie zwykłą, wersjonowaną ścieżką
  z powodem zmiany. `POST /tasks/{id}/applied` zapisuje wyłącznie
  **proweniencję** (że powstało z pomocą asystenta i jakim silnikiem).
* **Zgody bramkowane per RODZAJ DANYCH.** Zadanie na zasobach trenera
  (baza ćwiczeń, szablon bez klienta) nie wymaga żadnej zgody
  podopiecznego. Zadanie z danymi konkretnego klienta wymaga jego
  aktywnej zgody `funkcje_ai` — bez niej pola profilu (urazy,
  ograniczenia ruchu) **w ogóle nie powstają**, a interfejs mówi o tym
  wprost. Do dostawcy nie idzie żaden identyfikator osoby, e-mail ani
  nazwisko; lista pól profilu, które wolno wysłać, jest zamknięta.
* **Płynność jako kryterium akceptacji.** Zadanie idzie przez tabelę
  `assistant_tasks` + **istniejącą** magistralę SSE (`assistant.task`,
  sam status bez treści) z odpytywaniem zapasowym, więc edytor planu
  pozostaje w pełni używalny w trakcie generowania. Widoczny postęp,
  „trwa dłużej niż zwykle" po 8 s, anulowanie jednym kliknięciem, twardy
  timeout 60 s zamiast wiszącej kręciołki. Propozycja pojawia się OBOK
  planu, wstawienie to jedno kliknięcie, a zaraz po nim dostępne jest
  **„cofnij wstawienie"** (migawka stanu edytora). Domyślnie dni są
  DOKŁADANE, nigdy nie kasują pracy trenera. Bez przeładowań i skoków:
  `aria-live`, etykiety `for`/`id`, pełna obsługa klawiaturą. Powtórne
  kliknięcie nie mnoży zadań (klucz idempotencji z treści formularza),
  a szkic roboczy formularza przeżywa utratę sieci (wzorzec z P11).
* **Bez klucza API funkcja NIE jest ślepym zaułkiem.** Gdy dostawca
  modelu jest niedostępny (albo limit wyczerpany, albo odpowiedź
  odrzucona), ten sam przycisk otwiera **ścieżkę lokalną**: gotowy
  podział tygodnia zależny od liczby dni, wstępnie odfiltrowana baza
  ćwiczeń dla każdego wzorca ruchu (sprzęt, poziom), liczba pozycji
  wyliczona z czasu sesji i lista szablonów do skopiowania. Komunikat
  zawsze mówi, który tryb działa i dlaczego — brak dostawcy to STAN,
  nie awaria.
* **Wyszukiwanie ćwiczeń przy dużym katalogu** (baza rośnie do ~250
  pozycji): skrót **„ostatnio używane"** nad wynikami
  (`GET /api/coach/exercises/recent` — do 12 pozycji wyznaczonych
  z najświeższych wersji planów tego trenera, wyłącznie własne i aktywne,
  bez informacji o kliencie; widoczny tylko przy pustym wyszukiwaniu),
  pełna **obsługa klawiaturą** (fokus w polu wyszukiwania po otwarciu,
  strzałki po wynikach z zawijaniem, Enter dodaje, Escape zamyka i wraca
  fokusem do przycisku) oraz **czytelny licznik** („Znaleziono 84 —
  pokazano 20, zostało 64…") z konkretną podpowiedzią przy zerze trafień.
* **Migracja nr 23** (jedna krotka, wyłącznie addytywna): tabela
  `assistant_tasks` — klucz zadania, właściciel, status, **zredagowane**
  wejście (parametry, nigdy treść urazów), wynik, silnik, powód trybu,
  błąd, czasy, klucz idempotencji, proweniencja. Zero ALTER-ów, wszystkie
  kolumny NULLable. Plan wycofania w `docs/ASYSTENT_TRENERA.md` §11.
* **Prywatność.** Ani wejście, ani propozycja nie trafiają do logów,
  metryk i audytu — audyt notuje sam fakt (zadanie, silnik, liczba dni,
  czas). Koszty w istniejących licznikach `ai_usage_counters` (cecha
  `coach_assistant`), limit dzienny zadań na konto, limit kolejki.
  Cudze zadanie i cudze ćwiczenie = 404; klient i administrator dostają
  403 (asystent to narzędzie trenera).
* **Znane ograniczenia** (spisane w `docs/ASYSTENT_TRENERA.md` §12):
  kolejka żyje w pamięci jednego procesu (restart porzuca zadania w toku);
  brak automatycznego czyszczenia starych zadań; ścieżka lokalna nie zna
  urazów; brak progresji planu w czasie; katalog wysyłany do modelu jest
  przycięty do 120 pozycji; uzasadnienie dnia zostaje w panelu (plan nie
  ma pola na taki komentarz); „ostatnio używane" liczą się z 60
  najświeższych wersji planów.
* Testy: `backend/tests/test_coach_assistant.py` (26 — odrzucenie
  nieistniejącego i cudzego `exercise_id` bez cichej podmiany, ćwiczenie
  zarchiwizowane poza słownikiem, brak pola na ciężar i odrzut kilogramów,
  poprawna propozycja na atrapie dostawcy, minimalizacja wysyłanych
  danych, brak dostawcy → ścieżka lokalna z powodem, pusta baza jako
  czytelny stan, zadanie bez klienta bez zgody, dane klienta bez zgody
  pomijane i powiedziane wprost, dane klienta ze zgodą, 403 dla klienta
  i admina, cudze zadanie 404, klient spoza relacji 404, zero zapisów
  w planach, proweniencja po zatwierdzeniu, idempotencja, anulowanie,
  limit dzienny, brak treści w logach/metrykach/wejściu, liczniki
  kosztów, migracja nr 23 na starej bazie),
  `backend/tests/test_exercise_recent.py` (8) oraz helpery frontendu:
  `frontend/scripts/test-assistant-utils.mjs` (12) i
  `test-exercise-picker.mjs` (9).

## 0.29.0 — 2026-08-18

**Maszyna produkcyjna: 512 MB → 1 GB RAM** (`fly.toml`, `[[vm]] memory`).

Decyzja na podstawie pomiaru, nie przeczucia: aplikacja zajmuje 124 MB po
starcie i 129 MB po typowym ruchu klienta, a obróbka jednego zdjęcia
2560×1920 w Pillow kosztuje ~75 MB szczytowo (OCR na zmniejszonym obrazie
tyle samo). Pojedyncza operacja mieściła się w 512 MB z zapasem — ryzykiem
był zbieg zdarzeń: upload zdjęć raportu (każde przez Pillow) w tym samym
momencie co rozpoznawanie tekstu, przy stale działającej pętli przypomnień
i otwartych połączeniach wiadomości na żywo. Fly nie ma swapa, więc
przekroczenie limitu to ubicie maszyny i przestój, a nie spowolnienie.
Koszt zmiany: ok. 2-3 USD/mies.

Limity OCR (kolejka jednoslotowa, zmniejszanie obrazu, timeout) zostają
bez zmian — chronią czas odpowiedzi, nie tylko pamięć. Kolejność przy
dalszym skalowaniu bez zmian: najpierw pamięć, potem więcej slotów.
Zaktualizowane: `fly.toml`, `DEPLOYMENT.md` §4, `OCR.md` §2,
`DEFERRED_FEATURES.md`.

## 0.28.0 — 2026-08-18

**Auto-uzupełnianie tabeli parametrów ćwiczenia z wklejonego opisu.**
Trener wkleja jednolity opis ćwiczenia, klika „Uzupełnij z opisu” i
dostaje gotową propozycję pól do zatwierdzenia — zamiast wpisywać
kilkanaście pól ręcznie przy każdej ze 150 pozycji bazy. Pełny opis
parsera, słownik synonimów, oba tryby, plan wycofania migracji nr 22 i
znane ograniczenia: `docs/BAZA_CWICZEN.md` §10.

* **Silnik lokalny działa zawsze, tryb rozszerzony włącza się sam.**
  Domyślnie czyta deterministyczny parser polskiego tekstu
  (`dzik_os/exercise_parser.py`) — bez klucza, bez internetu, bez bazy.
  Gdy operator skonfiguruje dostawcę modelu, ten sam opis idzie trybem
  rozszerzonym (dokładniejsza struktura, zwłaszcza z tekstu ciągłego bez
  nagłówków). **Kod wywołujący nie ma przełącznika** — wybiera
  `exercise_parser_ai.resolve_mode`, a widok tylko pokazuje tryb i powód.
* **ZASADA NADRZĘDNA: nigdy nie zgadujemy.** Pole nierozpoznane zostaje
  PUSTE i trafia na jawną listę „nie udało się odczytać”. Stąd świadome
  ograniczenia: „barki” bez określenia aktonu nie są mapowane (trzy różne
  klucze, żaden domyślny), „podstawowe ćwiczenie” to nie poziom
  początkujący, a „2026” w notatce to nie tempo. Nazwa spoza słownika
  partii mięśniowych jest ignorowana, nie mapowana na najbliższą.
* **Co rozpoznaje parser lokalny:** mięśnie (słownik synonimów mapowany na
  21 kluczy `MUSCLE_LABELS`, odporny na odmianę i polskie znaki przez
  `muscles.fold()`), podział na główne/pomocnicze **po markerach w
  tekście** („pracują głównie”, „wspomagająco”, „dodatkowo angażuje”),
  sprzęt, poziom, wzorzec ruchu, kroki techniki (listy numerowane i
  punktowane albo zdania sekcji „wykonanie/technika/przebieg”), błędy,
  wskazówki, bezpieczeństwo, warianty łatwiejszy/trudniejszy, tempo,
  oddech i efekt. **Brak markera podziału = wszystko do głównych + jawna
  flaga „do potwierdzenia”** (dzielenie listy na oko byłoby zgadywaniem).
* **Wynik to ZAWSZE propozycja.** `POST /api/coach/exercises/parse-description`
  (rola COACH) nie zapisuje ani jednego ćwiczenia — zwraca propozycję
  pól, użyty tryb, powód trybu oraz dwie **rozłączne** listy: pól
  nierozpoznanych i pól wymagających potwierdzenia. Zapis następuje
  wyłącznie istniejącym endpointem tworzenia/edycji, po zatwierdzeniu
  przez trenera.
* **Edytor bazy ćwiczeń: panel „Uzupełnij z opisu”** z podglądem
  propozycji (co zostanie wstawione, czego nie rozpoznano, który tryb
  zadziałał). **Domyślnie uzupełniamy wyłącznie PUSTE pola** — praca
  trenera nie znika przez jedno kliknięcie; nadpisanie to osobny,
  świadomy przełącznik. Dostępność jak w rundzie P10 (etykiety `for`/`id`,
  `aria-live` na pojawienie się propozycji).
* **Synergia z OCR bez drugiego mechanizmu OCR.** Przycisk „Przepisz ze
  zdjęcia” otwiera istniejący komponent `OcrCapture`; zatwierdzony tekst
  dokleja się na końcu pola opisu. Ścieżka: zdjęcie kartki lub strony z
  książki → tekst → wypełniona tabela.
* **RÓŻNICA W BRAMKOWANIU ZGÓD względem OCR (świadoma).** Opis ćwiczenia
  to **własne know-how trenera**, nie dane zdrowotne klienta — klient w
  tym przepływie w ogóle nie występuje. Bramką nie jest więc zgoda
  `funkcje_ai` podmiotu danych (ta dotyczy danych klienta), tylko
  dostępność dostawcy i jawna decyzja trenera (świadome kliknięcie).
  Nowy cel przetwarzania w rejestrze czynności (poz. 14): trener jako
  podmiot danych własnego tekstu, dostawca modelu jako procesor —
  wyłącznie przy włączonym trybie rozszerzonym. Gdyby do tego przepływu
  miał kiedyś trafić tekst opisujący konkretnego klienta, bramkowanie
  MUSI wrócić do `authz.ai_features_consent_active`.
* **Minimalizacja i twardy kontrakt wyjścia.** Do dostawcy jedzie
  WYŁĄCZNIE wklejony tekst opisu — bez identyfikatorów, nazwisk i danych
  klientów (funkcja przyjmuje jeden argument i nie ma jak przemycić nic
  poza nim). Odpowiedź modelu przechodzi schemat `extra="forbid"`, w
  którym dozwolone są tylko klucze ze słownika mięśni, poziomów i wzorców
  — model **strukturalnie nie może wymyślić nowej wartości**; jedna
  wartość spoza słownika odrzuca całą odpowiedź, potem jedno ponowienie i
  zejście na silnik lokalny. Limity i liczniki jak w pozostałych funkcjach
  (`ai_usage_counters`, cecha `exercise_parse`). Ani jeden znak opisu nie
  trafia do logów i metryk.
* **Migracja nr 22** (jedna krotka, wyłącznie addytywna, obie kolumny
  NULLable): proweniencja ćwiczenia — `source_kind`
  (MANUAL / TEXT_PARSED / AI_ASSISTED, **NULL = historyczne, nie wiemy**)
  i `source_engine` (LOCAL/EXTENDED, nigdy nazwa dostawcy). Zwykła edycja
  nie kasuje zapisanej wcześniej proweniencji. Numer 21 zarezerwowany dla
  równoległej rundy — luka w numeracji jest świadoma.
* **Testy:** `backend/tests/test_exercise_parser.py` (42 przypadki) —
  opisy z nagłówkami i bez, synonimy i polskie znaki, podział po
  markerach, brak markera → flaga do potwierdzenia, pola nierozpoznane
  puste i wypisane, tekst bez sensu → pusta propozycja bez błędu, nieznana
  partia ignorowana, tryb rozszerzony na atrapie dostawcy (poprawna
  odpowiedź / wartość spoza słownika → odrzucenie i zejście na lokalny /
  brak odpowiedzi), klient 403, brak zapisu, brak treści w logach i
  metrykach, proweniencja przy zapisie, migracja nr 22 na starej bazie.
  Frontend: `scripts/test-exercise-parser.mjs` (9 przypadków scalania).

## 0.27.0 — 2026-08-18

**Przepisywanie tekstu ze zdjęcia (OCR) w dwóch trybach.** Pełna
architektura, limity maszyny, format propozycji, prywatność i plan
wycofania migracji nr 20: `docs/OCR.md`.

* **Silnik lokalny działa zawsze, tryb rozszerzony włącza się sam.**
  Domyślnie rozpoznaje Tesseract uruchomiony na naszym serwerze (`pol+eng`,
  wywoływany przez `subprocess` — uzasadnienie wyboru zamiast `pytesseract`
  w `docs/OCR.md` §1). Gdy operator skonfiguruje dostawcę modelu ORAZ
  podmiot danych ma aktywną zgodę `funkcje_ai`, to samo zadanie idzie
  trybem rozszerzonym (model widzenia, który dodatkowo **strukturyzuje**
  tabelę wartości odżywczych). **Kod wywołujący nie ma przełącznika** —
  wybiera `ocr_queue.resolve_mode`, a widok tylko pokazuje `mode` i powód.
* **Brak Tesseracta to STAN, nie awaria.** Środowisko testowe i
  deweloperskie nie ma binarki: `GET /api/ocr/status` zwraca wtedy
  `engine_available: false` z powodem po polsku, a zlecone zadanie kończy
  się statusem FAILED i kodem `ENGINE_UNAVAILABLE` — nigdy wyjątkiem ani
  500. Cały zestaw testów przechodzi bez Tesseracta (przebieg testowany na
  atrapie silnika; obecność binarki to osobny, pomijany test).
* **Kolejka jednoslotowa pod 512 MB RAM** (Fly.io shared-cpu-1x): jeden
  wątek roboczy + semafor(1), poczekalnia 20 zadań (potem czytelne 429),
  zmniejszenie obrazu do 1600 px w skali szarości PRZED rozpoznaniem,
  twardy limit 25 s z zabiciem procesu, limit wejścia 8 MB i limit dzienny
  na konto. Endpoint oddaje identyfikator zadania (202), front odpytuje, a
  zdarzenie `ocr.task` (sam status, bez treści) idzie na **istniejącą**
  magistralę `realtime.bus`. W `docs/OCR.md` §2 wprost: przy większym
  ruchu maszynę trzeba podbić do 1 GB.
* **Wynik to ZAWSZE propozycja.** Człowiek widzi rozpoznany tekst obok
  zdjęcia, poprawia go i dopiero zatwierdza; samo rozpoznanie nie zapisuje
  niczego poza własnym wierszem zadania. Zapisane dane niosą proweniencję
  (źródło OCR + plik źródłowy + użyty silnik). Rezygnacja kasuje wiersz
  razem z tekstem.
* **Trzy zastosowania:** (a) **etykieta produktu** → wstępnie wypełniony
  formularz nowego produktu (zakresy walidacji te same co przy imporcie
  CSV; wartość nierozpoznana zostaje PUSTA, nigdy zgadywana ani
  wyzerowana, a UI wypisuje, czego nie odczytano); (b) **kartka z planem
  lub dietą** → tekst do edytora planu treningowego (nowy dzień: jedna
  linia = jedna pozycja do poprawienia, bez zgadywania serii i powtórzeń)
  albo do zaleceń w edytorze diety; (c) **skan dokumentu** → tekst
  przeszukiwalny przy `Document` (oryginał pliku bez zmian; można przepisać
  plik już wgrany do aplikacji albo sfotografować dokument na nowo) plus
  wyszukiwarka dokumentów działająca również po tym tekście.
* **Prywatność i konstytucja.** Cudzy plik i cudze zadanie = 404;
  zdjęcie klienta przechodzi przez te same bramki relacji i zgód co każdy
  inny plik. Do zewnętrznego dostawcy nie idzie nic bez zgody `funkcje_ai`
  (jedna reguła `authz.ai_features_consent_active` dla wszystkich funkcji
  AI), a gdy idzie — **wyłącznie zdjęcie i rodzaj zadania**, bez
  identyfikatorów, e-maili i nazwisk. Odpowiedź modelu jest walidowana
  ścisłym schematem: niezgodna = odrzucona, jedno ponowienie, potem wynik
  lokalny. Rozpoznany tekst NIGDY nie trafia do logów ani metryk (tylko
  liczniki i czasy), audyt notuje sam fakt rozpoznania, a zadania wchodzą
  do eksportu danych (`export_version` 1.5) i znikają przy usunięciu konta.
  Zaktualizowane: rejestr czynności (poz. 13), polityka prywatności
  (dostawca modelu jako procesor — tylko gdy włączony), `ZGODY_MODEL.md`
  i opis kategorii `funkcje_ai` (`CONSENT_DOC_VERSION` 2.1 → 2.2).
* **Migracja nr 20** (jedna krotka, wyłącznie addytywna, wszystkie kolumny
  NULLable): tabela `ocr_tasks` + `documents.ocr_text/ocr_engine/ocr_at` +
  `food_products.origin_kind/origin_file_id/origin_engine`. Plan wycofania
  w `docs/OCR.md` §3.
* **Frontend:** wspólny komponent `OcrCapture` („Przepisz ze zdjęcia") —
  zrobienie zdjęcia telefonem (`capture="environment"`), podgląd OBOK
  edytowalnego tekstu, zatwierdzenie, ponowienie, anulowanie, jawny stan
  „silnik niedostępny" i „tryb lokalny vs rozszerzony". Dostępność jak w
  P10 (etykiety `for`/`id`, `aria-live` na zmianę stanu zadania,
  `aria-expanded` na przełącznikach), kompresja obrazu po stronie klienta
  jak w P11 — wydzielona do `src/imageCompress.ts` i wspólna z raportem
  tygodniowym (jedna ścieżka zamiast dwóch kopii).
* **Znane ograniczenia** (spisane w `docs/OCR.md` §7): Tesseract słabo
  radzi sobie z **pismem odręcznym**; PDF nie jest obsługiwany (tylko
  zdjęcia); kolumna „na porcję" na etykiecie potrafi zostać wzięta zamiast
  „w 100 g" (dlatego wartości stoją obok zdjęcia do porównania); kolejka
  żyje w pamięci jednego procesu (restart porzuca zadania w toku); brak
  automatycznego czyszczenia starych zadań.
* Testy: `backend/tests/test_ocr.py` (26 — brak silnika jako czytelny stan,
  rozpoznanie na atrapie, propozycja pól produktu, odrzucenie niezgodnej
  odpowiedzi modelu, brak zgody `funkcje_ai` → tryb lokalny z powodem,
  cudze zadanie i cudzy plik → 404, limity typu i rozmiaru, kolejka
  jednoslotowa, propozycja vs zatwierdzenie, eksport i usunięcie konta,
  brak treści w logach i metrykach, audyt bez treści, idempotencja, limit
  dzienny, zmniejszanie obrazu) oraz `frontend/scripts/test-ocr-utils.mjs`
  (9). Migracja nr 20 na starej bazie: stub tabeli `documents` dołożony do
  wszystkich testów migracji v1.

## 0.26.0 — 2026-08-18

**Cotygodniowy digest trenera** (runda 6b.8 ze `SPEC_NASTEPNE_RUNDY.md`).
Numer wpisu to kontynuacja bieżącej numeracji — polecenie mówiło o 0.10.0,
ale ta wersja została wydana dawno temu i cofanie numeracji zaciemniłoby
historię.

* **Ekran „Podsumowanie tygodnia"** w panelu trenera (`/trener/podsumowanie`,
  wejście z pulpitu i z „Więcej"): kto zaraportował w tym tygodniu, co czeka
  na ocenę, kto zalega z raportem, gdzie zalegają płatności, gdzie zgłoszono
  ból lub niepokojącą obserwację (14 dni) i jakie konsultacje są umówione.
* `GET /api/coach/weekly-digest` liczy wszystko przez `aggregates.client_flags_bulk`
  — dokładnie ten sam kod co pulpit i karta klienta, więc żaden ekran nie
  pokazuje innej prawdy. Stała liczba zapytań niezależnie od liczby
  podopiecznych.
* **Digest to metadane operacyjne, nigdy ranking**: brak punktacji, ocen
  i porównań między ludźmi; grupy sortowane alfabetycznie (kolejność nie
  sugeruje „lepszego" podopiecznego). Egzekwowane testem, który odrzuca
  pola typu score/rank i pilnuje sortowania.
* **Poniedziałkowe powiadomienie 07:00** czasu trenera przez wspólny system
  powiadomień (nowa kategoria `PODSUMOWANIE`): idempotentne po kluczu
  tygodnia ISO — restart maszyny ani tick co minutę nie tworzą duplikatu.
  E-mail jest dla tej jednej kategorii włączony domyślnie (bez niego digest
  nie miałby sensu), push wyłączony; przy `NullNotificationProvider` wpis
  trafia wyłącznie do centrum powiadomień w aplikacji i nic nie wychodzi
  na zewnątrz.
* Treść powiadomienia i e-maila jest neutralna — bez nazwisk, liczb i
  danych zdrowotnych (może trafić na ekran blokady); szczegóły wyłącznie
  po zalogowaniu. Potwierdzone testem skanującym wysłaną treść.
* Testy: `tests/test_weekly_digest.py` (8) — zgodność z pulpitem i listą
  klientów, brak sygnałów rankingowych, świeży raport przenosi klienta
  między grupami, dostęp tylko dla trenera i tylko do swoich podopiecznych,
  planowanie raz na tydzień, brak planowania w inne dni, neutralność treści
  przy działającym dostawcy e-mail, milczenie przy dostawcy Null.

## 0.25.0 — 2026-08-18

**Szkic pracujących mięśni w karcie ćwiczenia** + naprawa samoczynnego
przeładowania aplikacji przy pierwszej wizycie.

* Nowy komponent `MuscleMap.tsx`: sylwetka przód i tył rysowana wektorowo
  w aplikacji (zero zewnętrznych zasobów — działa offline i mieści się
  w ścisłej CSP), z podświetleniem partii: mocno główne, słabiej
  pomocnicze. Klucze pochodzą ze wspólnego słownika `MUSCLE_LABELS`
  (kontrakt z `dzik_os/muscles.py`), więc rysunek podświetla się z danych
  ćwiczenia — nic nie jest rysowane ręcznie per ćwiczenie. Klucz spoza
  słownika jest pomijany, żeby rysunek nigdy nie wywrócił karty.
* Rysunek jest DODATKIEM do opisu słownego, nie jego zamiennikiem: listy
  „główne / pomocnicze" zostają pod spodem (czytniki ekranu, wydruk),
  a przy szkicu stoi jawna informacja, że pokazuje okolicę ciała, a nie
  dokładny przebieg mięśni. Widoczny wszędzie tam, gdzie karta ćwiczenia:
  baza ćwiczeń klienta i trenera oraz podgląd techniki z planu.
* **Naprawa (PWA)**: przy pierwszej wizycie świeżo zainstalowany service
  worker przejmuje kontrolę sam (`clients.claim`), a `pwa.ts` traktował to
  jak aktualizację i przeładowywał stronę. Efekt: formularz wypełniany
  w tym momencie znikał — logowanie potrafiło „nie zadziałać" za pierwszym
  razem. Od teraz przeładowanie następuje WYŁĄCZNIE po świadomym kliknięciu
  w baner nowej wersji. Regresja zabezpieczona kontrolą w
  `e2e/test_pwa_offline.mjs` (znacznik na `window` przeżywa pierwszą wizytę).

## 0.24.0 — 2026-08-18

Znacząca rozbudowa **bazy ćwiczeń** wraz z pełnymi opisami oraz
**układanie planu treningowego z ćwiczeń już dodanych do aplikacji**
(zamiast wpisywania nazw z pamięci). Pełny opis modelu, słownika
mięśni jako kontraktu dla rysunku sylwetki, zasad opisów, API filtrów i
planu wycofania migracji nr 19: `docs/BAZA_CWICZEN.md`.

* **Rozszerzony model ćwiczenia** (migracja nr 19, wyłącznie addytywne
  `ALTER TABLE`, **wszystkie nowe kolumny NULLable**): mięśnie główne i
  pomocnicze (klucze słownikowe), poziom
  (POCZATKUJACY/SREDNIOZAAWANSOWANY/ZAAWANSOWANY), wzorzec ruchu
  (13 wartości: przysiad, zawias biodrowy, wypychanie/przyciąganie
  poziome i pionowe, wykrok, noszenie, rotacja, antyrotacja, izolacja,
  cardio, mobilność), kroki techniki, najczęstsze błędy, wskazówki
  („cue”), uwagi bezpieczeństwa, wariant łatwiejszy i trudniejszy,
  tempo i oddech. `how_to`/`benefit` **zostają polami zgodności
  wstecznej** — ćwiczenia sprzed rozbudowy zapisują się i wyświetlają
  bez zmian (test).
* **Słownik partii mięśniowych jako KONTRAKT** (21 kluczy, m.in.
  `KLATKA_PIERSIOWA`, `NAJSZERSZY_GRZBIETU`, `CZWOROGLOWY_UDA`,
  `ZGINACZE_BIODRA`) — jedno źródło w backendzie (`dzik_os/muscles.py`),
  lustro w `frontend/src/types.ts::MUSCLE_LABELS` i nowy endpoint
  `GET /api/exercise-dictionaries`. Walidacja serwerowa: nieznany klucz,
  poziom albo wzorzec = **422**. To ten sam słownik, którego użyje
  rysunek sylwetki z kolejnej rundy — w karcie ćwiczenia zostawiono
  oznaczony komentarzem punkt wstawienia komponentu.
* **Katalog startowy: 155 ćwiczeń** (`dzik_os/exercise_catalog.py`), każde
  z pełnym opisem (3–6 kroków techniki, 2–4 błędy, 1–3 wskazówki,
  bezpieczeństwo, warianty, sprzęt, poziom, wzorzec, mięśnie). Pokrycie:
  sztanga, hantle, kettlebell, maszyny i wyciągi, masa własna ciała,
  gumy oporowe, dom bez sprzętu, core, mobilność i rozgrzewka, cardio.
  Nowa grupa listy `CARDIO` obok dotychczasowych.
* **Granica roli utrzymana**: baza to know-how trenera, nie porada
  medyczna. Żaden opis nie twierdzi, że ćwiczenie coś leczy czy
  „naprawia”; uwagi bezpieczeństwa kierują do konsultacji ze
  specjalistą przy bólu lub urazie, a aplikacja **niczego nie dobiera
  automatycznie** — ćwiczenia wybiera trener.
* **Wyszukiwanie i filtry po stronie API** (obie listy, klienta i
  trenera): szukanie po nazwie i sprzęcie **odporne na polskie znaki**
  (`wioslowanie` = `wiosłowanie`), filtry partii mięśniowej, sprzętu,
  poziomu i wzorca ruchu, paginacja z `total`/`has_more` i przyciskiem
  „pokaż więcej”. Widok szczegółu (klient i trener) pokazuje pełny opis
  w czytelnych sekcjach.
* **Edytor trenera** obsługuje cały nowy model: listy kroków/błędów/
  wskazówek z dodawaniem i usuwaniem pozycji, wybór mięśni z listy
  słownikowej, poziom i wzorzec z list. Dostępność jak w P10 (etykiety
  `for`/`id`, `fieldset`/`legend`, opisane przyciski, `aria-live` na
  liczbie wyników).
* **Nowość — plan układany z bazy**: w edytorze planu przy każdym dniu
  wyszukiwarka ćwiczeń (te same filtry co w bazie); jedno kliknięcie
  dodaje pozycję i **nie zamyka wyszukiwarki**, więc można dodać kilka
  ćwiczeń pod rząd. Puste pola pomocnicze uzupełniają się z bazy
  (tempo, wskazówka jako komentarz, link do wideo) — **nigdy nie
  nadpisujemy wartości wpisanych przez trenera**. Ręczne wpisanie nazwy
  zostaje pełnoprawną ścieżką: aplikacja nie zamyka trenera w katalogu.
* **Powiązanie pozycji planu z ćwiczeniem** (`exercise_id` w treści
  wersji planu — **bez migracji**, ten sam wzorzec co suplementacja w
  diecie). Walidacja serwerowa: identyfikator musi wskazywać **aktywne
  ćwiczenie tego trenera**, inaczej 422 (nie da się wstawić cudzego).
  Odniesienie jest **miękkie**: archiwizacja ćwiczenia nie psuje
  istniejących planów — nazwa i parametry są w planie, znika tylko link
  do karty. Stare wersje planów bez `exercise_id` działają bez zmian.
* **Klient widzi technikę wprost z planu** i z ekranu „Dzisiaj”:
  rozwijana karta ćwiczenia (kroki, błędy, wskazówki, bezpieczeństwo,
  mięśnie). Widoczność rządzi się dotychczasową zasadą broadcastu —
  tylko przy aktywnej relacji z trenerem i tylko dla ćwiczeń ACTIVE.
* Seed ładuje pełny katalog **przed** planami, a każda pozycja planów i
  szablonów demo jest podpięta przez `exercise_id` — demo pokazuje
  docelowy przepływ, nie luźne nazwy.
* Testy: backend 413 → 442 (nowy `test_exercises_extended.py`: migracja
  19 na starej bazie, seed ≥150 bez duplikatów, walidacja słownika,
  filtry, wyszukiwanie z polskimi znakami, paginacja, zgodność wsteczna,
  izolacja trenerów, widoczność przy relacji, kontrakt `exercise_id` i
  zachowanie planu po archiwizacji); frontend helpers 42 → 49
  (`exerciseFilters`); Core 275 bez zmian. **Zaktualizowany świadomie**:
  `test_exercises.py::test_client_sees_seeded_exercises_grouped_by_muscle`
  zakładał, że wszystkie ćwiczenia zmieszczą się na jednej stronie —
  po wprowadzeniu paginacji pyta wprost o partię `NOGI` i sprawdza
  `total ≥ 150`.

## 0.23.0 — 2026-08-18

Baza produktów spożywczych jako narzędzie codziennej pracy, nie demo:
katalog urósł z 40 do **409 pozycji w 16 kategoriach**, doszedł błonnik,
jednostki sztukowe („2 jajka” = 100 g), źródło i uwagi przy każdej
wartości, wyszukiwarka odporna na polskie znaki, stronicowanie po stronie
API oraz import/eksport CSV. Pochodzenie danych, format CSV i plan
wycofania migracji nr 18: `docs/BAZA_PRODUKTOW.md`.

* **Katalog 409 pozycji** (`dzik_os/food_catalog_data.py` — osobny moduł,
  żeby seed pozostał czytelny) w kategoriach: mięso i drób (40), ryby i
  owoce morza (27), jaja (9), nabiał (39), zboża i pieczywo (32), kasze/
  ryż/makarony (28), warzywa (46), owoce (34), rośliny strączkowe (19),
  orzechy i nasiona (20), tłuszcze i oleje (15), przekąski i słodycze (24),
  napoje (20), odżywki i suplementy (15), dania gotowe i fast food (22),
  przyprawy i dodatki (19). Wartości **uśrednione** dla produktów
  dostępnych w Polsce; nazwy **generyczne** (zero marek i producentów);
  stan surowy / ugotowany / gotowy rozróżniony w nazwie i w polu `note`
  wszędzie, gdzie obróbka istotnie zmienia wartości (ryż, makaron, kasza,
  strączki, mięso).
* **Uczciwość danych widoczna w interfejsie, nie w dokumentacji**: każda
  odpowiedź katalogu, kalkulatora porcji i kompozytora diety niesie pole
  `disclaimer` („wartości są przybliżone i uśrednione — zależą od marki,
  partii i obróbki; punkt wyjścia do oszacowania, nie pomiar”), a widok
  pokazuje go przy katalogu i przy kalkulatorze. Katalog jest **opisowy,
  nie oceniający** — zero twierdzeń zdrowotnych i rekomendacji; o
  zastosowaniu produktu decyduje trener.
* **Nowe pola produktu** (migracja nr 18, czysto addytywna, wszystkie
  kolumny NULLable): `fiber_100g` (błonnik), `unit_name` + `unit_grams`
  (jednostka sztukowa: „1 kromka ≈ 35 g” — porcja bez wagi kuchennej),
  `source` (skąd pochodzą wartości), `note` (uwagi). Pełna zgodność
  wsteczna: produkty i żądania API sprzed migracji działają bez zmian, a
  brak danych zostaje `NULL`, nie zerem (0 g błonnika to twierdzenie, brak
  danych — nie).
* **Wyszukiwanie i stronicowanie po stronie API** (`q`, `category`, `sort`,
  `limit`/`offset`, `status`): 400+ rekordów nigdy nie ładuje się do widoku
  naraz — strona ma 30 pozycji, resztę dokłada „Pokaż więcej”. Wyszukiwarka
  ignoruje wielkość liter i polskie znaki („losos”, „ŁOSOŚ” → „Łosoś”), a
  gdy dopasowanie ścisłe nie da nic, drugi przebieg dopasowuje po słowach
  („lososiowy” → „Łosoś”). Sortowanie: nazwa / kalorie / białko. Filtr
  kategorii z listą liczoną z całego katalogu (wybór kategorii nie kasuje
  pozostałych opcji).
* **Kalkulator porcji** (`POST /api/food-products/portion` + wspólna czysta
  logika `frontend/src/foodUtils.ts`): gramy **albo** sztuki (podanie obu =
  422, bo wynik ma być jednoznaczny), błonnik pokazywany, gdy jest znany,
  sensowne zaokrąglenia (kcal do pełnych, makro do 0,1 g). Panel trenera i
  panel klienta liczą tą samą funkcją, więc liczby nie mogą się rozjechać.
  Kompozytor diety pokazuje dodatkowo błonnik i ekwiwalent w sztukach.
* **Import/eksport CSV katalogu przez trenera** (prawo wyjścia): eksport
  całego katalogu (UTF-8 z BOM, także archiwum) i import hurtem —
  separator `,` lub `;`, przecinek dziesiętny, limit 1000 wierszy,
  walidacja nagłówków, typów i zakresów (kcal 0–900, makro 0–100 na 100 g),
  **raport błędów per wiersz bez przerywania importu na pierwszym błędzie**.
  Upsert po nazwie w obrębie katalogu trenera; **izolacja trenerów**: wiersz
  o nazwie identycznej z cudzym produktem tworzy nowy własny produkt i nigdy
  nie modyfikuje cudzego. Obieg eksport → import jest idempotentny. Oba
  działania audytowane (`FOOD_CATALOG_EXPORTED`, `FOOD_CATALOG_IMPORTED`)
  bez treści produktów.
* Migracja schematu nr 18 (pięć kolumn na `food_products`) — addytywna, z
  testem na bazie v1 i planem wycofania w `docs/BAZA_PRODUKTOW.md`.
  `docs/PERMISSIONS.md` uzupełniony o trzy nowe endpointy.
* Testy: backend 413 → 446 (nowy `test_food_catalog_extended.py`: migracja
  18 na starej bazie, rozmiar katalogu i brak duplikatów nazw, polskie
  znaki w wyszukiwarce, filtr kategorii, stronicowanie, sortowanie,
  porcja gramowa i sztukowa, izolacja przy imporcie, eksport, walidacja
  zakresów); frontend helpers 42 → 55 (`foodUtils`: normalizacja nazw,
  gram↔sztuka, błonnik jako brak danych vs. zero, odporność na złe
  wejście); Core 275 bez zmian. Świadoma zmiana istniejących testów:
  `test_food_products.py` nie zakłada już, że cały katalog przychodzi w
  jednej odpowiedzi — produktów szuka przez `?q=`.

## 0.22.0 — 2026-08-18

Runda 14: **konwersacyjny onboarding** — rozmowa startowa zamiast ściany
formularza. Jedno pytanie na krok, z wyjaśnieniem PO CO jest potrzebne,
z możliwością pominięcia, powrotu, przerwania i wznowienia; na koniec
uporządkowane podsumowanie zatwierdzane NAJPIERW przez klienta, POTEM
przez trenera. Pełny opis architektury, schematu danych, promptów
systemowych w całości, zabezpieczeń przed wstrzyknięciem instrukcji,
minimalizacji danych, limitów kosztowych i planu wycofania migracji 17:
`docs/ONBOARDING_AI.md`.

**Cała funkcja działa end-to-end BEZ modelu językowego.** Tryb bez modelu
nie jest trybem awaryjnym drugiej kategorii — jest ścieżką domyślną,
w pełni przetestowaną, z tym samym kompletem pól. Model (gdy operator
skonfiguruje dostawcę, a klient wyrazi zgodę) może wyłącznie przygotować
**wersję roboczą podsumowania**.

* **Nowość — deterministyczny scenariusz rozmowy**
  (`onboarding_flow.py`): katalog kroków obejmujący cele, doświadczenie,
  dostępność, preferowane dni i godziny, sprzęt, ograniczenia, urazy,
  ból, sen, stres, żywienie, alergie, suplementację, preferencje
  komunikacji i informację o zgodach. Każdy krok niesie pytanie, „po co"
  i typ odpowiedzi; walidacja wyborów jest serwerowa (wartość spoza
  listy nigdy nie trafia do profilu).
* **Reguły adaptacji po stronie serwera** — brak sprzętu odsłania
  pytania o warianty domowe, zgłoszony uraz odsłania doprecyzowanie
  ograniczeń, początkujący dostaje pytanie o instruktaż techniki.
  Działają identycznie bez modelu. Pominięte pytanie **nie** odsłania
  kroków warunkowych (pominięcie niczego nie „odpowiada").
* **Dane wrażliwe zbierane tylko wtedy, gdy są potrzebne** — pytania
  zdrowotne powstają wyłącznie przy aktywnej zgodzie `dane_zdrowotne`,
  żywieniowe przy `zywienie_alergie`. Cofnięcie zgody w trakcie rozmowy
  natychmiast wycina dalsze pytania, chowa odpowiedzi przed trenerem
  i wyklucza te pola z zapisu do profilu (`skipped_fields`).
* **Objawy alarmowe** (ból w klatce, omdlenia, duszność, ostry ból po
  urazie, kołatanie serca, drętwienie/niedowład, nagły silny ból głowy):
  rozpoznaje je deterministyczna lista słów kluczowych — nie model —
  odporna na wielkość liter i brak polskich znaków. Reakcją jest spokojny
  komunikat kierujący do lekarza (112/999 przy nagłym przebiegu), bez
  diagnozy, bez nazywania przyczyny i bez straszenia; rozmowa nie jest
  przerywana, a trener dostaje wyraźny sygnał „wstrzymaj plan do
  konsultacji". Taka odpowiedź **nigdy nie jedzie do dostawcy modelu**.
* **Historia zamiast nadpisywania** (`onboarding_answers` append-only):
  poprawiona odpowiedź to nowa wersja, poprzednia zostaje. Sprzeczne
  odpowiedzi są widoczne dla trenera jako dane źródłowe z historią.
  Pominięcie zapisywane jest jawnie (`skipped`), a nie jako pusta
  wartość.
* **Przerwanie i wznowienie**: stan rozmowy (bieżący krok, odpowiedzi)
  żyje w bazie, nie w przeglądarce — nowe logowanie wraca dokładnie
  w to samo miejsce.
* **Warstwa modelu propose-only** (`onboarding_ai.py`): ścisły kontrakt
  wyjścia (Pydantic, `extra="forbid"`), biała lista pól wywiedziona ze
  scenariusza rozmowy, poziom pewności HIGH/MEDIUM/LOW per pole
  i wymuszone `needs_confirmation` dla MEDIUM/LOW — **niepewności nie da
  się ukryć**. Odpowiedź niezgodna ze schematem jest odrzucana
  (jedno ponowienie, potem tryb formularza) i nigdy nie ląduje
  w podsumowaniu ani w profilu. Wyjścia świadomie NIE naprawiamy.
* **Model nie publikuje planu ani diety** — pól planu i diety nie ma
  w białej liście, więc nie ma dokąd zapisać takiej propozycji
  (własność strukturalna, nie tylko zapis w promptcie).
* **Ochrona przed prompt injection** w czterech warstwach: wypowiedzi
  klienta wyłącznie jako WARTOŚCI w strukturze JSON (nigdy sklejane
  z instrukcją), jawne wygaszenie instrukcji z sekcji `DANE_KLIENTA`
  w promptcie systemowym, biała lista pól i walidacja wyjścia.
  Testy z czterema wektorami wstrzyknięcia (w tym próbą zamknięcia
  sekcji danych i podstawienia własnego JSON-a).
* **Minimalizacja zakresu**: do dostawcy jedzie wyłącznie lista
  `{pole, zagadnienie, pytanie, odpowiedź}` — bez identyfikatorów,
  e-maili, imion, nazwisk, bez odpowiedzi pominiętych i bez odpowiedzi
  z sygnałem alarmowym; wartości przycięte do limitu kroku, całość do
  `DZIK_AI_MAX_INPUT_CHARS`. Bez zgody `funkcje_ai` **nic** nie opuszcza
  serwera, a UI mówi to wprost (nie jako błąd techniczny).
* **Zgoda `funkcje_ai` objęła nowy cel przetwarzania** — opis kategorii
  rozszerzony o wersję roboczą podsumowania rozmowy startowej; wersja
  dokumentu zgód podbita do **2.1**, więc wcześniejsze zgody są
  oznaczone jako udzielone na starszą treść.
* **Dwie odrębne akceptacje**: klient zatwierdza podsumowanie (dopiero
  wtedy dane trafiają do profilu normalną, wersjonowaną ścieżką
  `CLIENT_DECLARED` — wspólny `profile_service.apply_profile_fields`,
  ten sam co formularz — oraz do celu głównego), trener zatwierdza je
  jako podstawę planu. Kolejność nie jest zamienna (`409`), a pola
  oznaczone niepewnością wymagają jawnego potwierdzenia przez trenera.
  Istniejący aktywny cel główny nie jest nadpisywany.
* **Suplementacja wyłącznie jako deklaracja klienta**
  (`suplementacja_deklaracja`, zgoda `zywienie_alergie`) — rozmowa nie
  tworzy planu suplementacji; ten powstaje wyłącznie w wersji planu
  diety, wprowadzony przez człowieka.
* **Ekran rozmowy** (`/rozmowa`): pasek postępu, „pomiń", „wróć",
  „przerwij i wróć później", podsumowanie do edycji i zatwierdzenia,
  jawna informacja skąd pochodzi każde pole i jaka jest jego pewność.
  Dostępność jak w P10: `aria-live` na zmianę kroku, fokus na nowym
  pytaniu, etykiety pól, `role="progressbar"` z wartością.
* **Integracja z ankietą startową**: `Intake` (`/ankieta`) **zostaje**
  jako pełnoprawny tryb awaryjny/alternatywny — obie drogi zapisują
  dokładnie te same pola profilu; ekran Dzisiaj proponuje wybór
  („Porozmawiajmy" / „Wolę formularz"), a oba ekrany linkują do siebie.
* **Widok trenera** (nowa zakładka „Rozmowa startowa" w karcie klienta):
  dane źródłowe z historią poprawek i oznaczeniem pominięć,
  podsumowanie, poziom niepewności per pole, pola do potwierdzenia,
  sygnał do konsultacji medycznej i przycisk zatwierdzenia.
* **Limity, timeouty i koszty**: `DZIK_AI_TIMEOUT_S` (20 s),
  `DZIK_AI_DAILY_CALLS_USER` (20), `DZIK_AI_DAILY_CALLS_GLOBAL` (500),
  `DZIK_AI_MAX_INPUT_CHARS` (6000); licznik wywołań i tokenów per
  użytkownik i dzień (`ai_usage_counters`), metryki w `/api/metrics`
  (`onboarding_ai_calls`, `_rejected`, `_fallback`, `_tokens_in`,
  `_tokens_out`, `onboarding_safety_flags`) — same liczby, nigdy treść.
  Logi (P9) niosą co najwyżej numer próby i kategorię odrzucenia —
  pełne rozmowy nigdy nie trafiają do logów technicznych.
* **Adapter dostawcy rozszerzony** (`ai_provider.py`): kontrakt
  `propose_json(...) -> AIJsonResponse | None` obok istniejącego
  `summarize_checkin`; domyślnie nadal `NullAIProvider` — bez klucza nic
  nie wychodzi, a UI podaje powód. Kontrakt jest w całości przetestowany
  na atrapie (poprawna odpowiedź, zły JSON, pole spoza listy, brak
  odpowiedzi, wyjątek).
* Eksport danych (`export_version` **1.4**) objął sesje rozmowy,
  wszystkie wersje odpowiedzi i podsumowanie oraz liczniki kosztów AI;
  usunięcie konta kasuje treść rozmów i liczniki.
* Migracja schematu nr **17** (cztery nowe tabele, zero ALTER-ów) —
  addytywna, z testem v1→17 i planem wycofania w `ONBOARDING_AI.md`.
* Testy: backend 413 → 460 (nowy `test_onboarding.py`: pełna rozmowa,
  przerwanie i wznowienie, sprzeczne odpowiedzi z zachowaną historią,
  pominięcia, reguły adaptacji, objawy alarmowe, brak i wycofanie zgody
  w trakcie, minimalizacja ładunku, prompt injection ×4, niedostępność
  dostawcy, błędny JSON, pole spoza białej listy, ukryta niepewność,
  limit dzienny, metryki bez treści, edycja podsumowania przez klienta,
  zatwierdzenie przez klienta i trenera, izolacja IDOR, migracja v1→17);
  frontend helpers 42 → 53 (`onboardingUtils`); Core 275 bez zmian.

## 0.21.0 — 2026-08-18

Powiadomienia i prawdziwe przypomnienia (P13): jeden spójny system dla
wszystkich kategorii i kanałów — przebudowa istniejących mechanizmów
(pętla przypomnień, pushe rozsiane po routerach), nie drugi równoległy.
Pełny opis modelu, strategii harmonogramu, zasad prywatności treści
i planu wycofania migracji 14: `docs/POWIADOMIENIA.md`.

* **Nowość — wspólny model powiadomienia** (`notifications`, migracja
  nr 14): kategoria (trening / suplement / harmonogram / raport /
  wiadomość / płatność / dokument / zmiana planu / konsultacja),
  odbiorca, kanały (centrum w aplikacji / push / e-mail), termin w UTC
  wyliczony w lokalnej strefie odbiorcy, statusy
  SCHEDULED/SENT/CANCELLED/SUPPRESSED z powodem tłumienia, **klucz
  idempotencji w bazie** (`UNIQUE(user_id, dedup_key)`) i źródło
  zdarzenia. Zastępuje dedup `_sent` w pamięci pętli — restart maszyny
  niczego nie duplikuje ani nie gubi (nadganianie do 30 min).
* **Przebudowa pętli przypomnień** (`reminder_loop`): planowanie
  dzisiejszych wystąpień (harmonogram z porą, jednorazowe przypomnienia
  trenera 08:00, płatności z dzisiejszym terminem) + doręczanie po
  terminie z bramkami PRZY WYSYŁCE: zadanie wykonane (trening
  odhaczony, raport wysłany, płatność opłacona) = przypomnienie nie
  wychodzi; wstrzymany element / odwołany slot = anulacja zaplanowanych
  wierszy (`cancel_source`).
* **Strefa czasowa per użytkownik**: nowa kolumna `users.timezone`
  (IANA) czytana przez przygotowany punkt rozszerzenia
  `dates.tz_for_user()` — steruje porami przypomnień i datami
  kalendarzowymi; DST rozstrzyga `zoneinfo` (testy na przejściu
  Europe/Warsaw). Zmiana w ustawieniach powiadomień.
* **Preferencje per kategoria × kanał** (`notification_preferences`;
  domyślnie push+centrum włączone, e-mail wyłączony) oraz
  **ciche godziny** (wyciszają push/e-mail, centrum zawsze dostaje
  wpis; zakres może przechodzić przez północ), **dni aktywne**
  przypomnień i **częstotliwość przypomnienia o raporcie**
  (codziennie vs raz w tygodniu — klucz idempotencji per dzień albo
  per tydzień ISO).
* **Dyskrecja na ekranie blokady**: push i e-mail niosą wyłącznie
  neutralny tytuł kategorii + „Masz nowe powiadomienie w Dzik OS" —
  nigdy dane zdrowotne, nazwy suplementów (SUPLEMENT ma celowo ogólny
  tytuł), kwoty, treści wiadomości ani tytuły dokumentów; klik prowadzi
  do właściwego ekranu (url per kategoria), a pełna treść jest w
  centrum po zalogowaniu. Istniejące pushe (wiadomości, raporty, plan,
  konsultacje, dokumenty) przepięte na wspólny system i zneutralizowane.
* **Nowość — centrum powiadomień w aplikacji** (`/powiadomienia`):
  lista z pełną treścią, przeczytane/nieprzeczytane (per sztuka
  i „oznacz wszystkie"), filtr kategorii, plakietka nieprzeczytanych
  w „Więcej"; **żywe aktualizacje przez SSE z P12** (zdarzenie
  `notification.new` w istniejącym kanale `/api/threads/events`).
  Na tym samym ekranie pełne ustawienia doręczeń.
* **Kontekstowe zachęty do push** (`PushContextPrompt`): zamiast prosić
  o zgodę od razu — karta z wyjaśnieniem korzyści na ekranie Dzisiaj
  (przypomnienia o harmonogramie) i w Wiadomościach (odpowiedzi
  trenera); systemowy dialog dopiero po świadomym „Włącz", „Nie teraz"
  zapamiętywane per kontekst.
* **Nowość — przypomnienie przed konsultacją**: rezerwacja slotu
  planuje powiadomienie 60 min przed startem; odwołanie terminu przez
  trenera lub zdjęcie rezerwacji anuluje je automatycznie.
* **E-mail jako opcjonalny kanał awaryjny**: per kategoria, przez
  istniejący adapter `notifications_provider` (domyślnie Null — nic nie
  wychodzi, dopóki operator nie skonfiguruje dostawcy); treść tak samo
  neutralna jak push.
* **Monitoring doręczeń** w `/api/metrics` (ADMIN): liczniki
  `notif_sent_center` / `notif_sent_push` / `notif_sent_email` /
  `notif_email_failures` / `notif_suppressed` — bez treści i bez metryk
  zaangażowania.
* Eksport danych (`export_version` 1.3) i usunięcie konta objęły
  powiadomienia, preferencje i ustawienia; zmiany ustawień audytowane
  bez treści (`NOTIFICATION_SETTINGS_CHANGED`).
* Migracja schematu nr 14 (trzy nowe tabele + `users.timezone`) —
  addytywna, z testem v1→14 i planem wycofania w POWIADOMIENIA.md.
* Testy: backend 335 → 357 (nowy `test_notifications.py`: strefa per
  użytkownik, DST Europe/Warsaw, duplikaty po restarcie, przestój
  i nadganianie, ciche godziny, dni aktywne, anulowanie terminu,
  zadanie wykonane / raport wysłany / płatność opłacona, wygasła
  subskrypcja, cofnięta zgoda, wiele urządzeń, url i neutralność per
  kategoria, preferencje, częstotliwość raportu, centrum, metryki,
  kanał e-mail); frontend helpers 36 → 42 (`notificationsUtils`:
  ciche godziny, dni aktywne, plakietka, scalanie SSE, wyłącznie
  wewnętrzne urle); Core 275 bez zmian.

## 0.20.0 — 2026-08-18

Runda 15: **wiarygodny moduł płatności** — jednoznaczne rozdzielenie
harmonogramu należności od faktycznie zarejestrowanych transakcji.
Pełny opis modelu, diagram stanów, zasady idempotencji, migracja z planem
wycofania i raport pojednania: `docs/PLATNOSCI.md`. System pozostaje
**ewidencją ręczną** (realna integracja operatora świadomie odłożona —
przygotowana wyłącznie architektura z testami kontraktu).

* **Rozdzielone modele**: należność/okres rozliczeniowy (`payment_records`,
  jak dotąd) vs append-only transakcje (`payment_transactions`: wpłata
  ręczna, wpłata operatora, zwrot, korekta, korekta odwracająca) +
  historia przejść statusu per rekord (`payment_status_changes`) + próby
  płatności i zdarzenia operatora (`payment_attempts`,
  `payment_provider_events`). Faktury: tylko pole referencji dokumentu
  zewnętrznego (`document_ref`) — bez generatora.
* **Kontrolowana maszyna stanów** (`payment_state.py`): PLANNED → PENDING
  → (IN_PROGRESS) → PAID / OVERDUE / FAILED / CANCELLED /
  PARTIALLY_REFUNDED / REFUNDED, z jawną tablicą dozwolonych przejść
  egzekwowaną w backendzie — nieprawidłowe przejście = 422.
* **Frontend nie ustawia „opłacona"**: ogólny endpoint `/status` przyjmuje
  wyłącznie statusy administracyjne (PENDING/OVERDUE/CANCELLED); statusy
  pieniężne wyłącznie przez dedykowane endpointy trenera-właściciela:
  `mark-paid` (kto i kiedy oznaczył — widoczne w UI obu paneli), `refund`
  (zwroty częściowe i pełne), `adjust` (korekta z obowiązkowym powodem),
  `transactions/{id}/reverse` (cofnięcie omyłki bez usuwania śladu).
  Wszystkie z idempotencją P11 (`idempotency_key`); podwójna wpłata bez
  klucza = 422 (PAID→PAID nie istnieje).
* **Kwoty w groszach + waluta przy każdej kwocie** (także zwroty/korekty);
  waluta operacji musi się zgadzać z walutą należności (422), sumy nigdy
  nie mieszają walut.
* **Architektura operatora (bez integracji)**: port
  `PaymentProviderPort` (podpis webhooka, parsowanie zdarzeń) +
  `NullPaymentProvider` + wspólne przetwarzanie
  `payment_events.process_webhook()` (idempotencja po `event_id`,
  powtórka=DUPLICATE, konflikt treści=CONFLICT, zła kolejność=STALE,
  PAID nigdy nie cofane, zły podpis odrzucany bez zapisu; przekierowanie
  przeglądarki niezaufane — żaden kod nie czyta parametrów powrotu).
  Endpoint HTTP webhooka celowo nie istnieje; instrukcja podłączenia
  prawdziwego operatora w `docs/PLATNOSCI.md` §7.
* **Przypomnienia o płatności** w pętli przypomnień: wyłącznie dla
  należności realnie wymagalnych (status sprawdzany w chwili wysyłki —
  zero przypomnień po opłaceniu), w dniu terminu i co 7 dni zaległości;
  treść neutralna bez kwot i nazw pakietów (ekran blokady).
* **Widok klienta** (Płatności): podział na należności i historię,
  wpisy transakcji (kto/kiedy oznaczył, zwroty, cofnięcia — przekreślone,
  nigdy usuwane).
* **Widok trenera** (karta klienta → Płatności): filtry
  zaległe/nadchodzące/opłacone, licznik zaległych, akcje wg stanu,
  rozwijana historia per rekord (przejścia + transakcje z możliwością
  cofnięcia). Nowy widok **„Pojednanie płatności"** (`/trener/rozliczenia`
  + `GET /api/payments/reconciliation`): należności vs zebrane/zwroty/
  korekty per okres, sumy per waluta, kolumna źródła (dziś adnotacje
  ręczne; format gotowy pod operatora).
* **Migracja schematu nr 15** (nr 14 zarezerwowany dla równoległej rundy):
  addytywna — statusy starych rekordów są podzbiorem nowego słownika
  (mapowanie tożsamościowe, zero utraty danych), `marked_at` uzupełnione
  z `paid_at`, nowe tabele startują puste (bez fabrykowania historii);
  plan wycofania w `docs/PLATNOSCI.md` §5.
* **Świadome zmiany starych testów**: `test_payments.py` i
  `test_e2e_paths.py` oznaczają płatność przez `mark-paid` (zamiast
  `/status PAID`); `test_idor.py` testuje IDOR statusem administracyjnym
  + `mark-paid` (schemat odrzuca „PAID" w `/status` zanim dojdzie do
  autoryzacji); stub `payment_records` dopisany do testu migracji v1.
* Testy: 335 → 365 backend (maszyna stanów, podwójna płatność
  z idempotencją i bez, zwrot częściowy/pełny/ponad stan, korekta
  + cofnięcie z pełnym śladem, różne waluty, kontrakt webhooka na Null
  — powtórka/zły podpis/zła kolejność/konflikt, IDOR wszystkich nowych
  endpointów, przypomnienia wg realnego statusu, migracja v1→v15
  z danymi płatności).

## 0.19.0 — 2026-08-18

Wspólne wyzwania i współpraca — **moduł PRYWATNY** (tylko-zaproszeni,
zero publicznych wyzwań). Pełny opis modelu, zasad prywatności, zgodności
z konstytucją Human OS (interpretacja rankingu opt-in), naliczania,
moderacji i planu wycofania migracji nr 16: `docs/WYZWANIA.md`.

* **Zgodność z konstytucją Human OS**: zakaz rankingowania ludzi jako
  mechanizmu domyślnego → ranking jest **opt-in per uczestnik i domyślnie
  WYŁĄCZONY** (obejmuje wyłącznie osoby z podwójnym opt-in:
  `share_result` + `ranking_opt_in`); domyślny widok = własny postęp
  względem celu + **zagregowany postęp grupy bez nazwisk**; wynik
  jednostkowy widoczny dla innych wyłącznie po świadomej decyzji
  uczestnika (ukrycie działa natychmiast); pseudonim per wyzwanie;
  trener nie widzi ukrytych wyników jednostkowych.
* **Model wyzwania** (migracja nr 16 — pięć nowych tabel, czysto
  addytywna, zero ALTER-ów): organizator, uczestnicy, cel, zasady,
  **wyłącznie neutralne jednostki wyniku** (`treningi`/`minuty`/
  `aktywnosci` — masa ciała odrzucana z jasnym komunikatem 422), daty
  start/koniec, **strefa czasowa wyzwania** (dzień wpisu liczony wg niej,
  nie wg strefy urządzenia), widoczność zawsze INVITE_ONLY, statusy
  DRAFT/ACTIVE/FINISHED/CANCELLED.
* **Rodzaje**: indywidualne (klient sam ze sobą — nikt inny go nie widzi,
  nawet trener), grupowe klientów tego samego trenera, prowadzone przez
  trenera. Zaproszenia wyłącznie do AKTYWNIE prowadzonych klientów.
* **Uczestnictwo dobrowolne**: zaproszenie → przyjęcie (z wyborem
  pseudonimu i ustawień widoczności) / odrzucenie; przed decyzją czytelne
  wyjaśnienie „kto zobaczy jaki wynik"; w każdej chwili: opuszczenie,
  ukrycie wyniku, wyłączenie rankingu, blokada uczestnika (obustronna
  niewidoczność), zgłoszenie do organizatora.
* **Dane zdrowotne nigdy w wyzwaniach**: moduł nie ma żadnej ścieżki do
  pomiarów, zdjęć, bólu, urazów, żywienia, raportów; jedyna integracja to
  licznik ukończonych treningów — wyłącznie z danych świadomie
  przeznaczonych do wyzwania (jawny wpis, jawne wskazanie treningu albo
  świadome „zaliczaj moje odhaczone treningi" przy dołączaniu).
* **Uczciwe liczenie**: idempotencja wpisów (`client_entry_id` +
  unikalność zgłoszonego treningu — powtórka zwraca `duplicate`, nie
  drugi wpis; auto-zaliczanie deduplikuje per dzień i wyklucza się
  wzajemnie z wpisami ręcznymi jawnym 409), korekty jako nowe wiersze z
  łańcuchem historii (nigdy nadpisanie), oznaczanie danych ręcznych,
  limit wpisów/dzień, walidacja zakresów, zamrożenie po zakończeniu.
* **Moderacja organizatora + audyt**: wyłącznie własne wyzwania
  (cudze = 404); usunięcie uczestnika, neutralizacja pseudonimu,
  czyszczenie notatek, oddalenie; zdarzenia `CHALLENGE_*` w łańcuchu
  audytu niosą wyłącznie identyfikatory i liczniki (nigdy aliasy,
  notatki, treści zgłoszeń).
* **Trwałe wycofanie udziału**: wpisy fizycznie usuwane, pseudonim
  anonimizowany, agregaty grupy trwale oznaczone „skorygowane"
  (integralność historii przez audyt, nie trzymanie danych osoby);
  usunięcie konta robi to samo dla wszystkich udziałów; eksport
  (export_version 1.3) zawiera udziały i wpisy użytkownika.
* **Nic nie wychodzi poza zamkniętą grupę**: publikowanie na zewnątrz NIE
  jest zaimplementowane — wymagałoby nowej kategorii zgody
  (docs/WYZWANIA.md §8).
* **Powiadomienia**: push przy zaproszeniu/zakończeniu/odwołaniu/
  zgłoszeniu — zawsze neutralne (bez tytułu wyzwania, aliasów, wyników);
  kanał push pozostaje opt-in przez zgodę `przypomnienia`; punkt
  integracji z przyszłym modelem preferencji P13 odnotowany w docs.
* **Frontend**: sekcja „Wyzwania" u klienta (`/wyzwania` — zaproszenia z
  wyjaśnieniem widoczności, lista z paskami postępu, szczegóły z wpisami/
  korektami/ustawieniami/blokadami, własne wyzwanie indywidualne) i u
  trenera (`/trener/wyzwania` — tworzenie, zaproszenia, cykl życia,
  uczestnicy, zgłoszenia z moderacją); linki w „Więcej"; dostępność
  wzorem P10 (etykiety `for`/`id`, `aria-pressed`, `aria-label` akcji,
  paski postępu `aria-hidden` z liczbami w tekście, karty na mobile).
* Testy: backend 335 → 355 (`test_challenges.py` — 20 testów: zaproszenie,
  odmowa, opuszczenie, ukrycie wyniku, 404 dla osób z zewnątrz i obcego
  trenera, korekta z historią, strefa czasowa wyzwania, zakończenie,
  blokada, wycofanie udziału, ranking podwójnego opt-in, idempotencja,
  auto-zaliczanie treningów, neutralny push/audyt, usunięcie konta,
  eksport; rozszerzony test migracji v1→…→16); frontend `npx tsc`,
  `npm run build`, `npm run test:helpers` (36) zielone.

## 0.18.0 — 2026-08-18

**Suplementacja jako część planu diety** — do tej pory suplementy istniały
wyłącznie jako gołe pozycje harmonogramu (nazwa + godzina), bez dawki, celu
i podstawy zalecenia w samym planie.

* Nowa sekcja **Suplementacja** w wersji planu żywieniowego: preparat, dawka,
  pora (i relacja do posiłku), cel, **podstawa zalecenia** (kto i na jakiej
  podstawie), opcjonalnie postać, okres i uwagi oraz znacznik „konsultowane
  ze specjalistą". Nazwa, dawka, pora, cel i podstawa są WYMAGANE — w planie
  nie może wylądować sama nazwa preparatu bez proweniencji.
* Bez migracji schematu: suplementacja jest częścią treści wersji planu
  (JSON), więc **każda zmiana dawki albo odstawienie preparatu zostaje
  w historii wersji** razem z powodem zmiany. Wersje sprzed tej rundy
  zwracają pustą listę (API normalizuje brakujący klucz).
* Nowa wersja planu **przenosi dotychczasową suplementację** do edytora —
  odstawienie preparatu musi być świadomym usunięciem pozycji, nigdy
  efektem ubocznym zapisania nowej wersji diety.
* `POST /api/nutrition/{plan_id}/supplements/reminders` — jednoklikowe
  przypomnienia w harmonogramie (kategoria SUPLEMENT) tworzone Z PLANU:
  dawka i sposób przyjmowania pochodzą z zapisanej pozycji, a nie z ręcznego
  przepisania, więc przypomnienie nie może rozjechać się z dietą. Wywołanie
  jest idempotentne (ta sama nazwa + godzina = pominięcie), a pozycja spoza
  bieżącej wersji planu jest odrzucana (422).
* Granice roli trenera: aplikacja niczego nie dobiera ani nie modyfikuje
  dawkowania — wyłącznie przechowuje zalecenie wprowadzone przez człowieka.
  Klient widzi przy suplementacji jednoznaczną informację, że suplementy nie
  są lekami, trener nie stawia diagnoz, a zmiany warto konsultować z lekarzem
  lub dietetykiem (zwłaszcza przy chorobach, lekach, ciąży i karmieniu).
  Trener przy edycji widzi zadeklarowane przez klienta alergie
  i nietolerancje.
* Audyt notuje fakt zmiany i LICZBĘ pozycji suplementacji — nigdy nazwy
  preparatów (nie powielamy danych zdrowotnych w dzienniku zdarzeń).
* Seed demo: plan „Redukcja 2300 kcal" ma teraz przykładową suplementację
  (witamina D3 z zaleceniem lekarza, kreatyna z zaleceniem trenera).
* Testy: 335 → 341 (walidacja kompletności wpisu, historia wersji przy
  zmianie suplementacji, audyt bez nazw preparatów, przypomnienia z planu
  + idempotencja, pozycja spoza planu, brak edycji przez klienta i izolacja
  cudzego planu).

## 0.17.0 — 2026-08-18

Runda czysto prezentacyjna: **responsywność, wygląd i dostępność**
(WCAG 2.2 AA jako punkt odniesienia) — zero zmian logiki biznesowej,
API i schematu bazy. Pełny opis, protokoły testów ręcznych i świadome
ograniczenia: `docs/DOSTEPNOSC.md`.

* **Responsywność**: formularze dwu-/trzykolumnowe schodzą do jednej
  kolumny poniżej 460 px (wyjątek `.field-row--keep` dla naprawdę
  krótkich par, np. kg × powtórzenia i porównywarki zdjęć); wszystkie
  tabele w kontenerze `.table-wrap` (kontrolowany poziomy scroll),
  a poniżej 620 px jako karty wierszy z etykietami danych
  (`data-label`); wiersze `.row` łamią się zamiast wypychać stronę
  w bok (koniec poziomego scrolla od 320 px — test e2e na
  320/375/768/1024); nowe breakpointy 700 px (stat/photo-grid
  4 kolumny) i 1200 px (szerszy panel trenera); ekran logowania na
  niskich ekranach (landscape telefonu) z mniejszym logo i układem od
  góry.
* **Rozmiary dotykowe i typografia**: przyciski min. 44 px (małe 44 px
  na ekranach dotykowych — `pointer: coarse`), linki nawigacji
  wypełniają cały pasek, checkboksy 20 px, suwaki z wyższym uchwytem;
  koniec tekstów poniżej 12 px (etykiety nawigacji z ~10,5 px → 12 px,
  podpisy suwaków i metadane wiadomości podniesione).
* **Kontrast**: obrysy elementów interaktywnych (`--border-strong`)
  podniesione do ~3:1 względem tła karty (WCAG 1.4.11); tekst
  przygaszony i kolory statusów ≥ 4,5:1 (wyliczenia w DOSTEPNOSC.md).
* **Jeden system ikon**: rozszerzony komponent `Icon` (~35 własnych SVG,
  opcjonalna dostępna nazwa `label`); emoji pełniące rolę ikon w UI
  zastąpione (nagłówki kart, skróty w „Więcej", załączniki, mikrofon,
  timer przerwy, pauza/wznów, ostrzeżenia, pobieranie…); emoji w
  treściach pisanych przez ludzi pozostają.
* **Semantyka**: skip-link „Przejdź do treści", landmarki `<main>` i
  `<nav aria-label>`, porządek nagłówków h1→h2→h3 bez przeskoków w całej
  aplikacji (nagłówki kart to teraz h2, `SectionLabel` to h3, sr-only h1
  na logowaniu), `html lang="pl"`, viewport bez blokady powiększania
  (było poprawnie — teraz pilnowane testem).
* **Formularze**: wszystkie pola z etykietami `for`/`id` albo
  `aria-label` (ok. 90 pól w 14 plikach); suwaki raportu z
  `aria-valuetext` i opisem skali; ocena raportu 1–5, dni tygodnia,
  filtry listy klientów i przełączniki archiwum jako przyciski z
  `aria-pressed` w nazwanych grupach; elementy rozwijane z
  `aria-expanded`.
* **Zakładki** (karta klienta, baza wiedzy trenera i klienta): wspólny
  komponent `Tabs`/`TabPanel` wg wzorca WAI-ARIA Tabs — role,
  `aria-selected`, roving tabindex, strzałki/Home/End.
* **Dynamiczne treści**: `role="status"`/`aria-live` dla spinnera,
  komunikatów sukcesu, banera aktualizacji PWA i stanu pobierania;
  `ErrorBox` pozostaje `role="alert"`; wykresy `Sparkline` z `role="img"`
  i generowaną alternatywą tekstową (zakres dat/wartości, ostatnia
  wartość), wykresy siły nazwane per ćwiczenie; paski postępu
  `aria-hidden` (liczby stoją obok); załączniki audio/wideo z
  dostępnymi nazwami.
* **Klawiatura i fokus**: globalny `:focus-visible` (obrys akcentu),
  pełna obsługa klawiaturą; modali własnych brak — natywne
  `confirm()`/`prompt()` (focus trap/Escape natywnie), odnotowane
  wymaganie dla przyszłych modali.
* **Ruch**: `prefers-reduced-motion` bez zmian (wyłącza animacje) —
  potwierdzone w rundzie.
* **Testy**: nowy `e2e/test_a11y.mjs` (Playwright + Chromium; axe-core
  wstrzykiwany, gdy dostępny w środowisku, plus własne asercje:
  skip-link, landmarki, etykiety pól, porządek nagłówków, brak
  poziomego scrolla na 4 szerokościach, rozmiary nawigacji, suwaki,
  wykresy, zakładki z klawiaturą, landscape logowania) — 40 kontroli
  zielonych; regresja `test_pwa_offline.mjs` zielona; backend 304 i
  Core 275 bez zmian.

## 0.16.0 — 2026-08-18

Wiadomości w czasie rzeczywistym i porządne nagrania głosowe. Pełny opis
architektury (transport, statusy, formaty audio, retencja, plan wycofania
migracji 13): `docs/WIADOMOSCI.md`.

* **Kanał czasu rzeczywistego (SSE)**: `GET /api/threads/events` —
  wybrane SSE zamiast WebSocketu (Bearer w nagłówku przez fetch — token
  NIGDY w query stringu; ten sam łańcuch middleware co reszta API:
  nagłówki P5, request id i model błędów P9, no-store; CSP connect-src
  'self' wystarcza; sw.js nie dotyka /api). Magistrala zdarzeń w pamięci
  procesu (`realtime.py`); zdarzenia: message.new / message.delivered /
  message.read / resync / session_expired + keepalive
  (`DZIK_SSE_KEEPALIVE_S`, domyślnie 25 s). **Każde doręczane zdarzenie
  przechodzi ponownie bramkę require_thread_party** (cofnięcie zgody
  odcina kanał trenera w locie), a ważność sesji jest sprawdzana W TRAKCIE
  strumienia — unieważniony token dostaje session_expired i czytelny
  powrót do logowania. Ograniczenie: jeden proces (fly:
  min_machines_running=1) — opisane w docs.
* **Reconnect + bezpieczny fallback**: frontendowy klient SSE
  (`realtime.ts`, fetch + własny parser strumienia) z wykładniczym
  backoffem 1→30 s; po 3 nieudanych próbach kontrolowany polling co 15 s
  WYŁĄCZNIE na otwartym i widocznym ekranie rozmowy, z powrotem na kanał
  gdy wróci. Lista wątków: odświeżanie liczników co 30 s na otwartym
  ekranie + przy powrocie do karty.
* **Statusy wiadomości** (migracja nr 13: `messages.delivered_at`,
  `messages.client_msg_id`, indeks porządku i częściowy indeks unikalny;
  addytywna, plan wycofania w docs): wysłana (potwierdzenie POST) →
  dostarczona (SSE/GET odbiorcy, na żywo z pokwitowaniem
  message.delivered) → przeczytana (otwarcie wątku lub
  `POST /threads/{id}/read` przy otwartym ekranie). Znaczniki
  monotoniczne, ustawia wyłącznie odbiorca; licznik nieprzeczytanych per
  wątek jak dotąd w `GET /api/threads`.
* **Deduplikacja i kolejność**: `client_msg_id` z urządzenia nadawcy
  (UUID) — ponowienie po utracie sieci zwraca istniejącą wiadomość
  (`duplicate: true`), unikalność per (wątek, autor, client_msg_id)
  także indeksem w bazie; stabilny porządek `(created_at, id)` po obu
  stronach; UI scala duplikaty i spóźnione zdarzenia
  (`messaging.ts::mergeMessage`).
* **Paginacja historii**: `?limit=50&before=<id>` + `has_more` i przycisk
  „Wczytaj starsze wiadomości"; kursor spoza wątku → 404; dociąganie
  starszych NIE znaczy przeczytania.
* **Szkic per wątek**: treść pola przeżywa utratę sieci, nawigację
  i przeładowanie (sessionStorage, czyszczony po wysłaniu); optymistyczny
  dymek „wysyłanie…" podmieniany potwierdzeniem serwera, a błąd wysyłki
  nie czyści formularza.
* **Nagrania głosowe naprawione**: format przez
  `MediaRecorder.isTypeSupported` (webm/opus → Chrome/Firefox/Android;
  audio/mp4 AAC → Safari/iOS ≥ 14.3), wysyłany RZECZYWISTY
  `recorder.mimeType` (typ bazowy, koniec ze sztywnym audio/webm),
  rozszerzenie wg typu; limit 3 min (auto-stop bez utraty nagrania)
  i 15 MB; odsłuch/nagraj ponownie/usuń przed wysłaniem; `track.stop()`
  na WSZYSTKICH ścieżkach mikrofonu po stopie, anulowaniu, błędzie
  i odmontowaniu; wszystkie Blob URL zwalniane. Logika wydzielona do
  testowalnego `audioCapture.ts` (wstrzykiwane getUserMedia/MediaRecorder).
* Backend audio bez zmian allowlisty (webm/m4a/mp3/ogg już wspierane —
  zweryfikowane magic bytes testami, w tym niezgodność zawartości i typ
  z parametrem kodeka = 415).
* **Prywatność**: treści rozmów i nagrania poza logami/metrykami/push
  (push nadal neutralne „Nowa wiadomość" — test); zdarzenia SSE nie są
  logowane; IDOR = 404 na wszystkich nowych ścieżkach. Retencja
  i usuwanie: anonimizacja wątków przy usunięciu konta zweryfikowana,
  osierocone głosówki trenera sprząta pętla plików-sierot — opis
  w `docs/WIADOMOSCI.md` §6.
* Testy: backend 304 → 323 (`test_messages_realtime.py` — wymiana dwóch
  użytkowników, duplikaty, kolejność, paginacja, IDOR, sesja na kanale,
  magistrala + przepełnienie, push bez treści, formaty audio; migracja
  v1→v13); frontend `npm run test:helpers` 10 → 29 (parser SSE, backoff,
  scalanie/porządek, szkice, wybór formatu, kontroler nagrywania —
  odmowa mikrofonu i odmontowanie w trakcie nagrania włącznie). Żywy
  strumień zweryfikowany uvicorn+curl (ograniczenie TestClienta w docs).

## 0.15.0 — 2026-08-18

Jakość raportów i zdjęć progresu: **koniec fałszywych danych z domyślnych
suwaków 3/5, pełny UX wysyłki zdjęć, idempotencja zapisu**.

* **Suwaki bez wartości domyślnej**: każde pytanie subiektywne raportu
  startuje PUSTE — użytkownik świadomie wybiera 1–5 (z opisem krańców:
  „1 = brak energii · 5 = pełna energia") albo oznacza pytanie jako
  „Pomijam" / „Nie dotyczy"; bez decyzji przy każdym pytaniu raportu nie
  da się wysłać. Model danych rozróżnia CZTERY stany odpowiedzi
  (`payload.scale_states`): brak odpowiedzi (brak klucza), świadoma
  wartość ANSWERED (w tym neutralne 3/5), świadome pominięcie SKIPPED,
  brak zastosowania NOT_APPLICABLE. Walidacja spójności w backendzie
  (ANSWERED wymaga wartości; SKIPPED/NOT_APPLICABLE jej zabrania; wartość
  bez stanu = 422). Stare raporty NIE są reinterpretowane — wiersze sprzed
  zmiany zostają, API oznacza je `scales_declared=false`, a UI trenera
  pokazuje notę „suwaki mogły pozostać na wartości domyślnej 3/5".
* **Idempotencja zapisu** (migracja nr 12, tabela `idempotency_keys`):
  pole `idempotency_key` w POST /api/checkins — powtórka tego samego
  żądania (podwójne kliknięcie, retry po utracie odpowiedzi sieci) zwraca
  zapisany wynik zamiast tworzyć rewizję; ten sam klucz z inną treścią =
  jawny 409. Przycisk wysyłki dodatkowo zablokowany na czas wysyłania.
  Klucze per użytkownik+operacja; usuwane przy usunięciu konta.
* **Wersja robocza formularza**: draft w localStorage per użytkownik +
  tydzień (pola, decyzje skal, klucz idempotencji) — przywracany po
  błędzie/zamknięciu karty; czyszczony po udanej wysyłce. Zdjęcia
  (obiekty File) świadomie poza draftem — z jawnym komunikatem.
* **Raport częściowy jako stan jawny**: `weekly_checkins.photos_expected`
  (migracja 12) — klient deklaruje liczbę zdjęć przy wysyłce; raport z
  mniejszą liczbą zapisanych jest oznaczony „częściowy · zdjęcia A/B"
  u klienta i trenera (`photos_complete` w API), do dokończenia przez
  nowy `POST /api/checkins/{id}/photos` (dopięcie brakujących po jednym
  albo świadome zamknięcie bez nich, `set_expected`). Po ocenie trenera
  zdjęcia raportu są zamrożone (409).
* **Pełny UX wysyłki zdjęć**: podgląd miniatur przed wysłaniem, obrót
  zgodny z orientacją EXIF, usuwanie i zmiana kolejności (↑/↓), opis typu
  ujęcia (przód/bok/tył/inne — kolumny `progress_photos.pose`/`position`,
  widoczne też u trenera i na liście zdjęć), pasek postępu per plik
  (upload przez XMLHttpRequest — `uploadFileWithProgress` w api.ts),
  anulowanie w trakcie, ponowienie wyłącznie nieudanych plików. Każde
  zdjęcie jest dopinane do raportu zaraz po udanym uploadzie — przerwanie
  sieci zostawia trwały, widoczny stan częściowy, nie sieroty.
* **Kompresja i EXIF po stronie klienta**: przed wysłaniem zdjęcie
  przechodzi przez createImageBitmap+canvas (maks. 2048 px, JPEG 0.85) —
  co naturalnie usuwa wszystkie metadane EXIF (w tym GPS) już na
  urządzeniu; backendowy strip z P4 (magic bytes, allowlista, limit
  strumieniowy, Pillow re-encode) zostaje jako druga warstwa i jedyna
  dla przeglądarek bez canvas (fallback = oryginał).
* **Korekta raportu**: bez zmian mechaniki (nowa rewizja, poprzednia
  treść w `checkin_revisions`, po ocenie 409) — ale dane skorygowane są
  teraz OZNACZONE: `corrected` w API, badge „skorygowany" u klienta
  i trenera.
* **Wykresy bez interpolacji dziur**: `seriesUtils.withGaps` wstawia
  przerwy w serie o znanym rytmie (samopoczucie — tygodnie bez raportu,
  dziennik kaloryczny — dni bez wpisu), a `Sparkline` renderuje segmenty
  z przerwaną linią zamiast łączyć przez dziurę; pominięte pytania nie
  generują punktów. Punkty samopoczucia niosą `declared` (false = raport
  sprzed rozróżniania stanów — nota o wiarygodności pod wykresem).
* **Prywatność zdjęć zweryfikowana**: zdarzenia audytu raportu/zdjęć
  niosą wyłącznie liczniki (`photos_attached`/`photos_expected`) — zero
  id i nazw plików (test); push bez zmian (neutralne wezwanie); logi
  strukturalne z P9 nadal wyłącznie z szablonami ścieżek.
* Testy: backend 304 → 316 (`test_checkin_quality.py`: cztery stany
  odpowiedzi, walidacja spójności, ścieżka legacy, idempotencja z 409
  i separacją per użytkownik, częściowy upload + dokończenie/zamknięcie,
  odmowy po ocenie/cudzy plik/cudzy raport, pose+kolejność, korekta
  z historią, flaga `declared` w monitoringu, brak wycieku zdjęć do
  audytu; migracja v1→v12 ze stubem `progress_photos`); frontend
  `npm run test:helpers` 7 → 14 (withGaps: dziury tygodniowe/dzienne,
  tolerancja 1,5×, przełom roku, daty niepoprawne).

## 0.14.0 — 2026-08-18

Przebudowa zgód i zgodności z RODO: **zgody granularne per kategoria
danych**, pełna informacja przy każdej zgodzie, kompletniejszy eksport
i usuwanie danych, pakiet dokumentacji RODO.

* **Katalog kategorii zgód** (`consent_catalog.py`, wersja dokumentu
  2.0): 10 odrębnych kategorii — prowadzenie konta, udostępnianie danych
  trenerowi, dane treningowe, komunikacja (wymagane, podstawa umowna)
  oraz dane zdrowotne, żywienie i alergie, zdjęcia progresu,
  przypomnienia/push, funkcje AI, marketing (opcjonalne zgody, art. 9
  dla wrażliwych). Każda kategoria niesie cel, zakres danych, odbiorców,
  okres przechowywania, informację o dobrowolności, sposób wycofania,
  podstawę prawną i wersję dokumentu. Zgody wymagane i opcjonalne nie
  są nigdy łączone; nie istnieje „zaakceptuj wszystko" dla niezależnych
  celów (jedyna decyzja grupowa: warunki jednej umowy o współpracę).
* **Autoryzacja per domena danych**: `resolve_client_access(domain=...)`
  — cofnięcie zgody jednej kategorii odbiera trenerowi dostęp tylko do
  niej (np. cofnięcie „żywienie i alergie" chowa dietę, dziennik
  kaloryczny i pola `alergie`/`preferencje_zywieniowe` profilu, nie
  ruszając planu treningowego). Pliki bramkowane wg kategorii zasobu
  (zdjęcie/dokument-DIETA/załącznik treningu/pozostałe). Agregat
  monitoringu wycina sekcje żywieniową i adherencji bez właściwych zgód.
  Historyczne zgody parasolowe (sprzed migracji) są honorowane w
  pierwotnym, pełnym zakresie — migracja niczego po cichu nie zawęża
  ani nie unieważnia (test).
* **Migracja nr 10**: `consents.category`, `legal_basis`, `source`,
  `denied_at` (czysto addytywna; plan wycofania w `ZGODY_MODEL.md` §7).
* **API zgód**: `GET /api/me/consents` zwraca katalog + historię z
  flagą aktualności wersji dokumentu; `POST /api/me/consents`
  {category, grantee_id}; nowy `POST /api/me/consents/decline` — jawna
  odmowa zgody opcjonalnej z historią (`denied_at`, zdarzenie
  CONSENT_DECLINED); cofnięcie `przypomnienia` usuwa wszystkie
  subskrypcje push; subskrypcja push rejestruje zgodę `przypomnienia`.
* **Zgoda klienta bramkuje funkcje AI**: `POST /api/checkins/{id}/
  ai-summary` wymaga aktywnej zgody `funkcje_ai` PODMIOTU danych —
  decyzja trenera nie zastępuje zgody klienta (dalej propose-only,
  domyślnie NullAIProvider).
* **Onboarding**: trener rejestruje ODRĘBNE deklaracje per kategoria
  (bez przypomnień/AI/marketingu — te tylko od klienta); klient przy
  pierwszym logowaniu potwierdza warunki wymagane i decyduje o każdej
  zgodzie wrażliwej osobno (Wyrażam zgodę / Odmawiam). Zachowane po P3:
  podpięcie istniejącego konta nie nadaje żadnej zgody.
* **Eksport** (JSON + Excel, export_version 1.2): dodane consult_slots,
  push_subscriptions (bez kluczy kryptograficznych subskrypcji),
  audit_receipts, schedule_completions; zgody z pełnym kontekstem
  kategorii/podstawy/wersji.
* **Usunięcie konta** — domknięte luki: usuwane subskrypcje push,
  odpinane sloty konsultacji (przyszłe wracają do puli), anonimizowane
  wolne teksty (cele, przypomnienia, harmonogram, komentarze i notatki
  bólu treningów, tytuły dokumentów, notatki płatności); ewidencja
  rozliczeń (kwoty/terminy/statusy) pozostaje — obowiązek podatkowy.
* **UI klienta**: nowy ekran zgód (onboarding) i karta „Prywatność
  i zgody" w Profilu — stan per kategoria, pełny opis (cel/zakres/
  odbiorcy/okres/wycofanie/wersja), historia decyzji, udzielanie i
  cofanie per kategoria; usunięte nieprawdziwe zdanie „dane nie są
  nikomu dalej przekazywane". Panel trenera: badge „ograniczone zgody"
  z listą brakujących kategorii.
* **Dokumentacja RODO** (docs/): `ZGODY_MODEL.md` (model + migracja +
  plan wycofania + decyzje administratora), `RODO_REJESTR_CZYNNOSCI.md`
  (rejestr czynności, administrator, procesorzy, retencja),
  `RODO_INCYDENTY.md` (proces obsługi incydentów), `RODO_DPIA.md`
  (wskazanie ws. DPIA), polityka prywatności v0.2 (prawdziwy opis
  hostingu Fly.io, adapterów Null poczty/AI, braku płatności online,
  self-hostowanych fontów, push, backupów i retencji; realizacja praw:
  eksport/poprawianie/usunięcie/anonimizacja/rozliczenia). Miejsca
  wymagające decyzji oznaczone „DECYZJA ADMINISTRATORA DANYCH" — to
  nie jest gwarancja prawna.
* Testy: 232 → 244 (nowe: `test_consent_categories.py` — odmowa,
  wersje dokumentu, bramka AI, push↔zgoda, onboarding per kategoria,
  zgoda parasolowa; przebudowane `test_consents.py` — utrata dostępu
  per kategoria; rozszerzone `test_privacy.py` — eksport, usunięcie z
  zachowaniem rozliczeń; migracja v1→v10). Świadomie zaktualizowane
  istniejące testy zbiorczego modelu zgód (szczegóły w ZGODY_MODEL.md).

## 0.13.0 — 2026-08-18

Obsługa błędów i obserwowalność: **koniec cichych awarii** (bez zmian
schematu bazy — zarezerwowana migracja nr 12 nie była potrzebna).
Szczegóły i progi alertowe: `docs/OBSERVABILITY.md`.

* Wspólny model błędów API: `{detail, code, request_id[, errors]}` —
  `detail` pozostaje bezpiecznym polskim komunikatem (kompatybilność
  z frontendem i testami), `code` to stabilny kod (`NOT_FOUND`,
  `VALIDATION_ERROR`, `RATE_LIMITED`…), `request_id` wraca też w nagłówku
  `X-Request-Id` każdej odpowiedzi. Globalne handlery FastAPI:
  `HTTPException`, `RequestValidationError` (422 z listą pól, celowo BEZ
  pydanticowego `input` — wartość mogłaby być daną zdrowotną) oraz
  `ErrorEnvelopeMiddleware` dla nieobsłużonych wyjątków (500 bez stack
  trace/SQL/komunikatów wewnętrznych; nagłówki bezpieczeństwa i no-store
  obejmują też 500). Handler `ResourceAccessDenied` z P3 bez zmian
  (nadal 404 + audyt ACCESS_DENIED, teraz też licznik w metrykach).
* Strukturalne logi backendu (stdout, JSON): request id, metoda + SZABLON
  ścieżki (`/api/clients/{client_id}/...` — nigdy surowe id), status, czas
  odpowiedzi, bezpieczny identyfikator użytkownika (id, nie e-mail).
  Redakcja obowiązkowa: zero danych zdrowotnych, treści wiadomości,
  e-maili, tokenów, endpointów push; wyjątki logowane jako typ + ramki
  stosu `plik:linia:funkcja` BEZ komunikatu (komunikaty ORM potrafią nieść
  parametry SQL). `print()` w push/pętli/seed/audycie zastąpione logiem
  strukturalnym; log e-maili nie zawiera już tematu wiadomości.
* Monitoring: `GET /api/metrics` (tylko ADMIN) — liczniki 2xx/4xx/5xx,
  percentyle czasu odpowiedzi p50/p95/p99 (okno 1000 żądań), błędy pętli
  przypomnień, nieudane pushe, nieobsłużone wyjątki, odmowy dostępu,
  awarie zapisu audytu. `GET /api/ready` (readiness: baza + zapisywalność
  katalogu uploadów, 503 gdy nie; bez sekretów) obok istniejącego
  `/api/health`. Progi alertowe opisane w `docs/OBSERVABILITY.md`
  (dokument + metryki, bez zewnętrznych integracji).
* Błędy JS frontendu: `POST /api/telemetry/frontend-errors` (dostępny bez
  logowania, rate limit 10/min/IP + 120/min globalnie + 5/min klientowo) —
  przyjmuje wyłącznie typ błędu, etykietę komponentu/trasy (id maskowane
  do `{id}`) i stos zredagowany do `plik.js:linia:kolumna`; serwer redaguje
  ponownie (defense in depth) i przechowuje tylko licznik + linię logu.
  Podpięte: globalny i per-trasa `ErrorBoundary` (koniec białego ekranu
  po awarii renderowania — czytelny ekran z „Spróbuj ponownie"),
  `window.onerror`, `unhandledrejection`.
* Frontend — koniec ukrytych `.catch(() => undefined)` (ok. 20 miejsc):
  sekcje pomocnicze (historia treningów, cele, zgody, zdjęcia, monitoring,
  statystyki trenera, pokwitowania, harmonogram, wersje planów, rekordy,
  wykresy siły) pokazują błąd z przyciskiem „Spróbuj ponownie" zamiast
  cicho znikać; nieobsłużone `await` w akcjach (cele, płatności, statusy,
  ocena raportu, weryfikacja audytu, eksporty) dostały obsługę błędów.
  Świadome wyjątki pozostały wyłącznie z komentarzem uzasadniającym
  (karty-podpowiedzi na „Dzisiaj", fail-open bramy zgód — egzekwowanie
  zgód i tak w backendzie, best-effort telemetrii/push/service workera).
* Klient API: timeout żądań 20 s (AbortController) z komunikatem po polsku,
  klasyfikacja offline/timeout/anulowanie (`ApiError.code`), anulowanie
  nieaktualnych żądań przy zmianie widoku/parametru (wątek wiadomości,
  karta klienta, miniatury i załączniki plików, wykresy — spóźniona
  odpowiedź nie nadpisze cudzych danych), 401 → powrót do logowania
  z jednorazowym komunikatem „sesja wygasła" na ekranie logowania.
  Błąd zapisu NIE czyści formularza (trening, cel, ocena raportu —
  komunikat przy formularzu, dane zostają).
* Backend — każdy `except: pass` przejrzany: świadome zignorowania mają
  komentarz uzasadniający (daty historyczne w monitoringu, uszkodzony JSON
  w eksporcie — pole zostaje w surowej postaci zamiast znikać, uszkodzone
  serie w rekordach); pętla przypomnień i push liczą błędy w metrykach.
* Testy: backend 232 → 250 (kształt modelu błędu dla 401/403/404/409/422/
  429/500, request id, redakcja logów i raportów JS, maskowanie ścieżek,
  metryki, readiness, rate limit telemetrii, IDOR w nowym kształcie);
  frontend: `npm run test:helpers` (Node, bez nowych zależności) — logika
  timeout/anulowanie/offline, redakcja stosu, maskowanie id w trasach,
  nazwy plików z Content-Disposition.

## 0.12.0 — 2026-08-18

Runda tożsamości: **zaproszenia z aktywacją konta, bezpieczny reset hasła
i MFA (TOTP)** — koniec hasła startowego widocznego dla trenera.

* **Zaproszenia zamiast hasła startowego**: trener podaje wyłącznie
  e-mail i imię; konto powstaje jako PENDING (bez żadnego hasła, login
  zablokowany), a klient otrzymuje jednorazowy link aktywacyjny
  (`/aktywacja#TOKEN` — token we fragmencie URL, poza logami serwera)
  i SAM ustawia hasło na ekranie aktywacji bez logowania. Token:
  `secrets.token_urlsafe(32)`, w bazie tylko hash SHA-256, ważny 7 dni,
  jednorazowy, anulowalny; ponowne wysłanie unieważnia poprzedni.
  Przepływ P3 dla istniejących kont (relacja bez auto-zgody) bez zmian.
* **Kompromis NullProvider (jawny)**: bez skonfigurowanego dostawcy
  e-mail link aktywacyjny wraca trenerowi w UI jako „link do
  przekazania”; ze skonfigurowanym dostawcą idzie wyłącznie e-mailem
  (trener go nie widzi) — opisane w PERMISSIONS.md.
* **Bezpieczny reset hasła**: `/reset-hasla` — żądanie z ogólnym
  komunikatem niezależnym od istnienia konta (bez enumeracji), limit
  prób per e-mail+IP, token hashowany (SHA-256) ważny 60 min,
  jednorazowy, nowszy unieważnia starszy; po resecie unieważnienie
  WSZYSTKICH sesji konta. Link wyłącznie e-mailem (przy NullProviderze
  reset wymaga skonfigurowanego dostawcy — świadomie bez linku w API).
* **MFA (TOTP RFC 6238)** w czystym Pythonie (stdlib hmac/struct, zero
  zależności): sekret base32 + URI `otpauth://` (tekst do przepisania /
  otwarcia w aplikacji), potwierdzenie kodem, logowanie dwuetapowe
  (wyzwanie 5 min, tylko hash w bazie), okno ±1 kroku z ochroną przed
  ponownym użyciem kodu (licznik ostatniego okna), limit prób i audyt
  nieudanych weryfikacji. **Obowiązkowe dla COACH/ADMIN**
  (`DZIK_MFA_REQUIRED_ROLES`): do pierwszej konfiguracji konto ma dostęp
  wyłącznie do ekranu konfiguracji MFA (403 `MFA_SETUP_REQUIRED`,
  wzorzec jak wymuszona zmiana hasła), wyłączenie zablokowane; dla
  CLIENT opcjonalne. WebAuthn/passkeys opisane w PERMISSIONS.md jako
  następny krok (świadomie nieimplementowane).
* **Kody odzyskiwania**: 10 jednorazowych kodów pokazywanych tylko raz
  (w bazie hashe), logowanie kodem audytowane z liczbą pozostałych,
  regeneracja za kodem TOTP unieważnia wszystkie stare.
* **Historia bezpieczeństwa konta**: `GET /api/auth/security-events`
  (logowania, nieudane MFA, resety, kody, zakończenia sesji — metadane
  bez tokenów) jako karta obok „Aktywnych sesji” (Profil / Więcej).
* **E-maile bez danych zdrowotnych**: naprawiony e-mail o niepokojącej
  obserwacji (wysyłał kategorię i pełną treść wpisu) — teraz neutralne
  wezwanie do panelu; treści zaproszeń/resetów projektowane bez PII
  zdrowotnego i potwierdzone testami.
* Migracja schematu nr 11 (kolumny `users.totp_*`, tabele
  `client_invitations`, `password_reset_tokens`, `mfa_recovery_codes`,
  `mfa_challenges`) — addytywna, plan wycofania w PERMISSIONS.md. Nowe
  ustawienia: `DZIK_INVITATION_TTL_DAYS`, `DZIK_RESET_TOKEN_TTL_MIN`,
  `DZIK_RESET_MAX_REQUESTS`, `DZIK_RESET_WINDOW_MIN`,
  `DZIK_MFA_REQUIRED_ROLES`, `DZIK_MFA_CHALLENGE_TTL_MIN`,
  `DZIK_PUBLIC_URL`.
* UI: ekran aktywacji, ekran resetu (żądanie + nowe hasło), krok MFA w
  logowaniu (kod TOTP/odzyskiwania), wymuszony ekran konfiguracji MFA
  (`/mfa`), karta MFA w Profilu klienta i w „Więcej” trenera/admina,
  formularz „Zaproś podopiecznego” bez pola hasła + status „oczekuje na
  aktywację” z ponowieniem/anulowaniem zaproszenia, link „Nie pamiętasz
  hasła?”.
* Konta demo seedu pozostają aktywne z hasłami z seedu (nowy przepływ
  dotyczy kont zakładanych przez UI/API); stare testy hasła startowego
  przepisane świadomie na przepływ zaproszeń (mechanizm
  `must_change_password` zachowany dla kont historycznych i nadal
  testowany).
* Testy: 232 → 256 (zaproszenia: ważne/wygasłe/ponowne
  użycie/anulowanie/ponowienie/izolacja trenerów/brak tokenu w audycie;
  reset: brak enumeracji, jednorazowość, wygaśnięcie, unieważnienie
  sesji, limit prób; MFA: wektor RFC, dobry/zły kod, okno czasowe,
  replay, kody odzyskiwania, wymuszenie dla trenera, opcjonalność dla
  klienta, sekrety poza audytem; historia bezpieczeństwa).

## 0.11.1 — 2026-08-18

* **Harmonogram kopii zapasowych (R-12, operacyjnie)**: nowy workflow
  `.github/workflows/fly-backup.yml` — codzienny backup na maszynie
  Fly.io (02:30 UTC) + uruchomienie na żądanie; archiwa na wolumenie
  `/data/backups` (retencja 14), bez pobierania danych do artefaktów
  GitHub Actions. Dokumentacja §4a zaktualizowana.

## 0.11.0 — 2026-08-18

Zamknięcie dwóch ryzyk z rejestru: R-12 (kopie zapasowe) i R-02 w części
plikowej (szyfrowanie at-rest uploadów).

* **Kopie zapasowe (R-12 — zamknięte)**: nowe narzędzie
  `python -m dzik_os.backup` tworzy jedno spójne, znakowane czasem
  archiwum `dzik-backup-<timestamp>.tar.gz`: główna baza przez sqlite3
  backup API (PostgreSQL: `pg_dump`, wykrywane z `DZIK_DATABASE_URL`),
  baza audytu Human OS (`audit.db`, też backup API) i katalog uploadów
  w postaci, w jakiej leży na dysku (czyli zaszyfrowanej). Retencja
  `DZIK_BACKUP_KEEP` (domyślnie 14), katalog `DZIK_BACKUP_DIR`
  (domyślnie `data/backups`). Odtwarzanie `--restore <archiwum>`
  z odmową nadpisania istniejących danych bez `--force`; po odtworzeniu
  łańcuch audytu jest weryfikowany (`verify_chain()`) i wynik jawnie
  raportowany. Pełny cykl backup → utrata danych → restore → weryfikacja
  łańcucha pokryty testem; harmonogram i snapshoty wolumenów Fly opisane
  w DEPLOYMENT §4a.
* **Szyfrowanie plików at-rest (R-02 — część plikowa zamknięta)**:
  uploady szyfrowane AES-256-GCM przy zapisie i deszyfrowane przy
  odczycie (`storage.py`), klucz z env `DZIK_FILE_KEY` (base64,
  32 bajty). Zaszyfrowane pliki mają nagłówek magiczny `DZIKENC1`;
  pliki wgrane przed włączeniem klucza czytane są wprost (kompatybilność
  wsteczna). Brak klucza = zachowanie dotychczasowe plus jedno
  ostrzeżenie w logu poza dev/test; zaszyfrowany plik bez klucza lub
  z błędnym kluczem to jawny błąd 500, błędny format klucza zatrzymuje
  start — tryby nigdy nie mieszają się po cichu. Klucz przechowywać
  OSOBNO od backupów (DEPLOYMENT §4b). Nowa zadeklarowana zależność
  backendu: `cryptography>=42,<47`. Otwarta pozostaje część bazodanowa
  R-02 (dysk szyfrowany / pgcrypto; wolumeny Fly szyfrowane blokowo).
* Testy: 97 → 115 (backup/restore/retencja, szyfrowanie — roundtrip,
  plik legacy, praca bez klucza; testy uploadów przechodzą w obu
  trybach przez sparametryzowaną fixture).

## 0.10.1 — 2026-08-18

Audyt i utwardzenie **całego systemu plików** (bez zmian schematu bazy).

* Naprawa pobierania z frontendu: wszystkie bezpośrednie linki do
  chronionych `/api/files/{id}` (PDF diety w Dieta, „Otwórz" w
  Dokumentach) zastąpione wspólnym `FileDownloadButton` — pobranie przez
  uwierzytelnione API do Blob, zapis/otwarcie klikiem w `<a>` (bez
  blokady popupów), poprawna nazwa z `Content-Disposition`, zawsze
  `URL.revokeObjectURL`; widoczne stany pobieranie/sukces/błąd/brak
  dostępu (także w `AuthAttachment`).
* Dieta: `document_id` (FK do `documents`) był wysyłany do frontendu
  jako rzekome id pliku — API zwraca teraz dodatkowo
  `document_file_id` (id pliku aktywnego dokumentu), a `document_id`
  jest walidowane przy tworzeniu wersji (dokument musi być ACTIVE i
  należeć do klienta planu).
* Upload: rozpoznawanie typu po ZAWARTOŚCI (magic bytes: PDF/PNG/JPEG/
  WEBP/MP4/WEBM/MP3/OGG) — niezgodność deklaracji z zawartością = 415
  (odrzuca m.in. `plik.pdf.exe`); limit rozmiaru egzekwowany
  strumieniowo; sanityzacja nazwy z wymuszonym kanonicznym rozszerzeniem;
  SVG i pliki wykonywalne poza allowlistą (jak dotąd) + potwierdzone
  testami.
* Zdjęcia (NOWE uploady image/*): usunięcie WSZYSTKICH metadanych EXIF
  (w tym GPS) z zachowaniem orientacji, dłuższy bok maks. 2560 px,
  rekompresja (jakość 85, Pillow). Istniejące pliki na dysku pozostają
  bez zmian (świadomie: bez retroaktywnego przetwarzania).
* Pobieranie: `Content-Disposition` wg RFC 5987 (sanityzowana nazwa),
  `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`;
  weryfikacja, że `storage_path` nie wychodzi poza katalog uploadów
  (path traversal = 404).
* Autoryzacja pobrania domknięta dla WSZYSTKICH ścieżek: właściciel;
  trener przez relację+zgodę (`resolve_client_access` — cofnięcie zgody
  odbiera dostęp też do ISTNIEJĄCYCH plików, test); załącznik wątku
  (klient zawsze, trener tylko przy AKTYWNEJ relacji); załącznik
  AKTYWNEGO wpisu bazy wiedzy dla aktywnie prowadzonych klientów
  (wcześniej klienci dostawali 404).
* Podpinanie plików walidowane wszędzie (`require_attachable_file`):
  wiadomości, zdjęcia raportu (limit 8 szt. / 60 MB łącznie, tylko
  obrazy własne), dokumenty (plik musi należeć do klienta), baza wiedzy
  (tylko plik własny trenera), wpisy treningowe — koniec z podpinaniem
  cudzych `file_id`.
* Pliki-sieroty: upload bez żadnej referencji po 24 h dostaje soft
  delete (`deleted_at`) i znika z dysku (pętla co godzinę + pierwszy
  przebieg po starcie; zdarzenie audytowe ORPHAN_FILES_CLEANED).
* Nowa zależność backendu: Pillow (>=10,<12). Nowe ustawienia:
  `DZIK_MAX_IMAGE_PX`, `DZIK_IMAGE_QUALITY`, `DZIK_MAX_CHECKIN_PHOTOS`,
  `DZIK_MAX_CHECKIN_PHOTOS_TOTAL_MB`, `DZIK_ORPHAN_FILE_TTL_H`.
* Testy: 113 → 134 (magic bytes, podwójne rozszerzenie, path traversal,
  EXIF, limity, cofnięta zgoda, wygasła relacja, baza wiedzy, sieroty,
  soft delete, nagłówki odpowiedzi).


## 0.10.0 — 2026-08-18

Runda bezpieczeństwa sesji: **serwerowe unieważnianie, rotacja tokenów,
ekran aktywnych sesji** (audyt wylogowania bez nagłówka autoryzacji).

* Naprawa audytowanej luki: wylogowanie szło gołym `fetch` bez nagłówka
  `Authorization`, więc serwer unieważniał co najwyżej sesję z ciasteczka
  (przy kilku kartach — potencjalnie cudzą kartę, nie bieżącą). Wszystkie
  operacje uwierzytelniania przechodzą teraz przez wspólnego klienta API
  (`api.ts`: `login`/`logout`/`changePassword`/`listSessions`/…); lokalne
  czyszczenie sesji działa też przy utracie połączenia (`finally`).
* Zmiana hasła = rotacja tokenu: serwer unieważnia WSZYSTKIE dotychczasowe
  sesje (z bieżącą włącznie) i wydaje nowy token — zero aktywnych starych
  tokenów; ponowne użycie unieważnionego tokenu to zawsze 401. Limit prób
  zmiany hasła (`password_change_rate_limiter`) analogiczny do logowania.
* Nowe endpointy: `GET /api/auth/sessions` (aktywne sesje: utworzona,
  ostatnie użycie, urządzenie, bieżąca oznaczona — bez tokenów/hashy),
  `POST /api/auth/sessions/{id}/revoke` (własna sesja; cudza = 404),
  `POST /api/auth/sessions/revoke-others`. Zdarzenia audytowe:
  SESSION_LOGGED_OUT, SESSION_REVOKED, SESSIONS_REVOKED, rozszerzone
  PASSWORD_CHANGED (forced/sessions_revoked/token_rotated — bez sekretów).
* `auth_sessions.last_used_at` (migracja nr 9, zapis z rozdzielczością
  ~5 min); w bazie nadal wyłącznie hash SHA-256 tokenu (potwierdzone
  testem i udokumentowane w PERMISSIONS.md, sekcja „Sesje i tokeny" —
  wraz ze świadomą decyzją o pozostaniu przy Bearer + sessionStorage
  i planem ewentualnej migracji na ciasteczka httpOnly z CSRF).
* UI: karta „Aktywne sesje" w Profilu klienta i w „Więcej"
  trenera/admina (zakończ wybraną / wyloguj z pozostałych urządzeń).
* Testy: 113 → 127 (wylogowanie Bearer i cookie, ponowne użycie
  unieważnionego tokenu, rotacja, wygaśnięcie, zakończenie sesji,
  izolacja cudzych sesji, limit prób, żądania równoległe, brak sekretów
  w audycie i bazie).

## 0.9.1 — 2026-08-18

Naprawa obsługi dat i stref czasowych w całej aplikacji.

* Błąd: daty kalendarzowe (`performed_on`, `logged_on`, `occurred_on`,
  `week_start`, `measured_at`...) liczone przez
  `new Date().toISOString().slice(0, 10)` (frontend) lub
  `datetime.now(UTC).date()` (backend) — rekord utworzony 18 sierpnia
  o 01:00 czasu polskiego trafiał do bazy z datą 17 sierpnia.
* Jeden wspólny moduł dat po obu stronach: `frontend/src/dates.ts`
  (`localToday()`, `mondayOfWeek()`, `localNowMinute()`, `parseApiDate()`,
  `plDate`/`plDateTime`/`WEEKDAYS` przeniesione z `api.ts`) i
  `backend/dzik_os/dates.py` (`local_today()`, `local_now()`,
  `local_now_minute()`, `tz_for_user()`); rozproszona logika usunięta
  (`todayIso`, `mondayOfCurrentWeek`, `_now_local` w konsultacjach).
* Przyjęty model dat: data kalendarzowa użytkownika = `YYYY-MM-DD`
  w strefie LOKALNEJ (frontend: strefa przeglądarki, backend: `DZIK_TZ`,
  domyślnie Europe/Warsaw); dokładny moment zdarzenia (`created_at`,
  `paid_at`, audyt) = pełny timestamp UTC (`now_iso()`), przeliczany do
  strefy dopiero przy prezentacji; termin konsultacji = naiwny lokalny
  `YYYY-MM-DDTHH:MM` porównywany wyłącznie z lokalnym „teraz".
  Szczegóły: docstring `dzik_os/dates.py` i sekcja „Konwencje dat"
  w `DATA_MODEL.md`.
* Naprawione porównania: flagi `checkin_overdue`/`payment_overdue`
  (lista klientów + dashboard trenera), status OVERDUE u klienta i na
  Dzisiaj, okno „nowego rekordu" (14 dni), zakresy monitoringu/adherencji/
  dziennika żywieniowego, `days_remaining` celu, ekran Dzisiaj
  (dzień tygodnia, harmonogram, przypomnienia), licznik nadchodzących
  konsultacji na dashboardzie (porównywał lokalny `starts_at` z czasem
  UTC) i filtr „nadchodzące" w konsultacjach trenera; `parseApiDate`
  parsuje `YYYY-MM-DD` jako lokalną północ (bez ryzyka przesunięcia dnia
  przy prezentacji).
* Architektura gotowa na strefę per użytkownik: `tz_for_user(user)`
  honoruje przyszłe pole `User.timezone` (dziś zawsze `DZIK_TZ`); bez UI
  i bez migracji schematu.
* Migracji danych historycznych NIE wykonano świadomie: po fakcie nie da
  się bezpiecznie odróżnić daty zapisanej błędnie (wpis z 00:00–02:00
  czasu polskiego) od poprawnej — przesuwanie rekordów hurtem
  uszkodziłoby dane wpisane w ciągu dnia (>95% przypadków).
* Testy: 113 → 128 (`tests/test_dates.py`: granica północy 00:30/01:00,
  czas letni/zimowy, obie zmiany DST, koniec miesiąca i roku, strefa
  z konfiguracji i per użytkownik, parsowanie dat z API). Logika
  `dates.ts` zweryfikowana skryptem Node z `TZ=Europe/Warsaw` (frontend
  nie ma infrastruktury testowej JS — ograniczenie opisane w raporcie).

## 0.9.0 — 2026-08-18

Runda 6b.7 specyfikacji: **terminarz konsultacji**.

* Tabela `consult_slots` (migracja nr 8): trener wystawia terminy
  (data+godzina, czas trwania), klient rezerwuje i odwołuje (do 12 h
  przed terminem; trener może odwołać w każdej chwili). Rezerwacje
  zawsze odwoływalne — bez kar i metryk za odwołania.
* Push przy rezerwacji/odwołaniu (obie strony), zdarzenia audytowe
  CONSULT_SLOT_CREATED/BOOKED/UNBOOKED/CANCELLED.
* UI: `/trener/konsultacje` (formularz + lista z odwołaniem, link w
  Więcej), `/konsultacje` u klienta (rezerwacje + wolne terminy, link w
  Więcej), karta „Najbliższa konsultacja" na Dzisiaj, licznik
  nadchodzących konsultacji na dashboardzie trenera.
* Izolacja: klient widzi wyłącznie terminy trenerów, którzy go aktywnie
  prowadzą; rezerwacja cudzego slotu = 404.
* Testy: 108 → 113.

## 0.8.0 — 2026-08-18

Runda 6b.6 specyfikacji: **strukturalny dziennik serii + wykresy siły**.

* `workout_entries.sets_json` (migracja nr 7): serie jako ciężar ×
  powtórzenia obok dotychczasowego tekstowego wyniku (kompatybilność
  wstecz — stare zapisy działają dalej).
* Logowanie treningu u klienta: szybkie wiersze serii (kg × powt.,
  „+ seria" kopiuje poprzednie wartości) + opcjonalna notatka tekstowa.
* Nowy endpoint `GET /clients/{id}/strength-series`: per ćwiczenie
  objętość dnia (suma kg×powt.) i najlepszy szacowany 1RM dnia (wzór
  Epleya — opisany w UI jako szacunek do obserwacji trendu, nie
  zalecenie obciążenia).
* Karta „Siła w czasie" (wybór ćwiczenia + dwa wykresy) na Postępach
  klienta i w Monitoringu trenera; rekordy osobiste liczą się teraz
  najpierw ze strukturalnych serii, potem z tekstu.
* Seed: treningi klienta A zapisane strukturalnie (progresja przysiadu
  95→105 kg widoczna na wykresie od pierwszego uruchomienia).
* Testy: 105 → 108.

## 0.7.0 — 2026-08-18

Runda 6b.5 specyfikacji: **powiadomienia push (PWA)**.

* Web Push z kluczami VAPID generowanymi automatycznie i trwałymi na
  wolumenie danych (zero sekretów w repo); tabela `push_subscriptions`
  (migracja nr 6), jawny opt-in w Profilu (klient) / Więcej (trener),
  wyłączane jednym przyciskiem; zdarzenia PUSH_SUBSCRIBED/UNSUBSCRIBED
  w audycie.
* Powiadomienia przy: nowej wiadomości (bez treści!), odpowiedzi trenera
  na raport, nowym raporcie od klienta (do trenera), nowej wersji planu.
* Pętla przypomnień (co 60 s, strefa DZIK_TZ): elementy harmonogramu z
  ustawioną porą + jednorazowe przypomnienia trenera o 08:00; dedup per
  dzień. Wymaga stale działającej maszyny — `min_machines_running = 1`
  w fly.toml (koszt: kilka USD/mies., opisany w komentarzu).
* Zasady: treść push nigdy nie zawiera danych zdrowotnych ani treści
  wiadomości; liczba wysłanych powiadomień nie jest metryką niczego.
* Testy: 100 → 105 (subskrypcje, triggery z podmienioną wysyłką,
  pętla przypomnień z dedupem).

## 0.6.0 — 2026-08-18

Runda 6a wg zatwierdzonej specyfikacji (docs/SPEC_NASTEPNE_RUNDY.md;
punkty 10–11 z listy propozycji świadomie poza zakresem).

* **Kopiowanie szablonu do klienta**: `POST /api/plans/{id}/copy-to/{client}`
  — bieżąca wersja szablonu staje się v1 nowego, NIEZALEŻNEGO planu
  klienta (późniejsza edycja szablonu nie zmienia planów klientów);
  w karcie klienta wybór „Z szablonu…" + „Kopiuj do klienta".
* **Porównywarka zdjęć „przed / po"**: zestawienie dwóch zdjęć sylwetki
  z wyborem dat (domyślnie najstarsze vs najnowsze) — u klienta na
  Postępach, u trenera w Monitoringu. Wyłącznie własna historia.
  Seed: dwa syntetyczne zdjęcia demo dla klienta A.
* **Timer przerw**: przy każdym ćwiczeniu z zapisaną przerwą przycisk ⏱
  odlicza czas (obsługa „120 s"/„2 min"/„90"), wibracja na koniec;
  czysto lokalny, niczego nie zapisuje.
* **Wywiad startowy** (`/ankieta`): strukturalna ankieta klienta (cel →
  cel główny, doświadczenie, dni, sprzęt, preferencje/alergie/kontuzje
  jako pola wrażliwe) zasilająca profil append-only z proweniencją
  CLIENT_DECLARED; baner-zaproszenie na Dzisiaj, dopóki profil pusty.
* Testy: 97 → 100 (kopiowanie szablonu: niezależność kopii, izolacja
  trenerów, blokada klienta).

## 0.5.2 — 2026-08-18

* **Powitanie na ekranie logowania**: pod logo ciepłe zaproszenie
  („Cześć, dobrze Cię widzieć! 💪 Zaloguj się — Twój plan, dieta i
  wiadomości od trenera czekają w jednym miejscu.").
* **PWA — świeża wersja przy każdym otwarciu**: nawigacje przełączone na
  network-first (cache tylko jako fallback offline) — użytkownik nie
  utknie już na starej wersji aplikacji do czasu kliknięcia banera;
  otwarcie/odświeżenie to naturalny moment aktualizacji, więc zasada
  „bez cichej podmiany kodu w trakcie sesji" pozostaje zachowana.
  Statyki nadal cache-first; /api nigdy nie jest cachowane. Cache
  podbity do v2.

## 0.5.1 — 2026-08-18

* **Duże logo na ekranie logowania**: pełna grafika marki (głowa dzika +
  wordmark „DZIK OS") w wysokiej rozdzielczości (900 px, spłaszczona
  paleta — 59 KB) zamiast małej ikonki z tekstem; napis „DZIK"
  przebarwiony na jasny wariant do ciemnego tła (czarny znikał na
  czarnym), „OS" pozostaje zielone. Znak nawigacji podbity do 512 px
  (ostrość na ekranach retina).
* **Symulowani klienci demo (C–E)** — panel trenera od razu pokazuje
  realną pracę: Marek Dziczek (raport czeka na ocenę + nieprzeczytana
  wiadomość), Anna Wilk (praca trenera wykonana: raport oceniony 4/5,
  odpowiedź w wątku, płatność opłacona, trend −2 kg), Piotr Zając
  (brak raportu, przeterminowana płatność, niepokojąca obserwacja
  kolana). Dashboard: 5 aktywnych klientów z pełnym przekrojem flag.

## 0.5.0 — 2026-08-18

* **Nowość — Rekordy osobiste i postęp od startu** (rywalizacja wyłącznie
  z własną historią, na życzenie użytkownika; zgodna z zasadą Human OS —
  żadnych porównań między ludźmi ani rankingów):
  `GET /api/clients/{id}/personal-records` liczy per ćwiczenie najlepszy
  własny ciężar (deterministyczny regex po tekstowych wynikach treningów,
  np. „3x8 @ 80kg"; wynik bez rozpoznawalnego ciężaru jest pomijany —
  zero zgadywania) z plakietką „nowy rekord!" gdy poprawiony w ostatnich
  14 dniach względem wcześniejszego własnego wyniku, oraz zmianę każdego
  pomiaru względem pierwszego zapisu („−4,2 kg od startu"). Karta
  „🏆 Rekordy osobiste" w Monitoringu klienta i w zakładce Monitoring
  trenera. Seed: 3 treningi klienta A z progresją przysiadu.
* Testy: 92 → 97.

## 0.4.1 — 2026-08-17

* **Logo**: zastąpiono wygenerowaną wcześniej prostą ikonę dzika docelową
  grafiką dostarczoną przez założyciela (szczegółowy maskotkowy portret
  głowy dzika + wordmark „DZIK OS"). Sama głowa (bez wordmarku, przycięta
  do kwadratu) jest teraz jedynym źródłem `Logo()` w UI oraz ikon PWA
  (`icon-192.png`/`icon-512.png` na ciemnym zaokrąglonym tle, favicon).

## 0.4.0 — 2026-08-17

Baza wiedzy trenera rozszerzona o know-how ćwiczeń i produktów, kompozytor
diety, ocena raportu i dashboard trenera; nowe logo z motywem dzika.

* **Nowość — logo z motywem dzika**: nowy znak (głowa dzika w profilu:
  ucho, ryj, kieł) zastępuje poprzedni abstrakcyjny zygzak — `Logo()`,
  ikony PWA (`icon.svg`/192/512) i favicon zaktualizowane.
* **Nowość — Baza ćwiczeń (know-how trenera)**: model `Exercise` z
  podziałem na partie mięśniowe (nogi/plecy/klatka/barki/ręce/brzuch/
  całe ciało/mobilność), techniką wykonania i efektem; CRUD trenera,
  broadcast do aktywnie prowadzonych klientów (ten sam wzorzec co Baza
  wiedzy) — nowa zakładka „Ćwiczenia" w panelu trenera i u klienta.
* **Nowość — Baza produktów z makro**: model `FoodProduct` (kcal/białko/
  tłuszcz/węglowodany na 100 g); zakładka „Produkty" z polem porcji (g),
  które na bieżąco przelicza kalorie i makro — po stronie trenera i
  klienta. Seed: ~40 typowych produktów w 8 kategoriach.
* **Nowość — Kompozytor diety** (propose-only): trener podaje cel kcal +
  makro i wybiera produkty z własnej bazy; `/api/coach/diet-suggestion`
  zwraca przejrzysty, deterministyczny podział celu na gramaturę wg
  dominującego makroskładnika każdego produktu (nigdy AI, nigdy
  automatyczna generacja diety) — wynik jest tylko sugestią do ręcznego
  wpisania w plan żywieniowy klienta, niczego nie zapisuje automatycznie.
* **Nowość — Ocena raportu przez trenera**: opcjonalna ocena 1-5 obok
  odpowiedzi na raport tygodniowy (`WeeklyCheckin.rating`) — dotyczy
  kompletności/jakości samego raportu, nie jest oceną osoby (zasada
  Human OS: system nie rankinguje ludzi); widoczna dla obu stron.
* **Nowość — Dashboard trenera**: `GET /api/coach/dashboard` agreguje
  metadane operacyjne (aktywni klienci, raporty do oceny, zaległe
  raporty/płatności, nieprzeczytane wiadomości, obserwacje) na górze
  listy klientów; nowa flaga i filtr „Raport do oceny".
* Migracja schematu nr 5 (`weekly_checkins.rating`, tabele `exercises`,
  `food_products`).
* Testy: 74 → 92 (ćwiczenia, produkty, kompozytor diety, ocena raportu,
  dashboard).

## 0.3.0 — 2026-08-17

Czytelność raportów, baza wiedzy, propozycje AI, aktualizacje PWA i
odświeżony design — na podstawie bezpośredniej informacji zwrotnej.

* **Raport tygodniowy w sekcjach**: formularz klienta i widok trenera
  podzielone na „Ciało", „Samopoczucie", „Ból/komentarz/pytania" —
  ocena raportu bez przewijania jednej długiej listy pól.
* **Nowość — podsumowanie AI raportu** (propose-only): przycisk w
  panelu trenera generuje streszczenie + szkic odpowiedzi do edycji;
  domyślnie `NullAIProvider` pokazuje jawny komunikat „wymaga
  konfiguracji" zamiast udawać działanie. Żadna odpowiedź nie trafia do
  klienta bez zatwierdzenia przez trenera.
* **Nowość — Baza wiedzy**: trener publikuje materiały (artykuł, link,
  plik) widoczne dla wszystkich aktywnie prowadzonych klientów; pełny
  CRUD (dodaj/edytuj/archiwizuj/przywróć), kategorie, przypinanie.
  Osobna oś uprawnień od danych zdrowotnych (to treść trenera, nie
  dane klienta) — patrz PERMISSIONS.md.
* **Nowość — aktualizacje PWA**: baner „Dostępna nowa wersja" zamiast
  cichej podmiany kodu aplikacji pod użytkownikiem w trakcie sesji;
  użytkownik sam decyduje, kiedy odświeżyć.
* **Design**: typografia Unbounded (nagłówki) + Inter (treść, cyfry
  tabelaryczne); warstwowe tło zamiast płaskich kart (surface staircase);
  delikatna poświata na kartach-bohaterach (trening dnia, cel); wykresy
  ze zanikającym wypełnieniem pod linią; mikrointerakcje (naciśnięcie
  przycisku, wejście karty) z pełnym poszanowaniem
  `prefers-reduced-motion`; wypełnione plakietki akcentu dla wyróżnień.
* Domyślny zakres trendów w Monitoringu skrócony z 90 do 30 dni —
  czytelniejszy, bardziej typowy okres.
* Migracja schematu nr 4 (`knowledge_items`) — bezpieczna dla istniejącej
  bazy.
* Testy: 65 → 74 backendu (275 Core bez zmian).

## 0.2.0 — 2026-08-17

Monitoring w czasie — na podstawie analizy rynku (`ANALIZA_RYNKU.md`) i
wniosku, że regularny monitoring pozwala wcześniej wychwycić niekorzystne
reakcje, a nie tylko śledzić postępy.

* **Nowość — Monitoring i postępy** (klient, `/postepy`) i zakładka
  **Monitoring** (trener): cel z odliczaniem dni, trendy pomiarów i
  samopoczucia (sen/energia/stres/głód/regeneracja z raportów), dziennik
  kaloryczny na tle celu z diety, realizacja harmonogramu per kategoria
  (pasek % zamiast surowych liczb), dziennik obserwacji.
* **Nowość — adherencja harmonogramu**: przycisk „Wykonane" na ekranie
  Dzisiaj dla każdego elementu harmonogramu (nie tylko treningu);
  idempotentne odhaczenie per dzień (`schedule_completions`).
* **Nowość — dziennik obserwacji** (`observations`): klient zgłasza
  samopoczucie lub reakcję (opcjonalnie powiązaną z suplementem/posiłkiem
  z harmonogramu), oznaczając wagę Informacja/Niepokojące. System **nigdy
  nie interpretuje ani nie diagnozuje** — wyłącznie zapisuje dosłownie i
  flaguje NIEPOKOJACE w panelu trenera (nowy filtr i badge na liście
  klientów) oraz — jeśli skonfigurowany dostawca — e-mailem.
* **Nowość — dziennik kaloryczny** (`daily_nutrition_logs`): szybki wpis
  kcal/wody na tle celu z aktywnej diety.
* **Nowość — eksport do Excela** (`/api/me/export.xlsx`, przycisk w
  Profilu): ten sam komplet danych co eksport JSON, jeden arkusz na
  tabelę.
* **Nowość — wiadomości głosowe**: nagrywanie w przeglądarce
  (MediaRecorder) i wysyłka jako załącznik; poprawiony też odbiór
  załączników dowolnego typu w wątku (wcześniej wszystko renderowało się
  jak obraz — PDF/wideo/audio wyświetlały się poprawnie po typie z
  serwera, nie po nazwie pliku).
* **Nowość — adapter powiadomień e-mail** (`notifications_provider.py`,
  wzorzec jak `payments_provider.py`): domyślnie `NullNotificationProvider`
  (nic nie wysyła, brak PII w logach); gotowy interfejs do podłączenia
  Resend/SendGrid/Mailgun/SMTP decyzją operatora.
* Migracja schematu nr 3 (trzy nowe tabele monitoringu) — bezpieczna dla
  istniejącej bazy (w tym produkcyjnej na Fly), testowana regresyjnie.
* Eksport JSON i procedura usunięcia danych objęły nowe tabele.
* Testy: 55 → 65 (adherencja, obserwacje z flagą, dziennik kaloryczny,
  eksport Excel, upload audio, migracja v1→v3).

## 0.1.1 — 2026-08-17

Runda poprawek po pełnym przekliku aplikacji + przygotowanie PaaS.

* **Naprawa**: eksport danych z poziomu Profilu pobiera plik JSON
  (wcześniej przycisk kończył się błędem po stronie przeglądarki).
* **Naprawa**: załącznik wysłany przez trenera w wiadomości jest widoczny
  dla klienta (dostęp dla stron wątku; osoby trzecie nadal 404) — test.
* **Bezpieczeństwo (R-06 zamknięte)**: konto założone przez trenera musi
  zmienić hasło startowe przy pierwszym logowaniu — blokada egzekwowana
  serwerowo (PASSWORD_CHANGE_REQUIRED), nowy ekran zmiany hasła, zmiana
  unieważnia pozostałe sesje (zdarzenie PASSWORD_CHANGED w audycie).
* **Zgody (R-05 zamknięte)**: klient przy pierwszym logowaniu jawnie
  potwierdza zgodę zarejestrowaną przy onboardingu (ekran „Twoje dane,
  Twoja zgoda"; CONSENT_CONFIRMED w łańcuchu audytu) albo odmawia;
  zgody nadawane samodzielnie są potwierdzone od razu.
* Migracja schematu nr 2 (`users.must_change_password`,
  `consents.confirmed_at`) — mechanizm migracji obsługuje istniejące bazy
  (ALTER) i świeże (stempel), z testem regresyjnym.
* Konfiguracja PaaS: `fly.toml` + instrukcja wdrożenia na Fly.io
  (darmowa subdomena z HTTPS; własna domena do dodania później).
* Testy: 50 → 55 (wymuszona zmiana hasła, potwierdzanie zgód, załączniki
  wątków, migracja v1→v2).

## 0.1.0 (MVP) — 2026-08-17

Pierwsze wydanie „Dzik OS — Panel Podopiecznego".

* Import fundamentów Human OS (`human-os@68fe1e4`) do `human-os2`
  (ADR-DZIK-003); regresja Core: 275 testów zielonych, zero zmian w Core.
* Backend FastAPI: uwierzytelnianie sesyjne (bcrypt, rate limiting),
  role COACH/CLIENT/ADMIN, relacje trener–klient, profil z wersjonowanymi
  polami i proweniencją, cele, plany treningowe i żywieniowe z
  niemutowalnymi wersjami (powód zmiany obowiązkowy), harmonogram z
  autorem zalecenia, raporty tygodniowe z rewizjami i odpowiedzią trenera,
  pomiary, wiadomości z załącznikami, dokumenty i zdjęcia (walidowany
  upload), płatności z adapterem operatora, zgody (decyzja w
  hos_engine.ConsentRegistry), eksport JSON, anonimizacja konta,
  audyt hash-chained (SQLiteEventStore) z pokwitowaniami.
* Frontend: mobile-first PWA po polsku (React+TS+Vite), aplikacja klienta
  (Dzisiaj/Plan/Dieta/Raport/Pomiary/Wiadomości/Płatności/Profil) i panel
  trenera (lista z flagami operacyjnymi, karta klienta z 8 zakładkami,
  szablony), panel admina (konta + weryfikacja łańcucha audytu).
* Dane demo (syntetyczne): trener, 2 klientów, admin, plany, dieta,
  raport, pomiary, wiadomości, dokument, płatności.
* Testy: 50 backend (izolacja, wersjonowanie, zgody, prywatność, uploady,
  płatności, audyt, E2E ścieżek) + 3 E2E przeglądarkowe (Playwright).
* Infrastruktura: Dockerfile, Docker Compose (PostgreSQL), .env.example,
  CI GitHub Actions (lint, testy Core i aplikacji, build frontendu).

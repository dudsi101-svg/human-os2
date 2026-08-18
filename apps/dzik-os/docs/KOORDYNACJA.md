# Koordynacja rund — jedna sesja naraz

## ZASADA NADRZĘDNA (decyzja właściciela produktu, 2026-08-18)

> **W jednym momencie pracuje JEDNA sesja.** Kończy rundę, scala do `main`,
> dopiero potem uruchamiamy następną.

Ta reguła jest nadrzędna wobec całej reszty dokumentu. Powód jest prosty i
sprawdzony na własnej skórze: **sesje nie mają ze sobą kanału**. Każda
widzi kod sprzed swojego startu i nie wie, co robią pozostałe. Git wykrywa
kolizje TEKSTU; kolizje ZNACZENIA przechodzą przez scalenie bez jednego
konfliktu i wychodzą dopiero na produkcji.

Przez jeden dzień pracy trzech równoległych sesji zdarzyło się:
ten sam numer wersji przydzielony dwa razy (0.29.0, potem 0.36.0), kolizja
numerów migracji, przypomnienia o zaległych płatnościach **po cichu
wyłączone** przez mechaniczne scalenie sprzecznych zmian, dwa katalogi
testów E2E, dwa wejścia do tego samego ekranu i bramka jakości, o której
przez pół dnia raportowano „chodzi w tle", choć nie istniała.

Mechanizmy niżej (rezerwacja, bramka, plany sesji) **zostają** — ale w
nowej roli: nie jako sposób na równoległość, tylko jako **przekazanie
pałeczki** między kolejnymi sesjami. Jeśli kiedyś świadomie wrócimy do
równoległości, są gotowe; dopóki nie wrócimy, są tanie i nic nie kosztują.

**Przed rozpoczęciem rundy przeczytaj dwa dokumenty:**
`docs/KARTA_WSPOLPRACY.md` (jak pracujemy — zasady i skąd się wzięły) oraz
`docs/STAN_PRZEKAZANIA.md` (gdzie jesteśmy — co zrobione, co w toku, co
następne).

---

---

## 1. Bramka: `tools/spojnosc.py`

```bash
python apps/dzik-os/tools/spojnosc.py     # 0 = czysto, 1 = są kolizje
```

Uruchamiana w CI (`dzik-os-ci.yml`) i lokalnie przed każdym scaleniem.
Dziesięć kontroli, każda wzięta z błędu, który **naprawdę się zdarzył**:

| Kontrola | Co łapie | Kiedy się zdarzyło |
|---|---|---|
| `migracje` | ten sam numer migracji w dwóch gałęziach; numery nierosnące | scalanie importu biblioteki (nr 24) |
| `changelog` | ta sama wersja przydzielona dwa razy; wersje nie malejąco | 0.29.0 w dwóch rundach naraz |
| `trasy API` | trasa statyczna przesłonięta przez wcześniejszą parametryzowaną | `/coach/exercises/import-schema` w 0.32.0 |
| `routery` | moduł w `routers/` bez `include_router` w `main.py` | — (zapobiegawczo) |
| `testy frontendu` | `scripts/test-*.mjs` spoza `test:helpers`, czyli test-widmo | przy dokładaniu testów pomocniczych |
| `dokumenty` | martwy odnośnik `docs/COŚ.md` (uwaga, nie błąd) | przy przenoszeniu dokumentacji |
| `higiena gałęzi` | objawy gałęzi żyjącej za długo jak na tempo main (uwagi, nigdy błąd) | PR #11: 6,5 h życia, 8 scaleń nadążających |
| `pliki poza gitem` | plik źródłowy ignorowany przez `.gitignore` (błąd) albo nigdy niedodany (uwaga) | `.coverage` dodany przez `git add -A`, potem gitignore — pytanie „czy nie giną nam pliki" |
| `konsultacje` | otwarte pytanie między sesjami (uwaga); zepsuty format wpisu (błąd) | cztery pytania czekały w pliku planu i nic o nich nie powiadamiało |
| `przekazanie` | `STAN_PRZEKAZANIA.md` bez bieżącej wersji z CHANGELOG-a | przy pisaniu Karty współpracy — dokument został przy 0.37.0, gdy repo było na 0.38.0 |

Kontrola **niczego nie naprawia** — od tego jest człowiek albo agent,
który zna zamiar. Ma wyłącznie nie pozwolić kolizji przejść niezauważenie.

**Kontrola też może zgnić.** Pierwsza wersja kontroli tras widziała 35 z
około 200 tras (ta wersja FastAPI nie spłaszcza dołączonych routerów do
`app.routes`) i przechodziła zawsze — wyszło to dopiero przy próbie z
celowo wstrzykniętym błędem. Dlatego `tests/test_spojnosc.py` wstrzykuje
każdy z tych błędów i sprawdza, że kontrola się zapala, a `PROG_TRAS`
wywraca kontrolę, gdy widzi podejrzanie mało tras. **Dokładając kontrolę,
dołóż test, który ją psuje.**

### Przegląd mutacyjny: czy te testy naprawdę pilnują

```bash
python apps/dzik-os/tools/mutacje.py     # z korzenia repozytorium
```

Narzędzie po kolei **psuje kontrolę** na siedemnaście sposobów, po każdym
uruchamia `tests/test_spojnosc.py` i na koniec przywraca oryginał.
Mutacja, po której testy nadal są zielone, to luka — wypisana wprost.

Pierwsze uruchomienie (2026-08-18) znalazło **dwie luki**:

* usunięcie progu `PROG_TRAS` nie wywracało żadnego testu — zabezpieczenie
  przed cichą śmiercią kontroli tras samo nie było zabezpieczone;
* zamiana kontroli dokumentów w atrapę przechodziła bez śladu.

Obie naprawione tego samego dnia; po naprawie **17 z 17 mutacji wykrytych**
(siedem pierwotnych, trzy dla plików poza gitem, pięć dla konsultacji).

**Samo narzędzie też miało błąd, i to niszczący.** Kopię oryginału robiło
tylko wtedy, gdy jeszcze nie istniała (`if not ORYGINAL.exists()`), pod stałą
ścieżką w `/tmp`. 18.08.2026 plik przetrwał z wcześniejszego uruchomienia,
więc kolejny przebieg **„przywrócił” stan sprzed 90 minut**, kasując świeżo
dopisaną kontrolę — po cichu, z komunikatem o powodzeniu. Naprawione trzema
zmianami naraz: katalog tymczasowy unikalny dla przebiegu, kopia robiona
bezwarunkowo, a po przywróceniu **sprawdzany hash** — rozbieżność przerywa
z błędem zamiast meldować sukces.
Uruchamiaj po każdej zmianie w `spojnosc.py` i po dołożeniu kontroli — bez
tego „mamy testy" jest deklaracją, nie faktem.

---

### 1a. Higiena gałęzi — jedyna kontrola patrząca na SPOSÓB pracy

Sześć pierwszych kontroli patrzy na kod. Siódma i ósma patrzą na to,
**jak pracujemy** — bo 18.08.2026 to sposób pracy, a nie treść zmian, wygenerował
większość kolizji.

Fakty z tego dnia, z których wzięły się progi:

| | PR #1–#9 | PR #11 |
|---|---|---|
| Czas życia gałęzi | od kilku sekund do 109 min | **6 h 20 min** |
| Scaleń nadążających za main | 0–1 | **8** |
| Konflikty | **żadne** | changelog ×3, trasy, importy |
| Regresy | brak | przesłonięte trasy importu z pliku |

Równoległość trwała przez cały ten czas — także wtedy, gdy nie było ani
jednego konfliktu. **Nie ona była przyczyną, tylko długość życia gałęzi.**
Lista zadań też nie: była zwyczajna. Zawiodła metoda — zebranie wszystkich
punktów listy na jednej gałęzi zamiast domykania ich po kolei.

Progi (`spojnosc.py`): `PROG_COMMITOW_MAIN = 5`, `PROG_GODZIN = 3.0`,
`PROG_SCALEN = 2`. Najważniejszy jest pierwszy — liczba commitów, które
przybyły na main od odgałęzienia. Mierzy ryzyko wprost, niezależnie od
zegara i strefy czasowej.

**To zawsze UWAGI, nigdy błędy.** Długa gałąź bywa uzasadniona, a
zatrzymanie builda z powodu upływu czasu byłoby karą za zegar. Rzecz w tym,
żeby ryzyko było widoczne **zanim** zamieni się w konflikt — 18.08 zobaczyliśmy
je dopiero przy ósmym scaleniu.

Zasada, która przez pierwsze sześć godzin dała zero konfliktów:
**jedna rzecz → PR → merge → następna rzecz.**

Ta sama zasada tłumaczy PR #10 (praca nad czytelnością UI, 60 linii CSS).
Nie był sporny ani duży — wisiał 8 godzin, bo jego **bazą była inna gałąź
robocza zamiast `main`**. Po scaleniu tamtej gałęzi PR stracił punkt
odniesienia i przestał się dać przejrzeć: GitHub nie miał czego z czym
porównać. **Gałąź odgałęzia się od `main` i wraca do `main`** — baza inna
niż `main` to nie skrót, tylko sposób na PR, którego nikt nie zamknie.

---

### 1b. Pliki poza gitem — druga kontrola patrząca na sposób pracy

Ósma kontrola odpowiada na pytanie „czy nie giną nam pliki". Odpowiedź
brzmi: dotąd nie zginął żaden, ale dwie drogi do tego stały otworem.

* **Ignorowany przez `.gitignore`** — BŁĄD. Tak zginąłby plik naprawdę:
  `git status` go nie pokaże, `git add -A` przejdzie obok, w przeglądzie
  nie będzie go widać. Zdarzyło się blisko: `.coverage` wpadł do repo
  przez `git add -A` i został dopisany do `.gitignore` — gdyby ktoś nazwał
  tak plik źródłowy, zniknąłby bez śladu.
* **Nieśledzony** — UWAGA. Plik widać w `git status`, ale nikt go nie
  dodał; zniknie przy zmianie gałęzi, `git clean` albo wraz z kontenerem.
  W trakcie pracy to stan normalny, więc nie blokuje.

Lista rozszerzeń (`ROZSZERZENIA_ZRODEL`) jest **celowo wąska**: `.env`,
klucze i bazy danych mają prawo być poza gitem, a kontrola, która zaczęłaby
wymuszać ich commitowanie, byłaby gorsza od braku kontroli. Reguły
ignorowania rozstrzyga prawdziwy `git check-ignore`, nie własny parser —
`.gitignore` składa się z kilku plików i ma wykluczenia (`!data/.gitkeep`),
a własny parser byłby kolejną rzeczą gnijącą po cichu.

---

## 2. Rezerwacja: zanim zaczniesz pracę
## 2. Rezerwacja i przekazanie: zanim zaczniesz pracę

Przy pracy jedna-sesja-naraz rezerwacja służy **przekazaniu**: następna
sesja ma od razu wiedzieć, jakie numery są wolne i czego nie ruszać, bo
jest w toku. Trzy zasoby są globalne i nie da się ich zająć dwa razy:

* **numer migracji** — kolejny wolny z `backend/dzik_os/db.py`;
* **numer wersji** w `docs/CHANGELOG.md`;
* **pliki, które będziesz zmieniać** — jeśli dwie równoległe prace
  wskazują ten sam plik, jedna z nich musi poczekać. To nie jest
  uprzejmość, tylko jedyny sposób uniknięcia sprzeczności znaczeniowej.

### Plan pracy każdej sesji

Zanim zaczniesz rundę, połóż swój plan w **`docs/plan-sesji/<nazwa-gałęzi>.md`**.
Nazwa pliku bierze się z gałęzi, więc dwa plany nie mogą się zderzyć —
inaczej niż numer wersji, który zderzył się już dwa razy.

Plan ma odpowiadać na cztery pytania: **co uważam za swój obszar**,
**czego nie dotykam** (żeby ktoś inny mógł to zająć bez pytania), **co
rezerwuję** (numery, pliki) i **czego świadomie nie robię**. Ostatnie
pytanie bywa najważniejsze — kolizje biorą się z rzeczy, których nikt nie
zadeklarował.

### Aktualne rezerwacje

| Gałąź / runda | Migracja | Wersja | Główne pliki | Status |
|---|---|---|---|---|
| `dzik-os-personal-trainer-app` — dostawca AI + sprzątnięcie styków | **26** (rezerwacja warunkowa) | **0.38.0** | `ai_provider.py`, `sheet_import.py`, `routers/`, `pages/coach/`, `components.tsx`, `docs/` | plan złożony, czeka na uzgodnienie |
| `ocena-projektu-dzik-os` — bramki, CI, E2E | — (nie dotyka schematu) | **0.39.0** | `tools/spojnosc.py`, `tools/mutacje.py`, `tests/test_spojnosc.py`, `.github/workflows/dzik-os-ci.yml`, `frontend/e2e/`, `e2e/`, `docs/KOORDYNACJA.md`, `docs/DOSTEPNOSC.md`, `docs/KARTA_WSPOLPRACY.md`, `docs/PRZEGLAD_KRZYZOWY_2026-08-18.md` | w scalaniu |

Następny wolny numer migracji: **27** · następna wolna wersja: **0.40.0**

> Po zakończeniu rundy usuń wiersz i podnieś „następne" numery. Rezerwację
> warunkową, której nie użyto, **zwolnij** — inaczej numer przepada.

**Ten wiersz raz już zniknął po cichu.** Scalenie mojej gałęzi z `main`
nadpisało świeżo wpisaną rezerwację drugiej sesji bez jednego konfliktu —
git widział tylko dwie różne wersje tej samej linii tabeli. Przywrócone
ręcznie. To przypadek nr 1 z §3 niżej i dowód, że tabelę trzeba przy
scalaniu **przeczytać**, a nie tylko rozwiązać konflikt (którego tu nie było).

Następny wolny numer migracji: **27** · następna wolna wersja: **0.39.0**

> Po zakończeniu rundy usuń wiersz i podnieś „następne" numery. Rezerwację
> warunkową, której nie użyto, **zwolnij** — inaczej numer przepada.

---

## 3. Czego bramka NIE złapie

Uczciwa lista — te rzeczy nadal wymagają człowieka przy scalaniu:

1. **Sprzeczność logiczna między rundami.** Realny przykład: jedna runda
   filtrowała płatności po statusie `PENDING`, druga wprowadziła
   `OVERDUE`. Scalenie tekstowe przeszło gładko i **po cichu wyłączyło
   przypomnienia o zaległych płatnościach**. Żadna maszyna tego nie
   zobaczy — trzeba przeczytać obie zmiany.
2. **Test, który sprawdza nieaktualne założenie.** Jedna runda zamieniła
   suwaki na grupy przycisków, test drugiej nadal liczył suwaki.
3. **Dublujący się pomysł.** Dwie rundy budujące to samo innymi słowami
   scalają się bez konfliktu i zostają na stałe jako dwa mechanizmy.

Dlatego przy scalaniu **czyta się obie zmiany**, a nie tylko rozwiązuje
konflikty. Bramka zdejmuje mechaniczną część, nie zastępuje czytania.

---

## 4. Kolejność scalania

1. `python apps/dzik-os/tools/spojnosc.py` — zanim cokolwiek scalisz.
2. Scalanie **po jednym**, nigdy hurtem: po każdym pełna weryfikacja.
3. Pełna weryfikacja — **dokładnie tymi poleceniami, z korzenia repozytorium**:

   ```bash
   python -m ruff check apps/dzik-os/backend     # tak samo jak CI
   python -m pytest apps/dzik-os/backend/tests -q
   python -m pytest tests/ -q                    # Core: 275 testów zielone
   cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build \
     && npm run test:helpers
   ```

   **Uruchamiaj `ruff` tak jak CI, nie „jakoś".** Ta sama zmiana przeszła
   lokalnie i wywróciła CI, bo lokalne `ruff` (starsza wersja z PATH)
   czytało inną konfigurację niż `python -m ruff` (wersja z środowiska,
   której używa CI). Weryfikacja innym poleceniem niż bramka to nie
   weryfikacja.
4. Uruchomienie tego, co nowe — patrz `docs/ZASADA_URUCHOMIENIA.md`.
5. Dopiero potem push i wdrożenie.

---

## 5. Brief dla pracy równoległej

Każda praca prowadzona równolegle dostaje ten sam zestaw ograniczeń:

```
Przeczytaj: /CLAUDE.md, apps/dzik-os/docs/KOORDYNACJA.md,
            apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md.
Pracujesz WYŁĄCZNIE w apps/dzik-os/. Core (hos_engine/, tests/) jest
  nietykalny — 275 testów Core musi zostać zielone.
Twoja rezerwacja: migracja nr <N>, wersja <X.Y.0>, pliki <lista>.
  Nie dotykaj plików spoza tej listy; jeśli musisz — zgłoś to zamiast
  zmieniać po cichu.
Nie pushuj. Commituj po polsku, bez nazw modeli AI w treści commita.
Przed zakończeniem: pełna weryfikacja (punkt 4 wyżej) plus
  `python apps/dzik-os/tools/spojnosc.py`.
W raporcie napisz, CO URUCHOMIŁEŚ I CO ZOBACZYŁEŚ — nie „sprawdzone".
```

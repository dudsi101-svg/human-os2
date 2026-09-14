# Plan sesji: szablony rozwijane po nazwie i opisy ćwiczeń z Wiedzy w planie klienta (0.75.0)

**Gałąź:** `agent/szablony-i-opisy` (od `main` = `8a71116`, 0.73.0 — cardio i rozgrzewka
scalone). **Rola:** podległa sesja pisząca wyznaczona przez integratora 14.09.2026
(polecenie właściciela z 14.09, słowa właściciela w promptcie integratora). **Bez migracji.**

**Uwaga o protokole jednego piszącego:** w chwili startu (14.09 ok. 14:55 UTC) otwarty jest
jeden PR `[WRITER]` — #76 (`agent/motyw-czerwony`, 0.74.0, motyw czerwono-biały, draft).
Integrator wyznaczył tę sesję jawnie z wiedzą o nim (wyjątek integratora, jak przy 0.71.0
i 0.73.0). Sesja nie dotyka plików tamtej gałęzi (`styles.css` poza ewentualnym dopisaniem
własnej klasy na końcu — jeśli da się obejść bez CSS, nie dotykam; motyw, `Landing.tsx`).

## Cel (słowami właściciela)

> W szablonach treningowych zrób tak, żeby nazwa szablonu była widoczna, a wszystkie dane
> o treningu można było rozwinąć klikając na nią. Kolejny ważny element: w każdym planie
> dodanym do klienta i ćwiczeń, które się w nim znajdują, stwórz połączenie prowadzące do
> szczegółowego opisu tego ćwiczenia z Wiedzy […] tak, by podopieczny, gdyby tego ćwiczenia
> nie znał, mógł sobie wygodnie rozwinąć lub przenieść się do miejsca, w którym jest
> szczegółowo opisane.

## Rozpoznanie (stan `main` 8a71116, z liniami)

* **Lista szablonów treningowych:** `frontend/src/pages/coach/Templates.tsx:72–96` —
  każda karta renderuje od razu wszystkie dni i ćwiczenia (`t.current_version?.content.days
  .map`), pod nimi `PublikacjaPanel` i notkę o kopiowaniu. Nagłówek `<h2>{t.title}</h2>`
  nie jest interaktywny. Zakładka „Dieta” (`DietTemplates.tsx:117+`) już ma listę zwiniętą
  z przyciskiem „Podgląd” (`open` lokalnie) — logiki diet nie zmieniam; ujednolicam tylko
  tyle, że nazwa też jest przyciskiem rozwijającym (ten sam `aria-expanded`).
* **Jak pozycja planu odwołuje się do ćwiczenia:** `types.ts:1–29` (`Exercise.exercise_id`
  — MIĘKKIE odniesienie do bazy ćwiczeń trenera, `kind`, `block`, `cardio`), `BlockItem.
  exercise_id` (`types.ts:32–37`), backend `schemas.py:207` (`ExerciseIn.exercise_id`).
  Nie ma `catalog_id`; Wiedza v2 używa osobnego `konfigurator_id` (`routers/wiedza.py:
  127–146`, karty atlasu `ex-<id konfiguratora>`) — to **inna** przestrzeń identyfikatorów
  (katalog konfiguratora, nie baza trenera). Seed (`seed.py:257–261`, `ex_ref`) podpina
  WSZYSTKIE pozycje planów przez `exercise_id`; pozycje z importu pliku/szablonów wbudowanych
  mogą nie mieć identyfikatora („pozycja bez odpowiednika i tak wejdzie do szablonu, tylko
  bez karty ćwiczenia” — `Templates.tsx:142`).
* **Co już istnieje:** `components.tsx:1292–1339` `ExerciseTechniqueLink` — rozwinięcie
  w miejscu z `GET /api/me/exercises/{id}` (leniwie po kliknięciu, bez cache między
  pozycjami) i `ExerciseDetail` (`components.tsx:1169`, pełna karta: kroki, błędy,
  wskazówki, tempo, warianty, bezpieczeństwo, mięśnie). Użycia: `Plan.tsx:249`,
  `Today.tsx:204`, `pozycje.tsx:144` (pozycje bloku). Działa **tylko** gdy jest
  `exercise_id`; nie ma linku do Wiedzy; brak dopasowania po nazwie.
* **Backend ćwiczeń:** `routers/exercises.py:577–618` — `GET /api/me/exercises` (lista,
  filtry, `_client_coach_ids` = trenerzy z relacją ACTIVE, tylko `status == "ACTIVE"`)
  i `GET /api/me/exercises/{item_id}` (404 dla cudzego/zarchiwizowanego). Trener:
  `GET /api/coach/exercises/{item_id}` (`:517`). Normalizacja nazw już jest:
  `muscles.fold` (`muscles.py:117`, casefold + bez diakrytyków, „ł”→„l”) i
  `import_exercises.normalize_name` (`:161`, fold + zbicie białych znaków) — do użycia
  1:1 w dopasowaniu po nazwie. **Lekcja z 0.33.0:** trasa `/by-name` musi być
  zadeklarowana PRZED `/{item_id}`, inaczej zostanie przesłonięta.
* **Wiedza — gdzie jest karta ćwiczenia trenera:** klient `pages/client/Knowledge.tsx`
  (v2 za `DZIK_WIEDZA_V2`: parametry `czesc`/`karta`/`widok` w URL, `:57–63`; część
  „Trening” → karta „Baza ćwiczeń trenera” = `ExercisesTab` z `KnowledgeLegacy.tsx:125`,
  lista z filtrami, karty rozwijane `ExerciseCard` `:192`); przy wyłączonej fladze
  `KnowledgeLegacy` z zakładką „Ćwiczenia” (stan lokalny, bez URL). **Nie ma trasy do
  konkretnego ćwiczenia** — ani u klienta, ani u trenera (`pages/coach/Knowledge.tsx:68–92`,
  zakładki w stanie lokalnym, `ExercisesTab` `:352`, `CoachExerciseCard` `:1120`).
  Atlas v2 (`ex-<konfigurator_id>`) dotyczy tylko planów z konfiguratora — poza zakresem.
* **Trener — podgląd planu klienta i edytor:** `ClientDetail.tsx:634–639` (odczyt: nazwa +
  odznaka + `opisPozycji`), `PlanEditor.tsx:485–520` (odznaka „z bazy” przy `exercise_id`,
  zmiana nazwy odpina id), `SzkicPlanu.tsx:407–436` (to samo w szkicu).
* **Testy i bramki:** `tests/access_matrix.py:347–348` (macierz wymaga wpisu dla każdej
  nowej trasy), `test_exercises.py` (wzorzec `seeded` + `login`), `test_idor.py:20–26`
  (`_foreign_coach`), `spojnosc.py:217` (każdy `scripts/test-*.mjs` w `test:helpers`),
  `playwright.config.ts` (projekty `telefon` i `desktop-trener`: `testMatch` szablonów),
  `e2e/test_a11y.mjs:313–326` (szerokości 320–1024 na wybranych trasach).

## Rezerwacje (sprawdzone na żywo 14.09 ~14:55 UTC)

* **Wersja 0.75.0** — `CHANGELOG.md` ma na górze 0.73.0; **0.74.0 = PR #76** (motyw, nie
  scalony). Sekcja 0.75.0 idzie NA GÓRĘ; jeśli #76 wejdzie wcześniej, sekcja zostaje nad
  nim. Numer podbijam w `frontend/package.json`, `backend/pyproject.toml`,
  `backend/dzik_os/__init__.py`, `README.md`, `RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`
  (kontrole `przekazanie` i `wersje dokumentów`).
* **Migracja: brak.** Ostatni wpis w `db.py` = 39; nie dokładam (identyfikator `exercise_id`
  istnieje w treści JSON; dopasowanie po nazwie jest odczytowe — patrz „Pytania”).
* **`export_version`:** bez zmian (żadnych nowych pól w danych klienta).
* **Porty E2E:** 8130/8131, katalog `/tmp/dzik-e2e-8130`; przy zajętych 8132/8133.

## Pliki

**Współdzielone (zmieniam jawnie, tylko własne fragmenty):** `routers/exercises.py` (dwie
trasy `by-name` przed `/{item_id}`), `tests/access_matrix.py` (2 wiersze), `seed.py`
(jedna pozycja planu po nazwie bez `exercise_id` — demo dopasowania; tylko jeśli żaden test
nie liczy pozycji), `components.tsx` (usunięcie `ExerciseTechniqueLink` po przeniesieniu),
`pozycje.tsx`, `Plan.tsx`, `Today.tsx`, `Templates.tsx`, `DietTemplates.tsx` (tylko nagłówek
jako przycisk), `ClientDetail.tsx`, `PlanEditor.tsx`, `SzkicPlanu.tsx`, `pages/client/
Knowledge.tsx`, `pages/client/KnowledgeLegacy.tsx`, `pages/coach/Knowledge.tsx`, `types.ts`
(bez zmian modelu — ewentualnie typ odpowiedzi), `package.json` (`test:helpers`),
`e2e/szablony.spec.ts`, `e2e/test_a11y.mjs` (Szablony + Plan: przyciski z etykietą, brak
scrolla), `CHANGELOG.md`, `RELEASE_STATUS.md`, `PERMISSIONS.md`, `INSTRUKCJA_KLIENTA.md`,
`INSTRUKCJA_TRENERA.md`, `E2E.md`, `STAN_PRZEKAZANIA.md` §1/§2, `docs/zlecenia/README.md`.

**Nowe:** `frontend/src/opisCwiczenia.tsx` (komponent `OpisCwiczenia` + cache),
`frontend/src/nazwy.ts` (normalizacja nazwy, klucz cache, adres karty w Wiedzy),
`frontend/scripts/test-nazwy.mjs` + `tsconfig.nazwy.json`, `frontend/e2e/plan-opis.spec.ts`,
`backend/tests/test_exercises_by_name.py`, `docs/szablony-i-opisy/PROGRESS.md`, ten plan.

**Zabronione:** `hos_engine/`, `tests/` w korzeniu, `db.py`, migracje, `AGENTS.md`,
`CLAUDE.md`, `KOORDYNACJA.md`, `KONSULTACJE.md`, `tools/spojnosc.py`, `tools/mutacje.py`,
pliki motywu (PR #76) i strony publicznej.

## Test INTENDED_PURPOSE §2/§3 (etap 0)

Dane, których dotyka runda: treść opublikowanego planu (domena treningowa, klient już ją
widzi) i baza ćwiczeń trenera (broadcast do klientów z aktywną relacją — istniejąca zasada
`_client_coach_ids`). Dopasowanie po nazwie nie ujawnia niczego ponad to, co klient dostaje
z `GET /api/me/exercises` (cała lista jest dla niego widoczna) — nowa trasa zawęża, nie
poszerza. Brak dopasowania = 404 bez rozróżniania „nie ma” od „nie Twój trener” (IDOR →
404). Trener widzi wyłącznie własne ćwiczenia (jak `/coach/exercises/{id}`). Zero danych
zdrowotnych, zero AI, nic nie jest zapisywane (stan rozwinięcia tylko w pamięci widoku).
Bez wątpliwości — bez pytania do foundera.

## Decyzje projektowe

1. **Szablony:** nagłówek karty = `<h2><button aria-expanded aria-controls>` z nazwą;
   obok meta „N dni · M ćwiczeń · data”. Zwinięte domyślnie; rozwinięcie pokazuje dni,
   ćwiczenia (z `opisPozycji` dla cardio/bloków), `PublikacjaPanel` i notkę. Stan lokalny
   (`Set<string>` id rozwiniętych), bez zapisu. `PublikacjaPanel` montowany dopiero po
   rozwinięciu (mniej żądań przy długiej liście). Jeden `h1` (TopBar), karty `h2`.
2. **Opis ćwiczenia w planie (`OpisCwiczenia`):** jeden komponent dla klienta i trenera
   (`rola: "klient" | "trener"`). Po kliknięciu „Opis ćwiczenia” pobiera leniwie:
   `exercise_id` → `GET /api/{me|coach}/exercises/{id}`; bez id → `GET /api/{me|coach}/
   exercises/by-name?name=…`. Cache w pamięci modułu (`Map` klucz `id:<id>` / `nazwa:<
   znormalizowana>`), wspólny dla Dzisiaj/Plan/bloków w tej sesji karty. Rozwinięcie
   w miejscu = **skrót**: technika w punktach (kroki albo `how_to`), najczęstsze błędy,
   mięśnie (główne/pomocnicze); pod nim link **„Pełny opis w Wiedzy”** → karta ćwiczenia
   z powrotem. Brak dopasowania: uczciwy tekst „Brak opisu tego ćwiczenia w Wiedzy” (nie
   da się ukryć przycisku przed kliknięciem bez N żądań na wejściu — decyzja: leniwie,
   zgodnie z poleceniem). Zastępuje `ExerciseTechniqueLink` w trzech miejscach (pozycje
   bloku dostają też dopasowanie po nazwie, gdy `BlockItem.exercise_id` brak).
3. **Karta ćwiczenia w Wiedzy:** klient `/wiedza?czesc=training&cwiczenie=<id>&powrot=/plan`
   (v2 i legacy obsługują ten sam parametr — wspólny `KartaCwiczeniaTrenera` w
   `KnowledgeLegacy.tsx`: pełny `ExerciseDetail`, przycisk „Wróć do planu” gdy `powrot`
   to wewnętrzna ścieżka zaczynająca się od `/` bez `//`, inaczej „Wróć do Wiedzy”; fokus
   na przycisku powrotu po wejściu); trener `/trener/wiedza?cwiczenie=<id>&powrot=…` →
   ta sama karta z `GET /api/coach/exercises/{id}` nad zakładkami. 404 → „Tego ćwiczenia
   nie ma już w bazie” + powrót.
4. **Backend `by-name`:** równość `normalize_name(name) == normalize_name(item.name)` wśród
   ACTIVE ćwiczeń dozwolonych trenerów (klient) / własnych (trener). Deterministycznie:
   przy kilku trafieniach (np. dwóch trenerów) wybór po `(created_at, id)` rosnąco.
   `name` 1–200 znaków, inaczej 422. 404 = brak (bez rozróżniania powodu). Bez zapisu.
5. **Trener:** `ClientDetail` podgląd planu i `PozycjaBloku` — ten sam `OpisCwiczenia
   rola="trener"`; w `PlanEditor`/`SzkicPlanu` przy pozycji z `exercise_id` link „Karta
   w Wiedzy” (bez rozwinięcia — edytor ma zostać lekki).
6. **Zero AI, bez migracji, bez flagi** (jak 0.71.0/0.73.0 — funkcja ma być widoczna).

## Etapy (z weryfikacją i nakładem)

| # | Etap | Weryfikacja | Nakład |
|---|---|---|---|
| 0 | plan sesji, push, draft PR `[WRITER]` | PR widoczny | 0,5 h |
| 1 | backend: `by-name` ×2, macierz, testy (klient: fold/diakrytyki, brak → 404, bez relacji → 404, zarchiwizowane → 404; trener: własne, cudze → 404; 422) | `pytest tests/test_exercises_by_name.py test_access_matrix.py test_authz_matrix.py` | 1 h |
| 2 | `nazwy.ts` + test helpera; `OpisCwiczenia` + cache; podmiana w Plan/Today/pozycje | `tsc`, `test:helpers` | 1,5 h |
| 3 | Wiedza: parametr `cwiczenie`/`powrot` u klienta (v2 + legacy) i trenera | ręcznie przez serwer E2E | 1 h |
| 4 | Szablony: nagłówek-przycisk, meta, zwinięcie; Dieta: nazwa jako przycisk | `tsc`, E2E szablony | 1 h |
| 5 | trener: ClientDetail/PlanEditor/SzkicPlanu | `tsc` | 0,5 h |
| 6 | E2E `szablony` (rozwinięcie po nazwie, oba projekty) i `plan-opis`; a11y; PWA | Playwright, `test_a11y.mjs`, `test_pwa_offline.mjs` | 1,5 h |
| 7 | dokumenty, wersje, przeklik ze zrzutami, przegląd 3 recenzentów, P0/P1 | `spojnosc.py`, pełny `pytest`, Core, mutacje, build | 2 h |

**Największy koszt:** etap 3 — dwa tryby Wiedzy (v2/legacy) i trzy miejsca wejścia do
karty; ryzyko, że parametr `cwiczenie` zderzy się z istniejącą obsługą `karta`/`widok`
(kolejność: `cwiczenie` ma pierwszeństwo, bo przychodzi z planu). **Bezpiecznik 3× plan:**
plan ≈ 9 h; przy przekroczeniu 27 h STOP i raport.

## Pytania do właściciela (domyślne przyjęte, nic nie blokuje)

1. **Utrwalenie dopasowania po nazwie w planie** (zapis `exercise_id` przy pierwszym
   trafieniu) wymagałoby zmiany treści wersji planu — historia jest niezmienna, więc
   musiałaby to być nowa wersja albo migracja treści. **Nie robię**; dopasowanie jest
   odczytowe i deterministyczne. Jeśli właściciel chce trwałego powiązania — osobna runda
   z decyzją o formie (nowa wersja planu z powodem „powiązanie z bazą”).
2. Skrót w miejscu vs pełna karta: przyjmuję skrót (technika w punktach, błędy, mięśnie)
   + link do pełnej karty; pełny `ExerciseDetail` w planie dublowałby Wiedzę.
3. Diety w Szablonach: tylko nazwa jako przycisk (ta sama zwijana lista co dotąd).

## Weryfikacja wykonana (14.09, stan przed scaleniem `main`)

**Bramki:** `python -m ruff check backend tools` — czysto; pełny `pytest tests -q`
(`PYTHONPATH=.`) — **1929 passed, 1 skipped** (po poprawce
`test_seeded_plans_and_templates_are_linked_to_library`: pozycja bez `exercise_id`
musi trafiać w bazę po nazwie — pierwszy przebieg 1928/1 failed właśnie na niej);
Core `pytest tests -q` — **275 passed**; `tools/spojnosc.py` — 13 kontroli czysto,
1 uwaga (K-001, cudza, otwarta od 647 h); `mutacje.py` 17/17 wykryte;
`mutacje_bezpieczenstwa.py` 9/9 zabitych; `tsc --noEmit` czysto; `npm run build`
— 92,5 kB gzip (budżet 120); `test:helpers` 153 pass (w tym `test-nazwy.mjs` 6);
E2E `telefon` (szablony, plan-opis, nawyki, dni-treningowe, wiedza, rozgrzewka)
15/15; `desktop-trener` (szablony, logowanie, pwa) 9/9; `test_a11y.mjs` — wszystkie
kontrole (w tym nowe 4a i 7a); `test_pwa_offline.mjs` — wszystkie.

**Prawdziwe żądania HTTP na uruchomionym serwerze (port 8132, `curl`):**
`GET /api/me/exercises/by-name?name=wioslowanie%20HANTLEM%20w%20podporze` → 200
(`Wiosłowanie hantlem w podporze`, 4 kroki); nazwa spoza bazy → 404; pusta → 422;
bez tokenu → 401; trener `…/coach/exercises/by-name?name=Przysiad ze sztangą` → 200;
klient na trasie trenera → 403. Trasa nie jest przesłonięta przez `/{item_id}`.

**Przeklik (Chromium; zrzuty w scratchpadzie `opisy-zrzuty/`, 13 plików):**
1. Klient A (Pixel 7) → `/plan`: pod każdym ćwiczeniem „Opis ćwiczenia” (zwinięty).
2. Klik przy „Wyciskanie sztangi leżąc” (po id) → skrót na całą szerokość
   wiersza: TECHNIKA W PUNKTACH (5), NAJCZĘSTSZE BŁĘDY (4), „Mięśnie: klatka
   piersiowa · pomocniczo triceps, bark przedni”, przycisk „Pełny opis w Wiedzy”.
   Pierwsza wersja miała opis w lewej kolumnie siatki `.exercise` (ściśnięty do
   połowy ekranu) i tekst wyrównany do prawej — naprawione (`gridColumn: 1 / -1`,
   `textAlign: left`).
3. „Wiosłowanie hantlem w podporze” (seed bez `exercise_id`) → opis dopasowany po
   nazwie.
4. „Pełny opis w Wiedzy” → `/wiedza?czesc=training&cwiczenie=HOS-EXC-…&powrot=/plan`
   — pełna karta (technika, błędy, wskazówki, tempo, mapa mięśni), fokus na
   „Wróć do planu”. 5. „Wróć do planu” → `/plan`.
6. Blok rozgrzewki dnia C → „Pokaż pozycje (6)” → pozycja 1 „Marsz pod górę na
   bieżni” → „Opis ćwiczenia” → technika w punktach z bazy.
7. „Dzisiaj” — w dniu przeklikania brak treningu (seed: pon/śr/pt), karta z
   opisem na „Dzisiaj” to ten sam komponent; E2E nie sprawdza jej osobno
   (odstępstwo jawne — pokrycie: Plan + a11y).
10. Trener (1280 px) → `/trener/szablony`: 1 szablon, „Szablon: Push/Pull/Legs ·
    3 dni · 6 pozycji · 14 września 2026”, treść zwinięta.
11. Klik w nazwę → Push/Pull/Legs z ćwiczeniami, „Karta w Wiedzy” przy każdej,
    „Edytuj (szkic) / Duplikuj / Archiwizuj”, notka o kopiowaniu.
12. „Karta w Wiedzy” → `/trener/wiedza?cwiczenie=…&powrot=/trener/szablony`,
    własna karta; 13. „Wróć do szablonów” → `/trener/szablony`.
14. Zakładka Dieta: w seedzie brak własnych szablonów diety — nazwa-przycisk
    sprawdzona w E2E po imporcie z katalogu (test „Dieta” przechodzi).
15. Karta klienta A → Plan → „Opis ćwiczenia” (rola trenera) rozwinięty;
16. „Pełny opis w Wiedzy” → „Wróć do karty klienta” → `/trener/klient/…?zakladka=plan`.
17. „Edytuj (szkic)” szablonu → 6 linków „Karta w Wiedzy” w szkicu (plus 6 na
    rozwiniętej liście). Zero błędów JS w konsoli u klienta i trenera.

**Przegląd (narzędzie `Agent` niedostępne w tej sesji — trzy przejścia własne,
zapisane jawnie):** (a) dostęp/IDOR: `by-name` zawęża zbiór listy, 404 jednolite,
trener tylko własne, klient 403 — bez uwag; (b) UX/a11y: naprawiony układ skrótu
na telefonie (pkt 2), przycisk w `h2` z `aria-controls`, fokus na powrocie —
bez P0/P1; (c) testy/dokumenty: test seedu dostosowany do pozycji po nazwie
(`po_nazwie >= 1`, bo v1 i v2), E2E.md, PERMISSIONS, instrukcje, STAN, zlecenia —
bez P0/P1. P2 w `docs/szablony-i-opisy/PROGRESS.md`.

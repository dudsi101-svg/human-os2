# Pakiet zleceń dla sesji piszącej — Dzik OS, 14.09.2026

**Jeden dokument zamiast dziesięciu plików.** Zawiera wszystko, co powstało 14.09 w sesji
tylko-do-odczytu: sześć zleceń dla writera (prompt do wklejenia jako pierwsza wiadomość,
szkice planów sesji, model suwaków, przetestowany blok tokenów), kolejność scalania,
decyzje właściciela z czterech tur i zbiorczą listę pytań, na które writer potrzebuje
odpowiedzi. Pliki źródłowe zostają w `apps/dzik-os/docs/zlecenia/` (każda sekcja podaje,
z którego pliku pochodzi) — ten dokument jest złożeniem, nie nową treścią.

## Spis treści

1. Jak używać pakietu i kolejność scalania (README)
2. Decyzje właściciela z 14.09 (cztery tury)
3. Zbiorcza lista otwartych pytań do właściciela
4. Zlecenie 0 — Ukryj kreator diety *(scalone jako 0.67.0, PR #68)*
5. Zlecenie 1 — Dni treningowe na „Dzisiaj”
6. Zlecenie 2 — Wymiany produktów v2 *(scalone jako 0.69.0, PR #69; import CSV osobno)*
7. Zlecenie 3 — Domknięcie PR #67: strona publiczna czerwono-biała
8. Zlecenie 4 — Motyw czerwono-biały jako drugi, kompletny motyw aplikacji
9. Zlecenie 5 — Rozgrzewka, rozciąganie i cardio z suwakami celów (model + prompt)

Stan na 14.09 wieczór: `main` = 0.69.0 (`04d1d58`); otwarte PR-y: #67 (landing, gotowy do
przeglądu). Kolejność w sekcji 1 jest propozycją — właściciel może ją zmienić.

---

## 1. Jak używać pakietu i kolejność scalania


Katalog na gotowe pakiety „prompt + szkic planu sesji”, przygotowane przez sesję
tylko-do-odczytu (rozpoznanie kodu, pomiar, decyzje do zatwierdzenia). Sesja
pisząca dostaje **prompt jako pierwszą wiadomość**, a szkic planu kopiuje do
`docs/plan-sesji/<gałąź>.md` jako pierwszy commit (protokół z `KOORDYNACJA.md`).

Pakiet nie jest planem sesji i nie rezerwuje niczego sam z siebie — numery wersji
i migracji w nim są **propozycją do sprawdzenia** tuż przed zmianą (`db.py`,
`CHANGELOG.md`, `STAN_PRZEKAZANIA.md` §2). Pliki tu nie są plikami integracyjnymi.

### 2026-09-14 — trzy zlecenia właściciela

| Zlecenie | Prompt | Szkic planu | Gałąź | Warunek startu |
|---|---|---|---|---|
| 0. Ukryj kreator diety (flaga, nic nie ginie; katalog produktów zostaje) | `PROMPT_writer_ukryj-kreator.md` | `plan-sesji_ukryj-kreator.md` | `agent/ukryj-kreator` | brak (małe, może iść pierwsze) |
| 1. Dni treningowe: klient wybiera dni tygodnia dla jednostek planu; „Dzisiaj” pokazuje trening z dzisiejszego dnia | `PROMPT_writer_dni-treningowe.md` | `plan-sesji_dni-treningowe.md` | `agent/dni-treningowe` | brak (niezależne od gałęzi w toku) |
| 3. Domknięcie PR #67 „Strona publiczna: wariant czerwono-biały” (nowa szata graficzna) | `PROMPT_writer_landing-czerwony-domkniecie.md` | — (kontynuacja `docs/plan-sesji/landing-czerwony.md`) | `agent/landing-czerwony` (istniejąca, PR #67) | decyzje właściciela z §3–5 promptu (kontrast, treść, znak marki) |
| 4. Motyw czerwono-biały jako drugi, kompletny motyw aplikacji do wyboru użytkownika (klient i trener) | `PROMPT_writer_motyw-czerwony.md` + `motyw-czerwony.tokens.css` | — (plan pisze writer wg §5 promptu) | `agent/motyw-czerwony` | scalenie #67; decyzje z §7 promptu |
| 5. Rozgrzewka (3×3) + rozciąganie + cardio na sprzęcie z suwakami celów (model: 3 strefy/Karvonen/Fatmax/VO2max) | `PROMPT_writer_cardio-i-rozgrzewka.md` + `model-suwakow-cardio.md` | — (plan pisze writer wg §6) | `agent/cardio-i-rozgrzewka` | decyzje z §8; nie równolegle ze zleceniem 1 (te same pliki planu) |
| 2. Wymiany produktów v2: grupy pokrewne, zgodność funkcji w posiłku, bramka „nie pogarsza”, przycisk dla roli NONE | `PROMPT_writer_wymiany-produktow.md` | `plan-sesji_wymiany-produktow.md` | `agent/wymiany-produktow` | **scalenie `agent/biblioteka-diet`** (te same pliki; sama biblioteka obniża odsetek składników bez zamiennika z 31 % do 11 %) |

**Kolejność scalania i numery wersji** (kontrola `changelog` wymaga wersji rosnących
w kolejności scalania, więc numer przydziela piszący dopiero przy starcie, wg tej tabeli):

| Krok | Co | Wersja | Migracja | Stan (14.09 wieczór, `main` = 0.69.0, `04d1d58`) |
|---|---|---|---|---|
| — | `agent/biblioteka-diet` | 0.64.0 | 35 | scalona |
| — | `agent/monitoring-postepy` (PR #61) | 0.66.0 | 36 | scalona |
| — | `agent/ukryj-kreator` (PR #68, zlecenie 0) | 0.67.0 | — | **scalona** |
| — | `agent/wymiany-produktow` (PR #69, zlecenie 2) | 0.69.0 | — | **scalona**; import CSV z decyzjami właściciela = osobny mały PR |
| 1 | zlecenie 1 — dni treningowe | **0.68.0 (zarezerwowane w CHANGELOG 0.69.0)** | **37 (zarezerwowana)** | nie rozpoczęte |
| 2 | PR #67 `agent/landing-czerwony` (zlecenie 3) | kolejna wolna (0.70.0, jeśli wejdzie przed dniami treningowymi — wtedy dni → 0.71.0; CHANGELOG musi rosnąć w kolejności scalania) | — | gotowy do przeglądu, wymaga dociągnięcia `main` i poprawek z promptu |
| 3 | rozpoznanie wywiadu kalorycznego (PR #71, tylko dokument) | — | 38 albo 39 (przyszła) | scalone; 7 decyzji właściciela |
| 4 | zlecenie 4 — motyw czerwono-biały (po #67) | kolejna wolna | kolejna wolna (pole `theme`) lub brak | nie rozpoczęte; podgląd tokenów wykonany 14.09 |
| 5 | zlecenie 5 — rozgrzewka, rozciąganie, cardio z suwakami | kolejna wolna | **38+** (37 zajęta; 38/39 może wziąć wywiad kaloryczny — sprawdź `db.py`) | nie rozpoczęte; model i szkic treści gotowe 14.09 |

Decyzje właściciela z trzeciej tury (14.09): docelowo dwa kompletne motywy do wyboru
użytkownika — czarno-zielony i czerwono-biały (zlecenie 4). Z drugiej tury (14.09): kreator diety odłożony i ukryty; klient na
diecie z szablonu; katalog pojedynczych produktów (2058 pozycji) ma zasilić zamienniki
szablonu przez przeglądany import (zlecenie 2, §5a). Każdy prompt kończy się pytaniami
z wartościami domyślnymi — odpowiedź wpisuje się w tę samą wiadomość do sesji piszącej.

---

## 2. Decyzje właściciela z 14.09 (cztery tury)

| Tura | Decyzja | Skutek w pakiecie |
|---|---|---|
| 1 | Klient z tygodniowym planem ma wybrać dni tygodnia dla jednostek; trening z dzisiejszego dnia ma być na „Dzisiaj” | zlecenie 1 (nakładka klienta, wersje planu nietknięte) |
| 1 | Przycisk wymiany produktu w Diecie ma działać: powiązać pokrewne grupy, zgodność makro i funkcji w posiłku | zlecenie 2 (scalone 0.69.0); pomiar 31 % → 11 % → dalej silnik v2 |
| 2 | Kreator diety odłożony — ukryć; klient na diecie z szablonu | zlecenie 0 (scalone 0.67.0); w zleceniu 2 pytanie 1 rozstrzygnięte |
| 2 | Lista pojedynczych produktów (katalog 2058) ma zasilić zamienniki szablonu | zlecenie 2 §5a: korelacja → CSV do przeglądu → import osobnym PR-em |
| 3 | Docelowo użytkownik wybiera między kompletnym motywem czarno-zielonym a nowym czerwono-białym; nowy ma być kompletny | zlecenie 4; w zleceniu 3 zdanie „Ciemny motyw aplikacji zostaje” do zamiany |
| 4 | Dwa nowe rodzaje ćwiczeń: rozgrzewka 3 poziomy × 3 warianty + rozciąganie; cardio na sprzęcie z trzema suwakami celów sterującymi tętnem, obciążeniem, tempem i czasem; znaleźć istniejący model | zlecenie 5 + `model-suwakow-cardio.md` (3 strefy wg progów, Karvonen, Fatmax, interwały pod VO2max; trzeci cel: Regeneracja) |



---

## 3. Zbiorcza lista otwartych pytań do właściciela

Każdy prompt kończy się pytaniami z wartością domyślną; bez odpowiedzi writer bierze
domyślne. Tu wszystkie w jednym miejscu (szczegóły i uzasadnienia w sekcjach zleceń).

| # | Zlecenie | Pytanie | Domyślnie |
|---|---|---|---|
| 1 | 1 dni treningowe | Czy trener może edytować wybór dni klienta z karty klienta? | tak (relacja + zgoda) |
| 2 | 1 | Dwie jednostki tego samego dnia? | nie (422) |
| 3 | 1 | Plan bez dni u trenera i klienta: pokazać pierwszą jednostkę „na zachętę” czy tylko kartę „ustaw dni”? | tylko karta |
| 4 | 2 wymiany | Kto przegląda CSV propozycji z katalogu — właściciel czy trener? | właściciel wstępnie, trener potwierdza alergeny |
| 5 | 2 | Pary grup oznaczone (?) włączyć od razu? | wyłączone do przeglądu |
| 6 | 2 | Wymiana w posiłku poza tolerancją: dozwolona gdy „nie pogarsza” czy tylko gdy „poprawia”? | nie pogarsza |
| 7 | 2 | Warzywa o roli NONE wymieniane 1:1 wagowo? | tak |
| 8 | 0 ukryj kreator | „Ułóż z dań” (kreator kulinarny) też ukryć? | zostawić |
| 9 | 0 | Ręczny formularz planu żywieniowego w karcie klienta zostaje? | tak |
| 10 | 3 landing | Kontrast: wariant A (obrys #B3878A, numery grafitowe na koralu) czy B (kolory ze spec z wpisanym odstępstwem)? | A |
| 11 | 3 | Cztery odstępstwa treściowe z opisu PR (w tym fraza „zwykle tego samego dnia”) | jak w PR; fraza bez potwierdzenia trenera nie wchodzi |
| 12 | 3 | Znak marki: dzik z limonki na czerwień — nowy znak wszędzie (etap 2) czy strona wraca do limonki? | nowy znak, etap 2 osobno |
| 13 | 3 | Numer wersji PR #67 | 0.70.0 |
| 14 | 3 | Treść syntetycznych kart w hero („Przysiad 110 kg”, „Raport z tygodnia 8”) | do potwierdzenia |
| 15 | 4 motyw | Motyw domyślny dla nowych kont | ciemny |
| 16 | 4 | Czerwony dzik tylko w jasnym motywie; ikony PWA/og zostają limonkowe do osobnej decyzji? | tak |
| 17 | 4 | Trzecia opcja „jak w systemie”? | nie w v1 |
| 18 | 4 | Zapis wyboru motywu na koncie (migracja) czy tylko na urządzeniu? | na koncie i urządzeniu |
| 19 | 4 | Nazwy w UI: „Ciemny (czarno-zielony)” / „Jasny (czerwono-biały)” | tak |
| 20 | 5 cardio | Trzeci cel: Regeneracja (baza tlenowa)? Alternatywy: Wytrzymałość, Moc | Regeneracja |
| 21 | 5 | Cel 1 nazwany „Redukcja (wydatek energii)” zamiast „Spalanie tłuszczu” | Redukcja |
| 22 | 5 | Warianty rozgrzewki: góra / dół / całe ciało (vs czas 5/10/15 min, vs siłownia/dom) | góra/dół/całe ciało |
| 23 | 5 | Rozciąganie: 3 warianty bez poziomów, po treningu | tak |
| 24 | 5 | Trener wskazuje dozwolone urządzenia, klient wybiera w dniu treningu | tak |
| 25 | 5 | Przegląd treści bloków, nowych ćwiczeń i tabeli urządzeń przez trenera przed użyciem | tak, wpisy „do przeglądu” |
| 26 | 5 | „Tętno spoczynkowe” jako metryka pomiarowa (dane zdrowotne, zgoda) | tak, opcjonalne, bez migracji |

Poza pytaniami: 7 decyzji z rozpoznania wywiadu kalorycznego (PR #71, `docs/wywiad-zapotrzebowanie/01_rozpoznanie_spec_v1.md`) — spoza tego pakietu, ale w tej samej kolejce.


---

## 4. Zlecenie 0 — Ukryj kreator diety (scalone jako 0.67.0, PR #68)
*Stan: wykonane i scalone 14.09. Zostawione dla kompletu i historii decyzji.*

### Źródło: `PROMPT_writer_ukryj-kreator.md`



---

Przeczytaj kolejno: `/AGENTS.md`, `/CLAUDE.md`,
`apps/dzik-os/docs/KARTA_WSPOLPRACY.md`, `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
`apps/dzik-os/docs/KOORDYNACJA.md`, `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`.

**Rola:** aktywny piszący (wyznaczony przez właściciela tą wiadomością).
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core (`hos_engine/`, `tests/` w korzeniu)
jest nietykalny.

**Gałąź:** `agent/ukryj-kreator` od aktualnego `main`. Pierwszy commit wyłącznie
`apps/dzik-os/docs/plan-sesji/ukryj-kreator.md` (szkic w `plan-sesji_ukryj-kreator.md`
obok). Po pushu draft PR `[WRITER] Ukryj kreator diety`. Dopiero potem kod.

**Rezerwacje:** wersja **wg kolejności scalania z `README.md` tego katalogu** (sprawdź
`CHANGELOG.md` i `STAN_PRZEKAZANIA.md` §2 tuż przed zmianą); **migracja: brak**
(żadnych zmian w danych). Nie rozwiązuj konfliktów automatycznie, nie rób
force-pusha, commituj po polsku, bez nazw modeli AI w commicie, nie scalaj PR-a.

---

#### 1. Decyzja właściciela (14.09.2026, druga tura)

> Ogólnie zrezygnujemy z kreatora diety na ten moment — wymaga wielkiej pracy, więc
> możemy go ukryć. Ale mamy dostęp do listy pojedynczych produktów, które można by
> skorelować z tymi, co chcemy wymieniać w szablonie.

Czyli: **kreator schowany, katalog produktów zostaje** (jest źródłem danych dla
zlecenia „Wymiany produktów v2”, §5a tamtego promptu). Dieta klienta = szablon
(`Przypisz dietę`).

#### 2. Rozpoznanie (zweryfikuj linie)

| Co | Gdzie | Los |
|---|---|---|
| Zakładka „Dieta” w Wiedzy trenera: sekcje „Ułóż dietę” (kompozytor), „Cel diety”, „Produkty (zaznacz do kompozycji)”, „Kreator diety”, „Utwórz plan żywieniowy z propozycji” | `frontend/src/pages/coach/Knowledge.tsx` l. 65 (`TABS`: `["dieta", "Dieta"]`), `DietTab` l. 79, sekcje l. 1518–1901 | **ukryć** za flagą (zakładka znika z `TABS`, gdy flaga wyłączona) |
| Zakładka „Produkty” (katalog `FoodProduct`, import/eksport CSV, „wbudowana baza”) | `Knowledge.tsx` l. 65, l. 1336–1408; API `routers/food_catalog.py` l. 154–561 | **zostaje bez zmian** |
| API kreatora | `routers/food_catalog.py` l. 604 `POST /coach/diet-wizard`, l. 646 `POST /coach/diet-suggestion` | za flagą: wyłączona → 404 (wzorzec `wymagaj_modulu()` z `routers/diet.py` l. 53–55) |
| Kontrakt klawiatury zakładek Wiedzy | `e2e/test_a11y.mjs` (komentarz nad `TABS` l. 60–63: kolejność pierwszych zakładek jest częścią kontraktu; strzałka z „Artykuły” trafia w „Ćwiczenia”) | usunięcie „Dieta” z listy nie zmienia pierwszych dwóch — sprawdź a11y |
| Wzorzec flagi | `backend/dzik_os/config.py` l. 128–136 (`_env("DZIK_…_ENABLED", "false") == "true"`), `fly.toml` `[env]` l. 37–41, `backend/tests/conftest.py` l. 29–34 (flagi włączone w testach), `/api/health` `features` w `main.py` l. 269 | nowa flaga `DZIK_DIET_WIZARD_ENABLED`, **domyślnie `false`**, w `fly.toml` **brak wpisu** (= ukryty na produkcji), w `conftest.py` `true` (istniejące testy kreatora dalej chodzą) |
| Testy kreatora | `backend/tests/test_diet_wizard.py`, wiersze w `backend/tests/access_matrix.py` | **zostają** (flaga w testach włączona) + nowy test: flaga wyłączona → obie trasy 404, `features.diet_wizard: false` |
| Plany żywieniowe z kreatora/ręczne (`NutritionPlan`) u klienta i trenera | `frontend/src/pages/client/Nutrition.tsx` l. 65–215, `ClientDetail.tsx` zakładka Dieta (formularz ręczny, „Z szablonu”, „Przypisz dietę”) | **bez zmian** — istniejące plany nadal widoczne; nic nie ginie (Karta §0.1) |
| Front — skąd wie o fladze | `ClientDetail.tsx` l. 705 sonduje `/api/diet/profiles` (try/catch); `/api/health` ma `features` | preferuj `features.diet_wizard` z `/api/health` (jedno źródło), a nie kolejną sondę |

#### 3. Co zbudować

1. `config.py`: `diet_wizard_enabled` (`DZIK_DIET_WIZARD_ENABLED`, domyślnie `false`).
2. `routers/food_catalog.py`: `wymagaj_kreatora()` → 404 dla `/coach/diet-wizard`
   i `/coach/diet-suggestion`, gdy flaga wyłączona (404, nie 403 — jak moduł diet).
3. `main.py`: `features.diet_wizard` w `/api/health`.
4. `Knowledge.tsx`: zakładka „Dieta” tylko przy `features.diet_wizard === true`
   (pobranie `/api/health` raz; przy błędzie — ukryta). Sekcje bez zmian w kodzie
   (nie kasuj komponentów — decyzja „na ten moment”).
5. `conftest.py`: flaga `true`; nowy test wyłączenia (przełączenie `settings` punktowo,
   jak test wyłączenia modułu diet).
6. `fly.toml`: **bez wpisu** + komentarz w `DEPLOYMENT.md` §flag, jak włączyć z powrotem.
7. Dokumentacja: `CHANGELOG.md`, `INSTRUKCJA_TRENERA.md` (kreator ukryty; dieta przez
   „Przypisz dietę”; katalog „Produkty” nadal do wglądu i importu), `RELEASE_STATUS.md`,
   `STAN_PRZEKAZANIA.md`, `DEFERRED_FEATURES.md` (kreator odłożony, powód, jak wrócić).

#### 4. Czego NIE robimy

Nie usuwamy kodu, tras, testów ani danych kreatora; nie ruszamy katalogu „Produkty”
ani `load-builtin`; nie ruszamy `NutritionPlan` (plany ręczne i istniejące plany
klientów); nie ruszamy „Ułóż z dań” (kulinaria) — pytanie 1.

#### 5. Weryfikacja

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q
python apps/dzik-os/tools/spojnosc.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```
Plus uruchomienie: jako trener wejdź w Wiedzę **bez flagi** — zakładki „Dieta” nie ma,
„Produkty” jest, klawiatura zakładek działa (a11y); w karcie klienta „Przypisz
dietę” działa; klient z planem ręcznym nadal go widzi. Zrzuty do PR.

#### 6. Pytania do właściciela

1. „Ułóż z dań” (kreator kulinarny, 0.57.0) w karcie klienta — też ukryć, czy zostawić?
   *Domyślnie: zostawić (osobny moduł, działa na recepturach, nie na kreatorze).*
2. Ręczny formularz planu żywieniowego w karcie klienta — zostawić? *Domyślnie: tak
   (nie jest kreatorem, a trener mógł z niego korzystać).*

### Źródło: `plan-sesji_ukryj-kreator.md`



**Gałąź:** `agent/ukryj-kreator` (od `main` = ⟨sha⟩). **Rola:** aktywny piszący — decyzja
właściciela 14.09.2026 („zrezygnujemy z kreatora diety na ten moment… możemy go ukryć”),
plik `PROMPT_writer_ukryj-kreator.md`. **Rezerwacje:** wersja ⟨wg kolejności scalania,
`docs/zlecenia/README.md`⟩, migracja **brak**. Pliki współdzielone: `config.py`, `main.py`
(`features`), `routers/food_catalog.py`, `Knowledge.tsx`, `conftest.py`, `CHANGELOG.md`.

#### Co robimy
Flaga `DZIK_DIET_WIZARD_ENABLED` (domyślnie wyłączona, brak wpisu w `fly.toml`): trasy
`/coach/diet-wizard` i `/coach/diet-suggestion` → 404, `features.diet_wizard` w health,
zakładka „Dieta” w Wiedzy trenera ukryta. Katalog „Produkty”, plany ręczne, istniejące
plany klientów, kod i testy kreatora — bez zmian.

#### Etapy
| Etap | Wytwarzam | Weryfikacja |
|---|---|---|
| 1 backend | flaga, `wymagaj_kreatora()`, health, test wyłączenia | pytest (kreator dalej zielony przy fladze w conftest) |
| 2 front | `TABS` warunkowe po `features.diet_wizard` | `tsc`, build, a11y (kolejność pierwszych zakładek), obejrzenie |
| 3 zamknięcie | CHANGELOG, INSTRUKCJA_TRENERA, DEPLOYMENT (jak włączyć), DEFERRED_FEATURES, RELEASE_STATUS, STAN_PRZEKAZANIA | ruff, spójność |

#### Czego nie dotykam
Kod/trasy/testy/dane kreatora (tylko bramka flagi), katalog produktów, `NutritionPlan`,
„Ułóż z dań”, dieta z szablonu, Core.

#### Odstępstwa / Weryfikacja wykonana / Plan kontra rzeczywistość
⟨uzupełnia sesja pisząca⟩


---

## 5. Zlecenie 1 — Dni treningowe na „Dzisiaj” (wersja 0.68.0 i migracja 37 zarezerwowane)

### Źródło: `PROMPT_writer_dni-treningowe.md`



---

Przeczytaj kolejno: `/AGENTS.md`, `/CLAUDE.md`,
`apps/dzik-os/docs/KARTA_WSPOLPRACY.md`, `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
`apps/dzik-os/docs/KOORDYNACJA.md`, `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`.

**Rola:** aktywny piszący (wyznaczony przez właściciela tą wiadomością).
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core (`hos_engine/`, `tests/` w korzeniu)
jest nietykalny — 275 testów Core musi zostać zielone.

**Gałąź:** `agent/dni-treningowe` od aktualnego `main`. Pierwszy commit zawiera
wyłącznie `apps/dzik-os/docs/plan-sesji/dni-treningowe.md` (szkic w pliku
`plan-sesji_dni-treningowe.md` obok tego promptu — uzupełnij go o rezerwacje
sprawdzone na żywo i wklej). Po pushu od razu draft PR `[WRITER] Dni treningowe`
do `main`. Dopiero potem kod.

**Rezerwacje (sprawdź w `db.py`, `CHANGELOG.md` i tabeli §2 `STAN_PRZEKAZANIA.md`
tuż przed zmianą — nie przepisuj z pamięci):** proponowane **wersja wg kolejności scalania z `README.md` tego katalogu,
migracja 37** (34 = ostatnia w `main`; 35 = `agent/biblioteka-diet`; 36 =
`agent/monitoring-postepy`). Jeśli któraś z tych gałęzi została scalona albo
zmieniła numer, weź kolejny wolny i odnotuj w planie sesji oraz w tabeli §2.
Zadanie jest niezależne od obu gałęzi w toku (nie dotyka diety ani monitoringu).

Nie rozwiązuj konfliktów automatycznie, nie rób force-pusha, commituj po polsku,
bez nazw modeli AI w treści commita. Nie scalaj własnego PR-a.

---

#### 1. Problem (słowami właściciela, 14.09.2026)

> Klient posiadający już plan na tydzień od trenera nie ma żadnej informacji,
> w jaki dzień realizuje jego części. Propozycja jest taka, żeby mógł sobie
> wybrać, w jakie dni tygodnia będzie go realizował. Chciałbym, żeby trening
> z konkretnego dnia pojawił się w pierwszej zakładce „Dziś”.

#### 2. Diagnoza (dlaczego dziś to nie działa)

Mechanizm „trening na dziś” **już istnieje**, ale zależy wyłącznie od pola
`weekday` wpisanego przez trenera w edytorze planu — i to pole jest prawie
zawsze puste:

* `TrainingPlanVersion.content_json` = `{"days": [{"id"?, "name", "weekday": int|null,
  "exercises": [...]}]}` (`backend/dzik_os/models.py` ~l. 252–256).
* `GET /api/me/today` (`backend/dzik_os/routers/today.py` l. 46–84) bierze
  najnowszy ACTIVE plan klienta, jego bieżącą wersję i **pierwszy** dzień, którego
  `weekday == local_today(user).isoweekday()`. Brak dopasowania → `workout: null`
  → ekran „Dzisiaj” pokazuje kartę „Dziś bez treningu / Regeneracja też jest częścią
  planu” (`frontend/src/pages/client/Today.tsx` l. 192–197). Klient z planem
  bez `weekday` widzi to **codziennie** — stąd zgłoszenie.
* `weekday` jest opcjonalne (`PlanDayIn.weekday: int | None`, `schemas.py` l. 95–99);
  `PlanEditor.tsx` l. 33 i 309 tworzy dni z `weekday: null`; gotowe schematy
  (`plan_templates.py` l. 94), kopie z szablonów, duplikaty i import nadają `None`.
* Klient nie ma **żadnego** sposobu, żeby to ustawić — `Plan.tsx` l. 255 tylko
  wyświetla odznakę dnia, jeśli trener ją wpisał.

Wniosek: nie budujemy nowego „harmonogramu treningów”, tylko dajemy klientowi
**własną nakładkę dni tygodnia** na plan trenera i uczymy `/api/me/today`, żeby
ją respektowało.

#### 3. Rozpoznanie — fakty z kodu (zweryfikuj linie)

| Co | Gdzie | Uwaga |
|---|---|---|
| Model planu i wersji (niemutowalne wersje, `reason`) | `models.py` l. 224–262 | wersje NIGDY nie są nadpisywane — nakładka klienta nie może zmieniać `content_json` |
| Stabilne `id` dni/ćwiczeń (0.58.0) | `publikacja/elementy.py::znormalizuj` l. 73–96 | nadawane przy publikacji ze szkicu i przy duplikacji; **starsze wersje i seed mogą nie mieć `id`** → potrzebny klucz zastępczy |
| Wybór treningu na dziś | `routers/today.py` l. 46–84 | pierwszy dzień z `weekday == dziś`; `done_today` po `WorkoutSession(plan_version_id, day_index, performed_on)` |
| Oznaczanie wykonania | `Today.tsx` l. 57–64 → `POST /api/clients/{id}/workouts` z `plan_version_id`, `day_index` | zostaje bez zmian (klucz = indeks dnia w wersji) |
| Widok planu klienta | `frontend/src/pages/client/Plan.tsx` l. 250–258 | karta dnia z odznaką `WEEKDAYS[day.weekday-1]` |
| Typy | `frontend/src/types.ts` l. 51–56 (`PlanDay`), l. 418–433 (`TodayData.workout`) | |
| Wzorzec zasobu klienta z dostępem trenera (0.63.0) | `routers/habits.py` (cały), `authz.resolve_client_access(..., action="write", domain=DOMAIN_TRAINING)`, `deny` → 404 | **kopiuj ten wzorzec 1:1** (dostęp, IDOR = 404, `record_event`) |
| Macierz dostępu | `backend/tests/access_matrix.py` l. 154–166 (`/api/clients/{client_id}/plans`, `.../habits` = `CLIENT_SCOPED`) | każdą nową trasę dopisz do macierzy |
| Eksport i usunięcie konta | `routers/privacy.py` l. 359–360, 409, 618–619 (wzorzec dla `Habit`) | **nowa tabela klienta MUSI trafić do eksportu i do usuwania** — test nawyków to sprawdza, zrób tak samo |
| Migracje | `db.py` l. 1440+ (wpis 34 jako wzorzec: `CREATE TABLE IF NOT EXISTS`, indeks, przenośność na PostgreSQL — BOOLEAN default `false`, `test_migracje_przenosnosc`) | |
| Seed demo | `seed.py` l. 254–290 (plan klienta A: „Trening A — góra” pon., „Trening B — dół” śr., „Trening C — całe ciało” pt.; l. 304–318 plan FBW wt./czw./sob.) | trener ustawił tu `weekday`, więc demo dziś działa — dodaj wariant **bez** `weekday` (patrz §5 seed) |
| Ekran trenera | `pages/coach/ClientDetail.tsx` (zakładka Plan) | pokaż wybór klienta tylko do odczytu |
| Gotowe pickery dnia tygodnia do skopiowania | `pages/coach/PlanEditor.tsx` l. 408–417, `pages/coach/SzkicPlanu.tsx` l. 392–396 (`<option value="">— dowolny —</option>` + `WEEKDAYS` z `dates.ts` l. 63) | ten sam `select` u klienta |
| Ślad audytu | `hos_bridge.record_event(db, action=..., actor_id, subject_ids, payload, summary)` **przed** `db.commit()`, payload tylko nazwy pól, nigdy wartości (wzorzec `habits.py` l. 155–157) | |
| Wzorzec panelu klienta zasilanego z `/api/me/today` | `pages/nawyki/PanelNawykow.tsx` (`onZmiana={load}`) | ten sam kształt dla karty „ustaw dni” |
| Zgody | domena `training_data` (jak harmonogram i nawyki) | bez nowej bramki zgód |
| a11y / E2E | `e2e/test_a11y.mjs` (jeden `h1` na „Dzisiaj”), `frontend/e2e/nawyki.spec.ts` + `helpers.ts` jako wzorzec, strefa `Europe/Warsaw` w `playwright.config.ts` | E2E musi liczyć „dzisiejszy” dzień tygodnia dynamicznie, nie na sztywno |

#### 4. Decyzje projektowe (propose-only → właściciel zatwierdził kierunek tą wiadomością)

1. **Nakładka klienta, nie edycja planu.** Wybór dni to osobny byt należący do
   klienta (`author_id` = klient albo trener), przypięty do `(client_id, plan_id)`.
   Wersje planu pozostają niemutowalne; trener nadal może wpisać `weekday` jako
   **domyślną propozycję**.
2. **Zasada pierwszeństwa — prosta i bez mieszania:** jeśli klient zapisał
   układ dla danego planu, obowiązuje **wyłącznie** jego układ (dni bez wpisu =
   nieprzypisane). Jeśli nie zapisał — obowiązują `weekday` trenera jak dziś.
   Formularz klienta startuje wstępnie wypełniony propozycją trenera.
   Powód: mieszanie dwóch źródeł per dzień daje kolizje, których nikt nie
   rozstrzygnie (dwa treningi w ten sam dzień, jeden z trenera, drugi z klienta).
3. **Klucz dnia:** `day.id`, jeśli wersja go ma; w przeciwnym razie `idx:<indeks>`.
   Klucz wyliczany jedną czystą funkcją i użyty wszędzie (API, `today`, front).
   Gdy trener opublikuje nową wersję: wpisy z nieistniejącym już kluczem są
   ignorowane, a klient widzi na Planie i na „Dzisiaj” łagodną notkę „Plan
   się zmienił — sprawdź dni tygodnia” (bez czerwieni, bez blokady).
4. **Walidacja:** `weekday` 1–7 albo brak (dzień wolny od tej jednostki); jeden
   dzień tygodnia może mieć **co najwyżej jedną** jednostkę (duplikat → 422
   z czytelnym komunikatem po polsku); klucz spoza bieżącej wersji planu → 422.
5. **Dostęp:** klient — swoje; trener — aktywna relacja + zgoda `training_data`
   (odczyt i zapis, żeby mógł pomóc klientowi na konsultacji); obcy klient / obcy
   plan → 404 logowane (`deny`). AGENT/SERVICE nie dotyczy (brak takich ról tutaj).
6. **Ślad:** `record_event(action="PLAN_WEEKDAYS_SET", ...)` z `plan_id` i liczbą
   przypisanych dni (bez treści planu). Historia: kolejny zapis nadpisuje układ
   (to preferencja, nie plan — nie wersjonujemy), ale zdarzenie audytu zostaje.
7. **Zero AI, zero rekomendacji.** System nie proponuje „lepszych” dni. Jedyny
   automatyzm to prefill z propozycji trenera.
8. **Human OS / INTENDED_PURPOSE:** dane = wybór dnia tygodnia dla jednostki
   treningowej; brak treści zdrowotnej; klient pozostaje autorem swojego tygodnia.
   Bez pytania do foundera.

#### 5. Co dokładnie zbudować

##### Backend

* **Moduł czystych funkcji `dzik_os/dni_treningowe.py`:**
  `klucz_dnia(day, idx) -> str`, `uklad_efektywny(content, wybor|None) ->
  dict[klucz, weekday|None]`, `dzien_na_dzis(content, wybor|None, weekday) ->
  (idx, day) | None`, `klucze_nieaktualne(content, wybor) -> list[str]`.
  Testy jednostkowe na przykładach ręcznych (prefill z trenera, nakładka wygrywa
  w całości, duplikat, klucz zastępczy `idx:`, klucz nieaktualny).
* **Model `PlanWeekdayChoice`** (jeden wiersz per `(client_id, plan_id)`,
  `UniqueConstraint`): `id`, `client_id`, `plan_id`, `choices_json`
  (`[{"day_key": "...", "weekday": 1..7|null}]`), `author_id`, `author_note|null`,
  `created_at`, `updated_at`, `version`. **Migracja 37** (patrz rezerwacje).
* **API** (prefix `/api`, plik `routers/plan_weekdays.py`, rejestracja w `main.py`,
  wiersze w `access_matrix.py`):
  * `GET /api/clients/{client_id}/plans/{plan_id}/dni` → `{plan_id, version_no,
    source: "client"|"coach"|"none", days: [{day_key, day_index, name,
    coach_weekday, weekday}], stale_keys: [...]}`
  * `PUT /api/clients/{client_id}/plans/{plan_id}/dni` body `{choices: [...],
    author_note?}` → to samo co GET po zapisie; walidacja z §4 pkt 4.
  * `DELETE …/dni` → wraca do propozycji trenera (`source: "coach"`).
* **`/api/me/today`:** zamiast pętli po `weekday` użyj `dzien_na_dzis(...)`; dołóż
  do `workout` pole `weekday_source: "client"|"coach"` i do odpowiedzi
  `workout_hint: {"kind": "no_weekdays"|"stale", "plan_id": ...} | null`, żeby
  front mógł pokazać „Ustaw dni tygodnia” zamiast „Dziś bez treningu”, gdy plan
  istnieje, ale nie ma żadnego przypisania.
* **Prywatność:** `privacy.py` — eksport (`"plan_weekday_choices"`, podbij
  `export_version` z `"1.8"` na `"1.9"` i popraw test, który go sprawdza) i usunięcie
  konta (delete po `client_id`), + test jak w `test_habits.py`.
* **Seed:** **bez zmian w istniejących planach demo** (klient A pon./śr./pt.,
  klient B wt./czw./sob. — inne testy na nich polegają). Stan „plan bez dni”
  tworzysz w teście przez API trenera (`POST /api/plans` z `weekday: null` dla
  klienta z `create_activated_client`). Nie dokładaj klientom demo drugiego
  planu ACTIVE — `today` bierze najnowszy ACTIVE i zmieniłoby to inne testy.
* **Flaga:** bez flagi (jak nawyki 0.63.0 — dodatek UI klienta + tabela
  addytywna; właściciel 14.09: nowe funkcje mają być widoczne).

##### Frontend

* **`pages/client/Plan.tsx`:** nad listą dni karta „Twoje dni treningowe” —
  dla każdej jednostki `select` pon.–niedz./„—”, prefill z propozycji trenera,
  przycisk „Zapisz dni”, komunikat sukcesu, błąd 422 pokazany przy polu, link
  „Wróć do propozycji trenera” (DELETE). Odznaka przy dniu: „pon. (Twój wybór)”
  albo „pon. (propozycja trenera)”. Notka o nieaktualnych kluczach (§4 pkt 3).
* **`pages/client/Today.tsx`:** gdy `workout_hint.kind === "no_weekdays"` — karta
  „Masz plan, ale nie wybrałeś dni tygodnia” z linkiem do Planu; gdy
  `workout` jest — mała etykieta źródła („Twój wybór” / „propozycja trenera”).
  Reszta karty (ćwiczenia, „Wykonane ✓”) bez zmian.
* **`pages/coach/ClientDetail.tsx` (zakładka Plan):** tylko do odczytu: przy
  każdej jednostce dzień wg klienta, jeśli ustawił; bez edycji w tej rundzie.
* **`types.ts`:** rozszerz `TodayData.workout` i dodaj typy odpowiedzi `/dni`.

##### Testy

* `backend/tests/test_dni_treningowe.py` (silnik + API): zapis i odczyt,
  prefill z trenera, nakładka wygrywa w całości, duplikat dnia → 422, klucz spoza
  wersji → 422, `weekday` 0/8 → 422, obcy klient → 404 (IDOR), trener z relacją
  i zgodą → 200, trener bez zgody treningowej → jak w `test_habits.py`, `today`
  bez wyboru = dzień trenera, `today` z wyborem = dzień klienta, `today` bez
  niczego = `workout: null` + `workout_hint.no_weekdays`, nowa wersja planu z tymi
  samymi `id` zachowuje wybór, usunięty dzień → `stale_keys`, eksport i usunięcie
  konta, wpis audytu `PLAN_WEEKDAYS_SET`.
* Macierz dostępu (`test_access_matrix.py`) zielona z nowymi wierszami.
* E2E `frontend/e2e/dni-treningowe.spec.ts` (na **kliencie B** — A jest
  współdzielony między specami; wzorzec `nawyki.spec.ts`: `zaloguj`, `data-testid`,
  `page.reload()` jako dowód zapisu po stronie serwera): Plan → w karcie „Twoje
  dni treningowe” ustawia **dzisiejszy** dzień tygodnia (liczony z `new Date()`
  w strefie `Europe/Warsaw` jak `raport.spec.ts`) dla jednostki „FBW 1”, pozostałe
  na „—” → „Zapisz dni” → reload → „Dzisiaj” pokazuje „FBW 1” i etykietę „Twój
  wybór”; potem „Wróć do propozycji trenera” → odznaki znów „propozycja trenera”.
  Drugi scenariusz: duplikat dnia → komunikat przy polu, nic nie zapisane.
  Stan „plan bez dni” pokrywa test API (nie E2E).

##### Dokumentacja (etap zamknięcia)

`CHANGELOG.md` 0.66.0, `INSTRUKCJA_KLIENTA.md` (§ „Ekran Dzisiaj” i § Plan),
`INSTRUKCJA_TRENERA.md` (co widzi trener), `PERMISSIONS.md` (nowe trasy),
`RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md` §1/§2, plan sesji („Odstępstwa”,
„Weryfikacja wykonana”). `docs/dni-treningowe/00_rozpoznanie.md` i `PROGRESS.md`
jak w `docs/nawyki/`.

#### 6. Czego świadomie NIE robimy

* Nie edytujemy `content_json` żadnej wersji planu i nie tworzymy nowej wersji
  „z dniami” — to nie jest zmiana planu trenera.
* Nie wpinamy tego w Harmonogram (`ScheduleItem`, kategoria TRENING) — to
  przypomnienia, inny byt; dublowanie = dwa mechanizmy na stałe.
* Nie dodajemy powiadomień push o treningu „na dziś” (osobna decyzja).
* Nie pozwalamy na dwie jednostki w jeden dzień ani na tygodnie A/B — v1 to
  jeden tydzień. Jeśli właściciel zechce rotację, to nowa runda.
* Nie zmieniamy `POST /api/clients/{id}/workouts` ani klucza `day_index`.

#### 7. Weryfikacja przed przekazaniem (z korzenia repozytorium)

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Plus **uruchomienie i obejrzenie** (`ZASADA_URUCHOMIENIA.md`): przez serwer E2E
zaloguj klienta z planem bez dni, ustaw dzisiejszy dzień, wróć na „Dzisiaj”,
zrób zrzut. W raporcie napisz, CO KLIKNĄŁEŚ I CO ZOBACZYŁEŚ — nie „sprawdzone”.
Przegląd: 3 recenzentów wsadowo (bezpieczeństwo/zgody, poprawność silnika
i `today`, testy/UX/treść), P0/P1 naprawione przed przekazaniem, P2 do
`docs/dni-treningowe/PROGRESS.md`. Bezpiecznik: 3× plan.

#### 8. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)

1. Czy trener ma móc **edytować** wybór klienta z karty klienta? *Domyślnie:
   tak (relacja + zgoda), bo tak jest z nawykami i harmonogramem.*
2. Czy dopuszczamy dwie jednostki tego samego dnia? *Domyślnie: nie (422).*
3. Gdy klient nie wybrał dni, a trener też nie — „Dzisiaj” ma pokazywać
   pierwszą jednostkę planu „na zachętę”, czy tylko kartę „ustaw dni”?
   *Domyślnie: tylko kartę „ustaw dni” — system nie zgaduje za człowieka.*

### Źródło: `plan-sesji_dni-treningowe.md`



**Gałąź:** `agent/dni-treningowe` (od `main` = ⟨sha⟩, po ⟨wersja main⟩). **Rola:** aktywny
piszący — polecenie właściciela z 14.09.2026 („klient posiadający już plan na tydzień od
trenera nie ma żadnej informacji, w jaki dzień realizuje jego części — niech wybierze dni
tygodnia; trening z konkretnego dnia ma pojawić się w zakładce „Dziś””), plik
`PROMPT_writer_dni-treningowe.md` (diagnoza, rozpoznanie, decyzje, zakres).
**Rezerwacje (KOORDYNACJA §0):** wersja ⟨wg kolejności scalania, `docs/zlecenia/README.md`⟩, migracja **37** (addytywna:
`plan_weekday_choices`) — ⟨potwierdzone w `db.py` / `CHANGELOG.md` / `STAN_PRZEKAZANIA.md` §2
dnia ⟨data⟩; jeśli 35/36 zostały scalone albo przesunięte, numery skorygowane tutaj i w §2⟩.
Pliki współdzielone: `models.py` (klasa na końcu), `db.py` (wpis 37), `main.py` (rejestracja
routera), `access_matrix.py`, `routers/today.py`, `routers/privacy.py`, `types.ts`
(`TodayData`), `CHANGELOG.md`. Kolejność scalania: po `agent/biblioteka-diet` i
`agent/monitoring-postepy`, jeśli będą gotowe wcześniej; w przeciwnym razie niezależnie
(zadanie nie dotyka diety ani monitoringu).

#### Co robimy

1. **Nakładka dni tygodnia klienta** na plan trenera: `PlanWeekdayChoice` (jeden wiersz per
   klient × plan, `choices_json` = lista `{day_key, weekday|null}`), API
   `GET/PUT/DELETE /api/clients/{client_id}/plans/{plan_id}/dni`.
2. **„Dzisiaj” respektuje nakładkę:** `dzien_na_dzis(content, wybor, weekday)` zamiast pętli
   po `weekday` trenera; `workout.weekday_source` i `workout_hint` (plan bez dni → karta
   „ustaw dni” zamiast „Dziś bez treningu”).
3. **UI klienta:** karta „Twoje dni treningowe” w zakładce Plan (prefill z propozycji trenera,
   zapis, powrót do propozycji), etykiety źródła na Planie i na „Dzisiaj”.
4. **UI trenera:** dzień wg klienta tylko do odczytu w karcie klienta (zakładka Plan).

#### Decyzje projektowe (właściciel 14.09 + wykonawcze)

* **Wersje planu niemutowalne** — nakładka nigdy nie dotyka `content_json`; trener nadal
  wpisuje `weekday` jako propozycję.
* **Bez mieszania źródeł:** zapisany układ klienta obowiązuje w całości; brak układu →
  propozycja trenera. Prefill formularza z propozycji trenera.
* **Klucz dnia:** `day.id` (stabilne `id` z publikacji 0.58.0) albo `idx:<n>` dla wersji
  bez `id` (seed, starsze wersje). Klucze nieaktualne po nowej wersji → ignorowane + łagodna
  notka „Plan się zmienił — sprawdź dni”.
* **Walidacja:** `weekday` 1–7 albo null; jeden dzień tygodnia = maks. jedna jednostka (422);
  klucz spoza bieżącej wersji (422).
* **Dostęp:** jak nawyki i harmonogram — klient swoje; trener z relacją i zgodą
  `training_data` (odczyt i zapis); obcy → 404 (`deny`). Bez nowej bramki zgód.
* **Ślad:** `PLAN_WEEKDAYS_SET` / `PLAN_WEEKDAYS_CLEARED` (payload: `plan_id`, liczba
  przypisanych dni — bez treści planu). Preferencja nadpisywana, zdarzenie zostaje.
* **Zero AI, zero rekomendacji dni.** Bez flagi (jak 0.63.0).
* **INTENDED_PURPOSE:** wybór dnia tygodnia = dane treningowe bez treści zdrowotnej;
  klient autorem swojego tygodnia. Bez pytania do foundera.

#### Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie | linie wskazane w prompcie (`today.py` 46–84, `models.py` 224–262, `elementy.py::znormalizuj`, `habits.py`, `privacy.py` 359–410/618, `access_matrix.py`, `Plan.tsx` 250–258, `Today.tsx` 156–197, `PlanEditor.tsx` 408–417) — tylko weryfikacja, bez ponownego rozpoznania | `docs/dni-treningowe/00_rozpoznanie.md` + ten plan | — | dziesiątki tys. |
| 1 silnik | — | `dzik_os/dni_treningowe.py`: `klucz_dnia`, `uklad_efektywny`, `dzien_na_dzis`, `klucze_nieaktualne` | `tests/test_dni_treningowe_silnik.py` na przykładach ręcznych | dziesiątki tys. |
| 2 model + migracja 37 | `models.py`, `db.py` (wpis 34 jako wzorzec) | `PlanWeekdayChoice`, migracja przenośna | `test_migracje_przenosnosc` | dziesiątki tys. |
| 3 API + `today` + prywatność | `routers/today.py`, `routers/habits.py`, `routers/privacy.py` | `routers/plan_weekdays.py`, zmiana `today.py`, eksport/usuwanie, macierz dostępu, `tests/test_dni_treningowe.py` | pytest modułu + macierz + prywatność | setki tys. |
| 4 UI | `Plan.tsx`, `Today.tsx`, `ClientDetail.tsx` (Plan), `PanelNawykow.tsx`, `types.ts`, `dates.ts` | karta „Twoje dni treningowe”, karta „ustaw dni” na „Dzisiaj”, etykiety źródła, widok trenera; E2E `dni-treningowe.spec.ts` (klient B) | `tsc`, build (budżet 120 kB), `test:helpers`, E2E, a11y (jeden `h1`), obejrzenie przez serwer E2E | setki tys. (największy koszt) |
| 5 zamknięcie | — | CHANGELOG 0.66.0, RELEASE_STATUS, PERMISSIONS, INSTRUKCJA_KLIENTA/TRENERA, STAN_PRZEKAZANIA §1/§2, `docs/dni-treningowe/PROGRESS.md` | pełny pytest, ruff z korzenia, spójność, mutacje, CI | dziesiątki tys. |

**Największy koszt:** etap 4. Taniej bez utraty informacji: jeden `select` skopiowany
z `PlanEditor.tsx`, karta na „Dzisiaj” w kształcie `PanelNawykow` (odświeżanie przez
`onZmiana={load}`), brak osobnego ekranu. Bezpiecznik: 3× plan. Przegląd: 3 recenzentów
wsadowo (bezpieczeństwo/zgody, poprawność silnika i `today`, testy/UX/treść), P0/P1
naprawione przed przekazaniem, P2 do `docs/dni-treningowe/PROGRESS.md`.

#### Czego nie dotykam

`content_json` wersji planu, `POST /api/clients/{id}/workouts` i klucz `day_index`,
Harmonogram (`ScheduleItem`), powiadomienia push, dieta, monitoring, Core Human OS.

#### Czego świadomie nie robię

Dwie jednostki w jeden dzień, tygodnie A/B (rotacja), edycja wyboru klienta przez trenera
z osobnego ekranu (tylko odczyt w tej rundzie — chyba że właściciel odpowie inaczej na
pytanie 1 promptu), przypomnienia o treningu „na dziś”.

#### Odstępstwa od planu

⟨uzupełnia sesja pisząca⟩

#### Weryfikacja wykonana

⟨uzupełnia sesja pisząca: co uruchomiono i co zobaczono — nie „sprawdzone”⟩

#### Plan kontra rzeczywistość (zasady v2 §5)

⟨uzupełnia sesja pisząca⟩


---

## 6. Zlecenie 2 — Wymiany produktów v2 (scalone jako 0.69.0, PR #69)
*Stan: silnik v2 i korelacja katalogu scalone 14.09. Otwarte: przegląd CSV propozycji przez właściciela (TAK/NIE) i import zatwierdzonych wierszy osobnym małym PR-em.*

### Źródło: `PROMPT_writer_wymiany-produktow.md`



---

Przeczytaj kolejno: `/AGENTS.md`, `/CLAUDE.md`,
`apps/dzik-os/docs/KARTA_WSPOLPRACY.md`, `apps/dzik-os/docs/STAN_PRZEKAZANIA.md`,
`apps/dzik-os/docs/KOORDYNACJA.md`, `apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`,
a potem `apps/dzik-os/docs/diet-module/PROGRESS.md` i
`apps/dzik-os/docs/diet-module/instrukcja_szablony_diet.md`.

**Rola:** aktywny piszący (wyznaczony przez właściciela tą wiadomością).
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core (`hos_engine/`, `tests/` w korzeniu)
jest nietykalny — 275 testów Core musi zostać zielone.

**WARUNEK STARTU:** gałąź `agent/biblioteka-diet` (0.64.0, migracja 35, 181
produktów, silnik v1.1) musi być **scalona do `main`** zanim odgałęzisz to zadanie.
Powód: ona zmienia `dieta/silnik.py`, `dieta/dane/produkty.csv` i seed — czyli
dokładnie pliki tej rundy; równoległa praca = pewny konflikt znaczeniowy (STOP wg
karty). Sama biblioteka zmniejsza już odsetek składników bez zamiennika z **31 %
do 11 %** (pomiar niżej) — to jest pierwszy krok naprawy i **nie wymaga kodu**.
Jeśli PR biblioteki nie jest scalony: zgłoś to właścicielowi i nie zaczynaj.

**Gałąź:** `agent/wymiany-produktow` od aktualnego `main` (po scaleniu biblioteki).
Pierwszy commit wyłącznie `apps/dzik-os/docs/plan-sesji/wymiany-produktow.md`
(szkic w `plan-sesji_wymiany-produktow.md` obok tego promptu — uzupełnij rezerwacje
sprawdzone na żywo). Po pushu od razu draft PR `[WRITER] Wymiany produktów`.
Dopiero potem kod.

**Rezerwacje (sprawdź w `db.py`, `CHANGELOG.md` i tabeli §2 `STAN_PRZEKAZANIA.md`
tuż przed zmianą):** proponowana **wersja wg kolejności scalania z `README.md` tego katalogu**
(numer wersji musi rosnąć w kolejności scalania — kontrola `changelog`). **Migracja:
brak** w wariancie rekomendowanym (powiązania grup jako plik danych ładowany przez
silnik; bez nowych kolumn). Jeśli w trakcie okaże się potrzebna (np. kolumna na
produkcie) — weź kolejny wolny numer i odnotuj w planie i w §2; nie zgaduj.

Nie rozwiązuj konfliktów automatycznie, nie rób force-pusha, commituj po polsku,
bez nazw modeli AI w treści commita. Nie scalaj własnego PR-a.

---

#### 1. Problem (słowami właściciela, 14.09.2026)

> Klient w zakładce Dieta przy elementach składowych posiłków ma przycisk, który
> powinien dawać mu szansę na wymianę jakiegoś produktu. Teraz to nie działa.
> Żeby to uruchomić, trzeba powiązać pokrewne grupy towarowe, by makro i funkcja
> w posiłku się zgadzały.

#### 2. Diagnoza — co naprawdę jest zepsute (zmierzone, nie oszacowane)

Przycisk **jest podpięty od końca do końca** i dla części składników działa (E2E
`dieta-szablon.spec.ts` dowodzi: kurczak → indyk). Zepsuta jest **podaż kandydatów**,
z czterech niezależnych przyczyn. Kolejność wg wagi:

| # | Przyczyna | Skala (Standard v1, 2000 kcal, `main` 0.63.0) | Gdzie |
|---|---|---|---|
| 1 | **Bramka tolerancji posiłku jest absolutna.** Kandydat przechodzi tylko, gdy posiłek *po* wymianie mieści się w `TOL_MEAL` (±8 %/40 kcal, P ±5 g, F ±4 g, C ±10 g) — tym samym `check()`, którym posiłek już był oceniony. **Posiłek, który już jest OSTRZEŻENIE/POZA ZAKRESEM, nigdy nie dostanie kandydata** — czyli wymiana jest martwa dokładnie tam, gdzie klient jej najbardziej potrzebuje. | 25 z 34 pustych list (21 w posiłkach już poza tolerancją) | `backend/dzik_os/dieta/silnik.py` l. 361–396 (`swap_candidates`), bramka l. ~390 |
| 2 | **Przycisk nie jest renderowany dla składników z rolą `NONE`** (warzywa, przyprawy, dodatki), bo `swappable` domyślnie = `role in ("P","C","F")`. To **124 z 232** składników szablonu — klient nie może zamienić brokułu na kalafior, choć oba są w `warzywa_gotowane`. | 124/232 składników bez przycisku | `backend/dzik_os/dieta/seed.py` l. ~234; `DietaSzablon.tsx` l. 89–92 (cztery warunki AND: `swappable && swaps_enabled && !swaps_locked && class !== "STAŁY"`) |
| 3 | **Grupy-singletony** — produkt sam w swojej `substitution_group` nigdy nie ma kandydata. | `main`: 8 singletonów (Jogurt grecki 10 %, Hummus, Płatki owsiane, Awokado, Gorzka czekolada, Bulion, WPC 80, Szynka z indyka); po bibliotece: 3 (Jogurt grecki 10 %, Awokado, Gorzka czekolada) | `dieta/dane/produkty.csv` kolumna `substitution_group` |
| 4 | **Zgodność „funkcji” = tylko twarde przecięcie `cooking_tags`**; brak przecięcia = odpad (np. tuńczyk z puszki vs ryby surowe w `ryba_chuda`). Nie ma pojęcia „grupy pokrewnej” — kandydat musi być z **dokładnie tej samej** grupy (`q.substitution_group != p.substitution_group → continue`). | 1 z 34 na `main`, ale to jest bariera dla całego pomysłu właściciela | `silnik.py` l. ~372 (A) i ~378 (B) |

**Pomiar (silnik + prawdziwe dane seeda, składniki z rolą P/C/F = 108):**

| Stan | posiłki nie-OK | składników bez ŻADNEGO kandydata |
|---|---|---|
| `main` 0.63.0, 1600 kcal | 5/28 | 27 |
| `main` 0.63.0, 2000 kcal | 6/28 | **34 (31 %)** |
| `main` 0.63.0, 2600 kcal | 3/28 | 31 |
| po `agent/biblioteka-diet` (181 produktów, silnik v1.1), 2000 kcal | 0/28 | **12 (11 %)** |

Wnioski: (a) scalenie biblioteki to pierwszy, bezkodowy krok; (b) resztę załatwia
przebudowa `swap_candidates` + dane powiązań grup + przycisk dla roli `NONE`.

**Ważne rozróżnienie (nie pomyl):** `docs/diet-module/PROGRESS.md` pyta „włączyć
regułę `group` domyślnie?”. To jest `DietTemplateIngredient.group_name`
(wspólny współczynnik skalowania ciasta/marynaty — `enforce_groups`, `silnik.py`
l. 194–239), **nie** grupa zamienników. Włączenie jej nie da ani jednego kandydata.
Grupa zamienników to `DietProduct.substitution_group` (`models.py` l. ~1847).

**Drugi przepływ diety — decyzja właściciela 14.09 (druga tura):** kreator diety
schodzi na bok („wymaga wielkiej pracy, możemy go ukryć”) — ukrycie to osobne, małe
zlecenie 3 (`PROMPT_writer_ukryj-kreator.md`). Plan z kreatora (`NutritionPlan`,
`Nutrition.tsx` l. 65–215) ma „zamienniki” jako **tekst** (`m.swaps`, l. 140) bez
przycisku i to zadanie go nie dotyka. **Klient jest na diecie z szablonu** — pytanie 1
z §9 jest rozstrzygnięte. Natomiast **katalog pojedynczych produktów trenera zostaje
i staje się źródłem nowych zamienników** — patrz §5a.

#### 3. Rozpoznanie — fakty z kodu (zweryfikuj linie po scaleniu biblioteki)

| Co | Gdzie |
|---|---|
| Przycisk i arkusz wymiany u klienta | `frontend/src/pages/client/DietaSzablon.tsx` l. 37–57 (`otworz` → `GET /api/diet/assigned/{id}/swaps?day&meal&ingredient`; `wymien` → `POST …/swaps`), l. 89–92 (warunki przycisku), l. 104–108 (stany: „Szukam…”, `blocked`, „Brak bezpiecznego zamiennika, napisz do trenera”) |
| Typy | `frontend/src/types.ts` l. 1696–1735 (`DietIngredientOut`, `DietMealOut`, `DietSwapCandidate {product, product_id, grams, macros}`) |
| API wymian | `backend/dzik_os/routers/diet.py` l. 325–349 (GET kandydaci + `blokada`), l. 352–400 (POST: kandydaci liczeni ponownie serwerowo, `to_product_id` musi być na liście → inaczej 422; gramatura walidowana `TOL_MEAL`; zapis `overrides_json["ingredients"]["day:meal:ing"]` + `DietSwapEvent` + audyt `DIET_SWAP`), l. 403–423 (PATCH `swaps_enabled`, `meal_swaps_enabled`) |
| Serwis | `backend/dzik_os/dieta/serwis.py` l. 252–270 (`kandydaci_wymiany`: `posilek_silnika` z migawki po korektach, wykluczenia alergenów/diet/„nie lubię” po nazwie), l. 31–37 (`produkt_silnika`: `substitution_group` → `""` gdy brak) |
| Silnik (kopia 1:1 prototypu `docs/diet-module/engine.py`) | `backend/dzik_os/dieta/silnik.py`: `TOL_MEAL`/`TOL_DAY` l. 38–39, `check` l. 183–188, `swap_candidates` l. 361–396; na gałęzi biblioteki dodatkowo limity porcji (mięso/ryby 300 g, jajka ≤4, tłuszcz krok 1 g) l. ~89–108 i `alergeny()` l. ~253 |
| Model produktu | `models.py` l. 1836–1862 `DietProduct` (`category`, `substitution_group`, makra/100 g, `cooking_tags` CSV z `*` jako wildcard, `allergens`, `diet_exclusions`, `default_scaling`, `source*`); rola makro jest **per składnik** (`DietTemplateIngredient.macro_role`, `group_name`, `swappable` l. 1940–1947), nie per produkt |
| Dane | `backend/dzik_os/dieta/dane/produkty.csv` (po bibliotece 181 wierszy, 40 grup; lista grup i członków niżej), `dane/szablon_standard_v1.json` (7 dni, 28 posiłków, 232 składniki), po bibliotece `dane/szablony/*.json` (45 odsłon) i `dane/biblioteka_index.json`; `docs/diet-module/subst_maps.json` (mapa 1:1 bez laktozy/glutenu użyta **offline** do generowania odsłon — nie jest w runtime) |
| Testy do świadomej aktualizacji | `backend/tests/test_dieta_silnik.py` l. 152 (`test_swap_candidates_nie_wyprowadza_poza_tolerancje_i_skyr_bez_laktozy_pusty` — złota lista `[Pierś z indyka, Schab, Polędwiczka] / [155,150,170]` **i pusta lista dla skyru bez laktozy zapisana jako poprawne zachowanie** — po bibliotece skyr bez laktozy istnieje, więc ten przypadek zmienia sens), l. 189 (`test_stale_silnika_identyczne_z_prototypem` — **nie zmieniaj `TOL_MEAL`/`TOL_DAY`**), l. 209; `backend/tests/test_dieta_api.py` l. 194 (`candidates == []` i `blocked is None` dla laktozy), l. 231; `test_dieta_poprawki.py` l. 65, 229, 248; E2E `frontend/e2e/dieta-szablon.spec.ts` l. 23–60 (jedyny ćwiczony składnik: kurczak → indyk) |
| Flaga | `DZIK_DIET_TEMPLATES_ENABLED` — produkcja `true` (`fly.toml` l. 37), testy w `conftest.py`; `routers/diet.py` l. 53–55 `wymagaj_modulu()` |
| Prototyp referencyjny | `docs/diet-module/engine.py` — po tej rundzie **silnik przestaje być 1:1 z prototypem w `swap_candidates`**: odnotuj to w `docs/diet-module/PROGRESS.md` i w docstringu funkcji (nie udawaj zgodności) |

**Grupy zamienników po bibliotece (181 produktów, 40 grup) — do tabeli powiązań:**
białko_chude (7: pierś kurczaka/indyka, polędwiczka, schab, krewetki, stek, wątróbka);
białko_mielone (2); białko_proszek (2); białko_roślinne (3: tofu, tempeh, seitan);
białko_tłuste (2: udo kurczaka, kiełbasa drobiowa); dodatek_tłuszczowy (4: śmietana 18 %,
oliwki, mleczko kokosowe, śmietanka bez laktozy); jajka (2); kasza_ryż (9); kiszonki (2);
makaron (4); mleko (4); mąka (4); nabiał_chudy (15, w tym 8 bez laktozy);
nabiał_tłusty (1: jogurt grecki 10 %); nasiona (4); orzechy (3); orzechy_pasty (2: masło
orzechowe, tahini); owoce (8); owoce_jagodowe (4); pasta_smarowanie (2: hummus, serek
śmietankowy light); pieczywo (7); pomidory_przetwory (3); przyprawa (16); płatki (5);
płyn (2: buliony); ryba_chuda (4, w tym tuńczyk z puszki); ryba_tłusta (5, w tym łosoś
wędzony, sardynki); ser (7); skrobiowe (2: ziemniak, batat); sos (5); strączki (5);
słodycze (1: gorzka czekolada); słodzik (5: miód, dżem, daktyle, rodzynki, syrop klonowy);
tłuszcz (4: masło, oliwa, rzepakowy, skwarki); tłuszcz_roślinny (1: awokado);
warzywa_aromat (2: cebula, por); warzywa_gotowane (12); warzywa_liściaste (3);
warzywa_surowe (6); wędlina (2).

#### 4. Decyzje projektowe (propose-only → właściciel zatwierdził kierunek tą wiadomością)

1. **Dwa poziomy zamienników.** Poziom 1 = ta sama `substitution_group` (jak dziś).
   Poziom 2 = **grupa pokrewna** z nowego pliku danych
   `backend/dzik_os/dieta/dane/grupy_pokrewne.json` (symetryczne pary + krótki powód
   po polsku + `source`). Kandydaci poziomu 1 zawsze przed poziomem 2; w UI etykieta
   „z tej samej grupy” / „grupa pokrewna: kasza_ryż”.
2. **„Funkcja w posiłku” = trzy sprawdzenia, nie jedno:**
   * **rola makro** — dla składnika z rolą P/C/F kandydat musi mieć **dominujące
     makro zgodne z rolą** (udział kcal z tego makro największy; dla P wystarczy
     `protein_100 ≥ 15 g`, bo nabiał chudy ma dużo wody); poziom 2 bez wyjątków,
     poziom 1 jak dotąd (`per > 0`);
   * **metoda przygotowania** — `cooking_tags` muszą się przecinać; `*` i **pusty**
     zestaw tagów traktuj jako wildcard (dziś pusty = odpad); na poziomie 2 wildcard
     kandydata **nie** wystarcza — musi przeciąć tagi składnika, chyba że składnik
     sam ma `*`;
   * **klasa i limity porcji** — gramatura kandydata mieści się w
     `min_factor..max_factor` składnika (po limitach v1.1: mięso/ryby ≤ 300 g,
     jajka ≤ 4) i jest zaokrąglona `round_step`; poza zakresem = odpad z powodem.
3. **Bramka posiłku „nie pogarsza” zamiast absolutnej.** Kandydat przechodzi, gdy
   posiłek po wymianie **mieści się w `TOL_MEAL`** ALBO gdy **żadne odchylenie
   (kcal, P, F, C) nie jest większe co do modułu niż przed wymianą** (a więc
   w posiłku już poza tolerancją wymiana neutralna lub poprawiająca jest
   dozwolona). `TOL_MEAL`/`TOL_DAY` **bez zmian** (test stałych). Odpowiedź niesie
   `meal_delta` (kcal/P/F/C po − przed) do pokazania klientowi.
4. **Rola `NONE` dostaje przycisk.** Składniki `NONE` (warzywa, przyprawy,
   kiszonki, dodatki) są wymienialne **na poziomie 1** (ta sama grupa), gramatura
   **1:1 wagowo** (funkcja = objętość/smak, nie makro), a potem ta sama bramka
   posiłku. `swappable` w seedzie: `True` dla P/C/F i dla `NONE`, gdy grupa ma ≥ 2
   produkty; `STAŁY` nadal bez przycisku (warunek frontu zostaje). **Istniejące
   przypisania mają `swappable` w migawce** — nie przepisuj migawek; policz
   `swappable` efektywnie przy odczycie (`dieta_out`) tą samą regułą, żeby
   przypisania sprzed rundy też dostały przycisk.
5. **Puste listy mają powód.** GET zwraca `reason` ∈ {`SINGLETON` (grupa bez innych
   produktów i bez grup pokrewnych), `EXCLUDED` (wszystko odpadło przez alergeny/
   wykluczenia/„nie lubię”), `FUNCTION` (nic nie pasuje metodą/rolą), `TOLERANCE`
   (kandydaci istnieją, ale każdy pogarsza posiłek), `PORTION`} + liczby odrzuconych
   per powód. Front pokazuje właściwy komunikat po polsku (np. „Zamienniki są, ale
   każdy zepsułby makra tego posiłku — poproś trenera o korektę posiłku”) zamiast
   jednego „Brak bezpiecznego zamiennika”. To jest zasada „nic nie udaje, że działa”.
6. **Ranking:** poziom (1 przed 2) → suma |Δ| posiłku po wymianie → odległość
   makro produktu (jak dziś). Limit `n` bez zmian; front pokazuje maks. 5.
7. **Bezpieczeństwo bez zmian:** POST nadal liczy kandydatów serwerowo i odrzuca
   `to_product_id` spoza listy (422); blokady trenera (`swaps_enabled`,
   `swaps_locked`, ARCHIVED) bez zmian; wykluczenia alergenów **przed** grupami
   pokrewnymi (poziom 2 nie może przemycić alergenu).
8. **Dane powiązań są propozycją do przeglądu trenera/dietetyka.** Plik
   `grupy_pokrewne.json` ma pole `status: "PROPOZYCJA"` i `reviewed_by: null`;
   panel szablonów pokazuje tabelę powiązań **tylko do odczytu** (edycja = osobna
   runda). Nie wymyślaj powiązań spoza tabeli w §5 bez zapisania powodu.
9. **Silnik przestaje być 1:1 z prototypem** w `swap_candidates` — zapisz to w
   `PROGRESS.md`, docstringu i CHANGELOG; pozostałe funkcje (skalowanie, `check`,
   `fit_*`) bez zmian.
10. **Zero AI.** Dobór kandydatów jest regułowy i deterministyczny (test).

#### 5. Tabela powiązań grup — punkt startowy dla `grupy_pokrewne.json`

Pary symetryczne. Kolumna „funkcja” to powód, który trafia do pliku. Powiązania
oznaczone (?) wymagają decyzji właściciela/trenera — w v1 wpisz je z
`status: "PROPOZYCJA_NIEPEWNA"` i **domyślnie wyłączone** (`enabled: false`).

| Grupa A | Grupa B | Funkcja / powód |
|---|---|---|
| białko_chude | białko_tłuste | to samo danie główne, inne mięso; tolerancja rozstrzygnie tłuszcz |
| białko_chude | białko_mielone | ta sama rola P w obiedzie |
| białko_chude | ryba_chuda | białko obiadowe, obróbka termiczna |
| białko_chude | białko_roślinne | tofu/tempeh/seitan jako białko dania |
| ryba_chuda | ryba_tłusta | ryba za rybę; F rozstrzyga bramka |
| białko_tłuste | ryba_tłusta | białko z tłuszczem |
| białko_mielone | białko_roślinne (?) | tempeh/tofu kruszone |
| strączki | białko_roślinne | białko roślinne w daniu |
| strączki | kasza_ryż | C w obiedzie (soczewica ↔ kasza) |
| kasza_ryż | makaron | dodatek skrobiowy |
| kasza_ryż | skrobiowe | dodatek skrobiowy |
| makaron | skrobiowe | dodatek skrobiowy |
| płatki | kasza_ryż | owsianka ↔ jaglanka; `cooking_tags` rozstrzyga |
| pieczywo | płatki (?) | śniadanie C — funkcja różna (kanapka vs miska) |
| mąka | płatki (?) | placki/naleśniki |
| nabiał_chudy | nabiał_tłusty | jogurt za jogurt |
| nabiał_chudy | białko_proszek | P w koktajlu/misce |
| nabiał_chudy | mleko | nabiał płynny |
| nabiał_chudy | jajka | P śniadaniowe |
| jajka | białko_roślinne | tofucznica |
| jajka | wędlina | P w kanapce |
| wędlina | białko_chude | plaster mięsa ↔ pieczone mięso |
| wędlina | ser | dodatek białkowy do pieczywa |
| ser | nabiał_tłusty | tłusty nabiał |
| ser | pasta_smarowanie | smarowidło/dodatek do pieczywa |
| pasta_smarowanie | orzechy_pasty | smarowidło |
| pasta_smarowanie | nabiał_chudy | serek wiejski jako smarowidło |
| tłuszcz | tłuszcz_roślinny | tłuszcz dodany (oliwa ↔ awokado) |
| tłuszcz | dodatek_tłuszczowy | F w daniu |
| tłuszcz | orzechy_pasty | F do miski/kanapki |
| orzechy | nasiona | F w misce/sałatce |
| orzechy | orzechy_pasty | F |
| orzechy | tłuszcz_roślinny | F |
| słodycze | orzechy | przekąska F/C |
| słodycze | słodzik (?) | słodka przekąska |
| słodzik | owoce | słodzenie (daktyle, rodzynki ↔ owoc) |
| owoce | owoce_jagodowe | owoc za owoc |
| warzywa_gotowane | warzywa_surowe | warzywo za warzywo (`cooking_tags`) |
| warzywa_gotowane | warzywa_liściaste | warzywo |
| warzywa_surowe | warzywa_liściaste | warzywo surowe |
| warzywa_surowe | kiszonki | dodatek surowy/kwaśny |
| warzywa_gotowane | warzywa_aromat | warzywo do duszenia |
| sos | pomidory_przetwory | baza sosu |
| sos | przyprawa | doprawienie |
| mleko | białko_proszek (?) | koktajl |

Bez powiązań (zostają singletonami poziomu 2 → `reason: SINGLETON`): `płyn`,
`kiszonki`↔inne poza warzywami surowymi, `przyprawa`↔inne poza sosem.

#### 5a. Katalog produktów trenera jako źródło zamienników (decyzja właściciela 14.09)

Właściciel: *„mamy dostęp do listy pojedynczych produktów, które można by skorelować
z tymi, co chcemy wymieniać w szablonie”*. Fakty:

* Katalog: `FoodProduct` (`models.py` l. 841–865) — per trener (`coach_id`), wgrywany
  przyciskiem `POST /api/coach/food-products/load-builtin` (`routers/food_catalog.py`
  l. 561) z wbudowanej listy `food_catalog_data.FOOD_ROWS_ALL` (**2058 pozycji**,
  16 kategorii: Mięso i drób 226, Warzywa 226, Nabiał 183, Ryby 154, Owoce 146, Zboża
  i pieczywo 133, Przyprawy i dodatki 124, Przekąski 116, Kasze/ryż/makarony 104,
  Napoje 93, Strączkowe 76, Orzechy 74, Odżywki 66, Tłuszcze 47, Jaja 31, Dania gotowe
  259). Pola: nazwa, kategoria, kcal/P/F/C/błonnik na 100 g, porcja, jednostka
  sztukowa, źródło. **Brak:** `substitution_group`, `cooking_tags`, `allergens`,
  `diet_exclusions` — czyli dokładnie tego, na czym stoi bezpieczeństwo wymian.
* Dlatego **nie robimy złączenia w czasie działania** (silnik nie może brać
  kandydatów z tabeli, która nie zna alergenów i jest edytowalna per trener).
  Korelacja to **jednorazowe, przeglądane przez człowieka wzbogacenie katalogu diet**
  (`DietProduct`), a silnik po tej rundzie nadal działa wyłącznie na `DietProduct`.

**Mechanizm (propose-only, trzy kroki):**

1. **Narzędzie korelacji** `apps/dzik-os/tools/koreluj_katalog.py` — bez bazy, czyta
   `FOOD_ROWS_ALL` i `dieta/dane/produkty.csv`, pisze
   `docs/diet-module/katalog_korelacja_propozycja.csv` z kolumnami:
   `name, category, kcal_100, protein_100, fat_100, carbs_100, fiber_100,
   proposed_group, confidence (WYSOKA|ŚREDNIA|NISKA), method (DUPLIKAT|SŁOWO_KLUCZOWE|
   KATEGORIA), proposed_cooking_tags, proposed_allergens, proposed_diet_exclusions,
   default_scaling, reason, decision (puste → właściciel/trener wpisuje TAK/NIE)`.
   Reguły (deterministyczne, w kodzie z testem):
   * **DUPLIKAT** — znormalizowana nazwa (`normalize_name` z `food_catalog`) pokrywa
     się z istniejącym `name_pl` → pomiń (nie dubluj produktu w innej grupie).
   * **SŁOWO_KLUCZOWE** → ŚREDNIA: np. „mielon” → `białko_mielone`; „szynka|wędlina|
     kiełbasa|polędwica wędzona” → `wędlina`; „udo|skrzydł|karkówka|boczek|kaczka|gęś”
     → `białko_tłuste`; „łosoś|makrela|śledź|sardynk|pstrąg|halibut” → `ryba_tłusta`;
     „ser|mozzarella|feta|parmezan|gouda|camembert” → `ser`; „mleko|napój sojowy|owsiany|
     migdałowy” → `mleko`; „śmietan” → `dodatek_tłuszczowy`; „płatk|musli|granola” →
     `płatki`; „mąk” → `mąka`; „makaron” → `makaron`; „ziemniak|batat” → `skrobiowe`;
     „kiszon” → `kiszonki`; „sałata|szpinak|rukola|jarmuż|roszponka” →
     `warzywa_liściaste`; „cebul|por|czosnek” → `warzywa_aromat`; „pomidor|ogórek|
     papryka|rzodkiew|seler naciowy” → `warzywa_surowe`; „borów|malin|truskaw|jagod|
     porzecz|jeżyn” → `owoce_jagodowe`; „suszon|daktyl|rodzynk|miód|dżem|syrop” →
     `słodzik`; „tofu|tempeh|seitan” → `białko_roślinne`; „hummus” →
     `pasta_smarowanie`; „masło orzechowe|pasta|tahini” → `orzechy_pasty`; „nasion|
     pestk|siemi|chia|słonecznik|sezam” → `nasiona`; „awokado” → `tłuszcz_roślinny`;
     „odżywka białkowa|WPC|WPI|izolat” → `białko_proszek`; „ketchup|musztarda|sos” →
     `sos`; „passata|koncentrat|pomidory z puszki” → `pomidory_przetwory`.
   * **KATEGORIA** → NISKA (domyślna grupa kategorii): Mięso i drób → `białko_chude`;
     Ryby → `ryba_chuda`; Jaja → `jajka`; Nabiał → `nabiał_chudy` (`nabiał_tłusty`, gdy
     tłuszcz ≥ 5 g/100 g); Zboża i pieczywo → `pieczywo`; Kasze/ryż/makarony →
     `kasza_ryż`; Warzywa → `warzywa_gotowane`; Owoce → `owoce`; Strączkowe →
     `strączki`; Orzechy → `orzechy`; Tłuszcze → `tłuszcz`; Przyprawy i dodatki →
     `przyprawa`. **Dania gotowe, Napoje (poza mlekami), Odżywki (poza białkiem),
     Przekąski i słodycze → `decision: NIE` z góry** (nie są zamiennikami składnika
     szablonu; rozstrzyga człowiek, jeśli chce inaczej).
   * `proposed_cooking_tags` = najczęstszy zestaw tagów **grupy docelowej** w
     `produkty.csv` (nie wymyślaj nowych tagów; słownik tagów odczytaj z pliku).
   * `proposed_allergens` / `proposed_diet_exclusions` — słownik **wyłącznie** z
     istniejącego CSV (np. `milk`, `lactose`, `gluten`, `eggs`, `fish`, `nuts`, `soy`,
     `meat`, …; sprawdź dokładne tokeny), heurystyki po nazwie i kategorii; każdy
     wiersz z pustym alergenem w kategorii, gdzie alergen jest typowy (Nabiał, Zboża,
     Ryby, Orzechy, Jaja, Strączkowe/soja), dostaje `confidence: NISKA`.
   * `default_scaling` = jak w grupie docelowej (`LINIOWY`/`DYSKRETNY`/`STAŁY`).
2. **Przegląd człowieka:** właściciel/trener wypełnia `decision` w CSV (TAK/NIE, może
   poprawić grupę i alergeny). To jest dokument do zlecenia zwrotnego — writer **nie
   zatwierdza sam** wierszy NISKA. Wiersze `WYSOKA`/`ŚREDNIA` bez alergenów do
   uzupełnienia można zaproponować jako `TAK` (właściciel potwierdza jednym słowem).
3. **Import zatwierdzonych:** `dieta/dane/produkty_z_katalogu.csv` (te same kolumny
   co `produkty.csv`, `source = "katalog_trenera"`, `source_id` = nazwa wbudowana,
   `source_desc` = wiersz propozycji) ładowany przez `dieta/seed.py` **po** głównym
   CSV, idempotentnie po `name_pl`; osobny plik = brak konfliktu z biblioteką
   i jawne pochodzenie; wpis w `package-data`. Test integralności jak dla głównego
   CSV (unikalność po znormalizowanej nazwie, zakresy, kcal↔makra, grupa istnieje,
   tokeny alergenów ze słownika).

**Bezpieczeństwo:** wiersz bez decyzji TAK nigdy nie trafia do seeda; wiersz z alergenem
„do uzupełnienia” nie może być zaimportowany (test), bo filtr alergenów wymian musi
pozostać kompletny. Pomiar po imporcie: ile z 12 pustych list (po bibliotece) znika
dzięki katalogowi, a ile dzięki grupom pokrewnym — osobno w tabeli CHANGELOG.

**Kolejność w rundzie:** narzędzie i CSV propozycji powstają w etapie 1 (dane), żeby
właściciel mógł przeglądać równolegle z pracą nad silnikiem; import zatwierdzonych
wierszy to ostatni etap przed zamknięciem (albo osobny, malutki PR, jeśli przegląd
potrwa dłużej niż runda — nie blokuj scalenia silnika na przeglądzie CSV).

#### 6. Co dokładnie zbudować

##### Backend
* `dieta/dane/grupy_pokrewne.json` (schemat: `{"version": 1, "status": "PROPOZYCJA",
  "reviewed_by": null, "links": [{"a": "...", "b": "...", "reason": "...", "enabled":
  true, "status": "PROPOZYCJA"}]}`) + `dieta/grupy.py` (ładowanie, walidacja: obie grupy
  istnieją w `produkty.csv`, brak duplikatów, symetria) + wpis w `package-data`
  (**strażnik `tests/test_pakietowanie.py` — lekcja 0.57.1**).
* `silnik.py`: `swap_candidates(meal_result, ing_index, products, exclusions, n,
  related=None, current_dev=None)` wg §4 pkt 1–6, zwracająca `{product, grams, macros,
  tier, meal_delta}` + osobno statystykę odrzuceń `{reason: count}` (druga funkcja
  `swap_candidates_z_powodami` albo tuple — jedna zasada: ta sama ścieżka dla GET
  i POST).
* `serwis.py::kandydaci_wymiany` — przekazuje powiązania i bieżące odchylenie
  posiłku; `dieta_out` — `swappable` efektywne (§4 pkt 4).
* `routers/diet.py` GET `/swaps` → `{candidates: [{…, tier, meal_delta}], blocked,
  reason, rejected: {…}}`; POST bez zmian kontraktu poza tym, że akceptuje kandydata
  z listy (poziom 1 lub 2) i zapisuje `tier` w `DietSwapEvent`/override (`kind:
  "swap"`, pole `tier` w JSON — bez migracji, jeśli override/event trzymają JSON;
  sprawdź).
* `seed.py`: `swappable` wg §4 pkt 4 (idempotentnie — seed po `name_pl`, nie
  przepisuje istniejących migawek).
* **Korelacja katalogu (§5a):** `tools/koreluj_katalog.py` + test reguł
  (`backend/tests/test_koreluj_katalog.py`: duplikat pomijany, słowo kluczowe przed
  kategorią, kategorie NIE z góry, tagi z grupy docelowej, tokeny ze słownika),
  `dieta/dane/produkty_z_katalogu.csv` (tylko wiersze TAK), seed po głównym CSV,
  `package-data`, test integralności.
* **Pomiar jako test-strażnik:** `tests/test_dieta_wymiany_pokrycie.py` — dla
  Standard v1 przy 1600/2000/2600 kcal liczy odsetek składników wymienialnych bez
  kandydata i porównuje z progiem **wpisanym z pomiaru po zmianie + margines**
  (komentarz z liczbą i datą pomiaru; nie „≤ 0”, bo to kłamstwo, i nie 50 %, bo to
  ozdoba). Osobno: żaden kandydat nie pogarsza posiłku (własność z §4 pkt 3),
  poziom 2 nigdy nie przemyca alergenu, wynik deterministyczny.

##### Frontend
* `DietaSzablon.tsx`: przycisk także dla `NONE` (wg `swappable` z serwera); arkusz:
  etykieta poziomu, `meal_delta` po polsku („posiłek: −12 kcal, białko +1 g”), lista
  do 5; komunikat pusty wg `reason` (5 wariantów po polsku); link do wiadomości
  zostaje przy `TOLERANCE`/`SINGLETON`.
* `types.ts`: `DietSwapCandidate` + `tier`, `meal_delta`; odpowiedź GET + `reason`,
  `rejected`.
* Panel trenera (`pages/coach/SzablonyDiet.tsx` albo `DietTemplates.tsx` — sprawdź,
  który jest żywy po bibliotece): karta „Grupy pokrewne (propozycja do przeglądu)”
  tylko do odczytu; historia wymian klienta pokazuje poziom.

##### Testy
* Aktualizacja świadoma: `test_dieta_silnik.py` l. 152 (nowa złota lista z powodem
  w commicie; przypadek „skyr bez laktozy” → **niepusty** po bibliotece, sprawdź, że
  kandydat jest `lactose`-free), `test_dieta_api.py` l. 194 (analogicznie).
* Nowe: poziom 2 działa (płatki owsiane → kasza jaglana / płatki jaglane),
  `NONE` (brokuł → kalafior 1:1), „nie pogarsza” w posiłku poza tolerancją,
  `reason` dla każdego z 5 przypadków, wildcard pustych tagów, POST odrzuca produkt
  spoza listy także na poziomie 2, alergen nie przechodzi poziomem 2, blokady trenera
  bez zmian, `swappable` efektywne dla starej migawki.
* E2E `dieta-szablon.spec.ts`: dołóż scenariusz na składniku, który na `main` nie
  miał kandydata (wybierz z pomiaru, np. „Płatki owsiane” albo warzywo `NONE`) —
  klient widzi etykietę poziomu i deltę posiłku, wymienia, trener widzi poziom
  w historii.

##### Dokumentacja (etap zamknięcia)
`CHANGELOG.md` 0.67.0 (z liczbami: przed/po), `docs/diet-module/PROGRESS.md`
(rozdział „Wymiany v2”: pomiar, odejście od 1:1 z prototypem, pytania otwarte),
`docs/diet-module/instrukcja_szablony_diet.md` (jak działa wymiana, poziomy,
powody), `INSTRUKCJA_KLIENTA.md` (Dieta → wymiana), `INSTRUKCJA_TRENERA.md`
(grupy pokrewne, jak zgłosić poprawkę), `BAZA_PRODUKTOW.md` (dwa nowe pliki danych: powiązania grup i produkty z katalogu, z pochodzeniem),
`RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`, plan sesji.

#### 7. Czego świadomie NIE robimy

* Nie zmieniamy `TOL_MEAL`/`TOL_DAY` ani skalowania (`fit_*`, `enforce_groups`).
* Nie przeliczamy pozostałych składników posiłku po wymianie (re-fit) — to zmienia
  model korekt (jedna korekta = jeden składnik); zapisz jako pytanie na v3.
* Nie dodajemy przycisku wymiany do planu z kreatora/kompozytora (`NutritionPlan`)
  — inny katalog, bez grup; osobna decyzja (pytanie 1).
* Nie edytujemy powiązań w UI — tylko odczyt; nie „włączamy reguły `group`”.
* Nie dotykamy `docs/diet-module/engine.py` (prototyp zostaje historyczny).
* Nie robimy złączenia silnika z `FoodProduct` w czasie działania i nie importujemy
  do katalogu diet ani jednego wiersza bez decyzji TAK człowieka.

#### 8. Weryfikacja przed przekazaniem (z korzenia repozytorium)

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q
python -m pytest tests/ -q                     # Core: 275 zielonych
python apps/dzik-os/tools/spojnosc.py
python apps/dzik-os/tools/mutacje.py
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers
```

Plus: **pomiar przed/po** tym samym skryptem (tabela w CHANGELOG i PROGRESS) i
**uruchomienie** (`ZASADA_URUCHOMIENIA.md`): przez serwer E2E jako klient B z
przypisaną dietą kliknij ↔ wymień na składniku, który na `main` dawał pustą listę,
zobacz etykietę poziomu i deltę, wymień, zrób zrzut; potem jako trener obejrzyj
historię. W raporcie napisz, CO KLIKNĄŁEŚ I CO ZOBACZYŁEŚ. Przegląd: 3 recenzentów
wsadowo (bezpieczeństwo/alergeny/wykluczenia, poprawność silnika i determinizm,
testy/UX/treść), P0/P1 przed przekazaniem, P2 do `PROGRESS.md`. Bezpiecznik: 3× plan.

#### 9. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)

1. ~~Szablon czy kreator?~~ **Rozstrzygnięte 14.09:** klient na diecie z szablonu;
   kreator ukrywamy (zlecenie 3); katalog produktów zostaje jako źródło zamienników
   (§5a). Pytanie zastępcze: kto przegląda CSV propozycji — właściciel czy trener
   Łukasz? *Domyślnie: właściciel wstępnie, trener potwierdza alergeny.*
2. Powiązania oznaczone (?) w §5 — włączyć od razu czy zostawić wyłączone do
   przeglądu trenera? *Domyślnie: wyłączone.*
3. Czy wymiana w posiłku już poza tolerancją ma być dozwolona, gdy **nie pogarsza**
   (rekomendacja), czy tylko gdy **poprawia**? *Domyślnie: nie pogarsza.*
4. Warzywa `NONE` 1:1 wagowo — zgoda? (alternatywa: izokalorycznie, ale 100 g ogórka
   ↔ 25 g kukurydzy nie jest wymianą, której klient oczekuje). *Domyślnie: 1:1.*

### Źródło: `plan-sesji_wymiany-produktow.md`



**Warunek startu:** `agent/biblioteka-diet` scalona do `main` (⟨PR #, sha⟩). Bez tego STOP.
**Gałąź:** `agent/wymiany-produktow` (od `main` = ⟨sha⟩, po ⟨wersja⟩). **Rola:** aktywny
piszący — polecenie właściciela z 14.09.2026 („przycisk wymiany produktu w zakładce Dieta
nie działa; trzeba powiązać pokrewne grupy towarowe, by makro i funkcja w posiłku się
zgadzały”), plik `PROMPT_writer_wymiany-produktow.md` (diagnoza z pomiarem, rozpoznanie,
decyzje, tabela powiązań).
**Rezerwacje (KOORDYNACJA §0):** wersja ⟨wg kolejności scalania, `docs/zlecenia/README.md`⟩; migracja **brak**
(plik danych + logika; jeśli okaże się potrzebna kolumna — kolejny wolny numer, wpisany tu
i w `STAN_PRZEKAZANIA.md` §2). Pliki współdzielone: `dieta/silnik.py`, `dieta/serwis.py`,
`dieta/seed.py`, `routers/diet.py`, `dieta/dane/` (nowy `grupy_pokrewne.json`),
`pyproject.toml`/`package-data`, `types.ts` (typy diety), `DietaSzablon.tsx`, panel szablonów
trenera, `CHANGELOG.md`.

#### Co robimy

1. **Pomiar przed** (skrypt w `tools/` albo test-strażnik) — odsetek składników bez kandydata
   przy 1600/2000/2600 kcal na `main` po bibliotece (oczekiwane ~11 % przy 2000).
2. **Dane:** `grupy_pokrewne.json` z tabelą z promptu (§5), walidowany, w `package-data`;
   **korelacja katalogu trenera** (§5a promptu): `tools/koreluj_katalog.py` → CSV propozycji
   do przeglądu właściciela; zatwierdzone wiersze → `produkty_z_katalogu.csv` w seedzie.
3. **Silnik:** `swap_candidates` v2 — poziom 1 (ta sama grupa) + poziom 2 (grupa pokrewna);
   funkcja w posiłku = rola makro dominująca + `cooking_tags` (pusty = wildcard) + limity
   porcji; bramka posiłku „w tolerancji ALBO nie pogarsza”; `tier`, `meal_delta`, statystyka
   odrzuceń z powodami.
4. **Rola NONE:** przycisk i wymiana 1:1 wagowo w tej samej grupie; `swappable` efektywne
   przy odczycie (stare migawki bez przepisywania).
5. **API/UI:** GET `/swaps` z `reason`/`rejected`/`tier`/`meal_delta`; arkusz klienta
   z etykietą poziomu, deltą i 5 komunikatami pustej listy; panel trenera — tabela powiązań
   tylko do odczytu; historia wymian z poziomem.
6. **Pomiar po** + test-strażnik pokrycia z progiem wpisanym z pomiaru.

#### Decyzje projektowe (właściciel 14.09 + wykonawcze)

* `TOL_MEAL`/`TOL_DAY` bez zmian (test stałych). Bramka „nie pogarsza” działa tylko
  na ścieżce wymiany.
* Alergeny/wykluczenia/„nie lubię” filtrowane **przed** poziomem 2 — poziom 2 nie może
  przemycić alergenu (test).
* Powiązania to **propozycja do przeglądu trenera/dietetyka** (`status`, `reviewed_by`);
  pary (?) domyślnie `enabled: false`.
* Silnik przestaje być 1:1 z prototypem w `swap_candidates` — jawnie w docstringu,
  `PROGRESS.md`, CHANGELOG.
* POST nadal liczy kandydatów serwerowo; blokady trenera bez zmian.
* Zero AI; wynik deterministyczny (test).
* Plan z kreatora (`NutritionPlan`) poza zakresem (kreator ukrywa zlecenie 3); katalog
  `FoodProduct` **nie** jest źródłem kandydatów w czasie działania — tylko przez
  przeglądany import do `DietProduct`.

#### Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Czytam (z hipotezą) | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 rozpoznanie + pomiar przed | linie z promptu (`silnik.py` 361–396, `serwis.py` 252–270, `routers/diet.py` 325–423, `seed.py` ~234, `DietaSzablon.tsx` 37–108, testy l. 152/194/231), stan po bibliotece | `docs/diet-module/wymiany_v2_rozpoznanie.md` z tabelą pomiaru + ten plan | skrypt pomiaru uruchomiony, liczby w pliku | dziesiątki tys. |
| 1 dane | `produkty.csv` (grupy, słowniki tagów/alergenów), `subst_maps.json`, `food_catalog_data.FOOD_ROWS_ALL` | `grupy_pokrewne.json`, `dieta/grupy.py`, `tools/koreluj_katalog.py` + `docs/diet-module/katalog_korelacja_propozycja.csv` (do przeglądu właściciela), wpis `package-data` | `test_pakietowanie`, test walidacji pliku (grupy istnieją, symetria, brak duplikatów), `test_koreluj_katalog.py` | setki tys. |
| 2 silnik | `silnik.py`, `check`, limity v1.1 | `swap_candidates` v2 + statystyka odrzuceń | `test_dieta_silnik.py` (aktualizacja złotej listy z powodem; nowe przypadki), determinizm | setki tys. |
| 3 serwis + API + seed | `serwis.py`, `routers/diet.py`, `seed.py`, `dieta_out` | `reason`/`rejected`/`tier`/`meal_delta`, `swappable` efektywne, `tier` w historii | `test_dieta_api.py`, `test_dieta_poprawki.py`, macierz dostępu (bez nowych tras) | setki tys. |
| 4 UI | `DietaSzablon.tsx`, `types.ts`, panel szablonów, historia wymian trenera | arkusz v2, komunikaty, tabela powiązań RO, E2E na składniku pustym na `main` | `tsc`, build (budżet), `test:helpers`, E2E `dieta-szablon.spec.ts`, obejrzenie przez serwer E2E | setki tys. (największy koszt) |
| 5a import zatwierdzonych | CSV z decyzjami właściciela | `dieta/dane/produkty_z_katalogu.csv` (tylko TAK), seed po głównym CSV, test integralności | pytest; jeśli przegląd nie zdąży — osobny mały PR po scaleniu | dziesiątki tys. |
| 5 pomiar po + strażnik | — | `tests/test_dieta_wymiany_pokrycie.py` (próg z pomiaru + margines, z datą) | pytest; tabela przed/po | dziesiątki tys. |
| 6 zamknięcie | — | CHANGELOG 0.67.0, PROGRESS.md, instrukcja szablonów, INSTRUKCJE, BAZA_PRODUKTOW, RELEASE_STATUS, STAN_PRZEKAZANIA | pełny pytest, ruff z korzenia, spójność, mutacje, CI | dziesiątki tys. |

**Największy koszt:** etap 2 (silnik) i 4 (UI). Taniej bez utraty informacji: jedna
ścieżka liczenia kandydatów dla GET i POST (żadnej drugiej implementacji), komunikaty pustej
listy jako słownik `reason → tekst` w jednym miejscu, tabela powiązań RO jako zwykła tabela
z JSON-a (bez formularza). Bezpiecznik: 3× plan. Przegląd: 3 recenzentów wsadowo
(alergeny/wykluczenia/bezpieczeństwo, poprawność silnika i determinizm, testy/UX/treść).

#### Czego nie dotykam

`TOL_MEAL`/`TOL_DAY`, `fit_*`, `enforce_groups`, `docs/diet-module/engine.py`, katalog
kreatora (`FoodProduct`, `food_catalog*`), `NutritionPlan`/`Nutrition.tsx`, migawki
istniejących przypisań (żadnego przepisywania danych), Core Human OS.

#### Czego świadomie nie robię

Re-fit pozostałych składników po wymianie (v3), edycja powiązań w UI, przycisk wymiany
w planie z kreatora, zmiana tolerancji.

#### Odstępstwa od planu

⟨uzupełnia sesja pisząca⟩

#### Weryfikacja wykonana

⟨uzupełnia sesja pisząca: pomiar przed/po (liczby), co kliknięto i co zobaczono⟩

#### Plan kontra rzeczywistość (zasady v2 §5)

⟨uzupełnia sesja pisząca⟩


---

## 7. Zlecenie 3 — Domknięcie PR #67: strona publiczna czerwono-biała

### Źródło: `PROMPT_writer_landing-czerwony-domkniecie.md`



---

Przeczytaj: `/AGENTS.md`, `/CLAUDE.md`, `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
`apps/dzik-os/docs/STAN_PRZEKAZANIA.md`, `apps/dzik-os/docs/KOORDYNACJA.md`,
`apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`, `apps/dzik-os/docs/plan-sesji/landing-czerwony.md`.

**Rola:** aktywny piszący, kontynuacja **istniejącej** gałęzi `agent/landing-czerwony`
i PR #67 (nie nowa gałąź). Jako jedyny piszący możesz teraz dotknąć plików
integracyjnych (KOORDYNACJA §0) — wpisy zaproponowane w opisie PR wchodzą do repo.
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Bez force-pusha; commity po polsku, bez nazw
modeli AI. Nie scalasz PR-a.

#### 0. Stan na 14.09 (zmierzone, nie oszacowane)

| Co | Stan |
|---|---|
| PR #67 | otwarty, gotowy do przeglądu, CI 8/8 zielone na `dfb35e9`, 0 recenzji |
| Baza | `cbfa893` (main 0.64.0). **`main` poszedł dalej:** `860035d` = 0.66.0 (monitoring, PR #61), migracja 36 |
| Próbne scalenie `origin/main` → gałąź (katalog roboczy poza repo) | **jeden konflikt: `frontend/package.json` (0.65.0 vs 0.66.0)**; `styles.css` scala się automatycznie, bez markerów; style Postępów z `main` obecne |
| Po scaleniu (wersja tymczasowo 0.66.0) | `tsc` czysto; `npm run build` OK, **92,1 kB gzip / budżet 120 kB**; precache SW zawiera `boar-mark-red.png` i `boar-hero-red.png`; E2E `strona-publiczna.spec.ts` **4/4** (projekt `telefon`, serwer E2E z seedem) |
| Zrzuty 1440 / 1024 / 768 / 390 (pełna strona, po przewinięciu) | 1440 i 390: bez przewijania poziomego, 1 `h1`, wszystkie `img` z `alt`. **1024: `scrollWidth` 1084 (+60 px)**. **768: `scrollWidth` 772 (+4 px)**. Obrazy `loading="lazy"` ładują się poprawnie (puste pola w pierwszym zrzucie były artefaktem zrzutu bez przewinięcia — nie błędem) |

#### 1. Krok 1 — dociągnij `main` i nadaj wersję

```bash
git fetch origin && git merge origin/main      # konflikt tylko w frontend/package.json
```
Wersja **wg kolejności scalania z `docs/zlecenia/README.md`** (kontrola `changelog`
wymaga wersji rosnących w kolejności scalania): stan 14.09 wieczór — `main` = **0.69.0**
(#68 „ukryj kreator” 0.67.0 i #69 „wymiany” 0.69.0 scalone), **0.68.0 zarezerwowane
w CHANGELOG dla „dni treningowych”** (jeszcze nie rozpoczęte). Ten PR bierze więc
**0.70.0** (a dni treningowe przesuwają się na 0.71.0 — odnotuj w `STAN_PRZEKAZANIA.md`
§2), chyba że właściciel zdecyduje inaczej. **Wersja żyje w sześciu
miejscach i poprzednie rundy podnosiły wszystkie naraz** (0.66.0 jest dziś w każdym):
`frontend/package.json`, `backend/pyproject.toml`, `backend/dzik_os/__init__.py`
(`__version__`), `docs/CHANGELOG.md` (nowy nagłówek `## X.Y.Z — data`), `README.md`
aplikacji i `docs/RELEASE_STATUS.md` (kontrola „wersje dokumentów” w `spojnosc.py`
wymaga, żeby oba wspominały bieżącą wersję z CHANGELOG-a). PR dziś podnosi tylko
`package.json` — uzupełnij pozostałe pięć w jednym commicie „Wersja X.Y.Z”.

#### 2. Krok 2 — poprawki z pomiaru (P1, wykonać)

| # | Objaw (zmierzony) | Przyczyna (`styles.css`, blok `.landing--czerwony`) | Poprawka |
|---|---|---|---|
| P1-a | **900–1150 px: strona przewija się poziomo** (zmierzone: 900 px → `scrollWidth` 1024, panel hero ściśnięty do **235 px**; 1024 px → 1086; 1100 px → 1124) | dwie przyczyny naraz: (1) `.landing-hero__grid { grid-template-columns: 1fr 1fr }` — `1fr` to `minmax(auto,1fr)`, a `.landing-proof__item { white-space: nowrap }` wymusza 581 px na kolumnę tekstu, więc panel się kurczy; (2) `.landing-panel` (l. ~715) ma `overflow: hidden` **tylko** w `@media (max-width: 699px)` (l. ~863), a `.landing-panel__ring` 520 px / `.landing-panel__blob` 440 px są centrowane i wystają | (1) `grid-template-columns: minmax(0,1fr) minmax(0,1fr)` + `.landing-proof { flex-wrap: wrap }` (albo bez `nowrap`); (2) dekoracje (plama, pierścień, raster, „LUBELSKI DZIK”) do wewnętrznej warstwy `.landing-panel__scene { position:absolute; inset:0; overflow:hidden; border-radius:inherit }`, karty-powiadomienia poza nią (mają wystawać) |
| P1-b | **700–899 px: +4 px przewijania**; odznaka „IFBB PRO / RAPTOR GYM” ok. 70 px na prawo od zdjęcia, nad pustym tłem; czerwony kwadrat `foto-bg` przy samej krawędzi ekranu | `.landing-about__badge { position:absolute; right:-22px; bottom:-22px }` (l. ~767) i `.landing-about__foto-bg { left:-18px }` — w bloku `@media (max-width: 899px)` siatka „O trenerze” spada do jednej kolumny, ale `.landing-about__foto-wrap` dostaje pełną szerokość bez marginesu (reguła `margin: 18px 22px 22px 18px` jest dopiero w ≤699) | w bloku 899: `.landing-about__foto-wrap { max-width: 480px; margin: 18px 22px 22px 18px }` (odznaka wraca na róg zdjęcia, kwadrat odsuwa się od krawędzi) |
| P1-c | **Cele dotyku < 24 px** w nawigacji kotwic (Oferta / Jak zaczynamy / Aplikacja / Trener / FAQ) na 1440 i 1024 — WCAG 2.2 **2.5.8** (AA) | `.landing-top__nav a` (l. ~697): `font-size: 15px`, brak paddingu → wysokość ~18 px | `padding: 8px 6px; display: inline-block` (wysokość ≥ 24 px); link „informacja o przetwarzaniu danych” w stopce to link w zdaniu — wyjątek 2.5.8, zostaw |
| P2 | `.wm` (znak wodny 220 px) i `.wm--kontakt` wystają z sekcji — obcięte przez `overflow:hidden` sekcji, **nie** powodują przewijania | — | bez zmian; upewnij się, że oba rodzice mają `overflow:hidden` po Twojej zmianie |

Po poprawkach dołóż do `strona-publiczna.spec.ts` asercję `scrollWidth <= clientWidth`
także dla viewportu **1024×800 i 768×1024** (jeden test z pętlą po trzech
szerokościach — dziś jest tylko 390).

##### 2b. Przegląd diffu (3 obszary, wykonany 14.09 na scalonym drzewie — do wykonania w tym PR)

**Bez P0.** Brak markerów konfliktu; blok `/prywatnosc` przywrócony dosłownie; style
Postępów z `main` obecne (26/26 selektorów); nowe reguły scope'owane do
`.landing--czerwony`; formularz, honeypot (`aria-hidden`, `tabIndex=-1`, −9999 px), notka
RODO (w `<form>`), kotwice `oferta/jak-to-dziala/aplikacja/o-trenerze/faq/kontakt`,
`role="status"/"alert"`, linki social i stopka — bez zmian względem `main`.

**P1-3 (semantyka nagłówków).** Stare `<h2>Jak zaczynamy</h2>` i `<h2>O trenerze</h2>` są
teraz `<div class="eyebrow">` (`Landing.tsx` ~l. 262 i 314), a `h2` to „Trzy kroki do
pierwszego planu” i „Łukasz Drygiel — Lubelski Dzik”. E2E przechodzi (`/Łukasz Drygiel/`),
ale każdy, kto szuka nagłówka „O trenerze”, go nie znajdzie. Do wyboru: etykieta jako
`<p class="eyebrow">` + `h2` z dotychczasową treścią, albo świadoma zmiana wpisana do
CHANGELOG. Do tego `Naglowek` (`Landing.tsx` l. 83–88) ma nieużywany prop `id` — usuń.

**P2 do wykonania w tym PR (tanie):**
* `scroll-margin-top`: brak w całym `styles.css`; przy 390 px po kliknięciu CTA etykieta
  `#kontakt` ląduje pod paskiem 76 px (y = 54). Dodaj `.landing--czerwony section[id]
  { scroll-margin-top: 76px }`.
* Pas 700–899: `.landing-steps` zostaje w 3 kolumnach po 207 px (h3 „Trenujemy
  i korygujemy” łamie się na 88 px) — w bloku 899 daj 1 kolumnę; panel hero
  `height: 560px` + `order: -1` spycha `h1` na y = 804 przy 768 px (pierwszy ekran to
  sama dekoracja) — rozważ `height: 360px` w tym pasie.
* Obraz LCP na telefonie/tablecie: `boar-hero-red.png` 102 kB, 560×721, bez
  `width/height/fetchpriority` (`Landing.tsx` ~l. 213) — dodaj `width={560} height={721}
  fetchpriority="high" decoding="async"`; WebP dałby ~30 kB (opcjonalnie).
* Treść: „−12 kg w 20 tygodni” (`Landing.tsx` ~l. 205 i 336) zgubiło „nawet” z opisu
  trenera — czyta się jak gwarancja; przywróć „nawet −12 kg”. Karty w hero („Przysiad
  110 kg — nowy rekord własny”, „Raport z tygodnia 8”, „Odpowiedź trenera: dziś 09:40”)
  są `aria-hidden` i oznaczone PERSONALIZACJA, ale widzący gość bierze je za prawdziwe —
  **właściciel potwierdza treść kart** (galeria mówi „dane demonstracyjne”, karty nie).
* Trzy dowody (IFBB PRO / 30 000+ / −12 kg) są dwa razy (`landing-proof` ~l. 200
  i `landing-stats` ~l. 333) — czytnik ekranu słyszy oba; jeśli celowo, test
  `getByText("30 000+")` ma mieć `toHaveCount(2)` zamiast `.first()`.
* `.landing-gallery` (przewijany poziomo) jest przystankiem fokusu bez nazwy — dodaj
  `role="region" aria-label="Ekrany aplikacji"` (błąd sprzed PR, tania poprawka).
* Nity CSS: zdublowane `margin: 0` w `.landing-top`; `.landing-form input:focus-visible`
  dubluje regułę globalną; komentarz przy bloku `/prywatnosc` nadal mówi „0.65.0”.
* Precache SW (`inject-precache.mjs` l. 50–81) bierze cały `dist/`, więc oba nowe PNG
  (+110 kB) trafiają do każdej instalacji PWA, choć używa ich tylko wylogowane `/`.
  Świadomy kompromis (offline `/` z grafiką) — zapisz w CHANGELOG; nic nie kasuj
  (`boar-mark.png` i `logo-full.png` nadal używane przez aplikację i `/login`).

**Zmiany treści względem `main` (do CHANGELOG, żeby nic nie zniknęło po cichu):** usunięty
`<img src="/icons/logo-full.png" alt="Dzik OS">` z hero (plik zostaje — `Login.tsx`);
akapit `landing-gallery__intro` zastąpiony `sec-head__desc` z dodanym zdaniem „Ciemny motyw
aplikacji zostaje: na siłowni ma być czytelny, nie jasny.” (**właściciel: to zdanie
przesądza o motywie aplikacji — zgodne z decyzją? patrz §8**); numery kroków „1/2/3” → „01/02/03”;
klasy `landing-top__login` i `landing-card` już tylko w `Privacy.tsx`.

**Luki testowe (`strona-publiczna.spec.ts`) — dołóż w tym PR:** `scrollWidth ≤ clientWidth`
przy 768×1024 i 1024×768 (dziś oba padają: 772 i 1086 — złapałyby P1-a i P1-b);
nawigacja `aria-label="Sekcje strony"` widoczna ≥ 900 i ukryta ≤ 899; po kliknięciu kotwicy
nagłówek sekcji poniżej paska; panel hero `aria-hidden`; honeypot niefokusowalny; migawka
konspektu `h1,h2,h3`; ścieżka błędu formularza (`role="alert"`).

#### 3. Krok 3 — kontrast: decyzja właściciela z policzonymi wartościami

Policzone wg WCAG (luminancja względna), pary z Twojej specyfikacji i alternatywy:

| Miejsce | Dziś | Współczynnik | Wymaganie | Propozycja (domyślna) | Współczynnik po |
|---|---|---|---|---|---|
| Obrys `.btn--ghost` i pól formularza na bieli | `--l-border-strong` #E0CFCF | **1,50** | 1.4.11 ≥ 3:1 dla granicy komponentu | nowy token `--l-border-ui: #B3878A` **tylko** dla obrysu przycisków ghost i pól (karty i separatory zostają na #ECE4E4/#E0CFCF) | **3,11** |
| Numer „03” na `.tile-coral` (gradient #B3341E → #FF6B5A → #FFC7BE), biały tekst | biały | 6,13 na ciemnym początku, **2,80** w środku, **1,48** na jasnym końcu | tekst duży ≥ 3:1 (AA) | numery na kaflu koralowym w `--l-graphite-deep` #0B0F14 (spec sama paruje koral z czernią: 6,87) | **3,14 / 6,87 / 12,96** na całym gradiencie |
| Alternatywa dla „03”, jeśli biały ma zostać | — | — | — | jasny koniec gradientu #FFC7BE → #E8503F | biały 3,72 na końcu (AA duży tekst), ale kafel traci „ciepło” ze spec |

Pozostałe pary ze spec są w normie: link/biel 6,95; link/pasmo różowe 6,09;
`--l-ink-2`/biel 6,13; `--l-ink-2`/pasmo różowe 5,38; biel/czerwień 4,75;
`--l-dark-text-dim`/#0B0F14 10,12; koral eyebrow/grafit 5,24.

**Właściciel:** zaznacz A (domyślne: `--l-border-ui` #B3878A + numery grafitowe na
koralu) albo B (zostaw kolory ze spec i wpisz świadome odstępstwo w
`docs/DOSTEPNOSC.md`). Bez odpowiedzi → A.

#### 4. Krok 4 — treść: potwierdzenia właściciela (z opisu PR)

1. „Wolisz bezpośrednio? Zadzwoń… albo napisz…” → dwa wiersze kontaktu z tymi samymi
   linkami. *Domyślnie: zostaje jak w PR.*
2. Notka o zdrowiu przeniesiona z formularza do lewej kolumny, widoczna także po
   wysłaniu. *Domyślnie: zostaje.*
3. „Odpowiadam na każde zgłoszenie — zwykle tego samego dnia.” — **niepotwierdzone**;
   w PR jest „Odpowiadam na każde zgłoszenie.” *Domyślnie: bez „zwykle tego samego
   dnia”, dopóki trener nie potwierdzi.*
4. „O trenerze” jako etykieta, nazwisko jako `h2`. *Domyślnie: zostaje.*

#### 5. Krok 5 — znak marki (adnotacja na kanwie, nierozstrzygnięta w PR)

Kanwa „Dzik OS — wariant jasny” ma adnotację: *„Dzik w logo przebarwiony z limonki na
czerwień (#E11D2E). To zmiana znaku marki — do potwierdzenia z właścicielem przed
wdrożeniem.”* PR #67 używa czerwonego dzika **tylko na stronie publicznej**; ikony
PWA, `logo-full.png`, `og.png`, aplikacja po zalogowaniu — nadal limonka. Do czasu
decyzji strona i aplikacja mają **dwa kolory znaku**.

**Właściciel:** (a) czerwień to nowy znak — wtedy etap 2 (niżej) po scaleniu #67;
(b) znak zostaje limonkowy — wtedy na stronie publicznej dzik wraca do limonki
(`boar-mark.png`/`boar-hero` w wersji limonkowej na czerwonym panelu — sprawdź kontrast
i podeślij zrzut). *Domyślnie: (a), bo właściciel zatwierdził kanwę.*

#### 6. Krok 6 — integracja i zamknięcie (teraz wolno)

* `CHANGELOG.md`: wpis z opisu PR z właściwym numerem + jedno zdanie o poprawkach
  z kroku 2–3 (liczby: 1024 px +60 px → 0; 768 px +4 px → 0; cele dotyku ≥ 24 px;
  kontrast obrysu 1,50 → 3,11, numeru na koralu min. 1,48 → 3,14).
* `RELEASE_STATUS.md` (wersja + jedna linia o stronie publicznej),
  `STAN_PRZEKAZANIA.md` §1 (akapit z opisu PR) i §2 (wiersz gałęzi), `DOSTEPNOSC.md`
  (nowe pary kontrastu i cele dotyku strony publicznej), plan sesji
  (`Odstępstwa`, `Weryfikacja wykonana` z tabelą 1440/1024/768/390).
* `KOORDYNACJA.md` bez zmian (dokument zasad).
* Zrzuty: PR nie przyjmie plików przez API — zrób 4 zrzuty (1440/1024/768/390) po
  poprawkach, zapisz jako JPEG ≤ 150 kB każdy w `docs/zrzuty/landing-czerwony/`
  (nowy katalog, tylko te 4 pliki) i podlinkuj w opisie PR. To jest dowód uruchomienia
  (`ZASADA_URUCHOMIENIA.md`), więc warto go mieć w repo, nie tylko w sesji.

#### 7. Weryfikacja przed przekazaniem (z korzenia repozytorium)

```bash
python -m ruff check apps/dzik-os/backend apps/dzik-os/tools
python -m pytest apps/dzik-os/backend/tests -q      # backend bez zmian, ale wersja/health
python -m pytest tests/ -q                           # Core 275
python apps/dzik-os/tools/spojnosc.py
cd apps/dzik-os/frontend && npx tsc --noEmit && npm run build && npm run test:helpers \
  && npx playwright test e2e/strona-publiczna.spec.ts
```
Plus obejrzenie po poprawkach na 1024 i 768 (właśnie te dwie szerokości nie były
oglądane przed PR). W raporcie: co kliknięto i co zobaczono; `scrollWidth` na
czterech szerokościach jako liczby.

#### 8. Etap 2 — osobne zlecenie po decyzji z kroku 5 (NIE w tym PR)

* **Znak w czerwieni wszędzie:** `og.png` (karta linku), ikony PWA
  (`public/icons/*`, `manifest.webmanifest`, `theme_color`), `logo-full.png`, ekran
  logowania, `<meta name="theme-color">` dla trybu jasnego (PR #67 świadomie pominął).
  Materiały: kanwa ma `boar-red.png` (121 kB) i `boar-mark-red.png`.
* **Motyw aplikacji po zalogowaniu — DECYZJA WŁAŚCICIELA 14.09 (trzecia tura):**
  użytkownik wybiera między kompletnym motywem czarno-zielonym a nowym czerwono-białym;
  nowy musi być kompletny. Osobne zlecenie `PROMPT_writer_motyw-czerwony.md` (po
  scaleniu #67). Podgląd na prawdziwych ekranach już istnieje — tokeny działają.
  **Do wykonania w tym PR (#67):** zdanie „Ciemny motyw aplikacji zostaje: na siłowni ma
  być czytelny, nie jasny.” w `sec-head__desc` sekcji Aplikacja zamień na „Motyw
  wybierasz sam: ciemny na siłownię albo jasny czerwono-biały.” (zrzuty galerii
  zostają ciemne do czasu jasnego kompletu). Rekomendacja: najpierw zlecenie projektowe (kanwa), potem prompt.


---

## 8. Zlecenie 4 — Motyw czerwono-biały jako drugi, kompletny motyw aplikacji

### Źródło: `PROMPT_writer_motyw-czerwony.md`



---

Przeczytaj: `/AGENTS.md`, `/CLAUDE.md`, `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
`apps/dzik-os/docs/STAN_PRZEKAZANIA.md`, `apps/dzik-os/docs/KOORDYNACJA.md`,
`apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`, `apps/dzik-os/docs/DOSTEPNOSC.md`
(§ „Kontrast (ciemny motyw marki)”), `apps/dzik-os/docs/zlecenia/README.md`.

**Rola:** aktywny piszący. Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Core nietykalny.
**Gałąź:** `agent/motyw-czerwony` od aktualnego `main`. Pierwszy commit wyłącznie
`docs/plan-sesji/motyw-czerwony.md`; draft PR `[WRITER] Motyw czerwono-biały`; dopiero
potem kod. **Warunek startu:** PR #67 (strona publiczna) scalony — ten prompt zakłada, że
`styles.css` ma już blok `.landing--czerwony` i grafiki `boar-*-red.png`.
**Rezerwacje:** wersja wg kolejności scalania z `README.md` tego katalogu; migracja
**kolejna wolna** (37 = dni treningowe; ten motyw potrzebuje jednej addytywnej kolumny —
patrz §4.3; jeśli właściciel wybierze zapis tylko na urządzeniu, migracji brak).
Bez force-pusha; commity po polsku, bez nazw modeli AI; nie scalasz PR-a.

#### 1. Decyzja właściciela (14.09.2026, trzecia tura)

> Docelowo użytkownicy będą mogli wybrać między kompletną czarno-zieloną a nową szatą.
> Do tego dążymy. Nowa szata musi być kompletna.

Czyli: **dwa motywy, oba pełne, wybór należy do użytkownika** (klienta i trenera, każdy
dla siebie). Ciemny czarno-zielony zostaje motywem domyślnym marki (§7 pyt. 1); nowy
jasny czerwono-biały ma objąć **każdy ekran** aplikacji, nie tylko stronę publiczną.
Konsekwencja dla PR #67: zdanie „Ciemny motyw aplikacji zostaje: na siłowni ma być
czytelny, nie jasny” na stronie publicznej **schodzi** (zastąpione: „Motyw wybierasz sam:
ciemny na siłownię albo jasny czerwono-biały.”) — wpisane do promptu domknięcia #67.

#### 2. Rozpoznanie — stan kodu (zmierzone)

| Fakt | Gdzie | Znaczenie |
|---|---|---|
| Jeden arkusz `src/styles.css` (653 linie na `main` 0.66.0), jeden blok `:root` z 24 tokenami (15 kolorów, 3 promienie, 2 fonty, ruch, `--nav-h`) | `styles.css` l. 6–33 | drugi motyw = **jeden blok nadpisujący tokeny** po `:root` |
| **~93 % kolorów idzie przez tokeny**: 124 odwołania `var(--…)` kontra **9 literałów** poza `:root` (i 1 w bloku landingu) | lista w §4.2 | tanie do domknięcia |
| **Zero literałów hex/rgb/hsl w całym `src/**/*.tsx`**; ~60 kolorów w `style={{}}` — wszystkie przez `var(--…)`; `Icon` = `currentColor`; `Sparkline` = `var(--accent)`; `MuscleMap.tsx` bez kolorów (klasy `.mmap__*`) | `components.tsx` l. 93, 1409–1423; `MuscleMap.tsx` l. 5–9 | komponenty przełączą się same |
| **Brak mechanizmu**: żadnego `data-theme`, `prefers-color-scheme`, `color-scheme`, stanu motywu | grep całego `src/`, `index.html`, `public/` | do zbudowania: atrybut + zapis + przełącznik |
| Brak tokenów cienia — głębię na ciemnym buduje „schodek powierzchni” (`--bg` → `--bg-raised` → `--bg-card`), komentarz l. 1–8 | `styles.css` l. 1–8 | na bieli schodek znika: potrzebny `--shadow-card` i obrys kart |
| `index.html` l. 6 `<meta name="theme-color" content="#0b0d0f">`; `manifest.webmanifest` `theme_color`/`background_color` = `#0b0d0f` | | meta przełączalna w runtime; manifest **nie** jest per użytkownik (zostaje ciemny) |
| CSP `style-src 'self'` (bez `unsafe-inline`) | nagłówki backendu | motyw nie może wstrzykiwać `<style>`; wszystko w `styles.css` |
| Grafiki marki są limonkowe i rastrowe: `boar-mark.png` (Logo w każdym `TopBar`, `components.tsx` l. 34), `logo-full.png` (`Login.tsx` l. 76), `icon-192/512.png`, `favicon-64.png`, `og.png`, 4 zrzuty w `public/screens/` (ciemna aplikacja) | `public/icons/`, `public/screens/` | znak w jasnym motywie: `boar-mark-red.png` (jest po #67); reszta = decyzja o znaku (§7 pyt. 2) |
| Zapis preferencji: `localStorage` użyty 2× (`dzik_push_prompt_*` w `components.tsx` l. 929/967, szkice formularzy w `assistantUtils.ts`); sesja w `sessionStorage` (`api.ts` l. 24–57, `clearSession()` = „JEDNO miejsce czyszczenia”); po stronie serwera `NotificationSetting` (jeden wiersz na użytkownika, `models.py` l. 977–993) z `GET/PUT /api/notifications/settings` (`routers/notifications.py` l. 130–230) i wrapperami `api.ts` l. 630–633 | | gotowy dom dla `theme` |
| Warstwa 4 modelu użytkownika klasyfikuje „motyw wyświetlania” jako **D0** (publiczne/neutralne) | `docs/LAYER_4_USER_MODEL_DIGEST.md` l. 272 | zapis serwerowy bez nowej zgody |
| Testy: `e2e/test_a11y.mjs` (poza Playwright) sprawdza brak przewijania 320/375/768/1024, nagłówki, etykiety, cele 44 px, a **kontrast tylko przez axe-core, jeśli jest zainstalowany** (inaczej cicho pomija), na ~5 ekranach; `playwright.config.ts` bez porównywania zrzutów | | kontrast jasnego motywu trzeba **policzyć i wpisać**, nie liczyć na axe |
| `DOSTEPNOSC.md` §45–54 deklaruje współczynniki **dla ciemnego motywu** | | potrzebna równoległa tabela dla jasnego |

#### 3. Podgląd wykonany (dowód, że to działa)

Na kopii `main` (0.66.0) dopisano do zbudowanego arkusza blok `html[data-theme="czerwony"]`
z `motyw-czerwony.tokens.css`, ustawiono atrybut po załadowaniu i zrobiono zrzuty
**tych samych 10 ekranów w obu motywach** na serwerze E2E z seedem: klient (Pixel 7):
Dzisiaj, Plan, Dieta, Postępy, Więcej, Profil; trener (1280 px): Klienci, karta klienta,
Szablony, Wiedza. Wynik: karty, odznaki, chipy, przyciski, tabele, zakładki, ikony,
kafle makro, karta celu z poświatą — **przełączają się poprawnie**. Widoczne braki (wszystkie
z listy literałów §4.2): dolna/górna **nawigacja zostaje ciemna** (`.nav` l. 246), **znak
dzika limonkowy** na jasnym tle, scrim `.dlaczego`, mapa mięśni. Zrzuty porównawcze
(`para-*.jpg`) właściciel dostał 14.09; powtórz je po wdrożeniu tym samym skryptem
(§5 etap 5) jako dowód uruchomienia.

#### 4. Co dokładnie zbudować

##### 4.1 Mechanizm
* `src/theme.ts`: `type Motyw = "ciemny" | "czerwony"`, `ustawMotyw(m)` (pisze
  `document.documentElement.dataset.theme`, `<meta name="theme-color">` = `#0b0d0f` /
  `#FFFFFF`, `localStorage["dzik_theme"]`), `odczytajMotyw()` (localStorage → domyślny
  `ciemny`). Wywołanie **w `main.tsx` przed `createRoot`** (CSP nie pozwala na skrypt
  inline w `index.html`; arkusz jest już załadowany, więc mignięcia praktycznie nie ma —
  zmierz i opisz).
* `clearSession()` (`api.ts` l. 47–57) **nie** czyści `dzik_theme` — świadomy wyjątek
  z komentarzem (motyw to preferencja urządzenia, nie stan sesji).
* `styles.css`: `:root { color-scheme: dark }` + `html[data-theme="czerwony"] { color-scheme:
  light; …tokeny… }`. Blok tokenów: `motyw-czerwony.tokens.css` (kontrast policzony
  w komentarzach). Nowe tokeny, które muszą powstać **w obu motywach** (bo dziś są
  literałami): `--shadow-card`, `--nav-bg`, `--scrim`, `--mmap-body`, `--mmap-region`,
  `--mmap-secondary`, `--danger-soft`, `--warn-soft`, `--landing-top-bg` (albo landing
  poza mechanizmem — patrz §4.5).

##### 4.2 Literały do zamiany na tokeny (9 + 1, `styles.css` na `main` 0.66.0)
| Linia | Selektor | Dziś | Token |
|---|---|---|---|
| 172 | `.btn--danger:hover` | `rgba(255,122,122,.1)` | `--danger-soft` |
| 246 | `.nav` | `rgba(20,23,26,.92)` pod `backdrop-filter` | `--nav-bg` (jasny: `rgba(251,245,245,.92)`) |
| 285 | `.alert--error` | `rgba(255,122,122,.12)` | `--danger-soft` |
| 287 | `.alert--warn` | `rgba(240,180,80,.12)` — **już dziś nie zgadza się z `--warn #ffc94d`** (dryf) | `--warn-soft` |
| 522 | `.mmap__body` | `rgba(255,255,255,.05)` | `--mmap-body` (jasny: `rgba(16,20,24,.06)`) |
| 524 | `.mmap__region` | `rgba(255,255,255,.07)` | `--mmap-region` |
| 525, 531 | `.mmap__region--secondary`, `.mmap__key--secondary` | `rgba(179,242,62,.34)` | `--mmap-secondary` (jasny: `rgba(225,29,46,.30)`) |
| 615 | `.dlaczego` (scrim) | `rgba(0,0,0,.45)` | `--scrim` (jasny: `rgba(16,20,24,.35)`) |
| 539 | `.landing-top` | `rgba(11,13,15,.92)` | patrz §4.5 |
Po zamianie: `grep -nE "#[0-9a-f]{3,6}|rgba?\(" src/styles.css` poza `:root`, blokiem
`[data-theme]` i `.landing--czerwony` ma zwrócić **0** — dołóż to jako kontrolę do
`tools/spojnosc.py`? **Nie** (plik integracyjny, inna runda) — dołóż jako test
`frontend/scripts/test-tokeny.mjs` w `test:helpers` (kontrola `testy frontendu` wymaga
wpisu).

##### 4.3 Zapis wyboru
* **Urządzenie:** `localStorage["dzik_theme"]` (jak wyżej) — działa też na `/login`.
* **Konto (rekomendowane, domyślne):** kolumna `theme VARCHAR(20) NULL` w
  `NotificationSetting` (migracja addytywna, kolejny wolny numer), pole `theme` w
  `SettingsIn`/odpowiedzi `GET/PUT /api/notifications/settings` (walidacja
  `^(ciemny|czerwony)$`), po zalogowaniu: jeśli serwer ma wartość, nadpisuje lokalną i
  zapisuje do localStorage; zmiana w UI = `PUT` + lokalnie. Eksport danych
  (`privacy.py`) już zawiera ustawienia powiadomień — sprawdź, że nowe pole wchodzi
  automatycznie; audyt: `record_event("THEME_CHANGED")` **nie** — D0, bez śladu
  (zapisz uzasadnienie w planie sesji).
* Trener wybiera dla siebie tak samo (to samo konto = ta sama tabela).

##### 4.4 Przełącznik w UI
`pages/More.tsx` („Więcej”): sekcja **„Wygląd”** z dwoma dużymi przyciskami-kartami
(podgląd kolorów, nazwa, opis): „Ciemny — czarno-zielony (domyślny, na siłownię)” /
„Jasny — czerwono-biały”. `role="radiogroup"`, klawiatura, `aria-checked`, bez
zapisu przy fokusie (zmiana = klik/Enter). Ten sam blok w panelu trenera („Więcej”
trenera). Na `/login` bez przełącznika (motyw z urządzenia).

##### 4.5 Znak, grafiki, strona publiczna
* `Logo` (`components.tsx` l. 31–34): `boar-mark.png` w ciemnym, `boar-mark-red.png`
  w jasnym (atrybut na `<html>` → CSS `content`/dwa `<img>` z `hidden`, bez JS).
* `Login.tsx` l. 76 `logo-full.png`: potrzebna wersja czerwona **albo** w jasnym motywie
  tylko znak + nazwa tekstem (jak zrobił landing) — domyślnie to drugie (zero nowej
  grafiki).
* Ikony PWA, `favicon`, `og.png`, `manifest` — **nie w tej rundzie** (decyzja o znaku,
  §7 pyt. 2; manifest i tak nie jest per użytkownik).
* Strona publiczna: ma własną paletę `.landing--czerwony` niezależną od `data-theme`
  (jest publiczna, nie ma użytkownika) — zostaje; `/prywatnosc` dzieli klasy `.landing*`
  z ciemnym blokiem: w jasnym motywie ma się przełączyć na tokeny (sprawdź P0 z #67:
  Privacy.tsx). `public/screens/*.jpg` (ciemne) zostają; jasny komplet = później.
* Zrzuty ekranu w galerii landingu: bez zmian.

##### 4.6 Dostępność i dokumenty
* `DOSTEPNOSC.md`: nowa sekcja „Kontrast (motyw jasny czerwono-biały)” z tabelą par
  i współczynników — **wartości policzone**: tekst/biel 18,5; `--text-dim`/biel 6,13;
  `--text-dim`/róż popielaty 5,69; biały tekst na `--accent` 4,75 (AA); `--danger` 6,95;
  `--warn #8A5A00` 5,93 (żółć ze spec `#FFC94D` nie ma AA na bieli — stąd bursztyn);
  `--ok #1E7A46` 5,35; obrys `--border-strong #B3878A` 3,11 (1.4.11); tekst na
  `--accent-soft` 15,2; link `#B3121F` na `--accent-soft` 5,72. Cele dotyku i fokus
  bez zmian (fokus: obrys `--accent` — na bieli 4,75, OK).
* `test_a11y.mjs`: parametr `DZIK_THEME` i drugi przebieg w jasnym motywie
  (ustawienie `localStorage` przed nawigacją); axe-core zainstalować jako devDependency,
  żeby kontrola kontrastu przestała być opcjonalna (jeśli koszt budżetu/CI akceptowalny —
  inaczej zapisz jawnie, że kontrast jest liczony ręcznie).
* `INSTRUKCJA_KLIENTA.md` / `INSTRUKCJA_TRENERA.md`: „Wygląd” w „Więcej”.
* `CHANGELOG.md`, `RELEASE_STATUS.md`, `STAN_PRZEKAZANIA.md`, `PERMISSIONS.md` (jeśli
  nowe pole w API), plan sesji.

#### 5. Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|
| 0 | plan sesji z rezerwacjami; `grep` literałów jako punkt odniesienia | — | tysiące |
| 1 tokeny | 9 literałów → tokeny (bez zmiany wyglądu ciemnego!), nowe tokeny w `:root`, blok `[data-theme="czerwony"]` z pliku, `color-scheme` | zrzuty ciemnego **przed/po** identyczne piksel w piksel (skrypt §5 etap 5, porównanie `PIL`/`pixelmatch`) — to jest bramka etapu | dziesiątki tys. |
| 2 mechanizm | `theme.ts`, `main.tsx`, `clearSession` wyjątek, meta theme-color, `Logo` dwa znaki, login bez `logo-full` w jasnym | `tsc`, build (budżet 120 kB), test helpera `theme.ts` (`scripts/test-theme.mjs` w `test:helpers`) | dziesiątki tys. |
| 3 zapis konta | migracja, model, API, `api.ts`, synchronizacja po logowaniu | `test_notifications.py` (walidacja wartości, obcy użytkownik, eksport), macierz dostępu bez nowych tras | dziesiątki tys. |
| 4 UI | sekcja „Wygląd” w `More.tsx` (klient i trener) | E2E `motyw.spec.ts`: wybór jasnego → `html[data-theme]`, meta, przetrwanie `reload` i wylogowania/zalogowania, trener niezależnie; a11y radiogroup | setki tys. |
| 5 kompletność | skrypt `frontend/scripts/zrzuty-motywy.mjs` (wzorzec z 14.09: logowanie, lista ekranów klienta i trenera, oba motywy, pełna strona) + **przegląd wszystkich ~60 ekranów** (8 publicznych, 15 klienta, 9 trenera, admin, 5 wspólnych, ~21 pod-ekranów w zakładkach: `PlanEditor`, `KreatorDan`, `PrzypiszDiete`, `SzkicPlanu`, `WywiadTab`, `PublikacjaPanel`, `DietaSzablon`, `PanelNawykow`, `Formularz`, `Zapotrzebowanie`, `Dlaczego`, `MuscleMap`, `FoodCatalog`, `OcrCapture`, `PlanAssistant`, `Thread`, `Notifications`, `Checkin`, `Progress`, `Onboarding`) | lista ekranów z odhaczeniem w `docs/motyw/PROGRESS.md`; każdy „dark island” (literał, który przeoczono) → poprawka | setki tys. (największy koszt) |
| 6 dostępność + dokumenty | `DOSTEPNOSC.md`, `test_a11y.mjs` w obu motywach, instrukcje, CHANGELOG | axe w obu motywach na 5 ekranach; ruff, pytest, Core 275, spójność, mutacje | dziesiątki tys. |

Bezpiecznik: 3× plan. Przegląd: 3 recenzentów wsadowo (kontrast/a11y, regresja ciemnego
motywu piksel w piksel, kompletność ekranów).

#### 6. Czego świadomie NIE robimy
Ikony PWA / favicon / `og.png` / manifest w czerwieni (decyzja o znaku), jasne zrzuty do
galerii landingu, motyw „systemowy” wg `prefers-color-scheme` (pyt. 3), zmiana strony
publicznej poza jednym zdaniem, zmiana ciemnego motywu (musi zostać piksel w piksel).

#### 7. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)
1. Motyw domyślny dla nowych kont i niezalogowanych: **ciemny** (marka, siłownia)?
   *Domyślnie: ciemny.*
2. Znak w jasnym motywie: czerwony dzik (`boar-mark-red.png`) tylko wewnątrz jasnego
   motywu, a ikony PWA/og zostają limonkowe do osobnej decyzji? *Domyślnie: tak.*
3. Trzecia opcja „jak w systemie” (`prefers-color-scheme`)? *Domyślnie: nie w v1
   (dwa motywy, jak brzmi decyzja).*
4. Zapis wyboru na koncie (migracja + pole w ustawieniach), czy tylko na urządzeniu?
   *Domyślnie: na koncie i na urządzeniu.*
5. Nazwy w UI: „Ciemny (czarno-zielony)” / „Jasny (czerwono-biały)”? *Domyślnie: tak.*

### Plik danych `motyw-czerwony.tokens.css`

```css
/* SZKIC (14.09) — drugi motyw „czerwono-biały” jako nadpisanie tokenów :root.
   Wartości z kanwy „Dzik OS — wariant jasny” (Paleta) + kontrast policzony.
   Do wklejenia w styles.css pod :root, po decyzji właściciela. */
html[data-theme="czerwony"] {
  color-scheme: light;
  --bg: #FFFFFF;             /* biel — tło strony */
  --bg-raised: #FBF5F5;      /* róż popielaty — pasma, nawigacja */
  --bg-card: #FFFFFF;        /* karta biała z obrysem (na ciemnym hierarchię budują schodki, tu obrys+cień) */
  --bg-hover: #FDECEE;       /* pasmo różowe */
  --border: #ECE4E4;         /* obrys kart i separatory */
  --border-strong: #B3878A;  /* obrys pól/ghost — 3,11:1 na bieli (1.4.11) */
  --text: #101418;           /* grafit — 17,6:1 */
  --text-dim: #566372;       /* 6,13:1 na bieli, 5,6:1 na różu popielatym */
  --accent: #E11D2E;         /* czerwień marki — przyciski, aktywna zakładka; biały tekst 4,75:1 */
  --accent-soft: #FDE3E5;    /* poświata — tła odznak */
  --accent-glow: rgba(225, 29, 46, 0.22);
  --accent-ink: #FFFFFF;     /* tekst na przycisku akcentowym */
  --danger: #B3121F;         /* 6,95:1 */
  --warn: #8A5A00;           /* 5,9:1 (ciemny bursztyn — żółć ze spec nie ma AA na bieli) */
  --ok: #1E7A46;             /* 5,3:1 */
}
/* Karty na bieli potrzebują cienia różowawego ze spec (na ciemnym cień nie istnieje). */
html[data-theme="czerwony"] .card { box-shadow: 0 10px 30px rgba(122, 10, 20, 0.06); }
```


---

## 9. Zlecenie 5 — Rozgrzewka, rozciąganie i cardio z suwakami celów

### Źródło: `model-suwakow-cardio.md`


**Status:** propozycja modelu do przeglądu trenera (Łukasz) i do implementacji w zleceniu
`PROMPT_writer_cardio-i-rozgrzewka.md`. Autor: sesja tylko-do-odczytu, 14.09.2026.
Poziomy pewności oznaczone: **[A]** zgodne z wytycznymi/metaanalizami, **[B]** dobrze
opisane w literaturze, ale z dużą zmiennością osobniczą, **[C]** synteza własna /
praktyka trenerska — do potwierdzenia przez trenera. Nic z tego nie jest poradą medyczną;
aplikacja proponuje, trener decyduje (zasada propose-only, `docs/PERMISSIONS.md` §5.5).

#### 1. Po co suwaki i na czym je oprzeć

Właściciel: trzy główne cele reprezentowane suwakami, które sumują się do całości
(domyślnie po 1/3; przesunięcie jednego zabiera pozostałym), a ustawienie ma sugerować
**tętno, obciążenie, tempo i czas**, po czym wybiera się jedno z urządzeń.

Istniejące modele, na które da się to odwzorować (nie wymyślamy własnej fizjologii):

| Model | Co daje | Pewność |
|---|---|---|
| **Trzy strefy wg progów (Seiler):** Z1 poniżej pierwszego progu (rozmowa swobodna), Z2 między progami, Z3 powyżej drugiego progu | jedna oś intensywności, na której leżą wszystkie trzy cele; rozkład polaryzowany 80/20 u wytrzymałościowców | [A] dla istnienia progów i stref, [B] dla przełożenia na %HRmax bez testu |
| **Karvonen (rezerwa tętna, HRR):** tętno docelowe = HRspocz + % × (HRmax − HRspocz) | lepsze niż %HRmax, gdy znamy tętno spoczynkowe | [A] |
| **HRmax z wieku:** Tanaka 208 − 0,7 × wiek (błąd ±10 ud./min); 220 − wiek gorsze | punkt startowy, gdy brak testu; zawsze jako **zakres**, nie liczba | [A] dla wzoru, [B] dla dokładności u konkretnej osoby |
| **Kategorie intensywności ACSM:** umiarkowana ≈ 64–76 % HRmax (40–59 % HRR), intensywna ≈ 77–95 % HRmax (60–89 % HRR) | wspólny język z wytycznymi zdrowia publicznego | [A] |
| **Fatmax (Achten & Jeukendrup):** maksymalne utlenianie tłuszczu ok. 60–65 % VO2max (≈ 65–75 % HRmax), szeroka strefa 55–72 % VO2max, duża zmienność osobnicza | podstawa dla celu „spalanie tłuszczu” | [B] |
| **Interwały pod VO2max (Helgerud 4×4 min przy 90–95 % HRmax; metaanaliza Milanović: HIIT > ciągły dla VO2max)** | podstawa dla celu „wydolność” | [A] |
| **Test mowy (Foster) i RPE (Borg CR10)** | zamiennik tętna, gdy brak pulsometru albo tętno nie ma sensu (beta-blokery) | [A] |

**Zastrzeżenie, które musi być w UI (uczciwość, KARTA §0.3):** „spalanie tłuszczu” w
strefie Fatmax to udział tłuszczu jako paliwa **podczas** wysiłku; o utracie tkanki
tłuszczowej decyduje bilans energetyczny w tygodniach. Metaanalizy (m.in. Keating 2017,
Wewege 2017) pokazują podobną utratę tłuszczu dla interwałów i wysiłku ciągłego przy tym
samym wydatku energii [A]. Dlatego cel 1 nazywamy w UI **„Redukcja (wydatek energii)”**
i pokazujemy szacowany wydatek kcal, a nie obiecujemy „spalania tłuszczu”.

#### 2. Trzy cele — nazwy i anatomia

Właściciel podał dwa: utrata tkanki, wydolność. Trzeci ma być „najtrafniejszy”. Kandydaci:

| Trzeci cel | Za | Przeciw |
|---|---|---|
| **Regeneracja i baza tlenowa (Z1)** — rekomendacja | rozciąga oś intensywności w dół (R < F < W), więc suwaki nie są redundantne; aktywna regeneracja to realna praktyka trenerska między dniami siłowymi; najniższe ryzyko | mniej „sprzedażowa” nazwa |
| Wytrzymałość (długi czas, Z2) | popularne słowo | prawie pokrywa się intensywnością z redukcją — suwak nie zmieniałby wyników |
| Moc / szybkość (Z3, sprinty) | wyraźnie inny | nakłada się z wydolnością, wyższe ryzyko u początkujących |

**Rekomendowana trójka (nazwy w UI):**
1. **Redukcja** — wydatek energii przy umiarkowanej intensywności, długi czas (Fatmax/Z2 dolna).
2. **Wydolność** — VO2max, interwały wysokiej intensywności (Z3).
3. **Regeneracja** — baza tlenowa, niska intensywność, krótko (Z1).

#### 3. Mechanika suwaków (simpleks)

Wagi `w = (wR, wW, wG)` dla (Redukcja, Wydolność, reGeneracja), każda 0–1, `wR + wW + wG = 1`.
Domyślnie `(1/3, 1/3, 1/3)`. Przesunięcie jednego suwaka o `+d` zabiera pozostałym
proporcjonalnie do ich bieżących wag (jeśli oba równe — po `d/2`); suwak zablokowany
(kłódka) nie oddaje. To jest ten sam mechanizm, co procentowy rozkład makro w kreatorze
diety (suma 100) — do skopiowania. Prezentacja: trzy suwaki + trójkąt (ternary) jako
podgląd, wartości zaokrąglone do 5 %.

#### 4. Kotwice i mieszanie

Każdy cel ma kotwicę: intensywność (%HRmax, %HRR, RPE CR10, test mowy), czas, strukturę.

| Cel | %HRmax | %HRR | RPE | Test mowy | Czas (min) | Struktura |
|---|---|---|---|---|---|---|
| Regeneracja (G) | 55–65 | 35–50 | 2–3 | pełne zdania swobodnie | 20–30 | ciągła |
| Redukcja (R) | 65–75 | 50–65 | 4–5 | zdania, lekko przerywane | 40–60 | ciągła (lub 2 bloki) |
| Wydolność (W) | 85–95 w pracy / 60–70 w przerwie | 75–90 / 45–55 | 7–9 / 3 | pojedyncze słowa | 20–30 łącznie (np. 4×4 min + przerwy 3 min) | interwały |

Pewność kotwic: [A] dla G/W, [B] dla R (Fatmax). Wszystkie liczby to **zakresy**.

**Mieszanie [C — synteza własna, do przeglądu trenera]:**
* intensywność ciągła = `Σ w_i × środek_i` (środek: G 60, R 70, W 90 %HRmax; w przerwach
  interwału stała 65);
* czas = `Σ w_i × środek_czasu_i` (G 25, R 50, W 25 min), zaokrąglony do 5 min;
* struktura wg `wW`: `wW ≥ 0,5` → interwały (4×4 dla zaawansowanych, 6×2 dla średnich,
  8×1 min lub 30/30 dla początkujących); `0,25 ≤ wW < 0,5` → „tempo” (ciągłe 78–85 % albo
  2×10 min); `wW < 0,25` → ciągłe;
* poziom zaawansowania (POCZATKUJACY/SREDNIOZAAWANSOWANY/ZAAWANSOWANY, jak w katalogu
  ćwiczeń) obniża sufit: początkujący maks. 85 % HRmax i interwały krótkie, czas −20 %;
* wynik prezentowany jako zakres ±5 % HRmax (niepewność wzoru HRmax), nigdy jako
  jedna liczba.

**Przykłady kontrolne (do testów jednostkowych):** `(1/3,1/3,1/3)` → ok. 73 % HRmax
ciągłe, 33 → 35 min, tempo umiarkowane; `(0,1,0)` → interwały 90 % wg poziomu, 25 min;
`(1,0,0)` → 70 %, 50 min ciągłe; `(0,0,1)` → 60 %, 25 min ciągłe; `(0.5,0.5,0)` → 80 %,
„tempo” 2×10 min, 38 → 40 min.

#### 5. Przełożenie na urządzenie (tempo i obciążenie) [C, do przeglądu trenera]

Intensywność jest jedna (tętno/RPE); urządzenie dostaje **dwie gałki**, które ją
realizują. Sugestie startowe (klient koryguje do tętna/RPE, aplikacja to mówi wprost):

| Urządzenie | Gałka „tempo” | Gałka „obciążenie” | G | R | W (praca) |
|---|---|---|---|---|---|
| Rowerek | kadencja (obr./min) | opór (poziom) | 70–80 rpm, opór niski | 80–90 rpm, opór umiarkowany | 90–100 rpm, opór wysoki |
| Bieżnia (bieg/marsz) | prędkość (km/h) | nachylenie (%) | marsz 5–6, 0–2 % | trucht 7–9 albo marsz 6–6,5 przy 3–5 % | bieg 10–14, 1 % |
| Bieżnia skos / chód pod górę | prędkość 4,5–6 km/h | nachylenie 5–15 % | 5 km/h, 5 % | 5,5 km/h, 8–12 % | 6 km/h, 12–15 % (interwały nachyleniem, nie biegiem — niski wpływ na stawy) |
| Steper | kroki/min | poziom oporu | 40–50 | 55–70 | 75–90 |
| Wioślarz | uderzenia/min (spm) | opór (damper 3–5) / czas na 500 m | 18–22 spm | 22–26 spm | 28–32 spm |

Zasada: pokazujemy „zacznij od…, dojdź do tętna/RPE z zakresu”, bo urządzenia różnią
się kalibracją. Wydatek energii: przybliżenie z METs (Compendium of Physical Activities)
× masa × czas, oznaczone jako szacunek [B].

#### 6. Dane wejściowe i bramki

* **Wiek** (z profilu / daty urodzenia) → HRmax Tanaka; brak wieku → tylko RPE i test mowy.
* **Tętno spoczynkowe** (opcjonalne, klient wpisuje) → Karvonen zamiast %HRmax.
* **Poziom** z profilu/wywiadu (doświadczenie) → sufity z §4.
* **Bramka zdrowotna (propose-only, jak konfigurator):** flagi z wywiadu
  (choroby układu krążenia, nadciśnienie, ciąża, leki wpływające na tętno, np.
  beta-blokery — tętno bezużyteczne → tylko RPE, cukrzyca, zawroty/omdlenia) →
  propozycja pokazuje się **tylko trenerowi** z ostrzeżeniem i wymaga jego akceptacji;
  klient nigdy nie dostaje propozycji bez publikacji przez trenera. Klasyfikacja
  danych: dane zdrowotne (domena `dane_zdrowotne`, zgoda), jak w konfiguratorze.
* Brak pulsometru → wariant „RPE + test mowy” jako równoprawny.

#### 7. Ślad decyzji („Dlaczego?”)

Każda propozycja zapisuje: wagi suwaków, poziom, źródło HRmax (Tanaka/Karvonen/brak),
kotwice użyte, reguły struktury, wersję modelu (`cardio_model_v1`) i listę zastrzeżeń —
w tym samym formacie, co ślad konfiguratora (`H_LAYOUT`/`H_VOLUME`), żeby zakładka
Wiedza → „Dlaczego?” mogła to pokazać klientowi po publikacji.

#### 8. Co model świadomie pomija (v1)

Testy progowe (LT1/LT2, FTP), strefy mocy, HRV, periodyzacja tygodniowa cardio vs
siła (interferencja), spalanie „po treningu” (EPOC — pomijalne w praktyce), ciąża
i choroby jako indywidualne protokoły (tylko bramka). To są kandydaci na v2 po
pilotażu z trenerem.

### Źródło: `PROMPT_writer_cardio-i-rozgrzewka.md`



---

Przeczytaj: `/AGENTS.md`, `/CLAUDE.md`, `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
`apps/dzik-os/docs/STAN_PRZEKAZANIA.md`, `apps/dzik-os/docs/KOORDYNACJA.md`,
`apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`, `apps/dzik-os/docs/KONFIGURATOR.md`,
`apps/dzik-os/docs/BAZA_CWICZEN.md`, `apps/dzik-os/docs/PERMISSIONS.md` §5.5
(propose-only), `apps/dzik-os/docs/zlecenia/model-suwakow-cardio.md`.

**Rola:** aktywny piszący. WYŁĄCZNIE `apps/dzik-os/`. Core nietykalny.
**Gałąź:** `agent/cardio-i-rozgrzewka` od aktualnego `main`. Pierwszy commit wyłącznie
`docs/plan-sesji/cardio-i-rozgrzewka.md`; draft PR `[WRITER] Rozgrzewka, rozciąganie
i cardio z suwakami`; dopiero potem kod. **Rezerwacje:** wersja wg kolejności scalania
z `README.md` tego katalogu; **migracja: kolejna wolna, 38 lub wyżej** (na `main` 0.69.0 ostatnia = 36;
**37 zarezerwowana** dla dni treningowych w CHANGELOG 0.69.0; 38/39 może wziąć runda
wywiadu kalorycznego — sprawdź `db.py` i tabelę §2 `STAN_PRZEKAZANIA.md` tuż przed zmianą).
Niezależne od gałęzi w toku (dieta, landing, motyw), ale dotyka `models.py`,
`schemas.py`, `db.py`, `Plan.tsx`, `Today.tsx`, `PlanEditor.tsx` — te same pliki co
zlecenie 1 (dni treningowe): **nie pracuj równolegle z nim na tych plikach**; kolejność
ustala właściciel. Bez force-pusha; commity po polsku, bez nazw modeli AI; nie scalasz PR-a.

#### 1. Zlecenie właściciela (14.09.2026, czwarta tura)

> Potrzebujemy zaimplementować jeszcze dwa rodzaje ćwiczeń: rozgrzewka na 3 poziomach
> zaawansowania w 3 wariantach, rozciąganie, i ćwiczenia fitness typu rowerek, bieżnia,
> bieżnia skos/chód, steper, wioślarz. W ćwiczeniach fitness genialnie byłoby mieć coś na
> zasadzie suwaka: 3 główne cele (utrata tkanki, wydolność i trzeci — znajdź najtrafniejszy);
> po równo każdy suwak ma 1/3, przesuwając jeden zabieramy pozostałym; z wiedzy i badań
> ustawienie suwaków sugeruje tętno, obciążenie, tempo i czas. Może uda się znaleźć model,
> na którym da się to odwzorować; następnie dobieramy jedno z ćwiczeń.

Odpowiedź na „czy jest model”: **tak** — trzy strefy wg progów (Seiler) + rezerwa tętna
(Karvonen) + Fatmax + interwały pod VO2max; trzeci cel: **Regeneracja (baza tlenowa)**
z uzasadnieniem i dwiema alternatywami w `model-suwakow-cardio.md` §2. Właściciel
zatwierdza nazwy trzech celów (§8 pyt. 1).

#### 2. Rozpoznanie — na czym budujemy (main 0.69.0, `04d1d58`; zweryfikuj linie)

| Element | Gdzie | Co z tego wynika |
|---|---|---|
| Katalog ćwiczeń: `Exercise` (`models.py` l. 774–~815): `muscle_group` ∈ NOGI/PLECY/KLATKA/BARKI/RECE/BRZUCH/CALE_CIALO/**MOBILNOSC/CARDIO**/INNE, `level` ∈ POCZATKUJACY/SREDNIOZAAWANSOWANY/ZAAWANSOWANY, `pattern`, `equipment`, `how_to`, `benefit`, `video_url`, broadcast trenera | wbudowana baza `exercise_catalog.py`: **155 ćwiczeń**, w tym **14 MOBILNOSC** (krążenia ramion, koci grzbiet, world's greatest stretch, rotacja 90/90, open book, zginacze bioder, łydki o ścianę, dwugłowe z taśmą, mobilizacja skokowego, halo KB, zwis, …) i **14 CARDIO** (rower stacjonarny, marsz pod górę na bieżni, stepper, wioślarz — interwały, orbitrek, bieg konwersacyjny, interwały 30/30, skakanka, assault bike, …) | rozgrzewki składamy z istniejących wpisów; brakuje **rozciągania statycznego** (czworogłowe, dwugłowe siedząc, pośladkowe, przywodziciele, kark, przedramiona) i **jednostek cardio „na parametry”** (bieżnia skos jako osobny wpis jest: „Marsz pod górę na bieżni”) |
| Pozycja ćwiczenia w planie: `schemas.ExerciseIn` (l. 68–93): `id`, `name`, `exercise_id` (miękkie odniesienie), `sets`, `reps`, `weight`, `tempo`, `rest`, `comment`, `video_url`, `target_rir`, `progression` — **wszystko tekst, bez rodzaju** | treść JSON w niemutowalnej wersji (`content_json`, `days[].exercises[]`), stabilne `id` z `publikacja/elementy.py::znormalizuj` | nowe rodzaje = **nowe opcjonalne klucze w tym samym JSON** (bez migracji planu): `kind`, `block_id`, `cardio` |
| Dzień planu: `PlanDayIn` (`id`, `name`, `weekday`, `exercises`) | | dzień dostaje opcjonalne `warmup_block_id`, `cooldown_block_id` |
| Dziennik: `WorkoutSetIn` ma już `warmup: bool` i `unit` (0.66.0, decyzja właściciela 14.09 — „seria rozgrzewkowa wykluczona z rekordów”), `WorkoutEntryIn` = `exercise_index`, `result`, `sets[]`, `comment`, `file_id`; `WorkoutSessionIn` = `plan_version_id`, `day_index`, `performed_on`, `status`, `pain_flag` | **brak pól czasu, tętna, RPE, dystansu** | cardio potrzebuje w `WorkoutEntryIn` opcjonalnych: `duration_min`, `avg_hr`, `rpe`, `distance_km`, `machine` — JSON w `WorkoutEntry` czy kolumny: patrz §4.4 (migracja) |
| Bramka zdrowotna konfiguratora: `konfigurator/zdrowie.py::ocen_zdrowie` (objawy alarmowe → `urgent_stop`; brak odpowiedzi → `needs_input`, nigdy „zielone”; choroba → `needs_review`) | | **reużyj 1:1** dla propozycji cardio; dołóż jedno pytanie: leki wpływające na tętno (beta-blokery) → tryb „tylko RPE” |
| Ślad decyzji: `konfigurator/silnik.py::_issue(code, severity, message, rule_id)` z `rule_id` `H_LAYOUT`/`H_VOLUME`; zapis przez `/konfigurator/zapisz` do `TrainingPlanVersion`; zakładka Wiedza → „Dlaczego?” czyta ślad | | ślad suwaków z `rule_id="H_CARDIO"` (§7 modelu) |
| Propose-only: `POST /api/konfigurator/podglad` (liczy) → `POST /zapisz` (trener tworzy wersję) | | ten sam kształt: `POST /api/cardio/podglad` → wynik trafia do edytora planu jako pozycja `kind: "cardio"`; klient nigdy nie dostaje propozycji bez publikacji |
| Sprzężone procenty: kreator diety pilnuje tylko „Suma makro = 100 %” (`Knowledge.tsx` l. 1828–1830), **bez sprzęgania suwaków**; jedyny `input[type=range]` to skala w raporcie (`.scale-row`) | | mechanizm „zabieranie pozostałym” trzeba napisać (mały helper + test) |
| Konfigurator 28 dni: K1 silnik bez rozgrzewki/cardio; `KONFIGURATOR.md` l. 58 wymienia „rozgrzewka vs …” jako temat pilotażu zrozumiałości; monitoring 0.66.0 wprowadził tylko flagę serii | | rozgrzewka jako **blok dnia** to nowość, nie rozszerzenie konfiguratora (K2 może z niej korzystać później) |
| Dane klienta do modelu: wiek/data urodzenia i doświadczenie w profilu/wywiadzie (`profile_service.py`, `coach_hints.py`), tętno spoczynkowe — brak | | wiek → HRmax (Tanaka); brak → RPE; tętno spoczynkowe jako metryka `MetricDefinition`/`Measurement` (bez migracji — patrz §2a) |

##### 2a. Miejsca, które bez zmiany **po cichu zgubią** nowe pola (wykryte 14.09 — obowiązkowe)

| Miejsce | Co robi | Co zrobić |
|---|---|---|
| `publikacja/elementy.py` l. 44–46 — allow-list pól ćwiczenia w szkicach (`name, exercise_id, sets, reps, weight, tempo, rest, comment, video_url, target_rir, progression, konfigurator_id`) | pole spoza listy **znika ze szkicu bez błędu** | dopisz `kind`, `block_id`, `cardio` (obiekt) i na poziomie dnia `warmup_block_id`, `cooldown_block_id`; test: szkic → publikacja zachowuje `cardio.goal_mix` |
| `wiedza/slad.py` l. 32–45 — słownik dozwolonych jednostek śladu (`minutes`, `seconds`, `sessions_per_week`, `weeks`, `hours`, …); nieznana jednostka = odrzucenie | ślad `H_CARDIO` z tętnem/%/RPE nie zapisze się | dodaj `bpm`, `percent_hrmax`, `percent_hrr`, `rpe`, `kcal`; ślad w **tej samej transakcji** co wersja planu (`slad.py` l. 3–8) — przez publikację 0.58.0, nie przez `/podglad` |
| `coach_hints.py` `HINT_AREAS` (l. 39–114) + test, że każde pytanie przepływu ma wpis | nowe pytanie wywiadu (leki wpływające na tętno) **czerwieni build** | zarejestruj w `HINT_AREAS` z `AREA_PLAN` |
| `import_exercises.py` l. 78–92 `CATEGORY_TO_GROUP` + `_assert_maps()` l. 145–156 | biblioteka v2 (`exercise_catalog_v2.py`, 120 wierszy, **wyłącznie siłowe**) twardo pada na kategorię bez mapy | jeśli dokładasz wpisy rozciągania/cardio do v2 — dodaj mapę `CARDIO`/`MOBILNOSC`; jeśli tylko do v1 (`exercise_catalog.py`) — bez zmian |
| `konfigurator/eksport.py` l. 54–60 | `warmup_minutes` z silnika K1 (budżet 600 s w `katalog.json`) jest **wyrzucany** przy zapisie do planu | nie ruszaj K1; odnotuj w `KONFIGURATOR.md`, że K2 podłączy blok rozgrzewki zamiast budżetu minut |
| `plan_templates.build_days` l. 52–95 i `plan_templates_data.py` TPL-025 (l. 936–937) / TPL-026 (l. 971–977) | trener dziś przemyca cardio i mobility jako **pseudo-dzień „1. Wytyczne tygodnia”** z `sets='5 / tydz.'`, `reps='20 min'`, notką „Tętno 130–140; rowerek lub orbitrek”, `progression='PRG-TIME'` | to jest **dokładnie to, co zastępujemy**: po rundzie TPL-025/026 dostają blok rozgrzewki (mobility) i pozycję `kind: "cardio"` (mix z notki: 130–140 ud./min ≈ Redukcja/Regeneracja); stare kopie planów zostają bez zmian |
| `docs/IMPORT_BAZ.md` §3.1 (import szablonów planów: `serie, powtorzenia, ciezar, tempo, przerwa`) | brak kolumn czasu/tętna | v1: bez zmian w imporcie (cardio i bloki tylko z edytora); wpis w „Ograniczenia” |
| `wywiad/definicje.py` l. 366–403 (`zk_wiek`, `zk_masa`, `zk_plec`, `zk_zaburzenia` z `DOMAIN_HEALTH`, `sensitive=True`) | jedyne źródło wieku; **brak tętna spoczynkowego, maks., daty urodzenia** | wiek z `zk_wiek` (gdy jest); tętno spoczynkowe **bez migracji** przez `MetricDefinition`+`Measurement` (`models.py` l. 438–461: metryka „tętno spoczynkowe”, jednostka ud./min) |
| `routers/postepy.py` l. 8–12 — filtr flagi zdrowotnej **po stronie serwera** (`hidden_for_client`) | wzorzec dla danych wrażliwych | ta sama reguła dla propozycji cardio: wynik bramki `needs_review` widzi tylko trener |
| `docs/INTENDED_PURPOSE.md` (korzeń repo) §2 i §3.3 | „każda funkcja dotykająca zdrowia przechodzi test względem §2 **przed** implementacją; wątpliwość = pytanie do foundera” | **wykonaj ten test w planie sesji (etap 0)** i zapisz wynik: propozycja tętna to struktura dla trenera, nie werdykt medyczny; bramka + RPE + propose-only; przy wątpliwości — pytanie do właściciela przed kodem |
| UI: brak `input[type=range]` w `src/` (martwy CSS `.scale-row` l. 226–231); istniejący wzorzec to segmentowana skala 1–5 z `aria-pressed` w `Checkin.tsx` l. 586–622; suma 100 w `DietWizardIn._suma_procentow` (`schemas.py` l. 684–691, tolerancja ±1) | | suwaki: prawdziwe `input[type=range]` z `aria-valuetext` + helper sprzęgający; serwer waliduje sumę wag (tolerancja 0,01), **nie normalizuje po cichu** |

#### 3. Decyzje projektowe (propose-only → do zatwierdzenia w §8)

1. **Trzy rodzaje pozycji w planie:** `kind ∈ {"strength" (domyślne, brak klucza = strength), "warmup_block", "stretch_block", "cardio"}`. Stare plany bez `kind` działają bez zmian (kompatybilność jak `target_rir`).
2. **Bloki rozgrzewki i rozciągania = byty katalogowe trenera** (`ExerciseBlock`: `id`, `coach_id`, `kind` WARMUP/STRETCH, `level`, `variant` G/D/C, `name`, `duration_min`, `items_json` = lista `{exercise_id|null, name, dose ("3 min"/"2×10"/"20 s/str."), note}`, `status`, wersjonowanie jak `Exercise`). Wbudowany zestaw **3×3 rozgrzewek + 3 bloki rozciągania** (szkic treści w §5) ładowany przyciskiem jak „wbudowana baza” (`load-builtin`), oznaczony `source="wbudowany — do przeglądu trenera"`. Dzień planu wskazuje blok przez `warmup_block_id`/`cooldown_block_id` (miękkie odniesienie + **migawka treści** w wersji planu, żeby archiwizacja bloku nie psuła planów — wzorzec `exercise_id` + `name`).
3. **Cardio = pozycja `kind: "cardio"`** z polami: `machine` ∈ {`rowerek`, `bieznia`, `bieznia_skos`, `steper`, `wioslarz`} **albo lista dozwolonych** (klient wybiera w dniu treningu), `goal_mix` `{redukcja, wydolnosc, regeneracja}` (suma 1), `prescription` = wynik silnika (`hr_pct_range`, `hr_bpm_range|null`, `hrr_used`, `rpe_range`, `talk_test`, `duration_min`, `structure` {`type` ciągła/tempo/interwały, `work`, `rest`, `rounds`}, `machine_params` per urządzenie, `kcal_estimate`, `caveats[]`), `trace` (ślad `H_CARDIO`) i `model_version: "cardio_model_v1"`. Trener może każdą liczbę nadpisać ręcznie (pole edytowalne = propose-only); nadpisanie zapisuje się w śladzie jako `overridden_by_coach`.
4. **Silnik = czyste funkcje** `dzik_os/cardio/model.py` (mieszanie wag, kotwice, struktura wg poziomu, przeliczenie HRmax/HRR, tłumaczenie na urządzenie, MET-y) z testami na przykładach kontrolnych z `model-suwakow-cardio.md` §4; **zero AI**; stałe modelu w jednym słowniku z komentarzem źródła i poziomem pewności.
5. **Bramka zdrowotna przed propozycją** (`ocen_zdrowie` + pytanie o leki wpływające na tętno). `needs_review` → propozycja tylko z ostrzeżeniem dla trenera; `urgent_stop` → brak propozycji. Blok zdrowotny **nie jest zapisywany** w planie (jak konfigurator).
6. **Klient:** na „Dzisiaj” i w Planie pozycja cardio pokazuje: cel (trzy paski wag), urządzenie do wyboru (jeśli lista), „zacznij od…” (tempo/obciążenie), zakres tętna **i** RPE + test mowy, czas, strukturę interwałów z prostym timerem (reużyj `RestTimer`), zastrzeżenie o bilansie energii (jedno zdanie), „Dlaczego?” ze śladem. Rozgrzewka/rozciąganie: rozwijana lista pozycji z dawką, odhaczana jako całość (nie per pozycja).
7. **Dziennik:** wpis cardio zapisuje `duration_min`, `avg_hr` (opcjonalnie), `rpe`, `machine`, `distance_km` (opcjonalnie); Postępy pokazują historię cardio osobno (bez rekordów kg). Serie rozgrzewkowe siłowe — bez zmian (flaga z 0.66.0).
8. **Zero rankingów, zero automatycznej progresji** — model proponuje na dziś; kolejny tydzień = trener.

#### 4. Co dokładnie zbudować

##### 4.1 Backend
* `dzik_os/cardio/model.py` + `dzik_os/cardio/urzadzenia.py` (tabela §5 modelu) + `dzik_os/cardio/dane/stale.json` (kotwice, MET-y, ze źródłem i pewnością).
* `routers/cardio.py`: `POST /api/clients/{client_id}/cardio/podglad` (COACH, `resolve_client_access` write + domena zdrowotna dla bramki; body: `goal_mix`, `level`, `machines[]`, `duration_hint?`, `health{}`, `resting_hr?`) → `prescription`+`trace`+`issues`; `GET /api/cardio/katalog` (urządzenia, cele, opisy). Bez `zapisz` — wynik wkleja się do szkicu planu przez istniejącą publikację (0.58.0).
* `ExerciseBlock` model + migracja (`exercise_blocks`), `routers/exercise_blocks.py` (CRUD trenera, `load-builtin`, archiwizacja ≠ kasowanie), macierz dostępu, eksport (broadcast trenera — jak `Exercise`, nie dane klienta).
* `schemas.py`: `ExerciseIn` + `kind`, `block_id`, `cardio: CardioIn|None`; `PlanDayIn` + `warmup_block_id`, `cooldown_block_id`; `WorkoutEntryIn` + pola cardio; `publikacja/elementy.py`: nowe klucze przechodzą przez normalizację/różnice (podsumowanie po polsku: „zmieniono cel cardio”).
* `WorkoutEntry`: kolumny `duration_min`, `avg_hr`, `rpe`, `distance_km`, `machine` (addytywne, NULL) — **ta sama migracja** co `exercise_blocks` (jedna na rundę).
* Katalog wbudowany: ~10 wpisów rozciągania statycznego (`muscle_group="MOBILNOSC"`, `pattern="ROZCIAGANIE"` — sprawdź słownik `muscles.MOVEMENT_PATTERNS`, jeśli brak wartości, dodaj) + 5 wpisów cardio „na parametry” (jeśli wpisy z katalogu nie wystarczą: „Bieżnia — chód pod górę”, „Steper”, „Wioślarz — ciągle”, „Rowerek — ciągle”, „Bieżnia — bieg”), z `how_to` napisanym przez writera **i oznaczonym do przeglądu trenera** (`source`).
* Seed demo: dzień „Trening C — całe ciało” klienta A dostaje rozgrzewkę C/początkujący i pozycję cardio (rowerek, mix 0,5/0,25/0,25).

##### 4.2 Frontend
* Edytor planu (`PlanEditor.tsx`, `SzkicPlanu.tsx`): w dniu „Rozgrzewka: [wybór bloku poziom/wariant]” i „Rozciąganie: [blok]”; przycisk „+ Cardio” → panel: trzy sprzężone suwaki (helper `suwaki.ts`: `przesun(wagi, indeks, nowa)` — zabiera pozostałym proporcjonalnie, kłódka; test w `test:helpers`), poziom, urządzenia, „Policz propozycję” → tabela tętno/RPE/czas/struktura/urządzenie + ostrzeżenia bramki + „Wstaw do dnia” (pola edytowalne przed wstawieniem).
* Klient (`Plan.tsx`, `Today.tsx`): renderowanie trzech rodzajów (§3.6), wybór urządzenia, timer interwałów, formularz dziennika cardio (czas, RPE, tętno, dystans).
* Postępy: sekcja „Cardio” (lista sesji, suma minut/tydzień, bez rankingu).
* Panel trenera: zakładka „Bloki” w Szablonach (lista 3×3 + rozciąganie, edycja pozycji, „Dodaj z wbudowanych”).
* Wiedza → „Dlaczego?”: ślad `H_CARDIO` czytelny dla klienta (wagi, kotwice, zastrzeżenia).

##### 4.3 Testy
* Silnik: przykłady kontrolne §4 modelu (5 przypadków), sufit początkującego, brak wieku → tylko RPE, Karvonen gdy `resting_hr`, beta-blokery → `hr_bpm_range=None`, determinizm, suma wag ≠ 1 → 422.
* Bramka: `urgent_stop` → brak propozycji; `needs_input` → pytania; `needs_review` → propozycja z ostrzeżeniem.
* API: trener bez relacji → 404; klient → 403 (propozycja tylko dla trenera); ślad w wersji planu po publikacji; różnice po `id` z polskim podsumowaniem dla `goal_mix`.
* Bloki: CRUD, load-builtin idempotentny, archiwizacja nie psuje planu (migawka).
* Dziennik: wpis cardio bez serii, eksport danych zawiera nowe pola, rekordy pomijają cardio.
* Front: `test-suwaki.mjs` (zabieranie proporcjonalne, kłódka, zaokrąglenie do 5 %, suma zawsze 100), E2E `cardio.spec.ts` (trener liczy propozycję i wstawia; klient widzi na „Dzisiaj”, wybiera wioślarz, zapisuje 25 min RPE 6; „Dlaczego?” pokazuje ślad) i `rozgrzewka.spec.ts` (blok w dniu, odhaczenie).
* a11y: suwaki jako `input[type=range]` z `aria-valuetext` („Redukcja 50 %”), klawiatura.

##### 4.4 Dokumentacja
`CHANGELOG`, `BAZA_CWICZEN.md` (bloki, nowe wpisy do przeglądu), `KONFIGURATOR.md`
(relacja K1/K2 ↔ bloki), `INSTRUKCJA_TRENERA.md` (suwaki, co znaczą, że to propozycja),
`INSTRUKCJA_KLIENTA.md`, `PERMISSIONS.md` (nowe trasy), `WIEDZA.md` (ślad `H_CARDIO`),
`RISK_REGISTER.md` (ryzyko: liczby tętna u osoby z chorobą — bramka + RPE),
`RELEASE_STATUS`, `STAN_PRZEKAZANIA`, plan sesji, `docs/cardio/00_rozpoznanie.md` i
`PROGRESS.md` (w tym **lista treści do przeglądu trenera**: bloki, nowe ćwiczenia,
tabela urządzeń, kotwice [C]).

#### 5. Szkic treści bloków (z katalogu; DO PRZEGLĄDU TRENERA)
Warianty = pod jaką sesję (spójne z nazwami dni „Trening A — góra / B — dół / C — całe ciało”):
**G** góra ciała · **D** dół ciała · **C** całe ciało. Poziom = POCZATKUJACY / SREDNIOZAAWANSOWANY /
ZAAWANSOWANY (słownik katalogu). Każdy blok: 1 pozycja „podniesienie tętna” (cardio z katalogu,
3–6 min, RPE 3–4) + 3–5 pozycji mobilności/aktywacji (czas lub powtórzenia) + 1 pozycja
„seria wprowadzająca” (opis, nie ćwiczenie: „pierwsze ćwiczenie planu z 40–50 % ciężaru”).

| Poziom | G — góra | D — dół | C — całe ciało |
|---|---|---|---|
| Początkujący (≈8 min) | Marsz w miejscu z wysokim kolanem 3 min · Krążenia ramion 2×10 · Koci grzbiet 8 · Rozciąganie klatki w narożniku 2×20 s · Open book 6/str. · seria wprowadzająca | Rower stacjonarny 4 min · Krążenia bioder w podporze 8/str. · Rozciąganie zginaczy bioder w wykroku 20 s/str. · Mobilizacja stawu skokowego 8/str. · Rotacja bioder 90/90 6/str. · seria wprowadzająca | Marsz pod górę na bieżni 4 min · Koci grzbiet 8 · World's greatest stretch 4/str. · Krążenia ramion 2×10 · Rozciąganie łydek o ścianę 20 s/str. · seria wprowadzająca |
| Średni (≈10 min) | Wioślarz lekko 4 min · Halo z kettlebell 2×8/str. · Open book 8/str. · Rozciąganie klatki w narożniku 2×20 s · Zwis na drążku 2×20 s · seria wprowadzająca | Stepper 4 min · Wykrok z rotacją 6/str. · Rotacja bioder 90/90 8/str. · Rozciąganie dwugłowych z taśmą 20 s/str. · Krążenia bioder w podporze 8/str. · seria wprowadzająca | Orbitrek 4 min · World's greatest stretch 5/str. · Halo z kettlebell 8/str. · Wykrok z rotacją 6/str. · Mobilizacja stawu skokowego 8/str. · seria wprowadzająca |
| Zaawansowany (≈12 min) | Assault bike / wioślarz 5 min z 2 przyspieszeniami · Halo z kettlebell 2×10/str. · Zwis na drążku 2×30 s · Open book 8/str. · Krążenia ramion z taśmą 2×12 · seria wprowadzająca 2 stopnie | Skakanka 4 min · Wykrok z rotacją 8/str. · Rotacja bioder 90/90 10/str. · Rozciąganie zginaczy bioder 30 s/str. · Podbiegi lekkie 3×20 m (albo marsz pod górę) · seria wprowadzająca 2 stopnie | Interwały biegowe lekkie 5 min (30/30 przy RPE 5) · World's greatest stretch 6/str. · Halo z kettlebell 10/str. · Krążenia bioder w podporze 10/str. · Rozciąganie łydek 20 s/str. · seria wprowadzająca 2 stopnie |

Brakuje w katalogu (nowe wpisy do dodania jako MOBILNOSC/ROZCIAGANIE, treść trenera):
rozciąganie po treningu (statyczne 20–30 s/str.): czworogłowe stojąc, dwugłowe siedząc, pośladkowe
(„figura 4”), łydki, klatka w narożniku (jest), najszersze (jest jako zwis), zginacze bioder (jest),
przywodziciele, kark/karkowe, przedramiona. Bloki rozciągania: te same 3 warianty (G/D/C), jeden
poziom (czas 5–8 min), po treningu — bez podziału na poziomy (właściciel wspomniał „rozciąganie”
bez poziomów; pytanie).

#### 6. Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

| Etap | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|
| 0 | plan sesji, `docs/cardio/00_rozpoznanie.md` (weryfikacja linii z §2) | — | tysiące |
| 1 silnik cardio | `cardio/model.py`, `urzadzenia.py`, `stale.json`, testy przykładów kontrolnych | pytest modułu | dziesiątki tys. |
| 2 model + migracja | `ExerciseBlock`, kolumny `WorkoutEntry`, wbudowane bloki i ćwiczenia, seed | `test_migracje_przenosnosc`, integralność katalogu | dziesiątki tys. |
| 3 API + publikacja | `routers/cardio.py`, `routers/exercise_blocks.py`, `schemas`, `elementy.py`, macierz, eksport | pytest API, macierz, bramka | setki tys. |
| 4 UI trenera | edytor: bloki + panel cardio z suwakami | `tsc`, build (budżet 120 kB — panel przez `React.lazy`), `test-suwaki.mjs`, obejrzenie | setki tys. (największy koszt) |
| 5 UI klienta + dziennik + Postępy | Plan/Dzisiaj/Postępy, timer, formularz | E2E ×2, a11y, obejrzenie na telefonie przez serwer E2E | setki tys. |
| 6 zamknięcie | dokumenty, lista do przeglądu trenera, CHANGELOG | pełny pytest, ruff z korzenia, Core 275, spójność, mutacje, CI | dziesiątki tys. |

Bezpiecznik: 3× plan. Przegląd: 3 recenzentów (bezpieczeństwo zdrowotne i propose-only,
poprawność silnika i determinizm, UX/a11y/treść). **Runda jest duża — jeśli przekracza
bezpiecznik, tnij w tej kolejności:** najpierw Postępy-cardio (etap 5, część), potem
zakładka „Bloki” w Szablonach (bloki tylko wbudowane, edycja później), nigdy bramka
zdrowotna ani ślad.

#### 7. Czego świadomie NIE robimy
Automatyczna progresja cardio tydzień do tygodnia; testy progowe/FTP/HRV; integracje
z zegarkami (import tętna); rankingi; AI; zmiana konfiguratora K1 (bloki podpina K2
później); kasowanie czegokolwiek (archiwizacja).

#### 8. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)
1. Trzeci cel: **Regeneracja (baza tlenowa)** — zgoda? Alternatywy: Wytrzymałość,
   Moc/szybkość (model §2). *Domyślnie: Regeneracja.*
2. Nazwa celu 1 w UI: „Redukcja (wydatek energii)” zamiast „Spalanie tłuszczu” — bo
   o utracie tkanki decyduje bilans, a nie strefa. *Domyślnie: „Redukcja”.*
3. Warianty rozgrzewki = pod sesję (góra/dół/całe ciało)? Alternatywa: czas 5/10/15 min
   albo miejsce (siłownia/dom). *Domyślnie: góra/dół/całe ciało.*
4. Rozciąganie: 3 warianty bez poziomów, po treningu (5–8 min)? *Domyślnie: tak.*
5. Kto wybiera urządzenie: trener wskazuje listę dozwolonych, klient wybiera w dniu
   treningu? *Domyślnie: tak.*
6. Kto przegląda treść bloków, nowe wpisy katalogu i tabelę urządzeń — trener Łukasz przed
   włączeniem u prawdziwych klientów? *Domyślnie: tak, wpisy oznaczone „do przeglądu”.*
7. „Tętno spoczynkowe” jako metryka pomiarowa (klient wpisuje w Pomiarach; dane zdrowotne,
   zgoda)? *Domyślnie: tak, opcjonalne, bez migracji.*


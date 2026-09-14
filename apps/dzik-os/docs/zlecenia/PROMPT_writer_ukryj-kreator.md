# PROMPT dla sesji piszącej — „Ukryj kreator diety” (flaga, bez kasowania; katalog produktów zostaje)

> Skopiuj ten plik w całości jako pierwszą wiadomość do sesji piszącej. Zlecenie jest
> **małe** (jedna flaga + ukrycie UI + test) i **niezależne** od gałęzi w toku —
> może iść pierwsze.

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

## 1. Decyzja właściciela (14.09.2026, druga tura)

> Ogólnie zrezygnujemy z kreatora diety na ten moment — wymaga wielkiej pracy, więc
> możemy go ukryć. Ale mamy dostęp do listy pojedynczych produktów, które można by
> skorelować z tymi, co chcemy wymieniać w szablonie.

Czyli: **kreator schowany, katalog produktów zostaje** (jest źródłem danych dla
zlecenia „Wymiany produktów v2”, §5a tamtego promptu). Dieta klienta = szablon
(`Przypisz dietę`).

## 2. Rozpoznanie (zweryfikuj linie)

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

## 3. Co zbudować

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

## 4. Czego NIE robimy

Nie usuwamy kodu, tras, testów ani danych kreatora; nie ruszamy katalogu „Produkty”
ani `load-builtin`; nie ruszamy `NutritionPlan` (plany ręczne i istniejące plany
klientów); nie ruszamy „Ułóż z dań” (kulinaria) — pytanie 1.

## 5. Weryfikacja

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

## 6. Pytania do właściciela

1. „Ułóż z dań” (kreator kulinarny, 0.57.0) w karcie klienta — też ukryć, czy zostawić?
   *Domyślnie: zostawić (osobny moduł, działa na recepturach, nie na kreatorze).*
2. Ręczny formularz planu żywieniowego w karcie klienta — zostawić? *Domyślnie: tak
   (nie jest kreatorem, a trener mógł z niego korzystać).*

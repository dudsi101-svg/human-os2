# Plan sesji: ukrycie kreatora diety za flagą (0.67.0, bez migracji)

**Gałąź:** `agent/ukryj-kreator` z `main` cbfa893 (0.64.0). **Rola:** aktywny piszący —
zlecenie 0 właściciela z 14.09 („małe i niezależne, może iść pierwsze”).
**Rezerwacje (KOORDYNACJA §0):** wersja **0.67.0** — kolejna wolna po 0.66.0 (Postępy,
PR #61) i 0.65.0 (strona publiczna, PR #67); tabela wersji w README właściciela może
przypisać inny numer — wtedy zmieniam przed scaleniem. **Bez migracji.** Kolejność
scalania wg właściciela: biblioteka diet (scalona 0.64.0) → **ukryj kreator** → dni
treningowe (migracja 37) → wymiany v2. Pliki współdzielone z #61: `config.py`, `main.py`,
`CHANGELOG`, `STAN_PRZEKAZANIA`, `package.json` (konflikty rozwiązuję przy scaleniu `main`).

## Cel
Kreator diety — zakładka **„Dieta”** w Bazie wiedzy trenera (`Knowledge.tsx`: „Ułóż dietę”
z trzema drogami: „Wygeneruj propozycję” = `DietWizardTab`, „Ułóż sam z produktów” =
`DietComposerTab`, „Ułóż z dań” = `KreatorDan`) oraz dwie trasy API
`POST /api/coach/diet-wizard` i `POST /api/coach/diet-suggestion` — schowany za flagą
`DZIK_DIET_WIZARD_ENABLED` (domyślnie **wyłączona**, bez wpisu w `fly.toml`).

## Czego NIE robię (zlecenie)
Nic nie kasuję: kod, testy, dane, ręczne plany żywieniowe i istniejące plany klientów
zostają widoczne i edytowalne. Zakładka **„Produkty”** z katalogiem zostaje (źródło dla
zlecenia 2). Trasy kreatora dań (`/api/kulinaria/*`) i szablonów diet nie są objęte flagą
(zlecenie wymienia dwie trasy); ukryta zakładka zabiera z interfejsu także wejście do
kreatora dań — odnotowane w raporcie do decyzji.

## Etapy → czytam → wytwarzam → weryfikacja → nakład
| Etap | Czytam | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 1 backend | `config.py` (wzór `diet_templates_enabled`), `main.py` (`features`), `routers/food_catalog.py` | `diet_wizard_enabled`, `features.diet_wizard`, 404 na obu trasach bez flagi | nowy test: bez flagi 404 + `features` false; z flagą istniejące `test_diet_wizard.py`, `test_food_products.py` (conftest ustawia flagę) | małe |
| 2 frontend | `Knowledge.tsx` (TABS, `DietTab`), `Admin.tsx` (wzór odczytu `features` z `/api/health`) | zakładka „Dieta” tylko przy `features.diet_wizard`; kod zakładki nietknięty | tsc, build, E2E `kulinaria.spec.ts` (serwer E2E z flagą), a11y (`/trener/wiedza` bez flagi: 4 zakładki, kontrakt klawiatury bez zmian) | małe |
| 3 dokumenty | CHANGELOG, RELEASE_STATUS, PERMISSIONS, INSTRUKCJA_TRENERA, STAN §2, `diet-module/00_rozpoznanie.md` | wpis 0.67.0, sekcja „za flagą, wyłączony”, adnotacja flagi przy trasach | `tools/spojnosc.py` | małe |

**Największy koszt:** pełny pytest (bramka), nie kod. **Bezpiecznik:** 3× plan → stop i raport.

## Bramki
ruff; pełny pytest (SQLite; PostgreSQL w CI); Core 275; `tools/spojnosc.py`; tsc + build;
`test:helpers`; E2E (`kulinaria.spec.ts` przy flagi włączonej w `serve.sh`); a11y; PWA.
Scalenie po zielonym CI i po #61 (wersja 0.67.0 > 0.66.0), zgodnie z zarządzeniem z 13.09.

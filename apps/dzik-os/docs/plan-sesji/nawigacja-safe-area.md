# Plan sesji: dolna nawigacja na iPhonie — ikony ściskane przez pasek bezpieczeństwa (0.75.1)

**Gałąź:** `agent/nawigacja-safe-area` (od `main` = `8a71116`, 0.73.0). **Rola:** integrator
jako piszący, zgłoszenie właściciela z 14.09 (zrzut z iPhone’a, 18:25): „dolne ikonki tam
gdzie jest dziś raport itd są zbyt małe”.

**Protokół jednego piszącego:** równolegle otwarte PR #76 (`agent/motyw-czerwony`, 0.74.0)
i #77 (`agent/szablony-i-opisy`, 0.75.0) — zadania równoległe wg `KOORDYNACJA.md` §0
(zarządzenie właściciela z 14.09). Pliki tej rundy: `styles.css` (blok `.nav` i odstępy
`.page`), CHANGELOG, wersje, dokument planu. Blok `.nav` nie jest ruszany przez #76 ani #77;
`styles.css` w #76 zmienia tokeny i sekcję motywu — konflikt tekstowy możliwy, merytoryczny nie.

## Rozpoznanie (na `main`, przed zmianą)

* `index.html`: `viewport-fit=cover` → na iPhonie `env(safe-area-inset-bottom)` ≈ 34 px.
* `styles.css` `.nav`: `height: var(--nav-h)` (62 px) **i** `padding-bottom:
  env(safe-area-inset-bottom)` przy globalnym `box-sizing: border-box` → pole treści paska
  spada do ~28 px. Linki (`flex-direction: column`) mają za mało miejsca, a `svg` bez
  `flex-shrink: 0` jest ściskany — na zrzucie ikony mają ~12 px zamiast 22 px, etykiety
  siedzą przy samej krawędzi. Na Androidzie/desktopie (wcięcie 0) wszystko wygląda poprawnie —
  dlatego nie wyszło w Playwright (projekt „telefon” nie emuluje wcięcia).
* Rozmiar ikony 22 px to świadoma decyzja produktowa (komentarz przy `.nav svg`, Karta
  współpracy §III) — **nie zmieniam**, przywracam jej faktyczne renderowanie.

## Rezerwacje (KOORDYNACJA §0)

* **wersja 0.75.1** — po 0.75.0 (#77). Sekcja CHANGELOG na górze; przy scalaniu `main`
  po #76/#77 pozostaje nad 0.75.0. `package.json`, `__init__.py`, `pyproject.toml`, README,
  RELEASE_STATUS → 0.75.1. Bez migracji, bez zmian API, `export_version` bez zmian.
* Porty E2E: 8136/8137 (`DZIK_E2E_DIR=/tmp/dzik-e2e-8136`).

## Co robię

1. `.nav { height: calc(var(--nav-h) + env(safe-area-inset-bottom, 0px)) }` — pasek rośnie
   o wcięcie, pole treści zostaje 62 px. `.nav svg { flex-shrink: 0 }` — ikona nigdy nie
   jest ściskana. Wskaźnik aktywnej sekcji (`::before`, `top: 0`) bez zmian.
2. Odstęp dolny treści (`.page`, mobile i desktop) o `env(safe-area-inset-bottom, 0px)`
   większy — pasek jest wyższy, ostatnia karta nie chowa się pod nim.
3. Test E2E `nawigacja-safe-area.spec.ts` (projekt „telefon”): wstrzyknięty arkusz
   nadpisuje `env()` nie da się — więc test sprawdza geometrię wprost: wysokość pola treści
   `.nav` (clientHeight − paddingBottom) ≥ 62 px oraz `svg` w linku ma 22 × 22 px, przy
   dodatkowym `padding-bottom: 34px` ustawionym przez `page.addStyleTag` na `.nav`
   (symulacja wcięcia iPhone’a). Na `main` ten test jest czerwony (svg ~12 px) — dowód.
4. Bramki: tsc, build (budżet 120 kB), a11y (`test_a11y.mjs`), spojnosc, E2E `logowanie`
   + nowy spec; backend bez zmian → tylko `pytest tests/test_health*`? — nie istnieje;
   pomijam backend (brak zmian w Pythonie poza wersją) i uruchamiam `ruff`.

## Czego NIE robię

* Nie zmieniam rozmiaru ikon (22 px — decyzja produktowa) ani układu paska na desktopie.
* Nie ruszam #76/#77.

## Odstępstwa od planu

(uzupełniane)

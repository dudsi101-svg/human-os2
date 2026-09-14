# Plan sesji: strona publiczna — wariant czerwono-biały (0.65.0)

**Gałąź:** `agent/landing-czerwony` (od `main` = ceca87a). **Rola:** aktywny piszący —
prompt właściciela z 14.09 „[WRITER]: strona publiczna Dzik OS w wariancie
czerwono-białym” (projekt zatwierdzony na kanwie „Dzik OS — wariant jasny”, strona
„Wariant czerwono-biały”; specyfikacja §3–6 promptu jest kompletna — pracuję z niej).
**Kolejka (KOORDYNACJA §0, polecenie „wiele zadań naraz”):** równolegle otwarte PR #65
(nawyki 0.63.0) i #66 (biblioteka diet 0.64.0) — pliki rozłączne (`Landing.tsx`, blok
`.landing` w `styles.css`, dwa nowe PNG, `strona-publiczna.spec.ts`, `package.json`).
Scalanie: po #65 i #66; `package.json` scala się jako konflikt wersji (rozwiązuję przy
ponownym scaleniu `main`).

**Rezerwacje:** wersja **0.65.0** (0.63.0 z promptu zajęte przez nawyki, 0.64.0 przez
bibliotekę diet; monitoring przesuwa się na 0.66.0 / migrację 36). Migracja: **brak**.
Backend: **bez zmian**. Plików integracyjnych (CHANGELOG, STAN_PRZEKAZANIA, KOORDYNACJA,
KONSULTACJE, db.py, tools) **nie dotykam** — propozycje wpisów w opisie PR.

## Cel
Warstwa wizualna `/` (`Landing.tsx`) wg zatwierdzonego projektu: paleta czerwono-biała
z rytmem sekcji biały → biały → ciemny → ciemny → biały → różowy → ciemny → ciemny,
tokeny scope’owane do `.landing`, dzik w czerwieni (dwa PNG wygenerowane skryptem
z §6), ikony SVG inline, chipy, kafle statystyk, karty-powiadomienia w hero.
Treść (teksty, kolejność sekcji, formularz, honeypot, RODO, linki) bez zmian poza
dodatkami z §5.

## Zamiar (etapy → czytam → wytwarzam → weryfikacja → nakład)

| Etap | Czytam | Wytwarzam | Weryfikacja | Nakład |
|---|---|---|---|---|
| 0 | `Landing.tsx`, blok `.landing` w `styles.css`, `strona-publiczna.spec.ts`, `index.html`, `main.tsx` | ten plan | — | tysiące |
| 1 grafiki | `boar-mark.png`, `logo-full.png` | `boar-mark-red.png` 96 px, `boar-hero-red.png` 560 px (skrypt §6, próg nasycenia 0,35 → 0,25 gdy zostają zielone obwódki) | podgląd PNG, wagi | tysiące |
| 2 style | §3–4 | tokeny `.landing`, gradienty/kafle/liść/dark/card--dark/wm, przyciski, karty, chipy, formularz, siatka, RWD 390 px | build | dziesiątki tys. |
| 3 sekcje | §5 | pasek górny z nawigacją, hero z panelem i kartami, oferta z kaflami/ikonami/chipami, kroki (ciemne), aplikacja (siatka 4), trener (zdjęcie + kafle statystyk), FAQ 2×2, kontakt (ciemny, formularz w karcie), stopka | tsc, build, E2E 3 istniejące + 1 nowy (nagłówek kroków, „30 000+”, chip „Mapa mięśni”, brak poziomego przewijania 390 px) | setki tys. |
| 4 weryfikacja | — | zrzuty 1440/390 (hero, oferta, ciemny blok, trener, FAQ, kontakt, stopka) + kontrolne `/login` i „Dzisiaj”; kontrast (`--l-red-link`/biel, `--l-dark-text-dim`/`#0B0F14`, biel/`--l-red`); klawiatura; a11y; bramka repo (ruff, pytest, Core, spójność) | raport w PR | dziesiątki tys. |

**Największy koszt:** etap 3 (JSX + CSS ~ 600 linii). Taniej bez utraty dokładności:
jedna mapa ikon SVG jako obiekt, kafle/chipy jako dane przy `ATUTY`, style pisane raz
na blok; zrzuty jednym skryptem Playwright. Bezpiecznik: 3× plan → stop i raport.

## Świadomie nie robię
* nie zmieniam `:root`, aplikacji po zalogowaniu, `/login`, `/prywatnosc`, ikon PWA,
  `logo-full.png`, `manifest.webmanifest`, `sw.js`, `og.png` (zadanie następne);
* nie dodaję drugiego `theme-color` (ryzyko zmiany wyglądu aplikacji — pomijam, §5.10);
* nie zmieniam treści poza dodatkami z §5; fraza „zwykle tego samego dnia” — **nie
  potwierdzona przez właściciela** → zostaje obecne „Odpowiadam na każde zgłoszenie.”;
* nie ruszam backendu ani migracji; bez AI.

## Bramki przed przekazaniem
`npm run build` (budżet JS), E2E `strona-publiczna.spec.ts` 4/4, a11y (`test_a11y.mjs`
obejmuje `/`?) — sprawdzę i dołożę kontrole strony publicznej jeśli ich nie ma; ruff,
pełny pytest backendu, Core 275, `tools/spojnosc.py`; zrzuty w PR. Nie scalam — decyzja
właściciela (prompt §0.5).

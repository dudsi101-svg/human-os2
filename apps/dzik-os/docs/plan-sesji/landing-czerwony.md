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

---

# Domknięcie PR #67 (zlecenie 3 z pakietu 14.09) — rezerwacja 0.72.0

**Stan wejściowy:** PR #67 na `dfb35e9` (baza `cbfa893` = 0.64.0); `main` poszedł do
0.69.0 (#68 ukryj kreator, #69 wymiany v2, #71 rozpoznanie wywiadu). Scalenie
`origin/main` → jeden konflikt (`frontend/package.json` 0.65.0 vs 0.69.0; wzięta wersja
z `main`, numer tego PR-a osobnym commitem „Wersja 0.72.0”), `styles.css` scalił się sam
(style Postępów z `main` obecne obok bloku `.landing--czerwony`), zero markerów.

**Rezerwacja:** wersja **0.72.0** — korekta integratora względem prompta (0.70.0):
0.70.0 = PR #70 „powitanie po pierwszym logowaniu”, 0.71.0 = zlecenie 1 „dni treningowe”
(równolegle), 0.68.0 zostaje zarezerwowane jak w CHANGELOG 0.69.0. Wersja w sześciu
miejscach: `frontend/package.json`, `backend/pyproject.toml`, `backend/dzik_os/__init__.py`,
`docs/CHANGELOG.md`, `README.md`, `docs/RELEASE_STATUS.md`. Migracja: brak. Backend: tylko
`__version__`. **Pliki integracyjne** (jedyny piszący, KOORDYNACJA §0): CHANGELOG (sekcja
0.72.0 na górze), STAN_PRZEKAZANIA §1/§2, RELEASE_STATUS, DOSTEPNOSC, `docs/zlecenia/README.md`
(tabela rezerwacji), ten plan; KOORDYNACJA, KONSULTACJE, `db.py`, `tools/` nietknięte.

## Odstępstwa / decyzje domyślne (brak odpowiedzi właściciela → domyślne z prompta)

| # | Pytanie | Przyjęte | Gdzie |
|---|---|---|---|
| 10 | Kontrast: wariant A czy B | **A**: token `--l-border-ui` #B3878A dla obrysu przycisków ghost i pól (1,50 → 3,11); numery kroków na kaflu koralowym w grafit `--l-graphite-deep` (biel: 6,13 / 2,80 / 1,48 → grafit: 3,14 / 6,87 / 12,96 wzdłuż gradientu). Karty i separatory zostają na #ECE4E4/#E0CFCF | `styles.css` |
| 11 | Cztery odstępstwa treściowe z opisu PR | jak w PR (dwa wiersze kontaktu, notka o zdrowiu w lewej kolumnie, etykieta „O trenerze” + h2 z nazwiskiem); „zwykle tego samego dnia” **nie wchodzi** bez potwierdzenia trenera | `Landing.tsx` |
| 12 | Znak marki (dzik limonka → czerwień) | **(a)** czerwień = nowy znak; strona zostaje w czerwieni, **etap 2** (`og.png`, ikony PWA, `logo-full.png`, `/login`, `theme-color` jasny) = osobne zlecenie po scaleniu #67 — nic z tego nie weszło do tego PR-a | — |
| 13 | Numer wersji | **0.72.0** (integrator) | 6 miejsc |
| 14 | Treść kart syntetycznych w hero | **niepotwierdzona — nie zgaduję**: treść bez zmian, każda karta dostała etykietę „przykład” (`.landing-panel__demo`, kontrast 9,79), panel nadal `aria-hidden`; E2E liczy trzy etykiety | `Landing.tsx`, `styles.css` |
| §8 | Zdanie o motywie w sekcji Aplikacja | „Motyw wybierasz sam: ciemny na siłownię albo jasny czerwono-biały.” (decyzja z trzeciej tury 14.09); zrzuty galerii zostają ciemne do jasnego kompletu | `Landing.tsx` |
| P1-3 | Semantyka nagłówków | zostaje: etykieta + h2 „Trzy kroki do pierwszego planu” / „Łukasz Drygiel — Lubelski Dzik”; świadoma zmiana wpisana do CHANGELOG, konspekt h1–h3 pilnowany w E2E; prop `id` w `Naglowek` usunięty | `Landing.tsx` |
| — | Dowody ×2 (pasek + kafle) | celowe; test `toHaveCount(2)` | spec |
| — | Panel hero w pasie 700–899 px | 360 px (prompt: „rozważ”) z plamą 300 / pierścieniem 340 / dzikiem 230 px; h1 przy 768 px z y ≈ 804 na 604 | `@media (max-width: 899px)` |
| — | Poza listą prompta | h1 hero `clamp(40px, 4.4vw, 58px)` — na podglądzie 1024 px przecinek z „prowadzony,” lądował sam w wierszu; pasek dowodów: bez `nowrap` na pozycji i bez `flex-wrap` (w wielowierszowym flexie pozycje spadają do nowego wiersza, zanim się skurczą), `min-width: 0`, etykieta `b` nierozdzielna z `clamp(18px, 1.5vw, 22px)`, podpis zawija się wewnątrz pozycji, „−12 kg” razem; na ≤ 699 px etykieta może się złamać („nawet / −12 kg”), bo inaczej siatka 3 kolumn dawała +4 px przewijania — cztery iteracje z pomiarem (po dodaniu „nawet” trzeci dowód spadał do drugiego wiersza przy 1440, potem pękało „IFBB / PRO”, potem 390 → 394) | `styles.css` |
| — | `fetchpriority` na obrazie LCP | małymi literami przez spread — React 18.3 nie zna `fetchPriority` (React 19 tak); `tsc` czysto | `Landing.tsx` |
| — | Precache SW | świadomy kompromis wpisany do CHANGELOG: oba nowe PNG (+110 kB) w każdej instalacji PWA; nic nie skasowano | — |
| — | Porty E2E | 8097 (własny serwer do zrzutów) i 8098 (Playwright); `playwright.config.ts` liczy port Postępów jako `PORT+1`, zmienna `DZIK_E2E_PORT_POSTEPY` nie jest czytana — stąd nie 8107 | — |
| — | Pytest backendu | pierwszy przebieg bez `PYTHONPATH` importował `dzik_os` z głównego checkoutu (instalacja edytowalna wskazuje `/home/user/human-os2`, nie worktree) i wywracał kolekcję 8 plików; powtórzony z `PYTHONPATH=backend` | — |

**Pytania do właściciela (nadal otwarte):** treść kart hero (14) — zostawić z etykietą
„przykład”, podmienić na prawdziwe liczby, czy usunąć?; znak marki (12) — potwierdzenie
(a), żeby uruchomić etap 2; fraza „zwykle tego samego dnia” (11) — trener potwierdza albo
zostaje bez; kontrast (10) — A wdrożone, B możliwe jedną zmianą tokenu.

## Weryfikacja wykonana (domknięcie)

| Szerokość | `scrollWidth` / `clientWidth` (Chromium, cała strona po przewinięciu) | y `h1` | nawigacja kotwic | zrzut (JPEG ≤ 150 kB) |
|---|---|---|---|---|
| 1440 | **1440 / 1440** | 196 | widoczna, link 39 px wys. | `docs/zrzuty/landing-czerwony/1440.jpg` |
| 1024 | **1024 / 1024** (przed: 1086) | 196 | widoczna, 39 px | `1024.jpg` |
| 768 | **768 / 768** (przed: 772) | 604 (przed ≈ 804) | ukryta | `768.jpg` |
| 390 | **390 / 390** | 465 | ukryta | `390.jpg` |

Zrzuty: pełna strona, Playwright na własnym serwerze E2E (port 8097, seed), PNG → JPEG
przez Pillow w skali 0,5 (390: 0,75), skrypt tymczasowy w `frontend/` usunięty.

**Co obejrzano:** 1440 — hero z panelem i trzema kartami „PRZYKŁAD”, pasek dowodów w jednym
wierszu, oferta 3×2, kroki z „03” grafitowym na koralu, znak wodny obcięty do sekcji;
1024 — h1 w trzech wierszach bez osieroconego przecinka, nawigacja wyśrodkowana, karty na
panelu; 768 — panel 360 px nad tekstem, kroki w jednej kolumnie, odznaka IFBB PRO na rogu
zdjęcia, czerwony kwadrat odsunięty od krawędzi, galeria 2 kolumny, kontakt w jednej
kolumnie; 390 — panel 290 px, przyciski na całą szerokość, dowody 3 kolumny, oferta w
wierszach. Kliknięte w E2E (Pixel 7): „Zaloguj się” → `/login`, wysyłka zapytania →
potwierdzenie, link RODO → `/prywatnosc` (ciemna), CTA „Umów…” → `#kontakt` pod paskiem,
błąd 429 → `role="alert"`.

**Bramki (z `/home/user/wt/landing`, worktree gałęzi):** wynik w opisie PR #67 i raporcie
końcowym — ruff, pytest backendu, Core 275, `tools/spojnosc.py`, `tsc`, build (budżet
120 kB gzip), `test:helpers`, E2E `strona-publiczna` (telefon), `test_a11y.mjs`,
`test_pwa_offline.mjs`.

**Krok 8 promptu (etap 2: znak w czerwieni wszędzie, motyw aplikacji) — świadomie NIE w tym
PR.**

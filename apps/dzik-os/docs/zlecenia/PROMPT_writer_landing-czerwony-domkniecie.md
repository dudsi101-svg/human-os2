# PROMPT dla sesji piszącej — domknięcie PR #67 „Strona publiczna: wariant czerwono-biały” (gałąź `agent/landing-czerwony`)

> Skopiuj ten plik w całości jako wiadomość do sesji piszącej, która prowadzi PR #67.
> Praca przygotowawcza (scalenie próbne, build, E2E, zrzuty na 4 szerokościach,
> pomiar kontrastu, przegląd diffu) jest **wykonana przez sesję tylko-do-odczytu
> 14.09** — wyniki niżej. Nie powtarzaj rozpoznania; zweryfikuj i wykonaj.

---

Przeczytaj: `/AGENTS.md`, `/CLAUDE.md`, `apps/dzik-os/docs/KARTA_WSPOLPRACY.md`,
`apps/dzik-os/docs/STAN_PRZEKAZANIA.md`, `apps/dzik-os/docs/KOORDYNACJA.md`,
`apps/dzik-os/docs/ZASADA_URUCHOMIENIA.md`, `apps/dzik-os/docs/plan-sesji/landing-czerwony.md`.

**Rola:** aktywny piszący, kontynuacja **istniejącej** gałęzi `agent/landing-czerwony`
i PR #67 (nie nowa gałąź). Jako jedyny piszący możesz teraz dotknąć plików
integracyjnych (KOORDYNACJA §0) — wpisy zaproponowane w opisie PR wchodzą do repo.
Pracujesz WYŁĄCZNIE w `apps/dzik-os/`. Bez force-pusha; commity po polsku, bez nazw
modeli AI. Nie scalasz PR-a.

## 0. Stan na 14.09 (zmierzone, nie oszacowane)

| Co | Stan |
|---|---|
| PR #67 | otwarty, gotowy do przeglądu, CI 8/8 zielone na `dfb35e9`, 0 recenzji |
| Baza | `cbfa893` (main 0.64.0). **`main` poszedł dalej:** `860035d` = 0.66.0 (monitoring, PR #61), migracja 36 |
| Próbne scalenie `origin/main` → gałąź (katalog roboczy poza repo) | **jeden konflikt: `frontend/package.json` (0.65.0 vs 0.66.0)**; `styles.css` scala się automatycznie, bez markerów; style Postępów z `main` obecne |
| Po scaleniu (wersja tymczasowo 0.66.0) | `tsc` czysto; `npm run build` OK, **92,1 kB gzip / budżet 120 kB**; precache SW zawiera `boar-mark-red.png` i `boar-hero-red.png`; E2E `strona-publiczna.spec.ts` **4/4** (projekt `telefon`, serwer E2E z seedem) |
| Zrzuty 1440 / 1024 / 768 / 390 (pełna strona, po przewinięciu) | 1440 i 390: bez przewijania poziomego, 1 `h1`, wszystkie `img` z `alt`. **1024: `scrollWidth` 1084 (+60 px)**. **768: `scrollWidth` 772 (+4 px)**. Obrazy `loading="lazy"` ładują się poprawnie (puste pola w pierwszym zrzucie były artefaktem zrzutu bez przewinięcia — nie błędem) |

## 1. Krok 1 — dociągnij `main` i nadaj wersję

```bash
git fetch origin && git merge origin/main      # konflikt tylko w frontend/package.json
```
Wersja **wg kolejności scalania z `docs/zlecenia/README.md`** (kontrola `changelog`
wymaga wersji rosnących w kolejności scalania): domyślnie **0.68.0** (po PR #68
„ukryj kreator” 0.67.0). Jeśli właściciel scali ten PR **przed** #68 — 0.67.0, a #68
przesuwa się (to draft, koszt zmiany jednej liczby). **Wersja żyje w sześciu
miejscach i poprzednie rundy podnosiły wszystkie naraz** (0.66.0 jest dziś w każdym):
`frontend/package.json`, `backend/pyproject.toml`, `backend/dzik_os/__init__.py`
(`__version__`), `docs/CHANGELOG.md` (nowy nagłówek `## X.Y.Z — data`), `README.md`
aplikacji i `docs/RELEASE_STATUS.md` (kontrola „wersje dokumentów” w `spojnosc.py`
wymaga, żeby oba wspominały bieżącą wersję z CHANGELOG-a). PR dziś podnosi tylko
`package.json` — uzupełnij pozostałe pięć w jednym commicie „Wersja X.Y.Z”.

## 2. Krok 2 — poprawki z pomiaru (P1, wykonać)

| # | Objaw (zmierzony) | Przyczyna (`styles.css`, blok `.landing--czerwony`) | Poprawka |
|---|---|---|---|
| P1-a | **1024 px: strona przewija się poziomo o 60 px** | `.landing-panel` (l. ~715) ma `overflow: hidden` **tylko** w `@media (max-width: 699px)` (l. ~863); dekoracje `.landing-panel__blob` 440 px i `.landing-panel__ring` 520 px są centrowane i wystają z panelu węższego niż 520 px | dekoracje (plama, pierścień, raster, „LUBELSKI DZIK”) przenieś do wewnętrznej warstwy `.landing-panel__scene { position:absolute; inset:0; overflow:hidden; border-radius: inherit }`, a karty-powiadomienia zostaw poza nią (mają wystawać). Alternatywa minimalna: `.landing-hero { overflow-x: clip }` (nie `hidden` — nie ucina cieni pionowo) |
| P1-b | **768 px: +4 px przewijania**; odznaka „IFBB PRO / RAPTOR GYM” oderwana od zdjęcia i przy prawej krawędzi ekranu | `.landing-about__badge { position:absolute; right:-22px; bottom:-22px }` (l. ~767) — przy jednej kolumnie kontener zdjęcia ma pełną szerokość, więc `-22px` wychodzi poza viewport | w `@media (max-width: 899px)`: `right: 12px; bottom: 12px` (odznaka wewnątrz zdjęcia) albo `position: static; margin-top: 12px` |
| P1-c | **Cele dotyku < 24 px** w nawigacji kotwic (Oferta / Jak zaczynamy / Aplikacja / Trener / FAQ) na 1440 i 1024 — WCAG 2.2 **2.5.8** (AA) | `.landing-top__nav a` (l. ~697): `font-size: 15px`, brak paddingu → wysokość ~18 px | `padding: 8px 6px; display: inline-block` (wysokość ≥ 24 px); link „informacja o przetwarzaniu danych” w stopce to link w zdaniu — wyjątek 2.5.8, zostaw |
| P2 | `.wm` (znak wodny 220 px) i `.wm--kontakt` wystają z sekcji — obcięte przez `overflow:hidden` sekcji, **nie** powodują przewijania | — | bez zmian; upewnij się, że oba rodzice mają `overflow:hidden` po Twojej zmianie |

Po poprawkach dołóż do `strona-publiczna.spec.ts` asercję `scrollWidth <= clientWidth`
także dla viewportu **1024×800 i 768×1024** (jeden test z pętlą po trzech
szerokościach — dziś jest tylko 390).

## 3. Krok 3 — kontrast: decyzja właściciela z policzonymi wartościami

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

## 4. Krok 4 — treść: potwierdzenia właściciela (z opisu PR)

1. „Wolisz bezpośrednio? Zadzwoń… albo napisz…” → dwa wiersze kontaktu z tymi samymi
   linkami. *Domyślnie: zostaje jak w PR.*
2. Notka o zdrowiu przeniesiona z formularza do lewej kolumny, widoczna także po
   wysłaniu. *Domyślnie: zostaje.*
3. „Odpowiadam na każde zgłoszenie — zwykle tego samego dnia.” — **niepotwierdzone**;
   w PR jest „Odpowiadam na każde zgłoszenie.” *Domyślnie: bez „zwykle tego samego
   dnia”, dopóki trener nie potwierdzi.*
4. „O trenerze” jako etykieta, nazwisko jako `h2`. *Domyślnie: zostaje.*

## 5. Krok 5 — znak marki (adnotacja na kanwie, nierozstrzygnięta w PR)

Kanwa „Dzik OS — wariant jasny” ma adnotację: *„Dzik w logo przebarwiony z limonki na
czerwień (#E11D2E). To zmiana znaku marki — do potwierdzenia z właścicielem przed
wdrożeniem.”* PR #67 używa czerwonego dzika **tylko na stronie publicznej**; ikony
PWA, `logo-full.png`, `og.png`, aplikacja po zalogowaniu — nadal limonka. Do czasu
decyzji strona i aplikacja mają **dwa kolory znaku**.

**Właściciel:** (a) czerwień to nowy znak — wtedy etap 2 (niżej) po scaleniu #67;
(b) znak zostaje limonkowy — wtedy na stronie publicznej dzik wraca do limonki
(`boar-mark.png`/`boar-hero` w wersji limonkowej na czerwonym panelu — sprawdź kontrast
i podeślij zrzut). *Domyślnie: (a), bo właściciel zatwierdził kanwę.*

## 6. Krok 6 — integracja i zamknięcie (teraz wolno)

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

## 7. Weryfikacja przed przekazaniem (z korzenia repozytorium)

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

## 8. Etap 2 — osobne zlecenie po decyzji z kroku 5 (NIE w tym PR)

* **Znak w czerwieni wszędzie:** `og.png` (karta linku), ikony PWA
  (`public/icons/*`, `manifest.webmanifest`, `theme_color`), `logo-full.png`, ekran
  logowania, `<meta name="theme-color">` dla trybu jasnego (PR #67 świadomie pominął).
  Materiały: kanwa ma `boar-red.png` (121 kB) i `boar-mark-red.png`.
* **Motyw aplikacji po zalogowaniu (Dzisiaj/Plan/Dieta/Raport/Więcej + panel
  trenera): NIE MA PROJEKTU.** Kanwa zawiera tylko stronę publiczną (desktop, hero
  telefon, paleta) i archiwalny kierunek zielony. Zanim ktokolwiek dotknie `:root`,
  potrzebna jest kanwa z ekranami aplikacji w wariancie jasnym czerwono-białym
  (min. Dzisiaj i Plan na telefonie, karta klienta trenera na desktopie) i decyzja,
  czy aplikacja przechodzi z ciemnego na jasny — to zmiana dla użytkowników w pilotażu,
  nie kosmetyka. Rekomendacja: najpierw zlecenie projektowe (kanwa), potem prompt.

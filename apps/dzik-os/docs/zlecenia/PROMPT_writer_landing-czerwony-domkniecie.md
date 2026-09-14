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

## 2. Krok 2 — poprawki z pomiaru (P1, wykonać)

| # | Objaw (zmierzony) | Przyczyna (`styles.css`, blok `.landing--czerwony`) | Poprawka |
|---|---|---|---|
| P1-a | **900–1150 px: strona przewija się poziomo** (zmierzone: 900 px → `scrollWidth` 1024, panel hero ściśnięty do **235 px**; 1024 px → 1086; 1100 px → 1124) | dwie przyczyny naraz: (1) `.landing-hero__grid { grid-template-columns: 1fr 1fr }` — `1fr` to `minmax(auto,1fr)`, a `.landing-proof__item { white-space: nowrap }` wymusza 581 px na kolumnę tekstu, więc panel się kurczy; (2) `.landing-panel` (l. ~715) ma `overflow: hidden` **tylko** w `@media (max-width: 699px)` (l. ~863), a `.landing-panel__ring` 520 px / `.landing-panel__blob` 440 px są centrowane i wystają | (1) `grid-template-columns: minmax(0,1fr) minmax(0,1fr)` + `.landing-proof { flex-wrap: wrap }` (albo bez `nowrap`); (2) dekoracje (plama, pierścień, raster, „LUBELSKI DZIK”) do wewnętrznej warstwy `.landing-panel__scene { position:absolute; inset:0; overflow:hidden; border-radius:inherit }`, karty-powiadomienia poza nią (mają wystawać) |
| P1-b | **700–899 px: +4 px przewijania**; odznaka „IFBB PRO / RAPTOR GYM” ok. 70 px na prawo od zdjęcia, nad pustym tłem; czerwony kwadrat `foto-bg` przy samej krawędzi ekranu | `.landing-about__badge { position:absolute; right:-22px; bottom:-22px }` (l. ~767) i `.landing-about__foto-bg { left:-18px }` — w bloku `@media (max-width: 899px)` siatka „O trenerze” spada do jednej kolumny, ale `.landing-about__foto-wrap` dostaje pełną szerokość bez marginesu (reguła `margin: 18px 22px 22px 18px` jest dopiero w ≤699) | w bloku 899: `.landing-about__foto-wrap { max-width: 480px; margin: 18px 22px 22px 18px }` (odznaka wraca na róg zdjęcia, kwadrat odsuwa się od krawędzi) |
| P1-c | **Cele dotyku < 24 px** w nawigacji kotwic (Oferta / Jak zaczynamy / Aplikacja / Trener / FAQ) na 1440 i 1024 — WCAG 2.2 **2.5.8** (AA) | `.landing-top__nav a` (l. ~697): `font-size: 15px`, brak paddingu → wysokość ~18 px | `padding: 8px 6px; display: inline-block` (wysokość ≥ 24 px); link „informacja o przetwarzaniu danych” w stopce to link w zdaniu — wyjątek 2.5.8, zostaw |
| P2 | `.wm` (znak wodny 220 px) i `.wm--kontakt` wystają z sekcji — obcięte przez `overflow:hidden` sekcji, **nie** powodują przewijania | — | bez zmian; upewnij się, że oba rodzice mają `overflow:hidden` po Twojej zmianie |

Po poprawkach dołóż do `strona-publiczna.spec.ts` asercję `scrollWidth <= clientWidth`
także dla viewportu **1024×800 i 768×1024** (jeden test z pętlą po trzech
szerokościach — dziś jest tylko 390).

### 2b. Przegląd diffu (3 obszary, wykonany 14.09 na scalonym drzewie — do wykonania w tym PR)

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
* **Motyw aplikacji po zalogowaniu — DECYZJA WŁAŚCICIELA 14.09 (trzecia tura):**
  użytkownik wybiera między kompletnym motywem czarno-zielonym a nowym czerwono-białym;
  nowy musi być kompletny. Osobne zlecenie `PROMPT_writer_motyw-czerwony.md` (po
  scaleniu #67). Podgląd na prawdziwych ekranach już istnieje — tokeny działają.
  **Do wykonania w tym PR (#67):** zdanie „Ciemny motyw aplikacji zostaje: na siłowni ma
  być czytelny, nie jasny.” w `sec-head__desc` sekcji Aplikacja zamień na „Motyw
  wybierasz sam: ciemny na siłownię albo jasny czerwono-biały.” (zrzuty galerii
  zostają ciemne do czasu jasnego kompletu). Rekomendacja: najpierw zlecenie projektowe (kanwa), potem prompt.

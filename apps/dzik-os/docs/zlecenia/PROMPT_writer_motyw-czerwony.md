# PROMPT dla sesji piszącej — „Motyw czerwono-biały” jako drugi, kompletny motyw aplikacji do wyboru przez użytkownika

> Skopiuj ten plik w całości jako pierwszą wiadomość do sesji piszącej. Rozpoznanie,
> blok tokenów i podgląd na prawdziwych ekranach są **wykonane 14.09** przez sesję
> tylko-do-odczytu (wyniki niżej, plik `motyw-czerwony.tokens.css` obok). Zweryfikuj
> i wykonaj; nie powtarzaj rozpoznania od zera.

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

## 1. Decyzja właściciela (14.09.2026, trzecia tura)

> Docelowo użytkownicy będą mogli wybrać między kompletną czarno-zieloną a nową szatą.
> Do tego dążymy. Nowa szata musi być kompletna.

Czyli: **dwa motywy, oba pełne, wybór należy do użytkownika** (klienta i trenera, każdy
dla siebie). Ciemny czarno-zielony zostaje motywem domyślnym marki (§7 pyt. 1); nowy
jasny czerwono-biały ma objąć **każdy ekran** aplikacji, nie tylko stronę publiczną.
Konsekwencja dla PR #67: zdanie „Ciemny motyw aplikacji zostaje: na siłowni ma być
czytelny, nie jasny” na stronie publicznej **schodzi** (zastąpione: „Motyw wybierasz sam:
ciemny na siłownię albo jasny czerwono-biały.”) — wpisane do promptu domknięcia #67.

## 2. Rozpoznanie — stan kodu (zmierzone)

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

## 3. Podgląd wykonany (dowód, że to działa)

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

## 4. Co dokładnie zbudować

### 4.1 Mechanizm
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

### 4.2 Literały do zamiany na tokeny (9 + 1, `styles.css` na `main` 0.66.0)
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

### 4.3 Zapis wyboru
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

### 4.4 Przełącznik w UI
`pages/More.tsx` („Więcej”): sekcja **„Wygląd”** z dwoma dużymi przyciskami-kartami
(podgląd kolorów, nazwa, opis): „Ciemny — czarno-zielony (domyślny, na siłownię)” /
„Jasny — czerwono-biały”. `role="radiogroup"`, klawiatura, `aria-checked`, bez
zapisu przy fokusie (zmiana = klik/Enter). Ten sam blok w panelu trenera („Więcej”
trenera). Na `/login` bez przełącznika (motyw z urządzenia).

### 4.5 Znak, grafiki, strona publiczna
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

### 4.6 Dostępność i dokumenty
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

## 5. Etapy (co czytam → co wytwarzam → jak weryfikuję → nakład)

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

## 6. Czego świadomie NIE robimy
Ikony PWA / favicon / `og.png` / manifest w czerwieni (decyzja o znaku), jasne zrzuty do
galerii landingu, motyw „systemowy” wg `prefers-color-scheme` (pyt. 3), zmiana strony
publicznej poza jednym zdaniem, zmiana ciemnego motywu (musi zostać piksel w piksel).

## 7. Pytania do właściciela (odpowiedz w tej wiadomości albo zostaw domyślne)
1. Motyw domyślny dla nowych kont i niezalogowanych: **ciemny** (marka, siłownia)?
   *Domyślnie: ciemny.*
2. Znak w jasnym motywie: czerwony dzik (`boar-mark-red.png`) tylko wewnątrz jasnego
   motywu, a ikony PWA/og zostają limonkowe do osobnej decyzji? *Domyślnie: tak.*
3. Trzecia opcja „jak w systemie” (`prefers-color-scheme`)? *Domyślnie: nie w v1
   (dwa motywy, jak brzmi decyzja).*
4. Zapis wyboru na koncie (migracja + pole w ustawieniach), czy tylko na urządzeniu?
   *Domyślnie: na koncie i na urządzeniu.*
5. Nazwy w UI: „Ciemny (czarno-zielony)” / „Jasny (czerwono-biały)”? *Domyślnie: tak.*

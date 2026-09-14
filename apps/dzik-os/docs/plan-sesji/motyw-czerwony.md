# Plan sesji: motyw czerwono-biały jako drugi, kompletny motyw aplikacji (0.74.0, migracja 40)

**Gałąź:** `agent/motyw-czerwony` (od `main` = `195d475`, po scaleniu PR #67 — strona
publiczna czerwono-biała 0.72.0). **Rola:** podległa sesja pisząca wyznaczona przez
integratora 14.09.2026 — decyzja właściciela z trzeciej tury 14.09 („Docelowo użytkownicy
będą mogli wybrać między kompletną czarno-zieloną a nową szatą. Nowa szata musi być
kompletna.”), pakiet zleceń 14.09 §8 (zlecenie 4: prompt + plik danych
`motyw-czerwony.tokens.css`). Warunek startu spełniony: `styles.css` na `main` ma blok
`.landing--czerwony`, są `boar-mark-red.png` i `boar-hero-red.png`.

**Uwaga o protokole jednego piszącego:** w chwili startu otwarty jest PR #75 `[WRITER]`
(`agent/cardio-i-rozgrzewka`, 0.73.0, migracja 39, `export_version` 2.1) — ten sam
piszący, równoległe zadanie zgodnie z `KOORDYNACJA.md` §0 (zarządzenie właściciela
z 14.09); integrator wyznaczył tę sesję jawnie z wiedzą o #75. Pliki obu gałęzi są
rozłączne poza wymienionymi niżej plikami współdzielonymi; cardio dodaje nowe ekrany
w `Plan`/`Today`, których ten motyw nie obejmuje — zapisane jako „do domknięcia po
0.73.0” w `docs/motyw/PROGRESS.md`.

## Rezerwacje (KOORDYNACJA §0, sprawdzone na żywo 14.09)

* **wersja 0.74.0** — `CHANGELOG.md` na `main` ma na górze 0.72.0; 0.73.0 = PR #75
  (cardio, gałąź `agent/cardio-i-rozgrzewka`, sekcja już napisana). Sekcja 0.74.0 wchodzi
  NA GÓRĘ; przy scaleniu `main` z 0.73.0 zostaje nad nią (kontrola `changelog`: wersje
  rosnące w kolejności scalania). `package.json` `version` → 0.74.0.
* **migracja 40** (addytywna: `ALTER TABLE notification_settings ADD COLUMN theme
  VARCHAR(20)`). Ostatni wpis w `db.py` na `main` to **38** (dni treningowe); **39 =
  cardio w PR #75** (sprawdzone w gałęzi: `exercise_blocks` + pola cardio) — numer należy
  do #75, nie do tej gałęzi. Do scalenia #75 kontrola ciągu migracji
  (`test_migracje_przenosnosc`) na tej gałęzi widziała lukę 38 → 40 — **#75 scalony
  (`8a71116`) w trakcie rundy, `main` dociągnięty, ciąg 1–40 bez luk.** Pakiet mówił
  „kolejna wolna” — przydział integratora: 40.
* **`export_version`** w `routers/privacy.py` **bez podbicia przez tę rundę** — eksport zrzuca
  wiersz `notification_settings` generycznie (`_rows`), więc kolumna `theme` wchodzi do eksportu
  automatycznie, bez zmiany kształtu; test sprawdza to wprost (po scaleniu cardio = „2.1”).
* **Porty E2E:** 8120 / 8121 (`DZIK_E2E_DIR=/tmp/dzik-e2e-8120`); przy zajętych → 8122/8123.

**Pliki współdzielone (zmieniam jawnie, tylko własne sekcje):** `backend/dzik_os/db.py`
(wpis 40 na końcu), `models.py` (`NotificationSetting.theme`),
`routers/notifications.py` (`SettingsIn.theme`, walidacja, odczyt/zapis), `frontend/src/api.ts`
(`NotificationSettingsData/Update.theme`, `clearSession` — świadomy wyjątek), `styles.css`
(`:root`, nowy blok `html[data-theme="czerwony"]`, zamiana literałów), `components.tsx`
(`Logo`), `Login.tsx` (znak w jasnym motywie), `main.tsx` (ustawienie motywu przed
`createRoot`), `More.tsx` (sekcja „Wygląd”), `index.html` (bez zmian treści —
`theme-color` przełączany w runtime), `package.json` (wersja, `test:helpers`),
`e2e/test_a11y.mjs` (parametr `DZIK_THEME`), `docs/CHANGELOG.md`, `RELEASE_STATUS.md`,
`README.md` (wersja), `DOSTEPNOSC.md`, `PERMISSIONS.md` (pole w istniejącej trasie),
`INSTRUKCJA_KLIENTA.md`, `INSTRUKCJA_TRENERA.md`, `STAN_PRZEKAZANIA.md` §1/§2,
`docs/zlecenia/README.md` (tabela rezerwacji), `backend/tests/test_notifications.py`.

**Pliki nowe:** `frontend/src/theme.ts`, `frontend/src/pages/Wyglad.tsx` (sekcja „Wygląd”
— jeden komponent dla klienta i trenera), `frontend/scripts/test-theme.mjs`,
`frontend/scripts/test-tokeny.mjs`, `frontend/scripts/tsconfig.theme.json`,
`frontend/scripts/zrzuty-motywy.mjs` (narzędzie przeglądu kompletności — zostaje w repo),
`frontend/e2e/motyw.spec.ts`, `docs/motyw/PROGRESS.md`, ten plan.

## Przyjęte domyślne (właściciel nie odpowiedział na §7 promptu — integrator: „bierz domyślne”)

| # | Pytanie | Przyjęte |
|---|---|---|
| 1 | Motyw domyślny dla nowych kont i niezalogowanych | **ciemny** (marka, siłownia) — brak wartości w localStorage i na koncie = ciemny |
| 2 | Znak w jasnym motywie | **czerwony dzik `boar-mark-red.png` tylko wewnątrz jasnego motywu**; ikony PWA, `favicon`, `og.png`, `manifest` zostają limonkowe/ciemne — osobna decyzja o znaku |
| 3 | Trzecia opcja „jak w systemie” (`prefers-color-scheme`) | **nie w v1** — dwa motywy, jak brzmi decyzja |
| 4 | Zapis wyboru | **na koncie i na urządzeniu** (`localStorage["dzik_theme"]` + kolumna `theme` w `NotificationSetting`, migracja 40) |
| 5 | Nazwy w UI | **„Ciemny (czarno-zielony)” / „Jasny (czerwono-biały)”** |

Jeśli właściciel odpowie inaczej: (1) jedna stała w `theme.ts`; (2) podmiana plików PNG +
`manifest`; (3) trzecia wartość typu `Motyw` i `matchMedia` w `odczytajMotyw`; (4) usunięcie
migracji i pola (kod front działa dalej na samym localStorage); (5) dwa napisy w `Wyglad.tsx`.

## Dlaczego zmiana motywu NIE trafia do audytu (D0)

Warstwa 4 modelu użytkownika (`docs/LAYER_4_USER_MODEL_DIGEST.md`, „motyw wyświetlania”)
klasyfikuje preferencję wyglądu jako **D0 — publiczne/neutralne**: nie jest daną zdrowotną,
nie mówi nic o osobie, nie zmienia niczego w relacji trener–klient ani w treściach. Audyt
(`record_event`) istnieje po to, żeby każda istotna zmiana miała autora i powód; zapis
„użytkownik przełączył kolory” nie niesie informacji, którą ktokolwiek musiałby odtworzyć,
a zaśmiecałby historię bezpieczeństwa konta. Dlatego `PUT /api/notifications/settings`
z samym `theme` **nie** emituje `NOTIFICATION_SETTINGS_CHANGED` z nowym payloadem — istniejące
zdarzenie zostaje dla pozostałych pól (bez zmiany zachowania), `theme` nie dokłada ani
zdarzenia, ani pola w payloadzie. Nowa zgoda też nie jest potrzebna (D0).

## Co robimy (etapy → wytwarzam → weryfikacja → nakład)

| Etap | Wytwarzam | Weryfikacja (bramka etapu) | Nakład |
|---|---|---|---|
| 0 plan | ten plan; punkt odniesienia: `grep -nE "#[0-9a-f]{3,6}\|rgba?\(" src/styles.css` poza `:root` i `.landing--czerwony` = **11 literałów** (l. 172 `.btn--danger:hover`, 246 `.nav`, 285 `.alert--error`, 287 `.alert--warn`, 522 `.mmap__body`, 524 `.mmap__region`, 525/531 `--secondary`, 543 `.landing-top`, 951 `.dlaczego`, 996 `.powitanie-tlo`) + 1 „wyspa” semantyczna: `.postepy-slupki .slupek` używa `--accent-ink` jako koloru słupka tła (na bieli zniknąłby) | — | tysiące |
| 1 tokeny | 11 literałów → tokeny (`--danger-soft`, `--warn-soft`, `--nav-bg`, `--landing-top-bg`, `--mmap-body`, `--mmap-region`, `--mmap-secondary`, `--scrim`, `--scrim-strong`, `--shadow-card`, `--bar-muted`) w `:root` z wartościami **identycznymi** jak literały; `:root { color-scheme: dark }`; blok `html[data-theme="czerwony"]` z pliku danych + nowe tokeny; `scripts/test-tokeny.mjs` (0 literałów poza dozwolonymi blokami) | **zrzuty ciemnego przed/po identyczne piksel w piksel** — ten sam skrypt (`zrzuty-motywy.mjs`) na tym samym serwerze E2E z seedem, porównanie `PIL.ImageChops.difference` → `getbbox() is None` dla każdego ekranu; liczby (ekrany × 0 różnic) wpisane niżej | dziesiątki tys. |
| 2 mechanizm | `theme.ts` (`Motyw`, `ustawMotyw`, `odczytajMotyw`, meta `theme-color` #0b0d0f / #FFFFFF), wywołanie w `main.tsx` przed `createRoot`, wyjątek w `clearSession`, `Logo` z dwoma `<img>` (CSS `hidden` wg `data-theme`, bez JS), `Login.tsx` w jasnym: znak + nazwa tekstem (zero nowej grafiki) | `tsc`, build (budżet 120 kB), `scripts/test-theme.mjs` w `test:helpers`; pomiar mignięcia: arkusz jest w `<head>` przed skryptem, atrybut ustawiany przed pierwszym renderem — opis w PROGRESS | dziesiątki tys. |
| 3 zapis konta | migracja 40, `NotificationSetting.theme`, `SettingsIn.theme` (`^(ciemny\|czerwony)$`, 422 inaczej), `GET` zwraca `settings.theme`, `api.ts`, synchronizacja po logowaniu (serwer ma wartość → nadpisuje lokalną) | `test_notifications.py`: walidacja, roundtrip, obcy użytkownik nie widzi cudzego (jak dziś — trasa per `current_user`), eksport zawiera `theme`; macierz dostępu bez nowych tras | dziesiątki tys. |
| 4 UI | `Wyglad.tsx`: sekcja „Wygląd” (radiogroup, dwie karty z podglądem kolorów, `aria-checked`, strzałki, zmiana = klik/Enter/Spacja, bez zapisu przy fokusie) w `More.tsx` dla klienta i trenera; `/login` bez przełącznika | E2E `motyw.spec.ts`: wybór jasnego → `html[data-theme]`, meta, przetrwanie `reload`, wylogowanie/zalogowanie (serwer), trener niezależnie; a11y radiogroup | setki tys. |
| 5 kompletność | `scripts/zrzuty-motywy.mjs` (logowanie, ekrany klienta 375 px i trenera 1280 px, oba motywy, pełna strona) + **przegląd wszystkich ekranów** (publiczne, klient, trener, admin, wspólne, pod-ekrany z zakładek, 0.70.0 dialog powitalny, 0.71.0 dni treningowe, 0.66.0 Postępy/Monitoring, 0.69.0 wymiany) | lista z odhaczeniem w `docs/motyw/PROGRESS.md`; każda „ciemna wyspa” → poprawka w tokenach | setki tys. (największy koszt) |
| 6 dostępność + dokumenty | `DOSTEPNOSC.md` (tabela par jasnego motywu — wartości policzone), `test_a11y.mjs` z `DZIK_THEME` i drugim przebiegiem, instrukcje, CHANGELOG 0.74.0, RELEASE_STATUS, README, PERMISSIONS, STAN_PRZEKAZANIA, `zlecenia/README.md` | a11y w obu motywach; ruff, pełny pytest, Core 275, `spojnosc.py`, `mutacje.py`, `mutacje_bezpieczenstwa.py`, PWA offline | dziesiątki tys. |

**Największy koszt:** etap 5 (przegląd ~60 ekranów w dwóch motywach). Taniej bez utraty
informacji: jeden skrypt Playwright z listą tras per rola, zrzuty pełnej strony do
scratchpadu, przegląd zrzutów po jednym, poprawki zbiorczo w tokenach (nie per ekran).
Bezpiecznik: **3× plan → stop i raport**. Przegląd: 3 recenzentów wsadowo (kontrast/a11y
jasnego motywu z policzonymi parami; regresja ciemnego piksel w piksel + brak literałów;
kompletność ekranów/UX/testy/dokumenty), P0/P1 naprawione przed przekazaniem, P2 do
`docs/motyw/PROGRESS.md`.

**axe-core:** zainstalowany (`axe-core@4.13.0`, devDependency — poza bundlem, budżet
92,9 kB bez zmian; a11y w obu motywach ≈ +1 min CI). Pierwsze obowiązkowe uruchomienie
złapało `scrollable-region-focusable` na wstędze rekordów w Postępach (dług 0.66.0) —
naprawione w tej rundzie (`role="region"` + `tabIndex=0`). Kontrast i tak policzony
ręcznie (tabela w `DOSTEPNOSC.md`), bo axe liczy tylko to, co widzi na 7 ekranach.

## Bramka etapu 1 — wynik (uzupełniane w trakcie)

Porównanie programowe (`PIL.ImageChops.difference(a, b).getbbox()`), Chromium Playwright,
`reducedMotion: reduce`, ten sam seed, te same trasy i rozmiary:

* **Podejście 1** (dwa osobne serwery/seedy, przed → po): 35/58 identycznych; różnice =
  znaczniki czasu seedu (15:09 vs 15:14), hashe zdarzeń, kolejność sesji — plus **jedna
  prawdziwa regresja**: `:root { color-scheme: dark }` z prompta zmieniał natywne
  kontrolki („Choose File”, checkbox, pasek przewijania). **Zdjęte.**
* **Podejście 2 — tryb A/B** (`DZIK_ZRZUTY_AB` w `zrzuty-motywy.mjs`: jeden serwer, jeden
  seed, podmiana zawartości serwowanego `dist/` per ekran, SW zablokowany, czekanie na koniec
  animacji): **58 ekranów, 55 identycznych co do bajta, 3 różne** — `admin-panel` (łańcuch
  audytu urósł o zdarzenia z wizyty `przed`), `klient-raport` („Przywrócono wersję roboczą”
  z `sessionStorage` po pierwszej wizycie), `pub-strona` (obrazy `lazy` niezdekodowane przy
  pierwszej wizycie). Każda obejrzana jako wycinek przed|po — żadna nie jest różnicą CSS.
* Migracja 40 przy luce 39: `test_migracje_przenosnosc::test_numery_migracji_sa_unikalne_i_rosnace`
  wymaga ciągu bez luk — na tej gałęzi czerwony do scalenia #75 (pełny pytest rundy
  uruchomiony z jawnym `--deselect` tego testu; `test_db_migracje` dopuszcza luki).

## Czego świadomie NIE robimy

* Ikony PWA / `favicon` / `og.png` / `manifest.webmanifest` w czerwieni (decyzja o znaku —
  manifest i tak nie jest per użytkownik, zostaje ciemny).
* Jasne zrzuty do galerii strony publicznej (`public/screens/*.jpg` zostają ciemne).
* Motyw „systemowy” wg `prefers-color-scheme`.
* Zmiana strony publicznej `/` (ma własną paletę `.landing--czerwony`, niezależną od
  `data-theme` — jest publiczna, nie ma użytkownika); `/prywatnosc` dzieli klasy `.landing*`
  z blokiem bazowym i w jasnym motywie przełącza się przez tokeny.
* Zmiana ciemnego motywu — **musi zostać piksel w piksel**.
* Ekrany cardio (0.73.0, PR #75) — nie istnieją na tej gałęzi; przegląd po scaleniu obu.
* Nowa kontrola w `tools/spojnosc.py` (plik integracyjny, inna runda) — kontrola literałów
  jest testem w `test:helpers`.
* Core `hos_engine/`, `tests/` w korzeniu — nietykalne.

## Odstępstwa od planu

* **Restart kontenera w trakcie rundy** (po etapie 6, przed końcowymi bramkami):
  praca była w worktree z 4 niewypchniętymi commitami; dokończenie = wypchnięcie,
  ponowne przejście wszystkich bramek na `2b12ed6`+, przegląd, opis PR. Kod z etapów
  0–6 nie był przepisywany. Narzędzie mutacyjne przerwane restartem zostawiło
  zmodyfikowany `sheet_import.py` — przywrócony z `git checkout` przed startem.
* `:root` **bez** `color-scheme: dark` (prompt je zakładał) — bramka pikselowa
  wykazała zmianę natywnych kontrolek w ciemnym motywie (PROGRESS).
* `--nav-bg` w jasnym motywie = biel `.94`, nie róż z pliku danych (kontrast 4,75
  zamiast 4,41); `.alert--info` w jasnym tekstem `--danger` (5,72 zamiast 3,92).
* Synchronizacja motywu z konta polem `theme` w odpowiedzi logowania / `/api/auth/me`
  zamiast osobnego `GET` ustawień po zalogowaniu.
* Migracja **40** wymagała scalenia `main` z #75 (39) w trakcie rundy, żeby ciąg
  migracji był bez luk; trzy testy „starej bazy” dostały stub `notification_settings`.
* `export_version` po scaleniu cardio = **2.1** (plan mówił „2.0” przed scaleniem) —
  bez podbicia przez tę rundę; test asertuje 2.1.
* Przegląd 3 recenzentów: narzędzie `Agent` niedostępne w obu sesjach (przed i po
  restarcie) — trzy przejścia tematyczne wykonał piszący (**nieniezależne**), a po
  restarcie powtórzył je na świeżo: (a) 12 par kontrastu przeliczonych niezależnym
  skryptem = tabela w `DOSTEPNOSC.md` co do setnych; (b) `grep` literałów kolorów w
  `src/**/*.{ts,tsx}` poza `Landing.tsx`/`theme.ts` = 0, diff `:root` tylko addytywny;
  (c) ekrany cardio 0.73.0 w skrypcie i w PROGRESS, zrzuty obejrzane (edytor cardio
  z suwakami, Bloki, Dzisiaj z pozycją cardio, „Wygląd”, `/login`), dokumenty —
  2 poprawki P2 (CHANGELOG `export_version` 2.1; cudzysłowy w instrukcji trenera).
* E2E: `npx playwright test motyw nawyki powitanie strona-publiczna cardio
  --project=telefon` uruchomiło **cały projekt `telefon`** (40 testów) — nadzbiór
  zlecenia, wynik zapisany dla całości.

* **Niezależny przegląd PR #76 (po przekazaniu):** P0 brak; dwa P1 naprawione —
  (1) `setSession` synchronizował motyw z nieświeżej kopii użytkownika (rotacja tokenu
  po zmianie hasła / MFA cofała wybór) → synchronizacja tylko w `login`/`verifyMfa`
  + `zapiszMotywWSesji` po udanym PUT w `Wyglad.tsx`, E2E odtwarzający rozjazd
  (mutant bez poprawki: czerwony); (2) wersja backendu `dzik_os/__init__.py` i
  `pyproject.toml` 0.73.0 → 0.74.0. P2: komentarz kontrastu `--text` 18,5:1.

## Weryfikacja wykonana (po restarcie, na `2b12ed6` + poprawki dokumentów)

| Bramka | Wynik |
|---|---|
| `ruff check backend tools` | All checks passed |
| pełny pytest backendu (`PYTHONPATH=.`, bez wykluczeń) | 1926 passed, 1 skipped (14:49) |
| Core `python -m pytest tests -q` (korzeń repo) | 275 passed |
| `tools/spojnosc.py` | czysto — 13 kontroli, 1 uwaga (K-001 otwarte 646 h — sprzed rundy) |
| `tools/mutacje.py` | 17/17 mutacji wykrytych (po przywróceniu: 37 passed) |
| `tools/mutacje_bezpieczenstwa.py` | zabitych 9/9 (oryginały przywrócone) |
| `npx tsc --noEmit -p .` | 0 błędów |
| `npm run build` | `index-*.js` 93,2 kB gzip (budżet 120 kB) |
| `npm run test:helpers` | 156/156 (w tym `test-tokeny.mjs` 4, `test-theme.mjs` 5) |
| E2E Playwright, projekt `telefon` (porty 8120/8121) | 40/40 w 2,5 min — `motyw.spec.ts` 1/1, `cardio.spec.ts` 3/3, nawyki 1/1, powitanie 1/1, strona-publiczna 8/8 |
| `test_a11y.mjs` ciemny / `DZIK_THEME=czerwony` | oba: „Wszystkie kontrole dostępności/responsywności przeszły” (axe-core 4.13.0 wstrzykiwane) |
| `test_pwa_offline.mjs` | „Wszystkie kontrole PWA/offline przeszły” |
| bramka pikselowa ciemnego (tryb A/B) | 58 ekranów: 55 identycznych co do bajta, 3 różnice = stan danych (PROGRESS) |
| przegląd kompletności (`zrzuty-motywy.mjs`) | 58 ekranów bazowych + 6 cardio 0.73.0 + 4 stany dodatkowe, × 2 motywy (`scratchpad/motyw-zrzuty/{oba,cardio,nowe}`) |
| kontrast jasnego motywu | 26 par w `DOSTEPNOSC.md`; 12 przeliczonych ponownie niezależnie — zgodne |
| `git status` po mutacjach | czysty (tylko 4 pliki dokumentów tej rundy) |

## Plan kontra rzeczywistość

* Etapy 0–6 wykonane w zaplanowanej kolejności; największy koszt zgodnie z
  przewidywaniem w etapie 5 (przegląd ekranów), drugi — bramka pikselowa etapu 1
  (dwa podejścia, bo pierwsze mierzyło szum seedu, nie CSS).
* Nieplanowane: (1) scalenie `main` 0.73.0 w trakcie rundy (wymuszone przez ciąg
  migracji) i przegląd 6 ekranów cardio; (2) instalacja axe-core jako devDependency
  i naprawa `scrollable-region-focusable` z 0.66.0; (3) `reducedMotion` w kontekstach
  a11y (axe liczył kontrast w połowie animacji wejścia); (4) restart kontenera —
  bramki końcowe przechodzone dwa razy.
* Nie zrobione, zgodnie z planem: PWA/favicon/og/manifest w czerwieni, jasne zrzuty
  galerii landingu, motyw „jak w systemie”, zmiany strony `/`, kontrola w
  `spojnosc.py`.
* Bezpiecznik 3× planu nie został uruchomiony.

## Weryfikacja po przeglądzie P1 (na commicie poprawki)

`tsc` 0 błędów · build 93,2 kB gzip · `test:helpers` 156/156 ·
`pytest tests/test_notifications.py` 24 passed · `spojnosc.py` czysto (13 kontroli,
1 uwaga sprzed rundy) · E2E `motyw.spec.ts` projekt `telefon` (port 8120) **2/2**;
test rotacji tokenu uruchomiony na mutancie (poprawka cofnięta, build): **czerwony**
(`Expected "czerwony", Received null`) — łapie wadę.

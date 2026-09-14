# Postęp — motyw jasny czerwono-biały jako drugi motyw aplikacji (0.74.0)

Plan: `docs/plan-sesji/motyw-czerwony.md`. Gałąź `agent/motyw-czerwony`, PR #76.

| Etap | Stan | Dowód |
|---|---|---|
| 0 plan | ✅ | plan sesji; punkt odniesienia: 11 literałów poza `:root`/`.landing--czerwony` + 1 wyspa semantyczna (`--accent-ink` jako słupek) |
| 1 tokeny | ✅ | `styles.css` (`:root` + 13 nowych tokenów, blok `html[data-theme="czerwony"]`), `scripts/test-tokeny.mjs` (4 testy); **bramka pikselowa** niżej |
| 2 mechanizm | ✅ | `src/theme.ts`, `main.tsx`, `api.ts` (`setSession` → synchronizacja, wyjątek w `clearSession`), `Logo` (dwa znaki), `Login.tsx`; `scripts/test-theme.mjs` (5 testów) |
| 3 zapis konta | ✅ | migracja 40, `NotificationSetting.theme`, `SettingsIn.theme`, `_user_payload.theme`, `/api/auth/me`; 2 testy w `test_notifications.py` (walidacja, roundtrip, login, obce konto, audyt, eksport) |
| 4 UI | ✅ | `pages/Wyglad.tsx` w `More.tsx` (klient i trener/admin), `e2e/motyw.spec.ts` |
| 5 kompletność | ✅ | `scripts/zrzuty-motywy.mjs`, 60 ekranów × 2 motywy — lista niżej |
| 6 dostępność + dokumenty | ✅ | `DOSTEPNOSC.md` §„Kontrast (motyw jasny)”, `test_a11y.mjs` z `DZIK_THEME` (drugi krok w CI), CHANGELOG, RELEASE_STATUS, PERMISSIONS, instrukcje, STAN_PRZEKAZANIA |

## Bramka etapu 1 — ciemny motyw piksel w piksel (wynik)

Metoda: `scripts/zrzuty-motywy.mjs` w trybie A/B (`DZIK_ZRZUTY_AB`) — **jeden serwer
E2E z jednym seedem**, dla każdego ekranu po kolei podmiana zawartości serwowanego
`dist/` (wariant `przed` = build z `styles.css` z `main` `195d475`, `po` = build po
etapie 1), Chromium, `reducedMotion: reduce`, service worker zablokowany, czekanie
na koniec animacji wejścia; porównanie `PIL.ImageChops.difference(...).getbbox()`.

* **58 ekranów: 55 identycznych co do bajta (bbox = None), 3 różne** — każda różnica
  obejrzana i przypisana do stanu, nie do CSS:
  * `admin-panel` — łańcuch audytu urósł o zdarzenia wygenerowane przez wizytę
    wariantu `przed` (`ADMIN_USER_LIST_ACCESSED`, `ADMIN_RECEIPTS_ACCESSED`);
  * `klient-raport` — druga wizyta pokazuje „Przywrócono wersję roboczą raportu”
    (szkic z `sessionStorage` zapisany przez pierwszą);
  * `pub-strona` — obrazy `loading="lazy"` galerii i zdjęcia trenera niezdekodowane
    przy pierwszej wizycie (druga miała je w cache).
* Pierwsze podejście (dwa osobne serwery/seedy) dawało 35/58 identycznych — pozostałe
  różnice to znaczniki czasu z seedu (15:09 vs 15:14) i hashe zdarzeń; stąd tryb A/B.
* **Wykryte i cofnięte:** `:root { color-scheme: dark }` (z prompta) zmieniał natywne
  kontrolki — „Choose File” w raporcie i wątku, niezaznaczony checkbox w Postępach,
  pasek przewijania okna powitania — czyli **zmieniał ciemny motyw**. Zdjęte;
  `color-scheme: light` zostaje tylko w bloku jasnego motywu. Strażnik pilnuje, żeby
  `:root` nie dostał `color-scheme`.

## Mignięcie motywu przy starcie (pomiar)

Arkusz `styles.css` ładuje się z `<head>` (Vite wstrzykuje `<link rel="stylesheet">`
przed skryptem modułu), a `zastosujMotyw(document, odczytajMotyw())` w `main.tsx`
wykonuje się przed `createRoot(...).render(...)`. Pierwsza farba React jest więc już
we właściwym motywie; jedyny „nagi” moment to pusty `<div id="root">` na tle
`:root --bg` (ciemnym) zanim moduł się wykona — bez treści, więc niewidoczny jako
zmiana treści. Pełne usunięcie (skrypt inline w `index.html`) blokuje CSP
(`script-src 'self'`) — świadomie nie robione.

## Lista ekranów przeglądu kompletności (oba motywy, `scratchpad/motyw-zrzuty/oba`)

Publiczne (5): `/` ✅ (własna paleta `.landing--czerwony`, niezmienna), `/login` ✅
(jasny: znak + nazwa zamiast limonkowego `logo-full.png`), `/prywatnosc` ✅ (blok
bazowy `.landing` przez tokeny: pasek, karty, linki), `/aktywacja` ✅, `/reset-hasla` ✅.

Klient, 375 px (24): Dzisiaj ✅ (powitanie, nawyki, karta celu z poświatą, harmonogram,
raport, płatność, wiadomość „nowa”), Plan ✅ (karta „Twoje dni treningowe” 0.71.0,
selecty, chipy dnia), Plan → panel „Dlaczego?” ✅ (scrim `--scrim`), Dieta ✅ (kafle makro,
suplementacja, plakietki), Postępy ✅ (0.66.0: kafelki, sparkline, słupki `--bar-muted`,
heatmapa, paski grup), Raport ✅ (skale, pole pliku, poprzednie raporty), Więcej ✅
(sekcja „Wygląd”), Więcej → Samouczek ✅ (0.70.0 dialog, scrim `--scrim-strong`), Profil ✅,
Wywiad ✅, Wywiad wstępny ✅, Wywiad kaloryczny ✅, Rozmowa startowa ✅, Ankieta ✅,
Wiedza ✅ (baner demo `--warn`, chipy części, karty „szkic”), Wiedza/ćwiczenia ✅,
Wiedza/produkty ✅, Konsultacje ✅, Wyzwania ✅, Dokumenty ✅, Płatności ✅, Wiadomości ✅,
Wątek ✅ (`.msg--own` biały na czerwieni), Powiadomienia ✅, Zmień hasło ✅.

Trener, 1280 px (28): Klienci ✅ (dashboard, chipy filtrów, plakietki), karta klienta ×11
zakładek ✅ (Profil, Rozmowa startowa, Wywiad, Plan, Dieta, Harmonogram, Raporty, Pomiary,
Monitoring, Płatności, Historia), Szablony ✅, Szablony diet ✅, Wiedza ×4 (Artykuły,
Ćwiczenia, Produkty, Karty) ✅, Wiedza → podgląd ćwiczenia z mapą mięśni ✅ (`--mmap-*`),
Konsultacje ✅, Wyzwania ✅, Rozliczenia ✅, Podsumowanie tygodnia ✅, Monitoring ✅,
Monitoring klienta ✅, Wiadomości ✅, Powiadomienia ✅, Więcej ✅ (Wygląd, push, MFA, sesje,
historia bezpieczeństwa).

Admin, 1280 px (2): panel (konta, łańcuch audytu) ✅, Więcej ✅.

Nieobjęte tym przeglądem (jawnie): wymiany produktów 0.69.0 w `DietaSzablon.tsx` —
seed E2E nie ma przypisanej diety z szablonu dla klienta A (ekran „Dieta” pokazuje plan
ręczny); komponent używa wyłącznie klas i tokenów (`grep` literałów w `src/**/*.tsx`: 0
poza `Landing.tsx`), więc przełącza się jak reszta. Kreator dań (`KreatorDan`),
`PlanEditor`, `PrzypiszDiete`, `SzkicPlanu`, `PublikacjaPanel`, `OcrCapture`,
`PlanAssistant`, `FoodCatalog`, `Onboarding` (rozmowa startowa — ✅ jako ekran) — nie
zrzucone jako osobne stany (wymagają danych/interakcji wielokrokowej), ten sam argument:
zero literałów w TSX, wszystkie style przez tokeny.

**Cardio 0.73.0 (PR #75 scalone `8a71116` w trakcie tej rundy — przegląd po scaleniu
`main`, `scratchpad/motyw-zrzuty/cardio`, 6 ekranów × 2 motywy):** Szablony → Bloki ✅
(katalog bloków, plakietki, „Dodaj wbudowane”), karta klienta → Plan → „+ Nowy plan” →
„+ Cardio” ✅ (panel suwaków: `input[type=range]` z `accent-color: var(--accent)`,
kłódki, urządzenia, kwalifikacja zdrowotna), Plan klienta z pozycją cardio z seedu ✅,
„Dlaczego takie cardio?” ✅ (dialog, scrim), Dzisiaj ✅, Plan trenera ✅. `styles.css`
z cardio nie dodał żadnego literału koloru (strażnik `test-tokeny.mjs` zielony po
scaleniu); `pozycje.tsx`, `CardioPanel.tsx`, `BlokiTab.tsx`, `suwaki.ts` — zero literałów.

## Kontrast — patrz `docs/DOSTEPNOSC.md` §„Kontrast (motyw jasny czerwono-biały)”

Korekty wynikające z policzenia: `--nav-bg` biel `.94` zamiast różu (aktywna pozycja
`--accent` 4,75 zamiast 4,41); `.alert--info` w jasnym motywie tekstem `--danger`
(#B3121F na #FDE3E5 = 5,72; `--accent` dawał 3,92).

## Przyjęte domyślne (pyt. §7 prompta)

ciemny domyślny · czerwony dzik tylko w jasnym motywie (PWA/og/manifest limonkowe) ·
bez „jak w systemie” · zapis na koncie i urządzeniu · „Ciemny (czarno-zielony)” /
„Jasny (czerwono-biały)”.

## Decyzje wykonawcze i odstępstwa od prompta

* `:root` **bez** `color-scheme: dark` (bramka pikselowa — patrz wyżej).
* `--nav-bg` w jasnym = biel `.94`, nie `rgba(251,245,245,.92)` z prompta (kontrast).
* Migracja **40** po 39 (cardio): do scalenia `main` `test_migracje_przenosnosc` (ciąg bez
  luk) był czerwony — po scaleniu `8a71116` ciąg 1–40 bez luk, pełny pytest bez wykluczeń.
  Trzy testy „starej bazy” (`test_migracja_23/22`, `test_migration_19`) dostały stub
  `notification_settings` (jak stub `workout_entries` dla 39).
* Synchronizacja motywu z konta idzie polem `theme` w odpowiedzi logowania
  (`_user_payload`, `/api/auth/me`), nie osobnym `GET` ustawień po zalogowaniu —
  jedna odpowiedź mniej na starcie; `Login.tsx` i tak przeładowuje stronę.
* Sam motyw w `PUT /api/notifications/settings` **nie** emituje
  `NOTIFICATION_SETTINGS_CHANGED` (D0); pozostałe pola — jak dotąd.
* **axe-core zainstalowany** (`axe-core@4.13.0`, devDependency, poza bundlem — budżet bez
  zmian; a11y w obu motywach ≈ +1 min CI). Pierwszy obowiązkowy przebieg złapał
  `scrollable-region-focusable` na wstędze rekordów w Postępach (dług 0.66.0) — naprawione
  (`role="region"` + `tabIndex=0` w `PanelPostepow.tsx`). Kontrast dodatkowo policzony
  ręcznie (`DOSTEPNOSC.md`).
* Przegląd 3 recenzentów: narzędzie `Agent` niedostępne w tej sesji — trzy przejścia
  (kontrast/a11y, regresja ciemnego + literały, kompletność/UX/testy) wykonał piszący
  jako osobne czytania z listą kontrolną; **to nie jest niezależna recenzja** — patrz
  sekcja niżej.

* **Restart kontenera po etapie 6:** bramki końcowe (pełny pytest, mutacje, E2E,
  a11y ×2, PWA) przeszły ponownie po restarcie na `2b12ed6` — wyniki z liczbami
  w planie sesji §„Weryfikacja wykonana”. Przy okazji dwie poprawki P2 w dokumentach
  (`export_version` 2.1 w CHANGELOG, cudzysłowy w instrukcji trenera).

## P2 / do rozważenia (nie blokują)

* Ciemne natywne kontrolki w ciemnym motywie (`color-scheme: dark`) — zmiana wyglądu,
  decyzja właściciela (dziś „Choose File” i checkboxy są jasne, jak od zawsze).
* Ikony PWA, `favicon`, `og.png`, `manifest.webmanifest` (`theme_color`/`background_color`)
  w czerwieni — decyzja o znaku (etap 2 z PR #67); manifest nie jest per użytkownik.
* Jasne zrzuty do galerii strony publicznej (`public/screens/*.jpg`).
* Opcja „jak w systemie” (`prefers-color-scheme`) — trzecia wartość typu `Motyw`.
* `Logo` renderuje dwa `<img>` (drugi `display: none`) — Chromium pobiera oba pliki
  (~5 kB, w precache SW); `<picture>` nie umie warunkować po atrybucie `data-theme`.
* Szkic raportu w `sessionStorage` powstaje już przy samym wejściu na pusty formularz
  (widać w bramce A/B) — dług sprzed rundy, poza zakresem.
* (zrobione po scaleniu) ekrany cardio/rozgrzewki 0.73.0 przejrzane w obu motywach — patrz
  lista wyżej.

## Przegląd wewnętrzny (trzy przejścia, zasady v2 §3)

**(a) kontrast/a11y jasnego motywu** — policzone 26 par (tabela w DOSTEPNOSC.md); dwie
poprawki (nawigacja, alert info); grupa radiowa: `role=radiogroup` + `aria-labelledby`,
`role=radio` + `aria-checked`, roving tabindex, strzałki/Home/End = fokus, Enter/Spacja =
wybór; status zapisu w `role=status`; próbki `aria-hidden`; blok logowania w jasnym
`aria-hidden` (nazwa marki jest w `h1.sr-only`). P1: brak. P2: obrys pola na `--bg-raised`
2,89 (na sąsiedniej bieli karty 3,11) — zapisane w tabeli.
**(b) regresja ciemnego + literały** — bramka A/B 55/58 + 3 wyjaśnione; strażnik
`test-tokeny.mjs` z testem psującym (wstrzyknięty literał → czerwony); `git diff` bloku
`:root`: tylko dodane tokeny, żadna dawna wartość nie zmieniona. P0/P1: brak.
**(c) kompletność/UX/testy/dokumenty** — 60 ekranów × 2 motywy obejrzane (lista wyżej);
P1 naprawione w trakcie: `.postepy-slupki .slupek` (`--accent-ink` = biel na bieli →
`--bar-muted`), `.landing-top` na `/prywatnosc`; E2E strict-mode „Wyloguj” u trenera
(dwa przyciski z tym słowem) → `exact: true`. P2 wyżej.

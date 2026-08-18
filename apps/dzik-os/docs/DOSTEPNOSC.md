# Dostępność i responsywność — Dzik OS

Stan po rundzie 0.15.0 (2026-08-18). Punkt odniesienia: **WCAG 2.2 AA**
(bez formalnego audytu zewnętrznego — patrz „Pozostałe ograniczenia").

## 1. Co jest spełnione

### Responsywność (320 / 375 / 768 / 1024 / szeroki desktop)

* **Brak poziomego scrolla strony** na wszystkich kluczowych ekranach od
  320 px wzwyż (kontrolowane testem e2e). Wiersze (`.row`) łamią się
  zamiast wypychać stronę w bok; pola w kontenerach flex mają
  `min-width: 0`.
* **Formularze wielokolumnowe** (`.field-row`, `.field-row-3`) schodzą do
  jednej kolumny poniżej 460 px. Wyjątek: pary naprawdę krótkie i czytelne
  obok siebie (`.field-row--keep` — np. porównywarka zdjęć „przed / po",
  wiersze serii kg × powtórzenia).
* **Tabele** (`table.simple`): każda jest w kontenerze
  `.table-wrap` (kontrolowany `overflow-x: auto`), a z klasą
  `.table--cards` poniżej 620 px zamienia się w karty wierszy —
  nagłówki kolumn stają się etykietami danych (`td::before` z
  `data-label`), thead pozostaje dostępny dla czytników (ukryty
  wizualnie). Dotyczy: historia wersji planu/diety, płatności (klient
  i trener), profil z proweniencją, konta w panelu admina.
* **Breakpointy**: 460 px (kolumny formularzy), 620 px (tabele-karty),
  700 px (większe odstępy, stat-grid i photo-grid 4 kolumny), 900 px
  (nawigacja przenosi się na górę), 1200 px (szerszy `.page--wide`
  dla panelu trenera/admina).
* **Ekran logowania na niskich ekranach** (landscape telefonu,
  `max-height: 640px`): logo zmniejszone (`clamp(64px, 22vh, 110px)`),
  układ od góry — formularz osiągalny bez walki z układem.

### Rozmiary dotykowe i typografia

* `.btn` ma `min-height: 44px`; `.btn--small` 38 px na wskaźnikach
  precyzyjnych i **44 px na ekranach dotykowych** (`pointer: coarse`,
  także `.tabs button` i nagłówki rozwijane w bazie wiedzy). Linki
  dolnej nawigacji wypełniają cały pasek (62 px wysokości, test e2e
  sprawdza ≥ 44×44 px). Checkboksy/radio 20×20 px, suwaki z wyższym
  uchwytem (28 px).
* **Żadnego tekstu poniżej 12 px**: etykiety nawigacji podniesione z
  ~10,5 px (0.66 rem) do 12 px (0.75 rem); podpisy suwaków i metadane
  wiadomości również do 0.75 rem.

### Kontrast (ciemny motyw marki)

* Tekst przygaszony `--text-dim` (#97a1ab) na kartach: ~6,4:1 (AA także
  dla małego tekstu).
* Kolory statusów (`--danger`, `--warn`, `--ok`, akcent #b3f23e) na tłach
  aplikacji: > 4,5:1; tekst na akcentowych przyciskach (`--accent-ink` na
  limonce): ~13:1.
* Obrysy elementów interaktywnych (`--border-strong`) podniesione z
  rgba(255,255,255,0.14) do **0.34** — ok. 3:1 względem tła karty
  (WCAG 1.4.11 dla granic komponentów: pola, przyciski ghost, taby).

### Semantyka i struktura

* `html lang="pl"`, viewport **bez** `maximum-scale`/`user-scalable=no`
  (powiększanie nie jest blokowane).
* **Landmarki**: `<main id="main">` wokół treści trasy, `<nav
  aria-label="Główna nawigacja">`; **skip-link** „Przejdź do treści" jako
  pierwszy element w porządku fokusu (widoczny po fokusie).
* **Nagłówki bez przeskoków**: h1 = tytuł strony (TopBar; na ekranie
  logowania sr-only), h2 = karty/sekcje, h3 = podsekcje (numerowane
  `SectionLabel` renderują się jako h3).
* **Jeden system ikon**: komponent `Icon` w `components.tsx` (własne SVG
  stroke 24×24, ~35 ikon). Emoji pełniące rolę ikon w UI zastąpione
  (nagłówki kart, linki „Więcej", załączniki, mikrofon/stop, timer
  przerwy, pauza/wznów, ostrzeżenia, pobieranie itd.). Emoji w treściach
  pisanych przez ludzi oraz w tekstach powitalnych pozostają.

### Formularze i kontrolki

* **Wszystkie pola mają dostępne etykiety**: `label for`/`id` tam, gdzie
  etykieta jest widoczna; `aria-label` dla pól z samym placeholderem
  (wyszukiwarki, wiersze serii, edytor planu). Kontrolowane testem e2e na
  ekranach logowania, raportu, postępów i bazy wiedzy trenera.
* **Suwaki raportu (1–5)**: label for/id, `aria-valuetext`
  („4 na 5 (niska–wysoka)"), podpowiedź skali przez `aria-describedby`.
* **Przyciski oceny 1–5** (panel trenera): `role="group"` z etykietą,
  `aria-pressed` i nazwa „Ocena n na 5" na każdym przycisku. Ten sam
  wzorzec: wybór dni tygodnia (ankieta, harmonogram), chipy filtrów listy
  klientów, przełącznik archiwum.
* **Zakładki** (karta klienta, baza wiedzy trenera i klienta): wzorzec
  WAI-ARIA Tabs — `role=tablist/tab/tabpanel`, `aria-selected`, roving
  tabindex, strzałki ←/→ oraz Home/End przenoszą fokus i wybór.
* Elementy rozwijane (historia wersji, historia bezpieczeństwa, karty
  bazy wiedzy, usuwanie konta, nowy klient) mają `aria-expanded` /
  `aria-pressed`.

### Komunikaty i dynamiczne treści

* Błędy: `ErrorBox` z `role="alert"` (plus przycisk „Spróbuj ponownie").
* Statusy dynamiczne: `role="status"`/`aria-live="polite"` — spinner,
  komunikaty sukcesu, baner aktualizacji PWA, stan pobierania pliku,
  wynik weryfikacji łańcucha audytu.
* **Wykresy** (`Sparkline`): `role="img"` + wygenerowana alternatywa
  tekstowa (nazwa serii, liczba pomiarów, zakres dat i wartości, ostatnia
  wartość). Wykresy siły dodatkowo nazwane per ćwiczenie; select wyboru
  ćwiczenia ma `aria-label`. Paski adherencji są `aria-hidden` — liczby
  (x/y, %) stoją obok jako tekst.
* Załączniki audio/wideo mają `aria-label` z nazwą pliku; miniatury
  zdjęć mają sensowne `alt` (data zdjęcia).

### Klawiatura, fokus, ruch

* Globalny, widoczny wskaźnik fokusu: `:focus-visible` (obrys akcentu);
  pola formularzy dodatkowo z obrysem i poświatą akcentu.
* Cała aplikacja obsługiwalna klawiaturą: brak elementów klikalnych
  niebędących buttonami/linkami; zakładki wg wzorca ARIA; skip-link.
* **Modale**: aplikacja nie ma własnych modali — dialogi potwierdzeń
  używają natywnych `confirm()`/`prompt()` przeglądarki, które same
  przejmują i zwracają fokus oraz obsługują Escape. Punkt „pułapka
  fokusu" jest przez to spełniony wprost (nie ma czego pułapkować);
  gdy powstanie pierwszy własny modal, musi implementować focus trap +
  Escape + zwrot fokusu.
* `prefers-reduced-motion: reduce` wyłącza wszystkie animacje i
  przejścia (globalna reguła w styles.css).

## 2. Jak testować

### Automatycznie

**Ten test chodzi w CI** (job `e2e` w `dzik-os-ci.yml`) — od 0.39.0. Do
tej pory był opisany tutaj, ale żaden przebieg go nie uruchamiał; jedyna
bramka łapiąca poziomy scroll na 320 px stała bezczynnie.

Lokalnie:

```bash
cd apps/dzik-os/frontend && npm run build
cd .. && NODE_PATH=$PWD/frontend/node_modules node e2e/test_a11y.mjs
```

`NODE_PATH` wskazuje na cokolwiek, gdzie stoi pakiet `playwright` —
`node_modules` frontendu albo instalacja globalna (`/opt/node22/lib/node_modules`).

Test uruchamia backend z seedem i Chromium (Playwright). Jeśli w
środowisku dostępny jest pakiet **axe-core**, jest wstrzykiwany i
uruchamiany (WCAG A/AA) na ekranach: logowanie, Dzisiaj, raport, postępy,
baza wiedzy trenera; niezależnie od axe działają własne asercje: lang,
viewport, skip-link, landmarki, etykiety pól, porządek nagłówków, brak
poziomego scrolla (320/375/768/1024), rozmiary nawigacji, suwaki,
wykresy, zakładki z klawiaturą, chipy filtrów, logowanie w landscape.

### Ręczny protokół (klawiatura)

1. `/login`: Tab przechodzi E-mail → Hasło → Zaloguj → „Nie pamiętasz
   hasła?"; fokus zawsze widoczny; Enter wysyła formularz.
2. Po zalogowaniu: pierwszy Tab pokazuje „Przejdź do treści"; Enter
   przenosi fokus za nawigację.
3. Dolna nawigacja: Tab po wszystkich pozycjach, Enter aktywuje; aktywna
   pozycja odróżniona nie tylko kolorem (ikona + stan aria-current z
   NavLink).
4. Raport: suwaki obsługiwane strzałkami (wartość ogłaszana jako
   „n na 5 …"); wysłanie formularza Enterem; błąd pojawia się jako alert
   bez utraty wpisanych danych.
5. Karta klienta (trener): fokus na zakładce, strzałki ←/→ zmieniają
   zakładkę i panel, Home/End skaczą na skraj; Tab wchodzi do panelu.
6. Ocena raportu 1–5: Tab po przyciskach, Enter/Spacja przełącza, stan
   słyszalny jako „naciśnięty".
7. Historia wersji / historia bezpieczeństwa / karty bazy wiedzy:
   przyciski rozwijane ogłaszają zwinięte/rozwinięte.
8. `confirm()`/`prompt()` (cofnięcie zgody, odwołanie terminu…): Escape
   anuluje, fokus wraca do przycisku wywołującego (zachowanie natywne).

### Ręczny protokół (czytnik ekranu — NVDA/VoiceOver)

1. Nawigacja po landmarkach: main, nav („Główna nawigacja").
2. Nawigacja po nagłówkach: h1 (tytuł ekranu) → h2 (karty) → h3
   (sekcje formularza) — bez przeskoków.
3. Wykresy w Postępach: ogłaszana pełna alternatywa tekstowa (zakres,
   liczba pomiarów, ostatnia wartość).
4. Formularz raportu: każda kontrolka ma nazwę; suwak ogłasza wartość
   słownie.
5. Wiadomości: załącznik audio/wideo przedstawia się nazwą pliku;
   przycisk mikrofonu ma nazwę „Nagraj wiadomość głosową".
6. Komunikaty błędu/sukcesu ogłaszane automatycznie (alert/status).

### Ręcznie (responsywność)

Chrome DevTools → Device toolbar: 320, 375, 768, 1024 px + landscape
390×844. Sprawdzić: brak poziomego scrolla, formularze jednokolumnowe
poniżej ~460 px, tabele jako karty poniżej ~620 px, logowanie w
landscape bez przewijania walki o logo, nawigacja czytelna (12 px+).

## 3. Pozostałe ograniczenia (świadome)

* **Brak formalnego audytu** WCAG i testu z użytkownikami czytników —
  powyższe to inżynierska implementacja + testy automatyczne; audyt
  zewnętrzny pozostaje do zlecenia przed deklaracją zgodności.
* **axe-core nie jest zależnością projektu** — test e2e używa go tylko
  wtedy, gdy jest dostępny w środowisku (w CI/sandboxie bez niego
  działają asercje własne). Dodanie `axe-core` do devDependencies to
  proste rozszerzenie.
* **Natywne `confirm()`/`prompt()`** są dostępne, ale nieostylowane pod
  markę; przy przejściu na własne modale trzeba będzie dodać focus trap,
  Escape i zwrot fokusu (dokumentowane wyżej).
* **Krzywe kolorów**: kilka ozdobnych obramowań (`--border` 0.08) celowo
  pozostaje subtelnych — to separatory, nie granice kontrolek.
* Duże tabele w panelu admina na bardzo wąskich ekranach są kartami —
  panel admina projektowany jest przede wszystkim na desktop.
* Etykiety dat na osiach wykresów są tylko skrajne (pierwsza/ostatnia) —
  świadomy minimalizm sparkline; pełne dane są w alternatywie tekstowej
  i liczbach obok wykresu.
* `aria-live` na przycisku pobierania pliku ogłasza zmiany stanu tylko
  w części czytników (wzorzec „przycisk zmieniający własną treść");
  błąd pobrania jest osobnym `role="alert"`, więc kluczowa informacja
  nie ginie.

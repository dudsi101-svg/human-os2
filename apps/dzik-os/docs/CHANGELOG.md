# Changelog — Dzik OS

## 0.5.2 — 2026-08-18

* **Powitanie na ekranie logowania**: pod logo ciepłe zaproszenie
  („Cześć, dobrze Cię widzieć! 💪 Zaloguj się — Twój plan, dieta i
  wiadomości od trenera czekają w jednym miejscu.").
* **PWA — świeża wersja przy każdym otwarciu**: nawigacje przełączone na
  network-first (cache tylko jako fallback offline) — użytkownik nie
  utknie już na starej wersji aplikacji do czasu kliknięcia banera;
  otwarcie/odświeżenie to naturalny moment aktualizacji, więc zasada
  „bez cichej podmiany kodu w trakcie sesji" pozostaje zachowana.
  Statyki nadal cache-first; /api nigdy nie jest cachowane. Cache
  podbity do v2.

## 0.5.1 — 2026-08-18

* **Duże logo na ekranie logowania**: pełna grafika marki (głowa dzika +
  wordmark „DZIK OS") w wysokiej rozdzielczości (900 px, spłaszczona
  paleta — 59 KB) zamiast małej ikonki z tekstem; napis „DZIK"
  przebarwiony na jasny wariant do ciemnego tła (czarny znikał na
  czarnym), „OS" pozostaje zielone. Znak nawigacji podbity do 512 px
  (ostrość na ekranach retina).
* **Symulowani klienci demo (C–E)** — panel trenera od razu pokazuje
  realną pracę: Marek Dziczek (raport czeka na ocenę + nieprzeczytana
  wiadomość), Anna Wilk (praca trenera wykonana: raport oceniony 4/5,
  odpowiedź w wątku, płatność opłacona, trend −2 kg), Piotr Zając
  (brak raportu, przeterminowana płatność, niepokojąca obserwacja
  kolana). Dashboard: 5 aktywnych klientów z pełnym przekrojem flag.

## 0.5.0 — 2026-08-18

* **Nowość — Rekordy osobiste i postęp od startu** (rywalizacja wyłącznie
  z własną historią, na życzenie użytkownika; zgodna z zasadą Human OS —
  żadnych porównań między ludźmi ani rankingów):
  `GET /api/clients/{id}/personal-records` liczy per ćwiczenie najlepszy
  własny ciężar (deterministyczny regex po tekstowych wynikach treningów,
  np. „3x8 @ 80kg"; wynik bez rozpoznawalnego ciężaru jest pomijany —
  zero zgadywania) z plakietką „nowy rekord!" gdy poprawiony w ostatnich
  14 dniach względem wcześniejszego własnego wyniku, oraz zmianę każdego
  pomiaru względem pierwszego zapisu („−4,2 kg od startu"). Karta
  „🏆 Rekordy osobiste" w Monitoringu klienta i w zakładce Monitoring
  trenera. Seed: 3 treningi klienta A z progresją przysiadu.
* Testy: 92 → 97.

## 0.4.1 — 2026-08-17

* **Logo**: zastąpiono wygenerowaną wcześniej prostą ikonę dzika docelową
  grafiką dostarczoną przez założyciela (szczegółowy maskotkowy portret
  głowy dzika + wordmark „DZIK OS"). Sama głowa (bez wordmarku, przycięta
  do kwadratu) jest teraz jedynym źródłem `Logo()` w UI oraz ikon PWA
  (`icon-192.png`/`icon-512.png` na ciemnym zaokrąglonym tle, favicon).

## 0.4.0 — 2026-08-17

Baza wiedzy trenera rozszerzona o know-how ćwiczeń i produktów, kompozytor
diety, ocena raportu i dashboard trenera; nowe logo z motywem dzika.

* **Nowość — logo z motywem dzika**: nowy znak (głowa dzika w profilu:
  ucho, ryj, kieł) zastępuje poprzedni abstrakcyjny zygzak — `Logo()`,
  ikony PWA (`icon.svg`/192/512) i favicon zaktualizowane.
* **Nowość — Baza ćwiczeń (know-how trenera)**: model `Exercise` z
  podziałem na partie mięśniowe (nogi/plecy/klatka/barki/ręce/brzuch/
  całe ciało/mobilność), techniką wykonania i efektem; CRUD trenera,
  broadcast do aktywnie prowadzonych klientów (ten sam wzorzec co Baza
  wiedzy) — nowa zakładka „Ćwiczenia" w panelu trenera i u klienta.
* **Nowość — Baza produktów z makro**: model `FoodProduct` (kcal/białko/
  tłuszcz/węglowodany na 100 g); zakładka „Produkty" z polem porcji (g),
  które na bieżąco przelicza kalorie i makro — po stronie trenera i
  klienta. Seed: ~40 typowych produktów w 8 kategoriach.
* **Nowość — Kompozytor diety** (propose-only): trener podaje cel kcal +
  makro i wybiera produkty z własnej bazy; `/api/coach/diet-suggestion`
  zwraca przejrzysty, deterministyczny podział celu na gramaturę wg
  dominującego makroskładnika każdego produktu (nigdy AI, nigdy
  automatyczna generacja diety) — wynik jest tylko sugestią do ręcznego
  wpisania w plan żywieniowy klienta, niczego nie zapisuje automatycznie.
* **Nowość — Ocena raportu przez trenera**: opcjonalna ocena 1-5 obok
  odpowiedzi na raport tygodniowy (`WeeklyCheckin.rating`) — dotyczy
  kompletności/jakości samego raportu, nie jest oceną osoby (zasada
  Human OS: system nie rankinguje ludzi); widoczna dla obu stron.
* **Nowość — Dashboard trenera**: `GET /api/coach/dashboard` agreguje
  metadane operacyjne (aktywni klienci, raporty do oceny, zaległe
  raporty/płatności, nieprzeczytane wiadomości, obserwacje) na górze
  listy klientów; nowa flaga i filtr „Raport do oceny".
* Migracja schematu nr 5 (`weekly_checkins.rating`, tabele `exercises`,
  `food_products`).
* Testy: 74 → 92 (ćwiczenia, produkty, kompozytor diety, ocena raportu,
  dashboard).

## 0.3.0 — 2026-08-17

Czytelność raportów, baza wiedzy, propozycje AI, aktualizacje PWA i
odświeżony design — na podstawie bezpośredniej informacji zwrotnej.

* **Raport tygodniowy w sekcjach**: formularz klienta i widok trenera
  podzielone na „Ciało", „Samopoczucie", „Ból/komentarz/pytania" —
  ocena raportu bez przewijania jednej długiej listy pól.
* **Nowość — podsumowanie AI raportu** (propose-only): przycisk w
  panelu trenera generuje streszczenie + szkic odpowiedzi do edycji;
  domyślnie `NullAIProvider` pokazuje jawny komunikat „wymaga
  konfiguracji" zamiast udawać działanie. Żadna odpowiedź nie trafia do
  klienta bez zatwierdzenia przez trenera.
* **Nowość — Baza wiedzy**: trener publikuje materiały (artykuł, link,
  plik) widoczne dla wszystkich aktywnie prowadzonych klientów; pełny
  CRUD (dodaj/edytuj/archiwizuj/przywróć), kategorie, przypinanie.
  Osobna oś uprawnień od danych zdrowotnych (to treść trenera, nie
  dane klienta) — patrz PERMISSIONS.md.
* **Nowość — aktualizacje PWA**: baner „Dostępna nowa wersja" zamiast
  cichej podmiany kodu aplikacji pod użytkownikiem w trakcie sesji;
  użytkownik sam decyduje, kiedy odświeżyć.
* **Design**: typografia Unbounded (nagłówki) + Inter (treść, cyfry
  tabelaryczne); warstwowe tło zamiast płaskich kart (surface staircase);
  delikatna poświata na kartach-bohaterach (trening dnia, cel); wykresy
  ze zanikającym wypełnieniem pod linią; mikrointerakcje (naciśnięcie
  przycisku, wejście karty) z pełnym poszanowaniem
  `prefers-reduced-motion`; wypełnione plakietki akcentu dla wyróżnień.
* Domyślny zakres trendów w Monitoringu skrócony z 90 do 30 dni —
  czytelniejszy, bardziej typowy okres.
* Migracja schematu nr 4 (`knowledge_items`) — bezpieczna dla istniejącej
  bazy.
* Testy: 65 → 74 backendu (275 Core bez zmian).

## 0.2.0 — 2026-08-17

Monitoring w czasie — na podstawie analizy rynku (`ANALIZA_RYNKU.md`) i
wniosku, że regularny monitoring pozwala wcześniej wychwycić niekorzystne
reakcje, a nie tylko śledzić postępy.

* **Nowość — Monitoring i postępy** (klient, `/postepy`) i zakładka
  **Monitoring** (trener): cel z odliczaniem dni, trendy pomiarów i
  samopoczucia (sen/energia/stres/głód/regeneracja z raportów), dziennik
  kaloryczny na tle celu z diety, realizacja harmonogramu per kategoria
  (pasek % zamiast surowych liczb), dziennik obserwacji.
* **Nowość — adherencja harmonogramu**: przycisk „Wykonane" na ekranie
  Dzisiaj dla każdego elementu harmonogramu (nie tylko treningu);
  idempotentne odhaczenie per dzień (`schedule_completions`).
* **Nowość — dziennik obserwacji** (`observations`): klient zgłasza
  samopoczucie lub reakcję (opcjonalnie powiązaną z suplementem/posiłkiem
  z harmonogramu), oznaczając wagę Informacja/Niepokojące. System **nigdy
  nie interpretuje ani nie diagnozuje** — wyłącznie zapisuje dosłownie i
  flaguje NIEPOKOJACE w panelu trenera (nowy filtr i badge na liście
  klientów) oraz — jeśli skonfigurowany dostawca — e-mailem.
* **Nowość — dziennik kaloryczny** (`daily_nutrition_logs`): szybki wpis
  kcal/wody na tle celu z aktywnej diety.
* **Nowość — eksport do Excela** (`/api/me/export.xlsx`, przycisk w
  Profilu): ten sam komplet danych co eksport JSON, jeden arkusz na
  tabelę.
* **Nowość — wiadomości głosowe**: nagrywanie w przeglądarce
  (MediaRecorder) i wysyłka jako załącznik; poprawiony też odbiór
  załączników dowolnego typu w wątku (wcześniej wszystko renderowało się
  jak obraz — PDF/wideo/audio wyświetlały się poprawnie po typie z
  serwera, nie po nazwie pliku).
* **Nowość — adapter powiadomień e-mail** (`notifications_provider.py`,
  wzorzec jak `payments_provider.py`): domyślnie `NullNotificationProvider`
  (nic nie wysyła, brak PII w logach); gotowy interfejs do podłączenia
  Resend/SendGrid/Mailgun/SMTP decyzją operatora.
* Migracja schematu nr 3 (trzy nowe tabele monitoringu) — bezpieczna dla
  istniejącej bazy (w tym produkcyjnej na Fly), testowana regresyjnie.
* Eksport JSON i procedura usunięcia danych objęły nowe tabele.
* Testy: 55 → 65 (adherencja, obserwacje z flagą, dziennik kaloryczny,
  eksport Excel, upload audio, migracja v1→v3).

## 0.1.1 — 2026-08-17

Runda poprawek po pełnym przekliku aplikacji + przygotowanie PaaS.

* **Naprawa**: eksport danych z poziomu Profilu pobiera plik JSON
  (wcześniej przycisk kończył się błędem po stronie przeglądarki).
* **Naprawa**: załącznik wysłany przez trenera w wiadomości jest widoczny
  dla klienta (dostęp dla stron wątku; osoby trzecie nadal 404) — test.
* **Bezpieczeństwo (R-06 zamknięte)**: konto założone przez trenera musi
  zmienić hasło startowe przy pierwszym logowaniu — blokada egzekwowana
  serwerowo (PASSWORD_CHANGE_REQUIRED), nowy ekran zmiany hasła, zmiana
  unieważnia pozostałe sesje (zdarzenie PASSWORD_CHANGED w audycie).
* **Zgody (R-05 zamknięte)**: klient przy pierwszym logowaniu jawnie
  potwierdza zgodę zarejestrowaną przy onboardingu (ekran „Twoje dane,
  Twoja zgoda"; CONSENT_CONFIRMED w łańcuchu audytu) albo odmawia;
  zgody nadawane samodzielnie są potwierdzone od razu.
* Migracja schematu nr 2 (`users.must_change_password`,
  `consents.confirmed_at`) — mechanizm migracji obsługuje istniejące bazy
  (ALTER) i świeże (stempel), z testem regresyjnym.
* Konfiguracja PaaS: `fly.toml` + instrukcja wdrożenia na Fly.io
  (darmowa subdomena z HTTPS; własna domena do dodania później).
* Testy: 50 → 55 (wymuszona zmiana hasła, potwierdzanie zgód, załączniki
  wątków, migracja v1→v2).

## 0.1.0 (MVP) — 2026-08-17

Pierwsze wydanie „Dzik OS — Panel Podopiecznego".

* Import fundamentów Human OS (`human-os@68fe1e4`) do `human-os2`
  (ADR-DZIK-003); regresja Core: 275 testów zielonych, zero zmian w Core.
* Backend FastAPI: uwierzytelnianie sesyjne (bcrypt, rate limiting),
  role COACH/CLIENT/ADMIN, relacje trener–klient, profil z wersjonowanymi
  polami i proweniencją, cele, plany treningowe i żywieniowe z
  niemutowalnymi wersjami (powód zmiany obowiązkowy), harmonogram z
  autorem zalecenia, raporty tygodniowe z rewizjami i odpowiedzią trenera,
  pomiary, wiadomości z załącznikami, dokumenty i zdjęcia (walidowany
  upload), płatności z adapterem operatora, zgody (decyzja w
  hos_engine.ConsentRegistry), eksport JSON, anonimizacja konta,
  audyt hash-chained (SQLiteEventStore) z pokwitowaniami.
* Frontend: mobile-first PWA po polsku (React+TS+Vite), aplikacja klienta
  (Dzisiaj/Plan/Dieta/Raport/Pomiary/Wiadomości/Płatności/Profil) i panel
  trenera (lista z flagami operacyjnymi, karta klienta z 8 zakładkami,
  szablony), panel admina (konta + weryfikacja łańcucha audytu).
* Dane demo (syntetyczne): trener, 2 klientów, admin, plany, dieta,
  raport, pomiary, wiadomości, dokument, płatności.
* Testy: 50 backend (izolacja, wersjonowanie, zgody, prywatność, uploady,
  płatności, audyt, E2E ścieżek) + 3 E2E przeglądarkowe (Playwright).
* Infrastruktura: Dockerfile, Docker Compose (PostgreSQL), .env.example,
  CI GitHub Actions (lint, testy Core i aplikacji, build frontendu).

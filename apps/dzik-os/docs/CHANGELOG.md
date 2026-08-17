# Changelog — Dzik OS

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

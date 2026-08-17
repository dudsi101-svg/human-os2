# Changelog — Dzik OS

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

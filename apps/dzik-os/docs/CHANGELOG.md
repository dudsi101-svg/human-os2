# Changelog — Dzik OS

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

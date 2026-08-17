# ADR-DZIK-001: Architektura aplikacji domenowej Dzik OS

Status: Accepted · Data: 2026-08-17 · Dotyczy: `apps/dzik-os/`

## Kontekst

Na fundamentach Human OS powstaje prosta aplikacja domenowa dla trenera
personalnego („Dzik OS — Panel Podopiecznego"). Repozytorium nie miało
dotąd produkcyjnego backendu (README: „Not production-ready"; AR-004);
`apps/user-demo` to prototyp UX-ONLY na localStorage, którego duplikacja
reguł w JS jest nazwana centralnym ryzykiem projektu
(docs/APP_CORE_CONTRACT.md).

## Decyzja

1. **Modularny monolit** w `apps/dzik-os`: backend FastAPI (Python ≥3.11,
   SQLAlchemy 2) + frontend React/TypeScript/Vite jako mobile-first PWA,
   serwowany przez backend w produkcji. Stos zgodny z istniejącym stosem
   repozytorium (Python + brak ustalonego standardu JS ⇒ wybrano
   najprostszy przemysłowy standard: Vite + React).
2. **Granica ADR-ARCH-003 zachowana**: frontend wysyła Request, wszystkie
   decyzje uprawnień/zgód/wersjonowania zapadają w backendzie, operacje
   wysokiej wagi zwracają pokwitowanie (Receipt) powiązane hash-em ze
   zdarzeniem. Frontend nie posiada kopii reguł.
3. **Baza**: SQLite domyślnie (deweloperka/testy), PostgreSQL w
   Docker Compose i produkcji. Migracje: rejestr `schema_migrations`
   z sekwencją wersji (v1 = schemat MVP z metadanych ORM; kolejne zmiany
   jako wpisy w `db.MIGRATIONS`).
4. **Pliki** za abstrakcją `storage.LocalStorage` (whitelist typów, limit
   rozmiaru, losowe nazwy, sha256) — wymienialna na S3 bez zmian routerów.
5. **Płatności** przez interfejs `PaymentProvider`; w MVP
   `LocalDemoProvider` (bez danych kart); instrukcja podłączenia
   Stripe/P24 w docs/DEPLOYMENT.md.
6. **AI: brak w MVP.** `DZIK_AI_ENABLED=false`; żaden kod nie wysyła danych
   do modeli AI. Ewentualne przyszłe funkcje AI muszą: mieć osobną zgodę,
   minimalizować zakres danych, być wyłączalne, oznaczać wyniki jako
   propozycje wymagające zatwierdzenia człowieka i nie zwiększać uprawnień
   ponad trenera/klienta.

## Konsekwencje

* Jedna aplikacja do wdrożenia (Compose: app+Postgres); prosta operacyjnie.
* Rozdzielenie frontend/backend umożliwia późniejsze wydzielenie API.
* Testy API (50) + regresja Core (275) + E2E przeglądarkowe (3) w CI.

# Dzik OS — Panel Podopiecznego

Prosta aplikacja domenowa dla internetowego trenera personalnego
(marka robocza: **Lubelski Dzik**), zbudowana na fundamentach
**Human OS** (`hos_engine`). Jedna przestrzeń zamiast WhatsAppa, arkuszy
i PDF-ów: plan treningowy, dieta, harmonogram, raporty tygodniowe,
pomiary, monitoring w czasie (cel, trendy, adherencja, dziennik
obserwacji), baza wiedzy (artykuły, know-how ćwiczeń z podziałem na
partie, baza produktów z makro i kompozytor diety), wiadomości (w tym
głosowe), dokumenty, płatności i dashboard trenera.

Status: **pilotaż na produkcji (0.53.11)** — bieżący stan wdrożenia,
kont i integracji: [docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md) ·
Język: polski · Licencja kodu: Apache-2.0

## Zasada uruchomienia

Nowa funkcja nie jest gotowa, dopóki nie została **uruchomiona w działającej
aplikacji** i obejrzana — przechodzące testy są warunkiem wstępnym, nie
dowodem. Pełna zasada wraz z uzasadnieniem i listą wymaganych dowodów:
`docs/ZASADA_URUCHOMIENIA.md`.

## Zasady (fundamenty Human OS)

* dane klienta są jego własnością — eksport i usunięcie wbudowane;
* dostęp trenera wynika z aktywnej relacji **i** zgody klienta
  (decyzję podejmuje `hos_engine.ConsentRegistry`, nie warstwa UI);
* plany i raporty są wersjonowane — nic nie jest cicho nadpisywane;
* każda istotna operacja trafia do niemutowalnego, hash-chained łańcucha
  zdarzeń (`hos_engine.sqlite_store.SQLiteEventStore`) i ma pokwitowanie
  (Receipt);
* granica: `UI → Request → Core/Policy → Result/Receipt → UI`
  (ADR-ARCH-003); frontend nie podejmuje decyzji bezpieczeństwa;
* AI jest opcjonalne i domyślnie wyłączone — aplikacja działa bez AI;
* zaimplementowany podzbiór Human OS jest oznaczony jako
  `MVP_IMPLEMENTED_SUBSET` (patrz ADR-DZIK-003) — to nie jest pełny
  Human OS.

## Szybki start (lokalnie, bez Dockera)

```bash
# z korzenia repozytorium; wymagany Python >= 3.11 i Node >= 20
pip install -e ".[dev]" && pip install -e "apps/dzik-os/backend[dev]"
(cd apps/dzik-os/frontend && npm install && npm run build)
python -m dzik_os.seed                     # syntetyczne dane demo
uvicorn dzik_os.main:app --port 8000       # http://localhost:8000
```

Lub jednym poleceniem przez Docker Compose:

```bash
docker compose -f apps/dzik-os/docker-compose.yml up --build
docker compose -f apps/dzik-os/docker-compose.yml run --rm seed   # dane demo
```

## Konta demonstracyjne (tylko lokalny seed!)

Poniższe konta tworzy `python -m dzik_os.seed` na LOKALNEJ bazie.
Na produkcji nie istnieją: konta demo sprzed pilotażu zostały
zdezaktywowane (`purge_demo`), a prawdziwe konta wymieniono
w `docs/RELEASE_STATUS.md`.

| Rola   | E-mail                | Hasło            |
|--------|-----------------------|------------------|
| Trener | `dzik@example.com`    | `DzikTrener#2026` |
| Klient A | `klient.a@example.com` | `KlientA#2026!x` |
| Klient B | `klient.b@example.com` | `KlientB#2026!x` |
| Klient C (raport do oceny) | `marek.dziczek@example.com` | `KlientC#2026!x` |
| Klient D (praca wykonana) | `anna.wilk@example.com` | `KlientD#2026!x` |
| Klient E (zaległości) | `piotr.zajac@example.com` | `KlientE#2026!x` |
| Admin  | `admin@example.com`   | `DzikAdmin#2026` |

## Testy i bramki

```bash
# z korzenia repozytorium
ruff check apps/dzik-os/backend apps/dzik-os/tools
pytest apps/dzik-os/backend/tests -q     # ~850 testów API/uprawnień/audytu
pytest tests/ -q                         # 275 testów regresyjnych Core
python apps/dzik-os/tools/spojnosc.py    # kontrole spójności (wersje, trasy, workflowy…)
python apps/dzik-os/tools/mutacje.py     # testy mutacyjne logiki
python apps/dzik-os/tools/mutacje_bezpieczenstwa.py

# frontend (w apps/dzik-os/frontend)
npx tsc --noEmit && npm run build
npm run test:helpers
npm run test:e2e                         # Playwright, telefon + desktop trenera
```

Dokładne liczby testów zmieniają się co rundę — źródłem prawdy jest
przebieg CI (`.github/workflows/dzik-os-ci.yml`), który uruchamia
wszystkie powyższe bramki na każdym PR.

## Dokumentacja

| Dokument | Zawartość |
|---|---|
| [docs/RELEASE_STATUS.md](docs/RELEASE_STATUS.md) | **Stan produkcji TERAZ**: wersja, konta, integracje, kroki właściciela |
| [docs/STAN_PRZEKAZANIA.md](docs/STAN_PRZEKAZANIA.md) | Stan prac między sesjami (gdzie jesteśmy, co w toku) |
| [docs/BRAMKA_GO_NOGO.md](docs/BRAMKA_GO_NOGO.md) | Decyzja jakościowa GO/NO-GO z listą blokerów |
| [docs/PRODUCT_BRIEF.md](docs/PRODUCT_BRIEF.md) | Cel produktu, role, zakres MVP |
| [docs/REQUIREMENTS_MAP.md](docs/REQUIREMENTS_MAP.md) | Mapa wymagań → implementacja → testy |
| [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md) | Kryteria ukończenia ze statusem weryfikacji |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Model danych (33 tabele) |
| [docs/PERMISSIONS.md](docs/PERMISSIONS.md) | Role i reguły dostępu |
| [docs/DATA_PROCESSING_MAP.md](docs/DATA_PROCESSING_MAP.md) | Mapa przetwarzania danych (RODO) |
| [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md) | Rejestr ryzyk |
| [docs/DEFERRED_FEATURES.md](docs/DEFERRED_FEATURES.md) | Świadomie odłożone funkcje |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Uruchomienie, staging, produkcja |
| [docs/OCR.md](docs/OCR.md) | Przepisywanie tekstu ze zdjęcia: dwa tryby, kolejka, limity, prywatność |
| [docs/INSTRUKCJA_TRENERA.md](docs/INSTRUKCJA_TRENERA.md) | Instrukcja dla trenera |
| [docs/INSTRUKCJA_KLIENTA.md](docs/INSTRUKCJA_KLIENTA.md) | Instrukcja dla podopiecznego |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Historia zmian aplikacji |
| [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) | Raport końcowy z budowy MVP |

Decyzje architektoniczne: `docs/adr/ADR-DZIK-001..003` w katalogu
[/docs/adr](../../docs/adr/) repozytorium.

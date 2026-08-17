# Dzik OS — Panel Podopiecznego

Prosta aplikacja domenowa dla internetowego trenera personalnego
(marka robocza: **Lubelski Dzik**), zbudowana na fundamentach
**Human OS** (`hos_engine`). Jedna przestrzeń zamiast WhatsAppa, arkuszy
i PDF-ów: plan treningowy, dieta, harmonogram, raporty tygodniowe,
pomiary, monitoring w czasie (cel, trendy, adherencja, dziennik
obserwacji), wiadomości (w tym głosowe), dokumenty i płatności.

Status: **MVP + monitoring (0.2.0)** · Język: polski · Licencja kodu: Apache-2.0

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

## Konta demonstracyjne (tylko lokalnie/staging!)

| Rola   | E-mail                | Hasło            |
|--------|-----------------------|------------------|
| Trener | `dzik@example.com`    | `DzikTrener#2026` |
| Klient A | `klient.a@example.com` | `KlientA#2026!x` |
| Klient B | `klient.b@example.com` | `KlientB#2026!x` |
| Admin  | `admin@example.com`   | `DzikAdmin#2026` |

## Testy

```bash
pytest apps/dzik-os/backend/tests -q   # 50 testów API/uprawnień/audytu
pytest tests/ -q                       # 275 testów regresyjnych Core
pytest apps/dzik-os/e2e -q             # 3 testy E2E w przeglądarce (po npm run build)
ruff check apps/dzik-os/backend
```

## Dokumentacja

| Dokument | Zawartość |
|---|---|
| [docs/PRODUCT_BRIEF.md](docs/PRODUCT_BRIEF.md) | Cel produktu, role, zakres MVP |
| [docs/REQUIREMENTS_MAP.md](docs/REQUIREMENTS_MAP.md) | Mapa wymagań → implementacja → testy |
| [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md) | Kryteria ukończenia ze statusem weryfikacji |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Model danych (27 tabel) |
| [docs/PERMISSIONS.md](docs/PERMISSIONS.md) | Role i reguły dostępu |
| [docs/DATA_PROCESSING_MAP.md](docs/DATA_PROCESSING_MAP.md) | Mapa przetwarzania danych (RODO) |
| [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md) | Rejestr ryzyk |
| [docs/DEFERRED_FEATURES.md](docs/DEFERRED_FEATURES.md) | Świadomie odłożone funkcje |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Uruchomienie, staging, produkcja |
| [docs/INSTRUKCJA_TRENERA.md](docs/INSTRUKCJA_TRENERA.md) | Instrukcja dla trenera |
| [docs/INSTRUKCJA_KLIENTA.md](docs/INSTRUKCJA_KLIENTA.md) | Instrukcja dla podopiecznego |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Historia zmian aplikacji |
| [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) | Raport końcowy z budowy MVP |

Decyzje architektoniczne: `docs/adr/ADR-DZIK-001..003` w katalogu
[/docs/adr](../../docs/adr/) repozytorium.

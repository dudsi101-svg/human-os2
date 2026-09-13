# Etap 0 — rozpoznanie repozytorium (13.09.2026)

**Aplikacja:** `apps/dzik-os` w monorepo `human-os2` (Core `hos_engine/` poza
zasięgiem; 275 testów musi zostać zielone).

## Stack

| Warstwa | Technologia | Gdzie |
|---|---|---|
| Backend | Python 3.11–3.13, FastAPI, SQLAlchemy 2 (`Mapped`/`mapped_column`), Pydantic v2 | `backend/dzik_os/` |
| Baza | SQLite (dev/test/produkcja Fly z wolumenem) + PostgreSQL w CI (`backend-postgres`) | `db.py` |
| Migracje | własny rejestr `MIGRATIONS: list[(nr, opis, [SQL])]` w `db.py`, tabela `schema_migrations`; świeża baza = `Base.metadata.create_all` + wpisy; SQL musi być przenośny (strażnik `tests/test_migracje_przenosnosc.py`: BOOLEAN `true/false`, bez składni tylko-SQLite). Ostatnia: **31** (Wywiad) → nowa: **32**. | `db.py` |
| Frontend | React 18 + TypeScript + Vite, PWA, trasy lazy w `App.tsx`, klient API `api.get/post/patch/put/del`, komponenty w `components.tsx`, budżet głównego chunku 120 kB gzip | `frontend/src/` |
| Testy backend | pytest (`tests/conftest.py`: `client`, `seeded` z kontami demo; `login`, `get_user_id`, `create_user_with_role`); macierz dostępu `tests/access_matrix.py` (każda nowa trasa MUSI mieć wpis, klasa dostępu weryfikowana wykonaniem) | `backend/tests/` |
| Testy frontend | `tsc -b`, `vite build` + budżet, `test:helpers` (node --test), E2E Playwright (`frontend/e2e/*.spec.ts`, projekt „telefon” zapisuje, „desktop-trener” tylko odczyt), `e2e/test_a11y.mjs` | `frontend/` |
| Spójność | `tools/spojnosc.py` (13 kontroli: CHANGELOG, wersje w STAN/RELEASE, pliki nieśledzone, …) | `tools/` |
| Pakowanie | wheel; katalogi danych wymagają `[tool.setuptools.package-data]` (`tests/test_pakietowanie.py`) — dane CSV/JSON modułu trafią do `dzik_os/dieta/dane/` | `pyproject.toml` |

## Autoryzacja i role

* Role: `COACH`, `CLIENT`, `ADMIN` (`RoleGrant`, `security.active_roles`,
  `require_role("COACH")`, `current_user`).
* Dostęp do danych klienta: `authz.resolve_client_access(db, actor, client_id,
  domain=…)` — klient sam albo trener z aktywną relacją (`CoachClientRelationship`)
  i zgodą kategorii danych (`ConsentService`); domena diety: `DOMAIN_NUTRITION`
  (`nutrition_data`). Cudzy zasób = 404 z wpisem ACCESS_DENIED (nie 403).
* Zasób po własnym id: `require_owned_resource(entity, actor=…, owner_attr=…)`.
* Audyt: `hos_bridge.record_event(db, action=…, actor_id=…, subject_ids=…,
  payload=…, summary=…)` — bez treści zdrowotnych w payloadzie.
* Idempotencja zapisów: `idempotency.replay_response/store_response`.

## Istniejące funkcje diet (nie ruszać)

| Co | Gdzie | Status |
|---|---|---|
| Plan żywieniowy klienta (wersje, sekcje/posiłki/suplementy), szkice i publikacja (0.58.0) | `routers/nutrition.py`, `publikacja/*`, `NutritionPlan(Version)` | zostaje — nowy moduł jest równoległy |
| Szablony diety trenera (kopia do klienta, 0.54.0) | `routers/nutrition_templates.py`, `NutritionTemplate` | zostaje |
| „Kreator diety” / kompozycja wg uznanych diet (0.44–0.48) + kreator dań z receptur (0.57.0) | `routers/kulinaria.py`, `kulinaria/*`, `KreatorDan.tsx` | to jest „stary konfigurator diet” z instrukcji — **nie naprawiamy, nie usuwamy**; wyłączenie flagą to osobna decyzja właściciela (poza tą rundą) |
| Konfigurator 28 dni (trening, K1) | `routers/konfigurator.py` | niezwiązany |
| Baza produktów spożywczych (~2000, `FoodProduct`) | `routers/food_catalog.py` | inna tabela; moduł ma własną `diet_products` (142 z CSV, z `substitution_group`, tagami, `source`) — bez łączenia w v1 |

## Konwencje

* Nazewnictwo polskie w kodzie aplikacyjnym (moduły `wywiad/`, `publikacja/`),
  trasy `/api/...`; nowy moduł: pakiet `dzik_os/dieta/` (silnik `silnik.py`
  = `engine.py` 1:1, `seed.py`, `serwis.py`), router `routers/diet.py`
  z prefiksem `/api/diet` (nazwy z zadania).
* Feature flag jak `szkice_publikacja`: pole w `config.Settings` z env
  `DZIK_DIET_TEMPLATES_ENABLED` (domyślnie `false`; `true` w `.env.example`
  dla dev, w testach ustawiane w `conftest`/monkeypatch, `serve.sh` E2E).
  Frontend rozpoznaje flagę po 404 z `GET /api/diet/profiles` (wzorzec
  `PublikacjaPanel.onDostepne`) oraz po `features` w `/api/health`.
* Wersja aplikacji w trzech miejscach (`pyproject.toml`, `dzik_os/__init__.py`,
  `frontend/package.json`) + CHANGELOG/RELEASE_STATUS/STAN — nowa: **0.60.0**.
* Protokół pracy: plan sesji jako pierwszy commit, draft PR `[WRITER]`,
  gałąź `agent/szablony-diet` od `main` (80deb80).

## Ryzyka rozpoznane przed kodem

1. `engine.py` czyta CSV przez pandas w czasie importu — w aplikacji produkty
   przychodzą z bazy jako parametr funkcji (bez pandas w runtime).
2. Puste pola CSV w pandas są `NaN` → `str(NaN) == "nan"`; port musi
   zachować semantykę (puste = brak dopasowania), a nie dopasowywać "nan".
3. Referencja **nie wymusza** wspólnego współczynnika `group` (golden:
   racuchy jajko ×1,0 vs mąka ×0,75) — zadanie każe dopisać; robię to jako
   jawną opcję silnika z osobnym testem, bez zmiany wyniku golden dnia 1
   (szczegóły w `PROGRESS.md`).
4. Kategoria `tłuszcze` + LINIOWY → `max_factor ≥ 3,0` zawsze (klucz
   `_explicit` w referencji nigdy nie jest ustawiany) — port zachowuje to.

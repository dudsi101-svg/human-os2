# Plan sesji: deploy po zielonym CI + wersja w health (audyt P0-2, P1-5)

**Gałąź:** `agent/deploy-po-ci` (od `main` = aktualny)
**Rola:** aktywny piszący (Sprint A audytu, pozycje A2+A3)
**Cel:** produkcja dostaje wyłącznie build, który przeszedł pełne CI,
a health identyfikuje uruchomioną wersję — smoke test przestaje wierzyć,
zaczyna sprawdzać.

## Zamiar

1. **`fly-deploy.yml` przez `workflow_run`**: trigger `push` znika;
   deploy rusza po ukończeniu workflow `dzik-os-ci` na `main`
   z `conclusion == success` (ręczny `workflow_dispatch` zostaje na
   awarie). Checkout z `github.event.workflow_run.head_sha` — wdraża się
   dokładnie ten commit, który przeszedł CI.
2. **Wersja/SHA w aplikacji**: `config.py` czyta `DZIK_BUILD_SHA`
   i `DZIK_APP_VERSION` (domyślnie `dev`); `/api/health` zwraca
   dodatkowo `version`, `build` (krótki SHA) i `migration` (najwyższy
   zastosowany numer, policzony raz przy starcie). Deploy przekazuje
   `--env DZIK_BUILD_SHA=<sha>` i `--env DZIK_APP_VERSION=<z CHANGELOG>`.
3. **Smoke test z zębami**: po deployu porównuje `build` z health
   z wdrażanym SHA i wersję z CHANGELOG — rozjazd czerwieni run.
4. `pyproject.toml`/`__init__.py` podbite do 0.53.3 (jednorazowe
   wyrównanie; stały mechanizm RELEASE_STATUS to Sprint B).

## Mój obszar

- `.github/workflows/fly-deploy.yml`;
- `backend/dzik_os/config.py`, `backend/dzik_os/main.py`,
  `backend/tests/test_health_version.py` (nowy),
  `backend/pyproject.toml`, `backend/dzik_os/__init__.py`;
- `docs/CHANGELOG.md` (0.53.3), `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Świadomie nie robię

- ochrony gałęzi `main` — to ustawienie konta GitHub (właściciel, W1
  planu; po scaleniu podam listę checków do zaznaczenia);
- środowiska `production` z aprobatami — wymaga decyzji właściciela
  o osobach zatwierdzających.

## Rezerwacje

- **Wersja: 0.53.3.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- pełne bramki; health lokalnie zwraca version/build/migration;
  po scaleniu: CI main → dopiero potem deploy (kolejność widoczna
  w Actions), smoke porównuje SHA.

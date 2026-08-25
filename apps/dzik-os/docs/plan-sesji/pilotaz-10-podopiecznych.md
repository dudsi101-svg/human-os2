# Plan sesji: pilotaż — limit 10 podopiecznych + konfiguracja bez terminala

**Gałąź:** `agent/pilotaz-10-podopiecznych` (od `main` = aktualny)
**Rola:** aktywny piszący (polecenie właściciela, 25.08: „zrealizuj te
punkty; dopuść 10 podopiecznych")
**Cel:** produkcja przyjmuje maksymalnie 10 podopiecznych (skala
pilotażu), a dwa właścicielskie kroki startowe — pierwsze konta
i sekrety — stają się klikalnymi workflow na GitHubie (bez instalowania
flyctl).

## Zamiar

1. **Limit podopiecznych** (`config.max_clients`, env `DZIK_MAX_CLIENTS`,
   domyślnie **10**; `0` = bez limitu): `POST /coach/clients` odmawia
   (409, komunikat po polsku) gdy trener ma już `max_clients`
   niezakończonych współprac (ACTIVE/PAUSED — ENDED zwalnia miejsce).
   `fly.toml` deklaruje `DZIK_MAX_CLIENTS = "10"` jawnie. Testy: limit
   osiągnięty → 409; ENDED zwalnia miejsce; 0 wyłącza limit.
2. **Workflow `fly-bootstrap.yml`** (workflow_dispatch): zakłada pierwsze
   konto trenera i admina na produkcji — hasła czyta z sekretów
   repozytorium (`DZIK_BOOTSTRAP_COACH_PASSWORD`,
   `DZIK_BOOTSTRAP_ADMIN_PASSWORD`), wstawia je chwilowo jako sekrety
   Fly (env — nigdy argv na maszynie), uruchamia `python -m
   dzik_os.bootstrap`, po czym sekrety bootstrapowe usuwa. E-maile kont
   to jawne parametry uruchomienia.
3. **Workflow `fly-sekrety.yml`** (workflow_dispatch): przenosi na Fly te
   sekrety konfiguracyjne repo, które są ustawione (SMTP_*, AI_*,
   FILE_KEY) — pominięte puste; bez podglądu wartości w logach
   (maskowanie Actions).
4. **`DEPLOYMENT.md`**: nowa sekcja „Konfiguracja bez terminala" —
   dokładna ścieżka klikania dla właściciela.

## Mój obszar

- `backend/dzik_os/config.py`, `backend/dzik_os/routers/clients.py`,
  `backend/tests/test_clients_limit.py` (nowy), `apps/dzik-os/fly.toml`;
- `.github/workflows/fly-bootstrap.yml`, `.github/workflows/fly-sekrety.yml`;
- `apps/dzik-os/docs/DEPLOYMENT.md`, `docs/CHANGELOG.md`,
  `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- frontendu (409 pokazuje istniejąca obsługa błędów), modeli/migracji,
  Core; cennika i domeny (decyzje właścicielskie, poza kodem).

## Rezerwacje

- **Wersja: 0.52.0** (ostatnia: 0.51.0). **Migracja: brak.**

## Świadomie nie robię

- nie przenoszę nazw wyświetlanych kont przez workflow (flyctl `-C`
  dzieli po spacjach — imię z nazwiskiem by się rozpadło); bootstrap
  użyje domyślnych „Trener"/„Administrator", a nazwę zmienimy w rundzie
  profilu, jeśli będzie potrzeba;
- nie uruchamiam workflow sam — hasła i klik należą do właściciela.

## Weryfikacja (do wypełnienia)

- pełne bramki; na żywo: limit odmawia przy 10 aktywnych współpracach
  i wpuszcza po zakończeniu jednej; workflow zwalidowane składniowo
  (actionlint/py yaml), uruchomienie na produkcji — właściciel.

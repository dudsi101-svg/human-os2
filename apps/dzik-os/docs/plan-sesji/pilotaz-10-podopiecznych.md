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
- ~~nie uruchamiam workflow sam~~ — **zmiana zakresu na wprost polecenia
  właściciela („zrealizuj sam te punkty")**: workflow bootstrapu dostał
  tryb awaryjny bez sekretów repo (generuje silne hasła jednorazowe
  openssl-em, maskuje je w logach i zostawia w artefakcie o ważności
  1 dnia — konto i tak wymusza zmianę hasła i MFA przy pierwszym
  logowaniu), dzięki czemu uruchamiam go sam przez API po scaleniu.
  Sekrety SMTP/AI zostają po stronie właściciela — to poświadczenia
  jego kont u zewnętrznych dostawców, których nie mogę i nie powinienem
  wytwarzać.

## Weryfikacja (wypełnione 25.08)

- Bramki: ruff czysto (po `--fix` 1×I001), backend **816** zaliczonych
  (3 nowe testy limitu), Core 275, spójność 10 kontroli, mutacje 17/17
  i 9/9, frontend tsc+build, helpers 0 fail, E2E 17/17.
- Uruchomienie na żywo (serve.sh :8153 z `DZIK_MAX_CLIENTS=5`; co
  uruchomiłem i co zobaczyłem): seed ma 5 aktywnych współprac →
  `POST /coach/clients` zwrócił **409** z komunikatem „Limit
  podopiecznych (5) jest osiągnięty…"; w testach jednostkowych ENDED
  zwalnia miejsce (201 po zakończeniu współpracy), a 0 wyłącza limit.
- Oba workflow zwalidowane YAML-owo + fragment bashowy `bash -n`;
  uruchomienie na produkcji (sekrety + klik) — świadomie po stronie
  właściciela.

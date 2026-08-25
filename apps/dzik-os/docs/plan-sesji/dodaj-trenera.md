# Plan sesji: drugie konto trenera (narzędzie + workflow)

**Gałąź:** `agent/dodaj-trenera` (od `main` = aktualny)
**Rola:** aktywny piszący (polecenie właściciela, 25.08: konto trenerskie
do przeglądania i testów — „jeśli nie ma, utwórz")
**Cel:** na działającej bazie da się założyć KOLEJNE konto COACH — panel
admina jest tylko do odczytu, a bootstrap słusznie działa wyłącznie na
pustej bazie; brakuje ścieżki operacyjnej.

## Zamiar

1. **`python -m dzik_os.dodaj_trenera --email X [--name Y]`** — zakłada
   jedno konto COACH na dowolnej bazie: hasło WYŁĄCZNIE z env
   `DZIK_BOOTSTRAP_COACH_PASSWORD` (ten sam kanał co bootstrap — nigdy
   argv), odmowa gdy e-mail zajęty, `must_change_password=True`, wpis
   audytu. Testy: sukces + logowanie, zajęty e-mail, brak env, krótkie
   hasło.
2. **Workflow „Dodaj trenera (Fly.io)"** — ta sama mechanika co
   bootstrap: sekret repo albo hasło wygenerowane (maskowane,
   artefakt „haslo-trenera" ważny 1 dzień), chwilowy sekret Fly
   kasowany po użyciu.
3. `DEPLOYMENT.md` §4bis: dopisek o trzecim workflow.

## Mój obszar

- `backend/dzik_os/dodaj_trenera.py` (nowy), `backend/tests/
  test_dodaj_trenera.py` (nowy);
- `.github/workflows/fly-dodaj-trenera.yml` (nowy);
- `apps/dzik-os/docs/DEPLOYMENT.md`, `docs/CHANGELOG.md` (0.53.1),
  `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Czego nie dotykam

- bootstrap/purge (zostają jak są), routerów, frontendu, Core.

## Rezerwacje

- **Wersja: 0.53.1** (ostatnia: 0.53.0). **Migracja: brak.**

## Świadomie nie robię

- nie dodaję nadawania ról z panelu admina (zmiana powierzchni ataku
  aplikacji webowej — osobna decyzja produktowa; narzędzie CLI+workflow
  wystarcza na skalę pilotażu i zostawia ślad w audycie).

## Weryfikacja (do wypełnienia)

- pełne bramki; na produkcji: workflow zakłada konto testowe właściciela
  (dudsi101+trener@gmail.com) — hasło w artefakcie.

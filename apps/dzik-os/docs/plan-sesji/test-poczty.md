# Plan sesji: test poczty w workflow sekretów

**Gałąź:** `agent/test-poczty` (od `main` = aktualny)
**Rola:** aktywny piszący (polecenie właściciela: „zainstaluj smtp" —
kod i workflow są od 0.42/0.52; brakuje wyłącznie poświadczeń dostawcy,
których nie mogę wytworzyć; domykam więc wszystko wokół)
**Cel:** po ustawieniu sekretów SMTP jeden przebieg workflow ma sam
udowodnić, że poczta działa — testowy e-mail zamiast wiary w konfigurację.

## Zamiar

1. **`python -m dzik_os.test_poczty ADRES`** — wysyła jeden testowy
   e-mail przez skonfigurowanego dostawcę (`_zbuduj_provider`); przy
   dostawcy `null` (brak DZIK_SMTP_HOST) kończy się błędem z czytelnym
   komunikatem; wynik `send_email` decyduje o kodzie wyjścia. Zero PII
   w logach (zasady providera bez zmian). Test jednostkowy na wstrzykniętym
   fake'u + odmowa bez konfiguracji.
2. **`fly-sekrety.yml`**: opcjonalny input `test_email` — po ustawieniu
   sekretów i restarcie maszyny workflow uruchamia test przez
   `flyctl ssh console` i kończy się czerwono, gdy wysyłka nie wyszła.
3. `DEPLOYMENT.md` §4bis: dopisek o teście + dokładna instrukcja
   hasła aplikacji Gmail (najkrótsza droga dla lubelskidzikk@gmail.com).

## Mój obszar

- `backend/dzik_os/test_poczty.py` (nowy), `backend/tests/
  test_test_poczty.py` (nowy);
- `.github/workflows/fly-sekrety.yml`;
- `apps/dzik-os/docs/DEPLOYMENT.md`, `docs/CHANGELOG.md` (0.52.3),
  `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Rezerwacje

- **Wersja: 0.52.3.** **Migracja: brak.**

## Weryfikacja (wypełnione 25.08)

- Bramki: ruff czysto, backend **821** zaliczonych (4 nowe testy
  test_poczty na wstrzykniętym fake'u: sukces/odmowa dostawcy/null/
  walidacja argumentów), Core 275, spójność, mutacje 17/17 i 9/9;
  YAML workflow zwalidowany.
- Prawdziwa wysyłka na produkcji — z natury po ustawieniu sekretów
  przez właściciela (workflow z polem test_email robi ją sam i czerwieni
  się przy porażce).

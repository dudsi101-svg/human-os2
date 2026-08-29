# Plan sesji: awaryjny reset hasła bez SMTP (potrzeba właściciela, na żywo)

**Gałąź:** `agent/reset-hasla-awaryjny` (od `main` = 4cc16fb)
**Rola:** aktywny piszący
**Cel:** właściciel i trener siedzą przed ekranem logowania: hasła
startowe wygasły z artefaktami (retencja 1 dzień), a reset e-mailem
nie działa, bo SMTP czeka na hasło aplikacji Gmail (W2). Nie istnieje
ŻADNA ścieżka odzyskania dostępu do istniejącego konta bez terminala —
bootstrap odmawia na niepustej bazie, dodaj_trenera odmawia na
istniejącym e-mailu. Ta runda domyka lukę raz na zawsze.

## Zamiar

1. **`dzik_os/resetuj_haslo.py`** — wzorzec `dodaj_trenera`: ustawia
   świeże hasło startowe dla ISTNIEJĄCEGO, aktywnego konta wskazanego
   e-mailem. Hasło wyłącznie z env `DZIK_RESET_PASSWORD` (nigdy argv);
   `must_change_password=True` (hasło jednorazowe — aplikacja wymusi
   zmianę, a rola COACH/ADMIN także MFA); unieważnienie wszystkich
   aktywnych sesji konta (reset = przejęcie kontroli, stare sesje
   nie mogą przeżyć); zdarzenie audytowe bez treści hasła; odmowa dla
   konta nieaktywnego (SUSPENDED — zdezaktywowanych kont demo nie
   wskrzeszamy resetem).
2. **`.github/workflows/fly-reset-hasla.yml`** — wzorzec
   `fly-dodaj-trenera`: input e-mail (walidowany, przez env),
   hasło z sekretu repo albo wygenerowane (`::add-mask::`), chwilowy
   sekret Fly kasowany po użyciu, artefakt `haslo-reset` (retencja
   1 dzień) w trybie wygenerowanym. Akcje przypięte po SHA.
3. Testy: sukces (nowe hasło działa, stare nie, sesje unieważnione,
   must_change ustawione), odmowa dla nieistniejącego e-maila,
   odmowa dla konta SUSPENDED, brak hasła w audycie.

## Świadomie nie robię

- nie dotykam mechanizmu resetu e-mailowego (działa, czeka na SMTP);
- nie resetuję nikomu hasła sam — workflow czeka na klik właściciela.

## Rezerwacje

- **Wersja: 0.53.13.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne; uruchomienie modułu na żywo w izolowanym środowisku.

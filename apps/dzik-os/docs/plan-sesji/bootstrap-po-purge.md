# Plan sesji: bootstrap po purge — naprawa strażnika pustej bazy

**Gałąź:** `agent/bootstrap-po-purge` (od `main` = aktualny)
**Rola:** aktywny piszący (kontynuacja „zrealizuj sam te punkty" — błąd
wykryty na produkcji: po `purge_demo --force` bootstrap nadal odmawia)
**Cel:** udokumentowana sekwencja purge→bootstrap ma działać.

## Diagnoza (z produkcji, nie z założeń)

`purge_demo` zawiesza konta demo (`User.status = SUSPENDED`), ale ich
wiersze `RoleGrant` zostają. Strażnik w `bootstrap.py` liczy WSZYSTKIE
nadania COACH/ADMIN — bez filtra statusu użytkownika i `revoked_at` —
więc po purge widzi „zajęte" role kont, którymi nie da się zalogować,
i odmawia na zawsze. Dowód: runy 32817190105 (purge OK, 7 kont
SUSPENDED) i 32817261325 (bootstrap: „W bazie istnieje już konto…").

## Zamiar

Strażnik liczy wyłącznie nadania COACH/ADMIN **nieodwołane**
(`revoked_at IS NULL`) należące do **aktywnych** kont
(`User.status == "ACTIVE"`) — intencja strażnika (nie nadpisuj działającej
instalacji) zostaje, a zawieszone konta demo przestają blokować start.
Test: seed → purge(force) → bootstrap zakłada konta (plus dotychczasowa
odmowa na zasianej bazie bez purge — bez zmian).

## Mój obszar

- `backend/dzik_os/bootstrap.py` (sam strażnik),
  `backend/tests/test_bootstrap_purge.py` (dopisek scenariusza purge→bootstrap);
- `docs/CHANGELOG.md` (0.52.2), `docs/STAN_PRZEKAZANIA.md`; ten plan.

## Rezerwacje

- **Wersja: 0.52.2.** **Migracja: brak.**

## Weryfikacja (wypełnione 25.08)

- Bramki: ruff czysto, backend **817** zaliczonych (nowy test regresji
  purge→bootstrap; dopasowanie komunikatu w teście odmowy), Core 275,
  spójność, mutacje 17/17 i 9/9.
- Na produkcji (po scaleniu): ponowny run workflow „Pierwsze konta" —
  wynik dopisany w rozmowie z właścicielem (artefakt hasła-startowe).

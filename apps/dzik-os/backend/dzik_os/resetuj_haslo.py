"""Awaryjny reset hasła istniejącego konta: `python -m dzik_os.resetuj_haslo`.

Reset e-mailem wymaga działającego SMTP, a hasła startowe z artefaktów
wygasają po jednym dniu — bez tego narzędzia właściciel mógł zostać
trwale zamknięty poza własnym systemem (bootstrap odmawia na niepustej
bazie, dodaj_trenera na zajętym e-mailu). Workflow „Reset hasła (Fly.io)"
uruchamia ten moduł na maszynie.

Zasady identyczne jak w bootstrap.py/dodaj_trenera.py:

* **Hasło wyłącznie ze zmiennej środowiskowej** `DZIK_RESET_PASSWORD`
  (workflow wstawia ją jako chwilowy sekret Fly i kasuje po użyciu;
  nigdy argv).
* Nowe hasło jest **jednorazowe**: `must_change_password=True` —
  aplikacja wymusi zmianę przy pierwszym logowaniu (a rola COACH/ADMIN
  także konfigurację MFA).
* **Wszystkie aktywne sesje konta zostają unieważnione** — reset to
  przejęcie kontroli nad kontem; żadna stara sesja nie może go przeżyć.
* Odmowa dla konta nieistniejącego i dla konta w stanie innym niż
  ACTIVE (zdezaktywowanych kont demo nie wskrzeszamy resetem).
* Zdarzenie audytowe bez treści hasła.

Użycie (na maszynie Fly przez `flyctl ssh console` albo lokalnie):

    DZIK_RESET_PASSWORD='...' \\
    python -m dzik_os.resetuj_haslo --email osoba@example.com
"""

from __future__ import annotations

import argparse
import os
import sys

from .bootstrap import MIN_PASSWORD_LEN
from .config import settings
from .db import db_session, run_migrations
from .hos_bridge import record_event
from .models import MfaRecoveryCode, User, now_iso
from .security import hash_password, revoke_other_sessions


def resetuj_haslo(email: str, password: str) -> str:
    """Ustawia świeże hasło startowe. Zwraca id użytkownika.
    Rzuca ValueError, gdy warunki nie są spełnione."""
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Hasło ma mniej niż {MIN_PASSWORD_LEN} znaków.")
    email = email.strip().lower()
    settings.ensure_dirs()
    run_migrations()
    with db_session() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            raise ValueError(f"Konto {email} nie istnieje.")
        if user.status != "ACTIVE":
            raise ValueError(
                f"Konto {email} ma stan {user.status} — reset dotyczy "
                "wyłącznie kont aktywnych."
            )
        user.password_hash = hash_password(password)
        user.must_change_password = True
        # Reset operatorski przywraca konto do logowania hasłem: czyścimy
        # TOTP i kody zapasowe (0.54.1) — inaczej konto z utraconym
        # telefonem albo z MFA sprzed zdjęcia przymusu zostaje zamknięte.
        # Jeśli rola ma MFA obowiązkowe, aplikacja i tak wymusi ponowną
        # konfigurację przy pierwszym logowaniu.
        mialo_mfa = user.totp_confirmed_at is not None
        user.totp_secret = None
        user.totp_confirmed_at = None
        user.totp_last_counter = None
        for kod in db.query(MfaRecoveryCode).filter(
            MfaRecoveryCode.user_id == user.id,
            MfaRecoveryCode.used_at.is_(None),
        ):
            kod.used_at = now_iso()
        uniewaznione = revoke_other_sessions(db, user.id, keep_token=None)
        record_event(
            db, action="PASSWORD_RESET_BY_OPERATOR", actor_id="resetuj_haslo",
            subject_ids=[user.id],
            payload={"sessions_revoked": uniewaznione,
                     "mfa_cleared": mialo_mfa,
                     "delivery": "workflow_artifact"},
            summary=f"Awaryjny reset hasła startowego ({email}); "
            "unieważniono aktywne sesje",
        )
        db.commit()
        return user.id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Awaryjny reset hasła istniejącego konta. Hasło "
        "WYŁĄCZNIE przez DZIK_RESET_PASSWORD."
    )
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    password = os.environ.get("DZIK_RESET_PASSWORD", "")
    if not password:
        print("BŁĄD: Ustaw DZIK_RESET_PASSWORD w środowisku "
              "(nie w argumentach).", file=sys.stderr)
        return 1
    try:
        user_id = resetuj_haslo(args.email, password)
    except ValueError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(f"Zresetowano hasło konta {args.email} ({user_id}): hasło "
          "jednorazowe (wymuszona zmiana przy logowaniu), aktywne sesje "
          "unieważnione.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

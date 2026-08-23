"""Pierwsze konta na PUSTEJ bazie produkcyjnej: `python -m dzik_os.bootstrap`.

Po wyłączeniu seeda (pilotaż, 0.43.0) nie istnieje żadna inna droga do
konta z rolą COACH/ADMIN: rejestracji nie ma, `routers/clients.py` nadaje
wyłącznie CLIENT i wymaga zalogowanego trenera, a seed był jedynym
miejscem nadającym role wyższe. To narzędzie zamyka tę pułapkę.

Zasady:

* **Hasła wyłącznie ze zmiennych środowiskowych** (`DZIK_BOOTSTRAP_COACH_PASSWORD`,
  `DZIK_BOOTSTRAP_ADMIN_PASSWORD`) — nigdy z argumentów wiersza poleceń,
  bo argv widać w `ps` i w historii powłoki.
* Działa tylko, gdy w bazie nie ma jeszcze żadnego konta z rolą
  COACH ani ADMIN — na zasianej/działającej bazie odmawia, niczego nie
  nadpisując.
* Konta powstają z `must_change_password=True`: hasło startowe jest
  jednorazowe, aplikacja wymusi zmianę przy pierwszym logowaniu
  (egzekwowane w `security.current_user`).
* Każde założenie konta trafia do dziennika zdarzeń (audyt).

Użycie (na maszynie Fly, po SSH):

    DZIK_BOOTSTRAP_COACH_PASSWORD='...' DZIK_BOOTSTRAP_ADMIN_PASSWORD='...' \\
    python -m dzik_os.bootstrap \\
        --coach-email trener@twojadomena.pl --coach-name "Imię Nazwisko" \\
        --admin-email admin@twojadomena.pl
"""

from __future__ import annotations

import argparse
import os
import sys

from .config import settings
from .db import db_session, run_migrations
from .hos_bridge import record_event
from .models import RoleGrant, User, new_id
from .security import hash_password

MIN_PASSWORD_LEN = 12


def _blad(msg: str) -> int:
    print(f"BŁĄD: {msg}", file=sys.stderr)
    return 1


def bootstrap(
    coach_email: str,
    coach_password: str,
    admin_email: str,
    admin_password: str,
    coach_name: str = "Trener",
    admin_name: str = "Administrator",
) -> dict[str, str]:
    """Zakłada konto trenera i admina. Zwraca {email: id}. Rzuca ValueError,
    gdy warunki nie są spełnione — wołający (CLI/test) decyduje, jak to
    pokazać."""
    for label, password in (("trenera", coach_password), ("admina", admin_password)):
        if len(password) < MIN_PASSWORD_LEN:
            raise ValueError(
                f"Hasło {label} ma mniej niż {MIN_PASSWORD_LEN} znaków."
            )
    if coach_email.strip().lower() == admin_email.strip().lower():
        raise ValueError("Konto trenera i admina muszą mieć różne adresy.")

    settings.ensure_dirs()
    run_migrations()
    with db_session() as db:
        zajete = (
            db.query(RoleGrant)
            .filter(RoleGrant.role.in_(("COACH", "ADMIN")))
            .count()
        )
        if zajete:
            raise ValueError(
                "W bazie istnieje już konto z rolą COACH albo ADMIN — "
                "bootstrap działa wyłącznie na pustej bazie. Do zarządzania "
                "istniejącymi kontami użyj aplikacji."
            )
        wynik: dict[str, str] = {}
        for email, password, name, role in (
            (coach_email, coach_password, coach_name, "COACH"),
            (admin_email, admin_password, admin_name, "ADMIN"),
        ):
            email = email.strip().lower()
            if db.query(User).filter(User.email == email).count():
                raise ValueError(f"Konto {email} już istnieje.")
            user = User(
                id=new_id("USR"),
                email=email,
                password_hash=hash_password(password),
                display_name=name,
                identity_id=new_id("ID"),
                must_change_password=True,
            )
            db.add(user)
            db.flush()
            db.add(RoleGrant(id=new_id("ROL"), user_id=user.id, role=role,
                             scope="*", issued_by="bootstrap"))
            record_event(
                db, action="IDENTITY_REGISTERED", actor_id="bootstrap",
                subject_ids=[user.id],
                payload={"identity_id": user.identity_id,
                         "identity_type": "HUMAN", "role": role,
                         "display_name": name, "demo": False},
                summary=f"Bootstrap: pierwsze konto {role} ({email})",
            )
            wynik[email] = user.id
        db.commit()
        return wynik


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pierwsze konto trenera i admina na pustej bazie. "
        "Hasła WYŁĄCZNIE przez DZIK_BOOTSTRAP_COACH_PASSWORD i "
        "DZIK_BOOTSTRAP_ADMIN_PASSWORD."
    )
    parser.add_argument("--coach-email", required=True)
    parser.add_argument("--coach-name", default="Trener")
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", default="Administrator")
    args = parser.parse_args(argv)

    coach_password = os.environ.get("DZIK_BOOTSTRAP_COACH_PASSWORD", "")
    admin_password = os.environ.get("DZIK_BOOTSTRAP_ADMIN_PASSWORD", "")
    if not coach_password or not admin_password:
        return _blad(
            "Ustaw DZIK_BOOTSTRAP_COACH_PASSWORD i "
            "DZIK_BOOTSTRAP_ADMIN_PASSWORD w środowisku (nie w argumentach)."
        )
    try:
        wynik = bootstrap(
            args.coach_email, coach_password, args.admin_email,
            admin_password, args.coach_name, args.admin_name,
        )
    except ValueError as exc:
        return _blad(str(exc))
    for email, user_id in wynik.items():
        print(f"Założono {email} ({user_id}) — hasło startowe jednorazowe, "
              "aplikacja wymusi zmianę przy pierwszym logowaniu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

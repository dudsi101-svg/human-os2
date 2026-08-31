"""Konto podopiecznego z zaplecza: `python -m dzik_os.dodaj_klienta`.

Normalna ścieżka to zaproszenie z panelu trenera (klient sam ustawia
hasło z jednorazowego linku). To narzędzie jest dla przypadków
operatorskich — trener niedostępny, a konto potrzebne od ręki (0.54.2,
potrzeba właściciela na żywo). Lustrzane do `dodaj_trenera`:

* **Hasło wyłącznie ze zmiennej środowiskowej** `DZIK_KLIENT_PASSWORD`
  (workflow wstawia ją jako chwilowy sekret Fly i kasuje po użyciu;
  nigdy argv).
* Konto powstaje ACTIVE z `must_change_password=True` — hasło startowe
  jest jednorazowe; właściciel konta ustawia własne przy pierwszym
  logowaniu.
* Relacja trener–podopieczny powstaje od razu jako ACTIVE (to jest
  sens tego narzędzia); trener wskazany e-mailem musi istnieć, być
  aktywny i mieć rolę COACH.
* Limit `DZIK_MAX_CLIENTS` honorowany tak samo jak w panelu trenera.
* Rejestracja konta i relacji w dzienniku zdarzeń (bez hasła).

Użycie (na maszynie Fly przez `flyctl ssh console` albo lokalnie):

    DZIK_KLIENT_PASSWORD='...' \\
    python -m dzik_os.dodaj_klienta --email osoba@example.com \\
        --coach-email trener@example.com [--name Podopieczny]
"""

from __future__ import annotations

import argparse
import os
import sys

from .bootstrap import MIN_PASSWORD_LEN
from .config import settings
from .db import db_session, run_migrations
from .hos_bridge import record_event
from .models import CoachClientRelationship, RoleGrant, User, new_id
from .security import hash_password


def dodaj_klienta(email: str, coach_email: str, password: str,
                  name: str = "Podopieczny") -> str:
    """Zakłada konto CLIENT z aktywną relacją do trenera. Zwraca id
    użytkownika. Rzuca ValueError, gdy warunki nie są spełnione."""
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Hasło ma mniej niż {MIN_PASSWORD_LEN} znaków.")
    email = email.strip().lower()
    coach_email = coach_email.strip().lower()
    settings.ensure_dirs()
    run_migrations()
    with db_session() as db:
        if db.query(User).filter(User.email == email).count():
            raise ValueError(f"Konto {email} już istnieje.")
        coach = db.query(User).filter(User.email == coach_email).one_or_none()
        if coach is None or coach.status != "ACTIVE":
            raise ValueError(f"Trener {coach_email} nie istnieje albo jest nieaktywny.")
        role_trenera = db.query(RoleGrant).filter(
            RoleGrant.user_id == coach.id, RoleGrant.role == "COACH",
            RoleGrant.revoked_at.is_(None),
        ).count()
        if not role_trenera:
            raise ValueError(f"Konto {coach_email} nie ma aktywnej roli COACH.")
        if settings.max_clients > 0:
            zajete = db.query(CoachClientRelationship).filter(
                CoachClientRelationship.coach_id == coach.id,
                CoachClientRelationship.status.in_(("ACTIVE", "PAUSED")),
            ).count()
            if zajete >= settings.max_clients:
                raise ValueError(
                    f"Limit podopiecznych ({settings.max_clients}) jest osiągnięty."
                )
        user = User(
            id=new_id("USR"), email=email,
            password_hash=hash_password(password), display_name=name,
            identity_id=new_id("ID"), must_change_password=True,
        )
        db.add(user)
        db.flush()
        db.add(RoleGrant(id=new_id("ROL"), user_id=user.id, role="CLIENT",
                         scope="*", issued_by="dodaj_klienta"))
        rel = CoachClientRelationship(
            id=new_id("REL"), coach_id=coach.id, client_id=user.id,
            created_by="dodaj_klienta",
        )
        db.add(rel)
        record_event(
            db, action="IDENTITY_REGISTERED", actor_id="dodaj_klienta",
            subject_ids=[user.id],
            payload={"identity_id": user.identity_id,
                     "identity_type": "HUMAN", "role": "CLIENT",
                     "display_name": name, "demo": False},
            summary=f"Konto podopiecznego założone operatorsko ({email})",
        )
        record_event(
            db, action="RELATIONSHIP_CREATED", actor_id="dodaj_klienta",
            subject_ids=[coach.id, user.id],
            payload={"relationship_id": rel.id, "status": "ACTIVE"},
            summary="Relacja trener-podopieczny utworzona operatorsko",
        )
        db.commit()
        return user.id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Konto podopiecznego z aktywną relacją do trenera. "
        "Hasło WYŁĄCZNIE przez DZIK_KLIENT_PASSWORD."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--coach-email", required=True)
    parser.add_argument("--name", default="Podopieczny")
    args = parser.parse_args(argv)

    password = os.environ.get("DZIK_KLIENT_PASSWORD", "")
    if not password:
        print("BŁĄD: Ustaw DZIK_KLIENT_PASSWORD w środowisku "
              "(nie w argumentach).", file=sys.stderr)
        return 1
    try:
        user_id = dodaj_klienta(args.email, args.coach_email, password, args.name)
    except ValueError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(f"Założono konto CLIENT {args.email} ({user_id}) z aktywną relacją "
          f"do {args.coach_email} — hasło startowe jednorazowe, aplikacja "
          "wymusi zmianę przy pierwszym logowaniu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

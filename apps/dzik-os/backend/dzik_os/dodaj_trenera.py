"""Kolejne konto trenera na DZIAŁAJĄCEJ bazie: `python -m dzik_os.dodaj_trenera`.

Bootstrap zakłada pierwsze konta i słusznie odmawia na niepustej bazie;
panel admina jest tylko do odczytu. To narzędzie wypełnia lukę pomiędzy:
jedno konto COACH na raz, na dowolnej bazie (0.53.1 — potrzeba
właściciela: konto trenerskie do przeglądania i testów).

Zasady identyczne jak w bootstrap.py:

* **Hasło wyłącznie ze zmiennej środowiskowej**
  `DZIK_BOOTSTRAP_COACH_PASSWORD` (ten sam kanał co bootstrap — workflow
  wstawia ją jako chwilowy sekret Fly i kasuje po użyciu; nigdy argv).
* Konto powstaje z `must_change_password=True` — hasło startowe jest
  jednorazowe.
* Odmowa, gdy e-mail jest już zajęty (żadnego nadpisywania).
* Założenie konta trafia do dziennika zdarzeń (audyt).

Użycie (na maszynie Fly przez `flyctl ssh console` albo lokalnie):

    DZIK_BOOTSTRAP_COACH_PASSWORD='...' \\
    python -m dzik_os.dodaj_trenera --email trener2@example.com \\
        [--name Trener]
"""

from __future__ import annotations

import argparse
import os
import sys

from .bootstrap import MIN_PASSWORD_LEN
from .config import settings
from .db import db_session, run_migrations
from .hos_bridge import record_event
from .models import RoleGrant, User, new_id
from .security import hash_password


def dodaj_trenera(email: str, password: str, name: str = "Trener") -> str:
    """Zakłada konto COACH. Zwraca id użytkownika. Rzuca ValueError,
    gdy warunki nie są spełnione."""
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(
            f"Hasło ma mniej niż {MIN_PASSWORD_LEN} znaków."
        )
    email = email.strip().lower()
    settings.ensure_dirs()
    run_migrations()
    with db_session() as db:
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
        db.add(RoleGrant(id=new_id("ROL"), user_id=user.id, role="COACH",
                         scope="*", issued_by="dodaj_trenera"))
        record_event(
            db, action="IDENTITY_REGISTERED", actor_id="dodaj_trenera",
            subject_ids=[user.id],
            payload={"identity_id": user.identity_id,
                     "identity_type": "HUMAN", "role": "COACH",
                     "display_name": name, "demo": False},
            summary=f"Dodano kolejne konto COACH ({email})",
        )
        db.commit()
        return user.id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kolejne konto trenera na działającej bazie. Hasło "
        "WYŁĄCZNIE przez DZIK_BOOTSTRAP_COACH_PASSWORD."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Trener")
    args = parser.parse_args(argv)

    password = os.environ.get("DZIK_BOOTSTRAP_COACH_PASSWORD", "")
    if not password:
        print("BŁĄD: Ustaw DZIK_BOOTSTRAP_COACH_PASSWORD w środowisku "
              "(nie w argumentach).", file=sys.stderr)
        return 1
    try:
        user_id = dodaj_trenera(args.email, password, args.name)
    except ValueError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(f"Założono konto COACH {args.email} ({user_id}) — hasło startowe "
          "jednorazowe, aplikacja wymusi zmianę przy pierwszym logowaniu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

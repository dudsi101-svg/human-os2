"""Dezaktywacja kont demo przed pilotażem: `python -m dzik_os.purge_demo`.

Konta demo mają hasła zapisane jawnie w publicznym repozytorium
(`seed.py`, README, testy). Zasiane raz na produkcji ZOSTAJĄ — bezpiecznik
seeda („baza nie jest pusta") działa tylko do przodu. To narzędzie
sprawia, że znane hasła przestają działać.

Świadomie DEZAKTYWUJE, a nie kasuje:

* usunięcie danych osoby to osobna ścieżka RODO (`/api/privacy`) z własnymi
  regułami anonimizacji;
* ręczne kasowanie wierszy z kluczami obcymi (plany, wiadomości, płatności,
  audyt) to ryzyko naruszenia integralności — dokładnie ten rodzaj cichego
  zepsucia, przed którym projekt się broni;
* cel bezpieczeństwa — „nikt nie zaloguje się znanym hasłem" — dezaktywacja
  realizuje w całości: status `SUSPENDED` (login filtruje `ACTIVE`) plus
  podmiana hasha na losowy, żeby ewentualny powrót do `ACTIVE` nie
  przywrócił starego hasła.

Bezpiecznik: odmawia, jeśli po dezaktywacji nie zostałby żaden AKTYWNY
trener spoza listy demo — najpierw `python -m dzik_os.bootstrap`, potem
purge. Nie da się zamknąć wszystkich drzwi naraz.
"""

from __future__ import annotations

import argparse
import secrets
import sys

from .db import db_session, run_migrations
from .hos_bridge import record_event
from .models import RoleGrant, User
from .security import hash_password
from .seed import DEMO_ACCOUNTS

#: Adresy kont demo — z tej samej stałej, którą zasiewa seed. Jedno źródło
#: prawdy: nowe konto demo w seedzie automatycznie podlega dezaktywacji.
DEMO_EMAILS = tuple(email for email, _, _ in DEMO_ACCOUNTS.values())


def purge_demo(*, force: bool = False) -> list[str]:
    """Dezaktywuje konta demo. Zwraca listę dezaktywowanych adresów.
    Rzuca ValueError, gdy zabrakłoby aktywnego trenera spoza demo
    (chyba że `force=True` — świadoma decyzja wołającego)."""
    run_migrations()
    with db_session() as db:
        demo = db.query(User).filter(User.email.in_(DEMO_EMAILS)).all()
        if not demo:
            return []
        if not force:
            aktywni_trenerzy_spoza_demo = (
                db.query(User)
                .join(RoleGrant, RoleGrant.user_id == User.id)
                .filter(
                    RoleGrant.role == "COACH",
                    User.status == "ACTIVE",
                    User.email.notin_(DEMO_EMAILS),
                )
                .count()
            )
            if aktywni_trenerzy_spoza_demo == 0:
                raise ValueError(
                    "Po dezaktywacji kont demo nie zostałby żaden aktywny "
                    "trener — najpierw załóż prawdziwe konto "
                    "(python -m dzik_os.bootstrap), potem uruchom purge. "
                    "Jeśli wiesz, co robisz: --force."
                )
        wylaczone: list[str] = []
        for user in demo:
            user.status = "SUSPENDED"
            # Losowy sekret, którego nikt nie zna — powrót do ACTIVE nie
            # przywróci hasła z publicznego repozytorium.
            user.password_hash = hash_password(secrets.token_urlsafe(32))
            record_event(
                db, action="IDENTITY_SUSPENDED", actor_id="purge_demo",
                subject_ids=[user.id],
                payload={"email": user.email, "reason": "konto demo przed "
                         "pilotażem; znane hasło unieważnione"},
                summary=f"Purge demo: dezaktywacja {user.email}",
            )
            wylaczone.append(user.email)
        db.commit()
        return wylaczone


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dezaktywuje konta demo (@example.com z seeda): status "
        "SUSPENDED + losowy hash hasła. Nie kasuje danych."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="pomiń bezpiecznik wymagający aktywnego trenera spoza demo",
    )
    args = parser.parse_args(argv)
    try:
        wylaczone = purge_demo(force=args.force)
    except ValueError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    if not wylaczone:
        print("Brak kont demo w bazie — nic do zrobienia.")
        return 0
    for email in wylaczone:
        print(f"Dezaktywowano {email} (SUSPENDED, hasło unieważnione).")
    print("Dane kont zostają w bazie; ewentualne usunięcie danych to "
          "osobna ścieżka RODO.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

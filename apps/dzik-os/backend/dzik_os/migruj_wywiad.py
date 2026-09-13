"""Narzędzie operatora: migracja sesji rozmowy startowej i głębokiego
wywiadu do zakładki „Wywiad” (0.59.0).

    python -m dzik_os.migruj_wywiad --raport    # liczby kontrolne, bez zapisu
    python -m dzik_os.migruj_wywiad --wykonaj   # ponawialnie; bez powiadomień

Raport zawiera liczby przed/po i identyfikatory sesji do ręcznej
weryfikacji — NIGDY treści odpowiedzi. Aplikacja wykonuje tę samą
migrację idempotentnie przy każdym starcie (`main.lifespan`).
"""

from __future__ import annotations

import argparse
import json
import sys

from .db import db_session, run_migrations
from .wywiad import migracja


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Migracja wywiadu do zakładki „Wywiad”")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--raport", action="store_true", help="tylko liczby kontrolne (bez zapisu)")
    g.add_argument("--wykonaj", action="store_true", help="wykonaj migrację (ponawialnie)")
    args = p.parse_args(argv)
    run_migrations()
    with db_session() as db:
        raport = migracja.migruj(db, wykonaj=bool(args.wykonaj))
    print(json.dumps(raport, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

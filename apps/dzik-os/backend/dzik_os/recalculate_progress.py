"""Backfill postępów (0.66.0, spec §11.3): przelicza rekordy osobiste i
agregaty tygodnia z całej historii sesji — idempotentnie (dwukrotne
uruchomienie = identyczny stan), dla jednego klienta albo wszystkich.

    python -m dzik_os.recalculate_progress            # wszyscy klienci z sesjami
    python -m dzik_os.recalculate_progress --client HOS-USR-…

Raport na stdout: per klient liczba ćwiczeń, rekordów (aktualnych / razem),
tygodni oraz „bliźniaki” nazw ćwiczeń (do decyzji trenera — nie scalane).
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import distinct

from .db import db_session
from .models import WorkoutSession
from .postepy import serwis


def przelicz(client_id: str | None = None) -> list[dict]:
    raporty: list[dict] = []
    with db_session() as db:
        if client_id:
            ids = [client_id]
        else:
            ids = [cid for (cid,) in db.query(distinct(WorkoutSession.client_id)).order_by(WorkoutSession.client_id).all()]
        for cid in ids:
            raporty.append(serwis.przelicz_klienta(db, cid))
    return raporty


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Przeliczenie rekordów i agregatów postępów.")
    parser.add_argument("--client", help="id klienta (domyślnie: wszyscy z sesjami)")
    parser.add_argument("--json", action="store_true", help="raport jako JSON")
    args = parser.parse_args(argv)
    raporty = przelicz(args.client)
    if args.json:
        print(json.dumps(raporty, ensure_ascii=False, indent=2))
    else:
        for r in raporty:
            print(f"{r['client_id']}: ćwiczeń {r['cwiczenia']}, rekordów {r['rekordy_aktualne']} aktualnych / "
                  f"{r['rekordy_razem']} razem, tygodni {r['tygodnie']}"
                  + (f", bliźniaki: {r['blizniaki']}" if r["blizniaki"] else ""))
        print(f"Przeliczono klientów: {len(raporty)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

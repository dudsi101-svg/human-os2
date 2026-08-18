"""Historia importów z pliku i cofanie jednego importu.

Wspólne dla obu baz (ćwiczenia, szablony), bo mechanizm jest jeden —
patrz `sheet_import.undo_import`.

DLACZEGO TO ISTNIEJE. Plany i diety mają niemutowalną historię wersji,
więc pomyłka jest tam odwracalna z definicji. **Ćwiczenia historii nie
mają**: import w trybie ZASTAP nadpisuje opis techniki napisany przez
trenera i bez punktu przywracania byłaby to strata bezpowrotna. Migawka
zdejmowana przed zapisem zamyka tę dziurę.

Czego cofnięcie NIE robi: nie kasuje. Pozycja utworzona przez import
zostaje zarchiwizowana, szablon wraca przez NOWĄ wersję z dawną treścią.
Historia — łącznie z samym importem i jego cofnięciem — zostaje w całości.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import sheet_import
from ..authz import require_owned_resource
from ..db import get_db
from ..hos_bridge import record_event
from ..models import ImportSnapshot, User
from ..security import require_role

router = APIRouter(prefix="/api", tags=["imports"])


@router.get("/coach/imports")
def list_imports(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    """Ostatnie importy z pliku wraz z informacją, które da się jeszcze
    cofnąć. Wyłącznie własne — `coach_id` bierze się z sesji."""
    rows = (
        db.query(ImportSnapshot)
        .filter(ImportSnapshot.coach_id == coach.id)
        .order_by(ImportSnapshot.created_at.desc())
        .all()
    )
    return {
        "imports": [sheet_import.snapshot_out(r) for r in rows],
        "keep": sheet_import.SNAPSHOT_KEEP,
    }


@router.post("/coach/imports/{snapshot_id}/undo")
def undo(
    snapshot_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Cofa jeden import do stanu sprzed niego.

    Cudzy albo nieistniejący identyfikator kończy się **404** — bez
    różnicy w komunikacie, żeby odpowiedź nie potwierdzała istnienia
    cudzego zasobu (ta sama reguła co w całej aplikacji)."""
    row = require_owned_resource(
        db.get(ImportSnapshot, snapshot_id), actor=coach, resource="import_snapshot",
    )
    try:
        result = sheet_import.undo_import(db, coach.id, row)
    except sheet_import.SheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_event(
        db, action="IMPORT_UNDONE", actor_id=coach.id, subject_ids=[coach.id],
        payload={
            "snapshot_id": row.id, "kind": row.kind, "source": row.source_ref,
            "mode": row.mode, **result,
        },
        summary=f"Cofnięcie importu z pliku „{row.source_ref}” — "
                f"{result['restored']} przywróconych, {result['archived']} zarchiwizowanych",
    )
    db.commit()
    return {"ok": True, "snapshot": sheet_import.snapshot_out(row), **result}

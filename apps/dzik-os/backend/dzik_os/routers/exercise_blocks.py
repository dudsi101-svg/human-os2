"""Bloki rozgrzewki i rozciągania — katalog trenera (0.73.0).

Broadcast trenera jak `Exercise`: własność trenera, bez danych klienta,
więc bez `resolve_client_access`; cudzy blok = 404 (`require_owned_resource`).
Archiwizacja zamiast kasowania. `load-builtin` ładuje idempotentnie 9
rozgrzewek + 3 bloki rozciągania (`cardio/bloki_wbudowane.py`, treść „do
przeglądu trenera”); pozycje dostają `exercise_id` po nazwie z aktywnej
bazy tego trenera (miękko — brak wpisu nie blokuje).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..authz import require_owned_resource
from ..cardio.bloki import migawka, zaladuj_wbudowane
from ..cardio.bloki_wbudowane import (
    ETYKIETY_RODZAJOW,
    ETYKIETY_WARIANTOW,
    RODZAJE,
    WARIANTY,
    ZRODLO_WBUDOWANE,
)
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Exercise, ExerciseBlock, User, new_id, now_iso
from ..muscles import EXERCISE_LEVELS
from ..schemas import BlockItemIn
from ..security import require_role

router = APIRouter(prefix="/api/coach/exercise-blocks", tags=["exercise-blocks"])


class BlockIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    kind: str = Field(pattern="^(WARMUP|STRETCH)$")
    level: str | None = Field(default=None, pattern="^(POCZATKUJACY|SREDNIOZAAWANSOWANY|ZAAWANSOWANY)$")
    variant: str = Field(pattern="^(G|D|C)$")
    duration_min: int | None = Field(default=None, ge=1, le=60)
    items: list[BlockItemIn] = Field(default=[], max_length=20)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(ACTIVE|ARCHIVED)$")


def _out(row: ExerciseBlock) -> dict:
    return {
        "id": row.id, "coach_id": row.coach_id, "kind_label": ETYKIETY_RODZAJOW[row.kind],
        "variant_label": ETYKIETY_WARIANTOW[row.variant], **migawka(row),
        "source": row.source, "status": row.status, "created_at": row.created_at, "updated_at": row.updated_at,
    }


def _sprawdz_exercise_ids(db: Session, coach: User, items: list[BlockItemIn]) -> None:
    """`exercise_id` w pozycji bloku musi wskazywać AKTYWNE ćwiczenie TEGO trenera (jak w planach)."""
    wanted = {i.exercise_id for i in items if i.exercise_id}
    if not wanted:
        return
    known = {r.id for r in db.query(Exercise).filter(Exercise.id.in_(wanted), Exercise.coach_id == coach.id,
                                                     Exercise.status == "ACTIVE").all()}
    missing = sorted(wanted - known)
    if missing:
        raise HTTPException(status_code=422, detail="Ćwiczenie spoza Twojej aktywnej bazy: " + ", ".join(missing))


def _apply(row: ExerciseBlock, body: BlockIn) -> None:
    if body.kind == "STRETCH":
        body.level = None
    row.name, row.kind, row.level, row.variant = body.name, body.kind, body.level, body.variant
    row.duration_min = body.duration_min
    row.items_json = json.dumps([i.model_dump() for i in body.items], ensure_ascii=False)
    row.updated_at = now_iso()


@router.get("")
def list_blocks(
    status: str = Query(default="ACTIVE", pattern="^(ACTIVE|ARCHIVED|all)$"),
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    q = db.query(ExerciseBlock).filter(ExerciseBlock.coach_id == coach.id)
    if status != "all":
        q = q.filter(ExerciseBlock.status == status)
    rows = q.order_by(ExerciseBlock.kind.desc(), ExerciseBlock.level.asc(), ExerciseBlock.variant.asc(),
                      ExerciseBlock.name.asc()).all()
    return {"items": [_out(r) for r in rows], "dictionaries": {
        "kinds": ETYKIETY_RODZAJOW, "variants": ETYKIETY_WARIANTOW, "levels": list(EXERCISE_LEVELS)}}


@router.post("", status_code=201)
def create_block(body: BlockIn, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    _sprawdz_exercise_ids(db, coach, body.items)
    row = ExerciseBlock(id=new_id("BLK"), coach_id=coach.id, created_by=coach.id, source="trener")
    _apply(row, body)
    db.add(row)
    record_event(db, action="EXERCISE_BLOCK_CREATED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"block_id": row.id, "kind": row.kind, "level": row.level, "variant": row.variant},
                 summary=f"Bloki: dodano „{row.name}”")
    db.commit()
    return _out(row)


@router.post("/load-builtin")
def load_builtin(coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    """Idempotentne ładowanie 9 rozgrzewek + 3 bloków rozciągania (`cardio/bloki.py`)."""
    raport = zaladuj_wbudowane(db, coach.id)
    if raport["created"]:
        record_event(db, action="EXERCISE_BLOCKS_BUILTIN_LOADED", actor_id=coach.id, subject_ids=[coach.id],
                     payload={k: raport[k] for k in ("created", "skipped", "items_without_card")},
                     summary=f"Bloki: załadowano {raport['created']} wbudowanych (pominięto {raport['skipped']})")
    db.commit()
    return {k: raport[k] for k in ("created", "skipped", "items_without_card", "total_builtin")} | {
        "kinds": list(RODZAJE), "variants": list(WARIANTY), "review": ZRODLO_WBUDOWANE}


@router.get("/{block_id}")
def get_block(block_id: str, coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)):
    row = db.get(ExerciseBlock, block_id)
    require_owned_resource(row, actor=coach, resource=f"exercise_block:{block_id}")
    return _out(row)


@router.put("/{block_id}")
def update_block(block_id: str, body: BlockIn, coach: User = Depends(require_role("COACH")),
                 db: Session = Depends(get_db)):
    row = db.get(ExerciseBlock, block_id)
    require_owned_resource(row, actor=coach, resource=f"exercise_block:{block_id}")
    _sprawdz_exercise_ids(db, coach, body.items)
    _apply(row, body)
    if row.source == ZRODLO_WBUDOWANE:
        row.source = "wbudowany — zmieniony przez trenera"
    record_event(db, action="EXERCISE_BLOCK_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"block_id": row.id, "kind": row.kind}, summary=f"Bloki: zmieniono „{row.name}”")
    db.commit()
    return _out(row)


@router.post("/{block_id}/status")
def set_status(block_id: str, body: StatusIn, coach: User = Depends(require_role("COACH")),
               db: Session = Depends(get_db)):
    row = db.get(ExerciseBlock, block_id)
    require_owned_resource(row, actor=coach, resource=f"exercise_block:{block_id}")
    row.status = body.status
    row.updated_at = now_iso()
    record_event(db, action="EXERCISE_BLOCK_STATUS", actor_id=coach.id, subject_ids=[coach.id],
                 payload={"block_id": row.id, "status": row.status},
                 summary=f"Bloki: „{row.name}” → {row.status}")
    db.commit()
    return _out(row)

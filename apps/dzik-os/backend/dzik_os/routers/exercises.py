"""Baza ćwiczeń (know-how trenera) — technika wykonania i efekt, z
podziałem na partie mięśniowe. Broadcast do wszystkich aktywnie
prowadzonych klientów; treść i odpowiedzialność merytoryczna należą do
trenera (system tylko przechowuje i pokazuje)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import require_owned_resource
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, Exercise, User, new_id, now_iso
from ..schemas import ExerciseLibraryItemIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["exercises"])


def _out(item: Exercise) -> dict:
    return {
        "id": item.id, "coach_id": item.coach_id, "name": item.name,
        "muscle_group": item.muscle_group, "how_to": item.how_to,
        "benefit": item.benefit, "equipment": item.equipment,
        "video_url": item.video_url, "status": item.status,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


@router.post("/coach/exercises", status_code=201)
def create_exercise(
    body: ExerciseLibraryItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = Exercise(
        id=new_id("EXC"), coach_id=coach.id, name=body.name,
        muscle_group=body.muscle_group, how_to=body.how_to, benefit=body.benefit,
        equipment=body.equipment, video_url=body.video_url, created_by=coach.id,
    )
    db.add(item)
    record_event(
        db, action="EXERCISE_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"exercise_id": item.id, "name": item.name, "muscle_group": item.muscle_group},
        summary=f"Baza ćwiczeń: dodano „{item.name}” ({item.muscle_group})",
    )
    db.commit()
    return _out(item)


@router.get("/coach/exercises")
def list_own_exercises(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    rows = (
        db.query(Exercise)
        .filter(Exercise.coach_id == coach.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    return {"items": [_out(i) for i in rows]}


@router.put("/coach/exercises/{item_id}")
def update_exercise(
    item_id: str,
    body: ExerciseLibraryItemIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    item = require_owned_resource(
        db.get(Exercise, item_id), actor=coach, resource=f"exercise:{item_id}"
    )
    item.name, item.muscle_group, item.how_to = body.name, body.muscle_group, body.how_to
    item.benefit, item.equipment, item.video_url = body.benefit, body.equipment, body.video_url
    item.updated_at = now_iso()
    record_event(
        db, action="EXERCISE_UPDATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"exercise_id": item.id, "name": item.name},
        summary=f"Baza ćwiczeń: zaktualizowano „{item.name}”",
    )
    db.commit()
    return _out(item)


@router.post("/coach/exercises/{item_id}/status")
def set_exercise_status(
    item_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "ARCHIVED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = require_owned_resource(
        db.get(Exercise, item_id), actor=coach, resource=f"exercise:{item_id}"
    )
    item.status = status
    item.updated_at = now_iso()
    db.commit()
    return {"ok": True, "status": status}


@router.get("/me/exercises")
def list_exercises_for_client(
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    coach_ids = [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]
    if not coach_ids:
        return {"items": []}
    rows = (
        db.query(Exercise)
        .filter(Exercise.coach_id.in_(coach_ids), Exercise.status == "ACTIVE")
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    return {"items": [_out(i) for i in rows]}

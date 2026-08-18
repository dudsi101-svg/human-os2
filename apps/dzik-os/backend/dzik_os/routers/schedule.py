from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import DOMAIN_TRAINING, resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..models import Reminder, ScheduleItem, User, new_id, now_iso
from ..schemas import ReminderIn, ScheduleItemIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["schedule"])


def _item_out(i: ScheduleItem) -> dict:
    return {
        "id": i.id,
        "name": i.name,
        "category": i.category,
        "time_of_day": i.time_of_day,
        "days_of_week": i.days_of_week,
        "instruction": i.instruction,
        "start_date": i.start_date,
        "end_date": i.end_date,
        "author_id": i.author_id,
        "author_note": i.author_note,
        "status": i.status,
        "version": i.version,
    }


@router.post("/schedule", status_code=201)
def create_schedule_item(
    body: ScheduleItemIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Element harmonogramu może dodać trener lub sam klient. Autor zalecenia
    jest zawsze zapisany (proweniencja). System wyłącznie przechowuje plan
    wprowadzony przez człowieka — nie dobiera i nie modyfikuje dawkowania."""
    resolve_client_access(db, user, body.client_id, action="write", domain=DOMAIN_TRAINING)
    item = ScheduleItem(
        id=new_id("SCH"),
        client_id=body.client_id,
        name=body.name,
        category=body.category,
        time_of_day=body.time_of_day,
        days_of_week=body.days_of_week,
        instruction=body.instruction,
        start_date=body.start_date,
        end_date=body.end_date,
        author_id=user.id,
        author_note=body.author_note,
    )
    db.add(item)
    record_event(
        db,
        action="SCHEDULE_ITEM_CREATED",
        actor_id=user.id,
        subject_ids=[body.client_id],
        payload={"item_id": item.id, "name": item.name, "category": item.category,
                 "author_id": user.id},
        summary=f"Harmonogram: dodano '{item.name}' ({item.category})",
    )
    db.commit()
    return {"id": item.id}


@router.get("/clients/{client_id}/schedule")
def list_schedule(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_TRAINING)
    rows = (
        db.query(ScheduleItem)
        .filter(ScheduleItem.client_id == client_id)
        .order_by(ScheduleItem.time_of_day)
        .all()
    )
    return {"items": [_item_out(i) for i in rows]}


@router.post("/schedule/{item_id}/status")
def set_schedule_status(
    item_id: str,
    status: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "PAUSED", "ENDED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    item = db.get(ScheduleItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    resolve_client_access(db, user, item.client_id, action="write", domain=DOMAIN_TRAINING)
    previous = item.status
    item.status = status
    item.updated_at = now_iso()
    item.version += 1
    record_event(
        db,
        action="SCHEDULE_ITEM_STATUS_CHANGED",
        actor_id=user.id,
        subject_ids=[item.client_id],
        payload={"item_id": item.id, "from": previous, "to": status},
        summary=f"Harmonogram '{item.name}': {previous} → {status}",
    )
    db.commit()
    return {"ok": True}


@router.post("/reminders", status_code=201)
def create_reminder(
    body: ReminderIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, body.client_id, action="write", domain=DOMAIN_TRAINING)
    reminder = Reminder(
        id=new_id("RMD"),
        client_id=body.client_id,
        text=body.text,
        due_date=body.due_date,
        created_by=coach.id,
    )
    db.add(reminder)
    db.commit()
    return {"id": reminder.id}


@router.get("/clients/{client_id}/reminders")
def list_reminders(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, domain=DOMAIN_TRAINING)
    rows = (
        db.query(Reminder)
        .filter(Reminder.client_id == client_id, Reminder.status == "ACTIVE")
        .order_by(Reminder.due_date)
        .all()
    )
    return {
        "reminders": [
            {"id": r.id, "text": r.text, "due_date": r.due_date, "created_by": r.created_by}
            for r in rows
        ]
    }

"""Terminarz konsultacji: trener wystawia sloty, klient rezerwuje.

Zasady (Human OS): rezerwacja jest zawsze odwoływalna — klient do 12 h
przed terminem, trener w każdej chwili (z powiadomieniem drugiej strony);
żadnych kar ani metryk za odwołania. Wszystkie zmiany audytowane."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import push_service
from ..authz import active_relationship
from ..config import settings
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, ConsultSlot, User, new_id, now_iso
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["consultations"])

CLIENT_CANCEL_HOURS = 12


def _now_local() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None)


class SlotIn(BaseModel):
    starts_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    duration_min: int = Field(default=30, ge=10, le=240)


def _out(slot: ConsultSlot, db: Session) -> dict:
    client_name = None
    if slot.client_id:
        client = db.get(User, slot.client_id)
        client_name = client.display_name if client else None
    return {
        "id": slot.id, "coach_id": slot.coach_id, "starts_at": slot.starts_at,
        "duration_min": slot.duration_min, "status": slot.status,
        "client_id": slot.client_id, "client_name": client_name,
        "booked_at": slot.booked_at,
    }


@router.post("/coach/consult-slots", status_code=201)
def create_slot(
    body: SlotIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if body.starts_at <= _now_local().strftime("%Y-%m-%dT%H:%M"):
        raise HTTPException(status_code=422, detail="Termin musi być w przyszłości")
    slot = ConsultSlot(
        id=new_id("CSL"), coach_id=coach.id, starts_at=body.starts_at,
        duration_min=body.duration_min,
    )
    db.add(slot)
    record_event(
        db, action="CONSULT_SLOT_CREATED", actor_id=coach.id, subject_ids=[coach.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at},
        summary=f"Nowy termin konsultacji: {slot.starts_at}",
    )
    db.commit()
    return _out(slot, db)


@router.get("/coach/consult-slots")
def coach_slots(
    coach: User = Depends(require_role("COACH")), db: Session = Depends(get_db)
):
    rows = (
        db.query(ConsultSlot)
        .filter(ConsultSlot.coach_id == coach.id, ConsultSlot.status != "CANCELLED")
        .order_by(ConsultSlot.starts_at)
        .all()
    )
    return {"slots": [_out(s, db) for s in rows]}


@router.post("/coach/consult-slots/{slot_id}/cancel")
def coach_cancel_slot(
    slot_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    slot = db.get(ConsultSlot, slot_id)
    if slot is None or slot.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    booked_client = slot.client_id
    slot.status = "CANCELLED"
    record_event(
        db, action="CONSULT_SLOT_CANCELLED", actor_id=coach.id,
        subject_ids=[booked_client or coach.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at,
                 "was_booked": booked_client is not None},
        summary=f"Odwołano termin konsultacji {slot.starts_at}",
    )
    if booked_client:
        push_service.send_to_user(
            db, booked_client, "Konsultacja odwołana",
            f"Trener odwołał konsultację {slot.starts_at.replace('T', ' ')}. "
            "Zarezerwuj nowy termin w aplikacji.", "/konsultacje",
        )
    db.commit()
    return {"ok": True}


@router.get("/me/consult-slots")
def client_slots(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Wolne sloty trenerów prowadzących + własne rezerwacje klienta."""
    coach_ids = [
        r.coach_id
        for r in db.query(CoachClientRelationship)
        .filter_by(client_id=user.id, status="ACTIVE")
        .all()
    ]
    now = _now_local().strftime("%Y-%m-%dT%H:%M")
    open_rows = (
        db.query(ConsultSlot)
        .filter(
            ConsultSlot.coach_id.in_(coach_ids) if coach_ids else False,
            ConsultSlot.status == "OPEN",
            ConsultSlot.starts_at > now,
        )
        .order_by(ConsultSlot.starts_at)
        .all()
    ) if coach_ids else []
    mine = (
        db.query(ConsultSlot)
        .filter(
            ConsultSlot.client_id == user.id,
            ConsultSlot.status == "BOOKED",
            ConsultSlot.starts_at > now,
        )
        .order_by(ConsultSlot.starts_at)
        .all()
    )
    return {
        "open": [_out(s, db) for s in open_rows],
        "booked": [_out(s, db) for s in mine],
    }


@router.post("/consult-slots/{slot_id}/book")
def book_slot(
    slot_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    slot = db.get(ConsultSlot, slot_id)
    if slot is None or slot.status != "OPEN":
        raise HTTPException(status_code=404, detail="Termin niedostępny")
    if not active_relationship(db, slot.coach_id, user.id):
        raise HTTPException(status_code=404, detail="Termin niedostępny")
    if slot.starts_at <= _now_local().strftime("%Y-%m-%dT%H:%M"):
        raise HTTPException(status_code=422, detail="Termin już minął")
    slot.status = "BOOKED"
    slot.client_id = user.id
    slot.booked_at = now_iso()
    record_event(
        db, action="CONSULT_SLOT_BOOKED", actor_id=user.id, subject_ids=[user.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at},
        summary=f"Rezerwacja konsultacji {slot.starts_at}",
    )
    push_service.send_to_user(
        db, slot.coach_id, "Nowa rezerwacja konsultacji",
        f"{user.display_name} zarezerwował(a) {slot.starts_at.replace('T', ' ')}.",
        "/trener/konsultacje",
    )
    db.commit()
    return _out(slot, db)


@router.post("/consult-slots/{slot_id}/unbook")
def unbook_slot(
    slot_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    slot = db.get(ConsultSlot, slot_id)
    if slot is None or slot.status != "BOOKED" or slot.client_id != user.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono rezerwacji")
    limit = (_now_local() + timedelta(hours=CLIENT_CANCEL_HOURS)).strftime("%Y-%m-%dT%H:%M")
    if slot.starts_at <= limit:
        raise HTTPException(
            status_code=422,
            detail=f"Rezerwację można odwołać najpóźniej {CLIENT_CANCEL_HOURS} h przed "
            "terminem — napisz do trenera wiadomość.",
        )
    slot.status = "OPEN"
    cancelling_client = user.display_name
    slot.client_id = None
    slot.booked_at = None
    record_event(
        db, action="CONSULT_SLOT_UNBOOKED", actor_id=user.id, subject_ids=[user.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at},
        summary=f"Odwołano rezerwację konsultacji {slot.starts_at}",
    )
    push_service.send_to_user(
        db, slot.coach_id, "Odwołana rezerwacja",
        f"{cancelling_client} odwołał(a) konsultację "
        f"{slot.starts_at.replace('T', ' ')} — termin znów wolny.",
        "/trener/konsultacje",
    )
    db.commit()
    return {"ok": True}

"""Terminarz konsultacji: trener wystawia sloty, klient rezerwuje.

Zasady (Human OS): rezerwacja jest zawsze odwoływalna — klient do 12 h
przed terminem, trener w każdej chwili (z powiadomieniem drugiej strony);
żadnych kar ani metryk za odwołania. Wszystkie zmiany audytowane."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import notifications
from ..authz import active_relationship, deny, require_owned_resource
from ..dates import local_now, local_now_minute, tz_for_user
from ..db import get_db
from ..hos_bridge import record_event
from ..models import CoachClientRelationship, ConsultSlot, User, new_id, now_iso
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["consultations"])

CLIENT_CANCEL_HOURS = 12


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
    if body.starts_at <= local_now_minute():
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
    slot = require_owned_resource(
        db.get(ConsultSlot, slot_id), actor=coach, resource=f"consult_slot:{slot_id}"
    )
    booked_client = slot.client_id
    slot.status = "CANCELLED"
    record_event(
        db, action="CONSULT_SLOT_CANCELLED", actor_id=coach.id,
        subject_ids=[booked_client or coach.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at,
                 "was_booked": booked_client is not None},
        summary=f"Odwołano termin konsultacji {slot.starts_at}",
    )
    # Odwołanie terminu anuluje zaplanowane przypomnienie przed konsultacją.
    notifications.cancel_source(db, f"consult_slot:{slot.id}")
    notification = None
    if booked_client:
        notification = notifications.notify_now(
            db,
            user_id=booked_client,
            category="KONSULTACJA",
            title="Konsultacja odwołana",
            body=f"Trener odwołał konsultację {slot.starts_at.replace('T', ' ')}. "
            "Zarezerwuj nowy termin w aplikacji.",
            url="/konsultacje",
            dedup_key=f"consult-cancel:{slot.id}:{now_iso()}",
        )
    db.commit()
    notifications.publish_realtime(notification)
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
    now = local_now_minute()
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
        # Slot istnieje, ale należy do trenera, z którym aktor nie ma
        # AKTYWNEJ relacji — logowana odmowa zasobowa (ta sama odpowiedź
        # 404, żeby nie ujawniać kalendarza obcego trenera).
        deny(user.id, f"consult_slot:{slot_id}")
    if slot.starts_at <= local_now_minute():
        raise HTTPException(status_code=422, detail="Termin już minął")
    slot.status = "BOOKED"
    slot.client_id = user.id
    slot.booked_at = now_iso()
    record_event(
        db, action="CONSULT_SLOT_BOOKED", actor_id=user.id, subject_ids=[user.id],
        payload={"slot_id": slot.id, "starts_at": slot.starts_at},
        summary=f"Rezerwacja konsultacji {slot.starts_at}",
    )
    notification = notifications.notify_now(
        db,
        user_id=slot.coach_id,
        category="KONSULTACJA",
        title="Nowa rezerwacja konsultacji",
        body=f"{user.display_name} zarezerwował(a) {slot.starts_at.replace('T', ' ')}.",
        url="/trener/konsultacje",
        dedup_key=f"consult-book:{slot.id}:{slot.booked_at}",
    )
    # Przypomnienie dla klienta 60 min przed startem (anulowane, gdy termin
    # zostanie odwołany albo rezerwacja zdjęta — punkt 9 modelu powiadomień).
    tz = tz_for_user(user)
    starts_local = datetime.strptime(slot.starts_at, "%Y-%m-%dT%H:%M").replace(tzinfo=tz)
    remind_utc = starts_local.astimezone(UTC) - timedelta(minutes=60)
    if remind_utc > datetime.now(UTC):
        notifications.schedule(
            db,
            user_id=user.id,
            category="KONSULTACJA",
            title=f"Konsultacja o {slot.starts_at[11:]}",
            body="Za godzinę masz konsultację z trenerem.",
            url="/konsultacje",
            source=f"consult_slot:{slot.id}",
            dedup_key=f"consult-remind:{slot.id}:{user.id}",
            scheduled_at_utc=remind_utc,
            timezone=str(tz),
        )
    db.commit()
    notifications.publish_realtime(notification)
    return _out(slot, db)


@router.post("/consult-slots/{slot_id}/unbook")
def unbook_slot(
    slot_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    slot = db.get(ConsultSlot, slot_id)
    if slot is None or slot.status != "BOOKED":
        raise HTTPException(status_code=404, detail="Nie znaleziono rezerwacji")
    if slot.client_id != user.id:
        # Cudza rezerwacja — logowana odmowa (nie zdradzamy, czyja jest).
        deny(user.id, f"consult_slot:{slot_id}")
    limit = (local_now() + timedelta(hours=CLIENT_CANCEL_HOURS)).strftime("%Y-%m-%dT%H:%M")
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
    # Zdjęcie rezerwacji anuluje zaplanowane przypomnienie klienta.
    notifications.cancel_source(db, f"consult_slot:{slot.id}")
    notification = notifications.notify_now(
        db,
        user_id=slot.coach_id,
        category="KONSULTACJA",
        title="Odwołana rezerwacja",
        body=f"{cancelling_client} odwołał(a) konsultację "
        f"{slot.starts_at.replace('T', ' ')} — termin znów wolny.",
        url="/trener/konsultacje",
        dedup_key=f"consult-unbook:{slot.id}:{now_iso()}",
    )
    db.commit()
    notifications.publish_realtime(notification)
    return {"ok": True}

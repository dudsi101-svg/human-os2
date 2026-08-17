from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import resolve_client_access
from ..db import get_db
from ..hos_bridge import record_event
from ..models import PaymentRecord, PaymentSchedule, User, new_id, now_iso
from ..payments_provider import provider
from ..schemas import PaymentScheduleIn, PaymentStatusIn
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/payments/schedules", status_code=201)
def create_schedule(
    body: PaymentScheduleIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    # Płatności nie są danymi zdrowotnymi — wystarczy aktywna relacja.
    resolve_client_access(db, coach, body.client_id, action="write", sensitive=False)
    schedule = PaymentSchedule(
        id=new_id("PSC"),
        client_id=body.client_id,
        coach_id=coach.id,
        package_name=body.package_name,
        amount_cents=body.amount_cents,
        currency=body.currency,
        period=body.period,
        external_link=body.external_link,
        created_by=coach.id,
    )
    db.add(schedule)
    record = PaymentRecord(
        id=new_id("PAY"),
        schedule_id=schedule.id,
        due_date=body.first_due_date,
        amount_cents=body.amount_cents,
        currency=body.currency,
    )
    db.add(record)
    record_event(
        db,
        action="PAYMENT_SCHEDULE_CREATED",
        actor_id=coach.id,
        subject_ids=[body.client_id],
        payload={"schedule_id": schedule.id, "package": body.package_name,
                 "amount_cents": body.amount_cents, "period": body.period,
                 "first_due_date": body.first_due_date},
        summary=f"Pakiet '{body.package_name}': {body.amount_cents/100:.2f} "
        f"{body.currency}, termin {body.first_due_date}",
    )
    db.commit()
    return {"schedule_id": schedule.id, "record_id": record.id}


@router.get("/clients/{client_id}/payments")
def client_payments(
    client_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, user, client_id, sensitive=False)
    schedules = (
        db.query(PaymentSchedule).filter(PaymentSchedule.client_id == client_id).all()
    )
    out = []
    for s in schedules:
        records = (
            db.query(PaymentRecord)
            .filter(PaymentRecord.schedule_id == s.id)
            .order_by(PaymentRecord.due_date.desc())
            .all()
        )
        out.append(
            {
                "schedule_id": s.id,
                "package_name": s.package_name,
                "amount_cents": s.amount_cents,
                "currency": s.currency,
                "period": s.period,
                "external_link": s.external_link,
                "status": s.status,
                "records": [
                    {
                        "id": r.id, "due_date": r.due_date,
                        "amount_cents": r.amount_cents, "currency": r.currency,
                        "status": r.status, "paid_at": r.paid_at, "note": r.note,
                        "payment_link": provider.payment_link(
                            record_id=r.id, amount_cents=r.amount_cents,
                            currency=r.currency, description=s.package_name,
                        ) or s.external_link,
                    }
                    for r in records
                ],
            }
        )
    return {"schedules": out, "provider": provider.name}


@router.post("/payments/records/{record_id}/status")
def set_payment_status(
    record_id: str,
    body: PaymentStatusIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    record = db.get(PaymentRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    schedule = db.get(PaymentSchedule, record.schedule_id)
    if schedule is None or schedule.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    previous = record.status
    record.status = body.status
    record.note = body.note
    record.marked_by = coach.id
    record.paid_at = now_iso() if body.status == "PAID" else None
    record_event(
        db,
        action="PAYMENT_STATUS_CHANGED",
        actor_id=coach.id,
        subject_ids=[schedule.client_id],
        payload={"record_id": record.id, "from": previous, "to": body.status,
                 "note": body.note},
        summary=f"Płatność {record.due_date}: {previous} → {body.status}",
    )
    db.commit()
    return {"ok": True, "status": body.status}


@router.post("/payments/schedules/{schedule_id}/records", status_code=201)
def add_payment_record(
    schedule_id: str,
    due_date: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    schedule = db.get(PaymentSchedule, schedule_id)
    if schedule is None or schedule.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    record = PaymentRecord(
        id=new_id("PAY"),
        schedule_id=schedule.id,
        due_date=due_date,
        amount_cents=schedule.amount_cents,
        currency=schedule.currency,
    )
    db.add(record)
    db.commit()
    return {"id": record.id}

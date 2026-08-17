from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import CONSENT_DOMAIN, CONSENT_PURPOSE, active_relationship, resolve_client_access
from ..db import get_db
from ..hos_bridge import ConsentService, record_event
from ..models import (
    CoachClientRelationship,
    Message,
    MessageThread,
    PaymentRecord,
    PaymentSchedule,
    RoleGrant,
    User,
    WeeklyCheckin,
    WorkoutSession,
    new_id,
    now_iso,
)
from ..schemas import RelationshipIn
from ..security import hash_password, require_role

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/clients", status_code=201)
def create_client(
    body: RelationshipIn,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Zakłada konto klienta i aktywną współpracę. Zgoda na przetwarzanie
    danych zdrowotnych jest rejestrowana jako deklaracja z onboardingu
    (proweniencja jawna w audycie); klient widzi ją w aplikacji i może ją
    w każdej chwili cofnąć."""
    email = body.client_email.lower()
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        client = existing
        if active_relationship(db, coach.id, client.id):
            raise HTTPException(status_code=409, detail="Współpraca już istnieje")
    else:
        client = User(
            id=new_id("USR"),
            email=email,
            password_hash=hash_password(body.initial_password),
            display_name=body.client_name,
            identity_id=new_id("ID"),
            status="ACTIVE",
        )
        db.add(client)
        db.add(
            RoleGrant(
                id=new_id("ROL"), user_id=client.id, role="CLIENT",
                scope="self", issued_by=coach.id,
            )
        )
        record_event(
            db,
            action="IDENTITY_REGISTERED",
            actor_id=coach.id,
            subject_ids=[client.id],
            payload={"identity_id": client.identity_id, "identity_type": "HUMAN",
                     "display_name": client.display_name},
            summary=f"Rejestracja tożsamości klienta {client.display_name}",
        )
    rel = CoachClientRelationship(
        id=new_id("REL"), coach_id=coach.id, client_id=client.id, created_by=coach.id
    )
    db.add(rel)
    db.add(MessageThread(id=new_id("THR"), coach_id=coach.id, client_id=client.id))
    ConsentService.grant(
        db,
        subject_id=client.id,
        grantee_id=coach.id,
        purpose=CONSENT_PURPOSE,
        domain=CONSENT_DOMAIN,
        actions="read,write",
        allow_sensitive=True,
    )
    record_event(
        db,
        action="RELATIONSHIP_STARTED",
        actor_id=coach.id,
        subject_ids=[client.id],
        payload={"relationship_id": rel.id, "coach_id": coach.id,
                 "consent_collected_via": "onboarding_declaration"},
        summary=f"Start współpracy: {coach.display_name} ↔ {client.display_name}",
    )
    db.commit()
    return {"client_id": client.id, "relationship_id": rel.id}


@router.get("/clients")
def list_clients(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Lista klientów z obiektywnymi flagami operacyjnymi (bez oceniania)."""
    rels = (
        db.query(CoachClientRelationship)
        .filter(CoachClientRelationship.coach_id == coach.id)
        .all()
    )
    today = datetime.now(UTC).date()
    out = []
    for rel in rels:
        client = db.get(User, rel.client_id)
        if client is None:
            continue
        has_consent = ConsentService.authorize(
            db, subject_id=client.id, grantee_id=coach.id,
            purpose=CONSENT_PURPOSE, domain=CONSENT_DOMAIN, action="read", sensitive=True,
        )
        last_checkin = (
            db.query(WeeklyCheckin)
            .filter(WeeklyCheckin.client_id == client.id)
            .order_by(WeeklyCheckin.week_start.desc())
            .first()
        )
        checkin_overdue = (
            last_checkin is None
            or (today - datetime.fromisoformat(last_checkin.week_start).date()).days > 13
        )
        overdue_payment = (
            db.query(PaymentRecord)
            .join(PaymentSchedule, PaymentRecord.schedule_id == PaymentSchedule.id)
            .filter(
                PaymentSchedule.client_id == client.id,
                PaymentSchedule.coach_id == coach.id,
                PaymentRecord.status.in_(["PENDING", "OVERDUE"]),
                PaymentRecord.due_date < today.isoformat(),
            )
            .count()
        )
        thread = (
            db.query(MessageThread)
            .filter_by(coach_id=coach.id, client_id=client.id)
            .one_or_none()
        )
        unread = 0
        if thread:
            unread = (
                db.query(Message)
                .filter(
                    Message.thread_id == thread.id,
                    Message.author_id == client.id,
                    Message.read_at.is_(None),
                )
                .count()
            )
        recent_pain = (
            db.query(WorkoutSession)
            .filter(
                WorkoutSession.client_id == client.id,
                WorkoutSession.pain_flag.is_(True),
                WorkoutSession.performed_on >= (today - timedelta(days=14)).isoformat(),
            )
            .count()
        )
        out.append(
            {
                "client_id": client.id,
                "display_name": client.display_name,
                "email": client.email,
                "relationship_status": rel.status,
                "consent_active": has_consent,
                "flags": {
                    "checkin_overdue": checkin_overdue,
                    "payment_overdue": overdue_payment > 0,
                    "unread_messages": unread,
                    "recent_pain_reports": recent_pain,
                },
                "last_checkin_week": last_checkin.week_start if last_checkin else None,
            }
        )
    return {"clients": out}


@router.post("/clients/{client_id}/relationship-status")
def set_relationship_status(
    client_id: str,
    status: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    if status not in {"ACTIVE", "PAUSED", "ENDED"}:
        raise HTTPException(status_code=422, detail="Nieprawidłowy status")
    rel = (
        db.query(CoachClientRelationship)
        .filter_by(coach_id=coach.id, client_id=client_id)
        .one_or_none()
    )
    if rel is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    previous = rel.status
    rel.status = status
    if status == "ENDED":
        rel.ended_at = now_iso()
    record_event(
        db,
        action="RELATIONSHIP_STATUS_CHANGED",
        actor_id=coach.id,
        subject_ids=[client_id],
        payload={"relationship_id": rel.id, "from": previous, "to": status},
        summary=f"Zmiana statusu współpracy: {previous} → {status}",
    )
    db.commit()
    return {"ok": True, "status": status}


@router.get("/clients/{client_id}/history")
def client_history(
    client_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Historia zmian (pokwitowania z łańcucha audytu) dotycząca klienta."""
    resolve_client_access(db, coach, client_id)
    from ..models import Receipt

    rows = (
        db.query(Receipt)
        .filter(Receipt.subject_id == client_id)
        .order_by(Receipt.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "receipts": [
            {
                "id": r.id, "event_id": r.event_id, "event_hash": r.event_hash,
                "action": r.action, "actor_id": r.actor_id,
                "summary": r.summary, "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.get("/clients/{client_id}/overview")
def client_overview(
    client_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    resolve_client_access(db, coach, client_id)
    client = db.get(User, client_id)
    assert client is not None
    return {
        "client_id": client.id,
        "display_name": client.display_name,
        "email": client.email,
        "created_at": client.created_at,
        "last_login_at": client.last_login_at,
    }

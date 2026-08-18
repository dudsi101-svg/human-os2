from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    DOMAIN_PHOTOS,
    DOMAIN_TRAINING,
    active_relationship,
    coach_can_access_client,
    resolve_client_access,
)
from ..consent_catalog import ONBOARDING_CATEGORIES
from ..dates import local_now_minute, local_today, parse_iso_date
from ..db import get_db
from ..hos_bridge import ConsentService, record_event
from ..models import (
    CoachClientRelationship,
    ConsultSlot,
    Exercise,
    FoodProduct,
    KnowledgeItem,
    Message,
    MessageThread,
    Observation,
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
from ..security import active_roles, hash_password, require_role

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
    new_account = existing is None
    if existing is not None:
        client = existing
        if active_relationship(db, coach.id, client.id):
            raise HTTPException(status_code=409, detail="Współpraca już istnieje")
        # Istniejące konto można podpiąć wyłącznie, gdy jest aktywnym
        # kontem KLIENTA — nie wolno tą ścieżką tworzyć „relacji" z kontem
        # trenera/admina ani z kontem usuniętym (jedna odpowiedź 409, żeby
        # nie ujawniać roli/statusu cudzego konta).
        if client.status != "ACTIVE" or "CLIENT" not in active_roles(db, client.id):
            raise HTTPException(status_code=409, detail="Współpraca już istnieje")
    else:
        client = User(
            id=new_id("USR"),
            email=email,
            password_hash=hash_password(body.initial_password),
            display_name=body.client_name,
            identity_id=new_id("ID"),
            status="ACTIVE",
            # Hasło startowe zna trener — klient musi je zmienić przy
            # pierwszym logowaniu, zanim uzyska dostęp do danych.
            must_change_password=True,
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
    # Relacja i wątek są unikalne per para trener–klient: wznowienie po
    # PAUSED/ENDED reaktywuje istniejący wiersz (bez duplikatów).
    rel = (
        db.query(CoachClientRelationship)
        .filter_by(coach_id=coach.id, client_id=client.id)
        .one_or_none()
    )
    if rel is None:
        rel = CoachClientRelationship(
            id=new_id("REL"), coach_id=coach.id, client_id=client.id, created_by=coach.id
        )
        db.add(rel)
    else:
        rel.status = "ACTIVE"
        rel.ended_at = None
    thread = (
        db.query(MessageThread)
        .filter_by(coach_id=coach.id, client_id=client.id)
        .one_or_none()
    )
    if thread is None:
        db.add(MessageThread(id=new_id("THR"), coach_id=coach.id, client_id=client.id))
    if new_account:
        # Deklaracje zgód z onboardingu wolno zarejestrować wyłącznie dla
        # konta zakładanego właśnie przez trenera. Dla ISTNIEJĄCEGO konta
        # zgody nie nadaje nikt poza podmiotem danych — klient nadaje je
        # sam w aplikacji (POST /api/me/consents); do tego czasu trener
        # widzi relację z consent_active=false i nie ma dostępu do danych.
        #
        # Każda kategoria to OSOBNY wiersz (RODO: odrębne cele) —
        # klient potwierdza lub odmawia każdej z osobna przy pierwszym
        # logowaniu. Kategorie czysto opcjonalne (przypomnienia, AI,
        # marketing) NIGDY nie są rejestrowane przez trenera.
        for category_key in ONBOARDING_CATEGORIES:
            ConsentService.grant_category(
                db,
                subject_id=client.id,
                category_key=category_key,
                grantee_id=coach.id,
                actions="read,write",
                source="ONBOARDING_DECLARATION",
                confirmed=False,
                actor_id=coach.id,
            )
    record_event(
        db,
        action="RELATIONSHIP_STARTED",
        actor_id=coach.id,
        subject_ids=[client.id],
        payload={
            "relationship_id": rel.id, "coach_id": coach.id,
            "consent_collected_via": (
                "onboarding_declaration" if new_account else "pending_subject_grant"
            ),
        },
        summary=f"Start współpracy: {coach.display_name} ↔ {client.display_name}",
    )
    db.commit()
    return {"client_id": client.id, "relationship_id": rel.id}


def _client_flags(db: Session, coach: User, client: User, today) -> dict:
    """Obiektywne flagi operacyjne dla jednego klienta — współdzielone
    przez listę klientów i dashboard trenera, by uniknąć rozjazdu logiki."""
    last_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .first()
    )
    checkin_overdue = (
        last_checkin is None
        or (today - parse_iso_date(last_checkin.week_start)).days > 13
    )
    awaiting_review = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.client_id == client.id, WeeklyCheckin.status == "SUBMITTED")
        .count()
        > 0
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
        db.query(MessageThread).filter_by(coach_id=coach.id, client_id=client.id).one_or_none()
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
    flagged_observations = (
        db.query(Observation)
        .filter(
            Observation.client_id == client.id,
            Observation.severity == "NIEPOKOJACE",
            Observation.occurred_on >= (today - timedelta(days=14)).isoformat(),
        )
        .count()
    )
    return {
        "checkin_overdue": checkin_overdue,
        "awaiting_review": awaiting_review,
        "payment_overdue": overdue_payment > 0,
        "unread_messages": unread,
        "recent_pain_reports": recent_pain,
        "flagged_observations": flagged_observations,
        "last_checkin_week": last_checkin.week_start if last_checkin else None,
    }


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
    # Data kalendarzowa "dziś" w strefie lokalnej (nie UTC!) — inaczej
    # flagi checkin_overdue/payment_overdue myliłyby się między 00:00 a
    # 01:00/02:00 czasu polskiego.
    today = local_today()
    out = []
    for rel in rels:
        client = db.get(User, rel.client_id)
        if client is None:
            continue
        # Zgody per kategoria danych: consent_active = podstawowa zgoda
        # współpracy (bez niej trener nie widzi danych klienta w ogóle);
        # consent_scopes pokazuje zakres zgód wrażliwych.
        has_consent = coach_can_access_client(
            db, coach.id, client.id, domain=DOMAIN_COLLABORATION
        )
        consent_scopes = {
            "collaboration": has_consent,
            "training": coach_can_access_client(
                db, coach.id, client.id, domain=DOMAIN_TRAINING
            ),
            "health": coach_can_access_client(
                db, coach.id, client.id, domain=DOMAIN_HEALTH
            ),
            "nutrition": coach_can_access_client(
                db, coach.id, client.id, domain=DOMAIN_NUTRITION
            ),
            "photos": coach_can_access_client(
                db, coach.id, client.id, domain=DOMAIN_PHOTOS
            ),
        }
        flags = _client_flags(db, coach, client, today)
        out.append(
            {
                "client_id": client.id,
                "display_name": client.display_name,
                "email": client.email,
                "relationship_status": rel.status,
                "consent_active": has_consent,
                "consent_scopes": consent_scopes,
                "flags": {
                    "checkin_overdue": flags["checkin_overdue"],
                    "awaiting_review": flags["awaiting_review"],
                    "payment_overdue": flags["payment_overdue"],
                    "unread_messages": flags["unread_messages"],
                    "recent_pain_reports": flags["recent_pain_reports"],
                    "flagged_observations": flags["flagged_observations"],
                },
                "last_checkin_week": flags["last_checkin_week"],
            }
        )
    return {"clients": out}


@router.get("/dashboard")
def coach_dashboard(
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Agregaty operacyjne panelu trenera — metadane o pracy trenera
    (ile raportów czeka, ile płatności zalega itd.), nigdy ranking ani
    ocena klientów (zasada Human OS: system nie rankinguje ludzi)."""
    rels = (
        db.query(CoachClientRelationship)
        .filter(CoachClientRelationship.coach_id == coach.id, CoachClientRelationship.status == "ACTIVE")
        .all()
    )
    today = local_today()
    active_clients = len(rels)
    awaiting_review = 0
    checkin_overdue_clients = 0
    payment_overdue_clients = 0
    unread_messages_total = 0
    flagged_observations_14d = 0
    recent_pain_reports_14d = 0
    for rel in rels:
        client = db.get(User, rel.client_id)
        if client is None:
            continue
        flags = _client_flags(db, coach, client, today)
        if flags["awaiting_review"]:
            awaiting_review += 1
        if flags["checkin_overdue"]:
            checkin_overdue_clients += 1
        if flags["payment_overdue"]:
            payment_overdue_clients += 1
        unread_messages_total += flags["unread_messages"]
        flagged_observations_14d += flags["flagged_observations"]
        recent_pain_reports_14d += flags["recent_pain_reports"]
    exercises_count = (
        db.query(Exercise).filter(Exercise.coach_id == coach.id, Exercise.status == "ACTIVE").count()
    )
    food_products_count = (
        db.query(FoodProduct)
        .filter(FoodProduct.coach_id == coach.id, FoodProduct.status == "ACTIVE")
        .count()
    )
    knowledge_items_count = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.coach_id == coach.id, KnowledgeItem.status == "ACTIVE")
        .count()
    )
    upcoming_consultations = (
        db.query(ConsultSlot)
        .filter(
            ConsultSlot.coach_id == coach.id,
            ConsultSlot.status == "BOOKED",
            # starts_at to naiwny czas LOKALNY (DZIK_TZ) — porównujemy
            # wyłącznie z lokalnym "teraz", nigdy z czasem UTC.
            ConsultSlot.starts_at > local_now_minute(),
        )
        .count()
    )
    return {
        "upcoming_consultations": upcoming_consultations,
        "active_clients": active_clients,
        "awaiting_review": awaiting_review,
        "checkin_overdue_clients": checkin_overdue_clients,
        "payment_overdue_clients": payment_overdue_clients,
        "unread_messages_total": unread_messages_total,
        "flagged_observations_14d": flagged_observations_14d,
        "recent_pain_reports_14d": recent_pain_reports_14d,
        "exercises_count": exercises_count,
        "food_products_count": food_products_count,
        "knowledge_items_count": knowledge_items_count,
    }


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
    resolve_client_access(db, coach, client_id, domain=DOMAIN_COLLABORATION)
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
    resolve_client_access(db, coach, client_id, domain=DOMAIN_COLLABORATION)
    client = db.get(User, client_id)
    assert client is not None
    return {
        "client_id": client.id,
        "display_name": client.display_name,
        "email": client.email,
        "created_at": client.created_at,
        "last_login_at": client.last_login_at,
    }

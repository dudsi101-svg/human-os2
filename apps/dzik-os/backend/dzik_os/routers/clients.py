from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..authz import CONSENT_DOMAIN, CONSENT_PURPOSE, active_relationship, resolve_client_access
from ..config import settings
from ..dates import local_now_minute, local_today, parse_iso_date
from ..db import get_db
from ..hos_bridge import ConsentService, record_event
from ..links import activation_link
from ..models import (
    ClientInvitation,
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
from ..notifications_provider import provider as notifications
from ..schemas import RelationshipIn
from ..security import _token_hash, active_roles, require_role

router = APIRouter(prefix="/api/coach", tags=["coach"])


def _issue_invitation(
    db: Session, request: Request, coach: User, client: User
) -> dict:
    """Wystawia jednorazowe zaproszenie aktywacyjne dla konta PENDING.
    Nowy token unieważnia wszystkie poprzednie aktywne (bez mnożenia
    tokenów). W bazie ląduje wyłącznie hash SHA-256; link z tokenem jest
    wysyłany e-mailem, a przy NullNotificationProvider zwracany trenerowi
    do ręcznego przekazania (świadomy kompromis — docs/PERMISSIONS.md)."""
    now = now_iso()
    for old in (
        db.query(ClientInvitation)
        .filter(
            ClientInvitation.client_id == client.id,
            ClientInvitation.used_at.is_(None),
            ClientInvitation.cancelled_at.is_(None),
        )
        .all()
    ):
        old.cancelled_at = now
    token = secrets.token_urlsafe(32)
    invitation = ClientInvitation(
        id=new_id("INV"),
        coach_id=coach.id,
        client_id=client.id,
        email=client.email,
        token_hash=_token_hash(token),
        expires_at=(
            datetime.now(UTC) + timedelta(days=settings.invitation_ttl_days)
        ).isoformat(),
    )
    db.add(invitation)
    link = activation_link(request, token)
    # Treść e-maila celowo bez JAKICHKOLWIEK danych zdrowotnych — tylko
    # zaproszenie i link (imię i nazwa trenera nie są danymi zdrowotnymi).
    sent = notifications.send_email(
        to=client.email,
        subject=f"{settings.brand_name}: aktywuj swoje konto",
        body=(
            f"Cześć {client.display_name}!\n\n"
            f"{coach.display_name} zaprasza Cię do aplikacji "
            f"{settings.brand_name}.\n\n"
            f"Aktywuj konto i ustaw własne hasło (link ważny "
            f"{settings.invitation_ttl_days} dni):\n{link}\n\n"
            "Link jest jednorazowy. Jeśli to nie do Ciebie — zignoruj tę "
            "wiadomość."
        ),
    )
    delivery = "email" if sent else "manual"
    result = {
        "id": invitation.id,
        "expires_at": invitation.expires_at,
        "delivery": delivery,
    }
    if not sent:
        # Brak skonfigurowanego dostawcy e-mail: jedyny kanał doręczenia to
        # trener ("link do przekazania"). Token nie trafia do audytu/logów.
        result["activation_link"] = link
    return result


@router.post("/clients", status_code=201)
def create_client(
    body: RelationshipIn,
    request: Request,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Zaprasza klienta: zakłada konto PENDING (bez hasła — ustawi je sam
    klient przez jednorazowy link aktywacyjny) i aktywną współpracę.
    Zgoda na przetwarzanie danych zdrowotnych jest rejestrowana jako
    deklaracja z onboardingu (proweniencja jawna w audycie); klient widzi
    ją w aplikacji i może ją w każdej chwili cofnąć."""
    email = body.client_email.lower()
    existing = db.query(User).filter(User.email == email).one_or_none()
    new_account = existing is None
    if existing is not None:
        client = existing
        if active_relationship(db, coach.id, client.id):
            raise HTTPException(status_code=409, detail="Współpraca już istnieje")
        # Istniejące konto można podpiąć wyłącznie, gdy jest aktywnym
        # kontem KLIENTA — nie wolno tą ścieżką tworzyć „relacji" z kontem
        # trenera/admina ani z kontem usuniętym/nieaktywowanym (jedna
        # odpowiedź 409, żeby nie ujawniać roli/statusu cudzego konta).
        if client.status != "ACTIVE" or "CLIENT" not in active_roles(db, client.id):
            raise HTTPException(status_code=409, detail="Współpraca już istnieje")
    else:
        client = User(
            id=new_id("USR"),
            email=email,
            # Konto czeka na aktywację: nie ma ŻADNEGO hasła ("!" nigdy nie
            # zweryfikuje się w bcrypt), a status PENDING blokuje logowanie.
            # Hasło ustawi wyłącznie klient na ekranie aktywacji.
            password_hash="!",
            display_name=body.client_name,
            identity_id=new_id("ID"),
            status="PENDING",
            must_change_password=False,
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
        # Deklarację zgody z onboardingu wolno zarejestrować wyłącznie dla
        # konta zakładanego właśnie przez trenera. Dla ISTNIEJĄCEGO konta
        # zgody nie nadaje nikt poza podmiotem danych — klient nadaje ją
        # sam w aplikacji (POST /api/me/consents); do tego czasu trener
        # widzi relację z consent_active=false i nie ma dostępu do danych.
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
        payload={
            "relationship_id": rel.id, "coach_id": coach.id,
            "consent_collected_via": (
                "onboarding_declaration" if new_account else "pending_subject_grant"
            ),
        },
        summary=f"Start współpracy: {coach.display_name} ↔ {client.display_name}",
    )
    invitation = None
    if new_account:
        invitation = _issue_invitation(db, request, coach, client)
        record_event(
            db,
            action="CLIENT_INVITED",
            actor_id=coach.id,
            subject_ids=[client.id],
            # Payload BEZ tokenu i BEZ linku — wyłącznie metadane zaproszenia.
            payload={
                "invitation_id": invitation["id"],
                "expires_at": invitation["expires_at"],
                "delivery": invitation["delivery"],
            },
            summary=f"Zaproszenie do aktywacji konta dla {client.display_name}",
        )
    db.commit()
    return {"client_id": client.id, "relationship_id": rel.id, "invitation": invitation}


def _own_pending_client(db: Session, coach: User, client_id: str) -> User:
    """Klient PENDING w ramach własnej relacji trenera (do operacji na
    zaproszeniach); inaczej 404/409 bez ujawniania szczegółów."""
    rel = (
        db.query(CoachClientRelationship)
        .filter_by(coach_id=coach.id, client_id=client_id)
        .one_or_none()
    )
    client = db.get(User, client_id) if rel is not None else None
    if client is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if client.status != "PENDING":
        raise HTTPException(status_code=409, detail="Konto jest już aktywowane")
    return client


@router.post("/clients/{client_id}/invitations", status_code=201)
def resend_invitation(
    client_id: str,
    request: Request,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Ponowne wysłanie zaproszenia (np. link wygasł albo zaginął).
    Nowy token unieważnia wszystkie poprzednie — zawsze co najwyżej jedno
    aktywne zaproszenie na konto."""
    client = _own_pending_client(db, coach, client_id)
    invitation = _issue_invitation(db, request, coach, client)
    record_event(
        db,
        action="CLIENT_INVITATION_RESENT",
        actor_id=coach.id,
        subject_ids=[client.id],
        payload={
            "invitation_id": invitation["id"],
            "expires_at": invitation["expires_at"],
            "delivery": invitation["delivery"],
        },
        summary=f"Ponowne zaproszenie do aktywacji konta dla {client.display_name}",
    )
    db.commit()
    return {"invitation": invitation}


@router.post("/clients/{client_id}/invitations/cancel")
def cancel_invitation(
    client_id: str,
    coach: User = Depends(require_role("COACH")),
    db: Session = Depends(get_db),
):
    """Anulowanie aktywnych zaproszeń — link natychmiast przestaje działać."""
    client = _own_pending_client(db, coach, client_id)
    now = now_iso()
    cancelled = 0
    for row in (
        db.query(ClientInvitation)
        .filter(
            ClientInvitation.client_id == client.id,
            ClientInvitation.used_at.is_(None),
            ClientInvitation.cancelled_at.is_(None),
        )
        .all()
    ):
        row.cancelled_at = now
        cancelled += 1
    record_event(
        db,
        action="CLIENT_INVITATION_CANCELLED",
        actor_id=coach.id,
        subject_ids=[client.id],
        payload={"cancelled": cancelled},
        summary=f"Anulowanie zaproszenia do aktywacji konta dla {client.display_name}",
    )
    db.commit()
    return {"ok": True, "cancelled": cancelled}


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
        has_consent = ConsentService.authorize(
            db, subject_id=client.id, grantee_id=coach.id,
            purpose=CONSENT_PURPOSE, domain=CONSENT_DOMAIN, action="read", sensitive=True,
        )
        flags = _client_flags(db, coach, client, today)
        invitation_expires_at = None
        if client.status == "PENDING":
            active_inv = (
                db.query(ClientInvitation)
                .filter(
                    ClientInvitation.client_id == client.id,
                    ClientInvitation.used_at.is_(None),
                    ClientInvitation.cancelled_at.is_(None),
                )
                .order_by(ClientInvitation.created_at.desc())
                .first()
            )
            if active_inv is not None:
                invitation_expires_at = active_inv.expires_at
        out.append(
            {
                "client_id": client.id,
                "display_name": client.display_name,
                "email": client.email,
                "relationship_status": rel.status,
                "consent_active": has_consent,
                # Konto z zaproszenia, które nie zostało jeszcze aktywowane
                # (klient nie ustawił hasła); expires_at aktywnego
                # zaproszenia — bez tokenu (serwer zna tylko hash).
                "account_pending": client.status == "PENDING",
                "invitation_expires_at": invitation_expires_at,
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

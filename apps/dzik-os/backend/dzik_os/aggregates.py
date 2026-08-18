"""Warstwa agregacji dla widoków zbiorczych trenera.

Problem, który rozwiązuje (znaleziony symulacją — patrz docs/SYMULACJA.md):
lista klientów i dashboard liczyły flagi operacyjne w pętli po podopiecznych,
wykonując ~18 zapytań SQL na osobę. Przy dziesięciu podopiecznych dashboard
kosztował 88 zapytań, a lista 184 — na SQLite to dziesiątki milisekund, ale
na PostgreSQL każde zapytanie to osobny round-trip, więc panel trenera
degradowałby się liniowo wraz z rozwojem współpracy.

Tutaj każda metryka liczona jest JEDNYM zapytaniem grupującym po kliencie,
niezależnie od liczby podopiecznych. Logika flag jest identyczna jak
poprzednio (te same warunki i progi) — zmienia się wyłącznie sposób
pobrania danych. Reguły zgód pozostają w Core: rejestr hos_engine jest
hydratowany raz dla wszystkich podopiecznych i to on odpowiada „czy wolno".
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from .authz import (
    DOMAIN_COLLABORATION,
    DOMAIN_HEALTH,
    DOMAIN_NUTRITION,
    DOMAIN_PHOTOS,
    DOMAIN_TRAINING,
)
from .consent_catalog import category_for_domain
from .dates import parse_iso_date
from .hos_bridge import ConsentService
from .models import (
    ClientInvitation,
    CoachClientRelationship,
    Message,
    MessageThread,
    Observation,
    PaymentRecord,
    PaymentSchedule,
    User,
    WeeklyCheckin,
    WorkoutEntry,
    WorkoutSession,
)
from .payment_state import DUE_STATUSES

# Domeny pokazywane w zakresie zgód na liście klientów (klucz odpowiedzi API
# -> domena katalogu zgód). Kolejność bez znaczenia — to mapa, nie ranking.
CONSENT_SCOPE_DOMAINS = {
    "collaboration": DOMAIN_COLLABORATION,
    "training": DOMAIN_TRAINING,
    "health": DOMAIN_HEALTH,
    "nutrition": DOMAIN_NUTRITION,
    "photos": DOMAIN_PHOTOS,
}


def consent_scopes_bulk(
    db: Session,
    coach_id: str,
    client_ids: list[str],
    *,
    domains: dict[str, str],
    action: str = "read",
) -> dict[str, dict[str, bool]]:
    """Zakres zgód trenera do danych każdego podopiecznego.

    Dwa zapytania łącznie (relacje + zgody) zamiast dwóch na każdą parę
    klient×domena. Decyzja pozostaje w hos_engine.ConsentRegistry.
    """
    if not client_ids:
        return {}
    active = {
        rel.client_id
        for rel in db.query(CoachClientRelationship)
        .filter(
            CoachClientRelationship.coach_id == coach_id,
            CoachClientRelationship.client_id.in_(client_ids),
            CoachClientRelationship.status == "ACTIVE",
        )
        .all()
    }
    registry = ConsentService.hydrate_many(db, client_ids)
    out: dict[str, dict[str, bool]] = {}
    for client_id in client_ids:
        scopes: dict[str, bool] = {}
        for key, domain in domains.items():
            if client_id not in active:
                scopes[key] = False
                continue
            cat = category_for_domain(domain)
            scopes[key] = registry.authorize(
                subject_id=client_id,
                grantee_id=coach_id,
                purpose=cat.purpose if cat else "coaching",
                domain=domain,
                action=action,
                sensitive=cat.sensitive if cat else True,
            )
        out[client_id] = scopes
    return out


def _count_by_client(db: Session, entity, client_column, *filters) -> dict[str, int]:
    """Jedno zapytanie: liczba rekordów per klient."""
    rows = (
        db.query(client_column, func.count(entity.id))
        .filter(*filters)
        .group_by(client_column)
        .all()
    )
    return {client_id: count for client_id, count in rows}


def client_flags_bulk(
    db: Session,
    coach_id: str,
    client_ids: list[str],
    today: date,
) -> dict[str, dict]:
    """Flagi operacyjne wszystkich podopiecznych — siedem zapytań łącznie.

    Flagi są obiektywne (co czeka na trenera), nigdy oceniające osobę —
    ta sama zasada co w implementacji jednostkowej, którą zastępuje.
    """
    if not client_ids:
        return {}
    horizon = (today - timedelta(days=14)).isoformat()

    last_checkin = dict(
        db.query(WeeklyCheckin.client_id, func.max(WeeklyCheckin.week_start))
        .filter(WeeklyCheckin.client_id.in_(client_ids))
        .group_by(WeeklyCheckin.client_id)
        .all()
    )
    awaiting = _count_by_client(
        db, WeeklyCheckin, WeeklyCheckin.client_id,
        WeeklyCheckin.client_id.in_(client_ids),
        WeeklyCheckin.status == "SUBMITTED",
    )
    overdue_payments = dict(
        db.query(PaymentSchedule.client_id, func.count(PaymentRecord.id))
        .join(PaymentRecord, PaymentRecord.schedule_id == PaymentSchedule.id)
        .filter(
            PaymentSchedule.client_id.in_(client_ids),
            PaymentSchedule.coach_id == coach_id,
            PaymentRecord.status.in_(list(DUE_STATUSES)),
            PaymentRecord.due_date < today.isoformat(),
        )
        .group_by(PaymentSchedule.client_id)
        .all()
    )
    unread = dict(
        db.query(MessageThread.client_id, func.count(Message.id))
        .join(Message, Message.thread_id == MessageThread.id)
        .filter(
            MessageThread.client_id.in_(client_ids),
            MessageThread.coach_id == coach_id,
            Message.author_id == MessageThread.client_id,
            Message.read_at.is_(None),
        )
        .group_by(MessageThread.client_id)
        .all()
    )
    pain = _count_by_client(
        db, WorkoutSession, WorkoutSession.client_id,
        WorkoutSession.client_id.in_(client_ids),
        WorkoutSession.pain_flag.is_(True),
        WorkoutSession.performed_on >= horizon,
    )
    flagged = _count_by_client(
        db, Observation, Observation.client_id,
        Observation.client_id.in_(client_ids),
        Observation.severity == "NIEPOKOJACE",
        Observation.occurred_on >= horizon,
    )

    out: dict[str, dict] = {}
    for client_id in client_ids:
        week = last_checkin.get(client_id)
        out[client_id] = {
            "checkin_overdue": week is None or (today - parse_iso_date(week)).days > 13,
            "awaiting_review": awaiting.get(client_id, 0) > 0,
            "payment_overdue": overdue_payments.get(client_id, 0) > 0,
            "unread_messages": unread.get(client_id, 0),
            "recent_pain_reports": pain.get(client_id, 0),
            "flagged_observations": flagged.get(client_id, 0),
            "last_checkin_week": week,
        }
    return out


def users_by_id(db: Session, user_ids: list[str]) -> dict[str, User]:
    """Jedno zapytanie zamiast db.get() w pętli."""
    if not user_ids:
        return {}
    return {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}


def pending_invitation_expiry(db: Session, client_ids: list[str]) -> dict[str, str]:
    """Termin ważności aktywnego zaproszenia dla kont oczekujących —
    jedno zapytanie zamiast jednego na konto. Zwraca wyłącznie datę
    wygaśnięcia; token pozostaje wyłącznie w postaci hasha po stronie
    serwera i nigdy nie opuszcza bazy."""
    if not client_ids:
        return {}
    rows = (
        db.query(ClientInvitation)
        .filter(
            ClientInvitation.client_id.in_(client_ids),
            ClientInvitation.used_at.is_(None),
            ClientInvitation.cancelled_at.is_(None),
        )
        .order_by(ClientInvitation.created_at.desc())
        .all()
    )
    out: dict[str, str] = {}
    for row in rows:
        # Wiersze posortowane malejąco — pierwszy trafiony to najnowszy.
        out.setdefault(row.client_id, row.expires_at)
    return out


def workout_entries_by_session(
    db: Session, session_ids: list[str]
) -> dict[str, list[WorkoutEntry]]:
    """Wpisy ćwiczeń pogrupowane po sesji — jedno zapytanie zamiast jednego
    na sesję. Kolejność ćwiczeń w sesji zachowana (exercise_index)."""
    if not session_ids:
        return {}
    rows = (
        db.query(WorkoutEntry)
        .filter(WorkoutEntry.session_id.in_(session_ids))
        .order_by(WorkoutEntry.session_id, WorkoutEntry.exercise_index)
        .all()
    )
    out: dict[str, list[WorkoutEntry]] = {}
    for row in rows:
        out.setdefault(row.session_id, []).append(row)
    return out


def last_message_by_thread(db: Session, thread_ids: list[str]) -> dict[str, Message]:
    """Ostatnia wiadomość każdego wątku — jedno zapytanie z funkcją okna
    zamiast jednego zapytania na wątek (SQLite ≥ 3.25 i PostgreSQL)."""
    if not thread_ids:
        return {}
    rn = (
        func.row_number()
        .over(
            partition_by=Message.thread_id,
            order_by=(Message.created_at.desc(), Message.id.desc()),
        )
        .label("rn")
    )
    ranked = (
        select(Message, rn)
        .where(Message.thread_id.in_(thread_ids))
        .subquery()
    )
    message_alias = aliased(Message, ranked)
    rows = db.execute(select(message_alias).where(ranked.c.rn == 1)).scalars().all()
    return {row.thread_id: row for row in rows}


def unread_by_thread(
    db: Session, thread_ids: list[str], reader_id: str
) -> dict[str, int]:
    """Liczba nieprzeczytanych wiadomości od DRUGIEJ strony, per wątek —
    jedno zapytanie grupujące."""
    if not thread_ids:
        return {}
    rows = (
        db.query(Message.thread_id, func.count(Message.id))
        .filter(
            Message.thread_id.in_(thread_ids),
            Message.author_id != reader_id,
            Message.read_at.is_(None),
        )
        .group_by(Message.thread_id)
        .all()
    )
    return {thread_id: count for thread_id, count in rows}

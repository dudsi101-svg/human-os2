from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id(prefix: str) -> str:
    """Stabilne identyfikatory w konwencji Human OS: HOS-<PREFIX>-<hex12>.
    (Ten sam format co hos_engine.security_identity / hub_entity_registry.)"""
    return f"HOS-{prefix}-" + uuid.uuid4().hex[:12].upper()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(200))
    # Tożsamość Human OS (AXIS A: rodzaj podmiotu). Rola uprawnień to osobna
    # oś (RoleGrant) — nie utożsamiamy typu tożsamości z rolą.
    identity_id: Mapped[str] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/SUSPENDED/DELETED
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    last_login_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    anonymized_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Konto założone przez trenera z hasłem startowym musi je zmienić przy
    # pierwszym logowaniu (egzekwowane w security.current_user).
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)


class RoleGrant(Base):
    """Domenowe role uprawnień (COACH/CLIENT/ADMIN) — wzorowane na
    hos_engine.authority.RoleGrant: nadanie jest jawne, ograniczone zakresem,
    odwoływalne i nigdy nie jest cichym flipem stanu."""

    __tablename__ = "role_grants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # COACH / CLIENT / ADMIN
    scope: Mapped[str] = mapped_column(String(100), default="*")
    issued_by: Mapped[str] = mapped_column(String(40))
    valid_from: Mapped[str] = mapped_column(String(40), default=now_iso)
    valid_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str] = mapped_column(String(40))
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)


class CoachClientRelationship(Base):
    __tablename__ = "coach_client_relationships"
    __table_args__ = (UniqueConstraint("coach_id", "client_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/PAUSED/ENDED
    started_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    ended_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_by: Mapped[str] = mapped_column(String(40))


class ProfileField(Base):
    """Profil klienta jako pola z pełną proweniencją — każde pole ma źródło,
    autora, datę, wersję, cel przetwarzania i status aktualności.
    Append-only: nowa wartość = nowy wiersz z wyższą wersją (brak cichego
    nadpisywania)."""

    __tablename__ = "profile_fields"
    __table_args__ = (
        UniqueConstraint("client_id", "field_key", "version"),
        Index("ix_profile_current", "client_id", "field_key", "is_current"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40))  # CLIENT_DECLARED / COACH_ENTERED / IMPORT
    author_id: Mapped[str] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(String(120), default="coaching")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="MAIN")  # MAIN / SECONDARY
    target_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/DONE/DROPPED
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    version: Mapped[int] = mapped_column(Integer, default=1)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )  # NULL => szablon trenera
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/ARCHIVED
    current_version_no: Mapped[int] = mapped_column(Integer, default=0)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class TrainingPlanVersion(Base):
    """Wersje planu są niemutowalne. Nowa wersja wymaga powodu zmiany;
    poprzednie wersje pozostają dostępne (zasada Human OS: brak cichego
    nadpisywania, pełna historia)."""

    __tablename__ = "training_plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version_no"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("training_plans.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    # Struktura dni/ćwiczeń: {"days": [{"name", "weekday", "exercises":
    # [{"name","sets","reps","weight","tempo","rest","comment","video_url"}]}]}
    content_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("training_plan_versions.id"))
    day_index: Mapped[int] = mapped_column(Integer)
    performed_on: Mapped[str] = mapped_column(String(40))  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(20), default="DONE")  # DONE / PARTIAL / SKIPPED
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    pain_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class WorkoutEntry(Base):
    __tablename__ = "workout_entries"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("workout_sessions.id"), index=True)
    exercise_index: Mapped[int] = mapped_column(Integer)
    exercise_name: Mapped[str] = mapped_column(String(300))
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # np. "3x8 @ 80kg"
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)


class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    current_version_no: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class NutritionPlanVersion(Base):
    __tablename__ = "nutrition_plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version_no"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("nutrition_plans.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    # {"kcal", "protein_g", "fat_g", "carbs_g", "sections":
    #  [{"title","body"}], "meals":[{"name","description","swaps"}]}
    content_json: Mapped[str] = mapped_column(Text)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ScheduleItem(Base):
    """Element harmonogramu. System wyłącznie przechowuje i przypomina plan
    świadomie wprowadzony przez człowieka (author_id + author_note) — nigdy
    nie dobiera ani nie zwiększa dawkowania (patrz docs/PERMISSIONS.md §5.5)."""

    __tablename__ = "schedule_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(30))  # TRENING/POSILEK/NAWODNIENIE/REGENERACJA/
    # SUPLEMENT/POMIAR/RAPORT/PLATNOSC/INNE
    time_of_day: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "07:30"
    days_of_week: Mapped[str] = mapped_column(String(30), default="1,2,3,4,5,6,7")
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    author_id: Mapped[str] = mapped_column(String(40))
    author_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/PAUSED/ENDED
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    due_date: Mapped[str] = mapped_column(String(40))
    created_by: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/DONE/CANCELLED
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class WeeklyCheckin(Base):
    __tablename__ = "weekly_checkins"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[str] = mapped_column(String(40))  # YYYY-MM-DD (poniedziałek)
    payload_json: Mapped[str] = mapped_column(Text)  # odpowiedzi formularza
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")  # SUBMITTED/REVIEWED
    revision: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    coach_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CheckinRevision(Base):
    """Poprawki deklaracji klienta zachowują poprzednią treść (append-only)."""

    __tablename__ = "checkin_revisions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    checkin_id: Mapped[str] = mapped_column(ForeignKey("weekly_checkins.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(120))  # weight/waist/chest/... lub metric_def id
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    measured_at: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(40), default="CLIENT_DECLARED")
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    deleted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"))
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(40), default="INNE")  # DIETA/PLAN/WYNIKI/INNE
    uploaded_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"))
    checkin_id: Mapped[str | None] = mapped_column(ForeignKey("weekly_checkins.id"), nullable=True)
    taken_at: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MessageThread(Base):
    __tablename__ = "message_threads"
    __table_args__ = (UniqueConstraint("coach_id", "client_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("message_threads.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    read_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class PaymentSchedule(Base):
    __tablename__ = "payment_schedules"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    package_name: Mapped[str] = mapped_column(String(200))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="PLN")
    period: Mapped[str] = mapped_column(String(20), default="MONTHLY")  # MONTHLY/WEEKLY/ONE_OFF
    external_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("payment_schedules.id"), index=True)
    due_date: Mapped[str] = mapped_column(String(40))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="PLN")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # PENDING / PAID / OVERDUE / CANCELLED — zmiany statusu audytowane
    paid_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    marked_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ConsentRecord(Base):
    """Rejestr zgód — trwała warstwa dla kontraktu
    hos_engine.consent.ConsentRegistry (patrz hos_bridge.ConsentService).
    Cofnięcie nie usuwa wiersza; ustawia revoked_at (pełna historia wersji)."""

    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)  # czyje dane
    grantee_id: Mapped[str] = mapped_column(String(40))  # kto dostaje dostęp (user/system/AI)
    purpose: Mapped[str] = mapped_column(String(120))  # np. "coaching"
    domain: Mapped[str] = mapped_column(String(120))  # np. "health_data"
    actions: Mapped[str] = mapped_column(String(200), default="read")  # CSV akcji
    allow_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text_version: Mapped[str] = mapped_column(String(20), default="1.0")
    granted_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Zgoda zarejestrowana przy onboardingu przez trenera czeka na jawne
    # potwierdzenie podmiotu w aplikacji (confirmed_at); zgody nadawane
    # samodzielnie przez podmiot są potwierdzone od razu.
    confirmed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Receipt(Base):
    """Pokwitowanie operacji o wysokim znaczeniu: wiąże odpowiedź API z
    niemutowalnym zdarzeniem w łańcuchu audytu Human OS (event_hash)."""

    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(40), unique=True)
    event_hash: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(80))
    actor_id: Mapped[str] = mapped_column(String(40), index=True)
    subject_id: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)

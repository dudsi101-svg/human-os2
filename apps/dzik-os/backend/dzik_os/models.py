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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id(prefix: str) -> str:
    """Stabilne identyfikatory w konwencji Human OS: HOS-<PREFIX>-<hex12>.
    (Ten sam format co hos_engine.security_identity / hub_entity_registry.)"""
    return f"HOS-{prefix}-" + uuid.uuid4().hex[:12].upper()


def now_iso() -> str:
    """Dokładny MOMENT zdarzenia (created_at/updated_at/paid_at/read_at,
    audyt): zawsze pełny timestamp UTC; do strefy lokalnej przeliczany
    dopiero przy prezentacji. Dat kalendarzowych (YYYY-MM-DD) nigdy nie
    wyliczać z UTC — patrz dzik_os/dates.py (local_today)."""
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
    # PENDING = konto z zaproszenia, czeka na aktywację (klient sam ustawia
    # hasło); ACTIVE / SUSPENDED / DELETED jak dotąd. PENDING nie może się
    # zalogować (login filtruje status == ACTIVE).
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    last_login_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    anonymized_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Konto założone przez trenera z hasłem startowym musi je zmienić przy
    # pierwszym logowaniu (egzekwowane w security.current_user). Historyczny
    # przepływ — nowe konta powstają z zaproszenia (bez hasła startowego).
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # MFA (TOTP, RFC 6238). Sekret jest potrzebny serwerowi do weryfikacji
    # kodów, więc nie może być hashem; nigdy nie trafia do logów, audytu ani
    # odpowiedzi API (poza jednorazowym zwrotem przy konfiguracji).
    # totp_confirmed_at != NULL oznacza aktywne MFA; totp_last_counter to
    # licznik ostatnio zaakceptowanego okna (ochrona przed replayem kodu).
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_confirmed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    totp_last_counter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Strefa czasowa użytkownika (IANA, np. "Europe/Warsaw"). NULL = strefa
    # aplikacji (DZIK_TZ). Odczytywana przez dates.tz_for_user() — steruje
    # datami kalendarzowymi i porami przypomnień (migracja nr 14).
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)


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
    """Sesja uwierzytelnienia. Serwer przechowuje WYŁĄCZNIE hash SHA-256
    tokenu (token_hash) — sam token zna tylko klient; wyciek bazy nie
    pozwala przejąć sesji. Unieważnienie = revoked_at (append-only,
    wiersz nigdy nie jest usuwany)."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str] = mapped_column(String(40))
    revoked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Ostatnie użycie tokenu (rozdzielczość ~5 min — patrz security.current_user);
    # pokazywane na ekranie aktywnych sesji.
    last_used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ClientInvitation(Base):
    """Zaproszenie do aktywacji konta klienta. Serwer przechowuje WYŁĄCZNIE
    hash SHA-256 tokenu aktywacyjnego (jak AuthSession.token_hash) — sam
    token istnieje tylko w linku przekazanym klientowi. Jednorazowe
    (used_at), anulowalne (cancelled_at), z terminem ważności; nowe
    zaproszenie unieważnia poprzednie aktywne (bez mnożenia tokenów)."""

    __tablename__ = "client_invitations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    email: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str] = mapped_column(String(40))
    used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cancelled_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class PasswordResetToken(Base):
    """Token resetu hasła: tylko hash SHA-256, jednorazowy (used_at),
    krótki termin ważności; użycie unieważnia wszystkie sesje konta."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str] = mapped_column(String(40))
    used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class MfaRecoveryCode(Base):
    """Kod odzyskiwania MFA — przechowywany wyłącznie jako hash SHA-256;
    jednorazowy (used_at); regeneracja unieważnia wszystkie poprzednie."""

    __tablename__ = "mfa_recovery_codes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class MfaChallenge(Base):
    """Krok pośredni logowania z MFA: poprawne hasło wydaje krótkotrwały
    token wyzwania (tu tylko jego hash SHA-256); dopiero poprawny kod TOTP
    lub kod odzyskiwania wymienia wyzwanie na pełną sesję. Jednorazowe."""

    __tablename__ = "mfa_challenges"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    expires_at: Mapped[str] = mapped_column(String(40))
    used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


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
    # Strukturalny zapis serii: [{"weight_kg": 80, "reps": 8}, ...] —
    # obok tekstowego `result` (kompatybilność wstecz); umożliwia wykresy
    # objętości i szacowanego 1RM bez parsowania tekstu.
    sets_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    # Ocena raportu przez trenera (1-5) — subiektywna notatka trenera o
    # jakości/kompletności RAPORTU, nie ocena wartości klienta jako osoby
    # (zasada Human OS: system nigdy nie rankinguje ludzi). Opcjonalna,
    # widoczna dla klienta obok odpowiedzi.
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Liczba zdjęć zadeklarowana przy wysyłce (migracja 12). Raport z
    # mniejszą liczbą zapisanych zdjęć jest jawnie CZĘŚCIOWY — stan widoczny
    # dla klienta i trenera, do dokończenia przez /checkins/{id}/photos.
    # NULL = raport sprzed migracji lub bez deklaracji (traktowany jako
    # kompletny — bez retroaktywnej reinterpretacji starych wierszy).
    photos_expected: Mapped[int | None] = mapped_column(Integer, nullable=True)


class IdempotencyKey(Base):
    """Klucz idempotencji operacji zapisu (migracja 12): powtórka żądania
    z tym samym kluczem (podwójne kliknięcie, retry po przerwaniu sieci)
    zwraca zapisany wynik zamiast tworzyć duplikat. request_hash chroni
    przed ponownym użyciem klucza z INNĄ treścią (jawny konflikt 409)."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "operation", "idem_key"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    operation: Mapped[str] = mapped_column(String(80))
    idem_key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


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
    # Typ ujęcia (PRZOD/BOK/TYL/INNE) i kolejność wybrana przez klienta
    # (migracja 12); NULL = zdjęcie historyczne bez deklaracji.
    pose: Mapped[str | None] = mapped_column(String(20), nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class MessageThread(Base):
    __tablename__ = "message_threads"
    __table_args__ = (UniqueConstraint("coach_id", "client_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Message(Base):
    """Wiadomość w wątku. Statusy doręczenia (model: docs/WIADOMOSCI.md):
    wysłana = istnieje wiersz (created_at), dostarczona = delivered_at
    (urządzenie odbiorcy odebrało ją kanałem SSE lub przez GET wątku),
    przeczytana = read_at (odbiorca miał otwarty wątek). client_msg_id to
    identyfikator nadany przez urządzenie nadawcy — deduplikacja ponowień
    po utracie sieci (unikalny per wątek+autor, patrz migracja nr 13)."""

    __tablename__ = "messages"
    __table_args__ = (
        # Stabilna kolejność i kursor paginacji: (created_at, id).
        Index("ix_messages_thread_created", "thread_id", "created_at", "id"),
        Index(
            "ux_messages_thread_author_client_msg",
            "thread_id",
            "author_id",
            "client_msg_id",
            unique=True,
            sqlite_where=text("client_msg_id IS NOT NULL"),
            postgresql_where=text("client_msg_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("message_threads.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    delivered_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    read_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    client_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


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


class ScheduleCompletion(Base):
    """Odhaczenie elementu harmonogramu na dany dzień — adherencja
    (trening/posiłek/suplement/nawodnienie/regenerację itd.), nie tylko
    treningi. Jeden wpis na dzień na element (append przez unique);
    poprawka = nowy POST nadpisujący wiersz (idempotentne 'wykonane')."""

    __tablename__ = "schedule_completions"
    __table_args__ = (UniqueConstraint("schedule_item_id", "completed_on"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    schedule_item_id: Mapped[str] = mapped_column(ForeignKey("schedule_items.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    completed_on: Mapped[str] = mapped_column(String(40))  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(20), default="DONE")  # DONE / SKIPPED
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Observation(Base):
    """Dziennik obserwacji klienta — samodzielne, dobrowolne zgłoszenie
    samopoczucia lub reakcji, opcjonalnie powiązane z elementem harmonogramu
    (np. suplementem lub posiłkiem). NIGDY nie jest diagnozą ani
    automatyczną analizą — wyłącznie deklaracja klienta (lub notatka
    trenera) do przeglądu przez człowieka. System tylko rejestruje i
    flaguje NIEPOKOJACE wpisy w panelu trenera; nie interpretuje ich."""

    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    occurred_on: Mapped[str] = mapped_column(String(40))  # YYYY-MM-DD
    schedule_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("schedule_items.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(30))  # SAMOPOCZUCIE/OBJAW/REAKCJA/INNE
    severity: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO/NIEPOKOJACE
    text: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class DailyNutritionLog(Base):
    """Dzienny log realizacji diety (kalorie/makra/woda) — deklaracja
    klienta, osobna od statycznego celu w NutritionPlanVersion; pozwala
    porównać cel z realizacją w czasie."""

    __tablename__ = "daily_nutrition_logs"
    __table_args__ = (UniqueConstraint("client_id", "logged_on"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    logged_on: Mapped[str] = mapped_column(String(40))  # YYYY-MM-DD
    kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carbs_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    water_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class KnowledgeItem(Base):
    """Baza wiedzy trenera — materiały (artykuł, link, plik), którymi
    trener wspiera podopiecznych; treść dostarcza i za nią odpowiada
    trener (nie jest to porada medyczna systemu). Broadcast: widoczne dla
    wszystkich aktywnie prowadzonych klientów danego trenera — to
    własność trenera, nie dane konkretnego klienta, więc nie przechodzi
    przez resolve_client_access jak dane zdrowotne."""

    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80), default="Inne")
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/ARCHIVED
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Exercise(Base):
    """Baza ćwiczeń (know-how trenera) — technika wykonania i efekt, z
    podziałem na partie mięśniowe. Broadcast: własność trenera, widoczna
    dla wszystkich aktywnie prowadzonych klientów (ten sam wzorzec co
    KnowledgeItem) — to nie są dane zdrowotne konkretnego klienta, więc
    nie przechodzi przez resolve_client_access."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    # NOGI/PLECY/KLATKA/BARKI/RECE/BRZUCH/CALE_CIALO/MOBILNOSC/INNE
    muscle_group: Mapped[str] = mapped_column(String(30))
    how_to: Mapped[str] = mapped_column(Text)
    benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(200), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/ARCHIVED
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class FoodProduct(Base):
    """Baza produktów spożywczych z makroskładnikami na 100 g — pozwala na
    automatyczne przeliczenie kalorii/makro względem wielkości porcji.
    Broadcast trenera, ten sam wzorzec co Exercise/KnowledgeItem."""

    __tablename__ = "food_products"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80), default="Inne")
    kcal_100g: Mapped[float] = mapped_column(Float)
    protein_100g: Mapped[float] = mapped_column(Float)
    fat_100g: Mapped[float] = mapped_column(Float)
    carbs_100g: Mapped[float] = mapped_column(Float)
    default_portion_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/ARCHIVED
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ConsultSlot(Base):
    """Slot konsultacji trenera. Czas lokalny (DZIK_TZ) jako ISO
    "YYYY-MM-DDTHH:MM" — porównania leksykograficzne działają.
    Rezerwacja jest zawsze odwoływalna (klient do 12 h przed terminem,
    trener w każdej chwili z powiadomieniem) — żadnych kar ani metryk
    za odwołania (zasada Human OS)."""

    __tablename__ = "consult_slots"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    coach_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[str] = mapped_column(String(20))  # YYYY-MM-DDTHH:MM
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN/BOOKED/CANCELLED
    client_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    booked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class PushSubscription(Base):
    """Subskrypcja Web Push (opt-in użytkownika). Treść powiadomień nigdy
    nie zawiera danych zdrowotnych — tylko neutralne wezwanie do wejścia
    do aplikacji. Wygaśnięte subskrypcje (404/410 od dostawcy) są usuwane."""

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(1000), unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class Notification(Base):
    """Wspólny model powiadomienia (migracja nr 14) — jedno źródło prawdy
    dla wszystkich kanałów: centrum w aplikacji (ten wiersz), push i e-mail.

    Zasady (docs/POWIADOMIENIA.md):
    - title/body to treść dla CENTRUM (widoczna dopiero po zalogowaniu);
      kanały push/e-mail dostają WYŁĄCZNIE neutralne wezwanie per kategoria
      (nigdy dane zdrowotne, kwoty, nazwy suplementów ani treści wiadomości);
    - dedup_key jest kluczem idempotencji w bazie — restart procesu nie
      może zdublować ani zgubić powiadomienia (UNIQUE(user_id, dedup_key));
    - scheduled_at (UTC) + timezone: termin wyliczony w lokalnej strefie
      odbiorcy w chwili planowania (DST rozstrzyga zoneinfo);
    - source wskazuje obiekt źródłowy (np. schedule_item:...) — zmiana lub
      odwołanie terminu anuluje zaplanowane wiersze po source."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key"),
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
        Index("ix_notifications_source", "source"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    # TRENING / SUPLEMENT / HARMONOGRAM / RAPORT / WIADOMOSC / PLATNOSC /
    # DOKUMENT / ZMIANA_PLANU / KONSULTACJA (notifications.CATEGORIES).
    category: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    # Ekran docelowy w aplikacji (klik w push/centrum) — per kategoria.
    url: Mapped[str] = mapped_column(String(300), default="/")
    # SCHEDULED (czeka na termin) / SENT / CANCELLED / SUPPRESSED.
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    # Powód SUPPRESSED: task_done / preferences / expired / source_gone.
    suppressed_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Kanały, którymi faktycznie doręczono (CSV: "center,push,email").
    channels: Mapped[str | None] = mapped_column(String(60), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(120))
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheduled_at: Mapped[str | None] = mapped_column(String(40), nullable=True)  # UTC ISO
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso)
    sent_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    read_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class NotificationPreference(Base):
    """Preferencja użytkownika per kategoria × kanał (PUSH/CENTER/EMAIL).
    Brak wiersza = domyślne: PUSH i CENTER włączone, EMAIL wyłączony."""

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "category", "channel"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(10))  # PUSH / CENTER / EMAIL
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class NotificationSetting(Base):
    """Ustawienia doręczeń per użytkownik: ciche godziny (czas lokalny,
    zakres może przechodzić przez północ), dni aktywne przypomnień
    harmonogramu i częstotliwość przypomnień o raporcie. Strefa czasowa
    mieszka na users.timezone (czyta ją dates.tz_for_user)."""

    __tablename__ = "notification_settings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "22:00"
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "07:00"
    active_days: Mapped[str] = mapped_column(String(30), default="1,2,3,4,5,6,7")
    # DAILY = przypomnienie o raporcie w każdy zaplanowany dzień;
    # WEEKLY = raz w tygodniu (klucz idempotencji per tydzień ISO).
    raport_frequency: Mapped[str] = mapped_column(String(10), default="DAILY")
    updated_at: Mapped[str] = mapped_column(String(40), default=now_iso)


class ConsentRecord(Base):
    """Rejestr zgód — trwała warstwa dla kontraktu
    hos_engine.consent.ConsentRegistry (patrz hos_bridge.ConsentService).
    Cofnięcie nie usuwa wiersza; ustawia revoked_at (pełna historia wersji).

    Od migracji nr 10 każda zgoda należy do jednej kategorii z
    consent_catalog.CONSENT_CATEGORIES (odrębne, jednoznaczne cele —
    RODO). Wiersze z category=NULL to historyczne zgody parasolowe
    coaching/health_data sprzed podziału — interpretowane zgodnie z ich
    pierwotnym, szerokim zakresem (patrz ConsentService._hydrate)."""

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
    # Klucz kategorii z consent_catalog (NULL = historyczna zgoda parasolowa).
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Podstawa prawna zapisana w chwili udzielenia (historia — treść
    # katalogu może się zmieniać, wiersz pamięta swoją).
    legal_basis: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Źródło wpisu: SUBJECT (podmiot danych osobiście) /
    # ONBOARDING_DECLARATION (deklaracja z onboardingu, czeka na
    # potwierdzenie podmiotu) / SEED (dane demo).
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Jawna ODMOWA zgody opcjonalnej (historia decyzji negatywnej) —
    # wiersz z denied_at nigdy nie autoryzuje dostępu.
    denied_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


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

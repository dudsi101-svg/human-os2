from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class ProfileFieldIn(BaseModel):
    field_key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=5000)
    purpose: str = Field(default="coaching", max_length=120)
    sensitive: bool = False


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    kind: str = Field(default="MAIN", pattern="^(MAIN|SECONDARY)$")
    target_date: str | None = None


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    sets: str | None = Field(default=None, max_length=40)
    reps: str | None = Field(default=None, max_length=40)
    weight: str | None = Field(default=None, max_length=40)
    tempo: str | None = Field(default=None, max_length=40)
    rest: str | None = Field(default=None, max_length=40)
    comment: str | None = Field(default=None, max_length=1000)
    video_url: str | None = Field(default=None, max_length=500)


class PlanDayIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    weekday: int | None = Field(default=None, ge=1, le=7)
    exercises: list[ExerciseIn] = []


class PlanVersionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    days: list[PlanDayIn] = []


class PlanCreateIn(BaseModel):
    client_id: str | None = None  # None => szablon
    title: str = Field(min_length=1, max_length=300)
    version: PlanVersionIn


class WorkoutSetIn(BaseModel):
    weight_kg: float = Field(ge=0, le=1000)
    reps: int = Field(ge=0, le=200)


class WorkoutEntryIn(BaseModel):
    exercise_index: int = Field(ge=0)
    exercise_name: str = Field(max_length=300)
    result: str | None = Field(default=None, max_length=1000)
    # Strukturalne serie (opcjonalne, obok/zamiast tekstowego wyniku).
    sets: list[WorkoutSetIn] = Field(default=[], max_length=30)
    comment: str | None = Field(default=None, max_length=1000)
    file_id: str | None = None


class WorkoutSessionIn(BaseModel):
    plan_version_id: str
    day_index: int = Field(ge=0)
    performed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field(default="DONE", pattern="^(DONE|PARTIAL|SKIPPED)$")
    comment: str | None = Field(default=None, max_length=2000)
    pain_flag: bool = False
    pain_note: str | None = Field(default=None, max_length=2000)
    entries: list[WorkoutEntryIn] = []


class NutritionVersionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    kcal: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    fat_g: int | None = Field(default=None, ge=0, le=2000)
    carbs_g: int | None = Field(default=None, ge=0, le=4000)
    sections: list[dict] = []  # [{"title","body"}]
    meals: list[dict] = []  # [{"name","description","swaps"}]
    document_id: str | None = None


class NutritionCreateIn(BaseModel):
    client_id: str
    title: str = Field(min_length=1, max_length=300)
    version: NutritionVersionIn


class ScheduleItemIn(BaseModel):
    client_id: str
    name: str = Field(min_length=1, max_length=300)
    category: str = Field(
        pattern="^(TRENING|POSILEK|NAWODNIENIE|REGENERACJA|SUPLEMENT|POMIAR|RAPORT|PLATNOSC|INNE)$"
    )
    time_of_day: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    days_of_week: str = Field(default="1,2,3,4,5,6,7", max_length=30)
    instruction: str | None = Field(default=None, max_length=2000)
    start_date: str | None = None
    end_date: str | None = None
    author_note: str | None = Field(default=None, max_length=2000)


class CheckinIn(BaseModel):
    week_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    weight_kg: float | None = Field(default=None, ge=0, le=500)
    measurements: dict[str, float] = {}
    trainings_done: int | None = Field(default=None, ge=0, le=21)
    diet_adherence: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    sleep: int | None = Field(default=None, ge=1, le=5)
    hunger: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    recovery: int | None = Field(default=None, ge=1, le=5)
    pain_note: str | None = Field(default=None, max_length=2000)
    comment: str | None = Field(default=None, max_length=5000)
    questions: str | None = Field(default=None, max_length=5000)
    photo_ids: list[str] = []


class CheckinReviewIn(BaseModel):
    coach_response: str = Field(min_length=1, max_length=10000)
    # Ocena RAPORTU (kompletność/jakość zapisu), nie oceną osoby — opcjonalna.
    rating: int | None = Field(default=None, ge=1, le=5)


class MeasurementIn(BaseModel):
    kind: str = Field(min_length=1, max_length=120)
    value: float
    unit: str = Field(default="kg", max_length=30)
    measured_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class MetricDefinitionIn(BaseModel):
    client_id: str
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=30)


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    file_id: str | None = None
    # Identyfikator nadany przez urządzenie nadawcy (np. UUID) — ponowienie
    # tego samego żądania po utracie sieci nie tworzy duplikatu wiadomości.
    client_msg_id: str | None = Field(
        default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


class PaymentScheduleIn(BaseModel):
    client_id: str
    package_name: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(gt=0)
    currency: str = Field(default="PLN", max_length=10)
    period: str = Field(default="MONTHLY", pattern="^(MONTHLY|WEEKLY|ONE_OFF)$")
    first_due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    external_link: str | None = Field(default=None, max_length=500)


class PaymentStatusIn(BaseModel):
    status: str = Field(pattern="^(PENDING|PAID|OVERDUE|CANCELLED)$")
    note: str | None = Field(default=None, max_length=1000)


class ReminderIn(BaseModel):
    client_id: str
    text: str = Field(min_length=1, max_length=1000)
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class RelationshipIn(BaseModel):
    """Zaproszenie klienta: wyłącznie niezbędne dane (e-mail + imię).
    Hasła nie podaje nikt poza samym klientem — konto aktywuje jednorazowy
    link (POST /api/auth/activate)."""

    client_email: EmailStr
    client_name: str = Field(min_length=1, max_length=200)


class ActivationInspectIn(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class ActivateAccountIn(BaseModel):
    token: str = Field(min_length=16, max_length=200)
    password: str = Field(min_length=10, max_length=200)


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=16, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class MfaVerifyIn(BaseModel):
    """Drugi krok logowania: token wyzwania + kod TOTP (6 cyfr) albo kod
    odzyskiwania (XXXXX-XXXXX)."""

    mfa_token: str = Field(min_length=16, max_length=200)
    code: str = Field(min_length=6, max_length=20)


class MfaCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class ConsentGrantIn(BaseModel):
    """Udzielenie zgody JEDNEJ kategorii z katalogu (consent_catalog).
    Cel/zakres/wrażliwość/podstawa prawna wynikają z katalogu — klient
    wskazuje kategorię i (dla kategorii trenerskich) odbiorcę."""

    category: str = Field(min_length=1, max_length=40)
    grantee_id: str | None = None  # wymagane dla kategorii trenerskich
    actions: str = Field(default="read,write", max_length=200)


class ConsentDeclineIn(BaseModel):
    """Jawna odmowa zgody OPCJONALNEJ (zapisywana z historią)."""

    category: str = Field(min_length=1, max_length=40)
    grantee_id: str | None = None


class DeletionRequestIn(BaseModel):
    password: str
    confirm: str = Field(pattern="^USUŃ MOJE DANE$")


class GoalStatusIn(BaseModel):
    status: str = Field(pattern="^(ACTIVE|DONE|DROPPED)$")


class ScheduleCompletionIn(BaseModel):
    completed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field(default="DONE", pattern="^(DONE|SKIPPED)$")
    note: str | None = Field(default=None, max_length=1000)


class ObservationIn(BaseModel):
    occurred_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    schedule_item_id: str | None = None
    category: str = Field(pattern="^(SAMOPOCZUCIE|OBJAW|REAKCJA|INNE)$")
    severity: str = Field(default="INFO", pattern="^(INFO|NIEPOKOJACE)$")
    text: str = Field(min_length=1, max_length=5000)


class NutritionLogIn(BaseModel):
    logged_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    kcal: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    fat_g: int | None = Field(default=None, ge=0, le=2000)
    carbs_g: int | None = Field(default=None, ge=0, le=4000)
    water_l: float | None = Field(default=None, ge=0, le=20)
    note: str | None = Field(default=None, max_length=1000)


class KnowledgeItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(default="Inne", max_length=80)
    body: str | None = Field(default=None, max_length=20000)
    external_url: str | None = Field(default=None, max_length=500)
    file_id: str | None = None
    pinned: bool = False


class DocumentIn(BaseModel):
    client_id: str
    file_id: str
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(default="INNE", pattern="^(DIETA|PLAN|WYNIKI|INNE)$")


class ExerciseLibraryItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    muscle_group: str = Field(
        pattern="^(NOGI|PLECY|KLATKA|BARKI|RECE|BRZUCH|CALE_CIALO|MOBILNOSC|INNE)$"
    )
    how_to: str = Field(min_length=1, max_length=5000)
    benefit: str | None = Field(default=None, max_length=2000)
    equipment: str | None = Field(default=None, max_length=200)
    video_url: str | None = Field(default=None, max_length=500)


class FoodProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    category: str = Field(default="Inne", max_length=80)
    kcal_100g: float = Field(ge=0, le=1000)
    protein_100g: float = Field(ge=0, le=110)
    fat_100g: float = Field(ge=0, le=110)
    carbs_100g: float = Field(ge=0, le=110)
    default_portion_g: float | None = Field(default=None, ge=0, le=5000)


class DietSuggestionIn(BaseModel):
    """Wejście kompozytora diety: cel kcal/makro + katalog produktów
    WYBRANYCH PRZEZ TRENERA. Wynik to przejrzysta arytmetyka (podział celu
    na gramaturę), nigdy autonomiczna generacja diety przez AI — zgodnie z
    zasadą Human OS „propose-only”, plan nadal wymaga ręcznego wpisania
    przez trenera do NutritionPlanVersion."""

    target_kcal: int = Field(ge=0, le=20000)
    target_protein_g: int = Field(default=0, ge=0, le=2000)
    target_fat_g: int = Field(default=0, ge=0, le=2000)
    target_carbs_g: int = Field(default=0, ge=0, le=4000)
    product_ids: list[str] = Field(min_length=1, max_length=40)

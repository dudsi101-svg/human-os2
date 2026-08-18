from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator


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


# Subiektywne skale raportu tygodniowego (1-5).
CHECKIN_SCALE_KEYS = (
    "diet_adherence", "energy", "sleep", "hunger", "stress", "recovery",
)

# Stany odpowiedzi na pytanie skalowe — rozróżnialne w modelu danych:
# * ANSWERED        — świadomie wybrana wartość 1-5 (w tym neutralne 3),
# * SKIPPED         — świadome pominięcie pytania (bez wartości),
# * NOT_APPLICABLE  — pytanie nie dotyczy tego tygodnia (bez wartości),
# * brak klucza     — brak odpowiedzi (NO_ANSWER; także wszystkie raporty
#                     sprzed wprowadzenia scale_states — bez reinterpretacji).
CHECKIN_SCALE_STATES = ("ANSWERED", "SKIPPED", "NOT_APPLICABLE")


class CheckinPhotoIn(BaseModel):
    """Zdjęcie raportu: plik + typ ujęcia + kolejność wybrana przez klienta."""

    file_id: str = Field(min_length=1, max_length=40)
    pose: str | None = Field(default=None, pattern="^(PRZOD|BOK|TYL|INNE)$")
    position: int | None = Field(default=None, ge=0, le=100)


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
    # Stan każdej odpowiedzi skalowej (patrz CHECKIN_SCALE_STATES).
    # None = klient bez rozróżniania stanów (stare wersje formularza) —
    # wartości interpretowane jak dotychczas, bez oznaczenia świadomości.
    scale_states: dict[str, str] | None = None
    pain_note: str | None = Field(default=None, max_length=2000)
    comment: str | None = Field(default=None, max_length=5000)
    questions: str | None = Field(default=None, max_length=5000)
    photo_ids: list[str] = []
    # Nowy kształt zdjęć (typ ujęcia + kolejność); photo_ids zostaje dla
    # kompatybilności wstecznej.
    photos: list[CheckinPhotoIn] = []
    # Zadeklarowana liczba zdjęć raportu: mniej zapisanych = raport jawnie
    # CZĘŚCIOWY (dokończenie przez POST /checkins/{id}/photos).
    photos_expected: int | None = Field(default=None, ge=0, le=50)
    # Klucz idempotencji: powtórka żądania (double-click, retry po utracie
    # odpowiedzi) zwraca zapisany wynik zamiast tworzyć rewizję.
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)

    @model_validator(mode="after")
    def _validate_scale_states(self) -> CheckinIn:
        """Spójność wartości skal ze stanami odpowiedzi. Reguły działają
        tylko przy podanym scale_states — stare klienty (bez pola) wysyłają
        wartości jak dotychczas."""
        if self.scale_states is None:
            return self
        for key, state in self.scale_states.items():
            if key not in CHECKIN_SCALE_KEYS:
                raise ValueError(f"Nieznane pytanie skalowe: {key}")
            if state not in CHECKIN_SCALE_STATES:
                raise ValueError(f"Nieznany stan odpowiedzi: {state}")
            value = getattr(self, key)
            if state == "ANSWERED" and value is None:
                raise ValueError(f"Odpowiedź ANSWERED wymaga wartości 1-5: {key}")
            if state in ("SKIPPED", "NOT_APPLICABLE") and value is not None:
                raise ValueError(
                    f"Pominięte pytanie nie może mieć wartości: {key}"
                )
        for key in CHECKIN_SCALE_KEYS:
            if getattr(self, key) is not None and key not in self.scale_states:
                raise ValueError(
                    f"Wartość skali bez zadeklarowanego stanu odpowiedzi: {key}"
                )
        return self


class CheckinPhotosAttachIn(BaseModel):
    """Dokończenie częściowego raportu: dopięcie zapisanych zdjęć i/lub
    świadome zamknięcie deklaracji (set_expected) bez brakujących plików."""

    photos: list[CheckinPhotoIn] = []
    set_expected: int | None = Field(default=None, ge=0, le=50)


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
    """Ogólna zmiana statusu należności — WYŁĄCZNIE statusy administracyjne
    (payment_state.ADMINISTRATIVE_TARGETS). Statusy pieniężne (PAID,
    REFUNDED, ...) mają dedykowane endpointy rejestrujące transakcję —
    frontend nie może dowolnie ustawić „opłacona"."""

    status: str = Field(pattern="^(PENDING|OVERDUE|CANCELLED)$")
    note: str | None = Field(default=None, max_length=1000)


class PaymentMarkPaidIn(BaseModel):
    """Ręczne oznaczenie „opłacona": tworzy transakcję MANUAL_PAYMENT
    (kto/kiedy widoczne w UI) + przejście statusu. document_ref to numer
    dokumentu zewnętrznego (faktura/przelew) — bez generatora faktur."""

    amount_cents: int | None = Field(default=None, gt=0)  # domyślnie kwota należności
    currency: str | None = Field(default=None, max_length=10)
    note: str | None = Field(default=None, max_length=1000)
    document_ref: str | None = Field(default=None, max_length=120)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)


class PaymentRefundIn(BaseModel):
    """Zwrot (pełny lub częściowy) — zawsze w groszach, w walucie należności."""

    amount_cents: int = Field(gt=0)
    currency: str | None = Field(default=None, max_length=10)
    note: str | None = Field(default=None, max_length=1000)
    document_ref: str | None = Field(default=None, max_length=120)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)


class PaymentAdjustIn(BaseModel):
    """Korekta księgowa (dodatnia lub ujemna, nigdy 0) — nowy wpis,
    nie edycja; wymaga powodu."""

    amount_cents: int
    currency: str | None = Field(default=None, max_length=10)
    reason: str = Field(min_length=1, max_length=1000)
    document_ref: str | None = Field(default=None, max_length=120)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)

    @model_validator(mode="after")
    def _nonzero(self) -> PaymentAdjustIn:
        if self.amount_cents == 0:
            raise ValueError("Korekta nie może wynosić 0")
        return self


class PaymentReverseIn(BaseModel):
    """Korekta odwracająca omyłkową transakcję — ślad zostaje (append-only)."""

    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=80)


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

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator

from .muscles import EXERCISE_LEVELS, MOVEMENT_PATTERNS, validate_muscle_keys


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


class OnboardingAnswerIn(BaseModel):
    """Odpowiedź na JEDEN krok rozmowy startowej.

    `skipped=True` to świadome pominięcie pytania (zapisywane jawnie) —
    nigdy nie udajemy pominięcia pustą wartością. Treść jest walidowana
    dodatkowo po stronie serwera regułami kroku
    (`onboarding_flow.validate_answer`)."""

    step_id: str = Field(min_length=1, max_length=40)
    value: str = Field(default="", max_length=2000)
    skipped: bool = False


class OnboardingSummaryItemIn(BaseModel):
    field_key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=2000)


class OnboardingSummaryIn(BaseModel):
    """Poprawki klienta w podsumowaniu przed zatwierdzeniem."""

    items: list[OnboardingSummaryItemIn] = Field(default_factory=list, max_length=60)


class OnboardingCoachApproveIn(BaseModel):
    """Zatwierdzenie podsumowania przez trenera. `confirmed_fields` to pola,
    które trener potwierdził po rozmowie z klientem (pola oznaczone
    niepewnością wymagają tego wprost)."""

    confirmed_fields: list[str] = Field(default_factory=list, max_length=60)
    note: str | None = Field(default=None, max_length=2000)


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    kind: str = Field(default="MAIN", pattern="^(MAIN|SECONDARY)$")
    target_date: str | None = None


class ExerciseIn(BaseModel):
    """Pozycja ćwiczenia w wersji planu (treść JSON, bez migracji).

    `exercise_id` to MIĘKKIE odniesienie do bazy ćwiczeń trenera: nazwa
    jest zawsze zapisana w planie, więc zarchiwizowanie ćwiczenia w bazie
    nie psuje istniejących planów — znika tylko link do karty."""

    name: str = Field(min_length=1, max_length=300)
    exercise_id: str | None = Field(default=None, max_length=40)
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


class SupplementIn(BaseModel):
    """Pozycja suplementacji w planie żywieniowym.

    Trener personalny NIE jest lekarzem ani dietetykiem klinicznym: system
    wyłącznie PRZECHOWUJE zalecenie wprowadzone przez człowieka i wymaga
    jawnej proweniencji (`source`) — nigdy sam nie dobiera preparatu ani
    dawki. Pola `purpose`, `dose` i `timing` są obowiązkowe, żeby w planie
    nie lądowała naga nazwa preparatu bez celu i sposobu przyjmowania."""

    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(min_length=1, max_length=120)
    timing: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=300)
    # Podstawa zalecenia: kto je wydał i na jakiej podstawie (np. „zalecenie
    # lekarza z 2026-07-12", „wynik badań", „konsultacja dietetyczna").
    source: str = Field(min_length=1, max_length=300)
    form: str | None = Field(default=None, max_length=60)
    duration: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    # Deklaracja trenera, że preparat był konsultowany ze specjalistą.
    specialist_consulted: bool = False


class NutritionVersionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    kcal: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    fat_g: int | None = Field(default=None, ge=0, le=2000)
    carbs_g: int | None = Field(default=None, ge=0, le=4000)
    sections: list[dict] = []  # [{"title","body"}]
    meals: list[dict] = []  # [{"name","description","swaps"}]
    supplements: list[SupplementIn] = Field(default_factory=list, max_length=40)
    document_id: str | None = None


class NutritionCreateIn(BaseModel):
    client_id: str
    title: str = Field(min_length=1, max_length=300)
    version: NutritionVersionIn


class SupplementReminderIn(BaseModel):
    """Prośba o przypomnienie dla JEDNEJ pozycji suplementacji. Dawka
    i sposób przyjmowania są brane z planu (po nazwie) — tutaj wskazujemy
    tylko, o której i w jakie dni przypominać."""

    name: str = Field(min_length=1, max_length=200)
    time_of_day: str = Field(pattern=r"^\d{2}:\d{2}$")
    days_of_week: str = Field(default="1,2,3,4,5,6,7", max_length=30)


class SupplementRemindersIn(BaseModel):
    entries: list[SupplementReminderIn] = Field(min_length=1, max_length=40)


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
    """Wejście edytora bazy ćwiczeń. Pola rozszerzonego opisu są
    opcjonalne — stare ćwiczenia (tylko `how_to`/`benefit`) nadal
    zapisują się i wyświetlają bez zmian."""

    name: str = Field(min_length=1, max_length=300)
    muscle_group: str = Field(
        pattern="^(NOGI|PLECY|KLATKA|BARKI|RECE|BRZUCH|CALE_CIALO|MOBILNOSC|CARDIO|INNE)$"
    )
    how_to: str = Field(min_length=1, max_length=5000)
    benefit: str | None = Field(default=None, max_length=2000)
    equipment: str | None = Field(default=None, max_length=200)
    video_url: str | None = Field(default=None, max_length=500)
    muscles_primary: list[str] = Field(default_factory=list, max_length=12)
    muscles_secondary: list[str] = Field(default_factory=list, max_length=12)
    level: str | None = None
    pattern: str | None = None
    steps: list[str] = Field(default_factory=list, max_length=12)
    mistakes: list[str] = Field(default_factory=list, max_length=12)
    cues: list[str] = Field(default_factory=list, max_length=8)
    safety: str | None = Field(default=None, max_length=2000)
    easier: str | None = Field(default=None, max_length=1000)
    harder: str | None = Field(default=None, max_length=1000)
    tempo_hint: str | None = Field(default=None, max_length=200)
    breathing: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def _check_dictionaries(self):
        unknown = validate_muscle_keys(
            [*self.muscles_primary, *self.muscles_secondary]
        )
        if unknown:
            raise ValueError(
                "Nieznane partie mięśniowe: " + ", ".join(sorted(set(unknown)))
            )
        if self.level is not None and self.level not in EXERCISE_LEVELS:
            raise ValueError(f"Nieznany poziom: {self.level}")
        if self.pattern is not None and self.pattern not in MOVEMENT_PATTERNS:
            raise ValueError(f"Nieznany wzorzec ruchu: {self.pattern}")
        for label, values, limit in (
            ("kroków techniki", self.steps, 600),
            ("błędów", self.mistakes, 400),
            ("wskazówek", self.cues, 300),
        ):
            for value in values:
                if not value.strip():
                    raise ValueError(f"Pusta pozycja na liście {label}")
                if len(value) > limit:
                    raise ValueError(f"Za długa pozycja na liście {label}")
        return self


class FoodProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    category: str = Field(default="Inne", max_length=80)
    kcal_100g: float = Field(ge=0, le=1000)
    protein_100g: float = Field(ge=0, le=110)
    fat_100g: float = Field(ge=0, le=110)
    carbs_100g: float = Field(ge=0, le=110)
    default_portion_g: float | None = Field(default=None, ge=0, le=5000)
    # Pola z migracji nr 18 — wszystkie opcjonalne; pominięcie ich w żądaniu
    # zachowuje zachowanie sprzed rozbudowy katalogu (zgodność wsteczna).
    fiber_100g: float | None = Field(default=None, ge=0, le=110)
    unit_name: str | None = Field(default=None, max_length=60)
    unit_grams: float | None = Field(default=None, gt=0, le=5000)
    source: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=300)


class PortionCalcIn(BaseModel):
    """Kalkulator porcji: gramy ALBO liczba sztuk (jednostka produktu).
    Podanie obu naraz jest błędem — wynik ma być jednoznaczny."""

    product_id: str = Field(min_length=1, max_length=40)
    grams: float | None = Field(default=None, ge=0, le=10000)
    units: float | None = Field(default=None, ge=0, le=100)


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

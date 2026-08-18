export interface Exercise {
  name: string;
  /** Miękkie odniesienie do bazy ćwiczeń trenera. Nazwa jest już zapisana
   * w planie, więc archiwizacja ćwiczenia nie psuje planu — znika tylko
   * link do karty z techniką. */
  exercise_id?: string | null;
  sets?: string | null;
  reps?: string | null;
  weight?: string | null;
  tempo?: string | null;
  rest?: string | null;
  comment?: string | null;
  video_url?: string | null;
}

export interface PlanDay {
  name: string;
  weekday?: number | null;
  exercises: Exercise[];
}

export interface PlanVersion {
  id: string;
  plan_id?: string;
  version_no: number;
  reason: string;
  content: { days: PlanDay[] };
  created_by: string;
  created_at: string;
}

export interface TrainingPlan {
  id: string;
  client_id: string | null;
  title: string;
  status: string;
  current_version_no: number;
  is_template: boolean;
  current_version?: PlanVersion | null;
}

/** Pozycja suplementacji w planie diety. Trener nie jest lekarzem —
 * aplikacja wyłącznie przechowuje zalecenie człowieka wraz z jego
 * podstawą (`source`); nic nie jest dobierane automatycznie. */
export interface SupplementEntry {
  name: string;
  dose: string;
  timing: string;
  purpose: string;
  source: string;
  form?: string | null;
  duration?: string | null;
  notes?: string | null;
  specialist_consulted?: boolean;
}

export interface NutritionContent {
  kcal?: number | null;
  protein_g?: number | null;
  fat_g?: number | null;
  carbs_g?: number | null;
  sections: { title: string; body: string }[];
  meals: { name: string; description?: string; swaps?: string }[];
  /** Wersje planu sprzed wprowadzenia suplementacji: pusta lista z API. */
  supplements: SupplementEntry[];
}

export interface NutritionVersion {
  id: string;
  version_no: number;
  reason: string;
  content: NutritionContent;
  document_id: string | null;
  /** file_id aktywnego dokumentu diety — do pobrania przez /api/files. */
  document_file_id: string | null;
  created_at: string;
}

export interface ScheduleItem {
  id: string;
  name: string;
  category: string;
  time_of_day: string | null;
  days_of_week: string;
  instruction: string | null;
  author_id: string;
  author_note: string | null;
  status: string;
}

/** Stan odpowiedzi na pytanie skalowe raportu (payload.scale_states):
 * ANSWERED = świadomie wybrana wartość (w tym neutralne 3),
 * SKIPPED = świadome pominięcie, NOT_APPLICABLE = nie dotyczy;
 * brak klucza = brak odpowiedzi (także raporty sprzed rozróżniania). */
export type ScaleAnswerState = "ANSWERED" | "SKIPPED" | "NOT_APPLICABLE";

export interface CheckinPhotoRef {
  id: string;
  file_id: string;
  pose: string | null;
  position: number | null;
  taken_at: string;
}

export interface CheckinData {
  id: string;
  week_start: string;
  payload: Record<string, unknown> & {
    scale_states?: Record<string, ScaleAnswerState>;
  };
  status: string;
  revision: number;
  submitted_at: string;
  coach_response: string | null;
  rating: number | null;
  photo_ids: string[];
  photos: CheckinPhotoRef[];
  /** Raport był poprawiany po wysłaniu (historia w /revisions). */
  corrected: boolean;
  /** False = raport sprzed rozróżniania stanów odpowiedzi — wartości skal
   * mogły zostać na domyślnym 3/5 (dane mniej wiarygodne). */
  scales_declared: boolean;
  /** Stan plikowy raportu: mniej zapisanych zdjęć niż zadeklarowano =
   * raport jawnie CZĘŚCIOWY (do dokończenia). */
  photos_expected: number | null;
  photos_attached: number;
  photos_complete: boolean;
}

export const POSE_LABELS: Record<string, string> = {
  PRZOD: "przód",
  BOK: "bok",
  TYL: "tył",
  INNE: "inne",
};

export interface MeasurementRow {
  id: string;
  kind: string;
  value: number;
  unit: string;
  measured_at: string;
  source: string;
}

export interface PaymentTransactionRow {
  id: string;
  kind: string; // MANUAL_PAYMENT / PROVIDER_PAYMENT / REFUND / ADJUSTMENT / REVERSAL
  amount_cents: number;
  currency: string;
  document_ref: string | null;
  note: string | null;
  reverses_transaction_id: string | null;
  reversed: boolean;
  provider: string | null;
  created_by: string;
  created_by_name: string | null;
  created_at: string;
}

export interface PaymentRecordRow {
  id: string;
  due_date: string;
  amount_cents: number;
  currency: string;
  status: string;
  effective_status: string; // status z zaległością liczoną serwerowo
  paid_at: string | null;
  marked_by: string | null;
  marked_by_name: string | null;
  marked_at: string | null;
  note: string | null;
  transactions: PaymentTransactionRow[];
  payment_link: string | null;
}

export interface PaymentStatusChangeRow {
  id: string;
  from_status: string;
  to_status: string;
  reason: string | null;
  transaction_id: string | null;
  changed_by: string;
  changed_by_name: string | null;
  changed_at: string;
}

export interface PaymentHistory {
  record: {
    id: string; due_date: string; amount_cents: number; currency: string;
    status: string; paid_at: string | null; marked_by: string | null;
    marked_by_name: string | null; marked_at: string | null; note: string | null;
  };
  status_changes: PaymentStatusChangeRow[];
  transactions: PaymentTransactionRow[];
}

export interface ReconciliationRow {
  record_id: string;
  client_id: string;
  client_name: string | null;
  package_name: string;
  due_date: string;
  status: string;
  currency: string;
  expected_cents: number;
  collected_cents: number;
  refunded_cents: number;
  adjustments_cents: number;
  balance_cents: number;
  difference_cents: number;
  source: string; // MANUAL / PROVIDER / MIXED / LEGACY / NONE
  legacy_mark: boolean;
}

export interface ReconciliationSummary {
  expected_cents: number;
  collected_cents: number;
  refunded_cents: number;
  adjustments_cents: number;
  balance_cents: number;
  difference_cents: number;
  records: number;
  legacy_marks: number;
}

export interface PaymentScheduleRow {
  schedule_id: string;
  package_name: string;
  amount_cents: number;
  currency: string;
  period: string;
  external_link: string | null;
  records: PaymentRecordRow[];
}

export interface ProfileFieldRow {
  field_key: string;
  value: string;
  source: string;
  author_id: string;
  version: number;
  sensitive: boolean;
  created_at: string;
  is_current?: boolean;
}

export interface GoalRow {
  id: string;
  title: string;
  description: string | null;
  kind: string;
  target_date: string | null;
  status: string;
}

export interface ConsentRow {
  id: string;
  grantee_id: string;
  grantee_name: string | null;
  category: string | null;
  legal_basis: string | null;
  source: string | null;
  purpose: string;
  domain: string;
  actions: string;
  allow_sensitive: boolean;
  consent_text_version: string;
  document_version_current: boolean;
  granted_at: string;
  revoked_at: string | null;
  confirmed_at: string | null;
  denied_at: string | null;
}

/** Kategoria zgody z katalogu backendu (pełny opis RODO). */
export interface ConsentCategoryInfo {
  key: string;
  label: string;
  purpose: string;
  domain: string;
  grantee_kind: "COACH" | "SYSTEM";
  required: boolean;
  sensitive: boolean;
  legal_basis: string;
  cel: string;
  zakres: string;
  odbiorcy: string;
  okres: string;
  dobrowolnosc: string;
  wycofanie: string;
  document_version: string;
}

export interface ConsentsResponse {
  document_version: string;
  catalog: ConsentCategoryInfo[];
  consents: ConsentRow[];
}

export interface ThreadRow {
  id: string;
  with_user: { id: string; display_name: string };
  last_message: { body: string; author_id: string; created_at: string } | null;
  unread: number;
}

export interface MessageRow {
  id: string;
  author_id: string;
  body: string;
  file_id: string | null;
  created_at: string;
  /** Urządzenie odbiorcy odebrało wiadomość (SSE lub otwarcie wątku). */
  delivered_at: string | null;
  read_at: string | null;
  /** Identyfikator nadany przez urządzenie nadawcy (deduplikacja ponowień). */
  client_msg_id?: string | null;
  /** Lokalnie: wiadomość w drodze (optymistyczna, czeka na potwierdzenie). */
  pending?: boolean;
}

export interface TodayData {
  date: string;
  weekday: number;
  workout: {
    plan_id: string;
    plan_title: string;
    plan_version_id: string;
    version_no: number;
    day_index: number;
    day: PlanDay;
    done_today: boolean;
  } | null;
  nutrition: { plan_id: string; title: string; kcal: number | null; protein_g: number | null; fat_g: number | null; carbs_g: number | null } | null;
  schedule: { id: string; name: string; category: string; time_of_day: string | null; instruction: string | null; done_today: boolean }[];
  reminders: { id: string; text: string; due_date: string }[];
  checkin_due: string | null;
  next_payment: { record_id: string; due_date: string; amount_cents: number; currency: string; status: string; package_name: string | null; external_link: string | null } | null;
  last_coach_message: { thread_id: string; body: string; created_at: string; unread: boolean } | null;
}

export interface CoachClientRow {
  client_id: string;
  display_name: string;
  email: string;
  relationship_status: string;
  consent_active: boolean;
  /** Konto z zaproszenia czekające na aktywację (klient nie ustawił hasła). */
  account_pending: boolean;
  /** Termin ważności aktywnego zaproszenia (bez tokenu — serwer zna tylko hash). */
  invitation_expires_at: string | null;
  consent_scopes: {
    collaboration: boolean;
    training: boolean;
    health: boolean;
    nutrition: boolean;
    photos: boolean;
  };
  flags: {
    checkin_overdue: boolean;
    awaiting_review: boolean;
    payment_overdue: boolean;
    unread_messages: number;
    recent_pain_reports: number;
    flagged_observations: number;
  };
  last_checkin_week: string | null;
}

export interface ConsultSlotRow {
  id: string;
  coach_id: string;
  starts_at: string; // YYYY-MM-DDTHH:MM (czas lokalny)
  duration_min: number;
  status: string;
  client_id: string | null;
  client_name: string | null;
  booked_at: string | null;
}

export interface CoachDashboardData {
  upcoming_consultations: number;
  active_clients: number;
  awaiting_review: number;
  checkin_overdue_clients: number;
  payment_overdue_clients: number;
  unread_messages_total: number;
  flagged_observations_14d: number;
  recent_pain_reports_14d: number;
  exercises_count: number;
  food_products_count: number;
  knowledge_items_count: number;
}

export interface WorkoutSet {
  weight_kg: number;
  reps: number;
}

export interface WorkoutRow {
  id: string;
  plan_version_id: string;
  day_index: number;
  performed_on: string;
  status: string;
  comment: string | null;
  pain_flag: boolean;
  pain_note: string | null;
  entries: { exercise_index: number; exercise_name: string; result: string | null;
    sets: WorkoutSet[]; comment: string | null; file_id: string | null }[];
}

export interface StrengthSeriesRow {
  exercise_name: string;
  points: { date: string; volume_kg: number; e1rm_kg: number }[];
}

export interface DocumentRow {
  id: string;
  file_id: string;
  title: string;
  category: string;
  uploaded_by: string;
  created_at: string;
}

export interface ReceiptRow {
  id: string;
  event_id: string;
  event_hash: string;
  action: string;
  actor_id: string;
  subject_id?: string;
  /** Wolny tekst — panel admina go NIE otrzymuje (może zawierać treści
   *  pochodne danych zdrowotnych); obecny w historii klienta u trenera. */
  summary?: string;
  created_at: string;
}

export const CATEGORY_LABELS: Record<string, string> = {
  TRENING: "Trening",
  POSILEK: "Posiłek",
  NAWODNIENIE: "Nawodnienie",
  REGENERACJA: "Regeneracja",
  SUPLEMENT: "Suplement",
  POMIAR: "Pomiar",
  RAPORT: "Raport",
  PLATNOSC: "Płatność",
  INNE: "Inne",
};

export const PAYMENT_LABELS: Record<string, string> = {
  PLANNED: "Zaplanowana",
  PENDING: "Oczekuje",
  IN_PROGRESS: "W trakcie",
  PAID: "Opłacona",
  OVERDUE: "Zaległa",
  FAILED: "Nieudana",
  CANCELLED: "Anulowana",
  PARTIALLY_REFUNDED: "Częściowy zwrot",
  REFUNDED: "Zwrócona",
};

export const PAYMENT_TX_LABELS: Record<string, string> = {
  MANUAL_PAYMENT: "Wpłata (adnotacja trenera)",
  PROVIDER_PAYMENT: "Wpłata (operator)",
  REFUND: "Zwrot",
  ADJUSTMENT: "Korekta",
  REVERSAL: "Korekta odwracająca",
};

/** Klasa badge dla statusu płatności — jedna definicja dla obu paneli. */
export function paymentBadgeClass(status: string): string {
  if (status === "PAID") return "badge badge--ok";
  if (status === "OVERDUE" || status === "FAILED") return "badge badge--danger";
  if (status === "CANCELLED" || status === "PLANNED") return "badge";
  if (status === "REFUNDED" || status === "PARTIALLY_REFUNDED") return "badge badge--accent";
  return "badge badge--warn"; // PENDING / IN_PROGRESS
}

export interface GoalProgress {
  id: string;
  title: string;
  target_date: string | null;
  days_remaining: number | null;
  created_at: string;
}

export interface SeriesPoint {
  date: string;
  value: number;
  unit?: string;
  /** Punkt samopoczucia: true = wartość świadomie zadeklarowana
   * (scale_states); false = raport sprzed rozróżniania — wartość mogła
   * zostać na domyślnym 3/5 (mniej wiarygodna). */
  declared?: boolean;
}

export interface AdherenceBucket {
  done: number;
  total: number;
  pct: number | null;
}

export interface MonitoringObservation {
  id: string;
  occurred_on: string;
  category: string;
  severity: string;
  text: string;
}

export interface ObservationRow extends MonitoringObservation {
  schedule_item_id: string | null;
  schedule_item_name: string | null;
  created_by: string;
  created_at: string;
}

export interface MonitoringData {
  period_days: number;
  goal: GoalProgress | null;
  measurement_series: Record<string, SeriesPoint[]>;
  wellbeing_series: Record<string, SeriesPoint[]>;
  nutrition: { target_kcal: number | null; log_series: SeriesPoint[] };
  adherence: Record<string, AdherenceBucket>;
  observations: MonitoringObservation[];
}

export interface NutritionLogRow {
  id: string;
  logged_on: string;
  kcal: number | null;
  protein_g: number | null;
  fat_g: number | null;
  carbs_g: number | null;
  water_l: number | null;
  note: string | null;
}

export const OBSERVATION_CATEGORY_LABELS: Record<string, string> = {
  SAMOPOCZUCIE: "Samopoczucie",
  OBJAW: "Objaw",
  REAKCJA: "Reakcja",
  INNE: "Inne",
};

export const SEVERITY_LABELS: Record<string, string> = {
  INFO: "Informacja",
  NIEPOKOJACE: "Niepokojące",
};

export const WELLBEING_LABELS: Record<string, string> = {
  sleep: "Sen",
  energy: "Energia",
  stress: "Stres",
  hunger: "Głód",
  recovery: "Regeneracja",
  diet_adherence: "Realizacja diety",
};

export interface KnowledgeItemRow {
  id: string;
  coach_id: string;
  title: string;
  category: string;
  body: string | null;
  external_url: string | null;
  file_id: string | null;
  pinned: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export const KNOWLEDGE_CATEGORY_SUGGESTIONS = [
  "Trening", "Dieta", "Regeneracja", "Motywacja", "Zdrowie", "Suplementacja", "Inne",
];

export const KIND_LABELS: Record<string, string> = {
  weight: "Masa ciała",
  waist: "Talia",
  chest: "Klatka",
  hips: "Biodra",
  arm: "Ramię",
  thigh: "Udo",
};

export interface ExerciseLibraryItem {
  id: string;
  coach_id: string;
  name: string;
  muscle_group: string;
  /** Pola zgodności wstecznej — ćwiczenia sprzed rozbudowy bazy mają
   * tylko how_to/benefit i nadal wyświetlają się poprawnie. */
  how_to: string;
  benefit: string | null;
  equipment: string | null;
  video_url: string | null;
  status: string;
  muscles_primary: string[];
  muscles_secondary: string[];
  level: string | null;
  pattern: string | null;
  steps: string[];
  mistakes: string[];
  cues: string[];
  safety: string | null;
  easier: string | null;
  harder: string | null;
  tempo_hint: string | null;
  breathing: string | null;
  created_at: string;
  updated_at: string;
}

/** Odpowiedź list ćwiczeń: filtry i paginacja są po stronie API. */
export interface ExerciseListResponse {
  items: ExerciseLibraryItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export const MUSCLE_GROUP_LABELS: Record<string, string> = {
  NOGI: "Nogi",
  PLECY: "Plecy",
  KLATKA: "Klatka piersiowa",
  BARKI: "Barki",
  RECE: "Ręce",
  BRZUCH: "Brzuch",
  CALE_CIALO: "Całe ciało",
  MOBILNOSC: "Mobilność",
  CARDIO: "Cardio",
  INNE: "Inne",
};

/** KONTRAKT słownika partii mięśniowych — te same klucze co backend
 * (`dzik_os/muscles.py::MUSCLE_LABELS`) i przyszły rysunek sylwetki.
 * Klucze nie mogą być zmieniane bez migracji danych. */
export const MUSCLE_LABELS: Record<string, string> = {
  KLATKA_PIERSIOWA: "klatka piersiowa",
  NAJSZERSZY_GRZBIETU: "najszerszy grzbietu",
  CZWOROBOCZNY: "czworoboczny",
  ROMBOIDALNE: "romboidalne",
  PROSTOWNIKI_GRZBIETU: "prostowniki grzbietu",
  BARK_PRZEDNI: "bark przedni",
  BARK_BOCZNY: "bark boczny",
  BARK_TYLNY: "bark tylny",
  BICEPS: "biceps",
  TRICEPS: "triceps",
  PRZEDRAMIE: "przedramię",
  BRZUCH_PROSTY: "brzuch prosty",
  BRZUCH_SKOSNY: "brzuch skośny",
  MIESNIE_GLEBOKIE: "mięśnie głębokie",
  POSLADKI: "pośladki",
  CZWOROGLOWY_UDA: "czworogłowy uda",
  DWUGLOWY_UDA: "dwugłowy uda",
  PRZYWODZICIELE: "przywodziciele",
  ODWODZICIELE: "odwodziciele",
  LYDKA: "łydka",
  ZGINACZE_BIODRA: "zginacze biodra",
};

export const EXERCISE_LEVEL_LABELS: Record<string, string> = {
  POCZATKUJACY: "początkujący",
  SREDNIOZAAWANSOWANY: "średniozaawansowany",
  ZAAWANSOWANY: "zaawansowany",
};

export const MOVEMENT_PATTERN_LABELS: Record<string, string> = {
  PRZYSIAD: "przysiad",
  ZAWIAS_BIODROWY: "zawias biodrowy",
  WYPYCHANIE_POZIOME: "wypychanie poziome",
  WYPYCHANIE_PIONOWE: "wypychanie pionowe",
  PRZYCIAGANIE_POZIOME: "przyciąganie poziome",
  PRZYCIAGANIE_PIONOWE: "przyciąganie pionowe",
  WYKROK: "wykrok",
  NOSZENIE: "noszenie",
  ROTACJA: "rotacja",
  ANTYROTACJA: "antyrotacja",
  IZOLACJA: "izolacja",
  CARDIO: "cardio",
  MOBILNOSC: "mobilność",
};

/** Etykiety partii mięśniowych do wyświetlenia (nieznany klucz zostaje
 * pokazany dosłownie — dane trenera nigdy nie znikają po cichu). */
export function muscleLabels(keys: string[]): string {
  return keys.map((k) => MUSCLE_LABELS[k] ?? k).join(", ");
}

export interface FoodProductRow {
  id: string;
  coach_id: string;
  name: string;
  category: string;
  kcal_100g: number;
  protein_100g: number;
  fat_100g: number;
  carbs_100g: number;
  default_portion_g: number | null;
  /** Pola z migracji nr 18 — zawsze opcjonalne (null = brak danych, nie zero). */
  fiber_100g?: number | null;
  unit_name?: string | null;
  unit_grams?: number | null;
  source?: string | null;
  note?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Stronicowana odpowiedź katalogu produktów (API filtruje i stronicuje —
 * widok nigdy nie ładuje całej bazy 400+ pozycji naraz). */
export interface FoodProductPage {
  items: FoodProductRow[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  categories: string[];
  /** Informacja o przybliżonym charakterze wartości — pokazywana w UI. */
  disclaimer: string;
}

export type FoodSort = "name" | "kcal" | "protein";

export const FOOD_SORT_LABELS: Record<FoodSort, string> = {
  name: "Nazwa (A→Z)",
  kcal: "Kalorie (najwięcej)",
  protein: "Białko (najwięcej)",
};

export interface FoodImportError {
  row: number;
  field: string;
  message: string;
}

export interface FoodImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: FoodImportError[];
  unknown_columns: string[];
}

export interface DietSuggestionItem {
  product_id: string;
  name: string;
  macro_role: "PROTEIN" | "FAT" | "CARB";
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  fiber_g?: number | null;
  /** Ile to sztuk jednostki produktu (gdy produkt ma jednostkę sztukową). */
  units?: number | null;
  unit_name?: string | null;
}

export interface PersonalRecordRow {
  exercise_name: string;
  best_kg: number;
  achieved_on: string;
  previous_best_kg: number | null;
  attempts: number;
  is_new: boolean;
}

export interface SinceStartRow {
  kind: string;
  unit: string;
  first_value: number;
  first_date: string;
  latest_value: number;
  latest_date: string;
  delta: number;
}

export interface PersonalRecordsData {
  records: PersonalRecordRow[];
  since_start: SinceStartRow[];
}

export interface DietSuggestionResult {
  target: { kcal: number; protein_g: number; fat_g: number; carbs_g: number };
  items: DietSuggestionItem[];
  totals: {
    kcal: number; protein_g: number; fat_g: number; carbs_g: number; fiber_g?: number;
  };
  warnings: string[];
  note: string;
  disclaimer?: string;
}

// --- Wspólne wyzwania (moduł prywatny — tylko zaproszeni) ---

export interface ChallengeBase {
  id: string;
  kind: "INDIVIDUAL" | "GROUP";
  title: string;
  description: string | null;
  unit: string;
  unit_label: string;
  goal_value: number | null;
  starts_on: string;
  ends_on: string;
  timezone: string;
  visibility: string;
  status: "DRAFT" | "ACTIVE" | "FINISHED" | "CANCELLED";
  max_entries_per_day: number;
  aggregates_adjusted: boolean;
  is_past: boolean;
}

export interface ChallengeProgress {
  value: number;
  goal_value: number | null;
  progress_pct: number | null;
  has_manual: boolean;
}

export interface ChallengeMe {
  participant_id?: string;
  status: string;
  alias?: string | null;
  share_result?: boolean;
  ranking_opt_in?: boolean;
  auto_count_workouts?: boolean;
  progress?: ChallengeProgress;
}

export interface ChallengeInvitation extends ChallengeBase {
  invited_by_name: string | null;
  invited_at?: string;
  explainer: string;
}

export interface ChallengeListItem extends ChallengeBase {
  me: ChallengeMe;
  progress: ChallengeProgress;
}

export interface ChallengeSharedRow {
  user_id: string;
  alias: string;
  value: number;
  progress_pct?: number;
  has_manual: boolean;
  is_me: boolean;
  position?: number;
}

export interface ChallengeGroup {
  active_participants: number;
  total_value: number;
  avg_progress_pct: number | null;
  completed_count: number | null;
  aggregates_adjusted: boolean;
}

export interface ChallengeDetail extends ChallengeBase {
  explainer: string;
  me?: ChallengeMe;
  invited_by_name?: string | null;
  group?: ChallengeGroup;
  shared?: ChallengeSharedRow[];
  ranking?: ChallengeSharedRow[];
  participants?: {
    participant_id: string;
    user_id: string;
    alias: string | null;
    status: string;
    share_result: boolean;
  }[];
  open_reports?: number;
}

export interface ChallengeEntryRow {
  id: string;
  entry_date: string;
  value: number;
  note: string | null;
  source: "MANUAL" | "WORKOUT";
  status: "ACTIVE" | "CORRECTED";
  corrects_entry_id: string | null;
  created_at: string;
}

export interface ChallengeUnit {
  key: string;
  label: string;
  fixed_value: number | null;
  max_value: number;
}

export interface CoachChallengeRow extends ChallengeBase {
  active_participants: number;
  pending_invitations: number;
  open_reports: number;
}

export interface ChallengeReportRow {
  id: string;
  reporter_name: string | null;
  reported_user_id: string;
  reported_name: string | null;
  reason: string;
  status: "OPEN" | "RESOLVED";
  resolution: string | null;
  resolution_note: string | null;
  created_at: string;
  resolved_at: string | null;
}

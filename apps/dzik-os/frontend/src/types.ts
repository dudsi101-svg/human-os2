export interface Exercise {
  /** Stabilna tożsamość elementu w szkicach (0.58.0); brak = wersja sprzed szkiców. */
  id?: string | null;
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
  /** Docelowy zapas powtórzeń, np. „2–3". Zakres, nie liczba — tak podaje
   * się to w praktyce treningowej. */
  target_rir?: string | null;
  /** Kod modelu progresji (np. „PRG-DOUBLE"). To OPIS dla człowieka —
   * aplikacja nic na jego podstawie nie przelicza ani nie podnosi sama. */
  progression?: string | null;
}

/** Model progresji z wbudowanego katalogu szablonów. */
export interface ProgressionModel {
  name: string;
  when: string;
  action: string;
  hold: string;
  regress: string;
  note?: string | null;
}

/** Pozycja katalogu gotowych schematów treningowych. */
export interface BuiltinPlanTemplate {
  id: string;
  name: string;
  level: string;
  goal: string;
  days_per_week: number;
  duration_min: string;
  intensity: string;
  target_rir: string;
  split: string;
  description: string;
  deload: string;
  days: number;
  exercises: number;
}

export interface PlanDay {
  id?: string | null;
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
  meals: NutritionMealRow[];
  /** Wersje planu sprzed wprowadzenia suplementacji: pusta lista z API. */
  supplements: SupplementEntry[];
  /** Kreator dań (0.57.0): metadane menu z całych receptur — tylko wersje z kreatora. */
  kulinaria?: KulinariaMetaWersji;
}

export interface NutritionMealRow {
  name: string;
  description?: string;
  swaps?: string;
  /** Pola kreatora dań (0.57.0) — brak = posiłek wpisany ręcznie albo ze starego kreatora. */
  day?: string;
  slot?: string;
  recipe_id?: string;
  portion_variant?: string;
  draft?: boolean;
  /** Cel śladu decyzji „d{dzień}:m{i}” — pod „Dlaczego to danie?”. */
  trace_target?: string;
  /** Ręczna zmiana posiłku z kreatora dań (0.58.0): wartości i walidacja nie obowiązują. */
  edited_manually?: boolean;
  nutrition?: Record<string, number> | null;
}

export interface KulinariaMetaWersji {
  engine_version: string;
  plan_id: string;
  mode: "preview" | "production";
  status: string;
  issues: unknown[];
  config: Record<string, unknown>;
  screening_status: string;
  targets_reference: string | null;
  shopping_list: KulinariaZakup[];
  versions: Record<string, string>;
  carb_compliance_verified: boolean;
  nutrition_scope: string[];
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
  /** Trenerzy z AKTYWNEJ relacji — odbiorcy zgód trenerskich niezależnie
   *  od historii zgód (konto bez żadnego wpisu też może ich udzielić). */
  coaches: { id: string; display_name: string }[];
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

export interface HabitOut {
  id: string;
  client_id: string;
  name: string;
  days_of_week: string;
  target_days: number;
  author_id: string;
  author_note: string | null;
  started_on: string;
  status: "ACTIVE" | "GRADUATED" | "ARCHIVED";
  graduated_on: string | null;
  ack_on: string | null;
  progress: number;
  progress_label: string;
  done_count: number;
  planned_count: number;
  scheduled_today: boolean;
  done_today: boolean;
  created_at: string;
}

export interface DailyMessage {
  text: string;
  author: string;
  note: string;
}

export interface TodayData {
  date: string;
  weekday: number;
  /** Panel rozwojowy (0.63.0). */
  greeting_name: string;
  daily_message: DailyMessage;
  habits: HabitOut[];
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
    /** Ostatnia przesłana wersja wywiadu bez przeglądu trenera (0.59.0). */
    interview_to_review?: number;
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
  /** Tekst przepisany ze skanu (OCR) i ZATWIERDZONY przez człowieka —
   * dzięki niemu dokument da się przeszukać. null = brak przepisania. */
  ocr_text?: string | null;
  ocr_engine?: string | null;
  ocr_at?: string | null;
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
  /** Proweniencja wpisu (migracja nr 22). `null` = ćwiczenie sprzed tej
   * migracji, o którym po prostu nie wiemy — nigdy nie udajemy MANUAL. */
  source_kind: string | null;
  source_engine: string | null;
  /** Import gotowej biblioteki (migracja nr 24). */
  name_en: string | null;
  tags: string[];
  /** Z jakiej dokładnie biblioteki i z jakiej daty pochodzi pozycja. */
  source_ref: string | null;
  /** NOTATKA ROBOCZA TRENERA („opis techniki pochodzi z szablonu
   * biblioteki”). API wysyła ją WYŁĄCZNIE na widoki trenera — w widoku
   * klienta pola po prostu nie ma, bo dla niego wyglądałoby jak ocena
   * jakości ćwiczenia wystawiona przez system. */
  review_reason?: string | null;
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

// --- Kreator diety (propozycja dnia/tygodnia — propose-only) ---

export interface DietWizardEntry {
  product_id: string;
  name: string;
  category: string;
  /** "coach" = katalog trenera, "builtin" = dopełnienie z wbudowanej bazy. */
  source: "coach" | "builtin";
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  units: number | null;
  unit_name: string | null;
}

export interface DietWizardMeal {
  name: string;
  kcal_share: number;
  entries: DietWizardEntry[];
  totals: { kcal: number; protein_g: number; fat_g: number; carbs_g: number };
  prep_minutes: number;
  prep_suggestion: string;
}

export interface DietWizardDay {
  day_no: number;
  meals: DietWizardMeal[];
  totals: { kcal: number; protein_g: number; fat_g: number; carbs_g: number };
}

export interface DietWizardResult {
  target: { kcal: number; protein_g: number; fat_g: number; carbs_g: number };
  days: DietWizardDay[];
  daily_average: { kcal: number; protein_g: number; fat_g: number; carbs_g: number };
  warnings: string[];
  recommendation: string | null;
  disclaimer: string;
  nutrition_plan_content: {
    kcal: number; protein_g: number; fat_g: number; carbs_g: number;
    sections: { title: string; body: string }[];
    meals: { name: string; description: string; swaps: string }[];
  };
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

/** Wiersz grupy w podsumowaniu tygodnia trenera (metadane operacyjne —
 *  nigdy ranking; brak punktacji i ocen z definicji). */
export interface WeeklyDigestRow {
  client_id: string;
  display_name: string;
  last_checkin_week: string | null;
  /** Wyłącznie w grupie „flagged": liczniki z ostatnich 14 dni. */
  flagged_observations?: number;
  recent_pain_reports?: number;
}

export interface WeeklyDigestData {
  week_start: string;
  generated_for: string;
  active_clients: number;
  reported_this_week: WeeklyDigestRow[];
  awaiting_review: WeeklyDigestRow[];
  checkin_overdue: WeeklyDigestRow[];
  payment_overdue: WeeklyDigestRow[];
  flagged: (WeeklyDigestRow & {
    flagged_observations: number;
    recent_pain_reports: number;
  })[];
  upcoming_consultations: {
    id: string;
    starts_at: string;
    duration_min: number;
    client_name: string | null;
  }[];
}

// --- Wiedza (0.56.0) ---------------------------------------------------------

export interface WiedzaKarta {
  id: string;
  revision: number;
  status: string;
  category: string;
  category_label: string;
  title: string;
  summary: string;
  estimated_read_minutes: number | null;
  evidence_kind: string | null;
  exercise_id: string | null;
  /** Treść robocza (bez przeglądu) — widoczna tylko w trybie demonstracyjnym. */
  szkic: boolean;
  przeglad_po_terminie: boolean;
  next_review_at: string | null;
}

export interface WiedzaZrodlo {
  id: string;
  title: string | null;
  authors?: string | null;
  year?: string | null;
  url?: string | null;
  type?: string | null;
  /** merytoryczne / inspiracja_produktowa — inspiracje nie są dowodem. */
  rola: string;
}

export interface WiedzaKartaPelna extends WiedzaKarta {
  steps: string[];
  detail: string;
  limits: string;
  aliases: string[];
  tags: string[];
  media: null | { url: string; caption: string; transcript: string; license_reference: string };
  author_label: string;
  review: {
    approved: boolean; reviewer_id: string | null;
    reviewed_at: string | null; next_review_at: string | null;
  };
  sources: WiedzaZrodlo[];
  zapisany: boolean;
  szkice_widoczne: boolean;
}

export type WyjasnienieStatus =
  | "explained" | "general_only" | "missing_trace" | "insufficient_data"
  | "inconsistent_data" | "stale_context" | "restricted";

export interface WyjasnienieAkcja {
  label: string;
  type: "open_article" | "open_source_view" | "open_safety_flow" | "retry";
  target_id: string | null;
}

/** ExplanationResult z kontraktu pakietu Wiedza (07_SCHEMATY). */
export interface Wyjasnienie {
  status: WyjasnienieStatus;
  trace_id: string | null;
  plan_revision: number | null;
  paragraphs: string[];
  used_fact_keys: string[];
  article_refs: { id: string; revision: number }[];
  actions: WyjasnienieAkcja[];
  historical: boolean;
}

export interface WiedzaPlanSkrot {
  plan_id: string;
  title: string;
  version_no: number;
  version_created_at: string;
  reason: string;
  days: number;
  exercise_ids: string[];
  ma_rir: boolean;
  z_konfiguratora: boolean;
}

export interface WiedzaZmiana {
  plan_kind: "training" | "nutrition";
  plan_id: string;
  plan_title: string;
  version_no: number;
  reason: string;
  created_at: string;
  ma_slad: boolean;
}

export interface WiedzaOdTrenera {
  id: string;
  title: string;
  category: string;
  czesc: string;
  body: string | null;
  external_url: string | null;
  file_id: string | null;
  pinned: boolean;
}

export interface WiedzaStart {
  wlaczone: boolean;
  szkice_widoczne?: boolean;
  personalizacja?: boolean;
  plan?: WiedzaPlanSkrot | null;
  dieta?: boolean;
  dla_ciebie?: (WiedzaKarta & { powod: string; punkty: number })[];
  ostatnie_zmiany?: WiedzaZmiana[];
  czesci?: { id: string; label: string; liczba: number }[];
  od_trenera?: WiedzaOdTrenera[];
  zakladki?: string[];
}

export interface WiedzaHistoriaWpis {
  trace_id: string;
  plan_revision: number;
  target_type: string;
  target_id: string;
  decision_origin: "engine" | "professional" | "user";
  rule_id: string | null;
  outcome_code: string;
  outcome_value: unknown;
  reason_note: string | null;
  created_at: string;
  version_created_at: string | null;
  version_reason: string | null;
  autor: string;
  aktualna: boolean;
}

export interface WiedzaWynikSzukania {
  id: string;
  revision: number;
  title: string;
  fragment: string;
  category: string;
  category_label: string | null;
  szkic: boolean;
  punkty: number;
}

export const WIEDZA_CZESCI: [string, string][] = [
  ["dla-ciebie", "Dla Ciebie"], ["training", "Trening"], ["nutrition", "Odżywianie"],
  ["progress", "Postępy i regeneracja"], ["basics", "Podstawy i źródła"],
];

export const WIEDZA_TYP_ELEMENTU: Record<string, string> = {
  training_frequency: "Liczba treningów",
  exercise_prescription: "Dawka ćwiczenia",
  plan_change: "Zmiana planu",
  energy_target: "Cel kaloryczny",
  macro_target: "Makroskładniki",
  load: "Ciężar",
  meal: "Posiłek",
};

// --- Kreator dań (0.57.0) ------------------------------------------------------

export type KulinariaStatus =
  | "draft_preview" | "ready_within_declared_bounds" | "needs_input" | "needs_review"
  | "nutrition_unverified" | "insufficient_catalog" | "search_exhausted" | "validation_failed";

export interface KulinariaZakup {
  food_id: string;
  name: string;
  state: string;
  edible_grams: number;
}

export interface KulinariaPosilek {
  slot: string;
  slot_label: string;
  recipe_id: string;
  recipe_revision: number;
  recipe_name: string;
  family_id: string;
  portion_variant: string;
  factor: number;
  ingredients: { food_id: string; grams: number; state: string; role: string }[];
  steps: string[];
  skladniki: string[];
  kroki: string[];
  draft: boolean;
  nutrition: Record<string, number> | null;
}

export interface KulinariaDzien {
  date: string;
  meals: KulinariaPosilek[];
  nutrition: Record<string, number> | null;
}

export interface KulinariaPlan {
  id: string;
  mode: "preview" | "production";
  days: KulinariaDzien[];
  limitations: string[];
  carb_compliance_verified: boolean;
  nutrition_scope: string[];
}

export interface KulinariaPokrycie {
  slots: Record<string, { recipes: number; families: number }>;
  rejected: Record<string, number>;
}

export interface KulinariaWynik {
  status: KulinariaStatus;
  issues: unknown[];
  plan: KulinariaPlan | null;
  engine_version: string;
  shopping_list?: KulinariaZakup[];
  coverage?: KulinariaPokrycie | null;
  config: Record<string, unknown> & { targets_reference?: string | null; daily_bounds?: Record<string, [number, number]> };
  meta: { screening_status: string; targets_source: { version_id: string; targets: Record<string, number> } | null };
  versions: Record<string, string>;
}

export interface KulinariaReceptura {
  id: string;
  revision: number;
  name: string;
  family_id: string;
  meal_slots: string[];
  cuisine: string;
  status: "draft" | "published" | "retired";
  total_minutes: number;
  active_minutes: number;
  review: { kitchen: boolean; dietitian: boolean; reviewer_id: string | null; expires_on: string | null };
  portion_variants: { id: string; factor: number; validated: boolean }[];
  ingredients: { food_id: string; grams: number; state: string; role: string }[];
}

export interface KulinariaRecepturaPelna extends KulinariaReceptura {
  steps: string[];
  equipment: string[];
  skladniki_opis: { skladniki: string[]; kroki: string[] };
  nutrition_base: Record<string, number> | null;
  nutrition_problem: string | null;
  source: string | null;
}

export interface KulinariaProfil {
  osie: Record<string, string[]>;
  alergeny: string[];
  sprzet: { id: string; label: string }[];
  rodziny: { id: string; name?: string }[];
  sloty: Record<string, string>;
  receptury: { razem: number; wg_statusu: Record<string, number> };
  produkty: { id: string; name: string; state: string; groups: string[]; nutrition_verified: boolean }[];
  mapowanie: { produkty: number; z_wartosciami: number; bez_wartosci: { id: string; name: string; powod: string | null }[];
    alergeny_zweryfikowane: number; status: string; carb_definition: string };
  versions: Record<string, string>;
  zakres_pola: string[];
}

export interface KulinariaZamianaPodglad {
  ok: boolean;
  problemy: string[];
  przed: { recipe_id: string; name: string; portion_variant: string };
  po: KulinariaPosilek;
  dzien: string;
  meal_index: number;
  nutrition_day: Record<string, number> | null;
}

// --- Panel trenera: szkice i publikacja zmian (0.58.0) ---------------------------

export type PlanKind = "training" | "nutrition";

export interface SzkicOperacja {
  op: "set" | "add" | "delete" | "move" | "duplicate" | "replace";
  id?: string;
  fields?: Record<string, unknown>;
  collection?: "days" | "exercises" | "sections" | "meals" | "supplements";
  parent_id?: string | null;
  item?: Record<string, unknown>;
  index?: number;
  content?: Record<string, unknown>;
}

export type SzkicCwiczenie = Omit<Exercise, "id"> & { id: string };
export type SzkicDzien = Omit<PlanDay, "id" | "exercises"> & { id: string; exercises: SzkicCwiczenie[] };

export interface SzkicTrening {
  title: string;
  days: SzkicDzien[];
}

export interface SzkicDieta {
  title: string;
  kcal?: number | null;
  protein_g?: number | null;
  fat_g?: number | null;
  carbs_g?: number | null;
  document_id?: string | null;
  sections: { id: string; title: string; body: string }[];
  meals: (NutritionMealRow & { id: string })[];
  supplements: (SupplementEntry & { id: string })[];
  kulinaria?: KulinariaMetaWersji;
}

export interface Szkic {
  id: string;
  plan_kind: PlanKind;
  plan_id: string;
  client_id: string | null;
  base_version_no: number;
  revision: number;
  status: "ACTIVE" | "PUBLISHED" | "DISCARDED";
  content: SzkicTrening | SzkicDieta;
  base_content: SzkicTrening | SzkicDieta;
  changes: number;
  summary: string;
  updated_at: string;
  updated_by: string;
}

export interface RoznicaPole { field: string; before: unknown; after: unknown }

export interface Roznice {
  added: { collection: string; parent_id: string | null; id: string; label: string; item: Record<string, unknown>; children: number }[];
  removed: { collection: string; parent_id: string | null; id: string; label: string; item: Record<string, unknown>; children: number }[];
  changed: { collection: string; id: string; label: string; label_before: string; fields: RoznicaPole[] }[];
  moved: { collection: string; id: string; label: string; from?: number; to?: number; from_parent?: string | null; to_parent?: string | null }[];
  root: RoznicaPole[];
  counts: { added: number; removed: number; changed: number; moved: number; root: number };
  summary: string;
  total: number;
  plan_id?: string;
  plan_title?: string;
  client_id?: string | null;
  base_version_no?: number;
  current_version_no?: number;
  stale_base?: boolean;
  effective?: string;
}

export interface WynikPublikacji {
  published: boolean;
  reason?: string;
  version_no: number;
  changeset_id?: string;
  summary: string;
  outbox_event_id?: string | null;
}

export interface ZestawZmian {
  id: string;
  plan_kind: PlanKind;
  plan_id: string;
  client_id: string | null;
  old_version_no: number;
  new_version_no: number;
  summary: string;
  note: string | null;
  author_id: string;
  published_at: string;
  notification: { id: string; created_at: string; read_at: string | null; channels: string | null } | null;
  diff?: Roznice;
  plan_title?: string;
  plan_url?: string;
  current_version_no?: number;
}

// --- Zakładka „Wywiad” (0.59.0) ---------------------------------------------

export type WywiadTyp = "wstepny" | "gleboki" | "zapotrzebowanie";
export type SubmissionStatus = "not_started" | "draft" | "submitted";
export type ReviewStatus = "not_reviewed" | "needs_clarification" | "reviewed";
export type FreshnessStatus = "current" | "update_requested";

export interface WywiadPostep {
  required_answered: number;
  required_total: number;
  percent: number;
  active_answered: number;
  active_total: number;
  ready: boolean;
  data_ready: boolean;
}

export interface WywiadPytanie {
  question_id: string;
  version: number;
  type: "TEXT" | "LONGTEXT" | "CHOICE" | "MULTI" | "SCALE" | "BOOL" | "INFO" | "NUMBER";
  label: string;
  why: string;
  section: string;
  options: string[];
  required: boolean;
  required_for: string[];
  active: boolean;
  visibility_rule: string;
  consent_domain: string | null;
  sensitive: boolean;
  access_class: string;
  fact_key: string | null;
  max_len: number;
  conditional: boolean;
  placeholder: string;
  info: boolean;
  /** NUMBER: [min, max]; pozostałe rodzaje: null. */
  range?: [number, number] | null;
}

export interface WywiadOdpowiedz {
  question_id: string;
  label: string;
  section: string;
  value: string | null;
  skipped: boolean;
  entered_by: string | null;
  at: string | null;
  hidden: boolean;
  active: boolean;
  fact_key: string | null;
  sensitive: boolean;
  to_discuss: boolean;
}

export interface WywiadFakt {
  value: string;
  source_type: string;
  question_id: string | null;
  author_id: string;
  created_at: string;
  version: number;
}

export interface WywiadDefinicja {
  typ: WywiadTyp;
  version: number;
  title: string;
  opis: string;
  sections: { key: string; label: string; opis: string }[];
  questions: WywiadPytanie[];
  progress: WywiadPostep;
  hidden_domains: string[];
  answers: WywiadOdpowiedz[];
  draft: { revision: number; updated_at: string; dirty: boolean; collection_mode: string; updated_by: string } | null;
  facts: Record<string, WywiadFakt>;
  has_coach: boolean;
}

export interface WywiadDoprecyzowanie {
  id: string;
  typ: WywiadTyp;
  submission_id: string | null;
  question_ids: string[];
  message: string;
  status: "OPEN" | "RESOLVED";
  created_at: string;
  resolved_at: string | null;
}

export interface WywiadPrzeglad {
  id?: string;
  outcome: "REVIEWED" | "NEEDS_CLARIFICATION";
  created_at: string;
  coach_id?: string;
  migrated: boolean;
  internal_note?: string | null;
}

export interface WywiadPrzeslanieMeta {
  id: string;
  version_no: number;
  definition_version: number;
  submitted_at: string;
  submitted_by: string;
  collection_mode: string;
  migrated: boolean;
  safety_flag: boolean;
  progress: Partial<WywiadPostep>;
  review: { outcome: "REVIEWED" | "NEEDS_CLARIFICATION"; created_at: string; migrated: boolean } | null;
}

export interface WywiadPrzeslanie extends WywiadPrzeslanieMeta {
  answers: WywiadOdpowiedz[];
  reviews: WywiadPrzeglad[];
  clarifications: WywiadDoprecyzowanie[];
}

export interface WywiadStan {
  typ: WywiadTyp;
  title: string;
  definition_version: number;
  submission_status: SubmissionStatus;
  review_status: ReviewStatus;
  freshness_status: FreshnessStatus;
  progress: WywiadPostep;
  draft: { revision: number; updated_at: string; updated_by: string; collection_mode: string; dirty: boolean } | null;
  last_submission: WywiadPrzeslanieMeta | null;
  submissions_count: number;
  open_clarifications: WywiadDoprecyzowanie[];
}

export interface ZadanieSprawdzenia {
  id: string;
  client_id: string;
  plan_kind: PlanKind;
  plan_id: string;
  submission_id: string;
  changed_facts: string[];
  status: "OPEN" | "RESOLVED";
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface WywiadyPrzeglad {
  client_id: string;
  access: { ok: boolean; reason: string | null; viewer: "client" | "coach"; has_coach: boolean;
    missing_domains: string[]; visible_domains: string[] };
  wywiady: WywiadStan[];
  review_tasks: ZadanieSprawdzenia[];
}

export interface WywiadZrodlo {
  question_id: string; label: string; version_no: number; typ: WywiadTyp; entered_by: string | null; at: string | null;
}

export interface WywiadPunkt { text: string; source: WywiadZrodlo }

export interface WywiadPodsumowanie {
  cele: WywiadPunkt[];
  ograniczenia: WywiadPunkt[];
  preferencje: WywiadPunkt[];
  do_wyjasnienia: WywiadPunkt[];
  do_aktualizacji: { text: string; question_ids: string[]; typ: WywiadTyp; created_at: string; clarification_id: string }[];
}

export interface WywiadPodpowiedzi {
  available: boolean;
  reason?: string;
  training: Record<string, unknown>;
  nutrition: { allergens: string[]; allergen_status: string | null; preferences: string[]; intolerances: string | null;
    exclusions: string | null; cooking: string | null; allergens_text?: string; goal_text?: string };
  sources: WywiadZrodlo[];
  warnings?: string[];
  interview_submission_ids: Partial<Record<WywiadTyp, string>>;
}

export interface WywiadDoPrzegladuWiersz {
  client_id: string;
  display_name: string;
  wywiady: Pick<WywiadStan, "typ" | "title" | "submission_status" | "review_status" | "freshness_status" | "progress" | "last_submission">[];
  open_review_tasks: number;
  needs_review: boolean;
  not_started: boolean;
}

// --- Szablony diet ze skalowaniem (0.60.0) ---------------------------------

export type DietStatus = "OK" | "OSTRZEŻENIE" | "POZA_ZAKRESEM" | "POZA_TOLERANCJĄ";
export interface DietMacros { kcal: number; P: number; F: number; C: number }

export interface DietWeekRow {
  id: string; variant_no: number; name: string; status: "DRAFT" | "PUBLISHED";
  base_kcal: number; kcal_min: number; kcal_max: number;
}
export interface DietProfileRow {
  id: string; name: string; description: string; base_macro_pct: { P: number; F: number; C: number };
  diet_tags: string[]; published_weeks: number; weeks: DietWeekRow[];
}
export interface DietTemplatePreview {
  week_id: string; profile: string; profile_id: string; variant_no: number; name: string; status: string;
  base_kcal: number; kcal_min: number; kcal_max: number; macro_pct: number[];
  days: { day: number; meals: { meal_id: string; name: string; slot: string; kcal_share: number; flexible: boolean; tags: string[]; ingredients: number }[] }[];
}
export interface DietIngredientOut {
  product: string; grams: number; base_grams: number; class: string; role: string; ingredient_id: string;
  swappable: boolean; min_factor: number; max_factor: number; factor: number | null; units?: number | null; unit_g?: number | null;
  round_step?: number | null; unit_step?: number | null;
  override?: { by?: string; at?: string; kind?: string };
}
export interface DietMealOut {
  meal_id: string; name: string; slot: string; status: DietStatus; macros: DietMacros; target: DietMacros;
  deviation: DietMacros; k: number; steps: string; tags: string[]; flexible: boolean; kcal_share: number;
  ingredients: DietIngredientOut[]; replaced_from?: string; swaps_locked?: boolean;
}
export interface DietDayOut { day: number; status: DietStatus; macros: DietMacros; target: DietMacros; deviation: DietMacros; meals: DietMealOut[] }
export interface DietPlanOut {
  week_id: string; target: DietMacros; kcal: number; days: DietDayOut[]; warnings: string[]; conflicts?: string[];
  summary: { days_ok: number; days: number; meals_flagged: number; meals: number };
  overrides?: { ingredients: Record<string, { product?: string; grams: number; by?: string; at?: string; kind?: string }>;
    meals: Record<string, { replaced_by_meal_id: string }>; accepted_warnings: boolean; accepted_days?: number[] };
}
export interface DietMacroIn { mode: "profile" | "per_kg" | "manual"; P?: number; F?: number; C?: number; protein_per_kg?: number; fat_per_kg?: number }
export interface DietAssignedOut {
  id: string; client_id: string; coach_id: string; week_id: string; week_name: string; profile: string;
  target: DietMacros; macro_mode: string; body_weight: number | null; exclusions: string[]; status: string;
  version: number; swaps_enabled: boolean; created_at: string; updated_at: string; plan: DietPlanOut;
}
export interface DietSwapCandidate { product: string; product_id: string; grams: number; macros: DietMacros }
export interface DietLibraryMeal { meal_id: string; name: string; slot: string; tags: string[]; week_id: string; variant_no: number; day_no: number; ingredients: string[] }
export interface DietProductRow {
  id: string; name_pl: string; category: string; substitution_group: string; kcal_100: number; protein_100: number;
  fat_100: number; carbs_100: number; default_scaling: string; cooking_tags: string; allergens: string; diet_exclusions: string; source: string;
}
export interface DietSweep {
  days: number; days_ok: number; ok_pct: number; error?: string | null; missing_days?: number[]; publishable: boolean;
  meals: { meal_id: string; day: number; name: string; slot: string; flags: number; out_of_range: number }[];
}
export interface DietWeekFull {
  week_id: string; profile: string; profile_id: string; variant: number; name: string; base_kcal: number; kcal_min: number;
  kcal_max: number; status: string; macro_pct: number[];
  days: { day: number; day_id: string; meals: { meal_id: string; name: string; slot: string; kcal_share: number; flexible: boolean;
    steps: string; tags: string[]; prep_minutes: number | null;
    ingredients: { product: string; grams: number; role: string; ingredient_id: string; swappable: boolean; class?: string;
      min_factor?: number; max_factor?: number; round_step?: number; unit_g?: number; unit_step?: number; group?: string }[] }[] }[];
}

// --- Zapotrzebowanie kaloryczne (0.62.0) --------------------------------------

export interface ZapotrzebowanieSzacunek {
  id: string;
  submission_id: string;
  version_no: number;
  created_at: string;
  inputs: { plec: string; wiek: number; wzrost_cm: number; masa_kg: number; praca: string; treningi: string;
    kroki: string | null; cel: string; tempo: string | null };
  ppm: number;
  pal: number;
  cpm: number;
  korekta_pct: number;
  kcal: number;
  kcal_effective: number;
  podstawienie: string[];
  ostrzezenia: string[];
  hidden_for_client: boolean;
  unhidden_by: string | null;
  unhidden_at: string | null;
  override: { kcal: number; by: string; at: string; reason: string } | null;
}

export interface ZapotrzebowanieOut {
  client_id: string;
  enabled: boolean;
  interview_typ: WywiadTyp;
  access: { ok: boolean; reason: string | null; viewer: "client" | "coach" };
  status: "none" | "ok" | "hidden" | "no_access";
  estimate: ZapotrzebowanieSzacunek | null;
  message?: string;
  version_no?: number;
  history?: { version_no: number; kcal: number; kcal_effective: number; override_kcal: number | null; created_at: string }[];
}


/* --- Postępy / Monitoring (0.66.0, spec docs/monitoring-tab) --- */
export interface PostepyRekord {
  id: string; exercise_key: string; exercise_name: string; record_type: string; value: number;
  secondary_value: number | null; achieved_on: string; previous_value: number | null; delta: number | null;
  equaled_on: string | null; superseded_at: string | null; estimated: boolean; days_since_previous?: number | null;
}
export interface PostepyCwiczenie {
  exercise_key: string; exercise_name: string; last_performed_on: string;
  max_weight: PostepyRekord | null; e1rm: PostepyRekord | null; set_volume: PostepyRekord | null; session_volume: PostepyRekord | null;
  e1rm_series: { date: string; value: number }[]; history?: PostepyRekord[];
}
export interface PostepyRekordy { recent: PostepyRekord[]; exercises: PostepyCwiczenie[]; archive: PostepyCwiczenie[]; e1rm_note: string }
export interface PostepyTrendWagi { kg_per_week: number | null; average: number | null; message: string | null; measurements: number }
export interface PostepySummary {
  week: { done: number; planned: number; days: { date: string; done: boolean }[]; message: string | null };
  streak: { weeks: number; longest: number; message: string | null };
  recent_records: number;
  diet: { days_logged: number; days: number; pct: number } | null;
  /** Brak pola = klient z flagą zdrowotną (kafelek znika, nie pokazuje pustego stanu). */
  weight?: PostepyTrendWagi;
}
export interface PostepyTydzien {
  week_start: string; sessions: number; planned: number; tonnage_kg: number; avg4_tonnage_kg?: number;
  sets_by_group: Record<string, number>; days: string[];
}
export interface PostepyTrening {
  weeks: PostepyTydzien[];
  sets_by_group: { current: Record<string, number>; previous: Record<string, number> };
  calendar: { from: string; to: string; session_days: string[] };
}
export interface PostepyPunkt { date: string; value: number }
export interface PostepyBody {
  weight: { average_points: PostepyPunkt[]; raw_points: PostepyPunkt[]; average: number | null; trend: PostepyTrendWagi; days: number; raw_visible_default?: boolean };
  circumferences: { kind: string; unit: string; points: { date: string; value: number; unit: string }[]; current: number; delta_from_first: number | null; first_date: string | null }[];
  photos: { id: string; file_id: string; taken_at: string; pose: string | null; note: string | null }[];
}
export interface PostepySygnal { key: string; level: "high" | "medium" | "info"; label: string }
export interface PostepyKlientSygnaly {
  client_id: string; display_name: string; email: string; last_activity: string | null;
  attendance_4w: { done: number; planned: number; pct: number | null }; weight_trend_kg_week: number | null;
  signals: PostepySygnal[]; priority: number; consents: { training: boolean; health: boolean };
}
export interface PostepyProgi {
  dni_bez_treningu: number; frekwencja_pct: number; dni_bez_wazenia: number; spadek_tonazu_pct: number;
  trend_wzrost_kg: number; dni_trendu: number; dni_rekordu: number;
}
export interface PostepyKlientTrenera {
  client_id: string; summary: PostepySummary; records: PostepyRekordy; training: PostepyTrening; health_flag: boolean;
  body?: PostepyBody; notes?: { date: string; text: string; category: string; severity: string }[];
  plan_changes: { date: string; version_no: number; reason: string }[];
}
export const GRUPA_LABELS: Record<string, string> = {
  NOGI: "Nogi", PLECY: "Plecy", KLATKA: "Klatka", BARKI: "Barki", RECE: "Ręce", BRZUCH: "Brzuch",
  CALE_CIALO: "Całe ciało", MOBILNOSC: "Mobilność", CARDIO: "Cardio", INNE: "Inne",
};
export const SYGNAL_LEVEL_LABELS: Record<PostepySygnal["level"], string> = { high: "wysoki", medium: "średni", info: "informacja" };

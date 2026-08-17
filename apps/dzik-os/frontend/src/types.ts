export interface Exercise {
  name: string;
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

export interface NutritionContent {
  kcal?: number | null;
  protein_g?: number | null;
  fat_g?: number | null;
  carbs_g?: number | null;
  sections: { title: string; body: string }[];
  meals: { name: string; description?: string; swaps?: string }[];
}

export interface NutritionVersion {
  id: string;
  version_no: number;
  reason: string;
  content: NutritionContent;
  document_id: string | null;
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

export interface CheckinData {
  id: string;
  week_start: string;
  payload: Record<string, unknown>;
  status: string;
  revision: number;
  submitted_at: string;
  coach_response: string | null;
  photo_ids: string[];
}

export interface MeasurementRow {
  id: string;
  kind: string;
  value: number;
  unit: string;
  measured_at: string;
  source: string;
}

export interface PaymentRecordRow {
  id: string;
  due_date: string;
  amount_cents: number;
  currency: string;
  status: string;
  paid_at: string | null;
  note: string | null;
  payment_link: string | null;
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
  purpose: string;
  domain: string;
  actions: string;
  allow_sensitive: boolean;
  granted_at: string;
  revoked_at: string | null;
  confirmed_at: string | null;
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
  read_at: string | null;
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
  flags: {
    checkin_overdue: boolean;
    payment_overdue: boolean;
    unread_messages: number;
    recent_pain_reports: number;
    flagged_observations: number;
  };
  last_checkin_week: string | null;
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
  entries: { exercise_index: number; exercise_name: string; result: string | null; comment: string | null; file_id: string | null }[];
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
  summary: string;
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
  PENDING: "Oczekuje",
  PAID: "Opłacona",
  OVERDUE: "Zaległa",
  CANCELLED: "Anulowana",
};

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

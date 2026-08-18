// Czysta logika ekranu rozmowy startowej — bez React i bez fetch,
// testowana w Node (scripts/test-onboarding-utils.mjs).
//
// Źródłem prawdy dla scenariusza, kolejności pytań, reguł adaptacji
// i objawów alarmowych jest BACKEND (dzik_os/onboarding_flow.py).
// Frontend tylko rysuje to, co dostał, i podpowiada — nigdy nie
// decyduje, o co zapytać ani czy coś wolno wysłać do modelu.

export type StepKind =
  | "TEXT"
  | "LONGTEXT"
  | "CHOICE"
  | "MULTI"
  | "SCALE"
  | "BOOL"
  | "INFO";

export interface OnboardingStep {
  id: string;
  topic: string;
  question: string;
  why: string;
  kind: StepKind;
  options: string[];
  placeholder: string;
  sensitive: boolean;
  max_len: number;
}

export interface OnboardingAnswerRow {
  step_id: string;
  topic: string;
  question: string;
  value: string;
  hidden: boolean;
  skipped: boolean;
  sensitive: boolean;
  safety_flagged: boolean;
  safety_signals: string[];
  version: number;
  is_current: boolean;
  created_at: string;
}

export interface OnboardingSummaryRow {
  field_key: string;
  value: string;
  hidden: boolean;
  step_id: string | null;
  origin: "DETERMINISTIC" | "AI_DRAFT" | "CLIENT_EDITED";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  needs_confirmation: boolean;
  coach_confirmed: boolean;
  sensitive: boolean;
  version: number;
}

export interface OnboardingSessionRow {
  id: string;
  status: "IN_PROGRESS" | "SUMMARY_READY" | "CLIENT_APPROVED" | "COACH_APPROVED"
    | "ABANDONED";
  summary_mode: "FORM" | "AI_DRAFT";
  summary_mode_reason: string | null;
  safety_flag: boolean;
  started_at: string;
  updated_at: string;
  summary_at: string | null;
  client_approved_at: string | null;
  coach_approved_at: string | null;
  summary_stale: boolean;
}

export interface OnboardingState {
  session: OnboardingSessionRow | null;
  step: OnboardingStep | null;
  current_answer: { step_id: string; value: string; skipped: boolean } | null;
  can_go_back?: boolean;
  finished?: boolean;
  progress: { answered: number; total: number; percent: number };
  planned_steps?: string[];
  answers?: OnboardingAnswerRow[];
  summary?: OnboardingSummaryRow[];
  ai: { available: boolean; reason: string; consent: boolean };
  safety_notice?: { message: string; signals: string[] } | null;
  needs_confirmation?: string[];
  can_approve?: boolean;
  applied_fields?: string[];
  skipped_fields?: string[];
}

/** Etykiety pól profilu w podsumowaniu (klucz techniczny -> po ludzku).
 * Nieznany klucz zostaje wyświetlony dosłownie — nigdy nie znika. */
export const FIELD_LABELS: Record<string, string> = {
  cel_glowny: "Główny cel",
  cel_termin: "Termin / wydarzenie",
  doswiadczenie: "Doświadczenie treningowe",
  wsparcie_techniki: "Wsparcie techniki",
  dostepnosc_tygodniowa: "Dostępność w tygodniu",
  dni_treningowe: "Preferowane dni",
  pora_treningu: "Preferowana pora",
  sprzet: "Sprzęt i miejsce",
  sprzet_domowy: "Sprzęt w domu / okolicy",
  ograniczenia_organizacyjne: "Ograniczenia organizacyjne",
  urazy_deklaracja: "Urazy — deklaracja",
  urazy: "Urazy i dolegliwości",
  ograniczenia_ruchu: "Czego unikać na treningu",
  bol_biezacy: "Ból teraz",
  bol_opis: "Opis bólu",
  sen_godziny: "Sen",
  poziom_stresu: "Poziom stresu",
  preferencje_zywieniowe: "Żywienie",
  alergie: "Alergie i nietolerancje",
  suplementacja_deklaracja: "Suplementy i leki (deklaracja)",
  preferencje_komunikacji: "Preferowany kontakt",
};

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

/** Opis poziomu pewności dla człowieka — nigdy surowa liczba. */
export const CONFIDENCE_LABELS: Record<string, string> = {
  HIGH: "wysoka pewność",
  MEDIUM: "do potwierdzenia",
  LOW: "niepewne",
};

export const ORIGIN_LABELS: Record<string, string> = {
  DETERMINISTIC: "z Twojej odpowiedzi",
  AI_DRAFT: "propozycja AI (do sprawdzenia)",
  CLIENT_EDITED: "poprawione przez Ciebie",
};

/** Szerokość paska postępu w procentach, zawsze 0..100. */
export function progressPercent(state: { progress?: { percent?: number } }): number {
  const raw = state.progress?.percent ?? 0;
  if (!Number.isFinite(raw)) return 0;
  return Math.max(0, Math.min(100, Math.round(raw)));
}

/** Komunikat postępu do aria-live (czytnik ekranu słyszy, gdzie jesteśmy). */
export function progressAnnouncement(state: OnboardingState): string {
  if (!state.session) return "Rozmowa nie została rozpoczęta.";
  if (!state.step) return "Rozmowa zakończona. Możesz przejrzeć podsumowanie.";
  const { answered, total } = state.progress;
  return `Pytanie ${Math.min(answered + 1, total)} z ${total}. ${state.step.topic}: ${
    state.step.question
  }`;
}

/** Czy odpowiedź w bieżącym kroku wolno wysłać (bez „pomiń"). */
export function canSubmit(step: OnboardingStep | null, value: string): boolean {
  if (!step) return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (trimmed.length > step.max_len) return false;
  if (step.kind === "MULTI") {
    return parseMulti(trimmed).length > 0;
  }
  if (step.options.length > 0) {
    return step.options.includes(trimmed);
  }
  return true;
}

/** Zaznaczenia w kroku wielokrotnego wyboru (przechowywane jako CSV). */
export function parseMulti(value: string): string[] {
  return value
    .split(",")
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

export function toggleMulti(value: string, option: string, options: string[]): string {
  const chosen = new Set(parseMulti(value));
  if (chosen.has(option)) chosen.delete(option);
  else chosen.add(option);
  // Kolejność listy, nie kolejność klikania (tak samo jak na serwerze).
  return options.filter((o) => chosen.has(o)).join(", ");
}

/** Ile znaków jeszcze zostało (podpowiedź pod polem tekstowym). */
export function charsLeft(step: OnboardingStep | null, value: string): number {
  if (!step) return 0;
  return step.max_len - value.length;
}

/** Bieżące (nieprzeterminowane) odpowiedzi w kolejności zadawania pytań. */
export function currentAnswers(rows: OnboardingAnswerRow[]): OnboardingAnswerRow[] {
  return rows.filter((r) => r.is_current);
}

/** Wcześniejsze wersje odpowiedzi na dany krok — historia poprawek
 * (klient zmienił zdanie; nic nie jest nadpisywane po cichu). */
export function answerHistory(
  rows: OnboardingAnswerRow[],
  stepId: string,
): OnboardingAnswerRow[] {
  return rows
    .filter((r) => r.step_id === stepId && !r.is_current)
    .sort((a, b) => b.version - a.version);
}

/** Pola, które trener musi potwierdzić z klientem przed zatwierdzeniem. */
export function pendingConfirmation(rows: OnboardingSummaryRow[]): OnboardingSummaryRow[] {
  return rows.filter((r) => r.needs_confirmation && !r.coach_confirmed);
}

/** Jednozdaniowy opis trybu podsumowania dla użytkownika.
 * Tryb formularza NIE jest awarią — dostaje neutralny opis z powodem. */
export function summaryModeNote(session: OnboardingSessionRow | null): string {
  if (!session) return "";
  if (session.summary_mode === "AI_DRAFT") {
    return "Podsumowanie przygotowane jako propozycja AI — sprawdź je i popraw, "
      + "zanim zatwierdzisz. Ostatnie słowo należy do Ciebie.";
  }
  const reason = session.summary_mode_reason?.trim();
  return reason
    ? `Podsumowanie przygotowane krok po kroku, wprost z Twoich odpowiedzi. ${reason}`
    : "Podsumowanie przygotowane krok po kroku, wprost z Twoich odpowiedzi.";
}

/** Czy klient może już zatwierdzić podsumowanie. */
export function canApproveSummary(state: OnboardingState): boolean {
  const session = state.session;
  if (!session) return false;
  if (session.status !== "SUMMARY_READY") return false;
  return (state.summary?.length ?? 0) > 0;
}

/** Scala lokalne poprawki klienta w podsumowaniu z wersją z serwera.
 * Zwraca wyłącznie pola FAKTYCZNIE zmienione (pusty wynik = brak PUT). */
export function changedSummaryItems(
  server: OnboardingSummaryRow[],
  edited: Record<string, string>,
): { field_key: string; value: string }[] {
  const out: { field_key: string; value: string }[] = [];
  for (const row of server) {
    if (row.hidden) continue;
    const next = edited[row.field_key];
    if (next === undefined) continue;
    if (next.trim() === row.value.trim()) continue;
    out.push({ field_key: row.field_key, value: next.trim() });
  }
  return out;
}

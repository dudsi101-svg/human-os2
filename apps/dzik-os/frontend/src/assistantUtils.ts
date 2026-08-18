// Czysta logika asystenta trenera (bez DOM — testowana w Node, patrz
// scripts/test-assistant-utils.mjs).
//
// Zasady, których pilnują te funkcje:
// * wynik asystenta to PROPOZYCJA — wstawienie do edytora nigdy nie kasuje
//   tego, co trener już napisał: dni są DOKŁADANE, a jedyny wyjątek to
//   pojedynczy pusty dzień startowy (nie ma czego chronić);
// * każde wstawienie da się COFNĄĆ — stąd migawka poprzedniego stanu
//   zamiast modyfikacji w miejscu;
// * asystent nie podaje kilogramów — pole `weight` zostaje puste, nawet
//   gdyby serwer coś w nim przysłał;
// * powtórne kliknięcie nie mnoży zadań — klucz idempotencji zależy od
//   TREŚCI formularza, a nowy szkic wymaga świadomego „generuj ponownie”.

import { Exercise, PlanDay } from "./types";

export type AssistantStatus = "PENDING" | "RUNNING" | "DONE" | "FAILED" | "CANCELLED";
export type AssistantEngine = "MODEL" | "LOCAL";

export interface AssistantProvenance {
  assisted: boolean;
  task_key: string;
  engine: AssistantEngine;
  engine_label: string;
  client_data_used: boolean;
  generated_at: string;
}

/** Pozycja propozycji — dokładnie kształt pozycji planu (bez ciężaru). */
export interface ProposalExercise {
  name: string;
  exercise_id: string;
  sets?: string | null;
  reps?: string | null;
  weight?: string | null;
  tempo?: string | null;
  rest?: string | null;
  comment?: string | null;
  video_url?: string | null;
}

export interface ProposalDay {
  name: string;
  weekday: number | null;
  rationale: string;
  exercises: ProposalExercise[];
}

export interface LocalMatch {
  id: string;
  name: string;
  equipment: string | null;
  level: string | null;
  muscles_primary: string[];
  tempo_hint: string | null;
  video_url: string | null;
}

export interface LocalSlot {
  pattern: string;
  pattern_label: string;
  matches: LocalMatch[];
}

export interface LocalDay {
  name: string;
  weekday: number | null;
  slots: LocalSlot[];
}

export interface LocalPath {
  hint: string;
  items_per_day: number;
  filters: { level: string; equipment: string[]; patterns: string[] };
  days: LocalDay[];
  templates: { id: string; title: string }[];
}

export interface AssistantResult {
  days?: ProposalDay[];
  local?: LocalPath;
  provenance?: AssistantProvenance;
  client_id?: string | null;
  client_data_used?: boolean;
  client_data_reason?: string;
  invalid_values?: string[];
}

export interface AssistantTask {
  id: string;
  task_key: string;
  status: AssistantStatus;
  client_id?: string | null;
  engine?: AssistantEngine | null;
  engine_label?: string | null;
  mode_reason?: string | null;
  result?: AssistantResult | null;
  error_code?: string | null;
  error?: string | null;
  approved_at?: string | null;
  created_at?: string;
}

export interface AssistantStatusInfo {
  task_key: string;
  title: string;
  description: string;
  mode: AssistantEngine;
  mode_reason: string;
  exercise_count: number;
  daily_limit: number;
  used_today: number;
  queue_depth: number;
  slow_after_s: number;
  timeout_s: number;
  client_data_used: boolean;
  client_data_reason: string;
}

export interface PlanDraftForm {
  days_per_week: number;
  equipment: string[];
  level: string;
  goal: string;
  session_minutes: number;
}

export const EMPTY_DRAFT_FORM: PlanDraftForm = {
  days_per_week: 3,
  equipment: [],
  level: "POCZATKUJACY",
  goal: "",
  session_minutes: 60,
};

/** Nazwa trybu dla człowieka — bez żargonu i bez nazw dostawców. */
export function engineLabel(engine: AssistantEngine | null | undefined): string {
  if (engine === "MODEL") return "asystent z modelem";
  if (engine === "LOCAL") return "asystent lokalny (bez modelu)";
  return "";
}

/** Komunikat stanu do aria-live: postęp, „trwa dłużej niż zwykle”, koniec.
 * Nigdy pusta kręciołka bez wyjaśnienia — po `slowAfterS` mówimy wprost. */
export function statusMessage(
  task: AssistantTask | null,
  elapsedS = 0,
  slowAfterS = 8
): string {
  if (!task) return "";
  const slow = elapsedS >= slowAfterS;
  switch (task.status) {
    case "PENDING":
      return slow
        ? "Zadanie czeka w kolejce dłużej niż zwykle. Możesz je anulować — edytor działa normalnie."
        : "Zadanie czeka w kolejce…";
    case "RUNNING":
      return slow
        ? "Przygotowuję szkic — trwa dłużej niż zwykle. Możesz pisać dalej albo anulować."
        : "Przygotowuję szkic…";
    case "DONE":
      return hasProposal(task)
        ? "Szkic gotowy. Sprawdź go obok planu i wstaw, jeśli pasuje — nic nie zostało zapisane."
        : "Gotowe: tryb lokalny. Poniżej podział tygodnia i ćwiczenia z Twojej bazy.";
    case "CANCELLED":
      return "Zadanie anulowane. Nic nie zostało zapisane.";
    case "FAILED":
      return task.error || "Nie udało się przygotować szkicu.";
    default:
      return "";
  }
}

export function isFinished(task: AssistantTask | null): boolean {
  return !!task && ["DONE", "FAILED", "CANCELLED"].includes(task.status);
}

export function hasProposal(task: AssistantTask | null): boolean {
  return !!task?.result?.days?.length;
}

export function hasLocalPath(task: AssistantTask | null): boolean {
  return !!task?.result?.local?.days?.length;
}

/** Czy wiersz edytora jest pusty (nic do stracenia przy podmianie). */
function emptyRow(ex: Exercise): boolean {
  return !ex.name?.trim() && !ex.sets && !ex.reps && !ex.weight;
}

/** Czy edytor stoi na jednym, nietkniętym dniu startowym. */
export function isUntouched(days: PlanDay[]): boolean {
  return (
    days.length === 1 &&
    !days[0].name.trim() &&
    days[0].exercises.every(emptyRow)
  );
}

/** Propozycja -> dni planu. Ciężar zostaje PUSTY (dobiera go trener),
 * nawet gdyby serwer coś w tym polu przysłał. */
export function proposalToPlanDays(result: AssistantResult | null | undefined): PlanDay[] {
  return (result?.days ?? []).map((day) => ({
    name: day.name,
    weekday: day.weekday ?? null,
    exercises: day.exercises.map((ex) => ({
      name: ex.name,
      exercise_id: ex.exercise_id,
      sets: ex.sets ?? "",
      reps: ex.reps ?? "",
      weight: "",
      tempo: ex.tempo ?? "",
      rest: ex.rest ?? "",
      comment: ex.comment ?? "",
      video_url: ex.video_url ?? "",
    })),
  }));
}

/** Dzień ścieżki lokalnej -> dzień planu: pierwsze dopasowanie z każdego
 * wzorca ruchu. Sloty bez dopasowania są POMIJANE — nigdy nie wstawiamy
 * pozycji „do wymyślenia”. */
export function localDayToPlanDay(day: LocalDay): PlanDay {
  return {
    name: day.name,
    weekday: day.weekday ?? null,
    exercises: day.slots
      .filter((slot) => slot.matches.length > 0)
      .map((slot) => ({
        name: slot.matches[0].name,
        exercise_id: slot.matches[0].id,
        sets: "",
        reps: "",
        weight: "",
        tempo: slot.matches[0].tempo_hint ?? "",
        rest: "",
        comment: "",
        video_url: slot.matches[0].video_url ?? "",
      })),
  };
}

/** Ćwiczenie z bazy -> pozycja planu (klik w wyniku ścieżki lokalnej). */
export function matchToExercise(match: LocalMatch): Exercise {
  return {
    name: match.name,
    exercise_id: match.id,
    sets: "",
    reps: "",
    weight: "",
    tempo: match.tempo_hint ?? "",
    rest: "",
    comment: "",
    video_url: match.video_url ?? "",
  };
}

/** Wstawienie dni: DOKŁADAMY, nigdy nie kasujemy pracy trenera. Jedyny
 * wyjątek to nietknięty dzień startowy — jego zachowanie nikomu nie służy. */
export function appendDays(existing: PlanDay[], incoming: PlanDay[]): PlanDay[] {
  if (!incoming.length) return existing;
  const base = isUntouched(existing) ? [] : existing;
  return [...base, ...incoming.map((d) => ({ ...d, exercises: [...d.exercises] }))];
}

/** Migawka do „cofnij wstawienie” — głęboka kopia, żeby późniejsza edycja
 * nie zmieniła tego, do czego wracamy. */
export function snapshot(days: PlanDay[]): PlanDay[] {
  return days.map((d) => ({ ...d, exercises: d.exercises.map((e) => ({ ...e })) }));
}

/** Krótki, deterministyczny odcisk treści (FNV-1a) — bez zależności. */
function fingerprint(value: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

/** Klucz idempotencji: ta sama treść formularza + to samo podejście =
 * ten sam klucz, więc podwójne kliknięcie NIE tworzy drugiego zadania.
 * Nowy szkic z tymi samymi warunkami wymaga świadomego „generuj ponownie”
 * (rosnące `generation`). */
export function idempotencyKey(
  form: PlanDraftForm,
  clientId: string | null,
  generation: number
): string {
  const canonical = JSON.stringify({
    d: form.days_per_week,
    e: [...form.equipment].sort(),
    l: form.level,
    g: form.goal.trim(),
    m: form.session_minutes,
    c: clientId ?? "",
    n: generation,
  });
  return `asy-${fingerprint(canonical)}-${generation}`;
}

/** Ciało żądania zadania „szkic planu”. */
export function draftRequest(
  form: PlanDraftForm,
  clientId: string | null,
  generation: number
): Record<string, unknown> {
  return {
    task_key: "PLAN_DRAFT",
    input: {
      days_per_week: form.days_per_week,
      equipment: form.equipment,
      level: form.level,
      goal: form.goal.trim(),
      session_minutes: form.session_minutes,
      client_id: clientId,
    },
    idempotency_key: idempotencyKey(form, clientId, generation),
  };
}

/** Czy formularz da się wysłać (cel jest jedynym polem tekstowym). */
export function formReady(form: PlanDraftForm): boolean {
  return form.goal.trim().length > 0;
}

// --- Szkic roboczy formularza (przeżywa utratę sieci, wzorzec z P11) ---

export function draftStorageKey(userId: string, clientId: string | null): string {
  return `dzik-assistant-draft:${userId}:${clientId ?? "szablon"}`;
}

export function saveFormDraft(key: string, form: PlanDraftForm): void {
  try {
    localStorage.setItem(key, JSON.stringify(form));
  } catch {
    /* Świadomie: pełny localStorage nie może wywrócić formularza. */
  }
}

export function loadFormDraft(key: string): PlanDraftForm | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return normalizeForm(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function clearFormDraft(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* Brak dostępu do localStorage nie zmienia wyniku. */
  }
}

/** Odtworzenie szkicu z nieznanego wejścia — wartości spoza zakresu
 * wracają do domyślnych zamiast psuć formularz. */
export function normalizeForm(raw: unknown): PlanDraftForm {
  const src = (raw ?? {}) as Partial<PlanDraftForm>;
  const days = Number(src.days_per_week);
  const minutes = Number(src.session_minutes);
  return {
    days_per_week: days >= 1 && days <= 7 ? Math.round(days) : EMPTY_DRAFT_FORM.days_per_week,
    equipment: Array.isArray(src.equipment)
      ? src.equipment.filter((e) => typeof e === "string" && e.trim()).slice(0, 12)
      : [],
    level: typeof src.level === "string" && src.level ? src.level : EMPTY_DRAFT_FORM.level,
    goal: typeof src.goal === "string" ? src.goal.slice(0, 300) : "",
    session_minutes:
      minutes >= 15 && minutes <= 180
        ? Math.round(minutes)
        : EMPTY_DRAFT_FORM.session_minutes,
  };
}

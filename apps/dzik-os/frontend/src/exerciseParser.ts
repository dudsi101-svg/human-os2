// Czysta logika panelu „Uzupełnij z opisu" (bez DOM — testowana w Node,
// patrz scripts/test-exercise-parser.mjs).
//
// Zasada nadrzędna jest ta sama co przy OCR: wynik czytania opisu to
// PROPOZYCJA. Te funkcje wyłącznie przygotowują wstępnie wypełniony
// formularz do poprawienia przez trenera — nigdy nie zgadują wartości i
// DOMYŚLNIE NIE NADPISUJĄ tego, co trener już wpisał. Pole, którego silnik
// nie odczytał, zostaje puste i jest wypisane wprost.

// Moduł jest ŚWIADOMIE bez importów: kompiluje się i uruchamia sam
// (scripts/tsconfig.exercise-parser.json), więc nazwę trybu do komunikatu
// podaje wołający — ten sam `modeLabel` co przy OCR, bez kopiowania go tutaj.

/** Klucze pól propozycji — dokładnie te same co w
 * `backend/dzik_os/exercise_parser.py::FIELD_ORDER`. */
export const PARSER_FIELDS = [
  "name", "muscles_primary", "muscles_secondary", "level", "pattern",
  "equipment", "steps", "mistakes", "cues", "safety", "easier", "harder",
  "tempo_hint", "breathing", "benefit",
] as const;

export type ParserField = (typeof PARSER_FIELDS)[number];

export interface ExerciseProposal {
  name: string | null;
  muscles_primary: string[];
  muscles_secondary: string[];
  level: string | null;
  pattern: string | null;
  equipment: string | null;
  steps: string[];
  mistakes: string[];
  cues: string[];
  safety: string | null;
  easier: string | null;
  harder: string | null;
  tempo_hint: string | null;
  breathing: string | null;
  benefit: string | null;
}

/** Odpowiedź `POST /api/coach/exercises/parse-description`. */
export interface ParseDescriptionResponse {
  engine: "LOCAL" | "EXTENDED";
  mode_reason: string;
  proposal: ExerciseProposal;
  unrecognized: string[];
  needs_confirmation: string[];
  field_labels: Record<string, string>;
}

/** Wartości edytora ćwiczenia (jedno źródło prawdy dla formularza i dla
 * scalania propozycji). */
export interface ExerciseFormValues {
  name: string;
  muscle_group: string;
  how_to: string;
  benefit: string;
  equipment: string;
  video_url: string;
  muscles_primary: string[];
  muscles_secondary: string[];
  level: string;
  pattern: string;
  steps: string[];
  mistakes: string[];
  cues: string[];
  safety: string;
  easier: string;
  harder: string;
  tempo_hint: string;
  breathing: string;
}

const TEXT_FIELDS = [
  "name", "level", "pattern", "equipment", "safety", "easier", "harder",
  "tempo_hint", "breathing", "benefit",
] as const;

const LIST_FIELDS = [
  "muscles_primary", "muscles_secondary", "steps", "mistakes", "cues",
] as const;

/** Czy pole formularza jest puste. Lista złożona z samych pustych wierszy
 * (edytor list trzyma jeden pusty wiersz „na start") też liczy się jako
 * puste — inaczej „wypełnij tylko puste" nigdy by nie zadziałało. */
export function isEmptyField(value: string | string[] | undefined): boolean {
  if (Array.isArray(value)) return value.every((v) => !v || !v.trim());
  return !value || !value.trim();
}

function proposedText(value: string | null | undefined): string {
  return (value ?? "").trim();
}

/** Które pola formularza REALNIE zmieni wstawienie propozycji.
 *
 * Służy podglądowi („co zostanie wstawione") — trener widzi listę, zanim
 * cokolwiek ruszy w formularzu. */
export function fieldsToInsert(
  form: ExerciseFormValues,
  proposal: ExerciseProposal | null | undefined,
  overwrite = false
): ParserField[] {
  if (!proposal) return [];
  const out: ParserField[] = [];
  for (const key of PARSER_FIELDS) {
    const proposed = proposal[key];
    const empty = Array.isArray(proposed)
      ? proposed.length === 0
      : !proposedText(proposed as string | null);
    if (empty) continue;
    // Każdy klucz propozycji ma pole o tej samej nazwie w formularzu
    // (`benefit` to „Co to daje (efekt)"), więc porównanie jest wprost.
    const current = form[key as keyof ExerciseFormValues] as string | string[] | undefined;
    if (overwrite || isEmptyField(current)) out.push(key);
  }
  return out;
}

/** Scalenie propozycji z formularzem.
 *
 * Domyślnie uzupełniamy WYŁĄCZNIE puste pola — praca trenera nigdy nie
 * znika przez kliknięcie „Wstaw do formularza". `overwrite` to świadoma,
 * osobna decyzja (osobny przełącznik w interfejsie). */
export function mergeProposalIntoForm(
  form: ExerciseFormValues,
  proposal: ExerciseProposal | null | undefined,
  overwrite = false
): ExerciseFormValues {
  if (!proposal) return form;
  const changing = new Set<string>(fieldsToInsert(form, proposal, overwrite));
  const next: ExerciseFormValues = { ...form };
  for (const key of TEXT_FIELDS) {
    if (!changing.has(key)) continue;
    (next as unknown as Record<string, string>)[key] = proposedText(proposal[key]);
  }
  for (const key of LIST_FIELDS) {
    if (!changing.has(key)) continue;
    (next as unknown as Record<string, string[]>)[key] = [...proposal[key]];
  }
  return next;
}

/** Etykiety pól do pokazania człowiekowi (bez kluczy technicznych). */
export function fieldLabels(
  keys: string[],
  labels: Record<string, string>
): string[] {
  return keys.map((key) => labels[key] ?? key);
}

/** Proweniencja wpisu do wysłania przy zapisie ćwiczenia.
 *
 * `null` znaczy „trener wypełnił tabelę sam" — wtedy nie wysyłamy nic i
 * zapis zostaje bez proweniencji (NULL w bazie = nie wiemy). */
export function provenanceFor(
  engine: "LOCAL" | "EXTENDED" | null | undefined
): { source_kind: string; source_engine: string } | null {
  if (engine === "LOCAL") return { source_kind: "TEXT_PARSED", source_engine: "LOCAL" };
  if (engine === "EXTENDED") {
    return { source_kind: "AI_ASSISTED", source_engine: "EXTENDED" };
  }
  return null;
}

/** Komunikat do `aria-live` po pojawieniu się propozycji — czytnik ekranu
 * ma usłyszeć, ile pól przybyło, czego nie odczytano i który tryb zadziałał. */
export function proposalMessage(
  result: ParseDescriptionResponse | null,
  form: ExerciseFormValues,
  modeText: string,
  overwrite = false
): string {
  if (!result) return "";
  const inserted = fieldsToInsert(form, result.proposal, overwrite).length;
  const missing = result.unrecognized.length;
  const confirm = result.needs_confirmation.length;
  const parts = [
    `Propozycja gotowa (${modeText}).`,
    inserted > 0
      ? `Do wstawienia: ${inserted} ${inserted === 1 ? "pole" : "pól"}.`
      : "Nie ma czego wstawić — wszystkie pola są już wypełnione.",
  ];
  if (missing > 0) parts.push(`Nie udało się odczytać: ${missing}.`);
  if (confirm > 0) parts.push(`Do potwierdzenia: ${confirm}.`);
  return parts.join(" ");
}

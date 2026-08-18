// Czysta logika „Przepisz ze zdjęcia" (bez DOM — testowana w Node, patrz
// scripts/test-ocr-utils.mjs).
//
// Zasada nadrzędna: wynik rozpoznania to PROPOZYCJA. Te funkcje wyłącznie
// przygotowują wstępnie wypełniony formularz do poprawienia przez człowieka
// — nigdy nie uzupełniają brakujących wartości i nie zgadują. Pole, którego
// silnik nie odczytał, zostaje puste.

/** Rodzaj zadania — ta sama lista co w backendzie (routers/ocr.py). */
export type OcrPurpose = "PRODUKT" | "PLAN" | "DOKUMENT";

export type OcrStatus = "PENDING" | "RUNNING" | "DONE" | "FAILED" | "CANCELLED";

export interface OcrProposal {
  name?: string | null;
  kcal_100g?: number | null;
  protein_100g?: number | null;
  fat_100g?: number | null;
  carbs_100g?: number | null;
  fiber_100g?: number | null;
  portion_g?: number | null;
}

export interface OcrTask {
  id: string;
  status: OcrStatus;
  purpose: OcrPurpose;
  file_id: string;
  document_id?: string | null;
  engine?: "LOCAL" | "EXTENDED" | null;
  mode_reason?: string | null;
  text?: string | null;
  proposal?: OcrProposal | null;
  error_code?: string | null;
  error?: string | null;
  chars?: number | null;
  approved_at?: string | null;
  result_ref?: string | null;
}

export interface OcrStatusInfo {
  engine_available: boolean;
  engine_reason: string;
  mode: "LOCAL" | "EXTENDED";
  mode_reason: string;
  queue_depth: number;
  max_input_mb: number;
  accepted_types: string[];
  timeout_s: number;
}

/** Komunikat stanu zadania do aria-live (czytnik ekranu słyszy zmianę). */
export function statusMessage(task: OcrTask | null, queueDepth = 0): string {
  if (!task) return "";
  switch (task.status) {
    case "PENDING":
      return queueDepth > 1
        ? `Zdjęcie czeka w kolejce (przed nim: ${queueDepth - 1}). Rozpoznajemy po jednym naraz.`
        : "Zdjęcie czeka w kolejce.";
    case "RUNNING":
      return "Przepisujemy tekst ze zdjęcia…";
    case "DONE":
      return `Tekst przepisany (${task.chars ?? 0} znaków). Sprawdź go i popraw przed zatwierdzeniem.`;
    case "FAILED":
      return task.error || "Nie udało się przepisać tekstu.";
    default:
      return "";
  }
}

/** Nazwa trybu do pokazania człowiekowi — bez żargonu i nazw dostawców. */
export function modeLabel(engine: string | null | undefined): string {
  if (engine === "EXTENDED") return "tryb rozszerzony";
  if (engine === "LOCAL") return "tryb lokalny";
  return "";
}

export interface ProductFormValues {
  name: string;
  category: string;
  kcal_100g: string;
  protein_100g: string;
  fat_100g: string;
  carbs_100g: string;
  fiber_100g: string;
  default_portion_g: string;
  unit_name: string;
  unit_grams: string;
  source: string;
  note: string;
}

const EMPTY_FORM: ProductFormValues = {
  name: "", category: "Inne", kcal_100g: "", protein_100g: "", fat_100g: "",
  carbs_100g: "", fiber_100g: "", default_portion_g: "", unit_name: "",
  unit_grams: "", source: "", note: "",
};

/** Zakresy dokładnie te same co przy imporcie CSV i w FoodProductIn —
 * wartość spoza zakresu NIE trafia do formularza (zostaje puste pole). */
const LIMITS: Record<string, number> = {
  kcal_100g: 900,
  protein_100g: 100,
  fat_100g: 100,
  carbs_100g: 100,
  fiber_100g: 100,
  portion_g: 5000,
};

function fieldValue(raw: number | null | undefined, key: string): string {
  if (raw === null || raw === undefined || Number.isNaN(raw)) return "";
  const max = LIMITS[key];
  if (raw < 0 || (max !== undefined && raw > max)) return "";
  return String(raw);
}

/** Wstępnie wypełniony formularz nowego produktu z propozycji OCR.
 *
 * Pola nierozpoznane zostają PUSTE — nigdy zgadywane ani zerowane
 * (0 kcal to konkretna informacja, brak odczytu to jej brak). */
export function productFormFromProposal(
  proposal: OcrProposal | null | undefined
): ProductFormValues {
  if (!proposal) return { ...EMPTY_FORM };
  return {
    ...EMPTY_FORM,
    name: (proposal.name ?? "").trim().slice(0, 300),
    kcal_100g: fieldValue(proposal.kcal_100g, "kcal_100g"),
    protein_100g: fieldValue(proposal.protein_100g, "protein_100g"),
    fat_100g: fieldValue(proposal.fat_100g, "fat_100g"),
    carbs_100g: fieldValue(proposal.carbs_100g, "carbs_100g"),
    fiber_100g: fieldValue(proposal.fiber_100g, "fiber_100g"),
    default_portion_g: fieldValue(proposal.portion_g, "portion_g"),
    source: "etykieta produktu (zdjęcie)",
  };
}

/** Których pól formularza NIE udało się odczytać — do pokazania wprost,
 * żeby brak nie wyglądał jak wartość. */
export function missingProductFields(form: ProductFormValues): string[] {
  const labels: Record<string, string> = {
    name: "nazwa",
    kcal_100g: "kcal",
    protein_100g: "białko",
    fat_100g: "tłuszcz",
    carbs_100g: "węglowodany",
  };
  return Object.entries(labels)
    .filter(([key]) => !form[key as keyof ProductFormValues])
    .map(([, label]) => label);
}

/** Czy formularz produktu ma komplet pól wymaganych przez API. */
export function productFormComplete(form: ProductFormValues): boolean {
  return missingProductFields(form).length === 0;
}

/** Rozpoznany tekst -> lista pozycji do ręcznej obróbki w edytorze planu.
 *
 * ŚWIADOMIE nie parsujemy serii, powtórzeń ani ciężarów — jedna linia to
 * jedna nazwa do poprawienia przez trenera. Puste linie i linie bez liter
 * (same śmieci OCR) są pomijane. */
export function linesToExerciseNames(text: string, limit = 30): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length >= 3 && /[a-zA-ZąćęłńóśżźĄĆĘŁŃÓŚŻŹ]{3}/.test(line))
    .slice(0, limit)
    .map((line) => line.slice(0, 300));
}

/** Wstawienie tekstu do pola edytora: dopisujemy na końcu, nigdy nie
 * nadpisujemy tego, co człowiek już napisał. */
export function appendText(existing: string, addition: string): string {
  const base = existing.trimEnd();
  const extra = addition.trim();
  if (!extra) return existing;
  return base ? `${base}\n${extra}` : extra;
}

/** Czy dokument pasuje do wyszukiwania — po tytule ORAZ po tekście
 * przepisanym ze skanu (po to on jest). */
export function documentMatches(
  doc: { title: string; ocr_text?: string | null },
  query: string
): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const haystack = `${doc.title}\n${doc.ocr_text ?? ""}`.toLowerCase();
  return haystack.includes(needle);
}

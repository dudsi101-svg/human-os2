import {
  BLOCK_KIND_LABELS,
  BLOCK_KINDS,
  BLOCK_VARIANT_LABELS,
  BlockKind,
  EXERCISE_LEVEL_LABELS,
  Exercise,
  ExerciseBlockRow,
} from "./types";

/**
 * Bloki jak szablony (0.76.0) — czyste funkcje wspólne dla edytora planu
 * (`PlanEditor`) i karty „Przypisz plan” (`ClientDetail`). Bez React, bez API:
 * testowane w `scripts/test-bloki.mjs`. Ta sama kolejność w dniu, którą
 * stosuje serwer (`cardio/bloki.py::wstaw_do_dnia`): rozgrzewka na początek,
 * aeroby po siłowych (przed rozciąganiem), rozciąganie na koniec.
 */

/** `kind` pozycji planu dla rodzaju bloku (kontrakt z `schemas.ExerciseIn`). */
export const KIND_POZYCJI: Record<BlockKind, NonNullable<Exercise["kind"]>> = {
  WARMUP: "warmup_block",
  CARDIO: "cardio",
  STRETCH: "stretch_block",
};

/** Rodzaj pozycji planu (jak `pozycje.rodzajPozycji`, bez importu React). */
function rodzaj(ex: Pick<Exercise, "kind">): string {
  return ex.kind && ex.kind !== "strength" ? ex.kind : "strength";
}

/** Pozycja planu z bloku: migawka treści + `block_id` (miękkie); CARDIO
 * dodatkowo kopia presetu `cardio`, żeby renderer cardio i dziennik działały. */
export function pozycjaZBloku(b: ExerciseBlockRow): Exercise {
  const poz: Exercise = {
    name: b.name,
    kind: KIND_POZYCJI[b.kind],
    block_id: b.id,
    block: { name: b.name, kind: b.kind, level: b.level, variant: b.variant ?? null, duration_min: b.duration_min, items: b.items },
    sets: "", reps: "", weight: "", rest: "",
  };
  if (b.kind === "CARDIO" && b.cardio) {
    poz.cardio = JSON.parse(JSON.stringify(b.cardio));
    poz.comment = b.cardio.prescription?.hr_bpm_range ? "" : "Prowadź według RPE i testu mowy.";
  }
  return poz;
}

/** Wstawienie pozycji do dnia zgodnie z kolejnością rodzaju (nie modyfikuje wejścia). */
export function wstawDoDnia(exercises: Exercise[], poz: Exercise): Exercise[] {
  const kind = rodzaj(poz);
  if (kind === "warmup_block") return [poz, ...exercises];
  if (kind === "cardio") {
    const ostatni = exercises[exercises.length - 1];
    if (ostatni && rodzaj(ostatni) === "stretch_block") return [...exercises.slice(0, -1), poz, ostatni];
  }
  return [...exercises, poz];
}

/** Etykieta bloku w wyborze: „poziom · wariant/cel · ≈min”. */
export function etykietaBloku(b: ExerciseBlockRow): string {
  return [
    b.level ? EXERCISE_LEVEL_LABELS[b.level] ?? b.level : null,
    b.kind === "CARDIO" ? (b.goal_label ?? b.goal ?? null) : (b.variant ? BLOCK_VARIANT_LABELS[b.variant] : null),
    b.duration_min ? `≈${b.duration_min} min` : null,
  ].filter(Boolean).join(" · ");
}

export interface WyborPrzypisania {
  /** Tytuł szablonu treningowego albo null = „bez szablonu — tylko bloki”. */
  szablon: string | null;
  bloki: Partial<Record<BlockKind, ExerciseBlockRow | null>>;
  /** Liczba dni (dla „tylko bloki”; dla szablonu — liczba dni szablonu, gdy znana). */
  dni: number | null;
}

/** Zdanie podsumowania przed wysłaniem: „Szablon X + rozgrzewka Y + cardio Z → 3 dni”. */
export function podsumowaniePrzypisania(w: WyborPrzypisania): string {
  const czesci: string[] = [w.szablon ? `Szablon „${w.szablon}”` : "Bez szablonu"];
  for (const k of BLOCK_KINDS) {
    const b = w.bloki[k];
    if (b) czesci.push(`${BLOCK_KIND_LABELS[k].toLowerCase()} „${b.name}”`);
  }
  const dni = w.dni ? ` → ${w.dni} ${w.dni === 1 ? "dzień" : "dni"}` : "";
  return czesci.join(" + ") + dni;
}

export interface BlocksApplied {
  added: { warmup: number; cardio: number; stretch: number };
  skipped_days: { day_index: number; day_name: string | null; kind: string }[];
}

/** Komunikat po sukcesie z `blocks_applied` („Dodano rozgrzewkę do 3 dni, cardio do 3 dni”). */
export function komunikatPoPrzypisaniu(r: BlocksApplied | null | undefined, dni: number): string {
  if (!r) return `Przypisano plan (${dni} ${dni === 1 ? "dzień" : "dni"}).`;
  const nazwy: Record<keyof BlocksApplied["added"], string> = { warmup: "rozgrzewkę", cardio: "cardio", stretch: "rozciąganie" };
  const dodane = (Object.keys(nazwy) as (keyof BlocksApplied["added"])[])
    .filter((k) => r.added[k] > 0)
    .map((k) => `${nazwy[k]} do ${r.added[k]} ${r.added[k] === 1 ? "dnia" : "dni"}`);
  let tekst = dodane.length ? `Dodano ${dodane.join(", ")}.` : "Nie dodano żadnego bloku.";
  if (r.skipped_days.length) {
    tekst += ` Pominięto ${r.skipped_days.length} ${r.skipped_days.length === 1 ? "pozycję" : "pozycje"} — dzień miał już blok tego rodzaju z szablonu.`;
  }
  return tekst;
}

/** Domyślne nazwy dni dla planu „tylko bloki”. */
export function domyslneDni(n: number): { name: string; weekday: number | null }[] {
  const liczba = Math.max(1, Math.min(7, Math.floor(n) || 1));
  return Array.from({ length: liczba }, (_, i) => ({ name: `Dzień ${i + 1}`, weekday: null }));
}

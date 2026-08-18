/** Import bazy danych trenera z pliku (CSV / XLSX) — logika raportu.
 *
 * Moduł jest czysty (bez React i bez `fetch`), żeby dało się go
 * przetestować w Node — tak samo jak `exerciseImport.ts` przy imporcie
 * gotowej biblioteki.
 *
 * Kształt raportu odpowiada `dzik_os/sheet_import.py::SheetReport`.
 * Rozdział na `errors` i `warnings` jest tu tak samo istotny jak po
 * stronie serwera: błąd znaczy „tego wiersza NIE ma w bazie”, ostrzeżenie
 * znaczy „jest, ale zerknij”. Zlanie ich w jedno ukryłoby, co realnie
 * wpadło do bazy. */

export interface SheetImportError {
  row: number;
  column: string;
  message: string;
}

export interface SheetImportReport {
  kind: "EXERCISES" | "TEMPLATES";
  dry_run: boolean;
  mode: string;
  source_ref: string;
  rows_read: number;
  created: number;
  updated: number;
  unchanged: number;
  skipped: number;
  linked: number;
  errors: SheetImportError[];
  warnings: string[];
  unknown_columns: string[];
  unmapped_muscles: string[];
  unlinked_exercises: string[];
  created_names: string[];
  updated_names: string[];
  /** Punkt przywracania utworzony przez ten import. `null` znaczy „nie ma
   * czego cofać" — podgląd albo import, który niczego nie zmienił. */
  snapshot_id: string | null;
}

export interface ImportSnapshotRow {
  id: string;
  kind: "EXERCISES" | "TEMPLATES";
  source_ref: string;
  mode: string;
  rows: number;
  created_at: string;
  restored_at: string | null;
}

export interface SheetColumn {
  key: string;
  label: string;
  required: boolean;
  example: string;
  aliases: string[];
}

export interface SheetSchema {
  columns: SheetColumn[];
  dictionaries?: Record<string, { key: string; label: string }[]>;
  modes?: string[];
  list_separator?: string;
  muscle_separator?: string;
  max_rows: number;
  max_bytes: number;
  formats: string[];
}

/** Odmiana rzeczownika po liczbie — inaczej raport pisze „2 pozycji”. */
export function plural(n: number, one: string, few: string, many: string): string {
  if (n === 1) return one;
  const last = n % 10;
  const lastTwo = n % 100;
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return few;
  return many;
}

const NOUNS: Record<string, [string, string, string]> = {
  EXERCISES: ["pozycja", "pozycje", "pozycji"],
  TEMPLATES: ["szablon", "szablony", "szablonów"],
};

/** Jedno zdanie podsumowania. Podgląd i zapis mówią o sobie WPROST —
 * trener nie może się zastanawiać, czy coś już jest w bazie. */
export function importSummary(report: SheetImportReport): string {
  const [one, few, many] = NOUNS[report.kind] ?? NOUNS.EXERCISES;
  const noun = (n: number) => `${n} ${plural(n, one, few, many)}`;
  const parts = [
    `${noun(report.created)} do dodania`,
    `${noun(report.updated)} do zmiany`,
    `${noun(report.unchanged)} bez zmian`,
  ];
  const saved = [
    `dodano ${noun(report.created)}`,
    `zmieniono ${noun(report.updated)}`,
    `${noun(report.unchanged)} bez zmian`,
  ];
  const tail = report.skipped > 0
    ? `, pominięto ${report.skipped} ${plural(report.skipped, "wiersz", "wiersze", "wierszy")}`
    : "";
  return report.dry_run
    ? `Podgląd (nic jeszcze nie zapisano): ${parts.join(", ")}${tail}.`
    : `Zapisano: ${saved.join(", ")}${tail}.`;
}

/** Czy jest cokolwiek do zapisania. Przycisk „Zaimportuj” ma się nie
 * pojawiać, gdy zapis i tak nic by nie zmienił. */
export function hasChanges(report: SheetImportReport): boolean {
  return report.created > 0 || report.updated > 0;
}

/** Co zrobić, gdy raport jest pusty — konkretna podpowiedź zamiast
 * samego „brak zmian”. */
export function noChangesHint(report: SheetImportReport): string {
  if (report.skipped > 0 && report.unchanged === 0) {
    return "Żaden wiersz nie przeszedł kontroli — popraw błędy wypisane niżej i wgraj plik jeszcze raz.";
  }
  if (report.mode === "UZUPELNIJ" && report.unchanged > 0) {
    return "Wszystko z pliku już jest w bazie. Jeśli plik ma nowsze treści, wgraj go w trybie „Zastąp” — nadpisze wypełnione pola.";
  }
  return "Plik nie wnosi zmian do bazy.";
}

/** Lista wartości do jednego wiersza raportu, z ucięciem ogona. */
export function sampleLine(values: string[], limit = 8): string {
  const shown = values.slice(0, limit).join(", ");
  const rest = values.length - limit;
  return rest > 0 ? `${shown} (i jeszcze ${rest})` : shown;
}

/** Podpowiedź o kolumnach, których nie znamy — z nazwami, żeby trener
 * zobaczył literówkę w nagłówku, a nie tylko „coś jest nie tak”. */
export function unknownColumnsHint(report: SheetImportReport): string | null {
  if (report.unknown_columns.length === 0) return null;
  return `Pominięto nieznane kolumny: ${sampleLine(report.unknown_columns)}. `
    + "Sprawdź pisownię nagłówka albo usuń te kolumny — ich zawartość nie trafia do bazy.";
}

/** Ile pozycji szablonu udało się powiązać z bazą ćwiczeń. Brak
 * powiązania NIE jest błędem — pozycja wchodzi z samą nazwą. */
export function linkHint(report: SheetImportReport): string | null {
  if (report.kind !== "TEMPLATES") return null;
  if (report.unlinked_exercises.length === 0) {
    return report.linked > 0
      ? `Wszystkie pozycje (${report.linked}) zostały powiązane z Twoją bazą ćwiczeń.`
      : null;
  }
  return `Powiązano z bazą: ${report.linked}. Bez odpowiednika w bazie: `
    + `${sampleLine(report.unlinked_exercises)} — te pozycje wejdą do szablonu `
    + "z samą nazwą (bez karty ćwiczenia). Możesz je dodać do bazy później.";
}

/** Czy plik w ogóle nadaje się do wysłania — sprawdzane PRZED wysyłką,
 * żeby trener nie czekał na odpowiedź serwera dla pliku .pdf. */
export function fileProblem(
  file: { name: string; size: number },
  schema: Pick<SheetSchema, "formats" | "max_bytes">
): string | null {
  const name = file.name.toLowerCase();
  if (!schema.formats.some((suffix) => name.endsWith(suffix))) {
    return `Obsługiwane formaty to ${schema.formats.join(" i ")}. Wybrany plik: ${file.name}.`;
  }
  if (file.size > schema.max_bytes) {
    const mb = Math.round(schema.max_bytes / (1024 * 1024));
    return `Plik jest większy niż ${mb} MB — podziel bazę na części.`;
  }
  if (file.size === 0) return "Plik jest pusty.";
  return null;
}


/** Czy po tym imporcie da się jeszcze cofnąć zmiany. Podgląd i import bez
 * zmian nie tworzą punktu przywracania — przycisk „cofnij" nie ma się
 * wtedy pojawiać, bo obiecywałby coś, czego nie ma. */
export function canUndo(report: SheetImportReport): boolean {
  return !report.dry_run && report.snapshot_id !== null;
}

/** Co dokładnie zrobi cofnięcie — powiedziane wprost PRZED kliknięciem.
 * „Cofnij" bez wyjaśnienia brzmi jak kasowanie, a nim nie jest. */
export function undoExplanation(report: SheetImportReport): string {
  const parts: string[] = [];
  if (report.updated > 0) {
    parts.push(
      report.kind === "TEMPLATES"
        ? `${report.updated} ${plural(report.updated, "szablon wróci", "szablony wrócą", "szablonów wróci")} do treści sprzed importu (jako nowa wersja — historia zostaje)`
        : `${report.updated} ${plural(report.updated, "pozycja wróci", "pozycje wrócą", "pozycji wróci")} do wartości sprzed importu`
    );
  }
  if (report.created > 0) {
    parts.push(
      `${report.created} ${plural(report.created, "nowa pozycja zostanie zarchiwizowana", "nowe pozycje zostaną zarchiwizowane", "nowych pozycji zostanie zarchiwizowanych")} (nie usunięta — możesz je przywrócić ręcznie)`
    );
  }
  if (parts.length === 0) return "Nie ma czego cofać.";
  return `Cofnięcie: ${parts.join("; ")}. Można je wykonać tylko raz.`;
}

/** Etykieta wpisu w historii importów. */
export function snapshotLabel(row: ImportSnapshotRow): string {
  const what = row.kind === "TEMPLATES" ? "szablony" : "ćwiczenia";
  const mode = row.kind === "EXERCISES" && row.mode === "ZASTAP" ? ", tryb: zastąp" : "";
  return `${what} z pliku „${row.source_ref}" — ${row.rows} ${plural(row.rows, "pozycja", "pozycje", "pozycji")}${mode}`;
}

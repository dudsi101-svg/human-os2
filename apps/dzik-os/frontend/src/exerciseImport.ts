/** Import gotowej biblioteki ćwiczeń — kształt raportu i czysta logika
 * jego opisu po polsku.
 *
 * Widok pokazuje trenerowi RAPORT PRZED ZAPISEM (`dry_run`), a dopiero
 * jego kliknięcie uruchamia import. Ten moduł nie wysyła zapytań i niczego
 * nie zapisuje — zamienia liczby z API na zdania, żeby te same reguły
 * dało się przetestować bez przeglądarki (`npm run test:helpers`).
 *
 * ZASADA: to, czego nie udało się zmapować, ma być widoczne. Listy
 * `unmapped_muscles` i `unmapped_patterns` nigdy nie są chowane „bo i tak
 * nikt nie przeczyta” — pole zostało w bazie puste i trener musi o tym
 * wiedzieć. */

/** Jedna nierozpoznana wartość ze źródła (nazwa mięśnia albo wzorca). */
export interface UnmappedValue {
  value: string;
  count: number;
  examples: string[];
}

export interface ExerciseImportError {
  exercise: string;
  field: string;
  message: string;
}

/** Raport z `/api/coach/exercises/import-library` (ta sama postać dla
 * próby i dla zapisu). */
export interface ExerciseImportReport {
  created: number;
  enriched: number;
  skipped: number;
  unmapped_muscles: UnmappedValue[];
  unmapped_patterns: UnmappedValue[];
  errors: ExerciseImportError[];
  created_names: string[];
  enriched_names: string[];
  dry_run: boolean;
  library: string;
  total_rows: number;
}

/** Czy import w ogóle coś zmieni (jeśli nie — przycisk zapisu nie ma sensu). */
export function hasChanges(report: ExerciseImportReport): boolean {
  return report.created > 0 || report.enriched > 0;
}

function pluralize(n: number, one: string, few: string, many: string): string {
  if (n === 1) return one;
  const rest = n % 10;
  const teens = n % 100;
  if (rest >= 2 && rest <= 4 && (teens < 12 || teens > 14)) return few;
  return many;
}

/** Zdanie podsumowujące raport — w trybie próby mówi wprost, że nic
 * jeszcze nie zostało zapisane. */
export function importSummary(report: ExerciseImportReport): string {
  const created = `${report.created} ${pluralize(
    report.created, "nowa pozycja", "nowe pozycje", "nowych pozycji"
  )}`;
  const enriched = `${report.enriched} ${pluralize(
    report.enriched, "uzupełniona", "uzupełnione", "uzupełnionych"
  )}`;
  const skipped = `${report.skipped} bez zmian`;
  const head = report.dry_run
    ? "Podgląd (nic jeszcze nie zapisano):"
    : "Zapisano:";
  return `${head} ${created}, ${enriched}, ${skipped} — na ${report.total_rows} `
    + "pozycji w bibliotece.";
}

/** Krótki opis, co zostanie pominięte, gdy raport nic nie zmienia. */
export function noChangesHint(report: ExerciseImportReport): string {
  return `Wszystkie ${report.total_rows} pozycji biblioteki są już w Twojej `
    + "bazie i mają komplet pól, które import umie uzupełnić. "
    + "Powtórzenie importu niczego nie zmieni.";
}

/** Lista nierozpoznanych wartości w jednej linii („nazwa (x3)”). */
export function unmappedLine(entries: UnmappedValue[], limit = 8): string {
  const head = entries.slice(0, limit)
    .map((e) => `${e.value} (x${e.count})`)
    .join(", ");
  const rest = entries.length - Math.min(limit, entries.length);
  return rest > 0 ? `${head} i ${rest} więcej` : head;
}

// Testy czystej logiki raportu importu bazy z pliku (src/sheetImport.ts)
// w Node — bez przeglądarki. Uruchomienie: npm run test:helpers.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.sheet-import.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "sheet-import-test");

const {
  fileProblem, hasChanges, importSummary, linkHint, noChangesHint,
  plural, sampleLine, unknownColumnsHint,
} = await import(pathToFileURL(join(outDir, "sheetImport.js")).href);

const base = {
  kind: "EXERCISES", dry_run: true, mode: "UZUPELNIJ", source_ref: "baza.csv",
  rows_read: 0, created: 0, updated: 0, unchanged: 0, skipped: 0, linked: 0,
  errors: [], warnings: [], unknown_columns: [], unmapped_muscles: [],
  unlinked_exercises: [], created_names: [], updated_names: [],
};

test("odmiana rzeczownika idzie za liczbą", () => {
  assert.equal(plural(1, "pozycja", "pozycje", "pozycji"), "pozycja");
  assert.equal(plural(3, "pozycja", "pozycje", "pozycji"), "pozycje");
  assert.equal(plural(5, "pozycja", "pozycje", "pozycji"), "pozycji");
  assert.equal(plural(12, "pozycja", "pozycje", "pozycji"), "pozycji");
  assert.equal(plural(22, "pozycja", "pozycje", "pozycji"), "pozycje");
});

test("podgląd mówi wprost, że nic nie zostało zapisane", () => {
  const text = importSummary({ ...base, created: 12, updated: 3, unchanged: 5 });
  assert.ok(text.startsWith("Podgląd (nic jeszcze nie zapisano):"));
  assert.ok(text.includes("12 pozycji do dodania"));
  assert.ok(text.includes("3 pozycje do zmiany"));
});

test("zapis jest opisany innym czasownikiem niż podgląd", () => {
  const text = importSummary({ ...base, dry_run: false, created: 1, unchanged: 2 });
  assert.ok(text.startsWith("Zapisano: dodano 1 pozycja"));
  assert.ok(!text.includes("do dodania"));
});

test("pominięte wiersze są policzone w podsumowaniu", () => {
  assert.ok(importSummary({ ...base, created: 1, skipped: 4 })
    .includes("pominięto 4 wiersze"));
  assert.ok(!importSummary({ ...base, created: 1 }).includes("pominięto"));
});

test("szablony liczą się w szablonach, nie w pozycjach", () => {
  const text = importSummary({ ...base, kind: "TEMPLATES", created: 2 });
  assert.ok(text.includes("2 szablony do dodania"));
});

test("przycisk zapisu pojawia się tylko, gdy jest co zapisać", () => {
  assert.equal(hasChanges({ ...base, unchanged: 10 }), false);
  assert.equal(hasChanges({ ...base, created: 1 }), true);
  assert.equal(hasChanges({ ...base, updated: 1 }), true);
});

test("pusty raport podpowiada konkretny następny krok", () => {
  assert.ok(noChangesHint({ ...base, skipped: 3 }).includes("popraw błędy"));
  assert.ok(noChangesHint({ ...base, unchanged: 4 }).includes("Zastąp"));
  assert.equal(noChangesHint({ ...base, mode: "ZASTAP" }), "Plik nie wnosi zmian do bazy.");
});

test("długie listy są ucinane z informacją, ile zostało", () => {
  assert.equal(sampleLine(["a", "b"], 8), "a, b");
  assert.equal(sampleLine(["a", "b", "c"], 2), "a, b (i jeszcze 1)");
});

test("nieznane kolumny są nazwane po imieniu", () => {
  assert.equal(unknownColumnsHint(base), null);
  const hint = unknownColumnsHint({ ...base, unknown_columns: ["cena", "uwagi wewnętrzne"] });
  assert.ok(hint.includes("cena"));
  assert.ok(hint.includes("nie trafia do bazy"));
});

test("brak powiązania pozycji szablonu z bazą nie jest błędem", () => {
  assert.equal(linkHint({ ...base, linked: 3 }), null, "dla ćwiczeń podpowiedzi nie ma");
  const all = linkHint({ ...base, kind: "TEMPLATES", linked: 4 });
  assert.ok(all.includes("Wszystkie pozycje (4)"));
  const some = linkHint({
    ...base, kind: "TEMPLATES", linked: 2, unlinked_exercises: ["Wykrok bułgarski"],
  });
  assert.ok(some.includes("Wykrok bułgarski"));
  assert.ok(some.includes("z samą nazwą"));
});

test("zły plik jest odrzucany przed wysyłką", () => {
  const schema = { formats: [".csv", ".xlsx"], max_bytes: 1024 };
  assert.ok(fileProblem({ name: "baza.pdf", size: 10 }, schema).includes(".csv"));
  assert.ok(fileProblem({ name: "baza.csv", size: 5000 }, schema).includes("MB"));
  assert.equal(fileProblem({ name: "baza.csv", size: 0 }, schema), "Plik jest pusty.");
  assert.equal(fileProblem({ name: "BAZA.XLSX", size: 10 }, schema), null);
});

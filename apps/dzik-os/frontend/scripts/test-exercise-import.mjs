// Testy czystej logiki raportu importu biblioteki ćwiczeń
// (src/exerciseImport.ts) w Node — bez przeglądarki.
// Uruchomienie: npm run test:helpers.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.exercise-import.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "exercise-import-test");

const { hasChanges, importSummary, noChangesHint, unmappedLine } = await import(
  pathToFileURL(join(outDir, "exerciseImport.js")).href
);

const base = {
  created: 0, enriched: 0, skipped: 0,
  unmapped_muscles: [], unmapped_patterns: [], errors: [],
  created_names: [], enriched_names: [],
  dry_run: true, library: "Biblioteka ćwiczeń trenera V2 (2026-08-18)",
  total_rows: 120,
};

test("podgląd mówi wprost, że nic nie zostało zapisane", () => {
  const text = importSummary({ ...base, created: 101, skipped: 19 });
  assert.ok(text.startsWith("Podgląd (nic jeszcze nie zapisano):"));
  assert.ok(text.includes("101 nowych pozycji"));
  assert.ok(text.includes("19 bez zmian"));
});

test("zapis jest opisany inaczej niż podgląd", () => {
  const text = importSummary({ ...base, dry_run: false, created: 101, skipped: 19 });
  assert.ok(text.startsWith("Zapisano:"));
});

test("liczebniki po polsku (1 / 2-4 / 5+ / nastki)", () => {
  assert.ok(importSummary({ ...base, created: 1 }).includes("1 nowa pozycja"));
  assert.ok(importSummary({ ...base, created: 3 }).includes("3 nowe pozycje"));
  assert.ok(importSummary({ ...base, created: 5 }).includes("5 nowych pozycji"));
  assert.ok(importSummary({ ...base, created: 12 }).includes("12 nowych pozycji"));
  assert.ok(importSummary({ ...base, created: 22 }).includes("22 nowe pozycje"));
  assert.ok(importSummary({ ...base, enriched: 2 }).includes("2 uzupełnione"));
  assert.ok(importSummary({ ...base, enriched: 1 }).includes("1 uzupełniona"));
});

test("raport bez zmian nie zachęca do zapisu", () => {
  assert.equal(hasChanges({ ...base, skipped: 120 }), false);
  assert.equal(hasChanges({ ...base, created: 1 }), true);
  assert.equal(hasChanges({ ...base, enriched: 1 }), true);
  assert.ok(noChangesHint({ ...base }).includes("120"));
});

test("nierozpoznane wartości są wypisane z liczbą wystąpień", () => {
  const line = unmappedLine([
    { value: "mięsień ramienny", count: 14, examples: ["Uginanie"] },
    { value: "obły większy", count: 9, examples: ["Podciąganie"] },
  ]);
  assert.equal(line, "mięsień ramienny (x14), obły większy (x9)");
});

test("długa lista jest ucinana, ale reszta jest policzona — nic nie znika", () => {
  const many = Array.from({ length: 12 }, (_, i) => ({
    value: `wartość ${i}`, count: 1, examples: [],
  }));
  const line = unmappedLine(many, 3);
  assert.ok(line.includes("wartość 0 (x1)"));
  assert.ok(line.endsWith("i 9 więcej"));
});

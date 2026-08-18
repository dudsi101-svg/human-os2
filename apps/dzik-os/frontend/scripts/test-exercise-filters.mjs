// Testy czystej logiki filtrów bazy ćwiczeń (src/exerciseFilters.ts)
// w Node — bez przeglądarki. Uruchomienie: npm run test:helpers.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.exercise-filters.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "exercise-filters-test");

const { EMPTY_FILTERS, exerciseQuery, hasActiveFilters } = await import(
  pathToFileURL(join(outDir, "exerciseFilters.js")).href
);

test("puste filtry dają wyłącznie limit", () => {
  assert.equal(exerciseQuery(EMPTY_FILTERS, 0, 30), "limit=30");
});

test("offset trafia do zapytania dopiero gdy jest niezerowy", () => {
  assert.equal(exerciseQuery(EMPTY_FILTERS, 0, 20), "limit=20");
  assert.ok(exerciseQuery(EMPTY_FILTERS, 20, 20).includes("offset=20"));
});

test("puste i białe filtry są pomijane", () => {
  const query = exerciseQuery({ ...EMPTY_FILTERS, q: "   ", muscle: "" }, 0, 10);
  assert.equal(query, "limit=10");
});

test("polskie znaki i spacje są kodowane w URL", () => {
  const query = exerciseQuery({ ...EMPTY_FILTERS, q: "wiosłowanie sztangą" }, 0, 10);
  assert.ok(query.startsWith("q="));
  assert.equal(new URLSearchParams(query).get("q"), "wiosłowanie sztangą");
});

test("komplet filtrów trafia do zapytania", () => {
  const params = new URLSearchParams(exerciseQuery({
    q: "przysiad", muscle: "POSLADKI", equipment: "Sztanga",
    level: "ZAAWANSOWANY", pattern: "PRZYSIAD",
  }, 40, 25));
  assert.equal(params.get("q"), "przysiad");
  assert.equal(params.get("muscle"), "POSLADKI");
  assert.equal(params.get("equipment"), "Sztanga");
  assert.equal(params.get("level"), "ZAAWANSOWANY");
  assert.equal(params.get("pattern"), "PRZYSIAD");
  assert.equal(params.get("limit"), "25");
  assert.equal(params.get("offset"), "40");
});

test("parametry dodatkowe (np. status) dokładają się bez nadpisywania filtrów", () => {
  const params = new URLSearchParams(
    exerciseQuery({ ...EMPTY_FILTERS, q: "deska" }, 0, 10, { status: "ARCHIVED" }),
  );
  assert.equal(params.get("status"), "ARCHIVED");
  assert.equal(params.get("q"), "deska");
});

test("hasActiveFilters rozpoznaje aktywny filtr", () => {
  assert.equal(hasActiveFilters(EMPTY_FILTERS), false);
  assert.equal(hasActiveFilters({ ...EMPTY_FILTERS, level: "POCZATKUJACY" }), true);
  assert.equal(hasActiveFilters({ ...EMPTY_FILTERS, q: "  " }), false);
});

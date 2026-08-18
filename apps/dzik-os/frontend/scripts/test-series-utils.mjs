// Testy czystej logiki serii wykresów (src/seriesUtils.ts) w Node —
// bez przeglądarki i bez dodatkowych zależności. Uruchomienie:
//     npm run test:helpers
// Zasada (PROMPT 11 pkt 16): brakujące dane NIGDY nie są interpolowane —
// dziura w rytmie serii daje punkt-przerwę (value: null), który Sparkline
// rysuje jako przerwanie linii.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.error-utils.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "error-utils-test");

const { daysBetween, withGaps } = await import(
  pathToFileURL(join(outDir, "seriesUtils.js")).href
);

test("daysBetween: proste odstępy i niepoprawne daty", () => {
  assert.equal(daysBetween("2026-08-10", "2026-08-17"), 7);
  assert.equal(daysBetween("2026-08-17", "2026-08-17"), 0);
  assert.equal(daysBetween("2026-12-29", "2027-01-05"), 7); // przełom roku
  assert.ok(Number.isNaN(daysBetween("zepsuta", "2026-08-17")));
});

test("withGaps: ciągła seria tygodniowa bez przerw", () => {
  const points = [
    { date: "2026-08-03", value: 3 },
    { date: "2026-08-10", value: 4 },
    { date: "2026-08-17", value: 5 },
  ];
  assert.deepEqual(withGaps(points, 7), points);
});

test("withGaps: dziura w serii tygodniowej daje punkt-przerwę", () => {
  const points = [
    { date: "2026-08-03", value: 3 },
    // 2026-08-10: tydzień BEZ raportu
    { date: "2026-08-17", value: 5 },
  ];
  const out = withGaps(points, 7);
  assert.equal(out.length, 3);
  assert.deepEqual(out[1], { date: null, value: null });
  assert.equal(out[0].value, 3);
  assert.equal(out[2].value, 5);
});

test("withGaps: seria dzienna — brakujący dzień przerywa linię", () => {
  const out = withGaps([
    { date: "2026-08-14", value: 2100 },
    { date: "2026-08-15", value: 2200 },
    { date: "2026-08-18", value: 1900 },
  ], 1);
  assert.equal(out.length, 4);
  assert.equal(out[2].value, null); // przerwa między 15 a 18
});

test("withGaps: tolerancja 1,5x rytmu nie tworzy fałszywych przerw", () => {
  // Raport co 8 dni (przesunięty o dzień) to nadal ciągła seria tygodniowa.
  const out = withGaps([
    { date: "2026-08-03", value: 3 },
    { date: "2026-08-11", value: 4 },
  ], 7);
  assert.equal(out.length, 2);
});

test("withGaps: nieparsowalna data nie generuje przerwy ani wyjątku", () => {
  const out = withGaps([
    { date: "zepsuta-data", value: 1 },
    { date: "2026-08-17", value: 2 },
  ], 7);
  assert.equal(out.length, 2);
});

test("withGaps: pusta i jednopunktowa seria przechodzą bez zmian", () => {
  assert.deepEqual(withGaps([], 7), []);
  assert.deepEqual(withGaps([{ date: "2026-08-17", value: 1 }], 7),
    [{ date: "2026-08-17", value: 1 }]);
});

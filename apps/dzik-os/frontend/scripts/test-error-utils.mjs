// Testy czystej logiki obsługi błędów (src/errorUtils.ts) w Node —
// bez przeglądarki i bez dodatkowych zależności. Uruchomienie:
//     npm run test:helpers
// (kompiluje errorUtils.ts do katalogu tymczasowego i odpala node --test).

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

const {
  classifyFetchFailure,
  errorTypeName,
  filenameFromDisposition,
  maskPathIds,
  redactStack,
} = await import(pathToFileURL(join(outDir, "errorUtils.js")).href);

test("classifyFetchFailure: anulowanie wygrywa z timeoutem", () => {
  assert.equal(classifyFetchFailure(true, true), "CANCELLED");
  assert.equal(classifyFetchFailure(true, false), "CANCELLED");
});

test("classifyFetchFailure: timeout vs offline", () => {
  assert.equal(classifyFetchFailure(false, true), "TIMEOUT");
  assert.equal(classifyFetchFailure(false, false), "OFFLINE");
});

test("errorTypeName: nazwa typu bez komunikatu", () => {
  assert.equal(errorTypeName(new TypeError("tajne dane zdrowotne")), "TypeError");
  assert.equal(errorTypeName("cokolwiek"), "Error");
  assert.equal(errorTypeName(null), "Error");
});

test("redactStack: tylko pliki własne z numerami linii, bez treści", () => {
  const stack = [
    "TypeError: Cannot read x of undefined — pacjent tajny@example.com 92kg",
    "    at save (https://dzik.example.com/assets/index-abc123.js:42:7)",
    "    at https://evil.example.com/steal?q=SEKRET123",
    "    at fetchX (https://dzik.example.com/assets/vendor-def.js:1:9999)",
  ].join("\n");
  const frames = redactStack(stack);
  assert.deepEqual(frames, ["index-abc123.js:42:7", "vendor-def.js:1:9999"]);
  const joined = frames.join("\n");
  assert.ok(!joined.includes("tajny@example.com"));
  assert.ok(!joined.includes("SEKRET123"));
  assert.ok(!joined.includes("92kg"));
});

test("redactStack: limit ramek i puste wejście", () => {
  assert.deepEqual(redactStack(null), []);
  assert.deepEqual(redactStack("bez ramek, tylko tekst"), []);
  const long = Array.from({ length: 40 },
    (_, i) => `    at f (https://x/assets/c-${i}.js:${i}:1)`).join("\n");
  assert.equal(redactStack(long).length, 20);
});

test("maskPathIds: identyfikatory znikają z etykiety trasy", () => {
  assert.equal(
    maskPathIds("/trener/klient/HOS-USR-AB12CD34EF56"),
    "/trener/klient/{id}"
  );
  assert.equal(maskPathIds("/wiadomosci/12345678"), "/wiadomosci/{id}");
  assert.equal(maskPathIds("/plan"), "/plan");
});

test("filenameFromDisposition: RFC 5987 + fallback + uszkodzone kodowanie", () => {
  assert.equal(
    filenameFromDisposition("attachment; filename*=UTF-8''dieta%20maj.pdf"),
    "dieta maj.pdf"
  );
  assert.equal(
    filenameFromDisposition('attachment; filename="plan.pdf"'),
    "plan.pdf"
  );
  // Uszkodzone %-kodowanie → świadomy fallback do zwykłego filename.
  assert.equal(
    filenameFromDisposition("attachment; filename*=UTF-8''%E0%A4%A; filename=\"x.pdf\""),
    "x.pdf"
  );
  assert.equal(filenameFromDisposition(null), null);
});

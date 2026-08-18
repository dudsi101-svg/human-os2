// Testy czystej logiki wyszukiwarki bazy ćwiczeń w edytorze planu
// (src/exercisePicker.ts) w Node. Uruchomienie: npm run test:helpers.
//
// Przy katalogu rzędu 250 pozycji liczy się nawigacja klawiaturą (seria
// ćwiczeń bez odrywania rąk), skrót „ostatnio używane” tylko wtedy, gdy
// nie zasłania wyników, i komunikat, który mówi WPROST, ile jeszcze
// zostało.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.exercise-picker.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "exercise-picker-test");

const { KEYBOARD_HINT, nextActiveIndex, resultsMessage, showRecent, tabIndexFor } =
  await import(pathToFileURL(join(outDir, "exercisePicker.js")).href);

test("strzałki chodzą po wynikach i zawijają na obu końcach", () => {
  assert.equal(nextActiveIndex(-1, 1, 5), 0);      // pierwsza strzałka w dół
  assert.equal(nextActiveIndex(-1, -1, 5), 4);     // pierwsza strzałka w górę
  assert.equal(nextActiveIndex(0, 1, 5), 1);
  assert.equal(nextActiveIndex(4, 1, 5), 0);       // zawijanie na dole
  assert.equal(nextActiveIndex(0, -1, 5), 4);      // zawijanie na górze
});

test("brak wyników = brak podświetlenia", () => {
  assert.equal(nextActiveIndex(-1, 1, 0), -1);
  assert.equal(nextActiveIndex(3, -1, 0), -1);
});

test("roving tabindex trzyma fokus na jednym wyniku", () => {
  // Przed pierwszą strzałką w tabulacji jest tylko pierwszy wynik.
  assert.equal(tabIndexFor(0, -1), 0);
  assert.equal(tabIndexFor(1, -1), -1);
  // Po strzałkach — dokładnie podświetlony.
  assert.equal(tabIndexFor(2, 2), 0);
  assert.equal(tabIndexFor(0, 2), -1);
});

test("skrót „ostatnio używane” pojawia się tylko przy pustym wyszukiwaniu", () => {
  assert.equal(showRecent(false, 6), true);
  // Trener bez planów: sekcja się nie pokazuje (żadnych pustych ramek).
  assert.equal(showRecent(false, 0), false);
  // Aktywny filtr albo wpisana fraza — skrót nie zasłania wyników.
  assert.equal(showRecent(true, 6), false);
});

test("komunikat mówi wprost, ile jeszcze zostało", () => {
  const message = resultsMessage({
    loading: false, error: null, total: 84, shown: 20, hasMore: true, hasFilters: false,
  });
  assert.match(message, /Znaleziono 84/);
  assert.match(message, /pokazano 20/);
  assert.match(message, /zostało 64/);
  assert.match(message, /Zawęź wyszukiwanie albo pokaż więcej/);
});

test("komplet wyników nie sugeruje, że coś zostało", () => {
  const message = resultsMessage({
    loading: false, error: null, total: 7, shown: 7, hasMore: false, hasFilters: false,
  });
  assert.match(message, /pokazano wszystkie/);
  assert.ok(!/zostało/.test(message));
});

test("zero trafień podpowiada konkretne wyjście", () => {
  const filtered = resultsMessage({
    loading: false, error: null, total: 0, shown: 0, hasMore: false, hasFilters: true,
  });
  assert.match(filtered, /Wyczyść filtry/);
  assert.match(filtered, /ręcznie/);
  const emptyBase = resultsMessage({
    loading: false, error: null, total: 0, shown: 0, hasMore: false, hasFilters: false,
  });
  assert.match(emptyBase, /baza ćwiczeń jest pusta/i);
});

test("stan ładowania i błąd nie udają wyniku", () => {
  assert.equal(
    resultsMessage({ loading: true, error: null, total: 0, shown: 0, hasMore: false,
                     hasFilters: false }),
    "Wyszukiwanie…",
  );
  assert.equal(
    resultsMessage({ loading: false, error: "sieć", total: 0, shown: 0, hasMore: false,
                     hasFilters: false }),
    "",
  );
});

test("podpowiedź klawiaturowa wymienia wszystkie trzy klawisze", () => {
  assert.match(KEYBOARD_HINT, /Strzałki/);
  assert.match(KEYBOARD_HINT, /Enter/);
  assert.match(KEYBOARD_HINT, /Escape/);
});

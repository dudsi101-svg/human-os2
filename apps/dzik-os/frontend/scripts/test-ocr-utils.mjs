// Testy czystej logiki „Przepisz ze zdjęcia" (src/ocrUtils.ts) w Node —
// bez przeglądarki. Uruchomienie: npm run test:helpers.
//
// Najważniejsza reguła pod testem: wynik rozpoznania to PROPOZYCJA, a pole
// nieodczytane zostaje PUSTE. Zerowanie albo zgadywanie brakującej wartości
// odżywczej byłoby fałszowaniem danych, na których ktoś planuje jedzenie.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.ocr.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "ocr-test");

const {
  appendText,
  documentMatches,
  linesToExerciseNames,
  missingProductFields,
  modeLabel,
  productFormComplete,
  productFormFromProposal,
  statusMessage,
} = await import(pathToFileURL(join(outDir, "ocrUtils.js")).href);

test("propozycja etykiety wypełnia formularz nowego produktu", () => {
  const form = productFormFromProposal({
    name: "Jogurt naturalny 2%",
    kcal_100g: 61,
    protein_100g: 5.1,
    fat_100g: 2,
    carbs_100g: 4.7,
    fiber_100g: 0,
    portion_g: 150,
  });
  assert.equal(form.name, "Jogurt naturalny 2%");
  assert.equal(form.kcal_100g, "61");
  assert.equal(form.protein_100g, "5.1");
  assert.equal(form.default_portion_g, "150");
  // Błonnik 0 to konkretna informacja z etykiety — zostaje.
  assert.equal(form.fiber_100g, "0");
  assert.equal(form.source, "etykieta produktu (zdjęcie)");
  assert.ok(productFormComplete(form));
});

test("pole nieodczytane zostaje puste, nigdy zgadywane ani zerowane", () => {
  const form = productFormFromProposal({
    name: null, kcal_100g: 250, protein_100g: null,
    fat_100g: null, carbs_100g: null, fiber_100g: null, portion_g: null,
  });
  assert.equal(form.protein_100g, "");
  assert.equal(form.fat_100g, "");
  assert.equal(form.name, "");
  assert.equal(form.kcal_100g, "250");
  assert.deepEqual(
    missingProductFields(form),
    ["nazwa", "białko", "tłuszcz", "węglowodany"]
  );
  assert.equal(productFormComplete(form), false);
});

test("wartość spoza zakresu importu CSV nie trafia do formularza", () => {
  const form = productFormFromProposal({
    name: "Dziwny produkt",
    kcal_100g: 5000,      // powyżej 900
    protein_100g: -2,     // ujemne
    fat_100g: 100,        // dokładnie na granicy — zostaje
    carbs_100g: 101,      // powyżej 100
    portion_g: 20000,     // powyżej 5000
  });
  assert.equal(form.kcal_100g, "");
  assert.equal(form.protein_100g, "");
  assert.equal(form.fat_100g, "100");
  assert.equal(form.carbs_100g, "");
  assert.equal(form.default_portion_g, "");
});

test("brak propozycji daje pusty formularz, a nie wyjątek", () => {
  const form = productFormFromProposal(null);
  assert.equal(form.name, "");
  assert.equal(form.category, "Inne");
  assert.equal(form.kcal_100g, "");
});

test("tekst z kartki staje się listą nazw bez zgadywania serii", () => {
  const names = linesToExerciseNames(
    "Trening A\n\nPrzysiad ze sztangą 4x8\n--\nWiosłowanie 3x12\nx\n"
  );
  assert.deepEqual(names, [
    "Trening A", "Przysiad ze sztangą 4x8", "Wiosłowanie 3x12",
  ]);
});

test("wstawianie tekstu dopisuje, nigdy nie nadpisuje pracy człowieka", () => {
  assert.equal(appendText("Zalecenia trenera", "Z kartki"), "Zalecenia trenera\nZ kartki");
  assert.equal(appendText("", "Z kartki"), "Z kartki");
  assert.equal(appendText("Zostaje", "   "), "Zostaje");
});

test("wyszukiwanie dokumentu obejmuje przepisany tekst skanu", () => {
  const doc = { title: "Wyniki badań", ocr_text: "Morfologia: hemoglobina 14,2" };
  assert.ok(documentMatches(doc, "morfologia"));
  assert.ok(documentMatches(doc, "wyniki"));
  assert.ok(documentMatches(doc, ""));
  assert.equal(documentMatches(doc, "kreatynina"), false);
  assert.equal(documentMatches({ title: "Umowa" }, "morfologia"), false);
});

test("komunikat stanu mówi wprost, co się dzieje", () => {
  assert.match(statusMessage({ status: "RUNNING" }), /Przepisujemy/);
  assert.match(statusMessage({ status: "PENDING" }, 3), /kolejce/);
  assert.match(statusMessage({ status: "DONE", chars: 120 }), /120 znak/);
  assert.equal(
    statusMessage({ status: "FAILED", error: "Silnik niedostępny." }),
    "Silnik niedostępny."
  );
  assert.equal(statusMessage(null), "");
});

test("nazwa trybu jest po polsku i bez nazw dostawców", () => {
  assert.equal(modeLabel("LOCAL"), "tryb lokalny");
  assert.equal(modeLabel("EXTENDED"), "tryb rozszerzony");
  assert.equal(modeLabel(null), "");
});

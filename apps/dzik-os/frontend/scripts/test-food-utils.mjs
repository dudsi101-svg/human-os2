// Testy czystej logiki bazy produktów (src/foodUtils.ts) w Node — bez
// przeglądarki. Uruchomienie: npm run test:helpers.
//
// Kalkulator porcji ma dawać te same liczby w panelu trenera i klienta,
// a wartości bez danych (błonnik) mają zostawać puste, a nie zerowe.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.food.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "food-test");

const {
  FOOD_APPROXIMATION_HINT,
  computePortion,
  defaultPortionGrams,
  formatPortion,
  gramsToUnits,
  matchesFoodQuery,
  normalizeFoodName,
  roundMacro,
  unitHint,
  unitsToGrams,
} = await import(pathToFileURL(join(outDir, "foodUtils.js")).href);

const EGG = {
  kcal_100g: 143, protein_100g: 12.6, fat_100g: 9.5, carbs_100g: 0.7,
  fiber_100g: 0, default_portion_g: 110, unit_name: "jajko M (bez skorupki)",
  unit_grams: 50,
};
const CHICKEN = {
  kcal_100g: 110, protein_100g: 23, fat_100g: 1.5, carbs_100g: 0,
  fiber_100g: null, default_portion_g: 150, unit_name: null, unit_grams: null,
};
const BREAD = {
  kcal_100g: 220, protein_100g: 7, fat_100g: 1.5, carbs_100g: 42,
  fiber_100g: 6.5, default_portion_g: 70, unit_name: "kromka", unit_grams: 35,
};

test("normalizeFoodName: małe litery i polskie znaki diakrytyczne", () => {
  assert.equal(normalizeFoodName("Łosoś"), "losos");
  assert.equal(normalizeFoodName("  ŻÓŁTKO  "), "zoltko");
  assert.equal(normalizeFoodName("Kasza jęczmienna"), "kasza jeczmienna");
  assert.equal(normalizeFoodName("Chleb"), "chleb");
});

test("matchesFoodQuery: dopasowanie bez wielkości liter i diakrytyków", () => {
  assert.ok(matchesFoodQuery("Łosoś, surowy", "losos"));
  assert.ok(matchesFoodQuery("Łosoś, surowy", "ŁOSOŚ"));
  assert.ok(matchesFoodQuery("Jogurt naturalny 2%", "jogurt"));
  assert.ok(matchesFoodQuery("Cokolwiek", ""), "puste zapytanie pasuje do wszystkiego");
  assert.equal(matchesFoodQuery("Łosoś, surowy", "dorsz"), false);
});

test("unitsToGrams: 2 jajka = 100 g, 2 kromki = 70 g", () => {
  assert.equal(unitsToGrams(EGG, 2), 100);
  assert.equal(unitsToGrams(BREAD, 2), 70);
  assert.equal(unitsToGrams(BREAD, 0.5), 17.5);
  // Produkt bez jednostki sztukowej nie udaje, że ją ma.
  assert.equal(unitsToGrams(CHICKEN, 2), null);
  assert.equal(unitsToGrams(EGG, -1), null);
  assert.equal(unitsToGrams(EGG, Number.NaN), null);
});

test("gramsToUnits: gramatura wyrażona w sztukach", () => {
  assert.equal(gramsToUnits(BREAD, 70), 2);
  assert.equal(gramsToUnits(BREAD, 50), 1.4);
  assert.equal(gramsToUnits(CHICKEN, 150), null);
  assert.equal(gramsToUnits(BREAD, 0), null);
});

test("computePortion: przeliczenie gramatury na kcal i makro", () => {
  const values = computePortion(CHICKEN, 200);
  assert.equal(values.grams, 200);
  assert.equal(values.kcal, 220);
  assert.equal(values.protein_g, 46);
  assert.equal(values.fat_g, 3);
  assert.equal(values.carbs_g, 0);
  // Brak danych o błonniku zostaje brakiem danych — nie zerem.
  assert.equal(values.fiber_g, null);
});

test("computePortion: błonnik liczony, gdy produkt go deklaruje", () => {
  const values = computePortion(BREAD, 70);
  assert.equal(values.fiber_g, 4.6);
  assert.equal(values.kcal, 154);
  const zeroFiber = computePortion(EGG, 100);
  assert.equal(zeroFiber.fiber_g, 0, "zadeklarowane 0 g to nie brak danych");
});

test("computePortion: niepoprawna gramatura daje zera, nigdy NaN", () => {
  for (const bad of [0, -50, Number.NaN, Number.POSITIVE_INFINITY]) {
    const values = computePortion(BREAD, bad);
    assert.equal(values.grams, 0);
    assert.equal(values.kcal, 0);
    assert.ok(!Number.isNaN(values.protein_g));
  }
});

test("computePortion: droga przez sztuki i przez gramy daje ten sam wynik", () => {
  const grams = unitsToGrams(BREAD, 2);
  assert.deepEqual(computePortion(BREAD, grams), computePortion(BREAD, 70));
});

test("defaultPortionGrams: typowa porcja albo 100 g", () => {
  assert.equal(defaultPortionGrams(CHICKEN), 150);
  assert.equal(defaultPortionGrams({ ...CHICKEN, default_portion_g: null }), 100);
  assert.equal(defaultPortionGrams({ ...CHICKEN, default_portion_g: 0 }), 100);
});

test("unitHint: czytelna podpowiedź jednostki sztukowej", () => {
  assert.equal(unitHint(BREAD), "1 kromka ≈ 35 g");
  assert.equal(unitHint(CHICKEN), null);
  assert.equal(unitHint({ ...BREAD, unit_grams: null }), null);
});

test("formatPortion: błonnik pokazywany tylko, gdy jest znany", () => {
  assert.equal(
    formatPortion(computePortion(CHICKEN, 100)),
    "110 kcal · B 23 g · T 1.5 g · W 0 g"
  );
  assert.ok(formatPortion(computePortion(BREAD, 100)).includes("Bł 6.5 g"));
});

test("roundMacro: jedno miejsce po przecinku (dane są przybliżone)", () => {
  assert.equal(roundMacro(12.34), 12.3);
  assert.equal(roundMacro(12.35), 12.4);
  assert.equal(roundMacro(0), 0);
});

test("FOOD_APPROXIMATION_HINT mówi wprost, że wartości są przybliżone", () => {
  assert.ok(FOOD_APPROXIMATION_HINT.includes("przybliżone"));
  assert.ok(FOOD_APPROXIMATION_HINT.includes("uśrednione"));
});

import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import test from "node:test";

// Helper jest w TypeScript — kompilujemy go do cache node_modules (jak test-food-utils).
execSync("npx tsc -p scripts/tsconfig.suwaki.json", { stdio: "inherit" });
const { przesun, naGoalMix, zGoalMix, opisWagi } = await import("../node_modules/.cache/suwaki-test/suwaki.js");

const suma = (w) => w.reduce((s, x) => s + x, 0);

test("przesunięcie zabiera pozostałym proporcjonalnie, suma zawsze 100", () => {
  assert.deepEqual(przesun([35, 35, 30], 0, 55), [55, 25, 20]);
  // Równe wagi: po równo (przykład z modelu: przesunięcie jednego o +d zabiera po d/2).
  assert.deepEqual(przesun([40, 30, 30], 0, 60), [60, 20, 20]);
  for (const [w, i, v] of [[[35, 35, 30], 1, 0], [[10, 80, 10], 2, 70], [[33, 33, 34], 0, 100], [[50, 25, 25], 1, 5]]) {
    const out = przesun(w, i, v);
    assert.equal(suma(out), 100, JSON.stringify(out));
    assert.ok(out.every((x) => x >= 0 && x % 5 === 0), JSON.stringify(out));
  }
});

test("zaokrąglenie do 5 % i domknięcie reszty", () => {
  assert.deepEqual(przesun([35, 35, 30], 0, 52), [50, 25, 25]);
  assert.deepEqual(przesun([35, 35, 30], 0, 100), [100, 0, 0]);
  assert.deepEqual(przesun([35, 35, 30], 0, 0), [0, 55, 45]);
});

test("kłódka: zablokowany suwak nie oddaje ani nie przyjmuje", () => {
  assert.deepEqual(przesun([40, 30, 30], 0, 60, [false, true, false]), [60, 30, 10]);
  assert.deepEqual(przesun([40, 30, 30], 0, 90, [false, true, false]), [70, 30, 0]); // sufit = 100 − zablokowane
  // Przesuwanie zablokowanego suwaka nic nie zmienia.
  assert.deepEqual(przesun([40, 30, 30], 1, 90, [false, true, false]), [40, 30, 30]);
  // Dwa zablokowane: jedyny wolny wynika z reszty — nie da się go ruszyć.
  assert.deepEqual(przesun([40, 30, 30], 0, 90, [false, true, true]), [40, 30, 30]);
});

test("wolne suwaki na zerze dzielą resztę po równo", () => {
  assert.deepEqual(przesun([100, 0, 0], 0, 60), [60, 20, 20]);
  // 17,5 + 17,5 → 20 + 20 = 105: domknięcie na pierwszym z największych wolnych.
  assert.deepEqual(przesun([100, 0, 0], 0, 65), [65, 15, 20]);
});

test("konwersja do goal_mix i z powrotem oraz aria-valuetext", () => {
  assert.deepEqual(naGoalMix([50, 25, 25]), { redukcja: 0.5, wydolnosc: 0.25, regeneracja: 0.25 });
  assert.deepEqual(zGoalMix({ redukcja: 0.5, wydolnosc: 0.25, regeneracja: 0.25 }), [50, 25, 25]);
  assert.deepEqual(zGoalMix(null), [35, 35, 30]); // te same domyślne, co suwaki w panelu
  assert.equal(opisWagi("Redukcja", 50), "Redukcja 50 %");
});

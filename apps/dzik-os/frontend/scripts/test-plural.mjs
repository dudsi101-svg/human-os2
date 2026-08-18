import assert from "node:assert/strict";
import test from "node:test";

import { ile, odmien } from "../src/plural.ts";

test("liczba pojedyncza", () => {
  assert.equal(odmien(1, "jednostka", "jednostki", "jednostek"), "jednostka");
});

test("2–4 biorą formę mnogą krótką", () => {
  for (const n of [2, 3, 4, 22, 23, 24, 102]) {
    assert.equal(odmien(n, "jednostka", "jednostki", "jednostek"), "jednostki", `n=${n}`);
  }
});

test("5+ oraz 0 biorą dopełniacz", () => {
  for (const n of [0, 5, 9, 25, 100]) {
    assert.equal(odmien(n, "jednostka", "jednostki", "jednostek"), "jednostek", `n=${n}`);
  }
});

test("nastki są wyjątkiem — 12 to „jednostek”, nie „jednostki”", () => {
  for (const n of [12, 13, 14, 112, 113, 114]) {
    assert.equal(odmien(n, "jednostka", "jednostki", "jednostek"), "jednostek", `n=${n}`);
  }
});

test("11 to dopełniacz mimo końcówki 1", () => {
  assert.equal(odmien(11, "jednostka", "jednostki", "jednostek"), "jednostek");
  assert.equal(odmien(21, "jednostka", "jednostki", "jednostek"), "jednostek");
});

test("ile() skleja liczbę z odmienioną formą", () => {
  assert.equal(ile(1, "ćwiczenie", "ćwiczenia", "ćwiczeń"), "1 ćwiczenie");
  assert.equal(ile(3, "ćwiczenie", "ćwiczenia", "ćwiczeń"), "3 ćwiczenia");
  assert.equal(ile(12, "ćwiczenie", "ćwiczenia", "ćwiczeń"), "12 ćwiczeń");
});

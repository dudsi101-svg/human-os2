import assert from "node:assert/strict";
import test from "node:test";

import { powitanie } from "../src/powitanie.ts";

test("pora dnia decyduje o słowie powitania", () => {
  assert.equal(powitanie(5, "Anna"), "Dzień dobry, Anna");
  assert.equal(powitanie(11, "Anna"), "Dzień dobry, Anna");
  assert.equal(powitanie(12, "Anna"), "Cześć, Anna");
  assert.equal(powitanie(17, "Anna"), "Cześć, Anna");
  assert.equal(powitanie(18, "Anna"), "Dobry wieczór, Anna");
  assert.equal(powitanie(23, "Anna"), "Dobry wieczór, Anna");
  assert.equal(powitanie(2, "Anna"), "Dobry wieczór, Anna");
});

test("bez imienia — samo powitanie, bez przecinka", () => {
  assert.equal(powitanie(9, ""), "Dzień dobry");
  assert.equal(powitanie(9, null), "Dzień dobry");
  assert.equal(powitanie(9, "  "), "Dzień dobry");
});

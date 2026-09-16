import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import test from "node:test";

// Helper jest w TypeScript — kompilujemy go do cache node_modules (jak test-suwaki).
// `bloki.ts` importuje etykiety z `types.ts`; tsc zostawia import bez rozszerzenia
// (bundler go rozwiązuje), a Node w ESM wymaga `./types.js` — dopisujemy je po kompilacji.
execSync("npx tsc -p scripts/tsconfig.bloki.json", { stdio: "inherit" });
const skompilowany = new URL("../node_modules/.cache/bloki-test/bloki.js", import.meta.url);
writeFileSync(skompilowany, readFileSync(skompilowany, "utf8").replace(/from "\.\/types"/g, 'from "./types.js"'));
const { pozycjaZBloku, wstawDoDnia, etykietaBloku, podsumowaniePrzypisania, komunikatPoPrzypisaniu, domyslneDni } =
  await import("../node_modules/.cache/bloki-test/bloki.js");

const blok = (kind, extra = {}) => ({
  id: `B-${kind}`, coach_id: "C", kind, kind_label: kind, variant_label: null, source: "trener", status: "ACTIVE",
  created_at: "", updated_at: "", name: `Blok ${kind}`, level: "POCZATKUJACY", variant: kind === "CARDIO" ? null : "C",
  duration_min: 10, items: [{ name: "x", dose: "1" }], ...extra,
});
const cardio = { goal_mix: { redukcja: 0, wydolnosc: 0, regeneracja: 1 }, level: "POCZATKUJACY", machines: ["rowerek"],
  prescription: { hr_pct_range: [55, 65], hr_bpm_range: null, rpe_range: [2, 3], duration_min: 20,
    structure: { type: "ciagla", rounds: 1, work_min: 20, rest_min: 0, label: "ciągła 20 min", total_min: 20 },
    machine_params: [], caveats: [] }, trace: { source: "blok" }, model_version: "cardio_model_v1", overridden_by_coach: [] };

test("pozycja z bloku: rodzaj pozycji, migawka, preset cardio kopiowany (nie współdzielony)", () => {
  const w = pozycjaZBloku(blok("WARMUP"));
  assert.equal(w.kind, "warmup_block");
  assert.equal(w.block_id, "B-WARMUP");
  assert.equal(w.block.variant, "C");
  assert.equal(w.cardio, undefined);
  const b = blok("CARDIO", { cardio, goal: "regeneracja", goal_label: "Regeneracja (baza tlenowa)" });
  const c = pozycjaZBloku(b);
  assert.equal(c.kind, "cardio");
  assert.equal(c.block.kind, "CARDIO");
  assert.equal(c.block.variant, null);
  assert.deepEqual(c.cardio, cardio);
  assert.notEqual(c.cardio, b.cardio);
  assert.equal(c.comment, "Prowadź według RPE i testu mowy.");
  assert.equal(pozycjaZBloku(blok("STRETCH")).kind, "stretch_block");
});

test("kolejność w dniu: rozgrzewka na początek, cardio przed rozciąganiem, rozciąganie na koniec", () => {
  const sila = [{ name: "Przysiad" }, { name: "Wyciskanie" }];
  const roz = pozycjaZBloku(blok("STRETCH"));
  const car = pozycjaZBloku(blok("CARDIO", { cardio }));
  const rozg = pozycjaZBloku(blok("WARMUP"));
  let dzien = wstawDoDnia(sila, roz);
  dzien = wstawDoDnia(dzien, car);
  dzien = wstawDoDnia(dzien, rozg);
  assert.deepEqual(dzien.map((e) => e.kind ?? "strength"), ["warmup_block", "strength", "strength", "cardio", "stretch_block"]);
  // Bez rozciągania cardio idzie na koniec; wejście nietknięte.
  assert.deepEqual(wstawDoDnia(sila, car).map((e) => e.kind ?? "strength"), ["strength", "strength", "cardio"]);
  assert.equal(sila.length, 2);
});

test("etykieta bloku: poziom · wariant/cel · ≈min", () => {
  assert.equal(etykietaBloku(blok("WARMUP")), "początkujący · całe ciało · ≈10 min");
  assert.equal(etykietaBloku(blok("CARDIO", { cardio, goal_label: "Regeneracja (baza tlenowa)" })),
    "początkujący · Regeneracja (baza tlenowa) · ≈10 min");
  assert.equal(etykietaBloku(blok("STRETCH", { level: null, duration_min: null })), "całe ciało");
});

test("podsumowanie i komunikat po przypisaniu", () => {
  assert.equal(podsumowaniePrzypisania({ szablon: "PPL", bloki: { WARMUP: blok("WARMUP"), STRETCH: blok("STRETCH") }, dni: 3 }),
    "Szablon „PPL” + rozgrzewka „Blok WARMUP” + rozciąganie „Blok STRETCH” → 3 dni");
  assert.equal(podsumowaniePrzypisania({ szablon: null, bloki: { CARDIO: blok("CARDIO") }, dni: 1 }),
    "Bez szablonu + aeroby (cardio) „Blok CARDIO” → 1 dzień");
  assert.equal(komunikatPoPrzypisaniu({ added: { warmup: 3, cardio: 3, stretch: 0 }, skipped_days: [] }, 3),
    "Dodano rozgrzewkę do 3 dni, cardio do 3 dni.");
  assert.equal(komunikatPoPrzypisaniu({ added: { warmup: 2, cardio: 0, stretch: 0 },
    skipped_days: [{ day_index: 0, day_name: "Push", kind: "warmup" }] }, 3),
    "Dodano rozgrzewkę do 2 dni. Pominięto 1 pozycję — dzień miał już blok tego rodzaju z szablonu.");
  assert.equal(komunikatPoPrzypisaniu(null, 1), "Przypisano plan (1 dzień).");
});

test("domyślne dni 1–7 z nazwami „Dzień n”", () => {
  assert.deepEqual(domyslneDni(2), [{ name: "Dzień 1", weekday: null }, { name: "Dzień 2", weekday: null }]);
  assert.equal(domyslneDni(9).length, 7);
  assert.equal(domyslneDni(0).length, 1);
});

// --- Wiele bloków tego samego rodzaju (0.80.0) -------------------------------

test("dwie rozgrzewki zachowują kolejność wyboru (nie odwracają się)", () => {
  // Reguła musi być IDENTYCZNA z backendem (`cardio/bloki.py::wstaw_do_dnia`),
  // bo podgląd w panelu i zapis po stronie serwera mają układać dzień tak samo.
  // Poprzednia wersja robiła `[poz, ...exercises]`, więc druga rozgrzewka
  // lądowała PRZED pierwszą.
  const w1 = { name: "Rozgrzewka A", kind: "warmup_block" };
  const w2 = { name: "Rozgrzewka B", kind: "warmup_block" };
  const silowe = { name: "Przysiad", kind: "strength" };

  let dzien = [silowe];
  dzien = wstawDoDnia(dzien, w1);
  dzien = wstawDoDnia(dzien, w2);
  assert.deepEqual(dzien.map((e) => e.name), ["Rozgrzewka A", "Rozgrzewka B", "Przysiad"]);
});

test("kilka bloków aerobowych idzie po sile, przed rozciąganiem", () => {
  const c1 = { name: "Cardio A", kind: "cardio" };
  const c2 = { name: "Cardio B", kind: "cardio" };
  const s = { name: "Rozciąganie", kind: "stretch_block" };

  let dzien = [{ name: "Przysiad", kind: "strength" }, s];
  dzien = wstawDoDnia(dzien, c1);
  dzien = wstawDoDnia(dzien, c2);
  assert.deepEqual(dzien.map((e) => e.name), ["Przysiad", "Cardio A", "Cardio B", "Rozciąganie"]);
});

test("podsumowanie wymienia każdy blok osobno", () => {
  const w1 = blok("WARMUP", { name: "Rozgrzewka A" });
  const w2 = blok("WARMUP", { name: "Rozgrzewka B" });
  assert.equal(
    podsumowaniePrzypisania({ szablon: "PPL", bloki: { WARMUP: [w1, w2] }, dni: 3 }),
    "Szablon „PPL” + rozgrzewka „Rozgrzewka A” + rozgrzewka „Rozgrzewka B” → 3 dni",
  );
  // Pojedynczy blok (bez listy) nadal działa — stare wywołania się nie psują.
  assert.equal(
    podsumowaniePrzypisania({ szablon: null, bloki: { WARMUP: w1 }, dni: 1 }),
    "Bez szablonu + rozgrzewka „Rozgrzewka A” → 1 dzień",
  );
});

test("komunikat rozróżnia liczbę dni od liczby bloków", () => {
  // Regresja wyłapana przez E2E: przy dwóch rozgrzewkach w jednodniowym planie
  // komunikat mówił „do 2 dni”, bo czytał `added` (pozycje) jako dni.
  assert.equal(
    komunikatPoPrzypisaniu(
      { added: { warmup: 2, cardio: 0, stretch: 0 }, days: { warmup: 1, cardio: 0, stretch: 0 }, skipped_days: [] },
      1),
    "Dodano rozgrzewkę do 1 dnia (2 bloki).");
  // Odpowiedź sprzed 0.80.0 (bez `days`) czytana po staremu.
  assert.equal(
    komunikatPoPrzypisaniu({ added: { warmup: 3, cardio: 0, stretch: 0 }, skipped_days: [] }, 3),
    "Dodano rozgrzewkę do 3 dni.");
});

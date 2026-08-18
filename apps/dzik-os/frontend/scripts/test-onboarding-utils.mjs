// Testy czystej logiki ekranu rozmowy startowej (src/onboardingUtils.ts)
// w Node — bez przeglądarki. Uruchomienie: npm run test:helpers.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.onboarding.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "onboarding-test");

const {
  answerHistory,
  canApproveSummary,
  canSubmit,
  changedSummaryItems,
  charsLeft,
  currentAnswers,
  fieldLabel,
  parseMulti,
  pendingConfirmation,
  progressAnnouncement,
  progressPercent,
  summaryModeNote,
  toggleMulti,
} = await import(pathToFileURL(join(outDir, "onboardingUtils.js")).href);

const step = (over = {}) => ({
  id: "cel_glowny",
  topic: "Cel",
  question: "Co chcesz osiągnąć?",
  why: "Cel decyduje o planie.",
  kind: "TEXT",
  options: [],
  placeholder: "",
  sensitive: false,
  max_len: 300,
  ...over,
});

const answer = (over = {}) => ({
  step_id: "cel_glowny",
  topic: "Cel",
  question: "Co chcesz osiągnąć?",
  value: "Redukcja",
  hidden: false,
  skipped: false,
  sensitive: false,
  safety_flagged: false,
  safety_signals: [],
  version: 1,
  is_current: true,
  created_at: "2026-08-18T10:00:00Z",
  ...over,
});

const summaryRow = (over = {}) => ({
  field_key: "cel_glowny",
  value: "Redukcja",
  hidden: false,
  step_id: "cel_glowny",
  origin: "DETERMINISTIC",
  confidence: "HIGH",
  needs_confirmation: false,
  coach_confirmed: false,
  sensitive: false,
  version: 1,
  ...over,
});

const session = (over = {}) => ({
  id: "HOS-ONB-1",
  status: "SUMMARY_READY",
  summary_mode: "FORM",
  summary_mode_reason: null,
  safety_flag: false,
  started_at: "2026-08-18T10:00:00Z",
  updated_at: "2026-08-18T10:05:00Z",
  summary_at: "2026-08-18T10:05:00Z",
  client_approved_at: null,
  coach_approved_at: null,
  summary_stale: false,
  ...over,
});

test("progressPercent przycina do 0..100 i radzi sobie z brakiem danych", () => {
  assert.equal(progressPercent({}), 0);
  assert.equal(progressPercent({ progress: { percent: 42.4 } }), 42);
  assert.equal(progressPercent({ progress: { percent: -5 } }), 0);
  assert.equal(progressPercent({ progress: { percent: 250 } }), 100);
  assert.equal(progressPercent({ progress: { percent: Number.NaN } }), 0);
});

test("progressAnnouncement mówi, gdzie jesteśmy (aria-live)", () => {
  const state = {
    session: session(),
    step: step(),
    current_answer: null,
    progress: { answered: 2, total: 10, percent: 20 },
    ai: { available: false, reason: "", consent: false },
  };
  const text = progressAnnouncement(state);
  assert.match(text, /Pytanie 3 z 10/);
  assert.match(text, /Co chcesz osiągnąć\?/);
  assert.match(
    progressAnnouncement({ ...state, step: null }),
    /Rozmowa zakończona/,
  );
  assert.match(
    progressAnnouncement({ ...state, session: null }),
    /nie została rozpoczęta/,
  );
});

test("canSubmit: pusta odpowiedź wymaga pominięcia, wybór musi być z listy", () => {
  assert.equal(canSubmit(null, "cokolwiek"), false);
  assert.equal(canSubmit(step(), "   "), false);
  assert.equal(canSubmit(step(), "Redukcja 5 kg"), true);
  assert.equal(canSubmit(step({ max_len: 5 }), "za długa odpowiedź"), false);
  const wybor = step({ kind: "CHOICE", options: ["Tak", "Nie"] });
  assert.equal(canSubmit(wybor, "Tak"), true);
  assert.equal(canSubmit(wybor, "Może"), false);
});

test("kroki wielokrotnego wyboru trzymają kolejność listy, nie klikania", () => {
  const dni = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"];
  let value = "";
  value = toggleMulti(value, "Śr", dni);
  value = toggleMulti(value, "Pn", dni);
  assert.equal(value, "Pn, Śr");
  value = toggleMulti(value, "Pn", dni);
  assert.equal(value, "Śr");
  assert.deepEqual(parseMulti("Pn ,  Śr ,"), ["Pn", "Śr"]);
  const wielo = step({ kind: "MULTI", options: dni });
  assert.equal(canSubmit(wielo, ""), false);
  assert.equal(canSubmit(wielo, "Pn, Śr"), true);
});

test("charsLeft pokazuje zapas do limitu kroku", () => {
  assert.equal(charsLeft(step({ max_len: 10 }), "abc"), 7);
  assert.equal(charsLeft(null, "abc"), 0);
});

test("historia odpowiedzi jest zachowana i posortowana od najnowszej", () => {
  const rows = [
    answer({ version: 1, is_current: false, value: "Schudnąć" }),
    answer({ version: 2, is_current: false, value: "Przytyć" }),
    answer({ version: 3, is_current: true, value: "Zbudować siłę" }),
    answer({ step_id: "sen", version: 1, is_current: true, value: "7-8 h" }),
  ];
  assert.equal(currentAnswers(rows).length, 2);
  const historia = answerHistory(rows, "cel_glowny");
  assert.deepEqual(historia.map((r) => r.version), [2, 1]);
  assert.equal(historia[0].value, "Przytyć");
});

test("pendingConfirmation zwraca tylko niepotwierdzone pola niepewne", () => {
  const rows = [
    summaryRow({ field_key: "a", needs_confirmation: true }),
    summaryRow({ field_key: "b", needs_confirmation: true, coach_confirmed: true }),
    summaryRow({ field_key: "c" }),
  ];
  assert.deepEqual(pendingConfirmation(rows).map((r) => r.field_key), ["a"]);
});

test("summaryModeNote: tryb formularza to informacja z powodem, nie awaria", () => {
  const form = summaryModeNote(session({ summary_mode_reason: "Brak zgody na funkcje AI." }));
  assert.match(form, /krok po kroku/);
  assert.match(form, /Brak zgody na funkcje AI\./);
  assert.doesNotMatch(form, /błąd|Błąd|awaria/);
  const ai = summaryModeNote(session({ summary_mode: "AI_DRAFT" }));
  assert.match(ai, /propozycja AI/);
  assert.match(ai, /Ostatnie słowo należy do Ciebie/);
  assert.equal(summaryModeNote(null), "");
});

test("canApproveSummary wymaga gotowego, niepustego podsumowania", () => {
  const base = {
    session: session(),
    step: null,
    current_answer: null,
    progress: { answered: 3, total: 3, percent: 100 },
    summary: [summaryRow()],
    ai: { available: false, reason: "", consent: false },
  };
  assert.equal(canApproveSummary(base), true);
  assert.equal(canApproveSummary({ ...base, summary: [] }), false);
  assert.equal(
    canApproveSummary({ ...base, session: session({ status: "IN_PROGRESS" }) }),
    false,
  );
  assert.equal(
    canApproveSummary({ ...base, session: session({ status: "CLIENT_APPROVED" }) }),
    false,
  );
  assert.equal(canApproveSummary({ ...base, session: null }), false);
});

test("changedSummaryItems wysyła wyłącznie faktyczne zmiany", () => {
  const server = [
    summaryRow({ field_key: "cel_glowny", value: "Redukcja" }),
    summaryRow({ field_key: "sen_godziny", value: "7-8 h" }),
    summaryRow({ field_key: "alergie", value: "", hidden: true }),
  ];
  assert.deepEqual(changedSummaryItems(server, {}), []);
  assert.deepEqual(changedSummaryItems(server, { cel_glowny: "  Redukcja  " }), []);
  assert.deepEqual(
    changedSummaryItems(server, { cel_glowny: "Redukcja 5 kg", sen_godziny: "7-8 h" }),
    [{ field_key: "cel_glowny", value: "Redukcja 5 kg" }],
  );
  // Pole ukryte (brak zgody na tę kategorię) nigdy nie jest odsyłane.
  assert.deepEqual(changedSummaryItems(server, { alergie: "orzechy" }), []);
});

test("fieldLabel tłumaczy znane klucze i nie gubi nieznanych", () => {
  assert.equal(fieldLabel("cel_glowny"), "Główny cel");
  assert.equal(fieldLabel("suplementacja_deklaracja"), "Suplementy i leki (deklaracja)");
  assert.equal(fieldLabel("nieznane_pole"), "nieznane_pole");
});

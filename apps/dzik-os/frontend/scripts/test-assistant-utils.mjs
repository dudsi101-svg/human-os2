// Testy czystej logiki asystenta trenera (src/assistantUtils.ts) w Node —
// bez przeglądarki. Uruchomienie: npm run test:helpers.
//
// Reguły pod testem: propozycja DOKŁADA dni (nigdy nie kasuje pracy
// trenera), każde wstawienie da się cofnąć (migawka jest niezależną kopią),
// ciężary nie są proponowane, a powtórne kliknięcie z tym samym formularzem
// daje ten sam klucz idempotencji.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.assistant.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "assistant-test");

const {
  appendDays,
  draftRequest,
  engineLabel,
  formReady,
  hasLocalPath,
  hasProposal,
  idempotencyKey,
  isFinished,
  isUntouched,
  localDayToPlanDay,
  matchToExercise,
  normalizeForm,
  proposalToPlanDays,
  snapshot,
  statusMessage,
} = await import(pathToFileURL(join(outDir, "assistantUtils.js")).href);

const emptyDay = () => ({
  name: "",
  weekday: null,
  exercises: [{ name: "", sets: "", reps: "", weight: "", rest: "" }],
});

const proposal = {
  days: [
    {
      name: "Trening A",
      weekday: 1,
      rationale: "Pokrywa przysiad i wypychanie.",
      exercises: [
        {
          name: "Przysiad ze sztangą",
          exercise_id: "HOS-EXC-1",
          sets: "3",
          reps: "8-10",
          weight: "60 kg",
          tempo: "2011",
          rest: "90 s",
        },
      ],
    },
  ],
};

test("propozycja zamienia się na dni planu, a ciężar zostaje pusty", () => {
  const days = proposalToPlanDays(proposal);
  assert.equal(days.length, 1);
  assert.equal(days[0].name, "Trening A");
  assert.equal(days[0].exercises[0].exercise_id, "HOS-EXC-1");
  // Dobór obciążenia to decyzja trenera — nawet jeśli serwer coś przyśle.
  assert.equal(days[0].exercises[0].weight, "");
  assert.equal(days[0].exercises[0].reps, "8-10");
});

test("wstawienie DOKŁADA dni i nie kasuje pracy trenera", () => {
  const existing = [
    { name: "Mój dzień", weekday: null, exercises: [{ name: "Martwy ciąg" }] },
  ];
  const merged = appendDays(existing, proposalToPlanDays(proposal));
  assert.equal(merged.length, 2);
  assert.equal(merged[0].name, "Mój dzień");
  assert.equal(merged[1].name, "Trening A");
});

test("nietknięty dzień startowy zostaje zastąpiony (nie ma czego chronić)", () => {
  assert.equal(isUntouched([emptyDay()]), true);
  const merged = appendDays([emptyDay()], proposalToPlanDays(proposal));
  assert.equal(merged.length, 1);
  assert.equal(merged[0].name, "Trening A");
});

test("migawka do cofnięcia jest niezależną kopią", () => {
  const days = [
    { name: "Dzień", weekday: null, exercises: [{ name: "Przysiad", sets: "3" }] },
  ];
  const before = snapshot(days);
  days[0].name = "Zmienione";
  days[0].exercises[0].sets = "5";
  assert.equal(before[0].name, "Dzień");
  assert.equal(before[0].exercises[0].sets, "3");
});

test("dzień ścieżki lokalnej bierze pierwsze dopasowanie i pomija puste sloty", () => {
  const day = localDayToPlanDay({
    name: "Trening A — całe ciało",
    weekday: 1,
    slots: [
      {
        pattern: "PRZYSIAD",
        pattern_label: "przysiad",
        matches: [
          { id: "HOS-EXC-1", name: "Przysiad", equipment: "Sztanga", level: null,
            muscles_primary: [], tempo_hint: "2011", video_url: null },
          { id: "HOS-EXC-2", name: "Przysiad goblet", equipment: "Hantle", level: null,
            muscles_primary: [], tempo_hint: null, video_url: null },
        ],
      },
      { pattern: "ROTACJA", pattern_label: "rotacja", matches: [] },
    ],
  });
  assert.equal(day.exercises.length, 1);
  assert.equal(day.exercises[0].exercise_id, "HOS-EXC-1");
  assert.equal(day.exercises[0].tempo, "2011");
  assert.equal(day.exercises[0].weight, "");
});

test("pojedyncze ćwiczenie z bazy staje się pozycją planu bez ciężaru", () => {
  const ex = matchToExercise({
    id: "HOS-EXC-9", name: "Wiosłowanie", equipment: "Sztanga", level: "POCZATKUJACY",
    muscles_primary: ["NAJSZERSZY_GRZBIETU"], tempo_hint: null, video_url: "https://x",
  });
  assert.equal(ex.exercise_id, "HOS-EXC-9");
  assert.equal(ex.weight, "");
  assert.equal(ex.video_url, "https://x");
});

test("ten sam formularz daje ten sam klucz idempotencji", () => {
  const form = { days_per_week: 3, equipment: ["Sztanga"], level: "POCZATKUJACY",
                 goal: "Siła", session_minutes: 60 };
  assert.equal(idempotencyKey(form, null, 0), idempotencyKey(form, null, 0));
  // Kolejność sprzętu nie zmienia treści żądania.
  assert.equal(
    idempotencyKey(form, null, 0),
    idempotencyKey({ ...form, equipment: ["Sztanga"] }, null, 0),
  );
  // Inny cel, inny klient albo świadome „generuj ponownie” = inny klucz.
  assert.notEqual(idempotencyKey({ ...form, goal: "Masa" }, null, 0),
                  idempotencyKey(form, null, 0));
  assert.notEqual(idempotencyKey(form, "HOS-USR-1", 0), idempotencyKey(form, null, 0));
  assert.notEqual(idempotencyKey(form, null, 1), idempotencyKey(form, null, 0));
  // Backend wymaga co najmniej 8 znaków.
  assert.ok(idempotencyKey(form, null, 0).length >= 8);
});

test("żądanie zadania niesie komplet warunków i klucz idempotencji", () => {
  const body = draftRequest(
    { days_per_week: 4, equipment: [], level: "SREDNIOZAAWANSOWANY",
      goal: "  Wrócić do biegania  ", session_minutes: 45 },
    "HOS-USR-7", 0,
  );
  assert.equal(body.task_key, "PLAN_DRAFT");
  assert.equal(body.input.goal, "Wrócić do biegania");
  assert.equal(body.input.client_id, "HOS-USR-7");
  assert.ok(body.idempotency_key);
});

test("komunikat stanu mówi wprost, gdy trwa dłużej niż zwykle", () => {
  const running = { id: "1", task_key: "PLAN_DRAFT", status: "RUNNING" };
  assert.match(statusMessage(running, 2, 8), /Przygotowuję szkic…/);
  assert.match(statusMessage(running, 12, 8), /dłużej niż zwykle/);
  assert.match(
    statusMessage({ id: "1", task_key: "PLAN_DRAFT", status: "FAILED",
                    error: "Baza ćwiczeń jest pusta." }),
    /Baza ćwiczeń jest pusta\./,
  );
  assert.match(
    statusMessage({ id: "1", task_key: "PLAN_DRAFT", status: "CANCELLED" }),
    /anulowane/,
  );
  assert.equal(statusMessage(null), "");
});

test("rozpoznanie propozycji, ścieżki lokalnej i stanu końcowego", () => {
  const withProposal = { id: "1", task_key: "PLAN_DRAFT", status: "DONE",
                         result: proposal };
  const withLocal = { id: "2", task_key: "PLAN_DRAFT", status: "DONE",
                      result: { local: { days: [{ name: "A", weekday: 1, slots: [] }] } } };
  assert.equal(hasProposal(withProposal), true);
  assert.equal(hasLocalPath(withProposal), false);
  assert.equal(hasLocalPath(withLocal), true);
  assert.equal(isFinished(withLocal), true);
  assert.equal(isFinished({ id: "3", task_key: "PLAN_DRAFT", status: "RUNNING" }), false);
  // Wynik lokalny mówi wprost, że to tryb lokalny, a nie awaria.
  assert.match(statusMessage(withLocal), /tryb lokalny/i);
});

test("nazwa trybu jest po ludzku, bez nazw dostawców", () => {
  assert.equal(engineLabel("MODEL"), "asystent z modelem");
  assert.equal(engineLabel("LOCAL"), "asystent lokalny (bez modelu)");
  assert.equal(engineLabel(null), "");
});

test("szkic roboczy z nieznanego wejścia wraca do wartości domyślnych", () => {
  const form = normalizeForm({ days_per_week: 99, session_minutes: 5,
                               equipment: "nie lista", goal: 42 });
  assert.equal(form.days_per_week, 3);
  assert.equal(form.session_minutes, 60);
  assert.deepEqual(form.equipment, []);
  assert.equal(form.goal, "");
  assert.equal(formReady(form), false);
  assert.equal(formReady({ ...form, goal: "Siła" }), true);
});

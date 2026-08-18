// Testy czystej logiki panelu „Uzupełnij z opisu" (src/exerciseParser.ts)
// w Node — bez przeglądarki. Uruchomienie: npm run test:helpers.
//
// Najważniejsza reguła pod testem: wstawienie propozycji NIE KASUJE pracy
// trenera. Domyślnie uzupełniamy wyłącznie puste pola; nadpisanie jest
// osobną, świadomą decyzją.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.exercise-parser.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "exercise-parser-test");

const {
  fieldLabels,
  fieldsToInsert,
  isEmptyField,
  mergeProposalIntoForm,
  proposalMessage,
  provenanceFor,
} = await import(pathToFileURL(join(outDir, "exerciseParser.js")).href);

const EMPTY_FORM = {
  name: "", muscle_group: "NOGI", how_to: "", benefit: "", equipment: "",
  video_url: "", muscles_primary: [], muscles_secondary: [], level: "",
  pattern: "", steps: [""], mistakes: [""], cues: [""], safety: "",
  easier: "", harder: "", tempo_hint: "", breathing: "",
};

const PROPOZYCJA = {
  name: "Przysiad ze sztangą z tyłu",
  muscles_primary: ["CZWOROGLOWY_UDA", "POSLADKI"],
  muscles_secondary: ["MIESNIE_GLEBOKIE"],
  level: "SREDNIOZAAWANSOWANY",
  pattern: "PRZYSIAD",
  equipment: "sztanga",
  steps: ["Ustaw sztangę.", "Zejdź w dół."],
  mistakes: ["kolana do środka"],
  cues: ["odepchnij podłogę"],
  safety: "Ustaw asekurację.",
  easier: "Przysiad goblet.",
  harder: "Przysiad przedni.",
  tempo_hint: "3010",
  breathing: "Wdech przed zejściem.",
  benefit: "Siła dolnej części ciała.",
};

test("pusty formularz przyjmuje całą propozycję", () => {
  const next = mergeProposalIntoForm(EMPTY_FORM, PROPOZYCJA);
  assert.equal(next.name, "Przysiad ze sztangą z tyłu");
  assert.deepEqual(next.muscles_primary, ["CZWOROGLOWY_UDA", "POSLADKI"]);
  assert.deepEqual(next.muscles_secondary, ["MIESNIE_GLEBOKIE"]);
  assert.equal(next.level, "SREDNIOZAAWANSOWANY");
  assert.equal(next.pattern, "PRZYSIAD");
  assert.deepEqual(next.steps, ["Ustaw sztangę.", "Zejdź w dół."]);
  assert.equal(next.tempo_hint, "3010");
  assert.equal(next.benefit, "Siła dolnej części ciała.");
  // Pola spoza propozycji zostają nietknięte.
  assert.equal(next.muscle_group, "NOGI");
  assert.equal(next.video_url, "");
});

test("domyślnie NIE nadpisujemy tego, co trener już wpisał", () => {
  const form = {
    ...EMPTY_FORM,
    name: "Moja nazwa",
    steps: ["Mój krok"],
    muscles_primary: ["LYDKA"],
  };
  const next = mergeProposalIntoForm(form, PROPOZYCJA);
  assert.equal(next.name, "Moja nazwa");
  assert.deepEqual(next.steps, ["Mój krok"]);
  assert.deepEqual(next.muscles_primary, ["LYDKA"]);
  // Puste pola i tak zostały uzupełnione.
  assert.equal(next.level, "SREDNIOZAAWANSOWANY");
  assert.deepEqual(next.mistakes, ["kolana do środka"]);
});

test("nadpisanie jest osobną, świadomą decyzją", () => {
  const form = { ...EMPTY_FORM, name: "Moja nazwa", steps: ["Mój krok"] };
  const next = mergeProposalIntoForm(form, PROPOZYCJA, true);
  assert.equal(next.name, "Przysiad ze sztangą z tyłu");
  assert.deepEqual(next.steps, ["Ustaw sztangę.", "Zejdź w dół."]);
});

test("lista z samych pustych wierszy liczy się jako pusta", () => {
  assert.equal(isEmptyField([""]), true);
  assert.equal(isEmptyField(["", "  "]), true);
  assert.equal(isEmptyField(["krok"]), false);
  assert.equal(isEmptyField(""), true);
  assert.equal(isEmptyField("  "), true);
  assert.equal(isEmptyField("x"), false);
});

test("puste pole propozycji nie kasuje wartości w formularzu", () => {
  const pusta = {
    name: null, muscles_primary: [], muscles_secondary: [], level: null,
    pattern: null, equipment: null, steps: [], mistakes: [], cues: [],
    safety: null, easier: null, harder: null, tempo_hint: null,
    breathing: null, benefit: null,
  };
  const form = { ...EMPTY_FORM, name: "Moja nazwa", level: "ZAAWANSOWANY" };
  const next = mergeProposalIntoForm(form, pusta, true);
  assert.equal(next.name, "Moja nazwa");
  assert.equal(next.level, "ZAAWANSOWANY");
  assert.deepEqual(fieldsToInsert(form, pusta, true), []);
});

test("podgląd wypisuje dokładnie te pola, które się zmienią", () => {
  const form = { ...EMPTY_FORM, name: "Moja nazwa" };
  const keys = fieldsToInsert(form, PROPOZYCJA);
  assert.equal(keys.includes("name"), false);
  assert.equal(keys.includes("steps"), true);
  assert.equal(keys.includes("muscles_primary"), true);
  assert.equal(fieldsToInsert(form, PROPOZYCJA, true).includes("name"), true);
  assert.deepEqual(fieldsToInsert(form, null), []);
});

test("etykiety pól są czytelne dla człowieka", () => {
  const labels = { name: "nazwa", steps: "kroki techniki" };
  assert.deepEqual(fieldLabels(["name", "steps"], labels), ["nazwa", "kroki techniki"]);
  // Nieznany klucz nie znika — pokazujemy go zamiast udawać, że go nie ma.
  assert.deepEqual(fieldLabels(["xyz"], labels), ["xyz"]);
});

test("proweniencja zależy od użytego silnika", () => {
  assert.deepEqual(provenanceFor("LOCAL"), {
    source_kind: "TEXT_PARSED", source_engine: "LOCAL",
  });
  assert.deepEqual(provenanceFor("EXTENDED"), {
    source_kind: "AI_ASSISTED", source_engine: "EXTENDED",
  });
  // Wpis wypełniony ręcznie nie dostaje proweniencji „na zapas".
  assert.equal(provenanceFor(null), null);
  assert.equal(provenanceFor(undefined), null);
});

test("komunikat dla czytnika ekranu mówi o trybie, brakach i potwierdzeniach", () => {
  const message = proposalMessage(
    {
      engine: "LOCAL",
      mode_reason: "",
      proposal: PROPOZYCJA,
      unrecognized: ["benefit"],
      needs_confirmation: ["muscles_primary", "muscles_secondary"],
      field_labels: {},
    },
    EMPTY_FORM,
    "tryb lokalny"
  );
  assert.match(message, /tryb lokalny/);
  assert.match(message, /Do wstawienia/);
  assert.match(message, /Nie udało się odczytać: 1/);
  assert.match(message, /Do potwierdzenia: 2/);
  assert.equal(proposalMessage(null, EMPTY_FORM, "tryb lokalny"), "");
});

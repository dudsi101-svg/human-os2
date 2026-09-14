import assert from "node:assert/strict";
import test from "node:test";

import {
  KLUCZ_MOTYWU, KOLOR_PASKA, MOTYW_DOMYSLNY, MOTYWY, NAZWY_MOTYWOW,
  jestMotywem, rozstrzygnijMotyw, zastosujMotyw,
} from "../src/theme.ts";

test("dwa motywy, ciemny domyślny (decyzja właściciela 14.09, pyt. 1 i 3)", () => {
  assert.deepEqual([...MOTYWY], ["ciemny", "czerwony"]);
  assert.equal(MOTYW_DOMYSLNY, "ciemny");
  assert.equal(KLUCZ_MOTYWU, "dzik_theme");
  assert.equal(NAZWY_MOTYWOW.ciemny.nazwa, "Ciemny (czarno-zielony)");
  assert.equal(NAZWY_MOTYWOW.czerwony.nazwa, "Jasny (czerwono-biały)");
});

test("jestMotywem odrzuca wszystko poza dwiema wartościami", () => {
  assert.equal(jestMotywem("ciemny"), true);
  assert.equal(jestMotywem("czerwony"), true);
  assert.equal(jestMotywem("system"), false);
  assert.equal(jestMotywem(""), false);
  assert.equal(jestMotywem(null), false);
  assert.equal(jestMotywem(undefined), false);
  assert.equal(jestMotywem(1), false);
});

test("rozstrzygnięcie: serwer > urządzenie > domyślny; wartości niepoprawne pomijane", () => {
  assert.equal(rozstrzygnijMotyw("czerwony", "ciemny"), "czerwony");
  assert.equal(rozstrzygnijMotyw(null, "czerwony"), "czerwony");
  assert.equal(rozstrzygnijMotyw(undefined, null), "ciemny");
  assert.equal(rozstrzygnijMotyw("system", "czerwony"), "czerwony");
  assert.equal(rozstrzygnijMotyw("x", "y"), "ciemny");
});

/** Minimalna atrapa dokumentu — bez jsdom: dataset + meta theme-color. */
function atrapaDokumentu(meta = { content: "#0b0d0f" }) {
  const dataset = {};
  return {
    documentElement: { dataset },
    querySelector: (sel) => (sel === 'meta[name="theme-color"]' ? meta : null),
    _dataset: dataset,
    _meta: meta,
  };
}

test("zastosujMotyw: jasny ustawia atrybut i meta, ciemny usuwa atrybut (stan sprzed 0.74.0)", () => {
  const doc = atrapaDokumentu();
  zastosujMotyw(doc, "czerwony");
  assert.equal(doc._dataset.theme, "czerwony");
  assert.equal(doc._meta.content, KOLOR_PASKA.czerwony);
  zastosujMotyw(doc, "ciemny");
  assert.equal("theme" in doc._dataset, false);
  assert.equal(doc._meta.content, KOLOR_PASKA.ciemny);
  assert.equal(KOLOR_PASKA.ciemny, "#0b0d0f");
});

test("zastosujMotyw bez meta theme-color nie wybucha", () => {
  const doc = atrapaDokumentu(null);
  zastosujMotyw(doc, "czerwony");
  assert.equal(doc._dataset.theme, "czerwony");
});

import assert from "node:assert/strict";
import test from "node:test";

import {
  adresApiOpisu, adresKartyCwiczenia, bezpiecznyPowrot, etykietaPowrotu, kluczOpisu,
  normalizujNazwe,
} from "../src/nazwy.ts";

// Lustro `import_exercises.normalize_name` z backendu — te same przypadki,
// które sprawdza test API (`test_exercises_by_name.py`).
test("normalizacja: wielkość liter, polskie znaki, spacje", () => {
  assert.equal(normalizujNazwe("  Wyciskanie  SZTANGI leżąc "), "wyciskanie sztangi lezac");
  assert.equal(normalizujNazwe("Przysiad ze sztangą"), normalizujNazwe("PRZYSIAD ZE SZTANGA"));
  assert.equal(normalizujNazwe("Łódź\tźdźbło"), "lodz zdzblo");
  assert.equal(normalizujNazwe("   "), "");
});

test("klucz cache: identyfikator ma pierwszeństwo przed nazwą", () => {
  assert.equal(kluczOpisu("HOS-EXC-1", "cokolwiek"), "id:HOS-EXC-1");
  assert.equal(kluczOpisu(null, "Przysiad ze sztangą"), "nazwa:przysiad ze sztanga");
  assert.equal(kluczOpisu(undefined, "PRZYSIAD ze  sztanga"), kluczOpisu(null, "Przysiad ze sztangą"));
});

test("adres API: po id albo po nazwie, osobno dla klienta i trenera", () => {
  assert.equal(adresApiOpisu("klient", "HOS-EXC-1", "x"), "/api/me/exercises/HOS-EXC-1");
  assert.equal(adresApiOpisu("trener", "HOS-EXC-1", "x"), "/api/coach/exercises/HOS-EXC-1");
  assert.equal(adresApiOpisu("klient", null, " Przysiad ze sztangą "),
    "/api/me/exercises/by-name?name=Przysiad%20ze%20sztang%C4%85");
  assert.equal(adresApiOpisu("trener", undefined, "A & B"), "/api/coach/exercises/by-name?name=A%20%26%20B");
});

test("powrót tylko na wewnętrzną ścieżkę", () => {
  assert.equal(bezpiecznyPowrot("/plan"), "/plan");
  assert.equal(bezpiecznyPowrot("/trener/klient/HOS-USR-1"), "/trener/klient/HOS-USR-1");
  for (const zly of [null, undefined, "", "plan", "//zly.host/x", "/\\zly", "https://zly.host", "/plan x", "/a<b>"]) {
    assert.equal(bezpiecznyPowrot(zly), null, String(zly));
  }
});

test("adres karty w Wiedzy: klient w części Trening, trener w swojej bazie", () => {
  assert.equal(adresKartyCwiczenia("klient", "HOS-EXC-1", "/plan"),
    "/wiedza?czesc=training&cwiczenie=HOS-EXC-1&powrot=%2Fplan");
  assert.equal(adresKartyCwiczenia("klient", "HOS-EXC-1", "https://zly.host"),
    "/wiedza?czesc=training&cwiczenie=HOS-EXC-1");
  assert.equal(adresKartyCwiczenia("trener", "HOS-EXC-1", "/trener/klient/HOS-USR-1"),
    "/trener/wiedza?cwiczenie=HOS-EXC-1&powrot=%2Ftrener%2Fklient%2FHOS-USR-1");
});

test("etykieta powrotu mówi, dokąd prowadzi", () => {
  assert.equal(etykietaPowrotu(null), "Wróć do Wiedzy");
  assert.equal(etykietaPowrotu("/plan"), "Wróć do planu");
  assert.equal(etykietaPowrotu("/"), "Wróć na Dzisiaj");
  assert.equal(etykietaPowrotu("/trener/klient/HOS-USR-1"), "Wróć do karty klienta");
  assert.equal(etykietaPowrotu("/cos"), "Wróć");
});

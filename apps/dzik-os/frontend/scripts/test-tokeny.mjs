// Strażnik tokenów motywu (0.74.0): poza trzema dozwolonymi miejscami
// (`:root`, `html[data-theme="czerwony"]`, scope `.landing--czerwony` strony
// publicznej z własną paletą) w styles.css NIE MA literałów kolorów.
// Literał poza tokenem to „ciemna wyspa” — element, który w jasnym motywie
// zostałby czarny (tak wyglądał podgląd z 14.09: nawigacja, scrim, mapa mięśni).
//
// Test 2: każdy token zdefiniowany w :root ma nadpisanie w bloku jasnego motywu
// (kompletność drugiego motywu — brak nadpisania = kolor z ciemnego na bieli),
// z wyjątkiem tokenów niekolorowych (promienie, fonty, ruch, wysokość nawigacji).

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8")
  .replace(/\/\*[\s\S]*?\*\//g, ""); // bez komentarzy (opisują kolory słowami i liczbami)

const LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\b(?:white|black)\b(?!-)/; // (?!-): white-space to nie kolor
const DOZWOLONE = [
  /^:root$/, /^html\[data-theme="czerwony"\]/, /\.landing--czerwony/,
  // Próbki kolorów w sekcji „Wygląd”: podgląd stałych barw KAŻDEGO motywu (nie
  // mogą zależeć od motywu aktywnego) — jedyny świadomy wyjątek poza paletami.
  /^\.wyglad__probka--/,
];

/** Lekki przebieg po arkuszu: stos selektorów, deklaracje sprawdzane
 * względem najbliższego selektora (blok @media nie liczy się jako selektor). */
export function literalyPozaTokenami(zrodlo) {
  const wyniki = [];
  const stos = [];
  let bufor = "";
  let linia = 1;
  for (const ch of zrodlo) {
    if (ch === "\n") linia++;
    if (ch === "{") {
      stos.push(bufor.trim());
      bufor = "";
    } else if (ch === "}") {
      sprawdz(bufor, stos, linia, wyniki);
      bufor = "";
      stos.pop();
    } else if (ch === ";") {
      sprawdz(bufor, stos, linia, wyniki);
      bufor = "";
    } else {
      bufor += ch;
    }
  }
  return wyniki;
}

function sprawdz(deklaracja, stos, linia, wyniki) {
  const d = deklaracja.trim();
  if (!d || !LITERAL.test(d)) return;
  const selektory = stos.filter((s) => !s.startsWith("@"));
  const dozwolone = selektory.some((s) => DOZWOLONE.some((re) => re.test(s)));
  if (!dozwolone) wyniki.push(`l. ${linia}: ${selektory.at(-1) ?? "?"} → ${d.slice(0, 80)}`);
}

function tokenyBloku(selektor) {
  const start = css.indexOf(`${selektor} {`);
  assert.notEqual(start, -1, `brak bloku ${selektor}`);
  const koniec = css.indexOf("}", start);
  return [...css.slice(start, koniec).matchAll(/--([a-z0-9-]+)\s*:/g)].map((m) => m[1]);
}

test("styles.css: zero literałów kolorów poza :root, [data-theme] i .landing--czerwony", () => {
  const znalezione = literalyPozaTokenami(css);
  assert.deepEqual(znalezione, [], `literały poza tokenami:\n${znalezione.join("\n")}`);
});

test("strażnik wykrywa literał wstrzyknięty do zwykłej reguły", () => {
  const zepsuty = css + "\n.x { color: #123456; }\n@media (min-width: 1px) { .y { background: rgba(0,0,0,.5); } }";
  const z = literalyPozaTokenami(zepsuty);
  assert.equal(z.length, 2, z.join("\n"));
  assert.match(z[0], /\.x/);
  assert.match(z[1], /\.y/);
});

test("każdy token koloru z :root ma nadpisanie w jasnym motywie", () => {
  const NIEKOLOROWE = new Set(["radius-sm", "radius", "radius-lg", "font-display", "font-body", "ease-out", "nav-h"]);
  const root = tokenyBloku(":root").filter((t) => !NIEKOLOROWE.has(t));
  const jasny = new Set(tokenyBloku('html[data-theme="czerwony"]'));
  const brak = root.filter((t) => !jasny.has(t));
  assert.deepEqual(brak, [], `tokeny bez nadpisania w jasnym motywie: ${brak.join(", ")}`);
  const nadmiar = [...jasny].filter((t) => !root.includes(t));
  assert.deepEqual(nadmiar, [], `tokeny jasnego motywu bez definicji w :root: ${nadmiar.join(", ")}`);
});

test("ciemny motyw = brak atrybutu i BEZ color-scheme w :root (bramka piksel w piksel); jasny — light", () => {
  const root = css.slice(css.indexOf(":root {"), css.indexOf("}", css.indexOf(":root {")));
  assert.doesNotMatch(root, /color-scheme/, "color-scheme w :root zmienia natywne kontrolki ciemnego motywu");
  assert.match(css, /html\[data-theme="czerwony"\]\s*\{\s*color-scheme:\s*light/);
});

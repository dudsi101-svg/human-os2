// Wstrzykiwanie listy precache do service workera po `vite build`.
//
// Dlaczego własny skrypt zamiast vite-plugin-pwa/Workbox: service worker
// tej aplikacji jest pisany ręcznie (Web Push, świadomy flow aktualizacji
// bez auto-skipWaiting, twarda zasada "API nigdy w cache") i ma pozostać
// w całości czytelny/audytowalny w jednym pliku. Potrzebujemy wyłącznie
// jednej rzeczy, której nie da się zapisać ręcznie: listy zahaszowanych
// plików danego builda. Ten skrypt skanuje dist/, liczy hash wersji
// i dopisuje na początek dist/sw.js dwie zmienne:
//   self.__BUILD_VERSION   — hash zawartości builda (nazwa cache),
//   self.__PRECACHE_MANIFEST — pełna lista plików tej wersji.
// Źródłowy public/sw.js pozostaje nietknięty (ma fallback "dev").
//
// Uruchamiane przez `npm run build` (patrz package.json).

import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const dist = resolve(dirname(fileURLToPath(import.meta.url)), "..", "dist");

// Pliki wchodzące do precache: shell HTML, manifest, wszystkie hashowane
// assety Vite (JS/CSS/fonty/obrazki w assets/), ikony. Wykluczone: sam
// sw.js (rejestrowany osobno, nie może cache'ować samego siebie) i mapy
// źródeł (niepotrzebne offline).
const EXCLUDE = new Set(["sw.js"]);
const EXCLUDE_EXT = new Set([".map"]);

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      out.push(...walk(full));
    } else {
      out.push(full);
    }
  }
  return out;
}

let files;
try {
  files = walk(dist);
} catch {
  console.error(`[precache] brak katalogu ${dist} — uruchom najpierw vite build`);
  process.exit(1);
}

const urls = [];
const hash = createHash("sha256");
for (const full of files.sort()) {
  const rel = relative(dist, full).split("\\").join("/");
  if (EXCLUDE.has(rel)) continue;
  if (EXCLUDE_EXT.has(rel.slice(rel.lastIndexOf(".")))) continue;
  urls.push(`/${rel}`);
  hash.update(rel);
  hash.update(readFileSync(full));
}

// Sanity check: bez shella i bez choć jednego skryptu precache jest
// bezużyteczny — lepiej przerwać build niż wydać PWA bez działającego
// trybu offline.
if (!urls.includes("/index.html")) {
  console.error("[precache] w dist/ brakuje index.html");
  process.exit(1);
}
if (!urls.some((u) => u.startsWith("/assets/") && u.endsWith(".js"))) {
  console.error("[precache] w dist/assets brakuje plików .js");
  process.exit(1);
}

const version = hash.digest("hex").slice(0, 12);
const swPath = join(dist, "sw.js");
const original = readFileSync(swPath, "utf8");
if (original.includes("self.__PRECACHE_MANIFEST =")) {
  console.error("[precache] dist/sw.js ma już wstrzyknięty manifest — przerwano");
  process.exit(1);
}
const header =
  `/* Wygenerowane przez scripts/inject-precache.mjs — nie edytować. */\n` +
  `self.__BUILD_VERSION = ${JSON.stringify(version)};\n` +
  `self.__PRECACHE_MANIFEST = ${JSON.stringify(urls, null, 2)};\n\n`;
writeFileSync(swPath, header + original);
console.log(`[precache] wersja ${version}, plików: ${urls.length}`);
for (const u of urls) console.log(`  ${u}`);

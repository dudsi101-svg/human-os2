// Strażnik budżetu rozmiaru (audyt B3, 0.53.11).
//
// Po podziale bundla per rolę wejściowy JS ma 91 kB gzip (z 169 kB).
// Ten skrypt pilnuje, żeby nie odrósł po cichu: mierzy gzip pliku
// index-*.js w dist/assets i czerwieni po przekroczeniu budżetu.
// Budżet = stan po podziale + ~30% zapasu na zwykły rozwój; podniesienie
// go to świadoma zmiana w PR z uzasadnieniem, nie dryf.
//
// Użycie: node scripts/sprawdz-budzet.mjs  (po `npm run build`)
// Test strażnika: BUDZET_KB=1 node scripts/sprawdz-budzet.mjs  → czerwień.

import { gzipSync } from "node:zlib";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const BUDZET_KB = Number(process.env.BUDZET_KB || 120);
const katalog = new URL("../dist/assets", import.meta.url).pathname;

const wejsciowe = readdirSync(katalog).filter(
  (f) => f.startsWith("index-") && f.endsWith(".js")
);
if (wejsciowe.length !== 1) {
  console.error(
    `BŁĄD: oczekiwano jednego pliku index-*.js w dist/assets, jest: ${wejsciowe.length}`
  );
  process.exit(1);
}
const plik = wejsciowe[0];
const gz = gzipSync(readFileSync(join(katalog, plik)), { level: 9 }).length;
const kb = Math.round(gz / 102.4) / 10;

if (kb > BUDZET_KB) {
  console.error(
    `BŁĄD: wejściowy JS ${plik} ma ${kb} kB gzip — budżet to ${BUDZET_KB} kB. ` +
      "Sprawdź, co wpadło do bundla wejściowego (nowy import eager? " +
      "biblioteka poza lazy?); podniesienie budżetu wymaga uzasadnienia w PR."
  );
  process.exit(1);
}
console.log(`Budżet rozmiaru: OK — ${plik}: ${kb} kB gzip (budżet ${BUDZET_KB} kB).`);

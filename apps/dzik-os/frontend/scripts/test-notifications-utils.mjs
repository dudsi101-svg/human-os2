// Testy czystej logiki centrum powiadomień (src/notificationsUtils.ts)
// w Node — bez przeglądarki. Uruchomienie: npm run test:helpers.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.notifications.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "notifications-test");

const {
  mergeNotification,
  notificationTargetUrl,
  parseActiveDays,
  quietHoursValid,
  toggleActiveDay,
  unreadBadge,
} = await import(pathToFileURL(join(outDir, "notificationsUtils.js")).href);

test("quietHoursValid: puste = wyłączone, HH:MM wymagane, zakres przez północ legalny", () => {
  assert.equal(quietHoursValid("", ""), true);
  assert.equal(quietHoursValid("22:00", "07:00"), true); // przez północ
  assert.equal(quietHoursValid("08:00", "21:30"), true);
  assert.equal(quietHoursValid("22:00", ""), false); // tylko jedna strona
  assert.equal(quietHoursValid("", "07:00"), false);
  assert.equal(quietHoursValid("25:00", "07:00"), false); // zły format
  assert.equal(quietHoursValid("22:0", "07:00"), false);
  assert.equal(quietHoursValid("22:00", "22:00"), false); // pusty zakres
});

test("parseActiveDays odrzuca śmieci i duplikaty", () => {
  assert.deepEqual([...parseActiveDays("1,2,3")].sort(), ["1", "2", "3"]);
  assert.deepEqual([...parseActiveDays("1, 2 ,9,x,1")].sort(), ["1", "2"]);
  assert.deepEqual([...parseActiveDays("")], []);
});

test("toggleActiveDay przełącza, sortuje i nie pozwala wyłączyć wszystkich dni", () => {
  assert.equal(toggleActiveDay("1,2,3", "2"), "1,3");
  assert.equal(toggleActiveDay("1,3", "2"), "1,2,3");
  assert.equal(toggleActiveDay("5", "5"), "5"); // ostatni dzień zostaje
  assert.equal(toggleActiveDay("1", "9"), "1"); // nieznany dzień ignorowany
});

test("notificationTargetUrl: tylko wewnętrzne ścieżki aplikacji", () => {
  assert.equal(notificationTargetUrl({ url: "/wiadomosci/HOS-THR-1" }), "/wiadomosci/HOS-THR-1");
  assert.equal(notificationTargetUrl({ url: "" }), "/");
  // Powiadomienie nigdy nie wyprowadza poza aplikację (np. phishing url).
  assert.equal(notificationTargetUrl({ url: "https://evil.example" }), "/");
});

test("unreadBadge: 0 bez plakietki, sufit 99+", () => {
  assert.equal(unreadBadge(0), "");
  assert.equal(unreadBadge(1), "1");
  assert.equal(unreadBadge(99), "99");
  assert.equal(unreadBadge(100), "99+");
});

test("mergeNotification: bez duplikatów, najnowsze na górze", () => {
  const rows = [{ id: "b" }, { id: "a" }];
  const merged = mergeNotification(rows, { id: "c" });
  assert.deepEqual(merged.map((r) => r.id), ["c", "b", "a"]);
  // Duplikat (wiersz przyszedł równolegle przez GET) — lista bez zmian.
  assert.equal(mergeNotification(merged, { id: "b" }), merged);
});

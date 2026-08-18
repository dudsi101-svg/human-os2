// E2E PWA/offline (Playwright + Chromium, Node).
//
// Sprawdza kontrakt service workera na PRAWDZIWEJ przeglądarce:
//   1. pierwsze wejście online → rejestracja SW + wypełniony precache,
//   2. offline po wcześniejszym załadowaniu → aplikacja uruchamia shell
//      (bez pustego ekranu), widoczny dedykowany ekran offline,
//   3. Cache Storage NIE zawiera żadnego wpisu /api (dane zdrowotne),
//   4. brakujący asset NIE dostaje HTML (offline: błąd sieci; online: 404),
//   5. /api offline = odrzucony fetch (SW nie serwuje API z cache),
//   6. aktualizacja SW → baner, BEZ auto-przeładowania; reload dopiero
//      po kliknięciu "Odśwież".
//
// Uruchomienie (wymaga wcześniejszego `npm run build` we frontend/
// oraz zainstalowanego pakietu backendu — jak istniejące e2e):
//   NODE_PATH=/opt/node22/lib/node_modules node e2e/test_pwa_offline.mjs
// Ścieżkę Chromium można nadpisać przez DZIK_E2E_CHROMIUM.

import { spawn, execFileSync } from "node:child_process";
import { cpSync, appendFileSync, mkdtempSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import net from "node:net";

// ESM ignoruje NODE_PATH — playwright szukamy jawnie: lokalnie, a potem
// w globalnych node_modules (środowisko z preinstalowanym playwrightem).
function loadPlaywright() {
  const candidates = [
    import.meta.url,
    ...(process.env.NODE_PATH ? [join(process.env.NODE_PATH, "/")] : []),
    "/opt/node22/lib/node_modules/",
  ];
  for (const base of candidates) {
    try {
      return createRequire(base)("playwright");
    } catch {
      /* następny kandydat */
    }
  }
  console.error("Nie znaleziono pakietu playwright (lokalnie ani globalnie).");
  process.exit(1);
}
const { chromium } = loadPlaywright();

const APP_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DIST = join(APP_DIR, "frontend", "dist");
const CHROMIUM =
  process.env.DZIK_E2E_CHROMIUM ||
  (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined);

if (!existsSync(join(DIST, "sw.js"))) {
  console.error("Brak frontend/dist — uruchom najpierw `npm run build`.");
  process.exit(1);
}

function freePort() {
  return new Promise((ok) => {
    const srv = net.createServer();
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => ok(port));
    });
  });
}

const failures = [];
function check(name, cond, detail = "") {
  if (cond) {
    console.log(`  ok: ${name}`);
  } else {
    failures.push(name);
    console.error(`  FAIL: ${name} ${detail}`);
  }
}

// — serwer: kopia dist (test aktualizacji modyfikuje sw.js) + świeża baza —
const tmp = mkdtempSync(join(tmpdir(), "dzik-pwa-e2e-"));
const distCopy = join(tmp, "dist");
cpSync(DIST, distCopy, { recursive: true });
const env = {
  ...process.env,
  DZIK_DATABASE_URL: `sqlite:///${tmp}/e2e.db`,
  DZIK_AUDIT_DB: `${tmp}/audit.db`,
  DZIK_UPLOAD_DIR: `${tmp}/uploads`,
  DZIK_ENV: "test",
  DZIK_BCRYPT_ROUNDS: "4",
  DZIK_FRONTEND_DIST: distCopy,
};
execFileSync("python3", ["-m", "dzik_os.seed"], { env, cwd: tmp });
const port = await freePort();
const server = spawn(
  "python3",
  ["-m", "uvicorn", "dzik_os.main:app", "--host", "127.0.0.1", "--port", String(port)],
  { env, cwd: tmp, stdio: "ignore" }
);
const url = `http://127.0.0.1:${port}`;
for (let i = 0; i < 100; i++) {
  try {
    const r = await fetch(`${url}/api/health`);
    if (r.ok) break;
  } catch {
    await new Promise((ok) => setTimeout(ok, 200));
  }
}

const browser = await chromium.launch({
  executablePath: CHROMIUM,
  args: ["--no-sandbox"],
});
let exitCode = 1;
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });

  // ————— 1. Pierwsze wejście online: rejestracja SW + precache —————
  console.log("1. Rejestracja service workera i precache");
  await page.goto(`${url}/`, { waitUntil: "load" });
  // Pierwsza instalacja: clients.claim() → controllerchange → jednorazowe
  // przeładowanie (istniejące zachowanie pwa.ts). Czekanie toleruje
  // zniszczenie kontekstu przez tę nawigację.
  const deadline = Date.now() + 20000;
  for (;;) {
    try {
      await page.waitForFunction(
        async () => {
          const reg = await navigator.serviceWorker.ready;
          return !!reg.active && !!navigator.serviceWorker.controller;
        },
        null,
        { timeout: Math.max(1000, deadline - Date.now()) }
      );
      break;
    } catch (err) {
      if (Date.now() > deadline) throw err;
      if (!/destroyed|navigation/i.test(String(err))) throw err;
      await page.waitForLoadState("load");
    }
  }
  // Pozwól dobiec jednorazowemu reloadowi po claim() i wykonaj świeżą,
  // już kontrolowaną nawigację — od tego miejsca kontekst jest stabilny.
  await page.waitForTimeout(1000);
  await page.goto(`${url}/`, { waitUntil: "load" });
  const precache = await page.evaluate(async () => {
    const keys = await caches.keys();
    const name = keys.find((k) => k.startsWith("dzik-os-precache-"));
    if (!name) return { name: null, urls: [] };
    const cache = await caches.open(name);
    return {
      name,
      urls: (await cache.keys()).map((r) => new URL(r.url).pathname),
    };
  });
  check("SW aktywny i kontroluje stronę", true);
  check(
    "cache wersjonowany per build (dzik-os-precache-<hash>)",
    /^dzik-os-precache-[0-9a-f]{12}$/.test(precache.name || ""),
    String(precache.name)
  );
  check(
    "precache zawiera shell i hashowane assety",
    precache.urls.includes("/index.html") &&
      precache.urls.some((u) => u.startsWith("/assets/") && u.endsWith(".js")) &&
      precache.urls.some((u) => u.startsWith("/assets/") && u.endsWith(".css")),
    JSON.stringify(precache.urls)
  );

  // Wywołaj ruch API w zasięgu SW, żeby było CO wykryć, gdyby SW
  // niepoprawnie cache'ował API.
  await page.evaluate(() => fetch("/api/health").then((r) => r.json()));

  // ————— 3. Cache Storage bez jakichkolwiek wpisów /api —————
  console.log("2. Cache Storage nie zawiera /api");
  const apiEntries = await page.evaluate(async () => {
    const hits = [];
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const req of await cache.keys()) {
        if (new URL(req.url).pathname.startsWith("/api")) hits.push(req.url);
      }
    }
    return hits;
  });
  check("żaden wpis /api w Cache Storage", apiEntries.length === 0, JSON.stringify(apiEntries));

  // ————— 2. Offline: shell startuje, ekran offline widoczny —————
  console.log("3. Offline po wcześniejszym załadowaniu");
  await context.setOffline(true);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="offline-screen"]', { timeout: 15000 });
  const rootHtml = await page.evaluate(
    () => document.getElementById("root")?.innerHTML || ""
  );
  check("aplikacja offline renderuje shell (bez pustego ekranu)", rootHtml.length > 0);
  check(
    "dedykowany ekran offline widoczny",
    await page.locator('[data-testid="offline-screen"]').isVisible()
  );
  check(
    "ekran offline informuje o braku sieci",
    (await page.textContent('[data-testid="offline-screen"]'))?.includes(
      "Brak połączenia"
    ) === true
  );

  // ————— 5. /api offline = błąd sieci, nie odpowiedź z cache —————
  const apiOffline = await page.evaluate(async () => {
    try {
      const r = await fetch("/api/health");
      return { rejected: false, status: r.status };
    } catch {
      return { rejected: true };
    }
  });
  check(
    "offline /api odrzucone (SW nie przejmuje API)",
    apiOffline.rejected === true,
    JSON.stringify(apiOffline)
  );

  // ————— 4a. Brakujący asset offline: błąd sieci, nigdy HTML —————
  const missingOffline = await page.evaluate(async () => {
    try {
      const r = await fetch("/assets/nie-istnieje-deadbeef.js");
      return {
        rejected: false,
        status: r.status,
        type: r.headers.get("content-type") || "",
      };
    } catch {
      return { rejected: true };
    }
  });
  check(
    "offline brakujący asset = błąd sieci lub nie-HTML",
    missingOffline.rejected === true ||
      !missingOffline.type.includes("text/html"),
    JSON.stringify(missingOffline)
  );

  // ————— 4b. Online: brakujący asset = 404, nie HTML —————
  console.log("4. Powrót online");
  await context.setOffline(false);
  await page.waitForSelector('[data-testid="offline-screen"]', {
    state: "detached",
    timeout: 15000,
  });
  check("ekran offline znika po powrocie sieci", true);
  const missingOnline = await page.evaluate(async () => {
    const r = await fetch("/assets/nie-istnieje-deadbeef.js");
    return { status: r.status, type: r.headers.get("content-type") || "" };
  });
  check(
    "online brakujący asset = 404 bez HTML",
    missingOnline.status === 404 && !missingOnline.type.includes("text/html"),
    JSON.stringify(missingOnline)
  );

  // ————— 6. Aktualizacja: baner, brak auto-reloadu, reload po kliku —————
  console.log("5. Flow aktualizacji (updatefound → baner → klik → reload)");
  await page.evaluate(() => {
    window.__pwaMarker = "sesja-przed-aktualizacja";
  });
  appendFileSync(join(distCopy, "sw.js"), "\n/* wymuszona nowa wersja e2e */\n");
  await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    await reg.update();
  });
  await page.waitForSelector(".update-banner", { timeout: 20000 });
  const markerStillThere = await page.evaluate(() => window.__pwaMarker);
  check(
    "nowa wersja czeka — brak auto-przeładowania w trakcie sesji",
    markerStillThere === "sesja-przed-aktualizacja"
  );
  await Promise.all([
    page.waitForNavigation({ waitUntil: "load", timeout: 20000 }),
    page.click(".update-banner button"),
  ]);
  const markerAfter = await page.evaluate(() => window.__pwaMarker);
  check("kontrolowane przeładowanie po kliknięciu użytkownika", markerAfter === undefined);

  const mimeErrors = consoleErrors.filter((e) => /MIME|module script/i.test(e));
  check("brak błędów MIME w konsoli", mimeErrors.length === 0, JSON.stringify(mimeErrors));

  exitCode = failures.length === 0 ? 0 : 1;
} catch (err) {
  console.error("Nieoczekiwany błąd testu:", err);
  exitCode = 1;
} finally {
  await browser.close();
  server.kill();
}
if (exitCode !== 0) console.error(`\nNiepowodzenia: ${failures.length || "błąd wykonania"}`);
else console.log("\nWszystkie kontrole PWA/offline przeszły.");
process.exit(exitCode);

// Zrzuty wszystkich ekranów aplikacji w obu motywach (0.74.0) — narzędzie
// przeglądu kompletności drugiego motywu i bramka „ciemny motyw piksel
// w piksel” (te same zrzuty przed i po zmianie arkusza, porównanie PIL).
//
// Uruchomienie (po `npm run build`, z katalogu frontend/):
//   DZIK_ZRZUTY_DIR=/tmp/motyw-zrzuty node scripts/zrzuty-motywy.mjs
// Zmienne:
//   DZIK_ZRZUTY_DIR   — katalog wyjściowy (wymagany)
//   DZIK_THEMES       — lista motywów, domyślnie "ciemny,czerwony"
//   DZIK_ZRZUTY_ONLY  — podzbiór nazw ekranów (po przecinku), np. "klient-dzisiaj"
//   DZIK_ZRZUTY_URL   — adres już działającego serwera (bez startu własnego);
//                       bramka pikselowa używa JEDNEGO serwera dla „przed” i „po”
//                       (podmiana zawartości dist/), żeby dane z seedu i ich
//                       znaczniki czasu były identyczne na obu zrzutach
//   DZIK_ZRZUTY_AB    — bramka pikselowa: "przed=/dist-a,po=/dist-b" + DZIK_ZRZUTY_DIST_SERW
//                       (katalog, który serwer podaje jako dist). Dla KAŻDEGO ekranu
//                       po kolei: podmiana zawartości katalogu serwowanego na wariant,
//                       nawigacja, zrzut do <dir>/<motyw>/<wariant>/<nazwa>.png — oba
//                       warianty widzą dokładnie ten sam stan bazy (te same sesje,
//                       znaczniki czasu, zdarzenia audytu), więc różnica = wyłącznie CSS.
//   DZIK_E2E_CHROMIUM — ścieżka Chromium (jak w e2e/test_a11y.mjs)
//   NODE_PATH         — gdzie stoi pakiet playwright, jeśli nie lokalnie
//
// Motyw jest ustawiany tak, jak robi to aplikacja: `localStorage["dzik_theme"]`
// przed pierwszą nawigacją (addInitScript) — bez wstrzykiwania stylów.
// Pliki: <dir>/<motyw>/<nazwa>.png (pełna strona). Serwer: świeża baza z seedem
// na wolnym porcie, flagi modułów włączone (Postępy, szablony diet, wywiad
// kaloryczny, szkice Wiedzy) — żeby ekrany za flagami też były na liście.

import { spawn, execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import net from "node:net";

function loadModule(name) {
  const candidates = [
    import.meta.url,
    ...(process.env.NODE_PATH ? [join(process.env.NODE_PATH, "/")] : []),
    "/opt/node22/lib/node_modules/",
  ];
  for (const base of candidates) {
    try { return createRequire(base)(name); } catch { /* następny */ }
  }
  return null;
}
const playwright = loadModule("playwright");
if (!playwright) { console.error("Brak pakietu playwright."); process.exit(1); }
const { chromium } = playwright;

const OUT = process.env.DZIK_ZRZUTY_DIR;
if (!OUT) { console.error("Podaj DZIK_ZRZUTY_DIR."); process.exit(1); }
const MOTYWY = (process.env.DZIK_THEMES || "ciemny,czerwony").split(",").map((s) => s.trim()).filter(Boolean);
const TYLKO = process.env.DZIK_ZRZUTY_ONLY ? new Set(process.env.DZIK_ZRZUTY_ONLY.split(",")) : null;
// Warianty A/B (bramka pikselowa) — domyślnie jeden wariant bez podmiany.
const WARIANTY = process.env.DZIK_ZRZUTY_AB
  ? process.env.DZIK_ZRZUTY_AB.split(",").map((w) => { const [nazwa, dist] = w.split("="); return { nazwa, dist }; })
  : [{ nazwa: "", dist: null }];
const DIST_SERW = process.env.DZIK_ZRZUTY_DIST_SERW || null;
if (WARIANTY[0].dist && !DIST_SERW) { console.error("DZIK_ZRZUTY_AB wymaga DZIK_ZRZUTY_DIST_SERW."); process.exit(1); }
function podmienDist(dist) {
  for (const f of readdirSync(DIST_SERW)) rmSync(join(DIST_SERW, f), { recursive: true, force: true });
  cpSync(dist, DIST_SERW, { recursive: true });
}

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DIST = join(FRONTEND, "dist");
const CHROMIUM = process.env.DZIK_E2E_CHROMIUM
  || (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined);
if (!existsSync(join(DIST, "index.html"))) {
  console.error("Brak frontend/dist — uruchom najpierw `npm run build`.");
  process.exit(1);
}

function freePort() {
  return new Promise((ok) => {
    const srv = net.createServer();
    srv.listen(0, "127.0.0.1", () => { const { port } = srv.address(); srv.close(() => ok(port)); });
  });
}

const KONTA = {
  klient: ["klient.a@example.com", "KlientA#2026!x"],
  trener: ["dzik@example.com", "DzikTrener#2026"],
  admin: ["admin@example.com", "DzikAdmin#2026"],
};

// Lista ekranów: nazwa → rola, trasa, selektor gotowości, opcjonalne kliknięcia
// (nazwy dostępne — role/tekst) po załadowaniu. Trasa z {klient} = id klienta A.
const EKRANY = [
  // publiczne
  { n: "pub-strona", rola: null, url: "/", czekaj: "h1" },
  { n: "pub-login", rola: null, url: "/login", czekaj: "#email" },
  { n: "pub-prywatnosc", rola: null, url: "/prywatnosc", czekaj: "h1" },
  { n: "pub-aktywacja", rola: null, url: "/aktywacja", czekaj: "main" },
  { n: "pub-reset-hasla", rola: null, url: "/reset-hasla", czekaj: "main" },
  // klient (375 px)
  { n: "klient-dzisiaj", rola: "klient", url: "/", czekaj: "h1:has-text('Dzisiaj')" },
  { n: "klient-plan", rola: "klient", url: "/plan", czekaj: "h1" },
  { n: "klient-plan-dlaczego", rola: "klient", url: "/plan", czekaj: "h1",
    klik: [{ rola: "button", nazwa: "Dlaczego ta wersja?" }], czekajPo: ".dlaczego__panel" },
  { n: "klient-dieta", rola: "klient", url: "/dieta", czekaj: "h1" },
  { n: "klient-postepy", rola: "klient", url: "/monitoring", czekaj: "h1:has-text('Postępy')" },
  { n: "klient-raport", rola: "klient", url: "/wiecej/raport", czekaj: "h1:has-text('Raport')" },
  { n: "klient-wiecej", rola: "klient", url: "/wiecej", czekaj: "h1:has-text('Więcej')" },
  { n: "klient-wiecej-samouczek", rola: "klient", url: "/wiecej", czekaj: "h1:has-text('Więcej')",
    klik: [{ rola: "button", nazwa: "Pomoc / Samouczek" }], czekajPo: "[role='dialog']" },
  { n: "klient-profil", rola: "klient", url: "/profil", czekaj: "h1" },
  { n: "klient-wywiad", rola: "klient", url: "/wywiad", czekaj: "h1:has-text('Wywiad')" },
  { n: "klient-wywiad-wstepny", rola: "klient", url: "/wywiad?typ=wstepny", czekaj: "h1" },
  { n: "klient-wywiad-kaloryczny", rola: "klient", url: "/wywiad?typ=kaloryczny", czekaj: "h1" },
  { n: "klient-rozmowa", rola: "klient", url: "/rozmowa", czekaj: "h1" },
  { n: "klient-ankieta", rola: "klient", url: "/ankieta", czekaj: "h1" },
  { n: "klient-wiedza", rola: "klient", url: "/wiedza", czekaj: "h1" },
  { n: "klient-wiedza-cwiczenia", rola: "klient", url: "/wiedza?czesc=cwiczenia", czekaj: "h1" },
  { n: "klient-wiedza-produkty", rola: "klient", url: "/wiedza?czesc=produkty", czekaj: "h1" },
  { n: "klient-konsultacje", rola: "klient", url: "/konsultacje", czekaj: "h1" },
  { n: "klient-wyzwania", rola: "klient", url: "/wyzwania", czekaj: "h1" },
  { n: "klient-dokumenty", rola: "klient", url: "/dokumenty", czekaj: "h1" },
  { n: "klient-platnosci", rola: "klient", url: "/platnosci", czekaj: "h1:has-text('Płatności')" },
  { n: "klient-wiadomosci", rola: "klient", url: "/wiadomosci", czekaj: "h1" },
  { n: "klient-watek", rola: "klient", url: "/wiadomosci", czekaj: "h1",
    klik: [{ sel: "a.card--nav[href^='/wiadomosci/'], a[href^='/wiadomosci/']" }], czekajPo: "textarea, form" },
  // Centrum powiadomień trzyma otwarte SSE — „networkidle” nigdy nie nadchodzi.
  { n: "klient-powiadomienia", rola: "klient", url: "/powiadomienia", czekaj: "h1", siec: "load" },
  { n: "klient-haslo", rola: "klient", url: "/haslo", czekaj: "h1" },
  // trener (1280 px)
  { n: "trener-klienci", rola: "trener", url: "/trener", czekaj: "h1:has-text('Klienci')" },
  { n: "trener-klient-profil", rola: "trener", url: "/trener/klient/{klient}", czekaj: "[role='tablist']" },
  { n: "trener-klient-rozmowa", rola: "trener", url: "/trener/klient/{klient}?zakladka=rozmowa", czekaj: "[role='tablist']" },
  { n: "trener-klient-wywiad", rola: "trener", url: "/trener/klient/{klient}?zakladka=wywiad", czekaj: "[role='tablist']" },
  { n: "trener-klient-plan", rola: "trener", url: "/trener/klient/{klient}?zakladka=plan", czekaj: "[role='tablist']" },
  { n: "trener-klient-dieta", rola: "trener", url: "/trener/klient/{klient}?zakladka=dieta", czekaj: "[role='tablist']" },
  { n: "trener-klient-harmonogram", rola: "trener", url: "/trener/klient/{klient}?zakladka=harmonogram", czekaj: "[role='tablist']" },
  { n: "trener-klient-raporty", rola: "trener", url: "/trener/klient/{klient}?zakladka=raporty", czekaj: "[role='tablist']" },
  { n: "trener-klient-pomiary", rola: "trener", url: "/trener/klient/{klient}?zakladka=pomiary", czekaj: "[role='tablist']" },
  { n: "trener-klient-monitoring", rola: "trener", url: "/trener/klient/{klient}?zakladka=monitoring", czekaj: "[role='tablist']" },
  { n: "trener-klient-platnosci", rola: "trener", url: "/trener/klient/{klient}?zakladka=platnosci", czekaj: "[role='tablist']" },
  { n: "trener-klient-historia", rola: "trener", url: "/trener/klient/{klient}?zakladka=historia", czekaj: "[role='tablist']" },
  { n: "trener-szablony", rola: "trener", url: "/trener/szablony", czekaj: "h1" },
  { n: "trener-szablony-diet", rola: "trener", url: "/trener/szablony-diet", czekaj: "h1" },
  { n: "trener-wiedza", rola: "trener", url: "/trener/wiedza", czekaj: "[role='tablist']" },
  { n: "trener-wiedza-cwiczenia", rola: "trener", url: "/trener/wiedza", czekaj: "[role='tablist']",
    klik: [{ rola: "tab", nazwa: "Ćwiczenia" }] },
  { n: "trener-wiedza-cwiczenie-mapa", rola: "trener", url: "/trener/wiedza", czekaj: "[role='tablist']",
    klik: [{ rola: "tab", nazwa: "Ćwiczenia" }, { rola: "button", nazwa: "Podgląd" }], czekajPo: ".mmap" },
  { n: "trener-wiedza-produkty", rola: "trener", url: "/trener/wiedza", czekaj: "[role='tablist']",
    klik: [{ rola: "tab", nazwa: "Produkty" }] },
  { n: "trener-wiedza-karty", rola: "trener", url: "/trener/wiedza", czekaj: "[role='tablist']",
    klik: [{ rola: "tab", nazwa: "Karty wiedzy" }] },
  { n: "trener-konsultacje", rola: "trener", url: "/trener/konsultacje", czekaj: "h1" },
  { n: "trener-wyzwania", rola: "trener", url: "/trener/wyzwania", czekaj: "h1" },
  { n: "trener-rozliczenia", rola: "trener", url: "/trener/rozliczenia", czekaj: "h1" },
  { n: "trener-podsumowanie", rola: "trener", url: "/trener/podsumowanie", czekaj: "h1" },
  { n: "trener-monitoring", rola: "trener", url: "/monitoring", czekaj: "h1:has-text('Monitoring')" },
  { n: "trener-monitoring-klient", rola: "trener", url: "/monitoring", czekaj: "h1:has-text('Monitoring')",
    klik: [{ sel: "a.card--nav[href^='/monitoring/klient/']" }], czekajPo: "h2:has-text('Rekordy')" },
  { n: "trener-wiadomosci", rola: "trener", url: "/wiadomosci", czekaj: "h1" },
  { n: "trener-powiadomienia", rola: "trener", url: "/powiadomienia", czekaj: "h1", siec: "load" },
  { n: "trener-wiecej", rola: "trener", url: "/wiecej", czekaj: "h1:has-text('Więcej')" },
  // admin (1280 px)
  { n: "admin-panel", rola: "admin", url: "/admin", czekaj: "h1" },
  { n: "admin-wiecej", rola: "admin", url: "/wiecej", czekaj: "h1:has-text('Więcej')" },
];

const VIEWPORT = { klient: { width: 375, height: 812 }, trener: { width: 1280, height: 800 },
  admin: { width: 1280, height: 800 }, pub: { width: 375, height: 812 } };

// — serwer (własny, chyba że DZIK_ZRZUTY_URL wskazuje działający) —
let server = null;
let url = process.env.DZIK_ZRZUTY_URL || "";
if (!url) {
const tmp = mkdtempSync(join(tmpdir(), "dzik-zrzuty-"));
const env = {
  ...process.env,
  DZIK_DATABASE_URL: `sqlite:///${tmp}/e2e.db`,
  DZIK_AUDIT_DB: `${tmp}/audit.db`,
  DZIK_UPLOAD_DIR: `${tmp}/uploads`,
  DZIK_ENV: "test",
  DZIK_BCRYPT_ROUNDS: "4",
  DZIK_FRONTEND_DIST: DIST,
  DZIK_MFA_REQUIRED_ROLES: "",
  DZIK_MONITORING_TAB_ENABLED: "true",
  DZIK_DIET_TEMPLATES_ENABLED: "true",
  DZIK_CALORIE_INTERVIEW_ENABLED: "true",
  DZIK_WIEDZA_SZKICE: "true",
  DZIK_DIET_WIZARD_ENABLED: "true",
};
execFileSync("python3", ["-m", "dzik_os.seed"], { env, cwd: tmp });
const port = process.env.DZIK_ZRZUTY_PORT ? Number(process.env.DZIK_ZRZUTY_PORT) : await freePort();
server = spawn("python3",
  ["-m", "uvicorn", "dzik_os.main:app", "--host", "127.0.0.1", "--port", String(port)],
  { env, cwd: tmp, stdio: "ignore" });
url = `http://127.0.0.1:${port}`;
for (let i = 0; i < 150; i++) {
  try { const r = await fetch(`${url}/api/health`); if (r.ok) break; }
  catch { await new Promise((ok) => setTimeout(ok, 200)); }
}
}

async function login(page, [email, password]) {
  await page.goto(`${url}/login`, { waitUntil: "networkidle" });
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button:has-text('Zaloguj się')");
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 });
  await page.waitForLoadState("networkidle");
}

// id klienta A z listy trenera (API) — do tras karty klienta.
async function idKlientaA() {
  const r = await fetch(`${url}/api/auth/login`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: KONTA.trener[0], password: KONTA.trener[1] }),
  });
  const { token } = await r.json();
  const lista = await (await fetch(`${url}/api/coach/clients`, { headers: { Authorization: `Bearer ${token}` } })).json();
  const rows = Array.isArray(lista) ? lista : lista.clients ?? lista.items ?? [];
  const a = rows.find((c) => (c.client_email || c.email) === KONTA.klient[0]) || rows[0];
  return a?.client_id || a?.id || a?.client?.id;
}

const browser = await chromium.launch({ executablePath: CHROMIUM, args: ["--no-sandbox"] });
let bledy = 0, zrobione = 0;
try {
  const klientId = await idKlientaA();
  for (const motyw of MOTYWY) {
    mkdirSync(join(OUT, motyw), { recursive: true });
    const konteksty = {};
    async function kontekst(rola) {
      const k = rola || "pub";
      if (konteksty[k]) return konteksty[k];
      // Service worker zablokowany: zrzuty mają pokazywać to, co serwuje serwer
      // (przy podmianie dist/ SW podałby zbuforowaną powłokę poprzedniego wariantu).
      const ctx = await browser.newContext({ viewport: VIEWPORT[k], reducedMotion: "reduce", locale: "pl-PL",
        timezoneId: "Europe/Warsaw", serviceWorkers: "block" });
      if (motyw !== "ciemny") {
        await ctx.addInitScript((m) => { try { localStorage.setItem("dzik_theme", m); } catch { /* prywatne okno */ } }, motyw);
      }
      const page = await ctx.newPage();
      if (rola) await login(page, KONTA[rola]);
      konteksty[k] = { ctx, page };
      return konteksty[k];
    }
    for (const e of EKRANY) {
      if (TYLKO && !TYLKO.has(e.n)) continue;
      for (const w of WARIANTY) {
      const katalog = w.nazwa ? join(OUT, motyw, w.nazwa) : join(OUT, motyw);
      mkdirSync(katalog, { recursive: true });
      try {
        if (w.dist) podmienDist(w.dist);
        const { page } = await kontekst(e.rola);
        await page.goto(`${url}${e.url.replace("{klient}", klientId ?? "")}`, { waitUntil: e.siec ?? "networkidle" });
        await page.waitForSelector(e.czekaj, { timeout: 15000 });
        for (const k of e.klik ?? []) {
          if (k.sel) await page.locator(k.sel).first().click();
          else await page.getByRole(k.rola, { name: k.nazwa }).first().click();
        }
        if (e.czekajPo) await page.waitForSelector(e.czekajPo, { timeout: 15000 });
        if (!e.siec) await page.waitForLoadState("networkidle");
        // Animacje wejścia kart (card-in) muszą się skończyć, inaczej zrzut
        // łapie półprzezroczystą kartę i porównanie pikselowe kłamie.
        await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => null))));
        // Przewinięcie do dołu i z powrotem: obrazy `loading="lazy"` zaczynają się
        // ładować dopiero w pobliżu widoku (pełnostronicowy zrzut ich nie budzi).
        await page.evaluate(async () => {
          const krok = Math.max(300, window.innerHeight);
          for (let y = 0; y < document.documentElement.scrollHeight; y += krok) { window.scrollTo(0, y); await new Promise((ok) => setTimeout(ok, 30)); }
          window.scrollTo(0, 0);
        });
        // Obrazy ładowane leniwie (galeria strony publicznej, zdjęcie trenera)
        // muszą być zdekodowane — inaczej pierwszy zrzut ma puste ramki.
        // (z limitem czasu: obraz `loading="lazy"` poza ekranem nigdy nie zacznie
        // się ładować, a decode() czekałby na niego w nieskończoność)
        await page.evaluate(() => Promise.race([
          Promise.all([...document.images].map((i) => (i.complete ? null : i.decode().catch(() => null)))),
          new Promise((ok) => setTimeout(ok, 3000)),
        ]));
        await page.waitForTimeout(e.siec ? 1200 : 300);
        await page.screenshot({ path: join(katalog, `${e.n}.png`), fullPage: true });
        zrobione++;
        console.log(`  ${motyw}/${w.nazwa ? w.nazwa + "/" : ""}${e.n}.png`);
      } catch (err) {
        bledy++;
        console.error(`  BŁĄD ${motyw}/${w.nazwa}${e.n}: ${String(err).split("\n")[0]}`);
      }
      }
    }
    for (const { ctx } of Object.values(konteksty)) await ctx.close();
  }
} finally {
  await browser.close();
  server?.kill();
}
console.log(`\nZrzuty: ${zrobione}, błędy: ${bledy} → ${OUT}`);
process.exit(bledy ? 1 : 0);

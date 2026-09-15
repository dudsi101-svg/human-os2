// E2E dostępności i responsywności (Playwright + Chromium, Node).
//
// Preferowane narzędzie: axe-core wstrzykiwane do strony (jeśli pakiet jest
// dostępny lokalnie lub globalnie). Gdy axe-core nie jest zainstalowany,
// test wykonuje WŁASNE asercje pokrywające kluczowe kontrakty rundy
// dostępności:
//   1. html[lang], viewport bez blokady powiększania,
//   2. skip-link jako pierwszy element fokusowalny + landmarki main/nav,
//   3. każde pole formularza ma etykietę (label[for] / aria-label /
//      aria-labelledby / label opakowujący / title),
//   4. porządek nagłówków h1→h2→h3 bez przeskoków,
//   5. brak poziomego scrolla strony na 320/375/768/1024 px,
//   6. etykiety nawigacji >= 12 px; obszary dotykowe nawigacji >= 44 px,
//   7. zakładki (WAI-ARIA Tabs): role, aria-selected, obsługa strzałek,
//   8. wykresy Sparkline mają role="img" i dostępną nazwę,
//   9. ekran logowania mieści się na niskim ekranie (landscape telefonu).
//
// Uruchomienie (wymaga wcześniejszego `npm run build` we frontend/ oraz
// zainstalowanego pakietu backendu — jak istniejące e2e):
//   NODE_PATH=/opt/node22/lib/node_modules node e2e/test_a11y.mjs
// Ścieżkę Chromium można nadpisać przez DZIK_E2E_CHROMIUM.
// DZIK_THEME=czerwony (0.74.0) uruchamia ten sam zestaw w jasnym motywie
// czerwono-białym — motyw ustawiany tak, jak robi to aplikacja
// (localStorage["dzik_theme"] przed nawigacją); CI ma dwa przebiegi.

import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import net from "node:net";

function loadModule(name) {
  const candidates = [
    import.meta.url,
    ...(process.env.NODE_PATH ? [join(process.env.NODE_PATH, "/")] : []),
    "/opt/node22/lib/node_modules/",
  ];
  for (const base of candidates) {
    try {
      return createRequire(base)(name);
    } catch {
      /* następny kandydat */
    }
  }
  return null;
}

const playwright = loadModule("playwright");
if (!playwright) {
  console.error("Nie znaleziono pakietu playwright (lokalnie ani globalnie).");
  process.exit(1);
}
const { chromium } = playwright;

// axe-core: opcjonalne — źródło do wstrzyknięcia, jeśli pakiet jest dostępny.
let axeSource = null;
for (const base of [import.meta.url, "/opt/node22/lib/node_modules/"]) {
  try {
    const req = createRequire(base);
    axeSource = readFileSync(req.resolve("axe-core/axe.min.js"), "utf8");
    break;
  } catch {
    /* brak axe-core — użyjemy własnych asercji */
  }
}

const APP_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DIST = join(APP_DIR, "frontend", "dist");
// Backend z TEGO drzewa roboczego, nie z zainstalowanego pakietu. Serwer
// startuje z katalogu tymczasowego (świeża baza), więc bez tego `python -m`
// importowałby `dzik_os` z site-packages — czyli kod SPRZED zmian rundy,
// a test dostępności milcząco sprawdzałby nie tę aplikację (`e2e/serve.sh`
// robi to samo przez `cd "$BACKEND"`).
const BACKEND = join(APP_DIR, "backend");
// Motyw (0.74.0): "ciemny" (domyślny, bez atrybutu) albo "czerwony".
const MOTYW = process.env.DZIK_THEME || "ciemny";
if (!["ciemny", "czerwony"].includes(MOTYW)) {
  console.error(`Nieznany DZIK_THEME=${MOTYW} (ciemny|czerwony).`);
  process.exit(1);
}
const CHROMIUM =
  process.env.DZIK_E2E_CHROMIUM ||
  (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined);

if (!existsSync(join(DIST, "index.html"))) {
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

// — serwer: dist + świeża baza z seedem —
const tmp = mkdtempSync(join(tmpdir(), "dzik-a11y-e2e-"));
const env = {
  ...process.env,
  DZIK_DATABASE_URL: `sqlite:///${tmp}/e2e.db`,
  DZIK_AUDIT_DB: `${tmp}/audit.db`,
  DZIK_UPLOAD_DIR: `${tmp}/uploads`,
  DZIK_ENV: "test",
  DZIK_BCRYPT_ROUNDS: "4",
  DZIK_FRONTEND_DIST: DIST,
  // Test dostępności loguje trenera bez przechodzenia konfiguracji TOTP —
  // wymóg MFA dla ról jest testowany osobno w backendzie (test_mfa).
  DZIK_MFA_REQUIRED_ROLES: "",
  // Zakładka Postępy/Monitoring (0.66.0) — docelowy stan nawigacji:
  // klient ma „Postępy” zamiast „Raportu”, trener szóstą pozycję „Monitoring”.
  DZIK_MONITORING_TAB_ENABLED: "true",
  // Wywiad kaloryczny (0.62.0, wyrównany w 0.77.0) — na produkcji włączony;
  // sekcja 4c ogląda kartę bilansu, która bez tej flagi w ogóle się nie renderuje.
  DZIK_CALORIE_INTERVIEW_ENABLED: "true",
  PYTHONPATH: [BACKEND, process.env.PYTHONPATH].filter(Boolean).join(":"),
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

// ————— wspólne asercje wykonywane w przeglądarce —————

/** Pola formularzy bez dostępnej etykiety. */
const UNLABELED_JS = `(() => {
  const out = [];
  for (const el of document.querySelectorAll("input, select, textarea")) {
    if (el.type === "hidden") continue;
    const labelled =
      (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) ||
      el.getAttribute("aria-label") ||
      el.getAttribute("aria-labelledby") ||
      el.closest("label") ||
      el.getAttribute("title");
    if (!labelled) out.push(el.outerHTML.slice(0, 90));
  }
  return out;
})()`;

/** Porządek nagłówków: [poziomy] + czy są przeskoki w dół o >1. */
const HEADINGS_JS = `(() => {
  const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")]
    .filter((h) => h.offsetParent !== null || h.classList.contains("sr-only"));
  const levels = hs.map((h) => Number(h.tagName[1]));
  let skip = null;
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] > levels[i - 1] + 1) skip = levels[i - 1] + "->" + levels[i];
  }
  return { levels, skip, h1: levels.filter((l) => l === 1).length };
})()`;

async function assertNoHorizontalScroll(page, label) {
  const m = await page.evaluate(
    () => ({
      scroll: document.documentElement.scrollWidth,
      inner: window.innerWidth,
    })
  );
  check(
    `${label}: brak poziomego scrolla strony (${m.inner}px)`,
    m.scroll <= m.inner + 1,
    `scrollWidth=${m.scroll}`
  );
}

async function runAxe(page, label) {
  if (!axeSource) return;
  await page.evaluate(axeSource);
  const result = await page.evaluate(async () => {
    const r = await window.axe.run(document, {
      runOnly: ["wcag2a", "wcag2aa", "wcag22aa"],
    });
    return r.violations.map((v) => `${v.id} (${v.nodes.length})`);
  });
  check(`${label}: axe-core bez naruszeń WCAG A/AA`, result.length === 0,
    JSON.stringify(result));
}

async function login(page, email, password, expectSelector) {
  // Ponawiamy raz: pierwsze wejście po starcie serwera bywa wolniejsze
  // (zimny backend + hydratacja SPA) — pojedynczy klik potrafi trafić
  // przed podpięciem handlera formularza.
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.goto(`${url}/login`, { waitUntil: "networkidle" });
    await page.fill("#email", email);
    await page.fill("#password", password);
    await page.click("button:has-text('Zaloguj się')");
    try {
      await page.waitForSelector(expectSelector, { timeout: 20000 });
      return;
    } catch (e) {
      if (attempt === 1) throw e;
    }
  }
}

const browser = await chromium.launch({
  executablePath: CHROMIUM,
  args: ["--no-sandbox"],
});
/** Kontekst przeglądarki z motywem z DZIK_THEME (jasny = wpis w localStorage
 * przed pierwszą nawigacją, dokładnie jak robi to sama aplikacja). */
async function nowyKontekst(opcje) {
  // reducedMotion: axe liczy kontrast z KOŃCOWYCH kolorów, nie z karty w połowie
  // animacji wejścia (card-in: opacity 0 → 1) — bez tego wynik zależał od
  // timingu (w jasnym motywie „color-contrast (10)” na monitoringu klienta,
  // niereprodukowalne przy ponownym wejściu na ten sam ekran).
  const ctx = await browser.newContext({ ...opcje, reducedMotion: "reduce" });
  if (MOTYW !== "ciemny") {
    await ctx.addInitScript((m) => { try { localStorage.setItem("dzik_theme", m); } catch { /* brak magazynu */ } }, MOTYW);
  }
  return ctx;
}
let exitCode = 1;
try {
  console.log(axeSource
    ? "axe-core dostępny — audyt automatyczny + asercje własne"
    : "axe-core niedostępny w środowisku — działają asercje własne");
  console.log(`Motyw: ${MOTYW}`);

  // ————— 1. Ekran logowania (320×568 — najwęższy wspierany) —————
  console.log("1. Ekran logowania (320 px)");
  const ctx320 = await nowyKontekst({ viewport: { width: 320, height: 568 } });
  const login320 = await ctx320.newPage();
  await login320.goto(`${url}/login`, { waitUntil: "networkidle" });

  const docMeta = await login320.evaluate(() => ({
    lang: document.documentElement.lang,
    viewport: document.querySelector('meta[name="viewport"]')?.content ?? "",
  }));
  check("html[lang=pl]", docMeta.lang === "pl", docMeta.lang);
  // Motyw obowiązuje już na /login (z urządzenia): atrybut, kolor tła i paska.
  const motywDoc = await login320.evaluate(() => ({
    atrybut: document.documentElement.getAttribute("data-theme"),
    tlo: getComputedStyle(document.body).backgroundColor,
    meta: document.querySelector('meta[name="theme-color"]')?.content,
  }));
  check(
    `motyw ${MOTYW}: atrybut, tło i theme-color zgodne`,
    MOTYW === "ciemny"
      ? motywDoc.atrybut === null && motywDoc.tlo === "rgb(11, 13, 15)" && motywDoc.meta === "#0b0d0f"
      : motywDoc.atrybut === "czerwony" && motywDoc.tlo === "rgb(255, 255, 255)" && motywDoc.meta === "#FFFFFF",
    JSON.stringify(motywDoc)
  );
  check(
    "viewport nie blokuje powiększania (bez maximum-scale/user-scalable=no)",
    !/maximum-scale|user-scalable\s*=\s*no/i.test(docMeta.viewport),
    docMeta.viewport
  );
  await assertNoHorizontalScroll(login320, "logowanie");
  const unlabeledLogin = await login320.evaluate(UNLABELED_JS);
  check("logowanie: wszystkie pola mają etykiety", unlabeledLogin.length === 0,
    JSON.stringify(unlabeledLogin));
  const h1Login = await login320.evaluate(HEADINGS_JS);
  check("logowanie: dokładnie jeden h1", h1Login.h1 === 1, JSON.stringify(h1Login));
  await runAxe(login320, "logowanie");

  // — niski ekran (landscape telefonu): formularz logowania osiągalny —
  console.log("2. Logowanie w orientacji poziomej (844×390)");
  const ctxLand = await nowyKontekst({ viewport: { width: 844, height: 390 } });
  const landPage = await ctxLand.newPage();
  await landPage.goto(`${url}/login`, { waitUntil: "networkidle" });
  // W jasnym motywie pełne logo jest schowane, a znak marki to blok
  // .login-brand--czerwony (znak 56 px + nazwa) — mierzymy to, co widać.
  const logoH = await landPage.evaluate(() => {
    const el = [...document.querySelectorAll(".login-logo, .login-brand--czerwony")]
      .find((e) => e.getBoundingClientRect().height > 0);
    return el ? el.getBoundingClientRect().height : 0;
  });
  check("landscape: logo zmniejszone (≤ 120 px wysokości)", logoH > 0 && logoH <= 120,
    String(logoH));
  const passVisible = await landPage.evaluate(() => {
    const el = document.querySelector("#password");
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.top >= 0 && r.top < window.innerHeight + window.innerHeight; // w zasięgu 2 ekranów
  });
  check("landscape: pole hasła osiągalne bez walki z układem", passVisible);
  await ctxLand.close();

  // ————— 3. Klient: Dzisiaj — landmarki, skip-link, nawigacja —————
  console.log("3. Klient — Dzisiaj (375 px)");
  const ctxClient = await nowyKontekst({ viewport: { width: 375, height: 812 } });
  const page = await ctxClient.newPage();
  await login(page, "klient.a@example.com", "KlientA#2026!x", "h1:has-text('Dzisiaj')");

  const landmarks = await page.evaluate(() => ({
    main: !!document.querySelector("main#main"),
    nav: !!document.querySelector("nav[aria-label]"),
    skip: (() => {
      const a = document.querySelector("a.skip-link");
      return a ? a.getAttribute("href") : null;
    })(),
  }));
  check("landmark main#main", landmarks.main);
  check("landmark nav z aria-label", landmarks.nav);
  check("skip-link celuje w #main", landmarks.skip === "#main", String(landmarks.skip));

  // skip-link jest pierwszym elementem w porządku fokusu
  await page.evaluate(() => { document.activeElement?.blur?.(); });
  await page.keyboard.press("Tab");
  const firstFocus = await page.evaluate(() =>
    document.activeElement?.className ?? ""
  );
  check("skip-link pierwszy w porządku fokusu", firstFocus.includes("skip-link"),
    firstFocus);

  const navMetrics = await page.evaluate(() => {
    const links = [...document.querySelectorAll("nav a")];
    return links.map((a) => {
      const cs = getComputedStyle(a);
      const r = a.getBoundingClientRect();
      return { fs: parseFloat(cs.fontSize), h: r.height, w: r.width };
    });
  });
  check(
    "nawigacja: etykiety >= 12 px",
    navMetrics.every((m) => m.fs >= 12),
    JSON.stringify(navMetrics.map((m) => m.fs))
  );
  check(
    "nawigacja: obszar dotykowy >= 44 px",
    navMetrics.every((m) => m.h >= 44 && m.w >= 44),
    JSON.stringify(navMetrics.map((m) => [m.w, m.h]))
  );

  const hToday = await page.evaluate(HEADINGS_JS);
  check("Dzisiaj: jeden h1, bez przeskoków nagłówków",
    hToday.h1 === 1 && hToday.skip === null, JSON.stringify(hToday));
  await runAxe(page, "Dzisiaj");

  // brak poziomego scrolla na kluczowych szerokościach
  console.log("4. Szerokości 320/375/768/1024 — Dzisiaj, Raport, Płatności, Wywiad");
  for (const width of [320, 375, 768, 1024]) {
    await page.setViewportSize({ width, height: 850 });
    for (const [path, sel] of [
      ["/", "h1:has-text('Dzisiaj')"],
      ["/plan", "h1:has-text('Plan treningowy')"],
      ["/raport", "h1:has-text('Raport tygodniowy')"],
      ["/monitoring", "h1:has-text('Postępy')"],
      ["/platnosci", "h1:has-text('Płatności')"],
      ["/wywiad", "h1:has-text('Wywiad')"],
      ["/wywiad?typ=wstepny", "h1:has-text('Wywiad wstępny')"],
    ]) {
      await page.goto(`${url}${path}`, { waitUntil: "networkidle" });
      await page.waitForSelector(sel);
      await assertNoHorizontalScroll(page, `${path} @${width}`);
    }
  }

  // ————— 4a. Plan (0.75.0): „Opis ćwiczenia” rozwijany w miejscu, bez scrolla @320 —————
  console.log("4a. Plan — opis ćwiczenia rozwinięty na 320 px");
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto(`${url}/plan`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1:has-text('Plan treningowy')");
  const opisPrzyciski = await page.evaluate(() =>
    [...document.querySelectorAll("[data-testid^='opis-'] > button")].map((b) => ({
      expanded: b.getAttribute("aria-expanded"), label: b.getAttribute("aria-label") || b.textContent.trim(),
    }))
  );
  check("plan: przyciski „Opis ćwiczenia” mają aria-expanded i etykietę z nazwą",
    opisPrzyciski.length > 0 && opisPrzyciski.every((b) => b.expanded === "false" && b.label.includes(": ")),
    JSON.stringify(opisPrzyciski.slice(0, 3)));
  await page.click("[data-testid='opis-0-0'] > button");
  await page.waitForSelector("[data-testid='opis-0-0-tresc'] h3");
  check("plan: rozwinięty opis ma aria-expanded=true",
    (await page.getAttribute("[data-testid='opis-0-0'] > button", "aria-expanded")) === "true");
  await assertNoHorizontalScroll(page, "plan z rozwiniętym opisem @320");
  const hPlan = await page.evaluate(HEADINGS_JS);
  check("plan z opisem: jeden h1, bez przeskoków nagłówków",
    hPlan.h1 === 1 && hPlan.skip === null, JSON.stringify(hPlan));
  await runAxe(page, "plan z rozwiniętym opisem");

  // ————— 4c. Bilans kaloryczny (0.77.0): karta z wynikiem na 320 px —————
  // Karta pokazuje wynik dopiero po przesłaniu wywiadu, więc najpierw
  // wypełniamy go przez API (tą samą sesją co interfejs), a potem oglądamy
  // to, co naprawdę zobaczy klient: pięć kafelków, flagi i podstawienie.
  console.log("4c. Bilans kaloryczny — karta z wynikiem na 320 px");
  await page.setViewportSize({ width: 320, height: 800 });
  const wynikWywiadu = await page.evaluate(async () => {
    const token = sessionStorage.getItem("dzik_token");
    const me = JSON.parse(sessionStorage.getItem("dzik_user") || "{}");
    const h = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
    const base = `/api/clients/${me.id}/wywiady/zapotrzebowanie`;
    const rev = async () => (await (await fetch(`${base}/definicja`, { headers: h })).json()).draft?.revision ?? 1;
    const odp = {
      zk_plec: "Kobieta", zk_wiek: "30", zk_wzrost: "170", zk_masa: "70",
      zk_neat: "Siedząca — biurko, samochód, mało chodzenia (poniżej 5 000 kroków)",
      zk_sila_tydz: "3", zk_cardio_tydz: "0",
      zk_cel: "Redukcja tkanki tłuszczowej", zk_tempo: "Umiarkowane",
    };
    const patch = async (a) => (await fetch(`${base}/szkic`, {
      method: "PATCH", headers: h,
      body: JSON.stringify({ revision: await rev(), answers: Object.fromEntries(
        Object.entries(a).map(([k, v]) => [k, { value: v }])) }),
    })).json();
    await patch(odp);
    await patch({ zk_sila_minuty: "60 minut" });
    const r = await fetch(`${base}/przeslij`, {
      method: "POST", headers: h, body: JSON.stringify({ revision: await rev() }),
    });
    return { status: r.status, body: await r.text() };
  });
  check("bilans: wywiad kaloryczny przesłany przez API", wynikWywiadu.status === 201,
    wynikWywiadu.body.slice(0, 200));
  await page.goto(`${url}/wywiad`, { waitUntil: "networkidle" });
  await page.waitForSelector("[data-testid='zapotrzebowanie-kcal']");
  await assertNoHorizontalScroll(page, "wywiad z bilansem @320");
  const bilans = await page.evaluate(() => {
    const karta = document.querySelector("[data-testid='zapotrzebowanie-karta']");
    const przycisk = [...karta.querySelectorAll("button")].find((b) => b.hasAttribute("aria-expanded"));
    return {
      region: karta.getAttribute("role") === "region" && !!karta.getAttribute("aria-label"),
      kafelki: karta.querySelectorAll(".stat").length,
      // Każdy kafelek: liczba (b) i zdanie wyjaśniające (span) — sama liczba nie wystarczy.
      opisane: [...karta.querySelectorAll(".stat")].every((s) => s.querySelector("b") && s.querySelector("span")),
      expanded: przycisk?.getAttribute("aria-expanded"),
      // Cele dotyku: każdy przycisk karty co najmniej 44 px wysokości.
      male: [...karta.querySelectorAll("button, a")]
        .map((b) => ({ t: b.textContent.trim().slice(0, 30), h: Math.round(b.getBoundingClientRect().height) }))
        .filter((b) => b.h < 44),
    };
  });
  check("bilans: karta jest regionem z nazwą", bilans.region);
  check("bilans: pięć kafelków wyniku, każdy z liczbą i wyjaśnieniem",
    bilans.kafelki >= 4 && bilans.opisane, JSON.stringify(bilans));
  check("bilans: „Skąd ta liczba?” ma aria-expanded", bilans.expanded === "false", String(bilans.expanded));
  check("bilans: cele dotyku w karcie >= 44 px", bilans.male.length === 0, JSON.stringify(bilans.male));
  const hBilans = await page.evaluate(HEADINGS_JS);
  check("bilans: jeden h1, bez przeskoków nagłówków", hBilans.h1 === 1 && hBilans.skip === null,
    JSON.stringify(hBilans));
  await runAxe(page, "wywiad z bilansem @320");

  // ————— 4b. Postępy (0.66.0): nagłówki sekcji, wykresy z opisem, formularz —————
  console.log("4b. Postępy — nagłówki, opisy wykresów, etykiety pól");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${url}/monitoring`, { waitUntil: "networkidle" });
  await page.waitForSelector("h2:has-text('Sylwetka')");
  const hPostepy = await page.evaluate(HEADINGS_JS);
  check("postępy: jeden h1, bez przeskoków nagłówków",
    hPostepy.h1 === 1 && hPostepy.skip === null, JSON.stringify(hPostepy));
  const wykresyBezOpisu = await page.evaluate(() =>
    [...document.querySelectorAll(".postepy-slupki, .postepy-heat")]
      .filter((el) => !(el.getAttribute("aria-label") || "").trim()).length
  );
  check("postępy: każdy wykres słupkowy/heatmapa ma aria-label", wykresyBezOpisu === 0,
    String(wykresyBezOpisu));
  const unlabeledPostepy = await page.evaluate(UNLABELED_JS);
  check("postępy: wszystkie pola mają etykiety", unlabeledPostepy.length === 0,
    JSON.stringify(unlabeledPostepy));
  await runAxe(page, "Postępy");

  // ————— 5. Raport: etykiety pól + suwaki —————
  console.log("5. Raport tygodniowy — etykiety i suwaki");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`${url}/raport`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1:has-text('Raport tygodniowy')");
  const unlabeledCheckin = await page.evaluate(UNLABELED_JS);
  check("raport: wszystkie pola mają etykiety", unlabeledCheckin.length === 0,
    JSON.stringify(unlabeledCheckin));
  // Skale ocen to grupy przycisków (P11: bez wartości domyślnej — świadomy
  // wybór 1–5 / Pomijam / Nie dotyczy), nie suwaki: każda grupa nazwana
  // (role=group + aria-label), a stan przycisków wyrażony aria-pressed.
  const scaleGroups = await page.evaluate(() =>
    [...document.querySelectorAll('.scale-row [role="group"]')].map((el) => ({
      label: el.getAttribute("aria-label") ?? "",
      buttons: [...el.querySelectorAll("button")].filter(
        (b) => b.hasAttribute("aria-pressed")
      ).length,
    }))
  );
  check("raport: 6 skal jako nazwane grupy przycisków z aria-pressed",
    scaleGroups.length === 6 &&
      scaleGroups.every((g) => g.label.length > 2 && g.buttons >= 7),
    JSON.stringify(scaleGroups));
  await runAxe(page, "raport");

  // ————— 6. Postępy: wykresy z alternatywą tekstową —————
  // 0.66.0: stary adres /postepy prowadzi do zakładki „Postępy” (/monitoring);
  // wykresy (Sparkline) żyją teraz w sekcjach Rekordy i Sylwetka.
  console.log("6. Postępy — dostępne nazwy wykresów");
  await page.goto(`${url}/postepy`, { waitUntil: "networkidle" });
  await page.waitForSelector("h1:has-text('Postępy')");
  await page.waitForSelector("svg.spark");
  const charts = await page.evaluate(() =>
    [...document.querySelectorAll("svg.spark")].map((el) => ({
      role: el.getAttribute("role"),
      label: el.getAttribute("aria-label") ?? "",
    }))
  );
  check(
    "wykresy: role=img i sensowna dostępna nazwa",
    charts.length > 0 &&
      charts.every((c) => c.role === "img" && c.label.length > 10),
    JSON.stringify(charts.slice(0, 3))
  );
  const unlabeledProgress = await page.evaluate(UNLABELED_JS);
  check("postępy: wszystkie pola mają etykiety", unlabeledProgress.length === 0,
    JSON.stringify(unlabeledProgress));
  await ctxClient.close();

  // ————— 7. Trener: zakładki WAI-ARIA + klawiatura —————
  console.log("7. Trener — zakładki bazy wiedzy (klawiatura)");
  const ctxCoach = await nowyKontekst({ viewport: { width: 1024, height: 800 } });
  const coach = await ctxCoach.newPage();
  await login(coach, "dzik@example.com", "DzikTrener#2026", "h1:has-text('Klienci')");
  await assertNoHorizontalScroll(coach, "lista klientów @1024");

  await coach.goto(`${url}/trener/wiedza`, { waitUntil: "networkidle" });
  await coach.waitForSelector("[role='tablist']");
  const tabInfo = await coach.evaluate(() => {
    const tablist = document.querySelector("[role='tablist']");
    const tabs = [...tablist.querySelectorAll("[role='tab']")];
    return {
      label: tablist.getAttribute("aria-label"),
      selected: tabs.map((t) => t.getAttribute("aria-selected")),
      tabindex: tabs.map((t) => t.getAttribute("tabindex")),
      panel: !!document.querySelector("[role='tabpanel'][aria-labelledby]"),
    };
  });
  check("tablist z aria-label", !!tabInfo.label, String(tabInfo.label));
  check("dokładnie jedna zakładka aria-selected=true",
    tabInfo.selected.filter((s) => s === "true").length === 1,
    JSON.stringify(tabInfo.selected));
  check("roving tabindex (jedna zakładka z tabindex=0)",
    tabInfo.tabindex.filter((t) => t === "0").length === 1,
    JSON.stringify(tabInfo.tabindex));
  check("aktywny panel role=tabpanel powiązany aria-labelledby", tabInfo.panel);

  // Strzałka w prawo przenosi wybór i fokus na następną zakładkę.
  await coach.focus("[role='tab'][aria-selected='true']");
  await coach.keyboard.press("ArrowRight");
  const afterArrow = await coach.evaluate(() => ({
    focused: document.activeElement?.getAttribute("role"),
    selectedId: document.querySelector("[role='tab'][aria-selected='true']")?.id,
    focusedId: document.activeElement?.id,
  }));
  check(
    "strzałka w prawo: fokus i wybór przechodzą na następną zakładkę",
    afterArrow.focused === "tab" && afterArrow.selectedId === afterArrow.focusedId &&
      afterArrow.selectedId === "tab-cwiczenia",
    JSON.stringify(afterArrow)
  );
  const unlabeledCoach = await coach.evaluate(UNLABELED_JS);
  check("baza wiedzy trenera: wszystkie pola mają etykiety",
    unlabeledCoach.length === 0, JSON.stringify(unlabeledCoach));
  await runAxe(coach, "baza wiedzy trenera");

  // ————— 7a. Trener: Szablony (0.75.0) — nazwa jako przycisk rozwijający —————
  console.log("7a. Trener — szablony rozwijane po nazwie (1024 px)");
  await coach.goto(`${url}/trener/szablony`, { waitUntil: "networkidle" });
  await coach.waitForSelector("[data-testid='szablon-nazwa']");
  const szablony = await coach.evaluate(() =>
    [...document.querySelectorAll("[data-testid='szablon-nazwa']")].map((b) => ({
      expanded: b.getAttribute("aria-expanded"), controls: b.getAttribute("aria-controls"),
      wH2: b.closest("h2") !== null, name: b.textContent.trim(),
    }))
  );
  check("szablony: nazwa to przycisk w h2 z aria-expanded=false i aria-controls",
    szablony.length > 0 && szablony.every((s) => s.expanded === "false" && !!s.controls && s.wH2 && s.name.length > 0),
    JSON.stringify(szablony));
  await coach.click("[data-testid='szablon-nazwa']");
  const poKliku = await coach.evaluate(() => {
    const b = document.querySelector("[data-testid='szablon-nazwa']");
    return { expanded: b.getAttribute("aria-expanded"), panel: !!document.getElementById(b.getAttribute("aria-controls")) };
  });
  check("szablony: po kliknięciu aria-expanded=true i panel o wskazanym id istnieje",
    poKliku.expanded === "true" && poKliku.panel, JSON.stringify(poKliku));
  const hSzablony = await coach.evaluate(HEADINGS_JS);
  check("szablony: jeden h1, bez przeskoków nagłówków",
    hSzablony.h1 === 1 && hSzablony.skip === null, JSON.stringify(hSzablony));
  await assertNoHorizontalScroll(coach, "szablony z rozwiniętą kartą @1024");
  await runAxe(coach, "szablony trenera");

  // ————— 7b. Trener: Monitoring (lista sygnałów + widok klienta) —————
  console.log("7b. Trener — Monitoring (1024 px)");
  await coach.goto(`${url}/monitoring`, { waitUntil: "networkidle" });
  await coach.waitForSelector("h1:has-text('Monitoring')");
  await assertNoHorizontalScroll(coach, "monitoring @1024");
  const unlabeledProgi = await coach.evaluate(UNLABELED_JS);
  check("monitoring: pola progów mają etykiety", unlabeledProgi.length === 0,
    JSON.stringify(unlabeledProgi));
  await runAxe(coach, "monitoring trenera");
  await coach.click("a.card--nav[href^='/monitoring/klient/']");
  await coach.waitForSelector("h2:has-text('Rekordy')");
  const hKlient = await coach.evaluate(HEADINGS_JS);
  check("monitoring klienta: jeden h1, bez przeskoków nagłówków",
    hKlient.h1 === 1 && hKlient.skip === null, JSON.stringify(hKlient));
  await runAxe(coach, "monitoring klienta");

  // ————— 8. Trener 320 px: tabela → karty, chipy filtrów —————
  console.log("8. Trener — wąski ekran (320 px)");
  await coach.setViewportSize({ width: 320, height: 700 });
  await coach.goto(`${url}/trener`, { waitUntil: "networkidle" });
  await coach.waitForSelector("h1:has-text('Klienci')");
  await assertNoHorizontalScroll(coach, "lista klientów @320");
  const chips = await coach.evaluate(() =>
    [...document.querySelectorAll(".tabs button")].map((b) => b.getAttribute("aria-pressed"))
  );
  check("chipy filtrów mają aria-pressed", chips.length > 0 && chips.every((c) => c !== null),
    JSON.stringify(chips));

  // ————— 8a. Trener 320 px: karta „Przypisz plan” (0.76.0, bloki jak szablony) —————
  console.log("8a. Trener — karta „Przypisz plan” (320 px)");
  await coach.click("a[href^='/trener/klient/']");
  await coach.waitForSelector("[role='tab']");
  await coach.click("[role='tab']:has-text('Plan')");
  await coach.click("button:has-text('Przypisz plan (szablon i bloki)')");
  await coach.waitForSelector("[data-testid='przypisz-plan'] #pp-blok-WARMUP, [data-testid='przypisz-plan'] #pp-blok-CARDIO");
  const przypisz = await coach.evaluate(() => {
    const karta = document.querySelector("[data-testid='przypisz-plan']");
    const legend = karta?.querySelector("fieldset > legend");
    const status = karta?.querySelector("[role='status']");
    const cele = [...karta.querySelectorAll("button, input[type='radio'], select")].map((el) => {
      const r = (el.tagName === "INPUT" ? el.closest("label") ?? el : el).getBoundingClientRect();
      return { tag: el.tagName, h: Math.round(r.height) };
    });
    return { legend: legend?.textContent?.trim() ?? null, status: !!status, cele };
  });
  check("przypisz plan: fieldset z legend „Przypisz plan” i role=status",
    przypisz.legend === "Przypisz plan" && przypisz.status, JSON.stringify(przypisz));
  check("przypisz plan: przyciski, radia (z etykietą) i selecty ≥ 44 px",
    przypisz.cele.length > 0 && przypisz.cele.every((c) => c.h >= 44), JSON.stringify(przypisz.cele));
  const unlabeledPrzypisz = await coach.evaluate(UNLABELED_JS);
  check("przypisz plan: wszystkie pola mają etykiety", unlabeledPrzypisz.length === 0,
    JSON.stringify(unlabeledPrzypisz));
  await coach.click("label:has-text('Bez szablonu — tylko bloki')");
  await coach.waitForSelector("#pp-title");
  const unlabeledBloki = await coach.evaluate(UNLABELED_JS);
  check("przypisz plan (tylko bloki): pola tytułu i liczby dni mają etykiety", unlabeledBloki.length === 0,
    JSON.stringify(unlabeledBloki));
  await assertNoHorizontalScroll(coach, "karta klienta z „Przypisz plan” @320");
  const hPrzypisz = await coach.evaluate(HEADINGS_JS);
  check("karta klienta z „Przypisz plan”: jeden h1, bez przeskoków nagłówków",
    hPrzypisz.h1 === 1 && hPrzypisz.skip === null, JSON.stringify(hPrzypisz));
  await runAxe(coach, "karta klienta — Przypisz plan @320");

  exitCode = failures.length === 0 ? 0 : 1;
} catch (err) {
  console.error("Nieoczekiwany błąd testu:", err);
  exitCode = 1;
} finally {
  await browser.close();
  server.kill();
}
if (exitCode !== 0) console.error(`\nNiepowodzenia: ${failures.length || "błąd wykonania"}`);
else console.log("\nWszystkie kontrole dostępności/responsywności przeszły.");
process.exit(exitCode);

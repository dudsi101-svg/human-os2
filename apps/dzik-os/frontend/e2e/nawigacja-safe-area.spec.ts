import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Dolna nawigacja na telefonie z wcięciem systemowym (iPhone, ~34 px).
 * 0.75.1: pasek miał `height: var(--nav-h)` i padding-bottom = wcięcie przy
 * border-box, więc pole treści malało do ~28 px, a ikony były ściskane do
 * ~12 px. env() nie da się zaemulować w Chromium Playwrighta, więc wcięcie
 * jest tokenem `--safe-bottom` (styles.css), który test nadpisuje — reguły
 * .nav/.page są prawdziwe, zmienia się tylko wartość wcięcia. Projekt „telefon”.
 */
test("z wcięciem 34 px ikony nawigacji mają 22 px, a pole treści paska pełną wysokość", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);
  await expect(page.getByRole("heading", { name: "Dzisiaj" })).toBeVisible();
  // CSSOM (setProperty), nie <style>: CSP aplikacji ma style-src 'self'.
  await page.evaluate(() => document.documentElement.style.setProperty("--safe-bottom", "34px"));

  const nav = page.getByRole("navigation", { name: "Główna nawigacja" });
  const geometria = await nav.evaluate((el) => {
    const cs = getComputedStyle(el);
    const svg = el.querySelector("svg")!.getBoundingClientRect();
    const link = el.querySelector("a")!.getBoundingClientRect();
    return {
      padDol: parseFloat(cs.paddingBottom),
      tresc: el.clientHeight - parseFloat(cs.paddingBottom),
      ikona: [Math.round(svg.width), Math.round(svg.height)],
      link: Math.round(link.height),
    };
  });
  expect(geometria.padDol).toBe(34);            // wcięcie faktycznie zaemulowane
  // clientHeight nie liczy 1 px obramowania: 62 − 1.
  expect(geometria.tresc).toBeGreaterThanOrEqual(61);
  expect(geometria.ikona).toEqual([22, 22]);
  expect(geometria.link).toBeGreaterThanOrEqual(44); // cel dotyku
});

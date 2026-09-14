import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Bloki rozgrzewki i rozciągania (0.73.0).
 *
 * 1. Trener: Szablony → zakładka „Bloki” — 12 wbudowanych z seedu, „Dodaj
 *    wbudowane” jest idempotentne (komunikat „już w Twoim katalogu”).
 * 2. Klient A: dzień C planu demo ma blok „Rozgrzewka — całe ciało
 *    (początkujący)” — rozwija listę 6 pozycji z dawką, odhacza blok jako
 *    całość w formularzu wykonania; historia pokazuje „wykonano”.
 * Projekt „telefon”. Założenie: świeża baza z `serve.sh`.
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

test("trener widzi 12 bloków wbudowanych, ponowne ładowanie nic nie dubluje", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");
  await klik(page.getByRole("tab", { name: "Bloki" }));
  const tab = page.getByTestId("bloki-tab");
  await expect(tab).toBeVisible({ timeout: 15_000 });
  await expect(tab.getByTestId("blok-karta")).toHaveCount(12);
  await expect(tab).toContainText("do przeglądu trenera");
  await klik(tab.getByRole("button", { name: "Dodaj wbudowane" }));
  await expect(tab.getByRole("status")).toContainText("już w Twoim katalogu", { timeout: 15_000 });
  await expect(tab.getByTestId("blok-karta")).toHaveCount(12);
});

test("klient rozwija blok rozgrzewki i odhacza go jako całość", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/plan");
  const blok = page.getByTestId("blok-2-0");
  await expect(blok).toBeVisible({ timeout: 15_000 });
  await expect(blok).toContainText("rozgrzewka");
  await klik(blok.getByRole("button", { name: /Pokaż pozycje \(6\)/ }));
  await expect(blok.getByRole("listitem")).toHaveCount(6);
  await expect(blok).toContainText("Marsz pod górę na bieżni");
  await expect(blok).toContainText("4 min");
  await expect(blok).toContainText("Seria wprowadzająca");

  await klik(page.getByRole("button", { name: "Zapisz wykonanie z wynikami" }).nth(2));
  await page.getByTestId("blok-done-2-0").check();
  await klik(page.getByRole("button", { name: "Zapisz trening" }));
  const historia = page.getByRole("heading", { name: "Ostatnie treningi" }).locator("..");
  await expect(historia).toContainText("Rozgrzewka — całe ciało (początkujący): wykonano", { timeout: 15_000 });
});

import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Panel rozwojowy „Dzisiaj” (0.63.0): klient B (bez nawyków w seedzie) widzi
 * powitanie i hasło dnia z autorem, dodaje nawyk, odhacza go, cofa, odhacza
 * ponownie i po odświeżeniu stan wraca z serwera; trener widzi nawyk
 * w karcie klienta (Harmonogram). Projekt „telefon” (zapisuje). Założenie:
 * świeża baza z `serve.sh`; spec zostawia klientowi B jeden aktywny nawyk.
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

test("klient dodaje nawyk, odhacza i cofa; trener widzi go w karcie klienta", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientB);
  await expect(page.getByTestId("powitanie")).toHaveText(/^(Dzień dobry|Cześć|Dobry wieczór), Klient$/, { timeout: 15_000 });
  await expect(page.getByTestId("haslo-dnia")).toContainText("—");
  const panel = page.getByTestId("panel-nawykow");
  await expect(panel.getByRole("heading", { name: /Nawyki/ })).toBeVisible();

  await klik(panel.getByRole("button", { name: "Dodaj nawyk" }));
  await klik(panel.getByRole("button", { name: /\+ Dodaj nawyk/ }));
  await panel.getByLabel(/Co chcesz utrwalić/).fill("Szklanka wody po przebudzeniu");
  await panel.getByLabel(/Termin \(dni/).fill("21");
  await klik(panel.getByRole("button", { name: "Dodaj", exact: true }));
  await expect(panel.getByText("Szklanka wody po przebudzeniu")).toBeVisible({ timeout: 15_000 });
  await expect(panel.getByText(/0 z 21/)).toBeVisible();
  await klik(panel.getByRole("button", { name: "Gotowe" }));

  const odhacz = panel.getByRole("button", { name: /Odhacz na dziś: Szklanka wody/ });
  await klik(odhacz);
  await expect(panel.getByRole("button", { name: /Cofnij odhaczenie: Szklanka wody/ })).toBeVisible({ timeout: 15_000 });
  await expect(panel.getByText(/1 z 21/)).toBeVisible();
  await klik(panel.getByRole("button", { name: /Cofnij odhaczenie: Szklanka wody/ }));
  await expect(panel.getByRole("button", { name: /Odhacz na dziś: Szklanka wody/ })).toBeVisible({ timeout: 15_000 });
  await expect(panel.getByText(/0 z 21/)).toBeVisible();
  await klik(panel.getByRole("button", { name: /Odhacz na dziś: Szklanka wody/ }));
  await expect(panel.getByText(/1 z 21/)).toBeVisible({ timeout: 15_000 });

  // Dowód po odświeżeniu: stan z serwera, nie z pamięci widoku.
  await page.reload();
  await expect(page.getByTestId("panel-nawykow").getByRole("button", { name: /Cofnij odhaczenie: Szklanka wody/ })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("panel-nawykow").getByText(/1 z 21/)).toBeVisible();
  // Bez języka streaków i kar.
  await expect(page.getByTestId("panel-nawykow")).not.toContainText(/passa|z rzędu|streak/i);

  // Trener: karta klienta → Harmonogram → panel nawyków klienta.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Harmonogram" }).click();
  const panelT = page.getByTestId("panel-nawykow");
  await expect(panelT.getByText("Szklanka wody po przebudzeniu")).toBeVisible({ timeout: 15_000 });
  await expect(panelT.getByText(/1 z 21/)).toBeVisible();
});

import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Wejście do aplikacji — obie role plus dwie odmowy.
 *
 * To najtańszy test o największej wartości: jeśli logowanie przestanie
 * działać, żaden inny ekran nie ma znaczenia. Testy backendu tego nie
 * złapią — one wołają API bezpośrednio, z pominięciem formularza,
 * routingu i przekierowań.
 */

test("trener loguje się i widzi listę klientów", async ({ page }) => {
  await zaloguj(page, KONTA.trener);

  await expect(page).toHaveURL(/\/trener$/);
  await expect(page.getByRole("heading", { name: "Klienci" })).toBeVisible();
  // Lista musi mieć treść, nie tylko nagłówek — pusty panel po udanym
  // logowaniu to dokładnie ta regresja, której szukamy.
  await expect(page.locator('a[href^="/trener/klient/"]').first()).toBeVisible();
});

test("klient loguje się i widzi ekran „Dzisiaj”", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Dzisiaj" })).toBeVisible();
  await expect(page.getByRole("navigation")).toContainText("Raport");
});

test("błędne hasło nie wpuszcza i pokazuje komunikat", async ({ page }) => {
  await page.goto("/login");
  await page.fill("#email", KONTA.klientA.email);
  await page.fill("#password", "NieprawidloweHaslo#2026");
  await page.getByRole("button", { name: /zaloguj/i }).click();

  await expect(page).toHaveURL(/\/login/);
  // Komunikat jest celowo jednakowy niezależnie od istnienia konta —
  // sprawdzamy, że w ogóle się pojawia, nie jego dokładną treść.
  await expect(page.locator(".login-box")).toContainText(/nieprawidłow|błęd/i);
});

test("niezalogowany nie wchodzi do panelu trenera", async ({ page }) => {
  await page.goto("/trener");

  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator("#email")).toBeVisible();
});

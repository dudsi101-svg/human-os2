import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Gotowe schematy treningowe — droga od katalogu do własnego szablonu.
 *
 * Test idzie przez pełny cykl: katalog → podgląd → import → obecność na
 * liście szablonów trenera. Sprawdzenie samego renderu katalogu byłoby
 * słabe: najczęstsza awaria to import, który wygląda na udany, a niczego
 * nie zapisuje.
 */
test("trener przegląda katalog i dodaje schemat do swoich szablonów", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");

  const katalog = page.locator(".card", { hasText: "Gotowe schematy" });
  await expect(katalog.getByRole("heading", { name: "Gotowe schematy" })).toBeVisible();

  // Podgląd pokazuje receptę: serie/powtórzenia, cel RIR i zasadę progresji.
  await katalog.getByRole("button", { name: "Podgląd" }).first().click();
  await expect(katalog).toContainText(/RIR/, { timeout: 15_000 });
  await expect(katalog).toContainText(/progresj/i);

  await katalog.getByRole("button", { name: "Dodaj do moich" }).first().click();

  // Potwierdzenie mówi, co dokładnie powstało — nie samo „OK".
  const potwierdzenie = page.getByRole("status");
  await expect(potwierdzenie).toBeVisible({ timeout: 15_000 });
  await expect(potwierdzenie).toContainText(/Dodano/);

  // Dowód twardy: po przeładowaniu szablon przyszedł z serwera.
  await page.reload();
  await expect(
    page.locator(".card").filter({ hasText: "Start — całe ciało 2 dni" }).first(),
  ).toBeVisible({ timeout: 15_000 });
});

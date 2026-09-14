import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Flaga DZIK_MONITORING_TAB_ENABLED wyłączona (domyślny serwer E2E, jak
 * produkcja przed włączeniem): nawigacja bez zmian — klient ma „Raport”,
 * trener nie ma „Monitoringu”, a /monitoring nie istnieje (wraca na start).
 * Ten spec pilnuje, żeby 0.66.0 nie zmieniło niczego bez decyzji właściciela.
 */

test("bez flagi: Raport w nawigacji, /monitoring nie istnieje", async ({ page }) => {
  await zaloguj(page, KONTA.klientB);
  const nav = page.getByRole("navigation", { name: "Główna nawigacja" });
  await expect(nav.getByRole("link", { name: "Raport" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Postępy" })).toHaveCount(0);
  await page.goto("/monitoring");
  await expect(page.getByRole("heading", { level: 1, name: "Dzisiaj" })).toBeVisible();
  await page.goto("/postepy");
  await expect(page.getByRole("heading", { level: 1, name: "Monitoring i postępy" })).toBeVisible();
  await page.goto("/raport");
  await expect(page).toHaveURL(/\/raport$/);
  await expect(page.getByRole("heading", { level: 1, name: "Raport tygodniowy" })).toBeVisible();
});

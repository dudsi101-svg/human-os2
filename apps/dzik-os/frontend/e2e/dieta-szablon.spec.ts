import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Szablony diet ze skalowaniem (0.60.0): trener przypisuje klientowi B
 * dietę z szablonu (profil → odsłona → cel 2200 kcal → podgląd → przypisz),
 * klient widzi dzień z gramaturami i wymienia kurczaka na zamiennik
 * policzony przez serwer. Projekt „telefon” (zapisuje).
 *
 * Przyciski nisko na długiej karcie przewijamy na środek ekranu przed
 * kliknięciem (`klik`): domyślne przewinięcie Playwrighta zostawia element
 * pod stałą dolną nawigacją telefonu, a klik z `force` trafiałby w nawigację.
 * Test włącza `prefers-reduced-motion`: aplikacja wyłącza wtedy płynne
 * przewijanie i animacje kart, przez które Playwright widział element
 * „w ruchu” (kontrola stabilności nigdy nie kończyła się sukcesem).
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

test("trener przypisuje dietę z szablonu, klient wymienia produkt", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Dieta" }).click();
  await page.getByRole("button", { name: "Przypisz dietę" }).click();
  await page.getByRole("button", { name: /Standard zbilansowana/ }).click();
  await page.getByRole("button", { name: /Odsłona 1/ }).click();
  await page.getByLabel("kcal / dzień").fill("2200");
  await klik(page.getByRole("button", { name: "Przelicz tydzień" }));
  await expect(page.getByText(/Dni OK: \d\/7/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Dzień 1" })).toBeVisible();
  // Edycja gramatury inline → przeliczenie przez preview (debounce).
  await klik(page.getByRole("button", { name: "Składniki i gramatury" }).first());
  const pole = page.getByLabel(/Płatki owsiane — gramy/).first();
  await pole.fill("50");
  await expect(page.getByText(/· korekta/).first()).toBeVisible({ timeout: 10_000 });
  await klik(page.getByRole("button", { name: "Przypisz", exact: true }));
  await klik(page.getByRole("button", { name: "Tak, przypisz" }));
  await expect(page.getByText(/Przypisano dietę z szablonu \(v1, 2200 kcal\)/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("heading", { name: /Dieta z szablonu: Standard zbilansowana/ })).toBeVisible();

  // Klient: dzień z gramaturami, wymiana kurczaka.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientB);
  await page.goto("/dieta");
  await expect(page.getByRole("heading", { name: /Twoja dieta: Standard zbilansowana/ })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Banan — /)).toBeVisible();
  await expect(page.getByText(/szt\. \(~/).first()).toBeVisible();
  await klik(page.getByRole("button", { name: "Wymień Pierś z kurczaka (surowa)" }));
  await expect(page.getByText(/Pierś z indyka \(surowa\)/).first()).toBeVisible({ timeout: 15_000 });
  await klik(page.getByRole("button", { name: "Wybierz" }).first());
  await expect(page.getByText(/Wymieniono: Pierś z kurczaka \(surowa\) → Pierś z indyka/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("(wymienione)").first()).toBeVisible();

  // Trener widzi historię wymian.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Dieta" }).click();
  await klik(page.getByText(/Historia wymian klienta \(1\)/));
  await expect(page.getByText(/Pierś z kurczaka \(surowa\) \d+ g → Pierś z indyka/)).toBeVisible({ timeout: 15_000 });
});

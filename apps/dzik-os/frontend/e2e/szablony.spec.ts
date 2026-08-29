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

  // Od 0.40.0 katalog nie stoi osobno: mieszka w karcie „Dodaj szablon"
  // i pokazuje się po wybraniu drogi „Weź gotowy schemat".
  const katalog = page.locator(".card", { hasText: "Dodaj szablon" });
  await expect(katalog).toContainText("Skąd bierzesz ten szablon?");
  await katalog.getByRole("button", { name: "Weź gotowy schemat" }).click();
  await expect(katalog).toContainText(/sprawdzonych planów/, { timeout: 15_000 });

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

test("trener otwiera zakładkę Dieta i dodaje autorski szablon z katalogu", async ({ page }) => {
  // 0.54.0: szablony diety żyją obok treningowych — jeden ekran, dwie
  // zakładki. Import z katalogu tworzy własny, edytowalny szablon.
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");

  await page.getByRole("tab", { name: "Dieta" }).click();
  await expect(page.getByText("Gotowe szablony diety")).toBeVisible();
  await expect(page.getByText(/Dieta — Etap I/).first()).toBeVisible();

  await page.getByRole("button", { name: /Dodaj do moich|Dodaj ponownie/ }).first().click();
  // Szablon pojawia się na liście moich, z podglądem posiłków.
  await expect(page.getByRole("heading", { name: /Dieta — Etap I/ }).first()).toBeVisible();
  await page.getByRole("button", { name: "Podgląd" }).first().click();
  await expect(page.getByText("Przekąska (posiłek ruchomy)").first()).toBeVisible();
  await expect(page.getByText(/Ściąga zamienników/).first()).toBeVisible();
});

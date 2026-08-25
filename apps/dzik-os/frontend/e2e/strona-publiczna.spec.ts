import { expect, test } from "@playwright/test";

/**
 * Publiczna strona marketingowa (0.49.0): gość na "/" widzi wizytówkę
 * zamiast formularza logowania, może przejść do logowania i wysłać
 * zapytanie kontaktowe. Zapis jest bezpieczny dla współdzielonej bazy:
 * każde zgłoszenie tworzy osobne powiadomienie trenera (świeży id),
 * niczego nie nadpisując.
 */

test("gość widzi stronę marketingową i przechodzi do logowania", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Trening prowadzony, nie zgadywany" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Co dostajesz we współpracy" })).toBeVisible();

  await page.getByRole("link", { name: "Zaloguj się" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("E-mail")).toBeVisible();
});

test("gość wysyła zapytanie kontaktowe i widzi potwierdzenie", async ({ page }) => {
  await page.goto("/#kontakt");

  await page.getByLabel("Imię").fill("Gość Testowy");
  await page.getByLabel("E-mail").fill("gosc@example.com");
  await page.getByLabel("Wiadomość — cel, doświadczenie, pytania")
    .fill("Chcę zacząć treningi siłowe od podstaw.");
  await page.getByRole("button", { name: "Wyślij zapytanie" }).click();

  await expect(page.getByText("Dziękuję za wiadomość!")).toBeVisible();
});

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

  // Galeria ekranów (0.50.0): sekcja jest na stronie, zrzuty się ładują.
  await expect(page.getByRole("heading", { name: "Zobacz aplikację" })).toBeVisible();
  // Prawdziwy trener (0.51.0): sekcja z nazwiskiem i kontakt bezpośredni.
  await expect(page.getByRole("heading", { name: /Łukasz Drygiel/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "+48 570 477 540" })).toBeVisible();
  await expect(page.getByAltText("Dzisiaj — Twój dzień w pigułce")).toBeVisible();

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

test("gość czyta informację o przetwarzaniu danych bez logowania", async ({ page }) => {
  // Warstwowa notka RODO przy formularzu (0.53.5, audyt P0-1).
  await page.goto("/#kontakt");
  await expect(page.getByText(/Nie wpisuj w formularzu informacji o zdrowiu/)).toBeVisible();

  // Link prowadzi na publiczną trasę /prywatnosc — bez przekierowania na /login.
  await page.getByRole("link", { name: "informacja o przetwarzaniu danych", exact: true }).click();
  await expect(page).toHaveURL(/\/prywatnosc$/);
  await expect(page.getByRole("heading", { name: "Informacja o przetwarzaniu danych osobowych" })).toBeVisible();
  await expect(page.getByText(/LUBELSKI DZIK/)).toBeVisible();
  await expect(page.getByText(/Prezesa\s+Urzędu Ochrony Danych Osobowych/)).toBeVisible();

  // Wejście bezpośrednie (świeża karta) też jest publiczne.
  await page.goto("/prywatnosc");
  await expect(page.getByRole("heading", { name: "Informacja o przetwarzaniu danych osobowych" })).toBeVisible();
});

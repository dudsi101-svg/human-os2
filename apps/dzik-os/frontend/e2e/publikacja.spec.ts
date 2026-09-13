import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Panel trenera (0.58.0): Edytuj → szkic (autozapis) → odświeżenie nie gubi
 * szkicu, a klient nadal widzi stary plan → Sprawdź zmiany → Opublikuj
 * zmiany i powiadom → klient ma JEDEN wpis i ekran „Zobacz zmiany”.
 *
 * Projekt „telefon” (zapisuje). Menu działań karty musi działać bez myszki:
 * usuwamy ćwiczenie z klawiatury i sprawdzamy „Cofnij”.
 */

test("trener: szkic przetrwa odświeżenie, publikacja daje klientowi jeden wpis ze zmianami", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy A/ }).first().click();
  await page.getByRole("tab", { name: "Plan" }).click();
  await page.getByRole("button", { name: "Edytuj (szkic)" }).click();
  await expect(page.getByText("Szkic — klient jeszcze nie widzi zmian").first()).toBeVisible({ timeout: 15_000 });

  // Edycja pola: autozapis potwierdzany odpowiedzią serwera.
  const serie = page.getByLabel("Ćwiczenie 1 — serie").first();
  await serie.fill("6");
  await expect(page.getByText(/Zapisano ✓ · zmian: 1/)).toBeVisible({ timeout: 10_000 });

  // Usunięcie z klawiatury przez menu działań + Cofnij.
  const menu = page.getByRole("button", { name: /Działania: Wiosłowanie/ }).first();
  await menu.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("menuitem", { name: "Usuń ćwiczenie" }).click();
  await expect(page.getByText(/Usunięto: Wiosłowanie/)).toBeVisible();
  await expect(page.getByText(/zmian: 2/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Cofnij" }).click();
  await expect(page.getByText(/zmian: 1/)).toBeVisible({ timeout: 10_000 });

  // Odświeżenie: szkic istnieje, zmiana zachowana.
  await page.reload();
  await page.getByRole("tab", { name: "Plan" }).click();
  await page.getByRole("button", { name: /Kontynuuj szkic \(1 zm\.\)/ }).click();
  await expect(page.getByLabel("Ćwiczenie 1 — serie").first()).toHaveValue("6");

  // Sprawdź zmiany → publikuj z notatką.
  await page.getByRole("button", { name: "Sprawdź zmiany" }).click();
  await expect(page.getByText("Zmieniono 1 ćwiczenie.")).toBeVisible();
  await page.getByLabel(/Co i dlaczego zmieniłem/).fill("Progresja po raporcie");
  await page.getByRole("button", { name: "Opublikuj zmiany i powiadom" }).click();
  await expect(page.getByText(/Opublikowano wersję v3/)).toBeVisible({ timeout: 15_000 });

  // Klient: jeden wpis → Zobacz zmiany.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientA);
  await page.goto("/powiadomienia");
  const wpisy = page.getByText("Trener zaktualizował Twój plan treningowy");
  await expect(wpisy).toHaveCount(1, { timeout: 15_000 });
  await wpisy.first().click();
  await expect(page).toHaveURL(/\/zmiany\//);
  await expect(page.getByText("Zmieniono 1 ćwiczenie.")).toBeVisible();
  await expect(page.getByText("Progresja po raporcie")).toBeVisible();
  await expect(page.getByText(/sets: 4 → 6/)).toBeVisible();
  await page.getByRole("link", { name: "Otwórz aktualny plan" }).click();
  await expect(page.getByText(/wersja 3/)).toBeVisible();
});

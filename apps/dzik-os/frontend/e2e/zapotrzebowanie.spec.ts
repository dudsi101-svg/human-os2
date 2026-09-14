import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Wywiad „Zapotrzebowanie kaloryczne” (0.62.0): klient A wypełnia formularz
 * (pola liczbowe z przecinkiem, pytanie warunkowe o tempo), przesyła i widzi
 * wynik z podstawieniem w zakładkach Wywiad i Dieta; trener widzi ten sam
 * wynik w karcie klienta, nadpisuje go z powodem, a w „Przypisz dietę”
 * przycisk „Zaproponuj kcal” wypełnia pole kcal ustaleniem trenera.
 * Projekt „telefon” (zapisuje).
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

test("klient liczy zapotrzebowanie, trener nadpisuje i proponuje kcal w diecie", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/wywiad?typ=zapotrzebowanie");
  await expect(page.getByRole("heading", { name: "Zapotrzebowanie kaloryczne" }).first()).toBeVisible({ timeout: 15_000 });

  await page.getByRole("radiogroup", { name: /^Płeć/ }).getByRole("radio", { name: "Kobieta" }).click();
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  await page.getByLabel(/Wiek \(lata\)/).fill("30");
  await page.getByLabel(/Wzrost \(cm\)/).fill("170");
  await page.getByLabel(/Aktualna masa ciała/).fill("70,0");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole("radiogroup", { name: /charakter pracy/ }).getByRole("radio", { name: /Siedząca/ }).click();
  await page.getByRole("radiogroup", { name: /Ile treningów/ }).getByRole("radio", { name: /3–4 treningi/ }).click();
  // Pytanie warunkowe: tempo pojawia się dopiero po wyborze redukcji.
  await expect(page.getByRole("radiogroup", { name: /tempo redukcji/ })).toHaveCount(0);
  await page.getByRole("radiogroup", { name: /Jaki jest cel/ }).getByRole("radio", { name: /Redukcja/ }).click();
  await page.getByRole("radiogroup", { name: /tempo redukcji/ }).getByRole("radio", { name: /Umiarkowane/ }).click();
  await page.getByRole("radiogroup", { name: /zaburzenia odżywiania/ }).getByRole("radio", { name: "Nie zgłaszam" }).click();
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });

  const przeslij = page.getByRole("button", { name: "Prześlij trenerowi" });
  await expect(przeslij).toBeEnabled({ timeout: 15_000 });
  await klik(przeslij);
  await expect(page.getByText(/Przesłano wersję 1/)).toBeVisible({ timeout: 15_000 });
  // Wynik: K 70 kg / 170 cm / 30 lat, PAL 1,35, −15 % → 1670 kcal.
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1670 kcal/, { timeout: 15_000 });
  await expect(page.getByText(/PPM \(Mifflin-St Jeor, kobieta\)/)).toBeVisible();
  await page.goto("/dieta");
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1670 kcal/, { timeout: 15_000 });

  // Trener: karta klienta → Wywiad → nadpisanie z powodem.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy A/ }).first().click();
  await page.getByRole("tab", { name: "Wywiad" }).click();
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1670 kcal/, { timeout: 15_000 });
  await klik(page.getByRole("button", { name: "Nadpisz wynik" }));
  await page.getByLabel(/kcal \/ dzień \(Twoja decyzja\)/).fill("1800");
  await page.getByLabel(/Powód \(klient go zobaczy\)/).fill("Pierwszy tydzień łagodniej.");
  await klik(page.getByRole("button", { name: "Zapisz", exact: true }));
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await expect(page.getByText(/Ustalone przez trenera/)).toBeVisible();

  // Dieta → Przypisz dietę → „Zaproponuj kcal” wypełnia pole ustaleniem trenera.
  await page.getByRole("tab", { name: "Dieta" }).click();
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await klik(page.getByRole("button", { name: "Przypisz dietę" }));
  await klik(page.getByRole("button", { name: /Standard zbilansowana/ }));
  await klik(page.getByRole("button", { name: /Odsłona 1/ }));
  await klik(page.getByRole("button", { name: "Zaproponuj kcal" }));
  await expect(page.getByLabel("kcal / dzień")).toHaveValue("1800");
  await expect(page.getByLabel(/Masa ciała \(kg/)).toHaveValue("70");

  // Klient widzi ustalenie trenera i powód.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientA);
  await page.goto("/dieta");
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await expect(page.getByText(/Pierwszy tydzień łagodniej/)).toBeVisible();
});

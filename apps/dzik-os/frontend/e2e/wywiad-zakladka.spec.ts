import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Zakładka „Wywiad” (0.59.0): klient wypełnia część wywiadu wstępnego
 * (autozapis potwierdzony przez serwer), odświeżenie nic nie gubi,
 * przesyła; trener widzi „wywiad do przejrzenia” na liście, w karcie
 * klienta przegląda odpowiedzi i prosi o uzupełnienie; klient dostaje
 * jeden wpis i widzi prośbę przy pytaniu. Projekt „telefon” (zapisuje).
 */

test("klient przesyła wywiad wstępny, trener prosi o uzupełnienie", async ({ page }) => {
  await zaloguj(page, KONTA.klientB);
  await page.goto("/wywiad");
  await expect(page.getByRole("heading", { name: "Wywiad wstępny" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Rozpocznij" }).first().click();

  // Autozapis: „Zapisano ✓” dopiero po odpowiedzi serwera.
  await page.getByLabel(/Od czego zaczniemy/).fill("Wrócić do formy po przerwie");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });

  // Pytanie warunkowe: „Tak” odsłania opis urazu.
  const urazy = page.getByRole("radiogroup", { name: /przebyte urazy/ });
  await urazy.getByRole("radio", { name: "Tak" }).click();
  await expect(page.getByLabel(/Opisz krótko, czego dotyczą/)).toBeVisible({ timeout: 10_000 });

  // Odświeżenie: szkic wraca z serwera, status „szkic”.
  await page.reload();
  await expect(page.getByLabel(/Od czego zaczniemy/)).toHaveValue("Wrócić do formy po przerwie", { timeout: 15_000 });

  // Wymagane odpowiedzi wyboru (pierwsza opcja każdego radia z etykietą „wymagane”).
  for (const label of [/doświadczenie z treningiem/, /Ile dni w tygodniu/, /Gdzie i na czym/, /Czy coś boli Cię teraz/, /kontaktować z trenerem/]) {
    await page.getByRole("radiogroup", { name: label }).getByRole("radio").first().click();
    await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  }
  await page.getByRole("radiogroup", { name: /potwierdzoną alergię/ }).getByRole("radio", { name: "Nie zgłaszam" }).click();
  await page.getByLabel(/Jak dziś wygląda Twoje jedzenie/).fill("2 posiłki, dużo w biegu");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Zapisz szkic" }).click();

  // Prześlij: gdy czegoś brakuje, serwer wskaże braki; uzupełniamy i wysyłamy.
  const przeslij = page.getByRole("button", { name: "Prześlij trenerowi" });
  await expect(przeslij).toBeEnabled({ timeout: 15_000 });
  await przeslij.click();
  await expect(page.getByText(/Przesłano wersję 1/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("przesłany").first()).toBeVisible();

  // Trener: lista → odznaka → karta → Wywiad → Przejrzyj → Poproś o uzupełnienie.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await expect(page.getByText("wywiad do przejrzenia").first()).toBeVisible({ timeout: 15_000 });
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Wywiad" }).click();
  await expect(page.getByRole("heading", { name: "Wywiad wstępny" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Przejrzyj" }).first().click();
  await expect(page.getByText("Wrócić do formy po przerwie").first()).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Poproś o uzupełnienie" }).first().click();
  await page.getByRole("button", { name: /Od czego zaczniemy/ }).click();
  await page.getByLabel("Wiadomość dla klienta").fill("Doprecyzuj proszę cel — do kiedy?");
  await page.getByRole("button", { name: "Wyślij prośbę" }).click();
  await expect(page.getByText(/Wysłano prośbę o uzupełnienie/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("wymaga doprecyzowania").first()).toBeVisible();

  // Klient: jeden wpis + prośba przy pytaniu.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientB);
  await page.goto("/powiadomienia");
  await expect(page.getByText("Trener prosi o uzupełnienie wywiadu")).toHaveCount(1, { timeout: 15_000 });
  await page.goto("/wywiad?typ=wstepny");
  await expect(page.getByText("trener prosi o doprecyzowanie").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Doprecyzuj proszę cel — do kiedy?").first()).toBeVisible();
});

import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Kreator dań (0.57.0) — przepływ P0 z instrukcji pakietu: trener podaje
 * parametry i poświadczenia zakresu, dostaje podgląd kulinarny ze szkiców
 * (jawnie bez wartości odżywczych), zagląda do receptury i listy zakupów,
 * zapisuje menu klientowi po jawnym potwierdzeniu; klient widzi posiłki
 * i „Dlaczego to danie?” z zapisanego śladu decyzji (bez generowania).
 *
 * Zapis zmienia bieżącą wersję diety klienta A — dlatego test jest w
 * projekcie „telefon” (jedyny, który zapisuje) i sprawdza treść po swojej
 * stronie, nie zakładając stanu innych testów.
 */

test("trener: układa menu z dań, zapisuje je; klient widzi Dlaczego to danie?", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/wiedza");
  await page.getByRole("tab", { name: "Dieta" }).click();
  await page.getByRole("button", { name: "Ułóż z dań" }).click();
  await expect(page.getByText(/Receptury: 300/)).toBeVisible({ timeout: 15_000 });

  await page.getByLabel(/^Klient/).selectOption({ label: "Klient Testowy A" });
  await page.getByLabel("Dni").fill("2");
  await page.getByLabel("Produkty zwierzęce").selectOption("vegan");
  for (const t of ["klient jest osobą dorosłą", "nie jest w ciąży ani nie karmi piersią",
    "nie ma zaleconej diety leczniczej", "nie ma cukrzycy ani leków wpływających na glikemię"]) {
    await page.getByLabel(t).check();
  }
  await page.getByRole("button", { name: "Policz menu" }).click();
  await expect(page.getByText("Podgląd kulinarny (szkice)")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Dzień 1 ·")).toBeVisible();

  // Receptura i lista zakupów są dostępne z podglądu.
  await page.getByRole("button", { name: "Receptura" }).first().click();
  await expect(page.getByText(/Składniki:/).first()).toBeVisible();
  await page.getByText(/Lista zakupów \(/).click();

  // Zapis podglądu ze szkiców wymaga jawnego potwierdzenia.
  await page.getByRole("button", { name: "Zapisz jako wersję planu diety" }).click();
  await expect(page.getByText(/zaznacz potwierdzenie/)).toBeVisible();
  await page.getByLabel(/Rozumiem, że to podgląd ze szkiców/).check();
  await page.getByRole("button", { name: "Zapisz jako wersję planu diety" }).click();
  await expect(page.getByText(/Zapisano jako wersja v\d+/)).toBeVisible({ timeout: 15_000 });

  // Klient: posiłki z menu i wyjaśnienie z zapisanego śladu.
  // Sesja żyje w sessionStorage — zmiana konta bez klikania po nawigacji trenera.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientA);
  await page.goto("/dieta");
  await expect(page.getByRole("heading", { name: "Menu z kreatora dań" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("szkic").first()).toBeVisible();
  await page.getByRole("button", { name: "Dlaczego to danie?", exact: true }).first().click();
  const panel = page.getByRole("dialog");
  await expect(panel).toContainText("Decyzja:");
  await expect(panel.getByRole("button", { name: /Wygeneruj/ })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
});

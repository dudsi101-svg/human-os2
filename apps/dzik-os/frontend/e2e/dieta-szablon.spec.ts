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
  // Wymiany v2 rankują po poziomie i wpływie na posiłek, więc indyk nie musi być pierwszy — wybieramy go po nazwie.
  await klik(page.getByRole("listitem").filter({ hasText: "Pierś z indyka (surowa)" }).getByRole("button", { name: "Wybierz" }));
  await expect(page.getByText(/Wymieniono: Pierś z kurczaka \(surowa\) → Pierś z indyka/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("(wymienione)").first()).toBeVisible();

  // Wymiany v2 (0.69.0): warzywo z rolą NONE ma przycisk (na `main` 0.64.0 nie miało),
  // zamiennik 1:1 wagowo z tej samej grupy i deltą posiłku po polsku.
  await klik(page.getByRole("button", { name: "Wymień Brokuł" }));
  const arkuszBrokul = page.getByRole("dialog", { name: /Zamienniki: Brokuł/ });
  await expect(arkuszBrokul.getByText("z tej samej grupy").first()).toBeVisible({ timeout: 15_000 });
  await expect(arkuszBrokul.getByText(/posiłek: [−+]?\d+ kcal/).first()).toBeVisible();
  await klik(arkuszBrokul.getByRole("button", { name: "Wybierz" }).first());
  await expect(page.getByText(/Wymieniono: Brokuł → /)).toBeVisible({ timeout: 15_000 });

  // Poziom 2: awokado (dzień 2) było singletonem bez zamiennika — teraz grupa pokrewna.
  await klik(page.getByRole("tab", { name: "Dzień 2" }));
  await klik(page.getByRole("button", { name: "Wymień Awokado" }));
  const arkuszAwokado = page.getByRole("dialog", { name: /Zamienniki: Awokado/ });
  await expect(arkuszAwokado.getByText(/grupa pokrewna: (orzechy|tłuszcz)/).first()).toBeVisible({ timeout: 15_000 });
  await klik(arkuszAwokado.getByRole("button", { name: "Wybierz" }).first());
  await expect(page.getByText(/Wymieniono: Awokado → /)).toBeVisible({ timeout: 15_000 });

  // Trener widzi historię wymian z poziomem.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Dieta" }).click();
  await klik(page.getByText(/Historia wymian klienta \(3\)/));
  await expect(page.getByText(/Pierś z kurczaka \(surowa\) \d+ g → Pierś z indyka/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("grupa pokrewna").first()).toBeVisible();
  await expect(page.getByText("ta sama grupa").first()).toBeVisible();
});

/**
 * Biblioteka 0.64.0: profil „Sportowa wysokobiałkowa” ma 5 slotów (dwa
 * obiady — etykiety „obiad I” / „obiad II”), a odsłona niesie notatki autora
 * biblioteki (suplementacja, sód) widoczne trenerowi przed przeliczeniem.
 */
test("trener widzi 5 slotów profilu Sportowa i notatki odsłony", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy B/ }).first().click();
  await page.getByRole("tab", { name: "Dieta" }).click();
  await klik(page.getByRole("button", { name: "Przypisz dietę" }));
  await page.getByRole("button", { name: /Sportowa wysokobiałkowa/ }).click();
  await page.getByRole("button", { name: /Odsłona 1/ }).click();
  await expect(page.getByText("Uwagi o suplementacji:")).toBeVisible({ timeout: 15_000 });
  await page.getByLabel("kcal / dzień").fill("2600");
  await klik(page.getByRole("button", { name: "Przelicz tydzień" }));
  await expect(page.getByText(/Dni OK: \d\/7/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/^obiad I: /).first()).toBeVisible();
  await expect(page.getByText(/^obiad II: /).first()).toBeVisible();
  await expect(page.getByText(/^obiad_1/)).toHaveCount(0);
});

import { expect, Locator, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Cardio z suwakami (0.73.0).
 *
 * 1. Trener (telefon): karta Anny Wilk (klient demo bez planu) → Plan → „+ Nowy
 *    plan” → w dniu „+ Cardio”: odpowiada na bramkę zdrowotną, podaje wiek,
 *    „Policz propozycję” → tabela zakresów → „Wstaw do dnia” → pozycja z odznaką
 *    „cardio” w edytorze → „Utwórz plan” → karta klienta pokazuje pozycję cardio.
 * 2. Klient A (plan demo: dzień C ma cardio rowerek/wioślarz): w Planie wybiera
 *    wioślarz, zapisuje wykonanie 25 min / RPE 6, historia pokazuje wpis cardio
 *    bez kilogramów; „Dlaczego takie cardio?” czyta zapisany ślad H_CARDIO.
 * Projekt „telefon” (zapisuje). Założenie: świeża baza z `serve.sh`.
 */

const KLIENT_D = { email: "anna.wilk@example.com", haslo: "KlientD#2026!x" };

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

async function kartaAnny(page: Page) {
  await page.goto("/trener");
  await klik(page.getByRole("link", { name: /Anna Wilk/ }).first());
  await expect(page).toHaveURL(/\/trener\/klient\//, { timeout: 15_000 });
  await klik(page.getByRole("tab", { name: "Plan" }));
}

test("trener liczy propozycję cardio z suwaków i wstawia ją do nowego planu", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  await kartaAnny(page);
  await klik(page.getByRole("button", { name: "+ Nowy plan" }));
  await page.fill("#pe-title", "Cardio z suwaków — test");
  await page.fill("#pe-reason", "Test E2E: propozycja z suwaków");
  await page.fill("#pe-day-name-0", "Dzień cardio");
  await page.fill("#pe-ex-0-0", "Przysiad ze sztangą");

  // 0.76.0: obok jest „+ Cardio z bloku” — dopasowanie dokładne, żeby nie było dwóch trafień.
  await klik(page.getByRole("button", { name: "+ Cardio", exact: true }));
  const panel = page.getByTestId("cardio-panel");
  await expect(panel).toBeVisible({ timeout: 15_000 });
  // Suwak: Redukcja na 60 % zabiera pozostałym — suma zostaje 100.
  await panel.locator("#suwak-redukcja").fill("60");
  await expect(panel.getByTestId("waga-redukcja")).toHaveText("60 %");
  await expect(panel.getByTestId("waga-wydolnosc")).toHaveText("20 %");
  await expect(panel.getByTestId("waga-regeneracja")).toHaveText("20 %");
  // Bramka zdrowotna: siedem odpowiedzi „nie” (bez odpowiedzi nie ma propozycji).
  for (const nie of await panel.getByRole("button", { name: "nie", exact: true }).all()) await klik(nie);
  await panel.locator("#cardio-age").fill("35");
  await klik(panel.getByTestId("cardio-policz"));
  const wynik = panel.getByTestId("cardio-wynik");
  await expect(wynik).toBeVisible({ timeout: 15_000 });
  await expect(wynik).toContainText("RPE / 10");
  await expect(wynik).toContainText("Rowerek stacjonarny");
  await klik(panel.getByTestId("cardio-wstaw"));
  const pozycja = page.getByTestId("pe-pozycja-0-1");
  await expect(pozycja).toContainText("cardio");
  await expect(pozycja).toContainText("R 60 % / W 20 % / G 20 %");

  await klik(page.getByRole("button", { name: "Utwórz plan" }));
  await expect(page.getByRole("heading", { name: "Cardio z suwaków — test" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("R 60 % / W 20 % / G 20 %")).toBeVisible();
});

test("klient wybiera wioślarz, zapisuje 25 min / RPE 6, widzi wpis i „Dlaczego?”", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/plan");
  const cardio = page.getByTestId("cardio-2-3");
  await expect(cardio).toBeVisible({ timeout: 15_000 });
  await expect(cardio.getByTestId("cardio-2-3-zakresy")).toContainText("% HRmax");
  await expect(cardio).toContainText("bilans energii");
  await cardio.locator("#cardio-2-3-urzadzenie").selectOption("wioslarz");
  await expect(cardio).toContainText("uderzenia");

  await klik(page.getByRole("button", { name: "Zapisz wykonanie z wynikami" }).nth(2));
  const log = page.getByTestId("cardio-log-2-3");
  await expect(log).toContainText("Wioślarz");
  await log.getByLabel(/czas w minutach/).fill("25");
  await log.getByLabel(/RPE/).fill("6");
  await klik(page.getByRole("button", { name: "Zapisz trening" }));
  const historia = page.getByRole("heading", { name: "Ostatnie treningi" }).locator("..");
  await expect(historia).toContainText("Wioślarz · 25 min · RPE 6", { timeout: 15_000 });
  // Najnowszy wpis (dzisiejszy) to cardio bez kilogramów; starsze wpisy demo są siłowe.
  const dzisiejszy = historia.locator(".exercise").first();
  await expect(dzisiejszy).toContainText("Wioślarz · 25 min · RPE 6");
  await expect(dzisiejszy).not.toContainText("kg×");

  await klik(cardio.getByRole("button", { name: "Dlaczego takie cardio?" }));
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Wyjaśnienie z zapisanej decyzji", { timeout: 15_000 });
  await expect(dialog).toContainText("Redukcja 50 %");
  await expect(dialog).toContainText("nie wynik badania");
});

test("klient D po publikacji widzi pozycję cardio na Planie", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KLIENT_D);
  await page.goto("/plan");
  const cardio = page.getByTestId("cardio-0-1");
  await expect(cardio).toBeVisible({ timeout: 15_000 });
  await expect(cardio.getByTestId("cardio-0-1-cele")).toHaveAttribute("aria-label", "Redukcja 60 %, Wydolność 20 %, Regeneracja 20 %");
});

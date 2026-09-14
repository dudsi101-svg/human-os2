import { expect, Locator, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Bloki jak szablony (0.76.0).
 *
 * 1. Trener (telefon): karta Piotra Zająca (klient demo bez planu) → Plan →
 *    „Przypisz plan” → szablon „Push/Pull/Legs” + rozgrzewka + aeroby +
 *    rozciąganie → komunikat „Dodano rozgrzewkę do 3 dni, cardio do 3 dni,
 *    rozciąganie do 3 dni”. Klient na `/plan` widzi w dniu 1 rozgrzewkę na
 *    górze, cardio „z bloku” i rozciąganie na dole.
 * 2. Trener: „bez szablonu — tylko bloki”, 2 dni, aeroby + rozciąganie →
 *    klient widzi nowy plan z dwoma dniami po dwie pozycje.
 * Projekt „telefon” (zapisuje). Założenie: świeża baza z `serve.sh`; konto
 * Piotra nie jest używane przez inne testy (nowy plan zmienia jego `/plan`).
 */

const KLIENT_E = { email: "piotr.zajac@example.com", haslo: "KlientE#2026!x" };

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

/** Wybór opcji selecta po fragmencie etykiety (Playwright nie przyjmuje wzorca w `label`). */
async function wybierz(select: Locator, fragment: string) {
  const value = await select.locator("option", { hasText: fragment }).first().getAttribute("value");
  expect(value, `brak opcji zawierającej „${fragment}”`).toBeTruthy();
  await select.selectOption(value!);
}

async function kartaPiotra(page: Page) {
  await page.goto("/trener");
  await klik(page.getByRole("link", { name: /Piotr Zając/ }).first());
  await expect(page).toHaveURL(/\/trener\/klient\//, { timeout: 15_000 });
  await klik(page.getByRole("tab", { name: "Plan" }));
  await klik(page.getByRole("button", { name: "Przypisz plan (szablon i bloki)" }));
  const karta = page.getByTestId("przypisz-plan");
  await expect(karta).toBeVisible({ timeout: 15_000 });
  return karta;
}

test("trener przypisuje szablon + rozgrzewkę + aeroby + rozciąganie; klient widzi kolejność w dniu", async ({ page, browser }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  const karta = await kartaPiotra(page);
  await karta.locator("#pp-szablon").selectOption({ label: "Szablon: Push/Pull/Legs" });
  await wybierz(karta.locator("#pp-blok-WARMUP"), "Rozgrzewka — całe ciało (początkujący)");
  await wybierz(karta.locator("#pp-blok-CARDIO"), "Aeroby — regeneracja (początkujący)");
  await wybierz(karta.locator("#pp-blok-STRETCH"), "Rozciąganie po treningu — całe ciało");
  const podsumowanie = karta.getByTestId("pp-podsumowanie");
  await expect(podsumowanie).toContainText("Szablon „Szablon: Push/Pull/Legs” + rozgrzewka");
  await expect(podsumowanie).toContainText("aeroby (cardio) „Aeroby — regeneracja (początkujący)”");
  await expect(podsumowanie).toContainText("→ 3 dni");
  await klik(karta.getByRole("button", { name: "Przypisz klientowi" }));
  await expect(karta.getByTestId("pp-status")).toContainText(
    "Dodano rozgrzewkę do 3 dni, cardio do 3 dni, rozciąganie do 3 dni", { timeout: 15_000 });
  // Karta klienta pokazuje nowy plan z pozycjami z bloków.
  await expect(page.getByRole("heading", { name: "Szablon: Push/Pull/Legs" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("tr-blok-0-0")).toContainText("rozgrzewka");

  // Klient (osobny kontekst): dzień 1 = rozgrzewka na górze, cardio z bloku i rozciąganie na dole.
  const ctx = await browser.newContext();
  const klient = await ctx.newPage();
  await klient.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(klient, KLIENT_E);
  await klient.goto("/plan");
  await expect(klient.getByText("Szablon: Push/Pull/Legs").first()).toBeVisible({ timeout: 15_000 });
  const blok = klient.getByTestId("blok-0-0");
  await expect(blok).toContainText("rozgrzewka");
  await expect(blok).toContainText("Rozgrzewka — całe ciało (początkujący)");
  // Kolejność pozycji nie-siłowych w dniu 1 po `data-testid` (pod-elementy `-cele`/`-zakresy`/`-blok` odpadają na wzorcu).
  const testidy = await klient.locator("[data-testid^='blok-0-'], [data-testid^='cardio-0-']")
    .evaluateAll((els) => els.map((e) => e.getAttribute("data-testid")));
  const glowne = testidy.filter((t) => /^(blok|cardio)-0-\d+$/.test(t ?? ""));
  expect(glowne.length).toBe(3);
  expect(glowne[0]).toBe("blok-0-0");
  expect(glowne[1]).toMatch(/^cardio-0-/);
  expect(glowne[2]).toMatch(/^blok-0-/);
  const cardio = klient.getByTestId(glowne[1]!);
  await expect(cardio).toContainText("z bloku");
  await expect(cardio.getByTestId(`${glowne[1]}-blok`)).toContainText("Aeroby (cardio) · początkujący · ≈20 min");
  await expect(cardio.getByTestId(`${glowne[1]}-cele`)).toHaveAttribute("aria-label", "Redukcja 0 %, Wydolność 0 %, Regeneracja 100 %");
  await expect(cardio).toContainText("prowadź według RPE i testu mowy");
  await expect(klient.getByTestId(glowne[2]!)).toContainText("rozciąganie");
  await ctx.close();
});

test("trener tworzy plan „tylko bloki” na 2 dni; klient widzi dwa dni po aeroby + rozciąganie", async ({ page, browser }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  const karta = await kartaPiotra(page);
  await klik(karta.getByLabel("Bez szablonu — tylko bloki"));
  await karta.locator("#pp-title").fill("Tylko aeroby i rozciąganie");
  await karta.locator("#pp-dni").fill("2");
  await wybierz(karta.locator("#pp-blok-CARDIO"), "Aeroby — wydolność (średniozaawansowany)");
  await wybierz(karta.locator("#pp-blok-STRETCH"), "Rozciąganie po treningu — dół ciała");
  await expect(karta.getByTestId("pp-podsumowanie")).toContainText("Bez szablonu + aeroby (cardio)");
  await expect(karta.getByTestId("pp-podsumowanie")).toContainText("→ 2 dni");
  await klik(karta.getByRole("button", { name: "Przypisz klientowi" }));
  await expect(karta.getByTestId("pp-status")).toContainText("Utworzono plan „Tylko aeroby i rozciąganie” z bloków. Dodano cardio do 2 dni, rozciąganie do 2 dni.", { timeout: 15_000 });

  const ctx = await browser.newContext();
  const klient = await ctx.newPage();
  await klient.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(klient, KLIENT_E);
  await klient.goto("/plan");
  await expect(klient.getByText("Tylko aeroby i rozciąganie").first()).toBeVisible({ timeout: 15_000 });
  await expect(klient.getByText("Dzień 1").first()).toBeVisible();
  await expect(klient.getByText("Dzień 2").first()).toBeVisible();
  for (const di of [0, 1]) {
    const cardio = klient.getByTestId(`cardio-${di}-0`);
    await expect(cardio).toContainText("z bloku");
    await expect(cardio).toContainText("6×2 min / przerwa 2 min");
    await expect(klient.getByTestId(`blok-${di}-1`)).toContainText("rozciąganie");
  }
  await ctx.close();
});

/**
 * Przegląd PR #79, P1: edycja bloku aerobowego zostawiała w formularzu stary
 * czas i stare pozycje opisowe, więc po zmianie celu blok reklamował się
 * sprzecznie (nagłówek „≈40 min”, a preset liczył 25 min) i ta sprzeczność
 * szła migawką do planu klienta. Po poprawce zmiana celu czyści oba pola,
 * a serwer wypełnia je presetem.
 */
test("zmiana celu bloku aerobowego przelicza czas i pozycje opisowe", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");
  await klik(page.getByRole("tab", { name: "Bloki" }));
  const tab = page.getByTestId("bloki-tab");
  await expect(tab).toBeVisible({ timeout: 15_000 });

  // Blok wbudowany „redukcja / średniozaawansowany”: ciągła 40 min.
  const karta = tab.getByTestId("blok-karta")
    .filter({ hasText: "Aeroby — redukcja (średniozaawansowany)" }).first();
  await expect(karta).toContainText("≈40 min");
  await klik(karta.getByRole("button", { name: "Edytuj" }));

  const formularz = page.getByTestId("blok-formularz");
  await expect(formularz).toBeVisible();
  await expect(formularz.locator("#bl-duration")).toHaveValue("40");
  await formularz.locator("#bl-goal").selectOption("regeneracja");
  // Zmiana celu czyści oba pola — puste znaczy „policz presetem”.
  await expect(formularz.locator("#bl-duration")).toHaveValue("");
  await expect(formularz.locator("#bl-items")).toHaveValue("");
  await klik(formularz.getByRole("button", { name: "Zapisz blok" }));

  const po = tab.getByTestId("blok-karta")
    .filter({ hasText: "Aeroby — redukcja (średniozaawansowany)" }).first();
  await expect(po).toContainText("≈25 min", { timeout: 15_000 });
  await expect(po).not.toContainText("≈40 min");
});

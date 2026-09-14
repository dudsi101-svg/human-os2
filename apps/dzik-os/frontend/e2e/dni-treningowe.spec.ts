import { expect, Locator, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Dni treningowe (0.71.0): klient B (plan „Masa — FBW 3x/tydz.”, propozycja
 * trenera wt./czw./sob., wersja bez `id` → klucze `idx:n`) ustawia w karcie
 * „Twoje dni treningowe” DZISIEJSZY dzień tygodnia dla „FBW 1”, pozostałe
 * na „—”, zapisuje; po odświeżeniu odznaki mówią „(Twój wybór)”, a „Dzisiaj”
 * pokazuje „FBW 1” z etykietą „Twój wybór”; „Wróć do propozycji trenera”
 * przywraca odznaki „(propozycja trenera)”. Drugi scenariusz: dwie jednostki
 * w ten sam dzień → komunikat przy polu, nic nie zapisane. Projekt „telefon”
 * (zapisuje). Założenie: świeża baza z `serve.sh`.
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

/** Dzisiejszy dzień tygodnia ISO (1 = pon … 7 = niedz) liczony w strefie
 * serwera E2E (`Europe/Warsaw`), nie w strefie runnera. */
function dzisIso(): number {
  const nazwa = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone: "Europe/Warsaw" }).format(new Date());
  return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(nazwa) + 1;
}
const WEEKDAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "niedz"];

async function otworzPlan(page: Page) {
  await page.goto("/plan");
  await expect(page.getByTestId("dni-treningowe").getByRole("heading", { name: /Twoje dni treningowe/ })).toBeVisible({ timeout: 15_000 });
}

test("klient ustawia dzisiejszy dzień dla FBW 1, „Dzisiaj” go pokazuje, powrót do propozycji trenera", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientB);
  const dzis = dzisIso();

  await otworzPlan(page);
  const karta = page.getByTestId("dni-treningowe");
  // Prefill z propozycji trenera: wt./czw./sob.
  await expect(karta.getByLabel("FBW 1")).toHaveValue("2");
  await expect(karta.getByLabel("FBW 2")).toHaveValue("4");
  await expect(karta.getByLabel("FBW 3")).toHaveValue("6");
  await expect(page.getByTestId("dzien-0")).toHaveText(`${WEEKDAYS[1]} (propozycja trenera)`);

  await karta.getByLabel("FBW 1").selectOption(String(dzis));
  await karta.getByLabel("FBW 2").selectOption("");
  await karta.getByLabel("FBW 3").selectOption("");
  await klik(karta.getByRole("button", { name: "Zapisz dni" }));
  await expect(karta.getByRole("status")).toContainText("Zapisano dni", { timeout: 15_000 });

  // Dowód po odświeżeniu: stan z serwera, nie z pamięci widoku.
  await page.reload();
  await expect(page.getByTestId("dzien-0")).toHaveText(`${WEEKDAYS[dzis - 1]} (Twój wybór)`, { timeout: 15_000 });
  await expect(page.getByTestId("dzien-1")).toHaveText("— (Twój wybór)");
  await expect(page.getByTestId("dzien-2")).toHaveText("— (Twój wybór)");
  await expect(page.getByTestId("dni-treningowe").getByLabel("FBW 1")).toHaveValue(String(dzis));

  // „Dzisiaj”: trening z dzisiejszego dnia + źródło.
  await page.goto("/");
  const trening = page.getByTestId("trening-dzis");
  await expect(trening.getByRole("heading", { name: /FBW 1/ })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("zrodlo-dnia")).toHaveText("Twój wybór");
  await expect(page.getByTestId("ustaw-dni")).toHaveCount(0);

  // Powrót do propozycji trenera.
  await otworzPlan(page);
  await klik(page.getByTestId("dni-treningowe").getByRole("button", { name: "Wróć do propozycji trenera" }));
  await expect(page.getByTestId("dni-treningowe").getByRole("status")).toContainText("Wrócono do propozycji trenera", { timeout: 15_000 });
  await expect(page.getByTestId("dzien-0")).toHaveText(`${WEEKDAYS[1]} (propozycja trenera)`);
  await expect(page.getByTestId("dzien-1")).toHaveText(`${WEEKDAYS[3]} (propozycja trenera)`);
  await page.reload();
  await expect(page.getByTestId("dzien-2")).toHaveText(`${WEEKDAYS[5]} (propozycja trenera)`, { timeout: 15_000 });
  await expect(page.getByTestId("dni-treningowe").getByRole("button", { name: "Wróć do propozycji trenera" })).toHaveCount(0);
});

test("dwie jednostki tego samego dnia: komunikat przy polu, nic nie zapisane", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientB);
  await otworzPlan(page);
  const karta = page.getByTestId("dni-treningowe");
  await karta.getByLabel("FBW 1").selectOption("3");
  await karta.getByLabel("FBW 2").selectOption("3");
  await klik(karta.getByRole("button", { name: "Zapisz dni" }));
  const blad = karta.getByRole("alert");
  await expect(blad).toContainText("FBW 1", { timeout: 15_000 });
  await expect(blad).toContainText("jeden dzień tygodnia to jedna jednostka");
  await expect(karta.getByLabel("FBW 2")).toHaveAttribute("aria-invalid", "true");
  // Nic nie zapisane: po odświeżeniu nadal propozycja trenera.
  await page.reload();
  await expect(page.getByTestId("dzien-0")).toHaveText(`${WEEKDAYS[1]} (propozycja trenera)`, { timeout: 15_000 });
  await expect(page.getByTestId("dni-treningowe").getByRole("button", { name: "Wróć do propozycji trenera" })).toHaveCount(0);
});

import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Zakładka „Postępy” / „Monitoring” (0.66.0) — projekt `telefon-postepy`, czyli
 * drugi serwer z DZIK_MONITORING_TAB_ENABLED=true (patrz playwright.config.ts).
 *
 * Klient A ma w seedzie trzy sesje z progresją przysiadu (95 → 100 → 105 kg),
 * więc rekord z ostatnich 30 dni istnieje bez zapisywania czegokolwiek. Test
 * dopisuje jeden pomiar wagi i sprawdza, że licznik pomiarów rośnie po
 * odświeżeniu (dowód z serwera). Trener wchodzi w listę sygnałów i w widok
 * klienta. Bez wpisów typu „streak”, bez czerwieni — to sprawdza a11y/spec.
 */

test("klient widzi Postępy zamiast Raportu, rekord z seedu i dopisuje pomiar", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  const nav = page.getByRole("navigation", { name: "Główna nawigacja" });
  await expect(nav.getByRole("link", { name: "Postępy" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Raport" })).toHaveCount(0);

  await nav.getByRole("link", { name: "Postępy" }).click();
  await expect(page).toHaveURL(/\/monitoring$/);
  await expect(page.getByRole("heading", { level: 1, name: "Postępy" })).toBeVisible();
  // Kafelki tygodnia zawsze w tej samej kolejności.
  const kafelki = page.getByRole("list", { name: "Ten tydzień" }).getByRole("listitem");
  await expect(kafelki).toHaveCount(3);
  await expect(kafelki.nth(0)).toContainText("Treningi");
  await expect(kafelki.nth(1)).toContainText("Konsekwencja");
  await expect(kafelki.nth(2)).toContainText("Trend wagi");
  for (const h of ["Rekordy", "Trening", "Konsekwencja", "Sylwetka"]) {
    await expect(page.getByRole("heading", { level: 2, name: h })).toBeVisible();
  }
  // Rekord ciężaru z seedu: przysiad 105 kg (poprzednio 100 kg), w wstędze 30 dni.
  const wstega = page.getByLabel("Rekordy z ostatnich 30 dni");
  await expect(wstega).toContainText("Przysiad ze sztangą");
  await expect(wstega).toContainText("105 kg");
  // e1RM zawsze podpisany jako szacunek.
  await expect(page.getByText(/Szacowany 1RM/).first()).toBeVisible();

  // Pomiar wagi: licznik rośnie o 1 po odświeżeniu (stan z serwera).
  const licznik = page.getByTestId("waga-pomiary");
  const przed = Number((await licznik.textContent())?.match(/\d+/)?.[0] ?? "0");
  await page.getByLabel("Rodzaj").selectOption("weight");
  await page.getByRole("textbox", { name: "Wartość" }).fill("84,5");
  await page.getByRole("button", { name: "Zapisz pomiar" }).click();
  await expect(licznik).toContainText(String(przed + 1), { timeout: 15_000 });
  await page.reload();
  await expect(page.getByTestId("waga-pomiary")).toContainText(String(przed + 1), { timeout: 15_000 });

  // Raport tygodniowy nie znika: stary adres przekierowuje do „Więcej”.
  await page.goto("/raport");
  await expect(page).toHaveURL(/\/wiecej\/raport$/);
  await expect(page.getByRole("heading", { level: 1, name: "Raport tygodniowy" })).toBeVisible();
  await page.goto("/wiecej");
  await expect(page.getByRole("link", { name: /Raport tygodniowy/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: /^Postępy$/ })).toBeVisible();
  // Stary adres /postepy prowadzi do nowej zakładki.
  await page.goto("/postepy");
  await expect(page).toHaveURL(/\/monitoring$/);
});

test("trener ma zakładkę Monitoring z sygnałami i wchodzi w widok klienta", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  const nav = page.getByRole("navigation", { name: "Główna nawigacja" });
  await nav.getByRole("link", { name: "Monitoring" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Monitoring" })).toBeVisible();
  const karta = page.getByRole("link", { name: /Klient Testowy A/ });
  await expect(karta).toBeVisible();
  await expect(karta).toContainText(/Frekwencja 4 tyg\./);
  await karta.click();
  await expect(page).toHaveURL(/\/monitoring\/klient\//);
  await expect(page.getByRole("heading", { level: 1, name: "Monitoring klienta" })).toBeVisible();
  for (const h of ["Rekordy", "Trening", "Konsekwencja"]) {
    await expect(page.getByRole("heading", { level: 2, name: h })).toBeVisible();
  }
  await expect(page.getByLabel("Rekordy z ostatnich 30 dni")).toContainText("Przysiad ze sztangą");
  await expect(page.getByRole("link", { name: "Karta klienta" })).toHaveAttribute("href", /\/trener\/klient\//);
});

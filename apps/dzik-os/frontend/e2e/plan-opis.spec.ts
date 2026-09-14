import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Opis ćwiczenia z Wiedzy w planie klienta (0.75.0, polecenie właściciela).
 *
 * Klient A, plan „Redukcja — siła 3x/tydz.”: dzień A ma pozycję z `exercise_id`
 * („Wyciskanie sztangi leżąc”) i pozycję TYLKO po nazwie („Wiosłowanie hantlem
 * w podporze” — seed bez identyfikatora, jak z importu pliku). Obie rozwijają
 * skrót w miejscu; link „Pełny opis w Wiedzy” prowadzi do pełnej karty i wraca
 * do planu. Trzeci przypadek: nazwa spoza bazy — uczciwy komunikat, nie pusta
 * karta (sprawdzane przez API w `test_exercises_by_name.py`; tutaj UI).
 * Projekt „telefon”; nic nie zapisuje.
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

test("klient rozwija opis ćwiczenia z planu, przechodzi do Wiedzy i wraca", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/plan");
  await expect(page.getByText("Redukcja — siła 3x/tydz.")).toBeVisible({ timeout: 15_000 });

  // Pozycja z identyfikatorem: skrót w miejscu.
  const opis = page.getByTestId("opis-0-0");
  const przycisk = opis.getByRole("button", { name: /Opis ćwiczenia: Wyciskanie sztangi leżąc/ });
  await expect(przycisk).toHaveAttribute("aria-expanded", "false");
  await klik(przycisk);
  const tresc = page.getByTestId("opis-0-0-tresc");
  await expect(tresc).toContainText("Technika w punktach", { timeout: 15_000 });
  await expect(tresc).toContainText("Najczęstsze błędy");
  await expect(tresc).toContainText("Mięśnie:");
  await expect(opis.getByRole("button", { name: /Ukryj opis/ })).toHaveAttribute("aria-expanded", "true");

  // Pełna karta w Wiedzy — z powrotem do planu.
  await klik(tresc.getByRole("link", { name: "Pełny opis w Wiedzy" }));
  await expect(page).toHaveURL(/\/wiedza\?.*cwiczenie=/);
  const karta = page.getByTestId("karta-cwiczenia");
  await expect(karta.getByRole("heading", { name: "Wyciskanie sztangi leżąc" })).toBeVisible({ timeout: 15_000 });
  await expect(karta).toContainText("Technika — krok po kroku");
  await expect(karta).toContainText("Pracujące mięśnie");
  // Fokus po wejściu ląduje na przycisku powrotu.
  await expect(karta.getByRole("link", { name: "Wróć do planu" }).first()).toBeFocused();
  await klik(karta.getByRole("link", { name: "Wróć do planu" }).first());
  await expect(page).toHaveURL(/\/plan$/);
  await expect(page.getByRole("heading", { name: "Plan treningowy" })).toBeVisible();
});

test("klient dostaje opis po nazwie dla pozycji bez identyfikatora", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/plan");
  await expect(page.getByText("Redukcja — siła 3x/tydz.")).toBeVisible({ timeout: 15_000 });
  const opis = page.getByTestId("opis-0-1");
  await klik(opis.getByRole("button", { name: /Opis ćwiczenia: Wiosłowanie hantlem w podporze/ }));
  const tresc = page.getByTestId("opis-0-1-tresc");
  await expect(tresc).toContainText("Wiosłowanie hantlem w podporze", { timeout: 15_000 });
  await expect(tresc).toContainText("Technika w punktach");
  await expect(tresc.getByRole("link", { name: "Pełny opis w Wiedzy" })).toHaveAttribute("href", /cwiczenie=HOS-EXC-/);
});

test("karta ćwiczenia spoza bazy mówi wprost, że jej nie ma", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);
  await page.goto("/wiedza?czesc=training&cwiczenie=HOS-EXC-NIEISTNIEJACE&powrot=/plan");
  const karta = page.getByTestId("karta-cwiczenia");
  await expect(karta).toContainText("nie ma już w bazie trenera", { timeout: 15_000 });
  await expect(karta.getByRole("link", { name: "Wróć do planu" })).toBeVisible();
});

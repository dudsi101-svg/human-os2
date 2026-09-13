import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Wiedza (0.56.0) — dwa obowiązkowe przepływy z pliku 02 pakietu:
 *
 * 1. Plan → „Dlaczego?” przy ćwiczeniu → karta wiedzy w panelu → powrót do
 *    TEJ SAMEJ sesji (otwarty formularz zapisu treningu nie znika, fokus
 *    wraca do przycisku). Plan z seedu powstał bez śladu decyzji, więc
 *    panel musi uczciwie pokazać brak zapisanego uzasadnienia i zasadę
 *    ogólną — nie wymyślony powód.
 * 5. Wiedza → wyszukiwanie („zapas” trafia przez alias do karty RIR) →
 *    karta → zapisanie → widoczna w Zapisanych po przeładowaniu.
 *
 * E2E chodzi w trybie demonstracyjnym (DZIK_WIEDZA_SZKICE=true w serve.sh):
 * treści startowe są szkicami i ekran to jawnie oznacza.
 */

test("klient: Dlaczego? przy ćwiczeniu nie gubi sesji i prowadzi do karty", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);
  await page.goto("/plan");
  await expect(page.getByText("Redukcja — siła 3x/tydz.")).toBeVisible({ timeout: 15_000 });

  // Otwieramy formularz zapisu sesji — stan, który panel ma zachować.
  await page.getByRole("button", { name: "Zapisz wykonanie z wynikami" }).first().click();
  const komentarz = page.locator("#workout-comment");
  await komentarz.fill("test panelu");

  const przycisk = page.getByRole("button", { name: "Dlaczego?", exact: true }).first();
  await przycisk.click();
  const panel = page.getByRole("dialog");
  await expect(panel).toBeVisible();
  // Plan z seedu nie ma śladu: uczciwy brak + zasada ogólna (bez „wygeneruj powód”).
  await expect(panel).toContainText("Nie mamy zapisanego uzasadnienia");
  await expect(panel.getByRole("button", { name: /Wygeneruj/ })).toHaveCount(0);

  // Karta wiedzy otwiera się wewnątrz panelu.
  await panel.getByRole("button", { name: "Co oznaczają serie i powtórzenia" }).click();
  await expect(panel).toContainText("W skrócie");
  await panel.getByRole("button", { name: "Wróć do wyjaśnienia" }).click();
  await expect(panel).toContainText("Nie mamy zapisanego uzasadnienia");

  // Escape zamyka; fokus wraca do przycisku; formularz sesji nietknięty.
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(przycisk).toBeFocused();
  await expect(komentarz).toHaveValue("test panelu");
});

test("klient: wyszukuje po aliasie, otwiera kartę i zapisuje ją", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);
  await page.goto("/wiedza");
  await expect(page.getByRole("heading", { name: "Wiedza" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Zrozum swój trening i odżywianie")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Tryb demonstracyjny");

  await page.getByLabel("Czego chcesz dowiedzieć się o swoim planie?").fill("zapas");
  await page.getByRole("button", { name: "Szukaj" }).click();
  const wynik = page.getByRole("button", { name: /Jak rozumieć zapas powtórzeń/ }).first();
  await expect(wynik).toBeVisible({ timeout: 15_000 });
  await wynik.click();

  await expect(page.getByRole("heading", { name: "Jak rozumieć zapas powtórzeń" })).toBeVisible();
  await expect(page.getByText("W skrócie")).toBeVisible();
  await expect(page.getByText("Źródła")).toBeVisible();
  await page.getByRole("button", { name: "Zapisz" }).click();
  await expect(page.getByRole("button", { name: "Zapisane" })).toBeVisible();

  // Dowód twardy: zakładka przyszła z serwera po przeładowaniu.
  await page.goto("/wiedza?widok=zapisane");
  await expect(page.getByText("Jak rozumieć zapas powtórzeń")).toBeVisible({ timeout: 15_000 });
});

test("trener: redakcja kart pokazuje szkice i liczbę opublikowanych", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/wiedza");
  await page.getByRole("tab", { name: "Karty wiedzy" }).click();
  await expect(page.getByText("Karty wiedzy — redakcja")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/szkic: \d+/)).toBeVisible();
  await expect(page.getByText(/Pokrycie typów elementów planu/)).toBeVisible();
});

import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Głęboki wywiad — drugi przepływ ekranu rozmowy (scenariusz serwerowy,
 * dzik_os/interview_flow.py). Test przechodzi prawdziwą ścieżką klienta:
 * wejście z menu „Więcej", start, krok informacyjny, pierwsza odpowiedź
 * i pominięcie — z asercją, że postęp idzie do przodu, a przeładowanie
 * strony wraca dokładnie w to samo miejsce (stan żyje na serwerze).
 */

test("klient zaczyna głęboki wywiad, odpowiada i wznawia po przeładowaniu", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);

  // Wejście jak człowiek: Więcej → Głęboki wywiad.
  await page.goto("/wiecej");
  await page.getByRole("link", { name: "Głęboki wywiad" }).click();
  await expect(page).toHaveURL(/\/wywiad/);
  await expect(page.getByRole("heading", { name: "Porozmawiajmy głębiej" }))
    .toBeVisible({ timeout: 15_000 });

  // Start rozmowy → krok informacyjny (intro scenariusza).
  await page.getByRole("button", { name: "Zacznijmy" }).click();
  await expect(page.locator(".card", { hasText: "głęboki wywiad" }).first())
    .toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Dalej" }).click();

  // Pierwsze prawdziwe pytanie (moduł „Cel głębiej") — odpowiadamy.
  await expect(page.getByText("Cel głębiej").first()).toBeVisible({ timeout: 15_000 });
  await page.locator("textarea").fill("Wbiegam po schodach bez zadyszki.");
  await page.getByRole("button", { name: "Dalej" }).click();

  // Skala ważności — pominięcie też jest pełnoprawną odpowiedzią.
  await page.getByRole("button", { name: "Pomiń to pytanie" }).click();

  // Postęp: intro + odpowiedź + pominięcie = 3 reakcje.
  await expect(page.getByText(/^3 z \d+/)).toBeVisible({ timeout: 15_000 });

  // Twardy dowód, że stan jest serwerowy: przeładowanie wraca w to samo
  // miejsce rozmowy, niczego nie gubiąc.
  await page.reload();
  await expect(page.getByText(/^3 z \d+/)).toBeVisible({ timeout: 15_000 });
});

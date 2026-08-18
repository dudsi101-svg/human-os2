import { expect, Page } from "@playwright/test";

/** Konta z `dzik_os.seed` — te same, na których stoi demo. */
export const KONTA = {
  trener: { email: "dzik@example.com", haslo: "DzikTrener#2026" },
  klientA: { email: "klient.a@example.com", haslo: "KlientA#2026!x" },
  // Osobne konto dla testów, które NIE mogą wysłać raportu: raport jest
  // jeden na tydzień, więc dwa testy na tym samym koncie sprzęgałyby się
  // przez kolejność uruchomienia. Rozdzielenie kont jest tańsze niż
  // resetowanie bazy między testami.
  klientB: { email: "klient.b@example.com", haslo: "KlientB#2026!x" },
} as const;

/**
 * Logowanie przez prawdziwy formularz — nie przez wstrzyknięcie tokenu.
 * Skrót po API testowałby API, które ma już własne pokrycie; tutaj chodzi
 * o to, czy człowiek jest w stanie się dostać do aplikacji.
 */
export async function zaloguj(
  page: Page,
  konto: { email: string; haslo: string },
): Promise<void> {
  await page.goto("/login");
  await page.fill("#email", konto.email);
  await page.fill("#password", konto.haslo);
  await page.getByRole("button", { name: /zaloguj/i }).click();
  // Logowanie kończy się przekierowaniem — czekamy na wyjście z /login,
  // a nie na dowolny „networkidle", który potrafi minąć przed nawigacją.
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
}

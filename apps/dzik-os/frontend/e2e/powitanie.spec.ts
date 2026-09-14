import { expect, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Powitanie po pierwszym logowaniu (0.70.0): świeże konto klienta (zaproszenie
 * → aktywacja przez API, jak `create_activated_client` w testach backendu —
 * konta demo z seedu mają znacznik już ustawiony) loguje się formularzem,
 * przechodzi bramę zgód i na „Dzisiaj” widzi dwuetapowy samouczek: krok 1 →
 * „Dalej” → krok 2 → pułapka fokusu (Tab z ostatniego przycisku wraca na
 * pierwszy) → „Rozumiem, zaczynajmy” → po odświeżeniu okna nie ma (znacznik
 * na serwerze, nie w pamięci przeglądarki) → „Więcej → Pomoc / Samouczek”
 * otwiera okno ponownie → Esc zamyka. Projekt „telefon” (zapisuje).
 */

const SWIEZY = { email: "swiezy.klient@example.com", haslo: "SwiezeHaslo#123" };

/** Brama zgód świeżego konta: warunki wymagane razem, każda opcjonalna osobno. */
async function przejdzBrameZgod(page: Page) {
  await page.getByRole("button", { name: "Potwierdzam warunki wymagane" }).click();
  for (let i = 0; i < 8; i++) {
    const zgoda = page.getByRole("button", { name: "Wyrażam zgodę" }).first();
    if (!(await zgoda.isVisible().catch(() => false))) break;
    await zgoda.click();
    await page.waitForTimeout(200);
  }
}

test("pierwsze logowanie pokazuje samouczek; zamknięty nie wraca; „Więcej” otwiera go ponownie", async ({ page, request }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });

  // Konto przez API (trener zaprasza, klient aktywuje z własnym hasłem):
  // dostawca e-maila w E2E to Null — link aktywacyjny wraca w odpowiedzi.
  const login = await request.post("/api/auth/login", {
    data: { email: KONTA.trener.email, password: KONTA.trener.haslo },
  });
  expect(login.ok()).toBeTruthy();
  const token = (await login.json()).token as string;
  const created = await request.post("/api/coach/clients", {
    headers: { Authorization: `Bearer ${token}` },
    data: { client_email: SWIEZY.email, client_name: "Świeży Klient" },
  });
  expect(created.status()).toBe(201);
  const link = (await created.json()).invitation.activation_link as string;
  const aktywacja = await request.post("/api/auth/activate", {
    data: { token: link.split("#", 2)[1], password: SWIEZY.haslo },
  });
  expect(aktywacja.ok()).toBeTruthy();

  await zaloguj(page, SWIEZY);
  await przejdzBrameZgod(page);
  await expect(page.getByRole("heading", { level: 1, name: "Dzisiaj" })).toBeVisible({ timeout: 15_000 });

  // Krok 1: dialog z nagłówkiem h2, imię z serwera, obie akcje jako przyciski.
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 15_000 });
  await expect(dialog).toHaveAttribute("aria-modal", "true");
  await expect(dialog.getByRole("heading", { level: 2, name: /Cześć, Świeży! Dobrze Cię widzieć/ })).toBeVisible();
  await expect(dialog).toContainText("Krok 1 z 2");
  await expect(dialog.getByRole("button", { name: "Pomiń na razie" })).toBeVisible();
  await dialog.getByRole("button", { name: "Dalej" }).click();

  // Krok 2 + pułapka fokusu: jedyny przycisk jest pierwszy i ostatni, więc
  // Tab z niego wraca na niego samego (fokus nie ucieka pod okno).
  await expect(dialog.getByRole("heading", { level: 2, name: "Co jeszcze warto wiedzieć" })).toBeVisible();
  await expect(dialog).toContainText("Krok 2 z 2");
  const zaczynajmy = dialog.getByRole("button", { name: "Rozumiem, zaczynajmy" });
  await zaczynajmy.focus();
  await page.keyboard.press("Tab");
  await expect(zaczynajmy).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(zaczynajmy).toBeFocused();
  await zaczynajmy.click();
  await expect(dialog).toBeHidden();

  // Znacznik jest na serwerze: po odświeżeniu okna nie ma.
  await page.reload();
  await expect(page.getByTestId("powitanie")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Ponowne otwarcie z „Więcej” → „Pomoc / Samouczek”; Esc = „Pomiń na razie”.
  await page.goto("/wiecej");
  await page.getByRole("button", { name: "Pomoc / Samouczek" }).click();
  const ponownie = page.getByRole("dialog");
  await expect(ponownie.getByRole("heading", { level: 2, name: /Cześć, Świeży/ })).toBeVisible();
  // Pułapka fokusu w kroku 1: Shift+Tab z pierwszego przycisku idzie na ostatni.
  await ponownie.getByRole("button", { name: "Dalej" }).focus();
  await page.keyboard.press("Shift+Tab");
  await expect(ponownie.getByRole("button", { name: "Pomiń na razie" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1, name: "Więcej" })).toBeVisible();
});

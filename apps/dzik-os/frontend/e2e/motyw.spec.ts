import { expect, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Motyw aplikacji (0.74.0): klient wybiera „Jasny (czerwono-biały)” w „Więcej →
 * Wygląd” → <html data-theme="czerwony"> + meta theme-color biały + znak czerwony
 * → przetrwa odświeżenie (urządzenie) → wylogowanie zostawia jasny /login
 * (świadomy wyjątek clearSession) → po ponownym zalogowaniu na CZYSTYM urządzeniu
 * (nowy kontekst) motyw wraca z konta → trener wybiera niezależnie i wraca do
 * ciemnego. A11y: grupa radiowa, strzałki przenoszą fokus bez zapisu, Enter
 * wybiera. Projekt „telefon” (zapisuje: klient B — bez kolizji z raportem).
 */

async function motyw(page: Page) {
  return page.evaluate(() => ({
    atrybut: document.documentElement.getAttribute("data-theme"),
    meta: document.querySelector('meta[name="theme-color"]')?.getAttribute("content"),
    lokalny: localStorage.getItem("dzik_theme"),
    tlo: getComputedStyle(document.body).backgroundColor,
    znakCzerwony: [...document.querySelectorAll<HTMLImageElement>("img.logo--czerwony")]
      .some((i) => i.offsetParent !== null),
  }));
}

test("wybór jasnego motywu: atrybut, meta, znak, urządzenie, konto; trener niezależnie", async ({ page, browser }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientB);
  await expect(page.getByRole("heading", { level: 1, name: "Dzisiaj" })).toBeVisible({ timeout: 15_000 });

  // Stan wyjściowy = dokładnie stan sprzed 0.74.0: bez atrybutu, ciemne tło.
  let m = await motyw(page);
  expect(m.atrybut).toBeNull();
  expect(m.meta).toBe("#0b0d0f");
  expect(m.tlo).toBe("rgb(11, 13, 15)");
  expect(m.znakCzerwony).toBe(false);

  await page.goto("/wiecej");
  const grupa = page.getByRole("radiogroup", { name: "Wygląd" });
  await expect(grupa).toBeVisible();
  const ciemny = grupa.getByRole("radio", { name: /Ciemny \(czarno-zielony\)/ });
  const jasny = grupa.getByRole("radio", { name: /Jasny \(czerwono-biały\)/ });
  await expect(ciemny).toHaveAttribute("aria-checked", "true");
  await expect(jasny).toHaveAttribute("aria-checked", "false");

  // Klawiatura: strzałka przenosi fokus, ale NIE zmienia wyboru (bez zapisu przy fokusie).
  await ciemny.focus();
  await page.keyboard.press("ArrowRight");
  await expect(jasny).toBeFocused();
  await expect(ciemny).toHaveAttribute("aria-checked", "true");
  expect((await motyw(page)).atrybut).toBeNull();

  // Enter na sfokusowanej karcie = wybór; zapis na koncie idzie w tle.
  const zapis = page.waitForResponse((r) => r.url().endsWith("/api/notifications/settings") && r.request().method() === "PUT" && r.ok());
  await page.keyboard.press("Enter");
  await zapis;
  await expect(jasny).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("status")).toContainText("Zapisano na koncie");
  m = await motyw(page);
  expect(m.atrybut).toBe("czerwony");
  expect(m.meta).toBe("#FFFFFF");
  expect(m.lokalny).toBe("czerwony");
  expect(m.tlo).toBe("rgb(255, 255, 255)");
  expect(m.znakCzerwony).toBe(true);

  // Odświeżenie: motyw z urządzenia, zanim serwer cokolwiek powie.
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Więcej" })).toBeVisible({ timeout: 15_000 });
  m = await motyw(page);
  expect(m.atrybut).toBe("czerwony");
  expect(m.tlo).toBe("rgb(255, 255, 255)");

  // Wylogowanie NIE czyści motywu: ekran logowania zostaje jasny, bez pełnego
  // logo (limonkowego) — znak + nazwa tekstem.
  // Dokładna nazwa: na „Więcej” trenera są też „Wyloguj …” w karcie sesji.
  await page.getByRole("button", { name: "Wyloguj", exact: true }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
  m = await motyw(page);
  expect(m.atrybut).toBe("czerwony");
  expect(m.lokalny).toBe("czerwony");
  await expect(page.locator(".login-logo--ciemny")).toBeHidden();
  await expect(page.locator(".login-brand--czerwony")).toBeVisible();

  // Czyste urządzenie (nowy kontekst, pusty localStorage): po zalogowaniu
  // motyw wraca z KONTA — dowód, że zapis serwerowy działa.
  const czyste = await browser.newContext(test.info().project.use);
  const strona2 = await czyste.newPage();
  await strona2.goto("/login");
  expect((await motyw(strona2)).atrybut).toBeNull();
  await zaloguj(strona2, KONTA.klientB);
  await expect(strona2.getByRole("heading", { level: 1, name: "Dzisiaj" })).toBeVisible({ timeout: 15_000 });
  m = await motyw(strona2);
  expect(m.atrybut).toBe("czerwony");
  expect(m.lokalny).toBe("czerwony");
  await czyste.close();

  // Trener wybiera dla siebie: to samo konto = ten sam wiersz, inne konto = inny.
  await zaloguj(page, KONTA.trener);
  await expect(page.getByRole("heading", { level: 1, name: "Klienci" })).toBeVisible({ timeout: 15_000 });
  // Konto trenera nie ma wyboru → zostaje motyw z urządzenia (jasny, ustawiony przez klienta B).
  expect((await motyw(page)).atrybut).toBe("czerwony");
  await page.goto("/wiecej");
  const grupaT = page.getByRole("radiogroup", { name: "Wygląd" });
  const zapisT = page.waitForResponse((r) => r.url().endsWith("/api/notifications/settings") && r.request().method() === "PUT" && r.ok());
  await grupaT.getByRole("radio", { name: /Ciemny/ }).click();
  await zapisT;
  m = await motyw(page);
  expect(m.atrybut).toBeNull();
  expect(m.meta).toBe("#0b0d0f");
  expect(m.lokalny).toBe("ciemny");
  expect(m.tlo).toBe("rgb(11, 13, 15)");

  // Klient B nadal ma jasny na koncie — wybór trenera go nie dotknął.
  // Dokładna nazwa: na „Więcej” trenera są też „Wyloguj …” w karcie sesji.
  await page.getByRole("button", { name: "Wyloguj", exact: true }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
  await zaloguj(page, KONTA.klientB);
  await expect(page.getByRole("heading", { level: 1, name: "Dzisiaj" })).toBeVisible({ timeout: 15_000 });
  expect((await motyw(page)).atrybut).toBe("czerwony");

  // Sprzątanie: klient B wraca do ciemnego (inne testy zakładają domyślny motyw).
  await page.goto("/wiecej");
  const zapisB = page.waitForResponse((r) => r.url().endsWith("/api/notifications/settings") && r.request().method() === "PUT" && r.ok());
  await page.getByRole("radiogroup", { name: "Wygląd" }).getByRole("radio", { name: /Ciemny/ }).click();
  await zapisB;
  expect((await motyw(page)).atrybut).toBeNull();
});

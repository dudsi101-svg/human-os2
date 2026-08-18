import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Wiadomości — jedyny kanał, którym klient i trener rozmawiają w aplikacji.
 *
 * Test idzie przez OBIE strony: klient pisze, trener czyta. Sprawdzenie
 * samego wysłania dowodziłoby tylko, że tekst zniknął z pola — dopiero
 * odczyt drugim kontem pokazuje, że wiadomość faktycznie przeszła przez
 * serwer i trafiła do właściwego wątku.
 */
test("klient pisze do trenera, a trener widzi wiadomość", async ({ browser }) => {
  // Treść z sygnaturą przebiegu — gdyby test kiedyś działał na
  // niewyczyszczonej bazie, nie dopasuje się do cudzej wiadomości.
  const tresc = `Wiadomość z testu E2E ${process.env.DZIK_E2E_STAMP || "lokalny"} — pytanie o rozgrzewkę.`;

  const klient = await browser.newPage();
  await zaloguj(klient, KONTA.klientA);
  await klient.goto("/wiadomosci");
  await klient.locator('a[href^="/wiadomosci/"]').first().click();

  const pole = klient.getByPlaceholder(/napisz wiadomość/i);
  await expect(pole).toBeVisible();
  await pole.fill(tresc);
  await klient.getByRole("button", { name: "Wyślij" }).click();

  // Po stronie nadawcy wiadomość ma się pojawić w wątku.
  await expect(klient.locator("#main")).toContainText(tresc, { timeout: 15_000 });

  // Druga strona: osobna sesja, osobne konto.
  const trener = await browser.newPage();
  await zaloguj(trener, KONTA.trener);
  await trener.goto("/wiadomosci");
  await trener.locator('a[href^="/wiadomosci/"]').first().click();

  await expect(trener.locator("#main")).toContainText(tresc, { timeout: 15_000 });

  await klient.close();
  await trener.close();
});

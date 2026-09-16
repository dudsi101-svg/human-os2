import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Usuwanie klientów i wybór doręczenia zaproszenia (0.79.0).
 *
 * Test ZAKŁADA WŁASNEGO klienta i jego kasuje — nie rusza kont z seeda,
 * na których stoją pozostałe testy (jedna baza SQLite, `workers: 1`).
 * Adres jest unikalny per przebieg, bo baza nie jest resetowana między
 * testami w obrębie jednego uruchomienia serwera.
 */

test("trener zaprasza z linkiem do przekazania, potem kasuje nieaktywowane konto", async ({ page }) => {
  // Okno potwierdzenia przy usuwaniu: akceptujemy, ale najpierw czytamy
  // jego treść — to ona ma mówić trenerowi prawdę o skutkach.
  let trescPytania = "";
  page.on("dialog", (d) => {
    trescPytania = d.message();
    d.accept();
  });

  await zaloguj(page, KONTA.trener);
  await expect(page.getByRole("heading", { level: 1, name: "Klienci" })).toBeVisible({ timeout: 15_000 });

  const email = `e2e.usuwanie.${Date.now()}@example.com`;
  await page.getByRole("button", { name: "+ Nowy klient" }).click();
  await page.getByLabel("Imię i nazwisko", { exact: true }).fill("Do Skasowania");
  // exact: bez tego „E-mail” trafia też w etykietę radia „Wyślij e-mail z linkiem”.
  await page.getByLabel("E-mail", { exact: true }).fill(email);

  // Wybór doręczenia: link zamiast wiadomości.
  await page.getByRole("radio", { name: /Pokaż mi link/ }).check();
  await page.getByRole("button", { name: "Utwórz i pokaż link" }).click();

  // Panel pokazuje link, a nie komunikat o wysłanym e-mailu.
  await expect(page.getByRole("heading", { name: "Link do przekazania" })).toBeVisible();
  await expect(page.getByText(/e-mail celowo nie został wysłany/)).toBeVisible();
  // Token siedzi we FRAGMENCIE (`/aktywacja#<token>`), nie w query —
  // fragment nie trafia do logów serwera ani do nagłówka Referer.
  await expect(page.getByText(/\/aktywacja#\S+/)).toBeVisible();

  // Klient jest na liście jako oczekujący na aktywację.
  const karta = page.locator(".card", { hasText: email });
  await expect(karta.getByText("oczekuje na aktywację")).toBeVisible();

  // Usunięcie: konto nigdy nie aktywowane, więc pytanie zapowiada skasowanie.
  await karta.getByRole("button", { name: "Usuń klienta Do Skasowania" }).click();
  await expect(page.locator(".card", { hasText: email })).toHaveCount(0);
  expect(trescPytania).toContain("Usunąć konto");
  expect(trescPytania).toContain("nie da się cofnąć");
});

test("usunięcie aktywnego klienta zapowiada zakończenie współpracy, nie kasowanie danych", async ({ page }) => {
  let trescPytania = "";
  // Odrzucamy okno — sprawdzamy WYŁĄCZNIE treść zapowiedzi, bo konto
  // klienta A jest potrzebne pozostałym testom w tym przebiegu.
  page.on("dialog", (d) => {
    trescPytania = d.message();
    d.dismiss();
  });

  await zaloguj(page, KONTA.trener);
  await expect(page.getByRole("heading", { level: 1, name: "Klienci" })).toBeVisible({ timeout: 15_000 });

  const karta = page.locator(".card", { hasText: KONTA.klientA.email });
  await karta.getByRole("button", { name: /^Usuń klienta / }).click();

  expect(trescPytania).toContain("z Twojej listy");
  expect(trescPytania).toContain("ZOSTAJĄ");
  expect(trescPytania).not.toContain("nie da się cofnąć");
  // Odrzucenie okna niczego nie zmienia — klient dalej jest na liście.
  await expect(page.locator(".card", { hasText: KONTA.klientA.email })).toHaveCount(1);
});

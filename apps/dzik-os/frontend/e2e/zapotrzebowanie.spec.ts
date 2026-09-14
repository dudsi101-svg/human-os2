import { expect, Locator, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Wywiad „Zapotrzebowanie kaloryczne” wg specyfikacji właściciela 1.0:
 * klient wypełnia pięć ekranów (pola liczbowe z przecinkiem, pytania
 * warunkowe o czas treningu i tempo), przesyła i widzi bilans — spoczynek,
 * cały dzień z zakresem, cel i makro — w zakładkach Wywiad i Dieta.
 * Trener widzi ten sam bilans z rozbiciem CPM na składniki, nadpisuje go
 * z powodem, a w „Przypisz dietę” przycisk „Użyj w przypisaniu diety”
 * wypełnia kcal, masę i makro w gramach.
 *
 * Kobieta 30 l. / 170 cm / 70 kg, dzień siedzący, 3 × 60 min siłowy, bez
 * cardio, redukcja umiarkowana: PPM 1452, trening 158 kcal/dzień, TEF 190,
 * CPM 2089 (1943–2235), cel 1671 kcal.
 *
 * Projekt „telefon” (zapisuje). Założenie: świeża baza z `serve.sh`; spec
 * zostawia klientowi A przesłaną wersję i ustalenie 1800 kcal (inne specy
 * nie czytają zapotrzebowania).
 */

async function klik(loc: Locator) {
  await loc.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await loc.click();
}

async function wybierz(page: import("@playwright/test").Page, grupa: RegExp, opcja: RegExp | string) {
  await klik(page.getByRole("radiogroup", { name: grupa }).getByRole("radio", { name: opcja }));
}

test("klient liczy bilans kaloryczny, trener widzi rozbicie i używa go w diecie", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await zaloguj(page, KONTA.klientA);
  await page.goto("/wywiad?typ=zapotrzebowanie");
  await expect(page.getByRole("heading", { name: "Zapotrzebowanie kaloryczne" }).first()).toBeVisible({ timeout: 15_000 });

  // Ekran 1 — dane podstawowe.
  await wybierz(page, /^Płeć biologiczna/, "Kobieta");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  await page.getByLabel(/Wiek \(lata\)/).fill("30");
  await page.getByLabel(/Wzrost \(cm\)/).fill("170");
  await page.getByLabel(/Aktualna masa ciała/).fill("70,0");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });

  // Ekran 2 — aktywność poza treningiem.
  await wybierz(page, /dzień poza treningiem/, /Siedząca/);

  // Ekran 3 — trening. Czas treningu jest warunkowy: pojawia się po liczbie sesji.
  await expect(page.getByRole("radiogroup", { name: /Średni czas treningu siłowego/ })).toHaveCount(0);
  await page.getByLabel(/Treningi siłowe w tygodniu/).fill("3");
  await page.getByLabel(/Treningi cardio lub sport w tygodniu/).fill("0");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });
  await wybierz(page, /Średni czas treningu siłowego/, "60 minut");
  // Bez cardio pytania o czas i intensywność cardio nie istnieją.
  await expect(page.getByRole("radiogroup", { name: /Intensywność cardio/ })).toHaveCount(0);

  // Ekran 4 — cel. Tempo jest warunkowe.
  await expect(page.getByRole("radiogroup", { name: /Jakie tempo/ })).toHaveCount(0);
  await wybierz(page, /Jaki jest cel/, /Redukcja tkanki tłuszczowej/);
  await wybierz(page, /Jakie tempo/, "Umiarkowane");

  // Ekran 5 — zdrowie (dobrowolne).
  await wybierz(page, /zaburzenia odżywiania/, "Nie zgłaszam");
  await expect(page.getByText(/Zapisano ✓/)).toBeVisible({ timeout: 10_000 });

  const przeslij = page.getByRole("button", { name: "Prześlij trenerowi" });
  await expect(przeslij).toBeEnabled({ timeout: 15_000 });
  await klik(przeslij);
  await expect(page.getByText(/Przesłano wersję 1/)).toBeVisible({ timeout: 15_000 });

  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1671 kcal/, { timeout: 15_000 });
  await expect(page.getByTestId("bilans-cpm")).toHaveText(/2089 kcal/);
  await expect(page.getByText(/zakres 1943–2235/)).toBeVisible();
  await expect(page.getByTestId("bilans-makro")).toHaveText(/B \d+ g · T \d+ g · W \d+ g/);
  await expect(page.getByText(/Oczekiwane tempo/)).toBeVisible();
  // Klient widzi też podstawienie „skąd ta liczba”.
  await klik(page.getByRole("button", { name: "Skąd ta liczba?" }));
  await expect(page.getByText(/PPM \(Mifflin-St Jeor, kobieta\)/)).toBeVisible();

  await page.goto("/dieta");
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1671 kcal/, { timeout: 15_000 });

  // Trener: karta klienta → Wywiad → rozbicie CPM i nadpisanie z powodem.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener");
  await page.getByRole("link", { name: /Klient Testowy A/ }).first().click();
  await page.getByRole("tab", { name: "Wywiad" }).click();
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1671 kcal/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Skąd wychodzi CPM" })).toBeVisible();
  await expect(page.getByText(/1452 × 1,2 = 1742 kcal/)).toBeVisible();
  await expect(page.getByText(/Termiczny efekt pożywienia/)).toBeVisible();

  await klik(page.getByRole("button", { name: "Nadpisz wynik" }));
  await page.getByLabel(/kcal \/ dzień \(Twoja decyzja\)/).fill("1800");
  await page.getByLabel(/Powód \(klient go zobaczy\)/).fill("Pierwszy tydzień łagodniej.");
  await klik(page.getByRole("button", { name: "Zapisz", exact: true }));
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await expect(page.getByText(/Ustalone przez trenera/)).toBeVisible();

  // Dieta → Przypisz dietę → „Użyj w przypisaniu diety” wypełnia kcal, masę i makro.
  await page.getByRole("tab", { name: "Dieta" }).click();
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await klik(page.getByRole("button", { name: "Przypisz dietę" }));
  await klik(page.getByRole("button", { name: /Standard zbilansowana/ }));
  await klik(page.getByRole("button", { name: /Odsłona 1/ }));
  await klik(page.getByRole("button", { name: /Użyj w przypisaniu diety/ }));
  await expect(page.getByLabel("kcal / dzień")).toHaveValue("1800");
  await expect(page.getByLabel(/Masa ciała \(kg/)).toHaveValue("70");
  await expect(page.getByRole("radio", { name: /ręcznie/ })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByLabel("Białko (g)")).not.toHaveValue("");
  // Samo wstawienie nie przypisuje diety.
  await expect(page.getByText(/Przypisano dietę/)).toHaveCount(0);

  // Klient widzi ustalenie trenera i powód.
  await page.evaluate(() => sessionStorage.clear());
  await zaloguj(page, KONTA.klientA);
  await page.goto("/dieta");
  await expect(page.getByTestId("zapotrzebowanie-kcal")).toHaveText(/≈ 1800 kcal/, { timeout: 15_000 });
  await expect(page.getByText(/Pierwszy tydzień łagodniej/)).toBeVisible();
});

import { expect, Page, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Raport tygodniowy — jedyna rzecz, którą klient robi sam i regularnie.
 *
 * Testy przechodzą CAŁĄ drogę: wypełnienie, wysyłkę i potwierdzenie, że
 * serwer raport przyjął. Sam fakt, że formularz się wyrenderował, nie
 * dowodzi niczego — najczęstsza awaria tego ekranu to formularz, który
 * wygląda dobrze i nic nie zapisuje.
 *
 * Każdy przebieg dostaje świeżą bazę (patrz `playwright.config.ts`), więc
 * raport za bieżący tydzień na starcie nie istnieje.
 */

/** Skale samopoczucia — każda wymaga świadomego wyboru (patrz drugi test). */
const SKALE = ["Energia", "Sen", "Głód", "Stres", "Regeneracja", "Realizacja diety"];

async function ocenSkale(page: Page, ocena: string): Promise<void> {
  for (const nazwa of SKALE) {
    // Uwaga: to przełączniki — kliknięcie już wybranej oceny ją odznacza.
    await page
      .getByRole("group", { name: nazwa })
      .getByRole("button", { name: ocena, exact: true })
      .click();
  }
}

test("klient wypełnia i wysyła raport tygodniowy", async ({ page }) => {
  await zaloguj(page, KONTA.klientA);

  await page.goto("/raport");
  await expect(page.getByRole("heading", { name: "Raport tygodniowy" })).toBeVisible();

  // Raport jest jeden na tydzień: dopóki go nie ma, przycisk brzmi „Wyślij
  // raport", potem „Wyślij poprawkę". Test przyjmuje oba stany, bo inaczej
  // nie przetrwałby powtórnego uruchomienia na tej samej bazie — a formularz
  // wypełnia się identycznie (po wysłaniu pola i skale wracają puste).
  const wyslij = page.getByRole("button", { name: /^Wyślij (raport|poprawkę)$/ });
  await expect(wyslij).toBeVisible();

  await page.locator("#ck-weight").fill("81.4");
  await page.locator("#ck-trainings").fill("3");
  await page.locator("#ck-comment").fill("Raport z testu E2E — tydzień przebiegł spokojnie.");
  await ocenSkale(page, "4");
  await wyslij.click();

  // Najpierw potwierdzenie na ekranie — przeładowanie strony przerywa
  // trwające żądanie, więc reload przed komunikatem sukcesu wyścigałby
  // się z zapisem na serwerze (na obciążonym runnerze CI ten wyścig
  // realnie przegrywał).
  await expect(page.getByRole("status")).toContainText(/Raport wysłany/, {
    timeout: 20_000,
  });

  // Dowód, że raport DOTARŁ na serwer, a nie tylko zniknął z ekranu:
  // po przeładowaniu aplikacja wie, że tydzień jest już zaraportowany,
  // i oferuje poprawkę zamiast nowego raportu.
  await page.reload();
  await expect(page.getByRole("button", { name: "Wyślij poprawkę" })).toBeVisible({
    timeout: 20_000,
  });
});

test("raport nie wychodzi, dopóki każda skala nie ma świadomej odpowiedzi", async ({ page }) => {
  // To nie jest szczegół implementacji, tylko obietnica produktu widoczna
  // na ekranie: „żadne pytanie nie ma wartości domyślnej". Bez tego testu
  // cicha zmiana domyślnej wartości na 3 przeszłaby niezauważona,
  // a raport zacząłby zawierać oceny, których nikt nie wystawił.
  //
  // Konto B, nie A: raport jest jeden na tydzień, więc test wysyłający
  // i test walidacji na tym samym koncie zależałyby od kolejności.
  await zaloguj(page, KONTA.klientB);
  await page.goto("/raport");

  await page.locator("#ck-weight").fill("80");
  await page.locator("#ck-trainings").fill("2");
  // Celowo bez oceny skal.
  await page.getByRole("button", { name: "Wyślij raport" }).click();

  const ostrzezenie = page.getByRole("alert");
  await expect(ostrzezenie).toBeVisible();
  await expect(ostrzezenie).toContainText(/świadomej decyzji|pominięte/i);
  // Wysyłka ma być zablokowana — zostajemy na formularzu, a tydzień nadal
  // czeka na raport. Sprawdzamy DOKŁADNĄ nazwę: pojawienie się „Wyślij
  // poprawkę" znaczyłoby, że walidacja przepuściła niekompletny raport.
  // Konto B nigdy nie wysyła raportu, więc ten stan jest stały także przy
  // powtórnym uruchomieniu.
  await page.reload();
  await expect(page.getByRole("button", { name: "Wyślij raport" })).toBeVisible();
});

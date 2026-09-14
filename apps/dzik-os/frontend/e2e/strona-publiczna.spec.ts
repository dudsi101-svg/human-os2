import { expect, test } from "@playwright/test";

/**
 * Publiczna strona marketingowa (0.49.0): gość na "/" widzi wizytówkę
 * zamiast formularza logowania, może przejść do logowania i wysłać
 * zapytanie kontaktowe. Zapis jest bezpieczny dla współdzielonej bazy:
 * każde zgłoszenie tworzy osobne powiadomienie trenera (świeży id),
 * niczego nie nadpisując.
 */

test("gość widzi stronę marketingową i przechodzi do logowania", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Trening prowadzony, nie zgadywany" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Co dostajesz we współpracy" })).toBeVisible();

  // Galeria ekranów (0.50.0): sekcja jest na stronie, zrzuty się ładują.
  await expect(page.getByRole("heading", { name: "Zobacz aplikację" })).toBeVisible();
  // Prawdziwy trener (0.51.0): sekcja z nazwiskiem i kontakt bezpośredni.
  await expect(page.getByRole("heading", { name: /Łukasz Drygiel/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "+48 570 477 540" })).toBeVisible();
  await expect(page.getByAltText("Dzisiaj — Twój dzień w pigułce")).toBeVisible();

  await page.getByRole("link", { name: "Zaloguj się" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("E-mail")).toBeVisible();
});

test("gość wysyła zapytanie kontaktowe i widzi potwierdzenie", async ({ page }) => {
  await page.goto("/#kontakt");

  await page.getByLabel("Imię").fill("Gość Testowy");
  await page.getByLabel("E-mail").fill("gosc@example.com");
  await page.getByLabel("Wiadomość — cel, doświadczenie, pytania")
    .fill("Chcę zacząć treningi siłowe od podstaw.");
  await page.getByRole("button", { name: "Wyślij zapytanie" }).click();

  await expect(page.getByText("Dziękuję za wiadomość!")).toBeVisible();
});

test("gość czyta informację o przetwarzaniu danych bez logowania", async ({ page }) => {
  // Warstwowa notka RODO przy formularzu (0.53.5, audyt P0-1).
  await page.goto("/#kontakt");
  await expect(page.getByText(/Nie wpisuj w formularzu informacji o zdrowiu/)).toBeVisible();

  // Link prowadzi na publiczną trasę /prywatnosc — bez przekierowania na /login.
  await page.getByRole("link", { name: "informacja o przetwarzaniu danych", exact: true }).click();
  await expect(page).toHaveURL(/\/prywatnosc$/);
  await expect(page.getByRole("heading", { name: "Informacja o przetwarzaniu danych osobowych" })).toBeVisible();
  await expect(page.getByText(/LUBELSKI DZIK/)).toBeVisible();
  await expect(page.getByText(/Prezesa\s+Urzędu Ochrony Danych Osobowych/)).toBeVisible();

  // Wejście bezpośrednie (świeża karta) też jest publiczne.
  await page.goto("/prywatnosc");
  await expect(page.getByRole("heading", { name: "Informacja o przetwarzaniu danych osobowych" })).toBeVisible();
});

test("wariant czerwono-biały: kroki, statystyki trenera, chipy, /prywatnosc bez zmian", async ({ page }) => {
  // 0.65.0: nowa warstwa wizualna — treść i testy powyżej bez zmian.
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Trzy kroki do pierwszego planu" })).toBeVisible();
  // Trzy dowody (IFBB PRO / 30 000+ / nawet −12 kg) są celowo dwa razy: pasek pod hero
  // i kafle w „O trenerze” (0.72.0) — czytnik ekranu słyszy oba.
  await expect(page.getByText("30 000+")).toHaveCount(2);
  await expect(page.getByText("nawet −12 kg")).toHaveCount(2);
  await expect(page.getByText("Mapa mięśni")).toBeVisible();
  await expect(page.getByRole("link", { name: "Zaloguj się" })).toHaveCount(1);

  // /prywatnosc korzysta z bazowych klas .landing i ma pozostać ciemna (bez zmian).
  await page.goto("/prywatnosc");
  await expect(page.getByRole("heading", { name: "Informacja o przetwarzaniu danych osobowych" })).toHaveCSS("color", "rgb(238, 240, 242)");
  const tlo = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(tlo).toBe("rgb(11, 13, 15)");
});

test("brak poziomego przewijania na 1440 / 1024 / 768 / 390", async ({ page }) => {
  // 0.72.0: przed poprawkami 1024 px dawało scrollWidth 1086 (pierścień 520 px w hero
  // wystawał z panelu), a 768 px — 772 (czerwony kwadrat „O trenerze” przy krawędzi).
  for (const [width, height] of [[1440, 900], [1024, 800], [768, 1024], [390, 844]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Trening prowadzony, nie zgadywany" })).toBeVisible();
    // Zdjęcia ładowane leniwie: przewinięcie na sam dół, żeby układ był policzony w całości
    // (stopka leży wewnątrz <main>, więc nie ma roli contentinfo — stąd nie przez getByRole).
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect(page.getByAltText("Postępy i rekordy")).toBeVisible();
    const wymiary = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(wymiary.scrollWidth, `viewport ${width}px`).toBeLessThanOrEqual(wymiary.clientWidth);
  }
});

test("nawigacja kotwic od 900 px; kotwica ląduje pod paskiem 76 px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Sekcje strony" });
  await expect(nav).toBeVisible();
  // Cele dotyku ≥ 24 px (WCAG 2.2 2.5.8) — przed 0.72.0 linki miały ~18 px wysokości.
  for (const link of await nav.getByRole("link").all()) {
    const box = await link.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(24);
  }

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/");
  await expect(nav).toBeHidden();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("link", { name: "Umów bezpłatną konsultację" }).click();
  await expect(page).toHaveURL(/#kontakt$/);
  // „Napisz do mnie” jest też h3 pierwszego kroku — tu chodzi o h2 sekcji kontaktu.
  await expect(page.getByRole("heading", { name: "Napisz do mnie", level: 2 })).toBeVisible();
  const gora = await page.evaluate(() => document.getElementById("kontakt")!.getBoundingClientRect().top);
  expect(gora).toBeGreaterThanOrEqual(75); // scroll-margin-top: 76px; pasek górny ma 76 px
});

test("panel hero dekoracyjny, honeypot poza fokusem, konspekt nagłówków", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.locator(".landing-panel")).toHaveAttribute("aria-hidden", "true");
  // Karty w hero to dane demonstracyjne — każda nosi etykietę „przykład” (0.72.0).
  await expect(page.locator(".landing-panel__demo")).toHaveCount(3);

  const hp = page.locator(".landing-form__hp input");
  await expect(hp).toHaveAttribute("tabindex", "-1");
  await expect(page.locator(".landing-form__hp")).toHaveAttribute("aria-hidden", "true");
  await expect(hp).not.toBeInViewport();

  const konspekt = await page.evaluate(() =>
    Array.from(document.querySelectorAll("h1, h2, h3")).map((h) => `${h.tagName} ${h.textContent?.trim()}`),
  );
  expect(konspekt).toEqual([
    "H1 Trening prowadzony, nie zgadywany",
    "H2 Co dostajesz we współpracy",
    "H3 Plan treningowy pod Ciebie",
    "H3 Dieta, którą da się odmierzyć",
    "H3 Cotygodniowy raport",
    "H3 Postępy czarno na białym",
    "H3 Stały kontakt",
    "H3 Twoje dane pod kontrolą",
    "H2 Trzy kroki do pierwszego planu",
    "H3 Napisz do mnie",
    "H3 Ankieta i plan startowy",
    "H3 Trenujemy i korygujemy",
    "H2 Zobacz aplikację",
    "H2 Łukasz Drygiel — Lubelski Dzik",
    "H2 Częste pytania",
    "H2 Napisz do mnie",
  ]);
});

test("formularz: błąd serwera trafia do role=alert, formularz zostaje", async ({ page }) => {
  // Ścieżka błędu bez dotykania limitera (5/h per IP) i bazy: odpowiedź 429 podstawiona.
  await page.route("**/api/public/lead", (route) => route.fulfill({ status: 429, body: "" }));
  await page.goto("/#kontakt");
  await page.getByLabel("Imię").fill("Gość Testowy");
  await page.getByLabel("E-mail").fill("gosc@example.com");
  await page.getByLabel("Wiadomość — cel, doświadczenie, pytania").fill("Chcę zacząć treningi siłowe od podstaw.");
  await page.getByRole("button", { name: "Wyślij zapytanie" }).click();
  await expect(page.getByRole("alert")).toContainText("Zbyt wiele zgłoszeń");
  await expect(page.getByRole("button", { name: "Wyślij zapytanie" })).toBeEnabled();
  await expect(page.getByText("Dziękuję za wiadomość!")).toHaveCount(0);
});

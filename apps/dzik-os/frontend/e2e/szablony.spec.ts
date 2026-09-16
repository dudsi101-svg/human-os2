import { expect, test } from "@playwright/test";
import { KONTA, zaloguj } from "./helpers";

/**
 * Gotowe schematy treningowe — droga od katalogu do własnego szablonu.
 *
 * Test idzie przez pełny cykl: katalog → podgląd → import → obecność na
 * liście szablonów trenera. Sprawdzenie samego renderu katalogu byłoby
 * słabe: najczęstsza awaria to import, który wygląda na udany, a niczego
 * nie zapisuje.
 */
test("trener przegląda katalog i dodaje schemat do swoich szablonów", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");

  // Od 0.40.0 katalog nie stoi osobno: mieszka w karcie „Dodaj szablon"
  // i pokazuje się po wybraniu drogi „Weź gotowy schemat".
  const katalog = page.locator(".card", { hasText: "Dodaj szablon" });
  await expect(katalog).toContainText("Skąd bierzesz ten szablon?");
  await katalog.getByRole("button", { name: "Weź gotowy schemat" }).click();
  await expect(katalog).toContainText(/sprawdzonych planów/, { timeout: 15_000 });

  // Podgląd pokazuje receptę: serie/powtórzenia, cel RIR i zasadę progresji.
  await katalog.getByRole("button", { name: "Podgląd" }).first().click();
  await expect(katalog).toContainText(/RIR/, { timeout: 15_000 });
  await expect(katalog).toContainText(/progresj/i);

  await katalog.getByRole("button", { name: "Dodaj do moich" }).first().click();

  // Potwierdzenie mówi, co dokładnie powstało — nie samo „OK".
  const potwierdzenie = page.getByRole("status");
  await expect(potwierdzenie).toBeVisible({ timeout: 15_000 });
  await expect(potwierdzenie).toContainText(/Dodano/);

  // Dowód twardy: po przeładowaniu szablon przyszedł z serwera.
  await page.reload();
  await expect(
    page.locator(".card").filter({ hasText: "Start — całe ciało 2 dni" }).first(),
  ).toBeVisible({ timeout: 15_000 });
});

test("trener otwiera zakładkę Dieta i dodaje autorski szablon z katalogu", async ({ page }) => {
  // 0.54.0: szablony diety żyją obok treningowych — jeden ekran, dwie
  // zakładki. Import z katalogu tworzy własny, edytowalny szablon.
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");

  await page.getByRole("tab", { name: "Dieta" }).click();
  await expect(page.getByText("Gotowe szablony diety")).toBeVisible();
  await expect(page.getByText(/Dieta — Etap I/).first()).toBeVisible();

  await page.getByRole("button", { name: /Dodaj do moich|Dodaj ponownie/ }).first().click();
  // Szablon pojawia się na liście moich, z podglądem posiłków.
  await expect(page.getByRole("heading", { name: /Dieta — Etap I/ }).first()).toBeVisible();
  await page.getByRole("button", { name: "Podgląd" }).first().click();
  await expect(page.getByText("Przekąska (posiłek ruchomy)").first()).toBeVisible();
  await expect(page.getByText(/Ściąga zamienników/).first()).toBeVisible();
});

/**
 * Wymiany v2 (0.69.0): panel szablonów diet pokazuje tabelę grup pokrewnych
 * zamienników tylko do odczytu (propozycja do przeglądu trenera/dietetyka).
 */
test("trener widzi grupy pokrewne zamienników tylko do odczytu", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony-diet");
  const karta = page.locator("details", { hasText: /Grupy pokrewne zamienników — \d+ par/ });
  await expect(karta).toBeVisible({ timeout: 15_000 });
  await karta.locator("summary").click();
  await expect(karta.getByRole("cell", { name: "Grupa A" })).toBeVisible();
  await expect(karta.getByText("włączona").first()).toBeVisible();
  await expect(karta.getByText(/wyłączona \(propozycja niepewna\)/).first()).toBeVisible();
  await expect(karta.getByRole("button", { name: /zapisz|usuń|dodaj|edytuj/i })).toHaveCount(0);
});

/**
 * 0.75.0 (polecenie właściciela): lista szablonów pokazuje NAZWY, a treść
 * (dni, ćwiczenia, panel publikacji) rozwija się dopiero po kliknięciu
 * w nazwę — i zwija tym samym przyciskiem. Test chodzi na obu projektach
 * (telefon i desktop-trener); niczego nie zapisuje.
 */
test("trener rozwija i zwija szablon kliknięciem w nazwę", async ({ page }) => {
  await zaloguj(page, KONTA.trener);
  await page.goto("/trener/szablony");
  const karta = page.getByTestId("szablon-karta").filter({ hasText: "Szablon: Push/Pull/Legs" }).first();
  await expect(karta).toBeVisible({ timeout: 15_000 });
  const nazwa = karta.getByTestId("szablon-nazwa");
  // Zwinięte: meta (dni · pozycje) widoczna, ćwiczenia i publikacja — nie.
  await expect(nazwa).toHaveAttribute("aria-expanded", "false");
  await expect(karta).toContainText(/3 dni · 6 pozycji/);
  await expect(karta).not.toContainText("Wyciskanie sztangi leżąc");
  await expect(karta.getByRole("heading", { level: 2 })).toHaveCount(1);

  await nazwa.click();
  await expect(nazwa).toHaveAttribute("aria-expanded", "true");
  await expect(karta).toContainText("Push");
  await expect(karta).toContainText("Wyciskanie sztangi leżąc");
  await expect(karta).toContainText(/4×8/);
  // Pozycja z bazy prowadzi do własnej karty ćwiczenia w Wiedzy.
  await expect(karta.getByRole("link", { name: "Karta w Wiedzy" }).first()).toHaveAttribute("href", /\/trener\/wiedza\?cwiczenie=/);
  // Wskazówka musi podawać nazwę przycisku, który NAPRAWDĘ istnieje w karcie
  // klienta. Do 0.79.0 mówiła „Z szablonu…” — nazwy zmienionej w 0.76.0 —
  // i przez to funkcja przypisywania z blokami wyglądała na nieistniejącą.
  await expect(karta).toContainText("Przypisanie klientowi");
  await expect(karta).toContainText("Przypisz plan (szablon i bloki)");

  // Klawiatura: Enter na przycisku zwija.
  await nazwa.focus();
  await page.keyboard.press("Enter");
  await expect(nazwa).toHaveAttribute("aria-expanded", "false");
  await expect(karta).not.toContainText("Wyciskanie sztangi leżąc");
});

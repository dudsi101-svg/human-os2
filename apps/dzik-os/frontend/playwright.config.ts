import { defineConfig, devices } from "@playwright/test";

/**
 * Testy E2E Dzik OS.
 *
 * Po co: audyt 18.08.2026 wykazał, że ~15 700 linii interfejsu nie było
 * chronione żadnym testem uruchamianym w CI — regresja w ekranie trenera
 * przechodziła przez wszystkie bramki. Backend odmawia nieuprawnionego
 * dostępu, ale nikt nie zauważał ekranu, który przestał się renderować.
 *
 * Zakres jest celowo wąski: cztery ścieżki, bez których aplikacja nie ma
 * sensu (logowanie trenera, logowanie klienta, check-in, wiadomość).
 * Lepszy mały zestaw chodzący przy każdym pushu niż duży, który nie chodzi.
 */
export default defineConfig({
  testDir: "./e2e",
  // Aplikacja jest mobile-first, więc domyślny widok też jest telefonem.
  use: {
    ...devices["Pixel 7"],
    baseURL: `http://127.0.0.1:${process.env.DZIK_E2E_PORT || 8099}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  // Jeden worker: backend ma jedną bazę SQLite z danymi demo, a testy
  // zapisują (check-in, wiadomość). Równoległość dawałaby wyścigi
  // o ten sam stan, czyli dokładnie tę flakowatość, której nie chcemy.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  webServer: {
    command: "bash e2e/serve.sh",
    url: `http://127.0.0.1:${process.env.DZIK_E2E_PORT || 8099}/api/health`,
    // Nigdy nie używamy działającego serwera — `serve.sh` kasuje bazę przy
    // starcie, więc świeży serwer znaczy świeże dane. Bez tego drugi przebieg
    // widzi skutki pierwszego (raport tygodniowy jest jeden na tydzień:
    // formularz zmienia się w „Wyślij poprawkę") i testy zaczynają zależeć
    // od tego, czy uruchamiasz je pierwszy raz. Kosztuje kilka sekund startu.
    reuseExistingServer: false,
    timeout: 120_000,
    // Logi żądań backendu zaśmiecałyby raport; błędy (stderr) zostają.
    stdout: "ignore",
    stderr: "pipe",
  },
});

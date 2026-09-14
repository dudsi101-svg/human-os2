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
// Dwa serwery: domyślny (flagi jak w produkcji) i drugi z włączoną zakładką
// Postępy/Monitoring (0.66.0) na sąsiednim porcie i osobnej bazie. Spec
// `postepy.spec.ts` chodzi tylko na drugim (projekt `telefon-postepy`);
// reszta zestawu nie widzi flagi i sprawdza, że bez niej nic się nie zmienia.
const PORT = Number(process.env.DZIK_E2E_PORT || 8099);
// Drugi port domyślnie sąsiedni; przy kilku sesjach na jednej maszynie
// (KOORDYNACJA §0) da się go wskazać osobno, gdy sąsiedni jest zajęty.
const PORT_POSTEPY = Number(process.env.DZIK_E2E_PORT_POSTEPY || PORT + 1);
const DIR = process.env.DZIK_E2E_DIR || "/tmp/dzik-e2e";

export default defineConfig({
  testDir: "./e2e",
  // Aplikacja jest mobile-first, więc domyślny widok też jest telefonem.
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Ta sama strefa co serwer (seed liczy „bieżący tydzień” wg Europe/Warsaw):
    // na runnerze w UTC między 22:00 a 24:00 w niedzielę przeglądarka
    // widziała jeszcze poprzedni tydzień, a seed już nowy — formularz raportu
    // trafiał na zeszłotygodniowy, oceniony raport i był zablokowany.
    timezoneId: "Europe/Warsaw",
    locale: "pl-PL",
  },
  // DWA PROJEKTY, NIE JEDEN — a podział między nimi nie jest kosmetyczny.
  //
  // Aplikacja jest mobile-first i cały zestaw chodził wyłącznie na telefonie.
  // Tyle że KLIENT używa telefonu, a TRENER siedzi przy panelu na desktopie:
  // lista klientów, karta klienta, katalog szablonów. Ta powierzchnia nie
  // miała ani jednego testu w swojej własnej szerokości.
  //
  // Desktop dostaje WYŁĄCZNIE testy, które nic nie zapisują. Powód jest
  // twardy, nie estetyczny: backend ma jedną bazę SQLite z danymi demo,
  // a raport wychodzi raz na tydzień. Uruchomienie testów zapisujących
  // drugi raz na tej samej bazie wywróciłoby je z powodu stanu zostawionego
  // przez pierwszy przebieg — czyli dokładnie ta flakowatość, przed którą
  // broni `workers: 1` i `retries: 0`.
  projects: [
    {
      name: "telefon",
      use: { ...devices["Pixel 7"] },
      testIgnore: /postepy\.spec\.ts/,
    },
    {
      name: "desktop-trener",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
      testMatch: /(logowanie|szablony|pwa)\.spec\.ts/,
    },
    {
      name: "telefon-postepy",
      use: { ...devices["Pixel 7"], baseURL: `http://127.0.0.1:${PORT_POSTEPY}` },
      testMatch: /postepy\.spec\.ts/,
    },
  ],
  // Jeden worker: backend ma jedną bazę SQLite z danymi demo, a testy
  // zapisują (check-in, wiadomość). Równoległość dawałaby wyścigi
  // o ten sam stan, czyli dokładnie tę flakowatość, której nie chcemy.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  // ZERO powtórzeń — świadomie. Testy zapisują dane do jednej bazy, a przy
  // powtórce baza NIE jest resetowana (serwer chodzi dalej), więc druga próba
  // zaczyna od stanu zostawionego przez pierwszą. Powtórzenie nie naprawiało
  // tu niestabilności, tylko utrwalało porażkę i zaciemniało przyczynę.
  // Test ma być odporny sam z siebie; jeśli nie jest, ma to być widać.
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  webServer: [{
    command: "bash e2e/serve.sh",
    url: `http://127.0.0.1:${PORT}/api/health`,
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
  }, {
    command: "bash e2e/serve.sh",
    url: `http://127.0.0.1:${PORT_POSTEPY}/api/health`,
    env: { DZIK_E2E_PORT: String(PORT_POSTEPY), DZIK_E2E_DIR: `${DIR}-postepy`, DZIK_MONITORING_TAB_ENABLED: "true" },
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
  }],
});

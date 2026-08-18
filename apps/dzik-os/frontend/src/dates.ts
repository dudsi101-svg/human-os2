// Wspólny moduł dat (jedno źródło prawdy — patrz backend/dzik_os/dates.py).
//
// Model dat w aplikacji:
// 1. Data kalendarzowa użytkownika (performed_on, logged_on, occurred_on,
//    completed_on, week_start, measured_at, due_date, target_date):
//    "YYYY-MM-DD" wyliczana w LOKALNEJ strefie przeglądarki. NIGDY przez
//    `new Date().toISOString().slice(0, 10)` — to data UTC, która o 00:30
//    czy 01:00 czasu polskiego wskazuje jeszcze wczorajszy dzień.
// 2. Dokładny moment zdarzenia (created_at, paid_at, read_at...): pełny
//    timestamp UTC z backendu; do strefy lokalnej przeliczany dopiero przy
//    prezentacji (plDateTime).
// 3. Termin lokalny (consult_slots.starts_at): naiwny "YYYY-MM-DDTHH:MM"
//    w strefie lokalnej; porównywany wyłącznie z localNowMinute().
//
// Parametr `now` służy testom — funkcje są czyste względem niego.

const pad2 = (n: number) => String(n).padStart(2, "0");

/** Data kalendarzowa Date → "YYYY-MM-DD" w lokalnej strefie. */
export function toIsoDate(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Dzisiejsza data kalendarzowa w lokalnej strefie ("YYYY-MM-DD"). */
export const localToday = (now: Date = new Date()): string => toIsoDate(now);

/** Poniedziałek tygodnia zawierającego `now` ("YYYY-MM-DD", lokalnie). */
export function mondayOfWeek(now: Date = new Date()): string {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = d.getDay() || 7; // niedziela=0 → 7
  d.setDate(d.getDate() - day + 1);
  return toIsoDate(d);
}

/** Lokalny czas z dokładnością do minuty ("YYYY-MM-DDTHH:MM") — jedyny
 * poprawny komparand dla terminów konsultacji (starts_at). */
export const localNowMinute = (now: Date = new Date()): string =>
  `${toIsoDate(now)}T${pad2(now.getHours())}:${pad2(now.getMinutes())}`;

/** Parsuje wartość z API: "YYYY-MM-DD" jako LOKALNĄ północ (data
 * kalendarzowa nie jest momentem — parsowanie przez `new Date(iso)`
 * dałoby północ UTC i ryzyko przesunięcia dnia), pozostałe formaty
 * (pełne timestampy UTC, naiwne "YYYY-MM-DDTHH:MM") natywnie. */
export function parseApiDate(iso: string): Date {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return new Date(iso);
}

/** Prezentacja daty kalendarzowej po polsku. */
export const plDate = (iso: string | null | undefined) =>
  iso
    ? parseApiDate(iso).toLocaleDateString("pl-PL", { day: "numeric", month: "long", year: "numeric" })
    : "—";

/** Prezentacja momentu zdarzenia po polsku (przeliczenie do strefy
 * lokalnej następuje dopiero tutaj). */
export const plDateTime = (iso: string | null | undefined) =>
  iso
    ? parseApiDate(iso).toLocaleString("pl-PL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : "—";

export const WEEKDAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "niedz"];

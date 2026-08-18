// Czysta logika centrum powiadomień i ustawień doręczeń — bez React i
// bez fetch, testowana w Node (scripts/test-notifications-utils.mjs).
// Źródłem prawdy dla kategorii/kanałów jest backend
// (GET /api/notifications/settings); poniższe etykiety to fallback UI.

export interface NotificationRow {
  id: string;
  category: string;
  category_label: string;
  title: string;
  body: string;
  url: string;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
}

export const CHANNEL_LABELS: Record<string, string> = {
  PUSH: "Push",
  CENTER: "W aplikacji",
  EMAIL: "E-mail",
};

export const DAY_LABELS: Record<string, string> = {
  "1": "Pn", "2": "Wt", "3": "Śr", "4": "Cz", "5": "Pt", "6": "So", "7": "Nd",
};

/** Krótkie IANA strefy sensowne dla użytkowników aplikacji (pełna
 * walidacja i tak jest po stronie backendu — ZoneInfo). */
export const TIMEZONE_CHOICES = [
  "Europe/Warsaw",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Madrid",
  "Europe/Kyiv",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Asia/Dubai",
  "Australia/Sydney",
];

const TIME_RE = /^([01][0-9]|2[0-3]):[0-5][0-9]$/;

/** Ciche godziny są poprawne, gdy oba pola są puste (wyłączone) albo oba
 * mają format HH:MM i różnią się od siebie (zakres może przechodzić przez
 * północ — 22:00–07:00 jest legalne). */
export function quietHoursValid(start: string, end: string): boolean {
  if (start === "" && end === "") return true;
  if (!TIME_RE.test(start) || !TIME_RE.test(end)) return false;
  return start !== end;
}

export function parseActiveDays(csv: string): Set<string> {
  return new Set(
    csv.split(",").map((d) => d.trim()).filter((d) => d in DAY_LABELS)
  );
}

/** Przełącza dzień w CSV dni aktywnych; nie pozwala wyłączyć wszystkich
 * (przypomnienia bez ani jednego dnia = wyłączenie kategorii, od tego są
 * preferencje). Zwraca CSV posortowane 1..7. */
export function toggleActiveDay(csv: string, day: string): string {
  const days = parseActiveDays(csv);
  if (days.has(day)) {
    if (days.size > 1) days.delete(day);
  } else if (day in DAY_LABELS) {
    days.add(day);
  }
  return Array.from(days).sort().join(",");
}

/** Adres docelowy kliknięcia — zawsze wewnętrzna ścieżka aplikacji
 * (powiadomienie nigdy nie wyprowadza poza aplikację). */
export function notificationTargetUrl(n: Pick<NotificationRow, "url">): string {
  const url = n.url || "/";
  return url.startsWith("/") ? url : "/";
}

/** Liczba nieprzeczytanych do plakietki: 0 → "", 100+ → "99+". */
export function unreadBadge(count: number): string {
  if (count <= 0) return "";
  return count > 99 ? "99+" : String(count);
}

/** Scala świeże zdarzenie SSE (notification.new) z listą — bez duplikatów
 * (odświeżenie GET mogło już zawierać ten wiersz), najnowsze na górze. */
export function mergeNotification<T extends { id: string }>(
  rows: T[], incoming: T
): T[] {
  if (rows.some((r) => r.id === incoming.id)) return rows;
  return [incoming, ...rows];
}

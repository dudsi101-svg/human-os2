// Czysta logika obsługi błędów — bez importów i bez DOM, żeby dało się ją
// testować w Node (scripts/test-error-utils.mjs) bez uruchamiania przeglądarki.

/** Klasyfikacja nieudanego fetch(): anulowane przez widok / timeout / offline.
 * Kolejność ma znaczenie: anulowanie przez wołającego wygrywa z timeoutem. */
export function classifyFetchFailure(
  callerAborted: boolean,
  timedOut: boolean
): "CANCELLED" | "TIMEOUT" | "OFFLINE" {
  if (callerAborted) return "CANCELLED";
  if (timedOut) return "TIMEOUT";
  return "OFFLINE";
}

/** Nazwa typu błędu (np. "TypeError", "ApiError") — bez komunikatu,
 * który mógłby zawierać dane. */
export function errorTypeName(error: unknown): string {
  if (error instanceof Error && error.name) return error.name.slice(0, 80);
  return "Error";
}

const FRAME = /([\w.-]+\.(?:m?js|ts|tsx))(?::(\d+))(?::(\d+))?/;

/** Redakcja stosu błędu do raportu: wyłącznie nazwy WŁASNYCH plików
 * skryptowych z numerami linii ("index-abc.js:10:20") — bez komunikatów,
 * URL-i, query stringów i czegokolwiek, co mogłoby nieść dane. Serwer
 * wykonuje tę samą redakcję drugi raz (defense in depth). */
export function redactStack(
  stack: string | null | undefined,
  maxFrames = 20
): string[] {
  if (!stack) return [];
  const frames: string[] = [];
  for (const line of stack.split("\n")) {
    const m = FRAME.exec(line);
    if (!m) continue;
    frames.push(`${m[1]}:${m[2]}${m[3] ? `:${m[3]}` : ""}`);
    if (frames.length >= maxFrames) break;
  }
  return frames;
}

/** Maskowanie identyfikatorów w ścieżce (np. /trener/klient/HOS-USR-...
 * → /trener/klient/{id}) — etykieta trasy w telemetrii nie niesie id. */
export function maskPathIds(path: string): string {
  return path
    .split("/")
    .map((seg) =>
      /^(HOS-[A-Z]{2,8}-[0-9A-Za-z]+|[0-9a-fA-F-]{8,}|\d+)$/.test(seg) ? "{id}" : seg
    )
    .join("/");
}

/** Nazwa pliku z nagłówka Content-Disposition (RFC 5987 z fallbackiem). */
export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim());
    } catch {
      /* Świadomie: uszkodzone kodowanie RFC 5987 → spróbuj zwykłego
       * filename= poniżej zamiast wywracać pobieranie. */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

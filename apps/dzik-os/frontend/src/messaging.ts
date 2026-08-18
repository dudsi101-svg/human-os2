// Czysta logika wiadomości w czasie rzeczywistym — bez DOM i bez fetch,
// żeby dała się testować w Node (scripts/test-messaging.mjs):
// parser strumienia SSE, backoff ponownego łączenia, scalanie i porządek
// wiadomości (created_at, id), deduplikacja po client_msg_id oraz
// szkice per wątek (draft przeżywa utratę sieci i nawigację).

export interface ChatMessage {
  id: string;
  author_id: string;
  body: string;
  file_id: string | null;
  created_at: string;
  delivered_at: string | null;
  read_at: string | null;
  client_msg_id?: string | null;
  /** Lokalna wiadomość w drodze (optymistyczna) — jeszcze bez id serwera. */
  pending?: boolean;
}

// --- Kolejność i scalanie ---------------------------------------------------

/** Stabilny porządek rozmowy: rosnąco po (created_at, id) — dokładnie ten
 * sam klucz co ORDER BY backendu; kolejność nie zależy od kolejności
 * doręczeń SSE/HTTP. */
export function sortMessages<T extends ChatMessage>(list: T[]): T[] {
  return [...list].sort((a, b) => {
    if (a.created_at !== b.created_at) return a.created_at < b.created_at ? -1 : 1;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
}

/** Scala przychodzącą wiadomość z listą: duplikat po id jest podmieniany
 * (świeższe statusy delivered/read), wiadomość optymistyczna z tym samym
 * client_msg_id jest zastępowana potwierdzoną z serwera, nowa trafia na
 * właściwe miejsce porządku. */
export function mergeMessage<T extends ChatMessage>(list: T[], incoming: T): T[] {
  const byId = list.findIndex((m) => m.id === incoming.id);
  if (byId >= 0) {
    const next = [...list];
    next[byId] = { ...next[byId], ...incoming };
    return sortMessages(next);
  }
  if (incoming.client_msg_id) {
    const byClientId = list.findIndex(
      (m) => m.client_msg_id === incoming.client_msg_id
    );
    if (byClientId >= 0) {
      const next = [...list];
      next[byClientId] = incoming;
      return sortMessages(next);
    }
  }
  return sortMessages([...list, incoming]);
}

/** Nakłada potwierdzenie przeczytania/doręczenia na własne wiadomości. */
export function applyReceipt<T extends ChatMessage>(
  list: T[],
  messageIds: string[],
  field: "read_at" | "delivered_at",
  stamp: string
): T[] {
  const ids = new Set(messageIds);
  return list.map((m) =>
    ids.has(m.id) && !m[field] ? { ...m, [field]: stamp } : m
  );
}

// --- Ponowne łączenie (backoff) --------------------------------------------

export const BACKOFF_BASE_MS = 1000;
export const BACKOFF_MAX_MS = 30_000;

/** Opóźnienie przed próbą nr `attempt` (1, 2, 3…): wykładniczy wzrost
 * z twardym sufitem. Jitter dokłada wołający (losowość nie jest częścią
 * logiki testowalnej). */
export function nextBackoffMs(attempt: number): number {
  const exp = Math.max(0, Math.min(attempt - 1, 30));
  return Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** exp);
}

/** Po ilu nieudanych próbach z rzędu przełączamy się na polling. */
export const FALLBACK_AFTER_FAILURES = 3;
/** Interwał pollingu awaryjnego (wyłącznie na otwartym ekranie rozmowy). */
export const FALLBACK_POLL_MS = 15_000;

// --- Parser SSE -------------------------------------------------------------

export interface SseEvent {
  event: string;
  data: string;
  id: string | null;
}

/** Przyrostowy parser text/event-stream: karm dowolnymi kawałkami
 * (feed), zdarzenia wychodzą przez callback po pustej linii kończącej
 * blok. Komentarze (linie od ":") są ignorowane — to keepalive. */
export function createSseParser(onEvent: (e: SseEvent) => void) {
  let buffer = "";
  let eventType = "message";
  let dataLines: string[] = [];
  let lastId: string | null = null;

  const dispatch = () => {
    if (dataLines.length > 0) {
      onEvent({ event: eventType, data: dataLines.join("\n"), id: lastId });
    }
    eventType = "message";
    dataLines = [];
  };

  const handleLine = (line: string) => {
    if (line === "") {
      dispatch();
      return;
    }
    if (line.startsWith(":")) return; // komentarz/keepalive
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") eventType = value;
    else if (field === "data") dataLines.push(value);
    else if (field === "id") lastId = value;
    // "retry" celowo pomijane — mamy własny backoff.
  };

  return {
    feed(chunk: string) {
      buffer += chunk;
      let idx: number;
      // Obsługa \n i \r\n; ostatnia niekompletna linia zostaje w buforze.
      while ((idx = buffer.indexOf("\n")) !== -1) {
        let line = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 1);
        if (line.endsWith("\r")) line = line.slice(0, -1);
        handleLine(line);
      }
    },
  };
}

// --- Szkice (draft per wątek) ----------------------------------------------

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const draftKey = (threadId: string) => `dzik_draft_${threadId}`;

export function loadDraft(storage: StorageLike, threadId: string): string {
  try {
    return storage.getItem(draftKey(threadId)) ?? "";
  } catch {
    return "";
  }
}

export function saveDraft(storage: StorageLike, threadId: string, text: string): void {
  try {
    if (text) storage.setItem(draftKey(threadId), text);
    else storage.removeItem(draftKey(threadId));
  } catch {
    /* Świadomie: pełny/zablokowany storage nie może wywrócić pisania. */
  }
}

export function clearDraft(storage: StorageLike, threadId: string): void {
  try {
    storage.removeItem(draftKey(threadId));
  } catch {
    /* jw. */
  }
}

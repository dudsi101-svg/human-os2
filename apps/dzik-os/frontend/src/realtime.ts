// Klient kanału czasu rzeczywistego (SSE) — własny odpowiednik EventSource
// oparty na fetch + ReadableStream, bo tylko fetch umie wysłać nagłówek
// Authorization: Bearer (EventSource nie przyjmuje nagłówków, a tokenu NIE
// wolno przekazywać w query stringu — trafiałby do logów proxy).
//
// Zachowanie:
// - automatyczne ponowne łączenie z wykładniczym backoffem (messaging.ts);
// - po FALLBACK_AFTER_FAILURES nieudanych próbach z rzędu zgłasza "down"
//   (widok włącza wtedy kontrolowany polling), po udanym połączeniu "up";
// - 401 lub zdarzenie session_expired → onSessionExpired (czytelny powrót
//   do logowania robi warstwa api.ts);
// - zamknięcie przez AbortController (odmontowanie widoku) kończy pętlę.

import { getToken } from "./api";
import {
  FALLBACK_AFTER_FAILURES,
  createSseParser,
  nextBackoffMs,
} from "./messaging";

export interface RealtimeHandlers {
  /** Zdarzenie z kanału: typ + zdekodowany JSON payload. */
  onEvent: (type: string, data: unknown) => void;
  /** Zmiana stanu kanału: "up" (połączony), "down" (fallback na polling). */
  onChannelState?: (state: "up" | "down") => void;
  /** Sesja wygasła/unieważniona (401 albo zdarzenie session_expired). */
  onSessionExpired?: () => void;
}

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const t = setTimeout(done, ms);
    function done() {
      clearTimeout(t);
      signal.removeEventListener("abort", done);
      resolve();
    }
    signal.addEventListener("abort", done);
  });

/** Utrzymuje połączenie SSE aż do przerwania sygnałem. Zwraca promise
 * kończący się dopiero po aborcie (wołający zwykle go nie awaituje). */
export async function connectRealtime(
  url: string,
  handlers: RealtimeHandlers,
  signal: AbortSignal
): Promise<void> {
  let failures = 0;
  let reportedDown = false;

  const setUp = () => {
    failures = 0;
    if (reportedDown) handlers.onChannelState?.("up");
    reportedDown = false;
  };
  const noteFailure = () => {
    failures += 1;
    if (failures >= FALLBACK_AFTER_FAILURES && !reportedDown) {
      reportedDown = true;
      handlers.onChannelState?.("down");
    }
  };

  while (!signal.aborted) {
    const token = getToken();
    if (!token) {
      handlers.onSessionExpired?.();
      return;
    }
    let gotReady = false;
    try {
      const resp = await fetch(url, {
        headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
        credentials: "same-origin",
        signal,
        cache: "no-store",
      });
      if (resp.status === 401) {
        handlers.onSessionExpired?.();
        return;
      }
      if (!resp.ok || !resp.body) {
        noteFailure();
      } else {
        const parser = createSseParser((e) => {
          if (e.event === "session_expired") {
            handlers.onSessionExpired?.();
            return;
          }
          if (e.event === "ready") {
            gotReady = true;
            setUp();
            return;
          }
          let payload: unknown = null;
          try {
            payload = JSON.parse(e.data);
          } catch {
            return; // uszkodzony blok — zignoruj, resync nadrobi
          }
          handlers.onEvent(e.event, payload);
        });
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        // Pętla czytania — kończy się przy zamknięciu strumienia/aborcie.
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value, { stream: true }));
        }
        // Serwer zamknął strumień (np. session_expired już obsłużone albo
        // restart) — jeśli w ogóle nie doszło "ready", licz jako porażkę.
        if (!gotReady) noteFailure();
      }
    } catch {
      if (signal.aborted) return;
      noteFailure();
    }
    if (signal.aborted) return;
    // Ponowne łączenie: rosnący odstęp + drobny jitter przeciw stampede.
    const backoff = nextBackoffMs(Math.max(1, failures));
    await sleep(backoff + Math.floor(Math.random() * 250), signal);
  }
}

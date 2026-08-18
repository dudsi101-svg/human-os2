// Nagrywanie wiadomości głosowych — logika wydzielona z widoku i oparta na
// wstrzykiwanych zależnościach (getUserMedia / MediaRecorder / isTypeSupported),
// żeby dała się testować w Node (scripts/test-messaging.mjs) bez przeglądarki.
//
// Zasady:
// - format wybierany przez MediaRecorder.isTypeSupported (webm/opus tam,
//   gdzie jest — Chrome/Firefox/Android; audio/mp4 (AAC) na iOS/Safari),
//   a wysyłany typ to RZECZYWISTY recorder.mimeType (bez parametru codecs),
//   nigdy sztywne audio/webm;
// - wszystkie ścieżki mikrofonu są zatrzymywane (track.stop()) po stop,
//   anulowaniu, błędzie i odmontowaniu komponentu (dispose);
// - limit czasu (3 min) i rozmiaru nagrania egzekwowany po stronie klienta
//   (backend i tak ma własny limit uploadu).

export const AUDIO_MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4;codecs=mp4a.40.2", // iOS/Safari (AAC)
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/ogg",
];

export const MAX_RECORDING_MS = 3 * 60 * 1000;
export const MAX_RECORDING_BYTES = 15 * 1024 * 1024;

/** Pierwszy realnie wspierany typ z listy kandydatów; "" = zostaw wybór
 * przeglądarce (MediaRecorder bez opcji mimeType). */
export function pickAudioMime(isSupported: (type: string) => boolean): string {
  for (const candidate of AUDIO_MIME_CANDIDATES) {
    try {
      if (isSupported(candidate)) return candidate;
    } catch {
      /* starsze przeglądarki bez isTypeSupported */
    }
  }
  return "";
}

/** Typ bazowy bez parametrów (";codecs=...") — to on idzie do uploadu;
 * backend przyjmuje wyłącznie typy bazowe z allowlisty. */
export function baseMime(mime: string): string {
  return mime.split(";", 1)[0].trim().toLowerCase();
}

const EXTENSIONS: Record<string, string> = {
  "audio/webm": ".webm",
  "audio/mp4": ".m4a",
  "audio/mpeg": ".mp3",
  "audio/ogg": ".ogg",
};

export function extensionForMime(mime: string): string {
  return EXTENSIONS[baseMime(mime)] ?? ".webm";
}

// --- Kontroler nagrywania ---------------------------------------------------

export interface TrackLike {
  stop(): void;
}

export interface MediaStreamLike {
  getTracks(): TrackLike[];
}

export interface MediaRecorderLike {
  start(timesliceMs?: number): void;
  stop(): void;
  state: string;
  mimeType: string;
  ondataavailable: ((e: { data: Blob }) => void) | null;
  onstop: (() => void) | null;
  onerror: ((e: unknown) => void) | null;
}

export interface RecorderDeps {
  getUserMedia: () => Promise<MediaStreamLike>;
  createRecorder: (stream: MediaStreamLike, mimeType: string) => MediaRecorderLike;
  isTypeSupported: (type: string) => boolean;
  /** Fabryka File — wstrzykiwana, bo Node nie ma File z Blobów DOM. */
  makeFile?: (chunks: Blob[], name: string, type: string) => File;
  maxDurationMs?: number;
  maxBytes?: number;
  /** Wywoływane przy auto-stopie po przekroczeniu limitu czasu. */
  onAutoStop?: () => void;
}

export type RecordingResult =
  | { kind: "ok"; file: File }
  | { kind: "error"; reason: "empty" | "too_large" | "recorder_error" }
  | { kind: "cancelled" };

/** Kontroler jednego nagrania. Gwarancja: po zakończeniu (stop/cancel/
 * dispose/błąd) żadna ścieżka mikrofonu nie zostaje otwarta. */
export function createVoiceRecorder(deps: RecorderDeps) {
  const maxDuration = deps.maxDurationMs ?? MAX_RECORDING_MS;
  const maxBytes = deps.maxBytes ?? MAX_RECORDING_BYTES;
  const makeFile =
    deps.makeFile ??
    ((chunks: Blob[], name: string, type: string) =>
      new File([new Blob(chunks, { type })], name, { type }));

  let stream: MediaStreamLike | null = null;
  let recorder: MediaRecorderLike | null = null;
  let chunks: Blob[] = [];
  let autoStopTimer: ReturnType<typeof setTimeout> | null = null;
  let finished: ((r: RecordingResult) => void) | null = null;
  /** Wynik zakończonego nagrania, gdy nikt jeszcze nie czekał w stop()
   * (np. auto-stop po limicie czasu) — odebrany następnym stop(). */
  let lastResult: RecordingResult | null = null;
  let stopRequested = false;
  let cancelled = false;
  let errored = false;

  const stopTracks = () => {
    stream?.getTracks().forEach((t) => {
      try {
        t.stop();
      } catch {
        /* ścieżka mogła już być zatrzymana */
      }
    });
    stream = null;
  };

  const clearTimer = () => {
    if (autoStopTimer !== null) {
      clearTimeout(autoStopTimer);
      autoStopTimer = null;
    }
  };

  const settle = (result: RecordingResult) => {
    clearTimer();
    stopTracks();
    recorder = null;
    if (finished !== null) {
      const cb = finished;
      finished = null;
      cb(result);
    } else {
      lastResult = result;
    }
  };

  return {
    get recording(): boolean {
      return recorder !== null && recorder.state === "recording";
    },

    /** Prosi o mikrofon i startuje nagranie. Rzuca, gdy dostęp odmówiony —
     * wtedy ŻADNA ścieżka nie została otwarta. */
    async start(): Promise<void> {
      if (recorder !== null) throw new Error("Nagrywanie już trwa");
      cancelled = false;
      errored = false;
      stopRequested = false;
      lastResult = null;
      chunks = [];
      stream = await deps.getUserMedia();
      try {
        const mime = pickAudioMime(deps.isTypeSupported);
        recorder = deps.createRecorder(stream, mime);
      } catch (err) {
        // Recorder nie wstał (np. brak MediaRecorder) — mikrofon nie może
        // zostać otwarty.
        stopTracks();
        throw err;
      }
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };
      recorder.onerror = () => {
        errored = true;
        try {
          recorder?.stop();
        } catch {
          settle({ kind: "error", reason: "recorder_error" });
        }
      };
      recorder.onstop = () => {
        if (cancelled) return settle({ kind: "cancelled" });
        if (errored) return settle({ kind: "error", reason: "recorder_error" });
        const type = baseMime(recorder?.mimeType || "") || "audio/webm";
        const total = chunks.reduce((sum, c) => sum + c.size, 0);
        if (total === 0) return settle({ kind: "error", reason: "empty" });
        if (total > maxBytes) return settle({ kind: "error", reason: "too_large" });
        const file = makeFile(
          chunks, `wiadomosc-glosowa${extensionForMime(type)}`, type
        );
        settle({ kind: "ok", file });
      };
      try {
        recorder.start();
      } catch (err) {
        recorder = null;
        stopTracks();
        throw err;
      }
      autoStopTimer = setTimeout(() => {
        // Limit czasu: zatrzymaj nagranie; wynik czeka w lastResult na
        // stop() z UI (onAutoStop informuje widok, że nagranie stanęło).
        if (recorder !== null && !stopRequested) {
          stopRequested = true;
          try {
            recorder.stop();
          } catch {
            settle({ kind: "error", reason: "recorder_error" });
          }
        }
        deps.onAutoStop?.();
      }, maxDuration);
    },

    /** Kończy nagranie i zwraca wynik (plik z RZECZYWISTYM mimeType).
     * Bezpieczne także po auto-stopie limitu czasu (wynik zbuforowany). */
    stop(): Promise<RecordingResult> {
      if (lastResult !== null) {
        const result = lastResult;
        lastResult = null;
        return Promise.resolve(result);
      }
      if (recorder === null) return Promise.resolve({ kind: "cancelled" });
      return new Promise((resolve) => {
        finished = resolve;
        if (!stopRequested) {
          stopRequested = true;
          try {
            recorder?.stop();
          } catch {
            settle({ kind: "error", reason: "recorder_error" });
          }
        }
      });
    },

    /** Porzuca nagranie (nic nie zwraca) — ścieżki zatrzymane. */
    cancel(): void {
      cancelled = true;
      lastResult = null;
      if (recorder === null) return;
      if (!stopRequested) {
        stopRequested = true;
        try {
          recorder.stop();
        } catch {
          settle({ kind: "cancelled" });
        }
      }
    },

    /** Sprzątanie przy odmontowaniu komponentu — bezwarunkowe zatrzymanie
     * recordera i wszystkich ścieżek mikrofonu. */
    dispose(): void {
      cancelled = true;
      lastResult = null;
      if (recorder !== null && !stopRequested) {
        stopRequested = true;
        try {
          recorder.stop();
        } catch {
          /* recorder mógł już stanąć */
        }
      }
      settle({ kind: "cancelled" });
    },
  };
}

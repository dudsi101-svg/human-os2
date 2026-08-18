// Testy czystej logiki wiadomości realtime i nagrywania głosówek
// (src/messaging.ts, src/audioCapture.ts) w Node — bez przeglądarki
// i bez dodatkowych zależności. Uruchomienie: npm run test:helpers
// (kompiluje TS do katalogu tymczasowego i odpala node --test).

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
execFileSync("npx", ["tsc", "-p", join(here, "tsconfig.messaging.json")], {
  stdio: "inherit",
  cwd: join(here, ".."),
});
const outDir = join(here, "..", "node_modules", ".cache", "messaging-test");

const {
  applyReceipt,
  createSseParser,
  clearDraft,
  draftKey,
  loadDraft,
  mergeMessage,
  nextBackoffMs,
  BACKOFF_MAX_MS,
  saveDraft,
  sortMessages,
} = await import(pathToFileURL(join(outDir, "messaging.js")).href);

const {
  baseMime,
  createVoiceRecorder,
  extensionForMime,
  pickAudioMime,
} = await import(pathToFileURL(join(outDir, "audioCapture.js")).href);

const msg = (id, created_at, extra = {}) => ({
  id, author_id: "U1", body: "x", file_id: null, created_at,
  delivered_at: null, read_at: null, ...extra,
});

// --- Kolejność i scalanie ---------------------------------------------------

test("sortMessages: porządek (created_at, id) niezależnie od kolejności doręczeń", () => {
  const shuffled = [
    msg("B", "2026-08-18T10:00:00"),
    msg("C", "2026-08-18T09:00:00"),
    msg("A", "2026-08-18T10:00:00"),
  ];
  assert.deepEqual(sortMessages(shuffled).map((m) => m.id), ["C", "A", "B"]);
});

test("mergeMessage: duplikat zdarzenia (to samo id) nie tworzy drugiego dymka", () => {
  const list = [msg("A", "t1")];
  const merged = mergeMessage(list, msg("A", "t1", { read_at: "t2" }));
  assert.equal(merged.length, 1);
  assert.equal(merged[0].read_at, "t2");
});

test("mergeMessage: potwierdzenie serwera zastępuje optymistyczną po client_msg_id", () => {
  const list = [msg("local-1", "t1", { client_msg_id: "cid-123", pending: true })];
  const merged = mergeMessage(
    list, msg("HOS-MSG-1", "t1", { client_msg_id: "cid-123" })
  );
  assert.equal(merged.length, 1);
  assert.equal(merged[0].id, "HOS-MSG-1");
  assert.ok(!merged[0].pending);
});

test("mergeMessage: nowa wiadomość trafia na właściwe miejsce (zła kolejność zdarzeń)", () => {
  let list = [msg("B", "2026-08-18T10:05:00")];
  list = mergeMessage(list, msg("A", "2026-08-18T10:00:00")); // spóźnione starsze
  assert.deepEqual(list.map((m) => m.id), ["A", "B"]);
});

test("applyReceipt: znaczy tylko wskazane i nie cofa istniejących", () => {
  const list = [
    msg("A", "t1"),
    msg("B", "t2", { read_at: "wcześniej" }),
    msg("C", "t3"),
  ];
  const out = applyReceipt(list, ["A", "B"], "read_at", "teraz");
  assert.equal(out[0].read_at, "teraz");
  assert.equal(out[1].read_at, "wcześniej");
  assert.equal(out[2].read_at, null);
});

// --- Backoff (logika reconnect/fallback) -----------------------------------

test("nextBackoffMs: wykładniczy wzrost z sufitem", () => {
  assert.equal(nextBackoffMs(1), 1000);
  assert.equal(nextBackoffMs(2), 2000);
  assert.equal(nextBackoffMs(3), 4000);
  assert.equal(nextBackoffMs(6), 32000 > BACKOFF_MAX_MS ? BACKOFF_MAX_MS : 32000);
  assert.equal(nextBackoffMs(50), BACKOFF_MAX_MS);
});

// --- Parser SSE -------------------------------------------------------------

test("SSE: pojedyncze zdarzenie z id i typem", () => {
  const events = [];
  const p = createSseParser((e) => events.push(e));
  p.feed("id: M1\nevent: message.new\ndata: {\"a\":1}\n\n");
  assert.deepEqual(events, [{ event: "message.new", data: '{"a":1}', id: "M1" }]);
});

test("SSE: chunk przecięty w środku linii i CRLF", () => {
  const events = [];
  const p = createSseParser((e) => events.push(e));
  p.feed("event: mess");
  p.feed("age.read\r\ndata: {\"ids\":[");
  p.feed("\"x\"]}\r\n\r\n");
  assert.equal(events.length, 1);
  assert.equal(events[0].event, "message.read");
  assert.equal(events[0].data, '{"ids":["x"]}');
});

test("SSE: komentarze keepalive są ignorowane, wielolinijkowe data sklejane", () => {
  const events = [];
  const p = createSseParser((e) => events.push(e));
  p.feed(": keepalive\n\nevent: e\ndata: a\ndata: b\n\n: znowu\n\n");
  assert.deepEqual(events, [{ event: "e", data: "a\nb", id: null }]);
});

// --- Szkice (draft per wątek) ----------------------------------------------

function fakeStorage() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, v),
    removeItem: (k) => map.delete(k),
  };
}

test("draft: zapis/odczyt/czyszczenie per wątek (utrata sieci nie traci treści)", () => {
  const s = fakeStorage();
  saveDraft(s, "T1", "niedokończona wiadomość");
  saveDraft(s, "T2", "inny wątek");
  assert.equal(loadDraft(s, "T1"), "niedokończona wiadomość");
  assert.equal(loadDraft(s, "T2"), "inny wątek");
  clearDraft(s, "T1");
  assert.equal(loadDraft(s, "T1"), "");
  assert.equal(loadDraft(s, "T2"), "inny wątek");
  saveDraft(s, "T2", ""); // pusty tekst usuwa szkic
  assert.equal(loadDraft(s, "T2"), "");
  assert.ok(draftKey("T1").includes("T1"));
});

test("draft: awaria storage nie wywraca pisania", () => {
  const broken = {
    getItem: () => { throw new Error("quota"); },
    setItem: () => { throw new Error("quota"); },
    removeItem: () => { throw new Error("quota"); },
  };
  assert.equal(loadDraft(broken, "T1"), "");
  saveDraft(broken, "T1", "x"); // nie rzuca
  clearDraft(broken, "T1"); // nie rzuca
});

// --- Formaty audio ----------------------------------------------------------

test("pickAudioMime: webm/opus tam gdzie wspierany (Chrome/Firefox/Android)", () => {
  const supported = new Set(["audio/webm;codecs=opus", "audio/webm"]);
  assert.equal(pickAudioMime((t) => supported.has(t)), "audio/webm;codecs=opus");
});

test("pickAudioMime: iOS Safari bez webm dostaje audio/mp4 (AAC)", () => {
  const supported = new Set(["audio/mp4", "audio/mp4;codecs=mp4a.40.2"]);
  assert.equal(pickAudioMime((t) => supported.has(t)), "audio/mp4;codecs=mp4a.40.2");
});

test("pickAudioMime: nic wspieranego / brak isTypeSupported → wybór przeglądarki", () => {
  assert.equal(pickAudioMime(() => false), "");
  assert.equal(pickAudioMime(() => { throw new Error("brak API"); }), "");
});

test("baseMime + extensionForMime: rzeczywisty mimeType, nie sztywne audio/webm", () => {
  assert.equal(baseMime("audio/mp4;codecs=mp4a.40.2"), "audio/mp4");
  assert.equal(extensionForMime("audio/mp4;codecs=mp4a.40.2"), ".m4a");
  assert.equal(extensionForMime("audio/webm;codecs=opus"), ".webm");
  assert.equal(extensionForMime("audio/ogg"), ".ogg");
  assert.equal(extensionForMime("audio/mpeg"), ".mp3");
});

// --- Kontroler nagrywania ---------------------------------------------------

class FakeBlob {
  constructor(size) { this.size = size; }
}

function fakeRecorderEnv({ mimeType = "audio/webm;codecs=opus", denyMic = false } = {}) {
  const tracks = [{ stopped: false, stop() { this.stopped = true; } }];
  const stream = { getTracks: () => tracks };
  let recorder = null;
  const deps = {
    getUserMedia: () =>
      denyMic ? Promise.reject(new Error("NotAllowedError")) : Promise.resolve(stream),
    createRecorder: (_stream, _mime) => {
      recorder = {
        state: "inactive",
        mimeType,
        ondataavailable: null,
        onstop: null,
        onerror: null,
        start() { this.state = "recording"; },
        stop() {
          this.state = "inactive";
          // MediaRecorder dostarcza dane i onstop asynchronicznie.
          queueMicrotask(() => {
            this.ondataavailable?.({ data: new FakeBlob(1024) });
            this.onstop?.();
          });
        },
      };
      return recorder;
    },
    isTypeSupported: () => true,
    makeFile: (chunks, name, type) => ({
      name, type, size: chunks.reduce((s, c) => s + c.size, 0), isFile: true,
    }),
  };
  return { deps, tracks, getRecorder: () => recorder };
}

test("recorder: odmowa mikrofonu — start rzuca, żadna ścieżka nie otwarta", async () => {
  const { deps, tracks } = fakeRecorderEnv({ denyMic: true });
  const rec = createVoiceRecorder(deps);
  await assert.rejects(() => rec.start());
  assert.ok(tracks.every((t) => !t.stopped)); // nigdy nie wystartowały
  assert.equal(rec.recording, false);
});

test("recorder: stop zwraca plik z RZECZYWISTYM mimeType i zatrzymuje ścieżki", async () => {
  const { deps, tracks } = fakeRecorderEnv({ mimeType: "audio/mp4;codecs=mp4a.40.2" });
  const rec = createVoiceRecorder(deps);
  await rec.start();
  assert.equal(rec.recording, true);
  const result = await rec.stop();
  assert.equal(result.kind, "ok");
  assert.equal(result.file.type, "audio/mp4"); // typ bazowy do uploadu
  assert.equal(result.file.name, "wiadomosc-glosowa.m4a");
  assert.ok(tracks.every((t) => t.stopped));
});

test("recorder: anulowanie zatrzymuje ścieżki i nie zwraca pliku", async () => {
  const { deps, tracks } = fakeRecorderEnv();
  const rec = createVoiceRecorder(deps);
  await rec.start();
  rec.cancel();
  await new Promise((r) => setTimeout(r, 0));
  assert.ok(tracks.every((t) => t.stopped));
  const result = await rec.stop(); // po anulowaniu nie ma wyniku
  assert.equal(result.kind, "cancelled");
});

test("recorder: odmontowanie w trakcie nagrania (dispose) zatrzymuje wszystko", async () => {
  const { deps, tracks, getRecorder } = fakeRecorderEnv();
  const rec = createVoiceRecorder(deps);
  await rec.start();
  rec.dispose();
  assert.ok(tracks.every((t) => t.stopped));
  assert.equal(getRecorder().state, "inactive");
  assert.equal(rec.recording, false);
});

test("recorder: błąd recordera zatrzymuje ścieżki i zgłasza błąd", async () => {
  const { deps, tracks, getRecorder } = fakeRecorderEnv();
  const rec = createVoiceRecorder(deps);
  await rec.start();
  const pending = rec.stop();
  getRecorder().onerror?.(new Error("awaria sprzętu"));
  const result = await pending;
  assert.equal(result.kind, "error");
  assert.ok(tracks.every((t) => t.stopped));
});

test("recorder: limit rozmiaru — zbyt duże nagranie odrzucone, ścieżki stoją", async () => {
  const { deps, tracks, getRecorder } = fakeRecorderEnv();
  const rec = createVoiceRecorder({ ...deps, maxBytes: 100 });
  await rec.start();
  const pending = rec.stop();
  // fake dostarcza 1024 B > 100 B
  const result = await pending;
  assert.equal(result.kind, "error");
  assert.equal(result.reason, "too_large");
  assert.ok(tracks.every((t) => t.stopped));
  assert.ok(getRecorder());
});

test("recorder: auto-stop po limicie czasu — wynik czeka na stop()", async () => {
  const { deps } = fakeRecorderEnv();
  let autoStopped = false;
  const rec = createVoiceRecorder({
    ...deps, maxDurationMs: 10, onAutoStop: () => { autoStopped = true; },
  });
  await rec.start();
  await new Promise((r) => setTimeout(r, 30));
  assert.equal(autoStopped, true);
  const result = await rec.stop(); // wynik zbuforowany po auto-stopie
  assert.equal(result.kind, "ok");
});

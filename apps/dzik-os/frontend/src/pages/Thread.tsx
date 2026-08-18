import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, getUser, handleSessionExpired, isCancel } from "../api";
import { plDateTime } from "../dates";
import { AuthAttachment, ErrorBox, Icon, Spinner, TopBar } from "../components";
import { MessageRow } from "../types";
import {
  FALLBACK_POLL_MS,
  applyReceipt,
  clearDraft,
  loadDraft,
  mergeMessage,
  saveDraft,
  sortMessages,
} from "../messaging";
import { connectRealtime } from "../realtime";
import {
  MAX_RECORDING_MS,
  MediaRecorderLike,
  createVoiceRecorder,
} from "../audioCapture";

const UPLOAD_ACCEPT =
  "image/jpeg,image/png,image/webp,application/pdf,video/mp4," +
  "audio/webm,audio/mp4,audio/mpeg,audio/ogg";

const PAGE_SIZE = 50;

/** Status własnej wiadomości pod dymkiem. */
function ownStatus(m: MessageRow): string {
  if (m.pending) return "wysyłanie…";
  if (m.read_at) return "przeczytano";
  if (m.delivered_at) return "dostarczono";
  return "wysłano";
}

export default function Thread() {
  const { threadId } = useParams();
  const user = getUser()!;
  const [messages, setMessages] = useState<MessageRow[] | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [channelDown, setChannelDown] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const recorderRef = useRef<ReturnType<typeof createVoiceRecorder> | null>(null);
  const recordTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const messagesRef = useRef<MessageRow[] | null>(null);
  messagesRef.current = messages;

  const filePreviewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => {
    // Zwolnienie Blob URL podglądu przy każdej zmianie pliku i odmontowaniu.
    if (filePreviewUrl) URL.revokeObjectURL(filePreviewUrl);
  }, [filePreviewUrl]);

  const scrollDown = () => setTimeout(() => bottom.current?.scrollIntoView(), 50);

  const load = (signal?: AbortSignal) => {
    setError(null);
    return api.get<{ messages: MessageRow[]; has_more: boolean }>(
      `/api/threads/${threadId}/messages?limit=${PAGE_SIZE}`, { signal }
    )
      .then((d) => {
        // Lokalne wiadomości „w drodze" nie mogą zniknąć przy odświeżeniu.
        const pending = (messagesRef.current ?? []).filter((m) => m.pending);
        setMessages(sortMessages([...d.messages, ...pending]));
        setHasMore(d.has_more);
        scrollDown();
      })
      .catch((e) => {
        // Zmiana wątku anuluje poprzednie pobranie — spóźniona odpowiedź
        // nie może nadpisać nowego wątku ani pokazać mylącego błędu.
        if (!isCancel(e)) setError(e.message);
      });
  };

  // Szkic per wątek: przywrócenie przy wejściu, zapis przy każdej zmianie —
  // treść przeżywa utratę sieci, nawigację i przeładowanie widoku.
  useEffect(() => {
    if (threadId) setBody(loadDraft(sessionStorage, threadId));
  }, [threadId]);
  useEffect(() => {
    if (threadId) saveDraft(sessionStorage, threadId, body);
  }, [threadId, body]);

  // Pobranie historii + kanał realtime (SSE) z bezpiecznym fallbackiem.
  useEffect(() => {
    const ac = new AbortController();
    load(ac.signal);

    let down = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    const startPolling = () => {
      if (pollTimer !== null) return;
      // Kontrolowany polling WYŁĄCZNIE na otwartym ekranie rozmowy,
      // dopóki kanał realtime nie wróci.
      pollTimer = setInterval(() => {
        if (!document.hidden) load(ac.signal);
      }, FALLBACK_POLL_MS);
    };
    const stopPolling = () => {
      if (pollTimer !== null) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    void connectRealtime("/api/threads/events", {
      onEvent: (type, data) => {
        const ev = data as {
          thread_id?: string;
          message?: MessageRow;
          message_id?: string;
          message_ids?: string[];
          read_at?: string;
          delivered_at?: string;
        };
        if (type === "resync") {
          load(ac.signal);
          return;
        }
        if (ev.thread_id !== threadId) return; // zdarzenie innego wątku
        if (type === "message.new" && ev.message) {
          const incoming = ev.message;
          setMessages((prev) => mergeMessage(prev ?? [], incoming));
          scrollDown();
          if (incoming.author_id !== user.id) {
            // Ekran rozmowy jest otwarty — od razu oznacz jako przeczytane
            // (nadawca dostaje potwierdzenie swoim kanałem).
            api.post(`/api/threads/${threadId}/read`).catch(() => {
              /* Świadomie: brak sieci nie może wywrócić odbioru wiadomości;
               * status doprze przy następnym otwarciu/odświeżeniu. */
            });
          }
        } else if (type === "message.read" && ev.message_ids && ev.read_at) {
          const ids = ev.message_ids;
          const stamp = ev.read_at;
          setMessages((prev) =>
            prev
              ? applyReceipt(
                  applyReceipt(prev, ids, "read_at", stamp),
                  ids, "delivered_at", stamp
                )
              : prev
          );
        } else if (type === "message.delivered" && ev.message_id && ev.delivered_at) {
          const ids = [ev.message_id];
          const stamp = ev.delivered_at;
          setMessages((prev) =>
            prev ? applyReceipt(prev, ids, "delivered_at", stamp) : prev
          );
        }
      },
      onChannelState: (state) => {
        down = state === "down";
        setChannelDown(down);
        if (down) startPolling();
        else {
          stopPolling();
          load(ac.signal); // nadrób ewentualną lukę z okresu bez kanału
        }
      },
      onSessionExpired: handleSessionExpired,
    }, ac.signal);

    return () => {
      ac.abort();
      stopPolling();
    };
  }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sprzątanie nagrywania przy odmontowaniu — wszystkie ścieżki mikrofonu
  // muszą zostać zatrzymane, nawet gdy użytkownik wyjdzie w trakcie nagrania.
  useEffect(() => () => {
    recorderRef.current?.dispose();
    if (recordTimerRef.current) clearInterval(recordTimerRef.current);
  }, []);

  const stopRecordTicker = () => {
    if (recordTimerRef.current) {
      clearInterval(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    setRecordSeconds(0);
  };

  async function startRecording() {
    setError(null);
    const recorder = createVoiceRecorder({
      getUserMedia: () => navigator.mediaDevices.getUserMedia({ audio: true }),
      createRecorder: (stream, mimeType) =>
        // Rzutowanie strukturalne: DOM-owy MediaRecorder spełnia kontrakt
        // MediaRecorderLike (ondataavailable dostaje nadzbiór {data: Blob}).
        new MediaRecorder(
          stream as MediaStream,
          mimeType ? { mimeType } : undefined
        ) as unknown as MediaRecorderLike,
      isTypeSupported: (t) =>
        typeof MediaRecorder !== "undefined" &&
        typeof MediaRecorder.isTypeSupported === "function" &&
        MediaRecorder.isTypeSupported(t),
      // Limit czasu osiągnięty: nagranie już stanęło w kontrolerze —
      // odbierz gotowy wynik tą samą ścieżką co ręczny Stop.
      onAutoStop: () => { void stopRecording(); },
    });
    try {
      await recorder.start();
    } catch {
      setError("Brak dostępu do mikrofonu — sprawdź uprawnienia przeglądarki.");
      return;
    }
    recorderRef.current = recorder;
    setRecording(true);
    setRecordSeconds(0);
    recordTimerRef.current = setInterval(
      () => setRecordSeconds((s) => s + 1), 1000
    );
  }

  async function stopRecording() {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    stopRecordTicker();
    if (!recorder) return;
    const result = await recorder.stop();
    if (result.kind === "ok") {
      setFile(result.file); // typ pliku = rzeczywisty mimeType recordera
    } else if (result.kind === "error") {
      setError(
        result.reason === "too_large"
          ? "Nagranie jest zbyt duże — nagraj krótszą wiadomość."
          : "Nagranie nie powiodło się. Spróbuj ponownie."
      );
    }
  }

  function cancelRecording() {
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setRecording(false);
    stopRecordTicker();
  }

  async function loadOlder() {
    const oldest = messages?.find((m) => !m.pending);
    if (!oldest) return;
    setLoadingOlder(true);
    try {
      const d = await api.get<{ messages: MessageRow[]; has_more: boolean }>(
        `/api/threads/${threadId}/messages?limit=${PAGE_SIZE}&before=${oldest.id}`
      );
      setMessages((prev) => sortMessages([...d.messages, ...(prev ?? [])]));
      setHasMore(d.has_more);
    } catch (err) {
      if (!isCancel(err)) setError((err as Error).message);
    } finally {
      setLoadingOlder(false);
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!body.trim() && !file) return;
    setBusy(true);
    setError(null);
    // Identyfikator kliencki: ponowienie po utracie sieci nie zduplikuje
    // wiadomości (backend deduplikuje po (wątek, autor, client_msg_id)).
    const clientMsgId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const text = body.trim() || (file ? `📎 ${file.name}` : "");
    try {
      let file_id: string | null = null;
      if (file) {
        const up = await api.upload<{ id: string }>("/api/files", file);
        file_id = up.id;
      }
      // Optymistyczny dymek „wysyłanie…" — zastąpiony potwierdzeniem serwera.
      const optimistic: MessageRow = {
        id: `local-${clientMsgId}`,
        author_id: user.id,
        body: text,
        file_id,
        created_at: new Date().toISOString(),
        delivered_at: null,
        read_at: null,
        client_msg_id: clientMsgId,
        pending: true,
      };
      setMessages((prev) => sortMessages([...(prev ?? []), optimistic]));
      scrollDown();
      const confirmed = await api.post<MessageRow>(
        `/api/threads/${threadId}/messages`,
        { body: text, file_id, client_msg_id: clientMsgId }
      );
      setMessages((prev) =>
        mergeMessage(
          (prev ?? []).filter((m) => m.id !== optimistic.id),
          { ...confirmed, pending: false }
        )
      );
      setBody("");
      setFile(null);
      if (threadId) clearDraft(sessionStorage, threadId);
    } catch (err) {
      // Niepowodzenie: dymek „w drodze" znika, a treść ZOSTAJE w polu
      // (szkic per wątek trzyma ją też po przeładowaniu widoku).
      setMessages((prev) =>
        (prev ?? []).filter((m) => m.client_msg_id !== clientMsgId)
      );
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !messages) {
    return <div className="page"><ErrorBox error={error} onRetry={() => load()} /></div>;
  }
  if (!messages) return <div className="page"><Spinner /></div>;

  const maxRecordS = Math.floor(MAX_RECORDING_MS / 1000);

  return (
    <div className="page">
      <TopBar title="Rozmowa" />
      {channelDown && (
        <p className="dim" style={{ margin: "4px 0" }}>
          Tryb offline kanału na żywo — wiadomości odświeżają się co kilkanaście sekund.
        </p>
      )}
      <div>
        {hasMore && (
          <div style={{ textAlign: "center", margin: "6px 0" }}>
            <button type="button" className="btn btn--ghost btn--small"
              onClick={loadOlder} disabled={loadingOlder}>
              {loadingOlder ? "Wczytywanie…" : "Wczytaj starsze wiadomości"}
            </button>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.author_id === user.id ? "msg--own" : "msg--other"}`}>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.body}</div>
            {m.file_id && (
              <div style={{ marginTop: 6, maxWidth: 240 }}>
                <AuthAttachment fileId={m.file_id} />
              </div>
            )}
            <small>
              {plDateTime(m.created_at)}
              {m.author_id === user.id && ` · ${ownStatus(m)}`}
            </small>
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form onSubmit={send} className="card" style={{ position: "sticky", bottom: "calc(var(--nav-h) + 8px)" }}>
        <ErrorBox error={error} />
        <textarea placeholder="Napisz wiadomość…" aria-label="Treść wiadomości" value={body}
          onChange={(e) => setBody(e.target.value)} style={{ minHeight: 56 }} />
        {file && file.type.startsWith("audio/") && filePreviewUrl && (
          <div className="row row--between" style={{ marginTop: 8 }}>
            <audio controls src={filePreviewUrl} style={{ maxWidth: 200 }}
              aria-label="Podgląd nagranej wiadomości głosowej" />
            <button type="button" className="btn btn--ghost btn--small"
              onClick={() => { setFile(null); startRecording(); }}
              title="Nagraj od nowa" aria-label="Nagraj od nowa">
              ↺ nagraj ponownie
            </button>
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setFile(null)}>
              <Icon name="close" size={14} /> usuń
            </button>
          </div>
        )}
        <div className="row" style={{ marginTop: 8 }}>
          <input type="file" accept={UPLOAD_ACCEPT} aria-label="Załącz plik"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="grow" style={{ padding: 6 }} />
          {!recording ? (
            <button type="button" className="btn btn--ghost btn--small" onClick={startRecording}
              title="Nagraj wiadomość głosową" aria-label="Nagraj wiadomość głosową">
              <Icon name="mic" size={18} />
            </button>
          ) : (
            <>
              <span className="dim" role="status" aria-live="polite"
                style={{ alignSelf: "center", fontVariantNumeric: "tabular-nums" }}>
                ● {Math.floor(recordSeconds / 60)}:{String(recordSeconds % 60).padStart(2, "0")} / {Math.floor(maxRecordS / 60)}:00
              </span>
              <button type="button" className="btn btn--ghost btn--small" onClick={cancelRecording}
                title="Odrzuć nagranie" aria-label="Odrzuć nagranie">✕</button>
              <button type="button" className="btn btn--danger btn--small" onClick={stopRecording}>
                <Icon name="stop" size={16} /> Stop
              </button>
            </>
          )}
          <button className="btn btn--small" disabled={busy}>Wyślij</button>
        </div>
      </form>
    </div>
  );
}

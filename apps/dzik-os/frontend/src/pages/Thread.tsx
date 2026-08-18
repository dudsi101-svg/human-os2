import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, getUser } from "../api";
import { plDateTime } from "../dates";
import { AuthAttachment, ErrorBox, Spinner, TopBar } from "../components";
import { MessageRow } from "../types";

const UPLOAD_ACCEPT =
  "image/jpeg,image/png,image/webp,application/pdf,video/mp4," +
  "audio/webm,audio/mp4,audio/mpeg,audio/ogg";

export default function Thread() {
  const { threadId } = useParams();
  const user = getUser()!;
  const [messages, setMessages] = useState<MessageRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const filePreviewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => {
    if (filePreviewUrl) URL.revokeObjectURL(filePreviewUrl);
  }, [filePreviewUrl]);

  const load = () =>
    api.get<{ messages: MessageRow[] }>(`/api/threads/${threadId}/messages`)
      .then((d) => {
        setMessages(d.messages);
        setTimeout(() => bottom.current?.scrollIntoView(), 50);
      })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setFile(new File([blob], "wiadomosc-glosowa.webm", { type: "audio/webm" }));
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Brak dostępu do mikrofonu — sprawdź uprawnienia przeglądarki.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!body.trim() && !file) return;
    setBusy(true);
    try {
      let file_id: string | null = null;
      if (file) {
        const up = await api.upload<{ id: string }>("/api/files", file);
        file_id = up.id;
      }
      await api.post(`/api/threads/${threadId}/messages`, {
        body: body.trim() || (file ? `📎 ${file.name}` : ""),
        file_id,
      });
      setBody("");
      setFile(null);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !messages) return <div className="page"><ErrorBox error={error} /></div>;
  if (!messages) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Rozmowa" />
      <div>
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
              {m.author_id === user.id && m.read_at && " · przeczytano"}
            </small>
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form onSubmit={send} className="card" style={{ position: "sticky", bottom: "calc(var(--nav-h) + 8px)" }}>
        <ErrorBox error={error} />
        <textarea placeholder="Napisz wiadomość…" value={body}
          onChange={(e) => setBody(e.target.value)} style={{ minHeight: 56 }} />
        {file && file.type.startsWith("audio/") && filePreviewUrl && (
          <div className="row row--between" style={{ marginTop: 8 }}>
            <audio controls src={filePreviewUrl} style={{ maxWidth: 220 }} />
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setFile(null)}>
              ✕ usuń
            </button>
          </div>
        )}
        <div className="row" style={{ marginTop: 8 }}>
          <input type="file" accept={UPLOAD_ACCEPT}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="grow" style={{ padding: 6 }} />
          {!recording ? (
            <button type="button" className="btn btn--ghost btn--small" onClick={startRecording}
              title="Nagraj wiadomość głosową">🎤</button>
          ) : (
            <button type="button" className="btn btn--danger btn--small" onClick={stopRecording}>
              ⏹ Stop
            </button>
          )}
          <button className="btn btn--small" disabled={busy}>Wyślij</button>
        </div>
      </form>
    </div>
  );
}

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, getUser, plDateTime } from "../api";
import { AuthImage, ErrorBox, Spinner, TopBar } from "../components";
import { MessageRow } from "../types";

export default function Thread() {
  const { threadId } = useParams();
  const user = getUser()!;
  const [messages, setMessages] = useState<MessageRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const load = () =>
    api.get<{ messages: MessageRow[] }>(`/api/threads/${threadId}/messages`)
      .then((d) => {
        setMessages(d.messages);
        setTimeout(() => bottom.current?.scrollIntoView(), 50);
      })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

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

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
  if (!messages) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Rozmowa" />
      <div>
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.author_id === user.id ? "msg--own" : "msg--other"}`}>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.body}</div>
            {m.file_id && (
              <div style={{ marginTop: 6, maxWidth: 220 }}>
                <AuthImage fileId={m.file_id} alt="załącznik" />
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
        <textarea placeholder="Napisz wiadomość…" value={body}
          onChange={(e) => setBody(e.target.value)} style={{ minHeight: 56 }} />
        <div className="row" style={{ marginTop: 8 }}>
          <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf,video/mp4"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="grow" style={{ padding: 6 }} />
          <button className="btn btn--small" disabled={busy}>Wyślij</button>
        </div>
      </form>
    </div>
  );
}

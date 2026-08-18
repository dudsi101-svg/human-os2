import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { plDateTime } from "../dates";
import { ErrorBox, Spinner, TopBar } from "../components";
import { ThreadRow } from "../types";

export default function Messages() {
  const [threads, setThreads] = useState<ThreadRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<{ threads: ThreadRow[] }>("/api/threads")
      .then((d) => setThreads(d.threads))
      .catch((e) => setError(e.message));
  };
  useEffect(() => {
    load();
    // Kontrolowane odświeżanie listy WYŁĄCZNIE na otwartym ekranie
    // wiadomości (liczniki nieprzeczytanych): co 30 s + przy powrocie do
    // karty. Kanał na żywo działa w otwartej rozmowie (Thread.tsx).
    const timer = setInterval(() => {
      if (!document.hidden) load();
    }, 30_000);
    const onVisible = () => {
      if (!document.hidden) load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!threads) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Wiadomości" />
      {threads.length === 0 && <p className="dim">Brak wątków.</p>}
      <div className="list">
        {threads.map((t) => (
          <Link to={`/wiadomosci/${t.id}`} key={t.id} className="card" style={{ display: "block" }}>
            <div className="row row--between">
              <b style={{ color: "var(--text)" }}>{t.with_user.display_name}</b>
              {t.unread > 0 && <span className="badge badge--accent">{t.unread} nowe</span>}
            </div>
            {t.last_message && (
              <small>
                {t.last_message.body}
                <span className="dim"> · {plDateTime(t.last_message.created_at)}</span>
              </small>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

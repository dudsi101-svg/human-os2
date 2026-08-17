import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, plDateTime } from "../api";
import { ErrorBox, Spinner, TopBar } from "../components";
import { ThreadRow } from "../types";

export default function Messages() {
  const [threads, setThreads] = useState<ThreadRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ threads: ThreadRow[] }>("/api/threads")
      .then((d) => setThreads(d.threads))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
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

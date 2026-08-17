import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, plDate } from "../../api";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import { CoachClientRow } from "../../types";

type Filter = "all" | "checkin" | "payment" | "messages" | "pain" | "observation";

export default function Clients() {
  const [clients, setClients] = useState<CoachClientRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [showNew, setShowNew] = useState(false);
  const [newClient, setNewClient] = useState({ client_name: "", client_email: "", initial_password: "" });

  const load = () =>
    api.get<{ clients: CoachClientRow[] }>("/api/coach/clients")
      .then((d) => setClients(d.clients))
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function createClient(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/coach/clients", newClient);
      setShowNew(false);
      setNewClient({ client_name: "", client_email: "", initial_password: "" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error && !clients) return <div className="page"><ErrorBox error={error} /></div>;
  if (!clients) return <div className="page"><Spinner /></div>;

  const filtered = clients.filter((c) => {
    if (query && !c.display_name.toLowerCase().includes(query.toLowerCase()) &&
        !c.email.toLowerCase().includes(query.toLowerCase())) return false;
    switch (filter) {
      case "checkin": return c.flags.checkin_overdue;
      case "payment": return c.flags.payment_overdue;
      case "messages": return c.flags.unread_messages > 0;
      case "pain": return c.flags.recent_pain_reports > 0;
      case "observation": return c.flags.flagged_observations > 0;
      default: return true;
    }
  });

  return (
    <div className="page page--wide">
      <TopBar title="Klienci" right={<LogoutButton />} />
      <ErrorBox error={error} />
      <div className="row" style={{ marginBottom: 10 }}>
        <input placeholder="Szukaj po nazwisku lub e-mailu…" value={query}
          onChange={(e) => setQuery(e.target.value)} className="grow" />
        <button className="btn btn--small" onClick={() => setShowNew(!showNew)}>
          + Nowy klient
        </button>
      </div>
      {showNew && (
        <form className="card card--accent" onSubmit={createClient}>
          <h3>Nowy podopieczny</h3>
          <label>Imię i nazwisko</label>
          <input required value={newClient.client_name}
            onChange={(e) => setNewClient({ ...newClient, client_name: e.target.value })} />
          <label>E-mail</label>
          <input type="email" required value={newClient.client_email}
            onChange={(e) => setNewClient({ ...newClient, client_email: e.target.value })} />
          <label>Hasło startowe (min. 10 znaków — klient zmieni po zalogowaniu)</label>
          <input required minLength={10} value={newClient.initial_password}
            onChange={(e) => setNewClient({ ...newClient, initial_password: e.target.value })} />
          <small>
            Zakładając konto potwierdzasz, że klient wyraził zgodę na
            przetwarzanie danych w celu prowadzenia trenerskiego. Klient
            zobaczy tę zgodę w aplikacji i może ją cofnąć.
          </small>
          <div style={{ marginTop: 10 }}>
            <button className="btn">Załóż konto i rozpocznij współpracę</button>
          </div>
        </form>
      )}
      <div className="tabs">
        {([
          ["all", `Wszyscy (${clients.length})`],
          ["checkin", `Zaległy raport (${clients.filter((c) => c.flags.checkin_overdue).length})`],
          ["payment", `Zaległa płatność (${clients.filter((c) => c.flags.payment_overdue).length})`],
          ["messages", `Nowe wiadomości (${clients.filter((c) => c.flags.unread_messages > 0).length})`],
          ["pain", `Zgłoszony ból (${clients.filter((c) => c.flags.recent_pain_reports > 0).length})`],
          ["observation", `Niepokojąca obserwacja (${clients.filter((c) => c.flags.flagged_observations > 0).length})`],
        ] as [Filter, string][]).map(([key, label]) => (
          <button key={key} className={filter === key ? "active" : ""}
            onClick={() => setFilter(key)}>{label}</button>
        ))}
      </div>
      <div className="list">
        {filtered.map((c) => (
          <Link to={`/trener/klient/${c.client_id}`} key={c.client_id} className="card"
            style={{ display: "block" }}>
            <div className="row row--between">
              <b style={{ color: "var(--text)" }}>{c.display_name}</b>
              <div className="row" style={{ gap: 6 }}>
                {!c.consent_active && <span className="badge badge--danger">brak zgody</span>}
                {c.relationship_status !== "ACTIVE" && (
                  <span className="badge">{c.relationship_status === "PAUSED" ? "pauza" : "zakończona"}</span>
                )}
                {c.flags.checkin_overdue && <span className="badge badge--warn">raport</span>}
                {c.flags.payment_overdue && <span className="badge badge--danger">płatność</span>}
                {c.flags.unread_messages > 0 && (
                  <span className="badge badge--accent">✉ {c.flags.unread_messages}</span>
                )}
                {c.flags.recent_pain_reports > 0 && <span className="badge badge--danger">ból</span>}
                {c.flags.flagged_observations > 0 && (
                  <span className="badge badge--danger">⚠ obserwacja</span>
                )}
              </div>
            </div>
            <small>
              {c.email} · ostatni raport:{" "}
              {c.last_checkin_week ? plDate(c.last_checkin_week) : "brak"}
            </small>
          </Link>
        ))}
        {filtered.length === 0 && <p className="dim">Brak klientów spełniających kryteria.</p>}
      </div>
    </div>
  );
}

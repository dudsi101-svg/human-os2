import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import { CoachClientRow, CoachDashboardData } from "../../types";

type Filter = "all" | "review" | "checkin" | "payment" | "messages" | "pain" | "observation";

interface InvitationInfo {
  id: string;
  expires_at: string;
  delivery: "email" | "manual";
  activation_link?: string;
}

interface CreateClientResponse {
  client_id: string;
  relationship_id: string;
  invitation: InvitationInfo | null;
}

/** Panel z wynikiem zaproszenia. Przy NullProvider (brak dostawcy e-mail)
 * link aktywacyjny wraca trenerowi jako „link do przekazania" — świadomy
 * kompromis opisany w docs/PERMISSIONS.md; ze skonfigurowanym dostawcą
 * link idzie WYŁĄCZNIE e-mailem i trener go nie widzi. */
function InvitationPanel({ invitation, onClose }: { invitation: InvitationInfo; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="card card--accent">
      <h3>Zaproszenie wysłane</h3>
      {invitation.delivery === "email" ? (
        <p>
          Klient otrzymał e-mail z jednorazowym linkiem aktywacyjnym
          (ważny do {plDate(invitation.expires_at)}). Sam ustawi swoje hasło —
          nikt inny go nie pozna.
        </p>
      ) : (
        <>
          <p>
            Wysyłka e-mail nie jest skonfigurowana, więc przekaż klientowi
            poniższy jednorazowy link aktywacyjny (ważny do{" "}
            {plDate(invitation.expires_at)}) zaufanym kanałem. Klient sam
            ustawi hasło — Ty go nigdy nie poznasz.
          </p>
          <p style={{ fontFamily: "monospace", fontSize: "0.8rem", wordBreak: "break-all" }}>
            {invitation.activation_link}
          </p>
          <div className="row">
            <button className="btn btn--small" onClick={async () => {
              await navigator.clipboard?.writeText(invitation.activation_link ?? "");
              setCopied(true);
            }}>
              {copied ? "Skopiowano ✓" : "Kopiuj link"}
            </button>
          </div>
        </>
      )}
      <div style={{ marginTop: 8 }}>
        <button className="btn btn--ghost btn--small" onClick={onClose}>Zamknij</button>
      </div>
    </div>
  );
}

export default function Clients() {
  const [clients, setClients] = useState<CoachClientRow[] | null>(null);
  const [dashboard, setDashboard] = useState<CoachDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [showNew, setShowNew] = useState(false);
  const [newClient, setNewClient] = useState({ client_name: "", client_email: "" });
  const [invitation, setInvitation] = useState<InvitationInfo | null>(null);

  const load = () => {
    api.get<{ clients: CoachClientRow[] }>("/api/coach/clients")
      .then((d) => setClients(d.clients))
      .catch((e) => setError(e.message));
    api.get<CoachDashboardData>("/api/coach/dashboard")
      .then(setDashboard)
      .catch(() => undefined);
  };
  useEffect(() => { load(); }, []);

  async function createClient(e: FormEvent) {
    e.preventDefault();
    try {
      const r = await api.post<CreateClientResponse>("/api/coach/clients", newClient);
      setShowNew(false);
      setNewClient({ client_name: "", client_email: "" });
      setInvitation(r.invitation);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function resendInvitation(clientId: string) {
    setError(null);
    try {
      const r = await api.post<{ invitation: InvitationInfo }>(
        `/api/coach/clients/${clientId}/invitations`
      );
      setInvitation(r.invitation);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function cancelInvitation(clientId: string) {
    if (!confirm("Anulować zaproszenie? Link aktywacyjny przestanie działać.")) return;
    setError(null);
    try {
      await api.post(`/api/coach/clients/${clientId}/invitations/cancel`);
      setInvitation(null);
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
      case "review": return c.flags.awaiting_review;
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
      {dashboard && (
        <div className="card" style={{ marginBottom: 10 }}>
          <h3 style={{ marginTop: 0 }}>Dashboard</h3>
          <p className="dim" style={{ fontSize: "0.82rem", marginTop: -4 }}>
            Metadane operacyjne — co wymaga Twojej uwagi teraz, nie ranking klientów.
          </p>
          <div className="stat-grid">
            <div className="stat"><b>{dashboard.active_clients}</b><span>aktywni klienci</span></div>
            <div className="stat"><b>{dashboard.awaiting_review}</b><span>raporty do oceny</span></div>
            <div className="stat"><b>{dashboard.upcoming_consultations}</b><span>konsultacje</span></div>
            <div className="stat"><b>{dashboard.checkin_overdue_clients}</b><span>zaległe raporty</span></div>
            <div className="stat"><b>{dashboard.payment_overdue_clients}</b><span>zaległe płatności</span></div>
            <div className="stat"><b>{dashboard.unread_messages_total}</b><span>nieprzeczytane wiadomości</span></div>
            <div className="stat"><b>{dashboard.flagged_observations_14d}</b><span>obserwacje (14 dni)</span></div>
          </div>
        </div>
      )}
      <div className="row" style={{ marginBottom: 10 }}>
        <input placeholder="Szukaj po nazwisku lub e-mailu…" value={query}
          onChange={(e) => setQuery(e.target.value)} className="grow" />
        <button className="btn btn--small" onClick={() => setShowNew(!showNew)}>
          + Nowy klient
        </button>
      </div>
      {invitation && (
        <InvitationPanel invitation={invitation} onClose={() => setInvitation(null)} />
      )}
      {showNew && (
        <form className="card card--accent" onSubmit={createClient}>
          <h3>Zaproś podopiecznego</h3>
          <label>Imię i nazwisko</label>
          <input required value={newClient.client_name}
            onChange={(e) => setNewClient({ ...newClient, client_name: e.target.value })} />
          <label>E-mail</label>
          <input type="email" required value={newClient.client_email}
            onChange={(e) => setNewClient({ ...newClient, client_email: e.target.value })} />
          <small>
            Klient otrzyma jednorazowy link aktywacyjny i SAM ustawi swoje
            hasło — nikt go nie zobaczy. Zapraszając potwierdzasz, że klient
            wyraził zgodę na przetwarzanie danych w celu prowadzenia
            trenerskiego; zobaczy ją w aplikacji i może ją cofnąć.
          </small>
          <div style={{ marginTop: 10 }}>
            <button className="btn">Wyślij zaproszenie</button>
          </div>
        </form>
      )}
      <div className="tabs">
        {([
          ["all", `Wszyscy (${clients.length})`],
          ["review", `Raport do oceny (${clients.filter((c) => c.flags.awaiting_review).length})`],
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
                {c.account_pending && (
                  <span className="badge badge--warn">oczekuje na aktywację</span>
                )}
                {!c.account_pending && !c.consent_active && <span className="badge badge--danger">brak zgody</span>}
                {c.relationship_status !== "ACTIVE" && (
                  <span className="badge">{c.relationship_status === "PAUSED" ? "pauza" : "zakończona"}</span>
                )}
                {c.flags.awaiting_review && <span className="badge badge--accent">raport do oceny</span>}
                {c.flags.checkin_overdue && <span className="badge badge--warn">zaległy raport</span>}
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
            {c.account_pending && (
              <div className="row" style={{ marginTop: 8, gap: 6 }}>
                <small className="dim">
                  {c.invitation_expires_at
                    ? `zaproszenie ważne do ${plDate(c.invitation_expires_at)}`
                    : "brak aktywnego zaproszenia"}
                </small>
                <button className="btn btn--ghost btn--small"
                  onClick={(e) => { e.preventDefault(); resendInvitation(c.client_id); }}>
                  Wyślij ponownie
                </button>
                {c.invitation_expires_at && (
                  <button className="btn btn--ghost btn--small"
                    onClick={(e) => { e.preventDefault(); cancelInvitation(c.client_id); }}>
                    Anuluj
                  </button>
                )}
              </div>
            )}
          </Link>
        ))}
        {filtered.length === 0 && <p className="dim">Brak klientów spełniających kryteria.</p>}
      </div>
    </div>
  );
}

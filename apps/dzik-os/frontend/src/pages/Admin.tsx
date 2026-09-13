import { useEffect, useState } from "react";
import { api } from "../api";
import { plDateTime } from "../dates";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../components";
import { ReceiptRow } from "../types";

interface UserRow {
  id: string;
  email: string;
  display_name: string;
  status: string;
  roles: string[];
  created_at: string;
  last_login_at: string | null;
}

export default function Admin() {
  const [users, setUsers] = useState<UserRow[] | null>(null);
  const [receipts, setReceipts] = useState<ReceiptRow[]>([]);
  const [chain, setChain] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Poczta Brevo (0.61.0): karta testu wysyłki tylko, gdy endpoint jest włączony flagą.
  const [pocztaTest, setPocztaTest] = useState(false);
  const [adres, setAdres] = useState("");
  const [wynikPoczty, setWynikPoczty] = useState<string | null>(null);
  const [wysylanie, setWysylanie] = useState(false);

  const load = () => {
    setError(null);
    api.get<{ users: UserRow[] }>("/api/admin/users")
      .then((d) => setUsers(d.users)).catch((e) => setError(e.message));
    // Pokwitowania audytu to osobna sekcja — błąd jest widoczny, nie cichy.
    api.get<{ receipts: ReceiptRow[] }>("/api/admin/receipts?limit=50")
      .then((d) => setReceipts(d.receipts))
      .catch((e) => setError(`Nie udało się wczytać pokwitowań audytu. ${e.message}`));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    api.get<{ features?: { mail_test_endpoint?: boolean } }>("/api/health")
      .then((h) => setPocztaTest(!!h.features?.mail_test_endpoint)).catch(() => setPocztaTest(false));
  }, []);

  async function wyslijTest() {
    setWysylanie(true); setWynikPoczty(null);
    try {
      const r = await api.post<{ message_id: string; to_domain: string }>("/api/admin/mail/test", { to: adres.trim() });
      setWynikPoczty(`Zakolejkowano wysyłkę do @${r.to_domain}. Identyfikator: ${r.message_id}. Wynik w logach Fly (wpis „Wysłano do”).`);
    } catch (e) {
      setWynikPoczty(`Nie udało się: ${(e as Error).message}`);
    } finally { setWysylanie(false); }
  }

  async function verify() {
    try {
      const r = await api.get<{ chain_valid: boolean }>("/api/admin/audit/verify");
      setChain(r.chain_valid);
    } catch (e) {
      setError(`Weryfikacja łańcucha nie powiodła się. ${(e as Error).message}`);
    }
  }

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!users) return <div className="page"><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Administracja" right={<LogoutButton />} />
      <p className="alert alert--info">
        Rola techniczna: bez dostępu do danych zdrowotnych klientów. Każde
        użycie panelu jest audytowane.
      </p>
      <div className="card">
        <h2>Konta ({users.length})</h2>
        <div className="table-wrap">
          <table className="simple table--cards">
            <thead><tr><th>Nazwa</th><th>E-mail</th><th>Role</th><th>Status</th><th>Ostatnie logowanie</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td data-label="Nazwa">{u.display_name}</td>
                  <td data-label="E-mail">{u.email}</td>
                  <td data-label="Role">{u.roles.join(", ")}</td>
                  <td data-label="Status">{u.status}</td>
                  <td data-label="Ostatnie logowanie">{u.last_login_at ? plDateTime(u.last_login_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {pocztaTest && (
        <div className="card">
          <h2>Poczta (Brevo SMTP) — test wysyłki</h2>
          <p className="dim">Wysyła „Test wysyłki Dzik OS” na podany adres przez skonfigurowany kanał SMTP. Zdarzenie trafia do audytu (bez adresu, tylko domena).</p>
          <label htmlFor="mail-test-to">Adres odbiorcy</label>
          <input id="mail-test-to" type="email" inputMode="email" value={adres} onChange={(e) => setAdres(e.target.value)} placeholder="adres@example.com" />
          <button type="button" className="btn btn--small" style={{ marginTop: 8 }} disabled={wysylanie || !adres.includes("@")} onClick={() => void wyslijTest()}>
            {wysylanie ? "Wysyłam…" : "Wyślij testowy e-mail"}
          </button>
          {wynikPoczty && <p role="status" className={`alert ${wynikPoczty.startsWith("Nie udało") ? "alert--error" : "alert--info"}`} style={{ marginTop: 8 }}>{wynikPoczty}</p>}
        </div>
      )}
      <div className="card">
        <div className="row row--between">
          <h2>Łańcuch audytu Human OS</h2>
          <button className="btn btn--ghost btn--small" onClick={verify}>Zweryfikuj integralność</button>
        </div>
        {chain !== null && (
          <p role="status" className={`alert ${chain ? "alert--info" : "alert--error"}`}>
            {chain ? "✅ Łańcuch zdarzeń spójny (hash chain zweryfikowany)."
              : "❌ Naruszenie integralności łańcucha!"}
          </p>
        )}
        {receipts.map((r) => (
          <div className="exercise" key={r.id}>
            <div>
              <b>{r.summary || r.action}</b>
              <div className="meta">{r.action} · {plDateTime(r.created_at)} · {r.event_hash.slice(0, 12)}…</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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

  useEffect(() => {
    api.get<{ users: UserRow[] }>("/api/admin/users")
      .then((d) => setUsers(d.users)).catch((e) => setError(e.message));
    api.get<{ receipts: ReceiptRow[] }>("/api/admin/receipts?limit=50")
      .then((d) => setReceipts(d.receipts)).catch(() => undefined);
  }, []);

  async function verify() {
    const r = await api.get<{ chain_valid: boolean }>("/api/admin/audit/verify");
    setChain(r.chain_valid);
  }

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
  if (!users) return <div className="page"><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Administracja" right={<LogoutButton />} />
      <p className="alert alert--info">
        Rola techniczna: bez dostępu do danych zdrowotnych klientów. Każde
        użycie panelu jest audytowane.
      </p>
      <div className="card">
        <h3>Konta ({users.length})</h3>
        <table className="simple">
          <thead><tr><th>Nazwa</th><th>E-mail</th><th>Role</th><th>Status</th><th>Ostatnie logowanie</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.display_name}</td>
                <td>{u.email}</td>
                <td>{u.roles.join(", ")}</td>
                <td>{u.status}</td>
                <td>{u.last_login_at ? plDateTime(u.last_login_at) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <div className="row row--between">
          <h3>Łańcuch audytu Human OS</h3>
          <button className="btn btn--ghost btn--small" onClick={verify}>Zweryfikuj integralność</button>
        </div>
        {chain !== null && (
          <p className={`alert ${chain ? "alert--info" : "alert--error"}`}>
            {chain ? "✅ Łańcuch zdarzeń spójny (hash chain zweryfikowany)."
              : "❌ Naruszenie integralności łańcucha!"}
          </p>
        )}
        {receipts.map((r) => (
          <div className="exercise" key={r.id}>
            <div>
              <b>{r.summary}</b>
              <div className="meta">{r.action} · {plDateTime(r.created_at)} · {r.event_hash.slice(0, 12)}…</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

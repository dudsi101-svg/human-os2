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

import { FormEvent, useEffect, useState } from "react";
import { api, clearSession, getUser } from "../../api";
import { plDate } from "../../dates";
import {
  ErrorBox, MfaCard, PushNotificationsCard, SecurityEventsCard, SessionsCard,
  Spinner, TopBar,
} from "../../components";
import { ConsentRow, GoalRow, ProfileFieldRow } from "../../types";

const FIELD_LABELS: Record<string, string> = {
  cel_glowny: "Cel główny",
  doswiadczenie: "Doświadczenie treningowe",
  sprzet: "Dostępny sprzęt",
  dni_treningowe: "Preferowane dni treningowe",
  ograniczenia_czasowe: "Ograniczenia czasowe",
  preferencje_zywieniowe: "Preferencje żywieniowe",
  alergie: "Alergie i nietolerancje",
  urazy: "Urazy i ograniczenia",
};

const SENSITIVE_KEYS = new Set(["preferencje_zywieniowe", "alergie", "urazy"]);

export default function Profile() {
  const user = getUser()!;
  const [fields, setFields] = useState<ProfileFieldRow[] | null>(null);
  const [goals, setGoals] = useState<GoalRow[]>([]);
  const [consents, setConsents] = useState<ConsentRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [deletePassword, setDeletePassword] = useState("");
  const [deletePhrase, setDeletePhrase] = useState("");
  const [showDelete, setShowDelete] = useState(false);

  const load = () => {
    api.get<{ fields: ProfileFieldRow[] }>(`/api/clients/${user.id}/profile`)
      .then((d) => setFields(d.fields)).catch((e) => setError(e.message));
    api.get<{ goals: GoalRow[] }>(`/api/clients/${user.id}/goals`)
      .then((d) => setGoals(d.goals)).catch(() => undefined);
    api.get<{ consents: ConsentRow[] }>(`/api/me/consents`)
      .then((d) => setConsents(d.consents)).catch(() => undefined);
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setOk(null);
    const payload = Object.entries(edits).map(([field_key, value]) => ({
      field_key, value, sensitive: SENSITIVE_KEYS.has(field_key),
    }));
    if (payload.length === 0) return;
    try {
      await api.put(`/api/clients/${user.id}/profile`, payload);
      setEdits({});
      setOk("Zapisano. Poprzednie wartości pozostają w historii.");
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function revoke(consentId: string) {
    if (!confirm("Cofnąć zgodę? Trener straci dostęp do Twoich danych do czasu ponownego jej udzielenia.")) return;
    await api.post(`/api/me/consents/${consentId}/revoke`);
    load();
  }

  async function regrant(c: ConsentRow) {
    await api.post(`/api/me/consents`, {
      grantee_id: c.grantee_id, purpose: c.purpose, domain: c.domain,
      actions: c.actions, allow_sensitive: c.allow_sensitive,
    });
    load();
  }

  async function exportData() {
    const data = await api.get<unknown>("/api/me/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dzik-os-export.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function exportDataExcel() {
    const blob = await api.get<Blob>("/api/me/export.xlsx");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dzik-os-export.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function requestDeletion(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/me/deletion-request", {
        password: deletePassword, confirm: deletePhrase,
      });
      clearSession();
      alert("Konto zostało zanonimizowane, a dane usunięte.");
      location.assign("/login");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!fields) return <div className="page"><Spinner /></div>;
  const byKey = Object.fromEntries(fields.map((f) => [f.field_key, f]));
  const allKeys = Array.from(new Set([...Object.keys(FIELD_LABELS), ...Object.keys(byKey)]));

  return (
    <div className="page">
      <TopBar title="Profil" />
      <PushNotificationsCard />
      <ErrorBox error={error} />
      {ok && <div className="alert alert--info">{ok}</div>}

      <form className="card" onSubmit={saveProfile}>
        <h3>{user.display_name}</h3>
        <small>{user.email}</small>
        {allKeys.map((key) => {
          const f = byKey[key];
          return (
            <div key={key}>
              <label>
                {FIELD_LABELS[key] ?? key}
                {f && (
                  <span className="dim">
                    {" "}· v{f.version} · {f.source === "CLIENT_DECLARED" ? "Ty" : "trener"} · {plDate(f.created_at)}
                  </span>
                )}
              </label>
              <input value={edits[key] ?? f?.value ?? ""}
                onChange={(e) => setEdits({ ...edits, [key]: e.target.value })} />
            </div>
          );
        })}
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={Object.keys(edits).length === 0}>Zapisz zmiany</button>
        </div>
      </form>

      <div className="card">
        <h3>Cele</h3>
        {goals.length === 0 && <small>Brak zdefiniowanych celów.</small>}
        {goals.map((g) => (
          <div className="exercise" key={g.id}>
            <div>
              <b>{g.title}</b>
              {g.target_date && <div className="meta">termin: {plDate(g.target_date)}</div>}
            </div>
            <span className={`badge ${g.status === "DONE" ? "badge--ok" : ""}`}>
              {g.kind === "MAIN" ? "główny" : "dodatkowy"}
            </span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Zgody na przetwarzanie danych</h3>
        <small>
          Twoje dane należą do Ciebie. Poniżej pełna historia zgód — cofnięcie
          działa natychmiast.
        </small>
        {consents.map((c) => (
          <div className="exercise" key={c.id}>
            <div>
              <b>{c.grantee_name ?? c.grantee_id}</b>
              <div className="meta">
                cel: {c.purpose} · zakres: {c.domain} · od {plDate(c.granted_at)}
                {c.revoked_at && ` · cofnięta ${plDate(c.revoked_at)}`}
              </div>
            </div>
            {c.revoked_at ? (
              <button className="btn btn--ghost btn--small" onClick={() => regrant(c)}>
                Udziel ponownie
              </button>
            ) : (
              <button className="btn btn--danger btn--small" onClick={() => revoke(c.id)}>
                Cofnij
              </button>
            )}
          </div>
        ))}
      </div>

      <MfaCard />
      <SessionsCard />
      <SecurityEventsCard />

      <div className="card">
        <h3>Twoje dane</h3>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn--ghost btn--small" onClick={exportData}>
            ⬇️ Eksportuj wszystkie dane (JSON)
          </button>
          <button className="btn btn--ghost btn--small" onClick={exportDataExcel}>
            ⬇️ Eksportuj do Excela
          </button>
          <button className="btn btn--danger btn--small" onClick={() => setShowDelete(!showDelete)}>
            Usuń konto i dane
          </button>
        </div>
        {showDelete && (
          <form onSubmit={requestDeletion} style={{ marginTop: 10 }}>
            <p className="alert alert--error">
              Operacja nieodwracalna: konto zostanie zanonimizowane, zdjęcia i
              pliki usunięte. Wpisz hasło oraz frazę <b>USUŃ MOJE DANE</b>.
            </p>
            <label>Hasło</label>
            <input type="password" value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)} required />
            <label>Fraza potwierdzająca</label>
            <input value={deletePhrase} onChange={(e) => setDeletePhrase(e.target.value)}
              placeholder="USUŃ MOJE DANE" required />
            <div style={{ marginTop: 10 }}>
              <button className="btn btn--danger">Usuń trwale</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

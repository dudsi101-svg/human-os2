import { FormEvent, useEffect, useState } from "react";
import { api, clearSession, getUser } from "../../api";
import { plDate } from "../../dates";
import {
  ErrorBox, MfaCard, PushNotificationsCard, SecurityEventsCard, SessionsCard,
  Spinner, TopBar,
} from "../../components";
import { ConsentDetails } from "../ConsentGate";
import {
  ConsentCategoryInfo, ConsentRow, ConsentsResponse, GoalRow, ProfileFieldRow,
} from "../../types";

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
  const [catalog, setCatalog] = useState<ConsentCategoryInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [deletePassword, setDeletePassword] = useState("");
  const [deletePhrase, setDeletePhrase] = useState("");
  const [showDelete, setShowDelete] = useState(false);

  const load = () => {
    setError(null);
    api.get<{ fields: ProfileFieldRow[] }>(`/api/clients/${user.id}/profile`)
      .then((d) => setFields(d.fields)).catch((e) => setError(e.message));
    // Cele i zgody to osobne sekcje tej strony — ich błąd jest widoczny
    // w tym samym ErrorBoxie (z ponowieniem), zamiast cicho znikać.
    api.get<{ goals: GoalRow[] }>(`/api/clients/${user.id}/goals`)
      .then((d) => setGoals(d.goals))
      .catch((e) => setError(`Nie udało się wczytać celów. ${e.message}`));
    api.get<ConsentsResponse>(`/api/me/consents`)
      .then((d) => { setConsents(d.consents); setCatalog(d.catalog); })
      .catch((e) => setError(`Nie udało się wczytać zgód. ${e.message}`));
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

  async function revoke(c: ConsentRow, label: string) {
    if (!confirm(
      `Cofnąć zgodę „${label}"? Działa natychmiast — odbiorca straci ` +
      "dostęp do danych tej kategorii do czasu ponownego jej udzielenia."
    )) return;
    try {
      await api.post(`/api/me/consents/${c.id}/revoke`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function grantCategory(categoryKey: string, granteeId: string | null) {
    try {
      await api.post(`/api/me/consents`, {
        category: categoryKey, grantee_id: granteeId,
      });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function exportData() {
    try {
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
    } catch (err) {
      setError(`Eksport nie powiódł się. ${(err as Error).message}`);
    }
  }

  async function exportDataExcel() {
    try {
      const blob = await api.get<Blob>("/api/me/export.xlsx");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "dzik-os-export.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(`Eksport nie powiódł się. ${(err as Error).message}`);
    }
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

  if (!fields) {
    return (
      <div className="page">
        {error ? <ErrorBox error={error} onRetry={load} /> : <Spinner />}
      </div>
    );
  }
  const byKey = Object.fromEntries(fields.map((f) => [f.field_key, f]));
  const allKeys = Array.from(new Set([...Object.keys(FIELD_LABELS), ...Object.keys(byKey)]));

  return (
    <div className="page">
      <TopBar title="Profil" />
      <PushNotificationsCard />
      <ErrorBox error={error} onRetry={load} />
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

      <ConsentsCard
        consents={consents}
        catalog={catalog}
        onRevoke={revoke}
        onGrant={grantCategory}
      />

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

/** Prywatność i zgody: stan per KATEGORIA (osobno wymagane i opcjonalne,
 *  bez żadnego zbiorczego przycisku), pełny opis każdej kategorii oraz
 *  historia decyzji (udzielenie / potwierdzenie / cofnięcie / odmowa,
 *  z wersją dokumentu). */
function ConsentsCard({
  consents,
  catalog,
  onRevoke,
  onGrant,
}: {
  consents: ConsentRow[];
  catalog: ConsentCategoryInfo[];
  onRevoke: (c: ConsentRow, label: string) => void;
  onGrant: (categoryKey: string, granteeId: string | null) => void;
}) {
  // Domyślny odbiorca zgód trenerskich: trener z ostatniego wiersza
  // kategorii trenerskiej (onboarding zawsze go zostawia w historii).
  const coachRow = [...consents].reverse().find(
    (c) => c.grantee_id !== "SYSTEM"
  );
  const coachId = coachRow?.grantee_id ?? null;
  const coachName = coachRow?.grantee_name ?? coachId;

  const rowsFor = (key: string) => consents.filter((c) => c.category === key);
  const activeFor = (key: string) =>
    rowsFor(key).find((c) => !c.revoked_at && !c.denied_at) ?? null;
  const legacyRows = consents.filter((c) => !c.category);

  const section = (cats: ConsentCategoryInfo[]) =>
    cats.map((cat) => {
      const active = activeFor(cat.key);
      const history = rowsFor(cat.key);
      const lastDenied = history.filter((c) => c.denied_at).pop();
      const status = active
        ? active.confirmed_at
          ? "aktywna"
          : "oczekuje potwierdzenia"
        : lastDenied
          ? "odmówiono"
          : history.length > 0
            ? "cofnięta"
            : "nieudzielona";
      const grantee =
        cat.grantee_kind === "SYSTEM" ? "Aplikacja Dzik OS" : coachName;
      return (
        <div className="exercise" key={cat.key}>
          <div style={{ width: "100%" }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <b>{cat.label}</b>
              <span className={`badge ${status === "aktywna" ? "badge--ok" : ""}`}>
                {status}
              </span>
            </div>
            <div className="meta">
              odbiorca: {grantee ?? "—"}
              {active && ` · od ${plDate(active.granted_at)}`}
              {active && !active.document_version_current &&
                " · nowsza wersja dokumentu dostępna"}
            </div>
            <ConsentDetails cat={cat} />
            {history.length > 0 && (
              <details style={{ marginTop: 4 }}>
                <summary style={{ cursor: "pointer", fontSize: "0.8rem" }}>
                  Historia decyzji ({history.length})
                </summary>
                <ul style={{ fontSize: "0.78rem", color: "var(--text-dim)", paddingLeft: 16 }}>
                  {history.map((h) => (
                    <li key={h.id}>
                      {h.denied_at
                        ? `odmowa ${plDate(h.denied_at)}`
                        : `udzielona ${plDate(h.granted_at)}` +
                          (h.confirmed_at ? `, potwierdzona ${plDate(h.confirmed_at)}` : "") +
                          (h.revoked_at ? `, cofnięta ${plDate(h.revoked_at)}` : "")}
                      {" "}· wersja {h.consent_text_version}
                      {h.source === "ONBOARDING_DECLARATION" && " · deklaracja z onboardingu"}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <div className="row" style={{ marginTop: 8 }}>
              {active ? (
                <button
                  className="btn btn--danger btn--small"
                  onClick={() => onRevoke(active, cat.label)}
                >
                  Cofnij
                </button>
              ) : (
                (cat.grantee_kind === "SYSTEM" || coachId) && (
                  <button
                    className="btn btn--ghost btn--small"
                    onClick={() =>
                      onGrant(cat.key, cat.grantee_kind === "SYSTEM" ? null : coachId)
                    }
                  >
                    {history.length > 0 ? "Udziel ponownie" : "Udziel zgody"}
                  </button>
                )
              )}
            </div>
          </div>
        </div>
      );
    });

  return (
    <div className="card">
      <h3>Prywatność i zgody</h3>
      <small>
        Twoje dane należą do Ciebie. Każda kategoria to osobna decyzja —
        cofnięcie działa natychmiast i dotyczy tylko tej kategorii.
      </small>
      <h4 style={{ marginBottom: 4 }}>Wymagane do współpracy (umowa)</h4>
      {section(catalog.filter((c) => c.required))}
      <h4 style={{ marginBottom: 4 }}>Zgody opcjonalne</h4>
      {section(catalog.filter((c) => !c.required))}
      {legacyRows.length > 0 && (
        <>
          <h4 style={{ marginBottom: 4 }}>Zgody historyczne (sprzed podziału na kategorie)</h4>
          {legacyRows.map((c) => (
            <div className="exercise" key={c.id}>
              <div>
                <b>{c.grantee_name ?? c.grantee_id}</b>
                <div className="meta">
                  cel: {c.purpose} · zakres: pełny dostęp trenerski (zgoda
                  parasolowa) · od {plDate(c.granted_at)}
                  {c.revoked_at && ` · cofnięta ${plDate(c.revoked_at)}`}
                </div>
              </div>
              {!c.revoked_at && !c.denied_at && (
                <button
                  className="btn btn--danger btn--small"
                  onClick={() => onRevoke(c, "zgoda parasolowa")}
                >
                  Cofnij
                </button>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

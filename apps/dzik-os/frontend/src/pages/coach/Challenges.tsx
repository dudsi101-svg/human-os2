import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { localToday, plDate } from "../../dates";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import {
  ChallengeDetail, ChallengeReportRow, ChallengeUnit, CoachChallengeRow,
  CoachClientRow,
} from "../../types";

/** Panel trenera: tworzenie i moderacja WŁASNYCH wyzwań grupowych.
 * Trener widzi listę uczestników i postęp grupy; wyniki jednostkowe
 * wyłącznie osób, które same je udostępniły. */

const STATUS_PL: Record<string, string> = {
  DRAFT: "szkic", ACTIVE: "trwa", FINISHED: "zakończone", CANCELLED: "odwołane",
};
const PART_STATUS_PL: Record<string, string> = {
  INVITED: "zaproszenie wysłane", ACTIVE: "bierze udział",
  LEFT: "opuścił(a)", REMOVED: "usunięty(a) przez organizatora",
};

function NewChallengeForm({ units, onDone, onError }: {
  units: ChallengeUnit[]; onDone: () => void; onError: (m: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [unit, setUnit] = useState("treningi");
  const [goal, setGoal] = useState("12");
  const [starts, setStarts] = useState(localToday());
  const [ends, setEnds] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/api/coach/challenges", {
        title: title.trim(), description: description.trim() || undefined,
        unit, goal_value: Number(goal) || undefined,
        starts_on: starts, ends_on: ends,
      });
      setTitle("");
      setDescription("");
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="nc-title">Nazwa wyzwania</label>
      <input id="nc-title" required minLength={3} maxLength={300} value={title}
        placeholder="np. 12 treningów w 4 tygodnie"
        onChange={(e) => setTitle(e.target.value)} />
      <label htmlFor="nc-desc">Zasady (opcjonalnie)</label>
      <textarea id="nc-desc" rows={2} maxLength={4000} value={description}
        onChange={(e) => setDescription(e.target.value)} />
      <div className="field-row">
        <div>
          <label htmlFor="nc-unit">Co liczymy (tylko neutralne jednostki)</label>
          <select id="nc-unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
            {units.map((u) => <option key={u.key} value={u.key}>{u.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="nc-goal">Cel na osobę</label>
          <input id="nc-goal" type="number" min={1} required value={goal}
            onChange={(e) => setGoal(e.target.value)} />
        </div>
      </div>
      <div className="field-row">
        <div>
          <label htmlFor="nc-starts">Start</label>
          <input id="nc-starts" type="date" required value={starts}
            onChange={(e) => setStarts(e.target.value)} />
        </div>
        <div>
          <label htmlFor="nc-ends">Koniec</label>
          <input id="nc-ends" type="date" required value={ends}
            onChange={(e) => setEnds(e.target.value)} />
        </div>
      </div>
      <p className="dim" style={{ fontSize: "0.78rem" }}>
        Masa ciała i inne dane zdrowotne nie są dostępne jako jednostki —
        wyzwania działają wyłącznie na neutralnych licznikach. Udział jest
        dobrowolny (zaproszenie → decyzja klienta), a ranking domyślnie
        wyłączony u każdego uczestnika.
      </p>
      <button className="btn btn--small" disabled={busy}>Utwórz szkic wyzwania</button>
    </form>
  );
}

function CoachDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [det, setDet] = useState<ChallengeDetail | null>(null);
  const [reports, setReports] = useState<ChallengeReportRow[] | null>(null);
  const [clients, setClients] = useState<CoachClientRow[]>([]);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<ChallengeDetail>(`/api/challenges/${id}`).then(setDet)
      .catch((e) => setError(e.message));
    api.get<{ reports: ChallengeReportRow[] }>(`/api/challenges/${id}/reports`)
      .then((d) => setReports(d.reports))
      .catch(() => setReports([]));
    api.get<{ clients: CoachClientRow[] }>("/api/coach/clients")
      .then((d) => setClients(d.clients.filter(
        (c) => c.relationship_status === "ACTIVE" && !c.account_pending)))
      .catch(() => setClients([]));
  }, [id]);
  useEffect(load, [load]);

  async function act(path: string, body?: unknown, confirmMsg?: string) {
    if (confirmMsg && !confirm(confirmMsg)) return;
    setError(null);
    try {
      await api.post(`/api/challenges/${id}/${path}`, body);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function invite() {
    if (picked.size === 0) return;
    await act("invite", { client_ids: [...picked] });
    setPicked(new Set());
  }

  if (error && !det) return <ErrorBox error={error} onRetry={load} />;
  if (!det) return <Spinner />;

  const invitedIds = new Set((det.participants ?? []).map((p) => p.user_id));
  const invitable = clients.filter((c) => !invitedIds.has(c.client_id));

  return (
    <div>
      <button className="btn btn--ghost btn--small" onClick={onBack}>
        ← Wszystkie wyzwania
      </button>
      <div className="card" style={{ marginTop: 8 }}>
        <h2>{det.title}</h2>
        <div className="meta">
          {plDate(det.starts_on)} – {plDate(det.ends_on)} · {det.unit_label}
          {det.goal_value != null && ` · cel: ${det.goal_value}`} ·{" "}
          {STATUS_PL[det.status] ?? det.status}
        </div>
        {det.description && <p>{det.description}</p>}
        {det.group && (
          <div className="meta">
            Grupa: {det.group.active_participants} os. · razem{" "}
            {det.group.total_value} {det.unit_label}
            {det.group.avg_progress_pct != null &&
              ` · średnio ${det.group.avg_progress_pct}% celu`}
            {det.group.aggregates_adjusted &&
              " · sumy skorygowane po wycofaniu udziału"}
          </div>
        )}
        <div className="row" style={{ marginTop: 8, gap: 8, flexWrap: "wrap" }}>
          {det.status === "DRAFT" && (
            <button className="btn btn--small" onClick={() => act("activate")}>
              Aktywuj wyzwanie
            </button>
          )}
          {det.status === "ACTIVE" && (
            <button className="btn btn--small"
              onClick={() => act("finish", undefined, "Zakończyć wyzwanie? Wpisy zostaną zamrożone.")}>
              Zakończ wyzwanie
            </button>
          )}
          {(det.status === "DRAFT" || det.status === "ACTIVE") && (
            <button className="btn btn--danger btn--small"
              onClick={() => act("cancel", undefined, "Odwołać wyzwanie? Uczestnicy dostaną powiadomienie.")}>
              Odwołaj
            </button>
          )}
        </div>
      </div>

      <ErrorBox error={error} />

      {(det.status === "DRAFT" || det.status === "ACTIVE") && (
        <div className="card">
          <h2>Zaproś podopiecznych</h2>
          {invitable.length === 0 && (
            <p className="dim">Wszyscy aktywni podopieczni są już zaproszeni.</p>
          )}
          {invitable.map((c) => (
            <label className="row" style={{ gap: 8 }} key={c.client_id}>
              <input type="checkbox" checked={picked.has(c.client_id)}
                onChange={(e) => {
                  const next = new Set(picked);
                  if (e.target.checked) next.add(c.client_id);
                  else next.delete(c.client_id);
                  setPicked(next);
                }} />
              <span>{c.display_name}</span>
            </label>
          ))}
          {invitable.length > 0 && (
            <button className="btn btn--small" style={{ marginTop: 8 }}
              disabled={picked.size === 0} onClick={invite}>
              Wyślij zaproszenia ({picked.size})
            </button>
          )}
          <p className="dim" style={{ fontSize: "0.78rem" }}>
            Udział jest dobrowolny — każdy zaproszony sam decyduje, czy
            dołączyć, jak się podpisać i czy pokazywać wynik.
          </p>
        </div>
      )}

      {det.participants && det.participants.length > 0 && (
        <div className="card">
          <h2>Uczestnicy</h2>
          {det.participants.map((p) => (
            <div className="row row--between" key={p.participant_id}>
              <span>
                {p.alias ?? "—"}
                <span className="dim"> · {PART_STATUS_PL[p.status] ?? p.status}</span>
                {p.status === "ACTIVE" && !p.share_result && (
                  <span className="dim"> · wynik ukryty (decyzja uczestnika)</span>
                )}
              </span>
              {p.status === "ACTIVE" && (
                <span className="row" style={{ gap: 6 }}>
                  <button className="btn btn--ghost btn--small"
                    aria-label={`Zresetuj pseudonim uczestnika ${p.alias ?? ""}`}
                    onClick={() => act(`participants/${p.participant_id}/reset-alias`,
                      undefined, "Zastąpić pseudonim neutralnym „Uczestnik”?")}>
                    Resetuj pseudonim
                  </button>
                  <button className="btn btn--danger btn--small"
                    aria-label={`Usuń uczestnika ${p.alias ?? ""} z wyzwania`}
                    onClick={() => act(`participants/${p.participant_id}/remove`,
                      undefined, "Usunąć uczestnika z wyzwania?")}>
                    Usuń
                  </button>
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {det.shared && det.shared.length > 0 && (
        <div className="card">
          <h2>Wyniki udostępnione przez uczestników</h2>
          {det.shared.map((s) => (
            <div className="row row--between" key={s.user_id}>
              <span>{s.alias}{s.has_manual && <span className="dim"> · wpisy ręczne</span>}</span>
              <b>{s.value} {det.unit_label}</b>
            </div>
          ))}
        </div>
      )}

      {reports && reports.length > 0 && (
        <div className="card">
          <h2>Zgłoszenia</h2>
          {reports.map((r) => (
            <div key={r.id} style={{ marginBottom: 10 }}>
              <div className="meta">
                {plDate(r.created_at)} · {r.reporter_name ?? "?"} zgłasza:{" "}
                {r.reported_name ?? "?"} ·{" "}
                {r.status === "OPEN" ? "otwarte" : `rozstrzygnięte (${r.resolution})`}
              </div>
              <div>{r.reason}</div>
              {r.status === "OPEN" && (
                <div className="row" style={{ gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                  <button className="btn btn--danger btn--small"
                    onClick={() => act(`reports/${r.id}/resolve`, { resolution: "REMOVED" },
                      "Usunąć zgłoszonego uczestnika z wyzwania?")}>
                    Usuń uczestnika
                  </button>
                  <button className="btn btn--ghost btn--small"
                    onClick={() => act(`reports/${r.id}/resolve`, { resolution: "ALIAS_RESET" })}>
                    Resetuj pseudonim
                  </button>
                  <button className="btn btn--ghost btn--small"
                    onClick={() => act(`reports/${r.id}/resolve`, { resolution: "NOTES_CLEARED" })}>
                    Usuń notatki wpisów
                  </button>
                  <button className="btn btn--ghost btn--small"
                    onClick={() => act(`reports/${r.id}/resolve`, { resolution: "DISMISSED" })}>
                    Oddal
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CoachChallenges() {
  const [rows, setRows] = useState<CoachChallengeRow[] | null>(null);
  const [units, setUnits] = useState<ChallengeUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<{ challenges: CoachChallengeRow[] }>("/api/coach/challenges")
      .then((d) => setRows(d.challenges))
      .catch((e) => setError(e.message));
    api.get<{ units: ChallengeUnit[] }>("/api/challenge-units")
      .then((d) => setUnits(d.units))
      .catch(() => setUnits([]));
  }, []);
  useEffect(load, [load]);

  if (error && !rows) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!rows) return <div className="page"><Spinner /></div>;

  if (selected) {
    return (
      <div className="page">
        <TopBar title="Wyzwanie" right={<LogoutButton />} />
        <CoachDetail id={selected} onBack={() => { setSelected(null); load(); }} />
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="Wyzwania" right={<LogoutButton />} />
      <p className="dim" style={{ marginTop: -8 }}>
        Prywatne wyzwania grupowe dla Twoich podopiecznych — tylko
        zaproszeni, neutralne jednostki, ranking wyłącznie za świadomą
        zgodą każdego uczestnika. Moderujesz wyłącznie własne wyzwania.
      </p>
      <div className="card">
        <h2>Nowe wyzwanie</h2>
        <NewChallengeForm units={units} onDone={load} onError={setError} />
      </div>
      <ErrorBox error={error} />
      <h2>Twoje wyzwania</h2>
      {rows.length === 0 && <p className="dim">Nie masz jeszcze żadnych wyzwań.</p>}
      {rows.map((ch) => (
        <button className="card" key={ch.id}
          style={{ width: "100%", textAlign: "left", cursor: "pointer", display: "block" }}
          onClick={() => setSelected(ch.id)}>
          <b>{ch.title}</b>
          <div className="meta">
            {plDate(ch.starts_on)} – {plDate(ch.ends_on)} · {ch.unit_label} ·{" "}
            {STATUS_PL[ch.status] ?? ch.status} · {ch.active_participants} uczestników
            {ch.pending_invitations > 0 && ` · ${ch.pending_invitations} zaproszeń czeka`}
            {ch.open_reports > 0 && ` · ${ch.open_reports} zgłoszeń do moderacji`}
          </div>
        </button>
      ))}
    </div>
  );
}

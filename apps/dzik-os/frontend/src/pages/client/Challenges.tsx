import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { localToday, plDate } from "../../dates";
import { ErrorBox, Icon, Spinner, TopBar } from "../../components";
import {
  ChallengeDetail, ChallengeEntryRow, ChallengeInvitation, ChallengeListItem,
  ChallengeUnit,
} from "../../types";

/** Wyzwania klienta — moduł PRYWATNY (tylko zaproszeni; publicznych nie ma).
 * Konstytucja Human OS: ranking jest opt-in i domyślnie WYŁĄCZONY; domyślny
 * widok to własny postęp + anonimowy postęp grupy; wynik jednostkowy widzą
 * inni wyłącznie po świadomej decyzji uczestnika. */

interface ListData {
  invitations: ChallengeInvitation[];
  challenges: ChallengeListItem[];
}

function ProgressLine({ value, goal, pct, unitLabel }: {
  value: number; goal: number | null; pct: number | null; unitLabel: string;
}) {
  return (
    <div>
      <div className="meta">
        {value} {unitLabel}
        {goal != null && ` z ${goal}`}
        {pct != null && ` · ${pct}%`}
      </div>
      {pct != null && (
        /* Pasek jest wyłącznie wizualizacją — liczby są w tekście obok. */
        <div aria-hidden style={{ background: "var(--bg-raised)", borderRadius: 999, height: 8, overflow: "hidden", marginTop: 4 }}>
          <div style={{ width: `${Math.min(100, pct)}%`, background: "var(--accent)", height: "100%" }} />
        </div>
      )}
    </div>
  );
}

function JoinForm({ inv, onDone, onError }: {
  inv: ChallengeInvitation; onDone: () => void; onError: (m: string) => void;
}) {
  const [alias, setAlias] = useState("");
  const [share, setShare] = useState(false);
  const [ranking, setRanking] = useState(false);
  const [autoCount, setAutoCount] = useState(false);
  const [busy, setBusy] = useState(false);

  async function join(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post(`/api/challenges/${inv.id}/join`, {
        alias: alias.trim() || undefined,
        share_result: share,
        ranking_opt_in: ranking,
        auto_count_workouts: autoCount,
      });
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function decline() {
    setBusy(true);
    try {
      await api.post(`/api/challenges/${inv.id}/decline`);
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={join}>
      <label htmlFor={`al-${inv.id}`}>Twoja widoczna nazwa (pseudonim)</label>
      <input id={`al-${inv.id}`} maxLength={80} value={alias}
        placeholder="np. Dzik z Lasu (puste = Twoje imię)"
        onChange={(e) => setAlias(e.target.value)} />
      <label className="row" style={{ gap: 8, marginTop: 8 }}>
        <input type="checkbox" checked={share}
          onChange={(e) => setShare(e.target.checked)} />
        <span>Pokazuj mój wynik innym uczestnikom (domyślnie ukryty)</span>
      </label>
      <label className="row" style={{ gap: 8 }}>
        <input type="checkbox" checked={ranking} disabled={!share}
          onChange={(e) => setRanking(e.target.checked)} />
        <span>Bierz mnie pod uwagę w rankingu (domyślnie wyłączony;
          wymaga pokazywania wyniku)</span>
      </label>
      {inv.unit === "treningi" && (
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={autoCount}
            onChange={(e) => setAutoCount(e.target.checked)} />
          <span>Zaliczaj automatycznie moje odhaczone treningi
            (bez tego zgłaszasz treningi ręcznie)</span>
        </label>
      )}
      <div className="row" style={{ marginTop: 10, gap: 8 }}>
        <button className="btn btn--small" disabled={busy}>Dołączam</button>
        <button type="button" className="btn btn--ghost btn--small" disabled={busy}
          onClick={decline}>
          Odrzucam
        </button>
      </div>
    </form>
  );
}

function EntryForm({ det, onDone, onError }: {
  det: ChallengeDetail; onDone: () => void; onError: (m: string) => void;
}) {
  const [value, setValue] = useState("");
  const [date, setDate] = useState(localToday());
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const fixed = det.unit !== "minuty";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post(`/api/challenges/${det.id}/entries`, {
        value: fixed ? undefined : Number(value),
        entry_date: date,
        note: note.trim() || undefined,
        client_entry_id: crypto.randomUUID(),
      });
      setValue("");
      setNote("");
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (det.me?.auto_count_workouts) {
    return (
      <p className="dim">
        Masz włączone automatyczne zaliczanie odhaczonych treningów — nic
        nie musisz zgłaszać ręcznie.
      </p>
    );
  }
  return (
    <form onSubmit={submit}>
      <div className="field-row">
        {!fixed && (
          <div>
            <label htmlFor="ce-value">Ile ({det.unit_label})</label>
            <input id="ce-value" type="number" min={1} max={600} required
              value={value} onChange={(e) => setValue(e.target.value)} />
          </div>
        )}
        <div>
          <label htmlFor="ce-date">Dzień</label>
          <input id="ce-date" type="date" required value={date}
            onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>
      <label htmlFor="ce-note">Notatka (opcjonalna, widoczna gdy udostępniasz wynik)</label>
      <input id="ce-note" maxLength={200} value={note}
        onChange={(e) => setNote(e.target.value)} />
      <div style={{ marginTop: 8 }}>
        <button className="btn btn--small" disabled={busy}>
          {fixed ? "Zgłoś 1 do wyzwania" : "Zapisz wpis"}
        </button>
      </div>
      <p className="dim" style={{ fontSize: "0.78rem" }}>
        Wpis ręczny jest oznaczany jako ręczny. Dzień liczy się według
        strefy wyzwania ({det.timezone}). Limit: {det.max_entries_per_day}{" "}
        wpisów dziennie.
      </p>
    </form>
  );
}

function Detail({ id, onBack }: { id: string; onBack: () => void }) {
  const [det, setDet] = useState<ChallengeDetail | null>(null);
  const [entries, setEntries] = useState<ChallengeEntryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [correcting, setCorrecting] = useState<string | null>(null);
  const [corrValue, setCorrValue] = useState("");

  const load = useCallback(() => {
    setError(null);
    api.get<ChallengeDetail>(`/api/challenges/${id}`).then(setDet)
      .catch((e) => setError(e.message));
    api.get<{ entries: ChallengeEntryRow[] }>(`/api/challenges/${id}/entries`)
      .then((d) => setEntries(d.entries))
      .catch(() => setEntries([]));
  }, [id]);
  useEffect(load, [load]);

  async function patchMe(body: Record<string, unknown>) {
    setError(null);
    try {
      await api.patch(`/api/challenges/${id}/me`, body);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function act(path: string, confirmMsg?: string) {
    if (confirmMsg && !confirm(confirmMsg)) return;
    setError(null);
    try {
      await api.post(`/api/challenges/${id}/${path}`);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function correct(entryId: string) {
    setError(null);
    try {
      await api.post(`/api/challenges/${id}/entries/${entryId}/correct`, {
        value: Number(corrValue),
      });
      setCorrecting(null);
      setCorrValue("");
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function blockUser(userId: string, alias: string) {
    if (!confirm(`Zablokować uczestnika „${alias}”? Przestaniecie wzajemnie widzieć swoje wyniki.`)) return;
    try {
      await api.post(`/api/challenges/${id}/block`, { user_id: userId });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function reportUser(userId: string, alias: string) {
    const reason = prompt(`Opisz problem z uczestnikiem „${alias}” (trafi do organizatora):`);
    if (!reason || reason.trim().length < 3) return;
    try {
      await api.post(`/api/challenges/${id}/report`, { user_id: userId, reason: reason.trim() });
      alert("Zgłoszenie wysłane do organizatora.");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error && !det) return <ErrorBox error={error} onRetry={load} />;
  if (!det) return <Spinner />;
  const me = det.me;
  const active = det.status === "ACTIVE" && me?.status === "ACTIVE";

  return (
    <div>
      <button className="btn btn--ghost btn--small" onClick={onBack}>
        ← Wszystkie wyzwania
      </button>
      <div className="card" style={{ marginTop: 8 }}>
        <h2>{det.title}</h2>
        <div className="meta">
          {plDate(det.starts_on)} – {plDate(det.ends_on)} · {det.unit_label}
          {" · "}
          {det.status === "ACTIVE" ? "trwa" :
            det.status === "FINISHED" ? "zakończone" :
            det.status === "DRAFT" ? "szkic" : "odwołane"}
        </div>
        {det.description && <p>{det.description}</p>}
        {me?.progress && (
          <>
            <h3>Twój postęp</h3>
            <ProgressLine value={me.progress.value} goal={me.progress.goal_value}
              pct={me.progress.progress_pct} unitLabel={det.unit_label} />
          </>
        )}
        {det.group && (
          <>
            <h3>Grupa (bez nazwisk)</h3>
            <div className="meta">
              {det.group.active_participants}{" "}
              {det.group.active_participants === 1 ? "osoba" : "osób"} ·
              razem {det.group.total_value} {det.unit_label}
              {det.group.avg_progress_pct != null &&
                ` · średnio ${det.group.avg_progress_pct}% celu`}
            </div>
            {det.group.aggregates_adjusted && (
              <p className="dim" style={{ fontSize: "0.78rem" }}>
                Ktoś trwale wycofał swój udział — sumy grupy zostały
                skorygowane (historia zmian w audycie).
              </p>
            )}
          </>
        )}
      </div>

      <ErrorBox error={error} />

      {active && (
        <div className="card">
          <h2>Dodaj wpis</h2>
          <EntryForm det={det} onDone={load} onError={setError} />
        </div>
      )}

      {det.ranking && det.ranking.length > 0 && (
        <div className="card">
          <h2>Ranking (tylko osoby, które go włączyły)</h2>
          {det.ranking.map((r) => (
            <div className="row row--between" key={r.user_id}>
              <span>{r.position}. {r.alias}{r.is_me ? " (Ty)" : ""}</span>
              <b>{r.value} {det.unit_label}</b>
            </div>
          ))}
        </div>
      )}

      {det.shared && det.shared.length > 0 && (
        <div className="card">
          <h2>Udostępnione wyniki</h2>
          {det.shared.map((s) => (
            <div className="row row--between" key={s.user_id}>
              <span>
                {s.alias}{s.is_me ? " (Ty)" : ""}
                {s.has_manual && <span className="dim"> · zawiera wpisy ręczne</span>}
              </span>
              <span className="row" style={{ gap: 6 }}>
                <b>{s.value} {det.unit_label}</b>
                {!s.is_me && (
                  <>
                    <button className="btn btn--ghost btn--small"
                      aria-label={`Zablokuj uczestnika ${s.alias}`}
                      onClick={() => blockUser(s.user_id, s.alias)}>
                      Zablokuj
                    </button>
                    <button className="btn btn--ghost btn--small"
                      aria-label={`Zgłoś uczestnika ${s.alias}`}
                      onClick={() => reportUser(s.user_id, s.alias)}>
                      Zgłoś
                    </button>
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
      )}

      {me?.status === "ACTIVE" && (
        <div className="card">
          <h2>Twoje ustawienia widoczności</h2>
          <p className="dim" style={{ fontSize: "0.82rem" }}>{det.explainer}</p>
          <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
            <button className="btn btn--ghost btn--small"
              aria-pressed={me.share_result}
              onClick={() => patchMe({ share_result: !me.share_result })}>
              {me.share_result ? "Wynik widoczny — ukryj" : "Wynik ukryty — pokaż innym"}
            </button>
            <button className="btn btn--ghost btn--small"
              aria-pressed={me.ranking_opt_in} disabled={!me.share_result && !me.ranking_opt_in}
              onClick={() => patchMe({ ranking_opt_in: !me.ranking_opt_in })}>
              {me.ranking_opt_in ? "Ranking włączony — wyłącz" : "Ranking wyłączony — włącz"}
            </button>
          </div>
          <div style={{ marginTop: 8 }}>
            <label htmlFor="ch-alias">Pseudonim w tym wyzwaniu</label>
            <div className="row" style={{ gap: 6 }}>
              <input id="ch-alias" maxLength={80} defaultValue={me.alias ?? ""}
                onBlur={(e) => {
                  const v = e.target.value.trim();
                  if (v && v !== me.alias) patchMe({ alias: v });
                }} />
            </div>
          </div>
          <div className="row" style={{ marginTop: 12, gap: 8, flexWrap: "wrap" }}>
            <button className="btn btn--ghost btn--small"
              onClick={() => act("leave", "Opuścić wyzwanie? Znikniesz z widoków grupy.")}>
              Opuść wyzwanie
            </button>
            <button className="btn btn--danger btn--small"
              onClick={() => act("withdraw",
                "Trwale wycofać udział? Twoje wpisy zostaną USUNIĘTE, a sumy grupy oznaczone jako skorygowane. Tej operacji nie można cofnąć.")}>
              Wycofaj udział i usuń moje wyniki
            </button>
          </div>
        </div>
      )}

      {entries && entries.length > 0 && (
        <div className="card">
          <h2>Twoje wpisy (historia z korektami)</h2>
          {entries.map((e) => (
            <div className="row row--between" key={e.id}>
              <span>
                {plDate(e.entry_date)} · {e.value} {det.unit_label}
                {e.source === "MANUAL" && <span className="dim"> · ręczny</span>}
                {e.status === "CORRECTED" && (
                  <span className="dim"> · skorygowany</span>
                )}
                {e.note && <span className="dim"> · {e.note}</span>}
              </span>
              {e.status === "ACTIVE" && active && det.unit === "minuty" && (
                correcting === e.id ? (
                  <span className="row" style={{ gap: 6 }}>
                    <label className="sr-only" htmlFor={`corr-${e.id}`}>
                      Nowa wartość
                    </label>
                    <input id={`corr-${e.id}`} type="number" min={1} max={600}
                      style={{ width: 80 }} value={corrValue}
                      onChange={(ev) => setCorrValue(ev.target.value)} />
                    <button className="btn btn--small" onClick={() => correct(e.id)}>
                      Zapisz
                    </button>
                    <button className="btn btn--ghost btn--small"
                      onClick={() => setCorrecting(null)}>
                      Anuluj
                    </button>
                  </span>
                ) : (
                  <button className="btn btn--ghost btn--small"
                    onClick={() => { setCorrecting(e.id); setCorrValue(String(e.value)); }}>
                    Popraw
                  </button>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewIndividualForm({ units, onDone, onError }: {
  units: ChallengeUnit[]; onDone: () => void; onError: (m: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [unit, setUnit] = useState("treningi");
  const [goal, setGoal] = useState("10");
  const [starts, setStarts] = useState(localToday());
  const [ends, setEnds] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/api/me/challenges", {
        title: title.trim(), unit, goal_value: Number(goal) || undefined,
        starts_on: starts, ends_on: ends,
      });
      setTitle("");
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="ni-title">Nazwa wyzwania</label>
      <input id="ni-title" required minLength={3} maxLength={300} value={title}
        placeholder="np. 12 treningów w miesiąc"
        onChange={(e) => setTitle(e.target.value)} />
      <div className="field-row">
        <div>
          <label htmlFor="ni-unit">Co liczymy</label>
          <select id="ni-unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
            {units.map((u) => <option key={u.key} value={u.key}>{u.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="ni-goal">Cel</label>
          <input id="ni-goal" type="number" min={1} required value={goal}
            onChange={(e) => setGoal(e.target.value)} />
        </div>
      </div>
      <div className="field-row">
        <div>
          <label htmlFor="ni-starts">Start</label>
          <input id="ni-starts" type="date" required value={starts}
            onChange={(e) => setStarts(e.target.value)} />
        </div>
        <div>
          <label htmlFor="ni-ends">Koniec</label>
          <input id="ni-ends" type="date" required value={ends}
            onChange={(e) => setEnds(e.target.value)} />
        </div>
      </div>
      <div style={{ marginTop: 8 }}>
        <button className="btn btn--small" disabled={busy}>Zacznij wyzwanie</button>
      </div>
    </form>
  );
}

export default function Challenges() {
  const [data, setData] = useState<ListData | null>(null);
  const [units, setUnits] = useState<ChallengeUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(() => {
    setError(null);
    api.get<ListData>("/api/me/challenges").then(setData)
      .catch((e) => setError(e.message));
    api.get<{ units: ChallengeUnit[] }>("/api/challenge-units")
      .then((d) => setUnits(d.units))
      .catch(() => setUnits([]));
  }, []);
  useEffect(load, [load]);

  if (error && !data) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!data) return <div className="page"><Spinner /></div>;

  if (selected) {
    return (
      <div className="page">
        <TopBar title="Wyzwanie" />
        <Detail id={selected} onBack={() => { setSelected(null); load(); }} />
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="Wyzwania" />
      <p className="dim" style={{ marginTop: -8 }}>
        Wyzwania są prywatne — widzą je tylko zaproszeni. Rywalizujesz przede
        wszystkim z własnym celem; ranking i widoczność wyniku włączasz
        wyłącznie sam(a). Dane zdrowotne nigdy nie trafiają do wyzwań.
      </p>

      {data.invitations.map((inv) => (
        <div className="card card--accent" key={inv.id}>
          <h2><Icon name="trophy" /> Zaproszenie: {inv.title}</h2>
          <div className="meta">
            {plDate(inv.starts_on)} – {plDate(inv.ends_on)} · {inv.unit_label}
            {inv.goal_value != null && ` · cel: ${inv.goal_value}`}
            {inv.invited_by_name && ` · od: ${inv.invited_by_name}`}
          </div>
          {inv.description && <p>{inv.description}</p>}
          <p className="dim" style={{ fontSize: "0.82rem" }}>{inv.explainer}</p>
          <JoinForm inv={inv} onDone={load} onError={setError} />
        </div>
      ))}

      <ErrorBox error={error} />

      <h2>Twoje wyzwania</h2>
      {data.challenges.length === 0 && (
        <p className="dim">
          Nie bierzesz udziału w żadnym wyzwaniu. Możesz zacząć własne
          (sam(a) ze sobą) poniżej albo poczekać na zaproszenie od trenera.
        </p>
      )}
      {data.challenges.map((ch) => (
        <button className="card" key={ch.id}
          style={{ width: "100%", textAlign: "left", cursor: "pointer", display: "block" }}
          onClick={() => setSelected(ch.id)}>
          <div style={{ flex: 1 }}>
            <b>{ch.title}</b>
            <div className="meta">
              {plDate(ch.starts_on)} – {plDate(ch.ends_on)} ·{" "}
              {ch.status === "ACTIVE" ? "trwa" :
                ch.status === "FINISHED" ? "zakończone" : ch.status.toLowerCase()}
              {ch.kind === "INDIVIDUAL" && " · indywidualne"}
            </div>
            <ProgressLine value={ch.progress.value} goal={ch.progress.goal_value}
              pct={ch.progress.progress_pct} unitLabel={ch.unit_label} />
          </div>
        </button>
      ))}

      <div className="card">
        <h2>Własne wyzwanie (sam ze sobą)</h2>
        {showNew ? (
          <NewIndividualForm units={units} onError={setError}
            onDone={() => { setShowNew(false); load(); }} />
        ) : (
          <button className="btn btn--ghost btn--small" onClick={() => setShowNew(true)}
            aria-expanded={showNew}>
            Zacznij własne wyzwanie
          </button>
        )}
      </div>
    </div>
  );
}

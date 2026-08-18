import { useEffect, useRef, useState } from "react";
import { api, getUser, plDate, WEEKDAYS } from "../../api";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { PlanVersion, TrainingPlan, WorkoutRow } from "../../types";

/** Wiersze serii (ciężar × powtórzenia) wpisywane jako tekst — puste są
 * pomijane przy zapisie. */
interface SetRow { weight: string; reps: string }

function toApiSets(rows: SetRow[]): { weight_kg: number; reps: number }[] {
  return rows
    .map((r) => ({
      weight_kg: Number(r.weight.replace(",", ".")),
      reps: Number(r.reps),
    }))
    .filter((s) => isFinite(s.weight_kg) && s.weight_kg > 0 && s.reps > 0);
}

/** "120 s" / "2 min" / "90" → sekundy (null, gdy nie da się odczytać). */
function parseRestSeconds(rest: string | null | undefined): number | null {
  if (!rest) return null;
  const m = rest.replace(",", ".").match(/([\d.]+)\s*(min|m\b)?/i);
  if (!m) return null;
  const value = parseFloat(m[1]);
  if (!isFinite(value) || value <= 0) return null;
  return Math.round(m[2] ? value * 60 : value);
}

/** Timer przerwy między seriami — czysto lokalny, niczego nie zapisuje. */
function RestTimer({ seconds }: { seconds: number }) {
  const [left, setLeft] = useState<number | null>(null);
  const interval = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (interval.current) clearInterval(interval.current); }, []);

  function start() {
    if (interval.current) clearInterval(interval.current);
    setLeft(seconds);
    interval.current = setInterval(() => {
      setLeft((prev) => {
        if (prev === null) return null;
        if (prev <= 1) {
          if (interval.current) clearInterval(interval.current);
          if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function stop() {
    if (interval.current) clearInterval(interval.current);
    setLeft(null);
  }

  if (left === null) {
    return (
      <button type="button" className="btn btn--ghost btn--small" onClick={start}>
        ⏱ przerwa {seconds >= 60 ? `${Math.round(seconds / 60)} min` : `${seconds} s`}
      </button>
    );
  }
  const done = left === 0;
  return (
    <button
      type="button"
      className="btn btn--small"
      style={done
        ? { background: "var(--accent)", color: "var(--accent-ink)" }
        : { background: "var(--bg-raised)", color: "var(--accent)", fontVariantNumeric: "tabular-nums" }}
      onClick={done ? () => start() : stop}
    >
      {done ? "✓ Koniec przerwy — jeszcze raz?" : `⏱ ${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")} (stop)`}
    </button>
  );
}

export default function Plan() {
  const user = getUser()!;
  const [plans, setPlans] = useState<TrainingPlan[] | null>(null);
  const [versions, setVersions] = useState<PlanVersion[] | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [workouts, setWorkouts] = useState<WorkoutRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [logDay, setLogDay] = useState<number | null>(null);
  const [results, setResults] = useState<Record<number, string>>({});
  const [sets, setSets] = useState<Record<number, SetRow[]>>({});
  const [comment, setComment] = useState("");
  const [pain, setPain] = useState(false);
  const [painNote, setPainNote] = useState("");

  const plan = plans?.find((p) => p.status === "ACTIVE") ?? plans?.[0] ?? null;

  useEffect(() => {
    api.get<{ plans: TrainingPlan[] }>(`/api/clients/${user.id}/plans`)
      .then((d) => setPlans(d.plans))
      .catch((e) => setError(e.message));
    api.get<{ workouts: WorkoutRow[] }>(`/api/clients/${user.id}/workouts`)
      .then((d) => setWorkouts(d.workouts))
      .catch(() => undefined);
  }, [user.id]);

  useEffect(() => {
    if (plan && showHistory && !versions) {
      api.get<{ versions: PlanVersion[] }>(`/api/plans/${plan.id}/versions`)
        .then((d) => setVersions(d.versions))
        .catch((e) => setError(e.message));
    }
  }, [plan, showHistory, versions]);

  async function saveWorkout(dayIndex: number) {
    if (!plan?.current_version) return;
    const day = plan.current_version.content.days[dayIndex];
    try {
      await api.post(`/api/clients/${user.id}/workouts`, {
        plan_version_id: plan.current_version.id,
        day_index: dayIndex,
        performed_on: new Date().toISOString().slice(0, 10),
        status: "DONE",
        comment: comment || null,
        pain_flag: pain,
        pain_note: pain ? painNote : null,
        entries: day.exercises.map((ex, i) => ({
          exercise_index: i,
          exercise_name: ex.name,
          result: results[i] || null,
          sets: toApiSets(sets[i] ?? []),
        })),
      });
      setLogDay(null);
      setResults({});
      setSets({});
      setComment("");
      setPain(false);
      setPainNote("");
      const d = await api.get<{ workouts: WorkoutRow[] }>(`/api/clients/${user.id}/workouts`);
      setWorkouts(d.workouts);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
  if (!plans) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Plan treningowy" />
      {!plan?.current_version && <p className="dim">Trener nie przypisał jeszcze planu.</p>}
      {plan?.current_version && (
        <>
          <div className="row row--between" style={{ marginBottom: 10 }}>
            <div>
              <b>{plan.title}</b>
              <div><small>wersja {plan.current_version_no} · {plDate(plan.current_version.created_at)}</small></div>
            </div>
            <button className="btn btn--ghost btn--small" onClick={() => setShowHistory(!showHistory)}>
              {showHistory ? "Ukryj historię" : "Historia wersji"}
            </button>
          </div>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Powód ostatniej zmiany: {plan.current_version.reason}
          </p>

          {showHistory && versions && (
            <div className="card">
              <h3>Historia wersji (nic nie znika)</h3>
              <table className="simple">
                <thead><tr><th>Wersja</th><th>Data</th><th>Powód zmiany</th></tr></thead>
                <tbody>
                  {versions.slice().reverse().map((v) => (
                    <tr key={v.id}>
                      <td>v{v.version_no}</td>
                      <td>{plDate(v.created_at)}</td>
                      <td>{v.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {plan.current_version.content.days.map((day, di) => (
            <div className="card" key={di}>
              <div className="row row--between">
                <h3>{day.name}</h3>
                {day.weekday && <span className="badge">{WEEKDAYS[day.weekday - 1]}</span>}
              </div>
              {day.exercises.map((ex, i) => {
                const restSeconds = parseRestSeconds(ex.rest);
                return (
                  <div className="exercise" key={i}>
                    <div>
                      <b>{ex.name}</b>
                      {ex.comment && <div className="meta">{ex.comment}</div>}
                      {ex.video_url && (
                        <a href={ex.video_url} target="_blank" rel="noreferrer">🎬 technika</a>
                      )}
                      {restSeconds !== null && (
                        <div style={{ marginTop: 6 }}><RestTimer seconds={restSeconds} /></div>
                      )}
                    </div>
                    <div className="meta">
                      {[ex.sets && `${ex.sets}×${ex.reps ?? "?"}`, ex.weight, ex.tempo, ex.rest]
                        .filter(Boolean).join(" · ")}
                    </div>
                  </div>
                );
              })}
              {logDay === di ? (
                <div style={{ marginTop: 10 }}>
                  {day.exercises.map((ex, i) => {
                    const rows = sets[i] ?? [{ weight: "", reps: "" }];
                    const setRows = (next: SetRow[]) => setSets({ ...sets, [i]: next });
                    return (
                      <div key={i} style={{ marginBottom: 12 }}>
                        <label style={{ marginBottom: 2 }}>{ex.name}</label>
                        {rows.map((row, si) => (
                          <div className="row" key={si} style={{ marginBottom: 4 }}>
                            <span className="badge">{si + 1}</span>
                            <input type="text" inputMode="decimal" placeholder="kg"
                              style={{ width: 90 }} value={row.weight}
                              onChange={(e) => setRows(rows.map((r, j) =>
                                j === si ? { ...r, weight: e.target.value } : r))} />
                            <span className="dim">×</span>
                            <input type="number" inputMode="numeric" placeholder="powt."
                              style={{ width: 90 }} value={row.reps}
                              onChange={(e) => setRows(rows.map((r, j) =>
                                j === si ? { ...r, reps: e.target.value } : r))} />
                            {si === rows.length - 1 && (
                              <button type="button" className="btn btn--ghost btn--small"
                                onClick={() => setRows([...rows, {
                                  weight: row.weight, reps: row.reps,
                                }])}>
                                + seria
                              </button>
                            )}
                          </div>
                        ))}
                        <input placeholder="notatka / wynik tekstowy (opcjonalnie)"
                          value={results[i] ?? ""}
                          onChange={(e) => setResults({ ...results, [i]: e.target.value })} />
                      </div>
                    );
                  })}
                  <label>Komentarz do treningu</label>
                  <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
                  <label className="row" style={{ alignItems: "center" }}>
                    <input type="checkbox" style={{ width: "auto" }} checked={pain}
                      onChange={(e) => setPain(e.target.checked)} />
                    <span>Zgłaszam ból / trudność</span>
                  </label>
                  {pain && (
                    <textarea placeholder="Opisz co i kiedy bolało"
                      value={painNote} onChange={(e) => setPainNote(e.target.value)} />
                  )}
                  <div className="row" style={{ marginTop: 10 }}>
                    <button className="btn" onClick={() => saveWorkout(di)}>Zapisz trening</button>
                    <button className="btn btn--ghost" onClick={() => setLogDay(null)}>Anuluj</button>
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: 10 }}>
                  <button className="btn btn--ghost btn--small" onClick={() => setLogDay(di)}>
                    Zapisz wykonanie z wynikami
                  </button>
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {workouts.length > 0 && (
        <div className="card">
          <h3>Ostatnie treningi</h3>
          {workouts.slice(0, 10).map((w) => (
            <div className="exercise" key={w.id}>
              <div>
                <b>{plDate(w.performed_on)}</b>
                {w.pain_flag && <span className="badge badge--danger" style={{ marginLeft: 8 }}>ból</span>}
                {w.entries.filter((e) => e.result || e.sets.length > 0).map((e, i) => (
                  <div className="meta" key={i}>
                    {e.exercise_name}:{" "}
                    {e.sets.length > 0
                      ? e.sets.map((s) => `${s.weight_kg} kg×${s.reps}`).join(", ")
                      : e.result}
                  </div>
                ))}
              </div>
              <div className="meta">{w.status === "DONE" ? "✅" : w.status}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api, getUser } from "../../api";
import { WEEKDAYS, localToday, plDate } from "../../dates";
import { ErrorBox, ExerciseTechniqueLink, Icon, Spinner, TopBar } from "../../components";
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
        <Icon name="timer" size={16} /> przerwa {seconds >= 60 ? `${Math.round(seconds / 60)} min` : `${seconds} s`}
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
      {done
        ? "✓ Koniec przerwy — jeszcze raz?"
        : <><Icon name="timer" size={16} /> {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")} (stop)</>}
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

  const [historyError, setHistoryError] = useState<string | null>(null);
  const loadWorkouts = () => {
    setHistoryError(null);
    api.get<{ workouts: WorkoutRow[] }>(`/api/clients/${user.id}/workouts`)
      .then((d) => setWorkouts(d.workouts))
      // Historia to sekcja pomocnicza — błąd jest widoczny przy niej
      // (z ponowieniem), nie wygasza całego planu.
      .catch((e) => setHistoryError(`Nie udało się wczytać historii treningów. ${e.message}`));
  };
  const loadPlans = () => {
    setError(null);
    api.get<{ plans: TrainingPlan[] }>(`/api/clients/${user.id}/plans`)
      .then((d) => setPlans(d.plans))
      .catch((e) => setError(e.message));
  };
  useEffect(() => {
    loadPlans();
    loadWorkouts();
  }, [user.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (plan && showHistory && !versions) {
      api.get<{ versions: PlanVersion[] }>(`/api/plans/${plan.id}/versions`)
        .then((d) => setVersions(d.versions))
        .catch((e) => setError(e.message));
    }
  }, [plan, showHistory, versions]);

  const [saveError, setSaveError] = useState<string | null>(null);

  async function saveWorkout(dayIndex: number) {
    if (!plan?.current_version) return;
    const day = plan.current_version.content.days[dayIndex];
    setSaveError(null);
    try {
      await api.post(`/api/clients/${user.id}/workouts`, {
        plan_version_id: plan.current_version.id,
        day_index: dayIndex,
        performed_on: localToday(),
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
      // Błąd ZAPISU pokazujemy przy formularzu (nie pełnoekranowo) —
      // wpisane serie/komentarz zostają nietknięte do ponowienia.
      setSaveError((e as Error).message);
    }
  }

  if (error) return <div className="page"><ErrorBox error={error} onRetry={loadPlans} /></div>;
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
            <button className="btn btn--ghost btn--small" aria-expanded={showHistory}
              onClick={() => setShowHistory(!showHistory)}>
              {showHistory ? "Ukryj historię" : "Historia wersji"}
            </button>
          </div>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Powód ostatniej zmiany: {plan.current_version.reason}
          </p>

          {showHistory && versions && (
            <div className="card">
              <h2>Historia wersji (nic nie znika)</h2>
              <div className="table-wrap">
                <table className="simple table--cards">
                  <thead><tr><th>Wersja</th><th>Data</th><th>Powód zmiany</th></tr></thead>
                  <tbody>
                    {versions.slice().reverse().map((v) => (
                      <tr key={v.id}>
                        <td data-label="Wersja">v{v.version_no}</td>
                        <td data-label="Data">{plDate(v.created_at)}</td>
                        <td data-label="Powód zmiany">{v.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {plan.current_version.content.days.map((day, di) => (
            <div className="card" key={di}>
              <div className="row row--between">
                <h2>{day.name}</h2>
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
                        <a href={ex.video_url} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Icon name="film" size={16} /> technika</a>
                      )}
                      {ex.exercise_id && (
                        <ExerciseTechniqueLink exerciseId={ex.exercise_id} name={ex.name} />
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
                        <span style={{ display: "block", fontSize: "0.85rem", color: "var(--text-dim)", margin: "10px 0 2px" }}>{ex.name}</span>
                        {rows.map((row, si) => (
                          <div className="row" key={si} style={{ marginBottom: 4 }}>
                            <span className="badge" aria-hidden>{si + 1}</span>
                            <input type="text" inputMode="decimal" placeholder="kg"
                              aria-label={`${ex.name} — seria ${si + 1}: ciężar (kg)`}
                              style={{ width: 90 }} value={row.weight}
                              onChange={(e) => setRows(rows.map((r, j) =>
                                j === si ? { ...r, weight: e.target.value } : r))} />
                            <span className="dim" aria-hidden>×</span>
                            <input type="number" inputMode="numeric" placeholder="powt."
                              aria-label={`${ex.name} — seria ${si + 1}: powtórzenia`}
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
                          aria-label={`${ex.name} — notatka lub wynik tekstowy`}
                          value={results[i] ?? ""}
                          onChange={(e) => setResults({ ...results, [i]: e.target.value })} />
                      </div>
                    );
                  })}
                  <label htmlFor="workout-comment">Komentarz do treningu</label>
                  <textarea id="workout-comment" value={comment} onChange={(e) => setComment(e.target.value)} />
                  <label className="row" style={{ alignItems: "center" }}>
                    <input type="checkbox" checked={pain}
                      onChange={(e) => setPain(e.target.checked)} />
                    <span>Zgłaszam ból / trudność</span>
                  </label>
                  {pain && (
                    <textarea placeholder="Opisz co i kiedy bolało"
                      aria-label="Opis bólu lub trudności"
                      value={painNote} onChange={(e) => setPainNote(e.target.value)} />
                  )}
                  <ErrorBox error={saveError} onRetry={() => saveWorkout(di)} />
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

      <ErrorBox error={historyError} onRetry={loadWorkouts} />
      {workouts.length > 0 && (
        <div className="card">
          <h2>Ostatnie treningi</h2>
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
              <div className="meta">{w.status === "DONE" ? <Icon name="check" size={16} label="wykonany" /> : w.status}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

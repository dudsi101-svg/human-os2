import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getUser } from "../../api";
import { WEEKDAYS, localToday, plDate } from "../../dates";
import { ErrorBox, Icon, Spinner, TopBar } from "../../components";
import { OpisCwiczenia } from "../../opisCwiczenia";
import { PozycjaBloku, PozycjaCardio, RestTimer, parseRestSeconds, rodzajPozycji } from "../../pozycje";
import { DniPlanu, MACHINE_LABELS, PlanVersion, TrainingPlan, WorkoutRow } from "../../types";
import { Dlaczego } from "../../wiedza/Dlaczego";
import DniTreningowe, { etykietaDnia } from "./DniTreningowe";

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
  // Cardio (0.73.0): urządzenie wybrane na dziś (per pozycja) i wpis bez serii.
  const [maszyny, setMaszyny] = useState<Record<number, string>>({});
  const [cardioLog, setCardioLog] = useState<Record<number, { czas: string; rpe: string; tetno: string; dystans: string }>>({});
  // Blok rozgrzewki/rozciągania odhaczany jako całość.
  const [blokiDone, setBlokiDone] = useState<Record<number, boolean>>({});
  const [pain, setPain] = useState(false);
  const [painNote, setPainNote] = useState("");

  const plan = plans?.find((p) => p.status === "ACTIVE") ?? plans?.[0] ?? null;
  // 0.58.0: nowsza wersja opublikowana, gdy ekran był otwarty — informujemy
  // i dajemy „Wczytaj zmiany”, zamiast podmieniać plan pod otwartym
  // formularzem wykonania (zapis pozostaje na wersji, na której się zaczął).
  const [nowszaWersja, setNowszaWersja] = useState<number | null>(null);
  const [ostatniaZmiana, setOstatniaZmiana] = useState<string | null>(null);
  useEffect(() => {
    if (!plan) return;
    api.get<{ changes: { id: string }[] }>(`/api/plany/training/${plan.id}/zmiany`)
      .then((d) => setOstatniaZmiana(d.changes[0]?.id ?? null)).catch(() => setOstatniaZmiana(null));
    const sprawdz = () => {
      if (document.visibilityState !== "visible") return;
      api.get<{ plans: TrainingPlan[] }>(`/api/clients/${user.id}/plans`)
        .then((d) => {
          const p = d.plans.find((x) => x.id === plan.id);
          if (p && p.current_version_no > plan.current_version_no) setNowszaWersja(p.current_version_no);
        })
        .catch(() => undefined);
    };
    document.addEventListener("visibilitychange", sprawdz);
    window.addEventListener("focus", sprawdz);
    const t = setInterval(sprawdz, 60_000);
    return () => { document.removeEventListener("visibilitychange", sprawdz); window.removeEventListener("focus", sprawdz); clearInterval(t); };
  }, [plan?.id, plan?.current_version_no, user.id]); // eslint-disable-line react-hooks/exhaustive-deps

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
  // Dni treningowe (0.71.0): układ klienta (albo propozycja trenera) do odznak przy dniach.
  const [dni, setDni] = useState<DniPlanu | null>(null);

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
        entries: day.exercises.map((ex, i) => {
          const rodzaj = rodzajPozycji(ex);
          if (rodzaj === "cardio") {
            const c = cardioLog[i] ?? { czas: "", rpe: "", tetno: "", dystans: "" };
            const liczba = (v: string) => { const n = Number(v.replace(",", ".")); return v.trim() && isFinite(n) ? n : null; };
            return {
              exercise_index: i, exercise_name: ex.name, result: results[i] || null, sets: [],
              duration_min: liczba(c.czas) !== null ? Math.round(liczba(c.czas)!) : null,
              rpe: liczba(c.rpe) !== null ? Math.round(liczba(c.rpe)!) : null,
              avg_hr: liczba(c.tetno) !== null ? Math.round(liczba(c.tetno)!) : null,
              distance_km: liczba(c.dystans),
              machine: maszyny[i] ?? ex.cardio?.machines[0] ?? null,
            };
          }
          if (rodzaj !== "strength") {
            return { exercise_index: i, exercise_name: ex.name, sets: [],
              result: blokiDone[i] ? "wykonano" : results[i] || null };
          }
          return { exercise_index: i, exercise_name: ex.name, result: results[i] || null, sets: toApiSets(sets[i] ?? []) };
        }),
      });
      setLogDay(null);
      setResults({});
      setSets({});
      setCardioLog({});
      setBlokiDone({});
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
            {ostatniaZmiana && <> · <Link to={`/zmiany/${ostatniaZmiana}`}>Zobacz zmiany</Link></>}
          </p>
          {nowszaWersja && (
            <p className="alert alert--info" role="status">
              Trener opublikował nowszą wersję planu (v{nowszaWersja}). Twój otwarty zapis treningu pozostaje na wersji {plan.current_version_no}.{" "}
              <button type="button" className="btn btn--small" onClick={() => { setNowszaWersja(null); loadPlans(); }}>Wczytaj zmiany</button>
            </p>
          )}
          {/* Wiedza (0.56.0): „Dlaczego?” czyta zapisany ślad decyzji —
              panel nakłada się na ekran, więc otwarty formularz sesji
              i timer zostają nietknięte. */}
          <div className="row" style={{ marginBottom: 10 }}>
            <Dlaczego etykieta="Dlaczego ta wersja?"
              naglowek={`Wersja ${plan.current_version_no} planu`}
              cel={{ plan_id: plan.id, plan_revision: plan.current_version_no,
                target_type: "plan_change", target_id: "plan" }} />
            <Dlaczego etykieta="Dlaczego tyle dni?"
              naglowek="Liczba treningów w tygodniu"
              cel={{ plan_id: plan.id, plan_revision: plan.current_version_no,
                target_type: "training_frequency", target_id: "plan" }} />
          </div>

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

          <DniTreningowe key={`dni-${plan.id}-${plan.current_version_no}`} clientId={user.id} planId={plan.id} tryb="klient" onZmiana={setDni} />

          {plan.current_version.content.days.map((day, di) => (
            <div className="card" key={di}>
              <div className="row row--between">
                <h2>{day.name}</h2>
                {(() => {
                  const wpis = dni?.days.find((x) => x.day_index === di);
                  const etykieta = dni && wpis ? etykietaDnia(dni.source, wpis.weekday) : null;
                  if (etykieta) return <span className="badge" data-testid={`dzien-${di}`}>{etykieta}</span>;
                  return day.weekday ? <span className="badge">{WEEKDAYS[day.weekday - 1]}</span> : null;
                })()}
              </div>
              {day.exercises.map((ex, i) => {
                const rodzaj = rodzajPozycji(ex);
                if (rodzaj === "warmup_block" || rodzaj === "stretch_block") {
                  return <PozycjaBloku key={i} ex={ex} powrot="/plan" testid={`blok-${di}-${i}`} />;
                }
                if (rodzaj === "cardio") {
                  return (
                    <PozycjaCardio key={i} ex={ex} testid={`cardio-${di}-${i}`}
                      machine={maszyny[i] ?? null} onMachine={(m) => setMaszyny({ ...maszyny, [i]: m })}
                      dlaczego={{ plan_id: plan.id, plan_revision: plan.current_version_no, target_id: `d${di}:e${i}` }} />
                  );
                }
                const restSeconds = parseRestSeconds(ex.rest);
                return (
                  <div className="exercise" key={i}>
                    <div>
                      <b>{ex.name}</b>
                      {ex.comment && <div className="meta">{ex.comment}</div>}
                      {ex.video_url && (
                        <a href={ex.video_url} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Icon name="film" size={16} /> technika</a>
                      )}
                      {/* Opis z bazy trenera (0.75.0): po id, a bez id po nazwie;
                          pełna karta w Wiedzy z powrotem do planu. */}
                      <OpisCwiczenia exerciseId={ex.exercise_id} name={ex.name} powrot="/plan" testid={`opis-${di}-${i}`} />
                      {restSeconds !== null && (
                        <div style={{ marginTop: 6 }}><RestTimer seconds={restSeconds} /></div>
                      )}
                      <div style={{ marginTop: 6 }}>
                        <Dlaczego naglowek={`${ex.name} — dawka w Twoim planie`}
                          cel={{ plan_id: plan.id, plan_revision: plan.current_version_no,
                            target_type: "exercise_prescription", target_id: `d${di}:e${i}` }} />
                      </div>
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
                    const rodzaj = rodzajPozycji(ex);
                    if (rodzaj === "warmup_block" || rodzaj === "stretch_block") {
                      return (
                        <label key={i} className="row" style={{ alignItems: "center", margin: "10px 0" }}>
                          <input type="checkbox" checked={!!blokiDone[i]} data-testid={`blok-done-${di}-${i}`}
                            onChange={(e) => setBlokiDone({ ...blokiDone, [i]: e.target.checked })} />
                          <span>{ex.name} — wykonane w całości</span>
                        </label>
                      );
                    }
                    if (rodzaj === "cardio") {
                      const c = cardioLog[i] ?? { czas: "", rpe: "", tetno: "", dystans: "" };
                      const ustaw = (k: keyof typeof c, v: string) => setCardioLog({ ...cardioLog, [i]: { ...c, [k]: v } });
                      const urzadzenie = maszyny[i] ?? ex.cardio?.machines[0];
                      return (
                        <div key={i} style={{ marginBottom: 12 }} data-testid={`cardio-log-${di}-${i}`}>
                          <span style={{ display: "block", fontSize: "0.85rem", color: "var(--text-dim)", margin: "10px 0 2px" }}>
                            {ex.name}{urzadzenie && <> · {MACHINE_LABELS[urzadzenie] ?? urzadzenie}</>}
                          </span>
                          <div className="field-row">
                            <input type="number" inputMode="numeric" placeholder="czas (min)" aria-label={`${ex.name} — czas w minutach`}
                              value={c.czas} onChange={(e) => ustaw("czas", e.target.value)} />
                            <input type="number" inputMode="numeric" min={1} max={10} placeholder="RPE 1–10" aria-label={`${ex.name} — RPE (1–10)`}
                              value={c.rpe} onChange={(e) => ustaw("rpe", e.target.value)} />
                          </div>
                          <div className="field-row" style={{ marginTop: 6 }}>
                            <input type="number" inputMode="numeric" placeholder="średnie tętno (opcjonalnie)" aria-label={`${ex.name} — średnie tętno (ud./min, opcjonalnie)`}
                              value={c.tetno} onChange={(e) => ustaw("tetno", e.target.value)} />
                            <input type="text" inputMode="decimal" placeholder="dystans km (opcjonalnie)" aria-label={`${ex.name} — dystans w km (opcjonalnie)`}
                              value={c.dystans} onChange={(e) => ustaw("dystans", e.target.value)} />
                          </div>
                        </div>
                      );
                    }
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
                {w.entries.filter((e) => e.result || e.sets.length > 0 || e.duration_min || e.rpe).map((e, i) => (
                  <div className="meta" key={i}>
                    {e.exercise_name}:{" "}
                    {e.sets.length > 0
                      ? e.sets.map((s) => `${s.weight_kg} kg×${s.reps}`).join(", ")
                      : (e.duration_min || e.rpe)
                        ? [e.machine && (MACHINE_LABELS[e.machine] ?? e.machine), e.duration_min && `${e.duration_min} min`,
                          e.rpe && `RPE ${e.rpe}`, e.avg_hr && `${e.avg_hr} ud./min`, e.distance_km && `${e.distance_km} km`]
                          .filter(Boolean).join(" · ")
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

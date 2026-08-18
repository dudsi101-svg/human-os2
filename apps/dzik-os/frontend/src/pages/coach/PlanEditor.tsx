import { FormEvent, useState } from "react";
import { api } from "../../api";
import { WEEKDAYS } from "../../dates";
import { ErrorBox } from "../../components";
import { Exercise, PlanDay, TrainingPlan } from "../../types";

const emptyExercise = (): Exercise => ({ name: "", sets: "", reps: "", weight: "", rest: "" });
const emptyDay = (): PlanDay => ({ name: "", weekday: null, exercises: [emptyExercise()] });

export default function PlanEditor({
  clientId,
  existingPlan,
  initialDays,
  onSaved,
  onCancel,
}: {
  clientId: string | null;
  existingPlan: TrainingPlan | null;
  initialDays?: PlanDay[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(existingPlan?.title ?? "");
  const [reason, setReason] = useState("");
  const [days, setDays] = useState<PlanDay[]>(
    initialDays?.length ? JSON.parse(JSON.stringify(initialDays)) : [emptyDay()]
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setDay = (i: number, day: PlanDay) =>
    setDays(days.map((d, j) => (i === j ? day : d)));

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const cleanDays = days
      .filter((d) => d.name.trim())
      .map((d) => ({ ...d, exercises: d.exercises.filter((ex) => ex.name.trim()) }));
    try {
      if (existingPlan) {
        await api.post(`/api/plans/${existingPlan.id}/versions`, { reason, days: cleanDays });
      } else {
        await api.post("/api/plans", {
          client_id: clientId, title, version: { reason, days: cleanDays },
        });
      }
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card card--accent" onSubmit={save}>
      <h3>{existingPlan ? `Nowa wersja: ${existingPlan.title}` : "Nowy plan treningowy"}</h3>
      {!existingPlan && (
        <>
          <label>Nazwa planu</label>
          <input required value={title} onChange={(e) => setTitle(e.target.value)} />
        </>
      )}
      <label>Powód {existingPlan ? "zmiany" : "utworzenia"} (obowiązkowy — trafia do historii)</label>
      <input required value={reason} onChange={(e) => setReason(e.target.value)}
        placeholder="np. progresja po raporcie z tygodnia 3" />
      {days.map((day, di) => (
        <div key={di} className="card" style={{ marginTop: 10 }}>
          <div className="field-row">
            <div>
              <label>Nazwa dnia</label>
              <input value={day.name} onChange={(e) => setDay(di, { ...day, name: e.target.value })}
                placeholder="np. Trening A — góra" />
            </div>
            <div>
              <label>Dzień tygodnia</label>
              <select value={day.weekday ?? ""}
                onChange={(e) => setDay(di, { ...day, weekday: e.target.value ? Number(e.target.value) : null })}>
                <option value="">— dowolny —</option>
                {WEEKDAYS.map((w, i) => (
                  <option key={i} value={i + 1}>{w}</option>
                ))}
              </select>
            </div>
          </div>
          {day.exercises.map((ex, ei) => (
            <div key={ei} style={{ borderTop: "1px solid var(--border)", paddingTop: 8, marginTop: 8 }}>
              <label>Ćwiczenie {ei + 1}</label>
              <input value={ex.name} placeholder="nazwa ćwiczenia"
                onChange={(e) => {
                  const exs = [...day.exercises];
                  exs[ei] = { ...ex, name: e.target.value };
                  setDay(di, { ...day, exercises: exs });
                }} />
              <div className="field-row-3" style={{ marginTop: 6 }}>
                {(["sets", "reps", "weight"] as const).map((f) => (
                  <input key={f} value={(ex[f] as string) ?? ""}
                    placeholder={{ sets: "serie", reps: "powt.", weight: "ciężar" }[f]}
                    onChange={(e) => {
                      const exs = [...day.exercises];
                      exs[ei] = { ...ex, [f]: e.target.value };
                      setDay(di, { ...day, exercises: exs });
                    }} />
                ))}
              </div>
              <div className="field-row" style={{ marginTop: 6 }}>
                <input value={ex.tempo ?? ""} placeholder="tempo (np. 2011)"
                  onChange={(e) => {
                    const exs = [...day.exercises];
                    exs[ei] = { ...ex, tempo: e.target.value };
                    setDay(di, { ...day, exercises: exs });
                  }} />
                <input value={ex.rest ?? ""} placeholder="przerwa (np. 120 s)"
                  onChange={(e) => {
                    const exs = [...day.exercises];
                    exs[ei] = { ...ex, rest: e.target.value };
                    setDay(di, { ...day, exercises: exs });
                  }} />
              </div>
              <input style={{ marginTop: 6 }} value={ex.comment ?? ""} placeholder="komentarz"
                onChange={(e) => {
                  const exs = [...day.exercises];
                  exs[ei] = { ...ex, comment: e.target.value };
                  setDay(di, { ...day, exercises: exs });
                }} />
              <input style={{ marginTop: 6 }} value={ex.video_url ?? ""}
                placeholder="link do filmu instruktażowego (https://…)"
                onChange={(e) => {
                  const exs = [...day.exercises];
                  exs[ei] = { ...ex, video_url: e.target.value };
                  setDay(di, { ...day, exercises: exs });
                }} />
            </div>
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            <button type="button" className="btn btn--ghost btn--small"
              onClick={() => setDay(di, { ...day, exercises: [...day.exercises, emptyExercise()] })}>
              + ćwiczenie
            </button>
            <button type="button" className="btn btn--danger btn--small"
              onClick={() => setDays(days.filter((_, j) => j !== di))}>
              usuń dzień
            </button>
          </div>
        </div>
      ))}
      <div className="row" style={{ marginTop: 10 }}>
        <button type="button" className="btn btn--ghost btn--small"
          onClick={() => setDays([...days, emptyDay()])}>
          + dzień treningowy
        </button>
      </div>
      <ErrorBox error={error} />
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={busy}>
          {busy ? "Zapisywanie…" : existingPlan ? "Zapisz nową wersję" : "Utwórz plan"}
        </button>
        <button type="button" className="btn btn--ghost" onClick={onCancel}>Anuluj</button>
      </div>
    </form>
  );
}

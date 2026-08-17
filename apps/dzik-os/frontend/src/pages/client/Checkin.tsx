import { FormEvent, useEffect, useState } from "react";
import { api, getUser, plDate } from "../../api";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { CheckinData } from "../../types";

function mondayOfCurrentWeek(): string {
  const d = new Date();
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - day + 1);
  return d.toISOString().slice(0, 10);
}

const SCALES: [string, string][] = [
  ["energy", "Energia"], ["sleep", "Sen"], ["hunger", "Głód"],
  ["stress", "Stres"], ["recovery", "Regeneracja"], ["diet_adherence", "Realizacja diety"],
];

export default function Checkin() {
  const user = getUser()!;
  const [checkins, setCheckins] = useState<CheckinData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({
    week_start: mondayOfCurrentWeek(),
    energy: 3, sleep: 3, hunger: 3, stress: 3, recovery: 3, diet_adherence: 3,
  });
  const [photos, setPhotos] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get<{ checkins: CheckinData[] }>(`/api/clients/${user.id}/checkins`)
      .then((d) => setCheckins(d.checkins))
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      const photo_ids: string[] = [];
      for (const f of photos) {
        const up = await api.upload<{ id: string }>("/api/files", f);
        photo_ids.push(up.id);
      }
      await api.post("/api/checkins", {
        ...form,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        trainings_done: form.trainings_done ? Number(form.trainings_done) : null,
        photo_ids,
      });
      setOk("Raport wysłany. Trener odpowie w aplikacji.");
      setPhotos([]);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const set = (key: string, value: unknown) => setForm({ ...form, [key]: value });

  if (!checkins) return <div className="page"><Spinner /></div>;
  const currentWeek = form.week_start as string;
  const existing = checkins.find((c) => c.week_start === currentWeek);

  return (
    <div className="page">
      <TopBar title="Raport tygodniowy" />
      <form className="card" onSubmit={submit}>
        <h3>Tydzień od {plDate(currentWeek)}</h3>
        {existing && existing.status === "REVIEWED" && (
          <p className="alert alert--info">Ten tydzień został już oceniony — raport można wysłać w kolejnym tygodniu.</p>
        )}
        {existing && existing.status !== "REVIEWED" && (
          <p className="alert alert--info">Masz już raport za ten tydzień (rewizja {existing.revision}). Wysłanie ponownie zapisze poprawkę — poprzednia wersja zostaje w historii.</p>
        )}
        <div className="field-row">
          <div>
            <label>Masa ciała (kg)</label>
            <input type="number" step="0.1" min="0"
              value={(form.weight_kg as string) ?? ""}
              onChange={(e) => set("weight_kg", e.target.value)} />
          </div>
          <div>
            <label>Wykonane treningi</label>
            <input type="number" min="0" max="21"
              value={(form.trainings_done as string) ?? ""}
              onChange={(e) => set("trainings_done", e.target.value)} />
          </div>
        </div>
        {SCALES.map(([key, label]) => (
          <div key={key}>
            <label>{label}: {String(form[key])}/5</label>
            <input type="range" min="1" max="5" value={form[key] as number}
              onChange={(e) => set(key, Number(e.target.value))} />
          </div>
        ))}
        <label>Ból lub urazy (jeśli wystąpiły)</label>
        <textarea value={(form.pain_note as string) ?? ""}
          onChange={(e) => set("pain_note", e.target.value)} />
        <label>Komentarz</label>
        <textarea value={(form.comment as string) ?? ""}
          onChange={(e) => set("comment", e.target.value)} />
        <label>Pytania do trenera</label>
        <textarea value={(form.questions as string) ?? ""}
          onChange={(e) => set("questions", e.target.value)} />
        <label>Zdjęcia sylwetki (opcjonalnie)</label>
        <input type="file" accept="image/jpeg,image/png,image/webp" multiple
          onChange={(e) => setPhotos(Array.from(e.target.files ?? []))} />
        {photos.length > 0 && <small>{photos.length} zdjęć do wysłania</small>}
        <ErrorBox error={error} />
        {ok && <div className="alert alert--info">{ok}</div>}
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy || existing?.status === "REVIEWED"}>
            {busy ? "Wysyłanie…" : existing ? "Wyślij poprawkę" : "Wyślij raport"}
          </button>
        </div>
      </form>

      <h2>Poprzednie raporty</h2>
      {checkins.length === 0 && <p className="dim">Brak raportów.</p>}
      {checkins.map((c) => (
        <div className="card" key={c.id}>
          <div className="row row--between">
            <b>{plDate(c.week_start)}</b>
            <span className={`badge ${c.status === "REVIEWED" ? "badge--ok" : "badge--warn"}`}>
              {c.status === "REVIEWED" ? "Oceniony" : "Wysłany"}
            </span>
          </div>
          <small>
            {[
              c.payload.weight_kg != null && `masa ${c.payload.weight_kg} kg`,
              c.payload.trainings_done != null && `${c.payload.trainings_done} treningów`,
              c.revision > 1 && `rewizja ${c.revision}`,
            ].filter(Boolean).join(" · ")}
          </small>
          {c.coach_response && (
            <div className="alert alert--info" style={{ marginTop: 8 }}>
              <b>Odpowiedź trenera:</b> {c.coach_response}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

import { FormEvent, useEffect, useState } from "react";
import { api, getUser } from "../../api";
import { mondayOfWeek, plDate } from "../../dates";
import { ErrorBox, SectionLabel, Spinner, TopBar } from "../../components";
import { CheckinData } from "../../types";

const SCALES: [string, string, string][] = [
  ["energy", "Energia", "niska–wysoka"],
  ["sleep", "Sen", "słaby–dobry"],
  ["hunger", "Głód", "brak–duży"],
  ["stress", "Stres", "niski–wysoki"],
  ["recovery", "Regeneracja", "słaba–dobra"],
  ["diet_adherence", "Realizacja diety", "słaba–pełna"],
];

export default function Checkin() {
  const user = getUser()!;
  const [checkins, setCheckins] = useState<CheckinData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({
    week_start: mondayOfWeek(),
    energy: 3, sleep: 3, hunger: 3, stress: 3, recovery: 3, diet_adherence: 3,
  });
  const [photos, setPhotos] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const MAX_PHOTOS = 8; // ten sam limit egzekwuje backend (422)

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
    if (photos.length > MAX_PHOTOS) {
      setError(`Maksymalnie ${MAX_PHOTOS} zdjęć na raport.`);
      setBusy(false);
      return;
    }
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
  const locked = existing?.status === "REVIEWED";

  return (
    <div className="page">
      <TopBar title="Raport tygodniowy" />
      <form className="card" onSubmit={submit}>
        <div className="row row--between">
          <h3 style={{ margin: 0 }}>Tydzień od {plDate(currentWeek)}</h3>
          {existing && (
            <span className={`badge ${locked ? "badge--ok" : "badge--warn"}`}>
              {locked ? "oceniony" : `rewizja ${existing.revision}`}
            </span>
          )}
        </div>
        {locked && (
          <p className="alert alert--info">
            Ten tydzień został już oceniony — raport można wysłać w kolejnym tygodniu.
          </p>
        )}
        {existing && !locked && (
          <p className="alert alert--info">
            Masz już raport za ten tydzień. Wysłanie ponownie zapisze poprawkę —
            poprzednia wersja zostaje w historii.
          </p>
        )}

        <SectionLabel n={1} title="Ciało" />
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
        <label>Zdjęcia sylwetki (opcjonalnie, maks. {MAX_PHOTOS})</label>
        <input type="file" accept="image/jpeg,image/png,image/webp" multiple
          onChange={(e) => setPhotos(Array.from(e.target.files ?? []))} />
        {photos.length > 0 && (
          <small style={photos.length > MAX_PHOTOS ? { color: "var(--danger)" } : undefined}>
            {photos.length} zdjęć do wysłania
            {photos.length > MAX_PHOTOS && ` — limit to ${MAX_PHOTOS}`}
          </small>
        )}

        <SectionLabel n={2} title="Samopoczucie" />
        <p className="dim" style={{ fontSize: "0.82rem", marginTop: -4 }}>
          Przesuń suwaki — to szybciej niż opisywanie słowami i łatwiej
          porównać tydzień do tygodnia.
        </p>
        {SCALES.map(([key, label, hint]) => (
          <ScaleRow key={key} label={label} hint={hint} value={form[key] as number}
            onChange={(v) => set(key, v)} />
        ))}

        <SectionLabel n={3} title="Ból, urazy i pytania" />
        <label>Ból lub urazy (jeśli wystąpiły)</label>
        <textarea value={(form.pain_note as string) ?? ""}
          placeholder="Opisz dokładnie: gdzie, kiedy, przy jakim ruchu"
          onChange={(e) => set("pain_note", e.target.value)} />
        <label>Komentarz</label>
        <textarea value={(form.comment as string) ?? ""}
          onChange={(e) => set("comment", e.target.value)} />
        <label>Pytania do trenera</label>
        <textarea value={(form.questions as string) ?? ""}
          onChange={(e) => set("questions", e.target.value)} />

        <ErrorBox error={error} />
        {ok && <div className="alert alert--info">{ok}</div>}
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy || locked}>
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
              {c.rating != null && (
                <div style={{ marginTop: 4 }}>
                  <span className="badge badge--accent">Ocena raportu: {c.rating}/5</span>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ScaleRow({ label, hint, value, onChange }: {
  label: string; hint: string; value: number; onChange: (v: number) => void;
}) {
  return (
    <div className="scale-row">
      <div className="row row--between">
        <label style={{ margin: 0 }}>{label}</label>
        <span className="badge badge--accent">{value}/5</span>
      </div>
      <input type="range" min="1" max="5" value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
      <div className="scale-row__hint">{hint}</div>
    </div>
  );
}

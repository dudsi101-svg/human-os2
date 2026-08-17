import { FormEvent, useEffect, useState } from "react";
import { api, getUser, plDate } from "../../api";
import { AuthImage, ErrorBox, Sparkline, Spinner, TopBar } from "../../components";
import { KIND_LABELS, MeasurementRow } from "../../types";

interface Photo { id: string; file_id: string; taken_at: string; note: string | null }

export default function Progress() {
  const user = getUser()!;
  const [rows, setRows] = useState<MeasurementRow[] | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState("weight");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("kg");

  const load = () => {
    api.get<{ measurements: MeasurementRow[] }>(`/api/clients/${user.id}/measurements`)
      .then((d) => setRows(d.measurements))
      .catch((e) => setError(e.message));
    api.get<{ photos: Photo[] }>(`/api/clients/${user.id}/photos`)
      .then((d) => setPhotos(d.photos))
      .catch(() => undefined);
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function addMeasurement(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/api/clients/${user.id}/measurements`, {
        kind, value: Number(value), unit,
        measured_at: new Date().toISOString().slice(0, 10),
      });
      setValue("");
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!rows) return <div className="page"><Spinner /></div>;
  const kinds = Array.from(new Set(rows.map((r) => r.kind)));

  return (
    <div className="page">
      <TopBar title="Pomiary i postępy" />
      <ErrorBox error={error} />
      <form className="card" onSubmit={addMeasurement}>
        <h3>Dodaj pomiar</h3>
        <div className="field-row-3">
          <div>
            <label>Rodzaj</label>
            <select value={kind} onChange={(e) => {
              setKind(e.target.value);
              setUnit(e.target.value === "weight" ? "kg" : "cm");
            }}>
              {Object.entries(KIND_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Wartość</label>
            <input type="number" step="0.1" required value={value}
              onChange={(e) => setValue(e.target.value)} />
          </div>
          <div>
            <label>Jednostka</label>
            <input value={unit} onChange={(e) => setUnit(e.target.value)} />
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <button className="btn btn--ghost btn--small">Zapisz pomiar</button>
        </div>
      </form>

      {kinds.map((k) => {
        const data = rows.filter((r) => r.kind === k);
        return (
          <div className="card" key={k}>
            <div className="row row--between">
              <h3>{KIND_LABELS[k] ?? k}</h3>
              <span className="badge">{data[data.length - 1].value} {data[data.length - 1].unit}</span>
            </div>
            <Sparkline unit={data[0].unit}
              points={data.map((r) => ({ x: plDate(r.measured_at), y: r.value }))} />
          </div>
        );
      })}

      {photos.length > 0 && (
        <div className="card">
          <h3>Zdjęcia progresu</h3>
          <div className="photo-grid">
            {photos.map((p) => (
              <AuthImage key={p.id} fileId={p.file_id} alt={`Zdjęcie ${plDate(p.taken_at)}`} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

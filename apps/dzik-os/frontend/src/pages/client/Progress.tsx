import { FormEvent, useEffect, useState } from "react";
import { api, getUser, plDate, todayIso } from "../../api";
import {
  AuthImage,
  ErrorBox,
  PersonalRecordsCard,
  PhotoCompare,
  Sparkline,
  Spinner,
  StrengthChartsCard,
  TopBar,
} from "../../components";
import {
  CATEGORY_LABELS,
  KIND_LABELS,
  MeasurementRow,
  MonitoringData,
  OBSERVATION_CATEGORY_LABELS,
  ObservationRow,
  ScheduleItem,
  SEVERITY_LABELS,
  WELLBEING_LABELS,
} from "../../types";

interface Photo { id: string; file_id: string; taken_at: string; note: string | null }

export default function Progress() {
  const user = getUser()!;
  const [rows, setRows] = useState<MeasurementRow[] | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [monitoring, setMonitoring] = useState<MonitoringData | null>(null);
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
    api.get<MonitoringData>(`/api/clients/${user.id}/monitoring`)
      .then(setMonitoring)
      .catch(() => undefined);
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function addMeasurement(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/api/clients/${user.id}/measurements`, {
        kind, value: Number(value), unit,
        measured_at: todayIso(),
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
      <TopBar title="Monitoring i postępy" />
      <ErrorBox error={error} />

      {monitoring?.goal && <GoalCard goal={monitoring.goal} />}

      <PersonalRecordsCard clientId={user.id} />
      <StrengthChartsCard clientId={user.id} />

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

      {monitoring && Object.keys(monitoring.wellbeing_series).length > 0 && (
        <div className="card">
          <h3>Samopoczucie (z raportów tygodniowych)</h3>
          {Object.entries(monitoring.wellbeing_series).map(([key, points]) => (
            <div key={key} style={{ marginTop: 10 }}>
              <div className="row row--between">
                <b style={{ fontSize: "0.9rem" }}>{WELLBEING_LABELS[key] ?? key}</b>
                <span className="badge">{points[points.length - 1].value}/5</span>
              </div>
              <Sparkline unit="/5" points={points.map((p) => ({ x: plDate(p.date), y: p.value }))} />
            </div>
          ))}
        </div>
      )}

      {monitoring && <NutritionLogCard target={monitoring.nutrition.target_kcal}
        series={monitoring.nutrition.log_series} onSaved={load} userId={user.id} />}

      {monitoring && Object.keys(monitoring.adherence).length > 0 && (
        <div className="card">
          <h3>Realizacja harmonogramu ({monitoring.period_days} dni)</h3>
          {Object.entries(monitoring.adherence).map(([cat, bucket]) => (
            <AdherenceBar key={cat} label={CATEGORY_LABELS[cat] ?? cat} bucket={bucket} />
          ))}
        </div>
      )}

      <ObservationsCard userId={user.id} onSaved={load} />

      {photos.length >= 2 && <PhotoCompare photos={photos} formatDate={plDate} />}

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

function GoalCard({ goal }: { goal: NonNullable<MonitoringData["goal"]> }) {
  return (
    <div className="card card--accent">
      <div className="row row--between">
        <h3>🎯 {goal.title}</h3>
        {goal.days_remaining !== null && (
          <span className={`badge ${goal.days_remaining < 0 ? "badge--warn" : "badge--accent"}`}>
            {goal.days_remaining < 0
              ? `${Math.abs(goal.days_remaining)} dni po terminie`
              : `${goal.days_remaining} dni do celu`}
          </span>
        )}
      </div>
      {goal.target_date && <small>Termin: {plDate(goal.target_date)}</small>}
    </div>
  );
}

function AdherenceBar({ label, bucket }: { label: string; bucket: MonitoringData["adherence"][string] }) {
  const pct = bucket.pct ?? 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="row row--between">
        <b style={{ fontSize: "0.9rem" }}>{label}</b>
        <small>{bucket.done}/{bucket.total}{bucket.pct !== null && ` · ${bucket.pct}%`}</small>
      </div>
      <div style={{ background: "var(--bg-raised)", borderRadius: 999, height: 8, overflow: "hidden", marginTop: 4 }}>
        <div style={{ width: `${Math.min(100, pct)}%`, background: "var(--accent)", height: "100%" }} />
      </div>
    </div>
  );
}

function NutritionLogCard({ target, series, userId, onSaved }: {
  target: number | null;
  series: { date: string; value: number }[];
  userId: string;
  onSaved: () => void;
}) {
  const [kcal, setKcal] = useState("");
  const [waterL, setWaterL] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post(`/api/clients/${userId}/nutrition-log`, {
        logged_on: todayIso(),
        kcal: kcal ? Number(kcal) : null,
        water_l: waterL ? Number(waterL) : null,
      });
      setKcal("");
      setWaterL("");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="row row--between">
        <h3>Dziennik kaloryczny</h3>
        {target !== null && <span className="badge">cel: {target} kcal</span>}
      </div>
      <form onSubmit={save}>
        <div className="field-row">
          <div>
            <label>Dzisiaj — kcal</label>
            <input type="number" min="0" value={kcal} onChange={(e) => setKcal(e.target.value)} />
          </div>
          <div>
            <label>Woda (l)</label>
            <input type="number" step="0.1" min="0" value={waterL}
              onChange={(e) => setWaterL(e.target.value)} />
          </div>
        </div>
        <ErrorBox error={error} />
        <div style={{ marginTop: 8 }}>
          <button className="btn btn--ghost btn--small" disabled={busy || (!kcal && !waterL)}>
            Zapisz dzisiejszy wpis
          </button>
        </div>
      </form>
      {series.length >= 2 && (
        <div style={{ marginTop: 10 }}>
          <Sparkline unit="kcal" points={series.map((p) => ({ x: plDate(p.date), y: p.value }))} />
        </div>
      )}
    </div>
  );
}

function ObservationsCard({ userId, onSaved }: {
  userId: string;
  onSaved: () => void;
}) {
  const [observations, setObservations] = useState<ObservationRow[] | null>(null);
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [category, setCategory] = useState("SAMOPOCZUCIE");
  const [severity, setSeverity] = useState("INFO");
  const [scheduleItemId, setScheduleItemId] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFull = () => {
    api.get<{ observations: ObservationRow[] }>(`/api/clients/${userId}/observations`)
      .then((d) => setObservations(d.observations))
      .catch(() => undefined);
  };
  useEffect(() => {
    loadFull();
    api.get<{ items: ScheduleItem[] }>(`/api/clients/${userId}/schedule`)
      .then((d) => setItems(d.items))
      .catch(() => undefined);
  }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/clients/${userId}/observations`, {
        occurred_on: todayIso(),
        schedule_item_id: scheduleItemId || null,
        category, severity, text,
      });
      setText("");
      setSeverity("INFO");
      setScheduleItemId("");
      loadFull();
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>Dziennik obserwacji</h3>
      <p className="dim" style={{ fontSize: "0.85rem", marginTop: -4 }}>
        Zapisuj samopoczucie lub reakcje (np. po suplemencie czy posiłku).
        To nie jest diagnoza — wpisy oznaczone jako niepokojące trafiają do
        przeglądu trenera, który zdecyduje o dalszych krokach.
      </p>
      <form onSubmit={submit}>
        <div className="field-row">
          <div>
            <label>Kategoria</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {Object.entries(OBSERVATION_CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label>Waga zgłoszenia</label>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="INFO">Informacja</option>
              <option value="NIEPOKOJACE">Niepokojące — proszę o uwagę</option>
            </select>
          </div>
        </div>
        {items.length > 0 && (
          <>
            <label>Powiązane z elementem harmonogramu (opcjonalnie)</label>
            <select value={scheduleItemId} onChange={(e) => setScheduleItemId(e.target.value)}>
              <option value="">— brak —</option>
              {items.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({CATEGORY_LABELS[i.category] ?? i.category})
                </option>
              ))}
            </select>
          </>
        )}
        <label>Opis</label>
        <textarea required value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Co zaobserwowałeś/aś?" />
        <ErrorBox error={error} />
        <div style={{ marginTop: 8 }}>
          <button className="btn btn--ghost btn--small" disabled={busy || !text.trim()}>
            Zapisz obserwację
          </button>
        </div>
      </form>
      {observations === null && <p className="dim">Wczytywanie…</p>}
      {observations && observations.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {observations.map((o) => (
            <div className="exercise" key={o.id}>
              <div>
                <b>{OBSERVATION_CATEGORY_LABELS[o.category] ?? o.category}</b>
                {o.schedule_item_name && <span className="meta"> · {o.schedule_item_name}</span>}
                <div className="meta">{o.text}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span className={`badge ${o.severity === "NIEPOKOJACE" ? "badge--danger" : ""}`}>
                  {SEVERITY_LABELS[o.severity] ?? o.severity}
                </span>
                <div className="meta">{plDate(o.occurred_on)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

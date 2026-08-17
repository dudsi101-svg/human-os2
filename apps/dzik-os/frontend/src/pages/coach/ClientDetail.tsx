import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, plDate, plDateTime, WEEKDAYS } from "../../api";
import { AuthImage, ErrorBox, SectionLabel, Sparkline, Spinner, TopBar } from "../../components";
import {
  CATEGORY_LABELS,
  CheckinData,
  GoalRow,
  KIND_LABELS,
  MeasurementRow,
  MonitoringData,
  NutritionVersion,
  OBSERVATION_CATEGORY_LABELS,
  PAYMENT_LABELS,
  PaymentScheduleRow,
  PlanVersion,
  ProfileFieldRow,
  ReceiptRow,
  ScheduleItem,
  SEVERITY_LABELS,
  TrainingPlan,
  WELLBEING_LABELS,
  WorkoutRow,
} from "../../types";
import PlanEditor from "./PlanEditor";

type Tab = "profil" | "plan" | "dieta" | "harmonogram" | "raporty" | "pomiary"
  | "monitoring" | "platnosci" | "historia";

const TABS: [Tab, string][] = [
  ["profil", "Profil"], ["plan", "Plan"], ["dieta", "Dieta"],
  ["harmonogram", "Harmonogram"], ["raporty", "Raporty"], ["pomiary", "Pomiary"],
  ["monitoring", "Monitoring"], ["platnosci", "Płatności"], ["historia", "Historia"],
];

interface NutritionPlanRow {
  id: string;
  title: string;
  current_version_no: number;
  current_version: NutritionVersion | null;
}

export default function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const [tab, setTab] = useState<Tab>("profil");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [noAccess, setNoAccess] = useState(false);

  useEffect(() => {
    api.get<{ display_name: string }>(`/api/coach/clients/${clientId}/overview`)
      .then((d) => setName(d.display_name))
      .catch((e) => {
        if (e.status === 404) setNoAccess(true);
        else setError(e.message);
      });
  }, [clientId]);

  if (noAccess) {
    return (
      <div className="page">
        <TopBar title="Brak dostępu" />
        <p className="alert alert--error">
          Nie masz dostępu do danych tego klienta (brak aktywnej współpracy
          lub klient cofnął zgodę na przetwarzanie danych).
        </p>
        <Link to="/trener">← Wróć do listy</Link>
      </div>
    );
  }

  return (
    <div className="page page--wide">
      <TopBar title={name || "Klient"}
        right={<Link className="btn btn--ghost btn--small" to="/trener">← Lista</Link>} />
      <ErrorBox error={error} />
      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "profil" && <ProfileTab clientId={clientId!} />}
      {tab === "plan" && <PlanTab clientId={clientId!} />}
      {tab === "dieta" && <NutritionTab clientId={clientId!} />}
      {tab === "harmonogram" && <ScheduleTab clientId={clientId!} />}
      {tab === "raporty" && <CheckinsTab clientId={clientId!} />}
      {tab === "pomiary" && <MeasurementsTab clientId={clientId!} />}
      {tab === "monitoring" && <MonitoringTab clientId={clientId!} />}
      {tab === "platnosci" && <PaymentsTab clientId={clientId!} />}
      {tab === "historia" && <HistoryTab clientId={clientId!} />}
    </div>
  );
}

function ProfileTab({ clientId }: { clientId: string }) {
  const [fields, setFields] = useState<ProfileFieldRow[] | null>(null);
  const [goals, setGoals] = useState<GoalRow[]>([]);
  const [goalTitle, setGoalTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get<{ fields: ProfileFieldRow[] }>(`/api/clients/${clientId}/profile`)
      .then((d) => setFields(d.fields)).catch((e) => setError(e.message));
    api.get<{ goals: GoalRow[] }>(`/api/clients/${clientId}/goals`)
      .then((d) => setGoals(d.goals)).catch(() => undefined);
  }, [clientId]);
  useEffect(load, [load]);

  async function addGoal(e: FormEvent) {
    e.preventDefault();
    await api.post(`/api/clients/${clientId}/goals`, { title: goalTitle, kind: "SECONDARY" });
    setGoalTitle("");
    load();
  }

  if (error) return <ErrorBox error={error} />;
  if (!fields) return <Spinner />;
  return (
    <>
      <div className="card">
        <h3>Profil (z proweniencją pól)</h3>
        <table className="simple">
          <thead><tr><th>Pole</th><th>Wartość</th><th>Źródło</th><th>Wersja</th></tr></thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.field_key}>
                <td>{f.field_key}</td>
                <td>{f.value}</td>
                <td><small>{f.source === "CLIENT_DECLARED" ? "klient" : "trener"} · {plDate(f.created_at)}</small></td>
                <td>v{f.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Cele</h3>
        {goals.map((g) => (
          <div className="exercise" key={g.id}>
            <div><b>{g.title}</b>{g.target_date && <div className="meta">do {plDate(g.target_date)}</div>}</div>
            <span className="badge">{g.kind === "MAIN" ? "główny" : "dodatkowy"} · {g.status}</span>
          </div>
        ))}
        <form className="row" style={{ marginTop: 8 }} onSubmit={addGoal}>
          <input className="grow" placeholder="Nowy cel…" required value={goalTitle}
            onChange={(e) => setGoalTitle(e.target.value)} />
          <button className="btn btn--small">Dodaj</button>
        </form>
      </div>
    </>
  );
}

function PlanTab({ clientId }: { clientId: string }) {
  const [plans, setPlans] = useState<TrainingPlan[] | null>(null);
  const [versions, setVersions] = useState<PlanVersion[] | null>(null);
  const [workouts, setWorkouts] = useState<WorkoutRow[]>([]);
  const [editing, setEditing] = useState<"new" | "version" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const plan = plans?.find((p) => p.status === "ACTIVE" && !p.is_template) ?? null;

  const load = useCallback(() => {
    setEditing(null);
    setVersions(null);
    api.get<{ plans: TrainingPlan[] }>(`/api/clients/${clientId}/plans`)
      .then((d) => setPlans(d.plans)).catch((e) => setError(e.message));
    api.get<{ workouts: WorkoutRow[] }>(`/api/clients/${clientId}/workouts`)
      .then((d) => setWorkouts(d.workouts)).catch(() => undefined);
  }, [clientId]);
  useEffect(load, [load]);

  useEffect(() => {
    if (plan && !versions) {
      api.get<{ versions: PlanVersion[] }>(`/api/plans/${plan.id}/versions`)
        .then((d) => setVersions(d.versions)).catch(() => undefined);
    }
  }, [plan, versions]);

  if (error) return <ErrorBox error={error} />;
  if (!plans) return <Spinner />;

  return (
    <>
      {editing === "new" && (
        <PlanEditor clientId={clientId} existingPlan={null} onSaved={load}
          onCancel={() => setEditing(null)} />
      )}
      {editing === "version" && plan && (
        <PlanEditor clientId={clientId} existingPlan={plan}
          initialDays={plan.current_version?.content.days} onSaved={load}
          onCancel={() => setEditing(null)} />
      )}
      {!editing && (
        <div className="row" style={{ marginBottom: 10 }}>
          <button className="btn btn--small" onClick={() => setEditing("new")}>+ Nowy plan</button>
          {plan && (
            <button className="btn btn--ghost btn--small" onClick={() => setEditing("version")}>
              Nowa wersja aktualnego planu
            </button>
          )}
        </div>
      )}
      {plan?.current_version && (
        <div className="card">
          <div className="row row--between">
            <h3>{plan.title}</h3>
            <span className="badge badge--accent">v{plan.current_version_no}</span>
          </div>
          <small>Powód: {plan.current_version.reason}</small>
          {plan.current_version.content.days.map((d, i) => (
            <div key={i} style={{ marginTop: 8 }}>
              <b>{d.name}</b> {d.weekday && <span className="badge">{WEEKDAYS[d.weekday - 1]}</span>}
              {d.exercises.map((ex, j) => (
                <div className="exercise" key={j}>
                  <div>{ex.name}</div>
                  <div className="meta">
                    {[ex.sets && `${ex.sets}×${ex.reps ?? "?"}`, ex.weight, ex.rest].filter(Boolean).join(" · ")}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      {versions && versions.length > 1 && (
        <div className="card">
          <h3>Historia wersji</h3>
          <table className="simple">
            <thead><tr><th>Wersja</th><th>Data</th><th>Powód</th></tr></thead>
            <tbody>
              {versions.slice().reverse().map((v) => (
                <tr key={v.id}><td>v{v.version_no}</td><td>{plDate(v.created_at)}</td><td>{v.reason}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {workouts.length > 0 && (
        <div className="card">
          <h3>Wykonane treningi</h3>
          {workouts.slice(0, 12).map((w) => (
            <div className="exercise" key={w.id}>
              <div>
                <b>{plDate(w.performed_on)}</b>
                {w.pain_flag && <span className="badge badge--danger" style={{ marginLeft: 6 }}>ból: {w.pain_note}</span>}
                {w.comment && <div className="meta">{w.comment}</div>}
                {w.entries.filter((e) => e.result).map((e, i) => (
                  <div className="meta" key={i}>{e.exercise_name}: {e.result}</div>
                ))}
              </div>
              <div className="meta">{w.status}</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function NutritionTab({ clientId }: { clientId: string }) {
  const [plans, setPlans] = useState<NutritionPlanRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: "", reason: "", kcal: "", protein_g: "", fat_g: "", carbs_g: "", zasady: "", meals: "" });

  const plan = plans?.[0] ?? null;
  const load = useCallback(() => {
    setEditing(false);
    api.get<{ plans: NutritionPlanRow[] }>(`/api/clients/${clientId}/nutrition`)
      .then((d) => setPlans(d.plans)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  async function save(e: FormEvent) {
    e.preventDefault();
    const version = {
      reason: form.reason,
      kcal: form.kcal ? Number(form.kcal) : null,
      protein_g: form.protein_g ? Number(form.protein_g) : null,
      fat_g: form.fat_g ? Number(form.fat_g) : null,
      carbs_g: form.carbs_g ? Number(form.carbs_g) : null,
      sections: form.zasady ? [{ title: "Zalecenia", body: form.zasady }] : [],
      meals: form.meals
        ? form.meals.split("\n").filter(Boolean).map((line) => {
            const [name, ...rest] = line.split(":");
            return { name: name.trim(), description: rest.join(":").trim() };
          })
        : [],
    };
    try {
      if (plan) {
        await api.post(`/api/nutrition/${plan.id}/versions`, version);
      } else {
        await api.post("/api/nutrition", { client_id: clientId, title: form.title, version });
      }
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error) return <ErrorBox error={error} />;
  if (!plans) return <Spinner />;
  const v = plan?.current_version;

  return (
    <>
      {!editing && (
        <button className="btn btn--small" style={{ marginBottom: 10 }}
          onClick={() => {
            setForm({
              title: plan?.title ?? "", reason: "",
              kcal: String(v?.content.kcal ?? ""), protein_g: String(v?.content.protein_g ?? ""),
              fat_g: String(v?.content.fat_g ?? ""), carbs_g: String(v?.content.carbs_g ?? ""),
              zasady: v?.content.sections.map((s) => s.body).join("\n") ?? "",
              meals: v?.content.meals.map((m) => `${m.name}: ${m.description ?? ""}`).join("\n") ?? "",
            });
            setEditing(true);
          }}>
          {plan ? "Nowa wersja diety" : "+ Nowa dieta"}
        </button>
      )}
      {editing && (
        <form className="card card--accent" onSubmit={save}>
          {!plan && (
            <>
              <label>Nazwa planu żywieniowego</label>
              <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </>
          )}
          <label>Powód zmiany</label>
          <input required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <div className="field-row">
            <div><label>kcal</label><input type="number" value={form.kcal} onChange={(e) => setForm({ ...form, kcal: e.target.value })} /></div>
            <div><label>Białko (g)</label><input type="number" value={form.protein_g} onChange={(e) => setForm({ ...form, protein_g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label>Tłuszcze (g)</label><input type="number" value={form.fat_g} onChange={(e) => setForm({ ...form, fat_g: e.target.value })} /></div>
            <div><label>Węglowodany (g)</label><input type="number" value={form.carbs_g} onChange={(e) => setForm({ ...form, carbs_g: e.target.value })} /></div>
          </div>
          <label>Zalecenia tekstowe</label>
          <textarea value={form.zasady} onChange={(e) => setForm({ ...form, zasady: e.target.value })} />
          <label>Posiłki (jeden na linię: „Nazwa: opis")</label>
          <textarea value={form.meals} onChange={(e) => setForm({ ...form, meals: e.target.value })} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn">Zapisz</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(false)}>Anuluj</button>
          </div>
        </form>
      )}
      {v && (
        <div className="card">
          <div className="row row--between">
            <h3>{plan!.title}</h3>
            <span className="badge badge--accent">v{plan!.current_version_no}</span>
          </div>
          <small>Powód: {v.reason}</small>
          <div className="stat-grid" style={{ marginTop: 8 }}>
            <div className="stat"><b>{v.content.kcal ?? "—"}</b><span>kcal</span></div>
            <div className="stat"><b>{v.content.protein_g ?? "—"} g</b><span>białko</span></div>
            <div className="stat"><b>{v.content.carbs_g ?? "—"} g</b><span>węgle</span></div>
            <div className="stat"><b>{v.content.fat_g ?? "—"} g</b><span>tłuszcze</span></div>
          </div>
          {v.content.meals.map((m, i) => (
            <div className="exercise" key={i}>
              <div><b>{m.name}</b><div className="meta">{m.description}</div></div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function ScheduleTab({ clientId }: { clientId: string }) {
  const [items, setItems] = useState<ScheduleItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", category: "TRENING", time_of_day: "", days: [] as number[], instruction: "", author_note: "" });

  const load = useCallback(() => {
    api.get<{ items: ScheduleItem[] }>(`/api/clients/${clientId}/schedule`)
      .then((d) => setItems(d.items)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/schedule", {
        client_id: clientId, name: form.name, category: form.category,
        time_of_day: form.time_of_day || null,
        days_of_week: (form.days.length ? form.days : [1, 2, 3, 4, 5, 6, 7]).join(","),
        instruction: form.instruction || null,
        author_note: form.author_note || null,
      });
      setForm({ name: "", category: "TRENING", time_of_day: "", days: [], instruction: "", author_note: "" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function setStatus(id: string, status: string) {
    await api.post(`/api/schedule/${id}/status?status=${status}`);
    load();
  }

  if (error) return <ErrorBox error={error} />;
  if (!items) return <Spinner />;
  return (
    <>
      <form className="card" onSubmit={add}>
        <h3>Dodaj element harmonogramu</h3>
        <div className="field-row">
          <div>
            <label>Nazwa</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label>Kategoria</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
        </div>
        <div className="field-row">
          <div>
            <label>Pora (HH:MM)</label>
            <input value={form.time_of_day} placeholder="np. 08:00" pattern="\d{2}:\d{2}"
              onChange={(e) => setForm({ ...form, time_of_day: e.target.value })} />
          </div>
          <div>
            <label>Dni tygodnia</label>
            <div className="row" style={{ flexWrap: "wrap", gap: 4 }}>
              {WEEKDAYS.map((w, i) => (
                <button type="button" key={i}
                  className={`btn btn--ghost btn--small ${form.days.includes(i + 1) ? "active" : ""}`}
                  style={form.days.includes(i + 1) ? { background: "var(--accent)", color: "var(--accent-ink)" } : {}}
                  onClick={() => setForm({
                    ...form,
                    days: form.days.includes(i + 1)
                      ? form.days.filter((d) => d !== i + 1)
                      : [...form.days, i + 1],
                  })}>
                  {w}
                </button>
              ))}
            </div>
          </div>
        </div>
        <label>Instrukcja</label>
        <input value={form.instruction} onChange={(e) => setForm({ ...form, instruction: e.target.value })} />
        {form.category === "SUPLEMENT" && (
          <>
            <label>Autor zalecenia / źródło (wymagane dla suplementów)</label>
            <input required value={form.author_note}
              placeholder="np. dawka wpisana na prośbę klienta; zalecenie lekarza"
              onChange={(e) => setForm({ ...form, author_note: e.target.value })} />
            <small className="dim">
              System tylko przypomina o planie wprowadzonym przez człowieka —
              nie dobiera i nie zmienia dawkowania.
            </small>
          </>
        )}
        <div style={{ marginTop: 10 }}><button className="btn btn--small">Dodaj</button></div>
      </form>
      {items.map((s) => (
        <div className="card" key={s.id}>
          <div className="row row--between">
            <div>
              <b>{s.name}</b> <span className="badge">{CATEGORY_LABELS[s.category] ?? s.category}</span>
              {s.status !== "ACTIVE" && <span className="badge badge--warn" style={{ marginLeft: 4 }}>
                {s.status === "PAUSED" ? "wstrzymane" : "zakończone"}</span>}
              <div className="meta dim" style={{ fontSize: "0.8rem" }}>
                {s.days_of_week.split(",").map((d) => WEEKDAYS[Number(d) - 1]).join(", ")}
                {s.time_of_day && ` · ${s.time_of_day}`}
                {s.instruction && ` · ${s.instruction}`}
              </div>
              {s.author_note && <small className="dim">ℹ️ {s.author_note}</small>}
            </div>
            <div className="row">
              {s.status === "ACTIVE" ? (
                <button className="btn btn--ghost btn--small" onClick={() => setStatus(s.id, "PAUSED")}>⏸</button>
              ) : (
                <button className="btn btn--ghost btn--small" onClick={() => setStatus(s.id, "ACTIVE")}>▶</button>
              )}
              <button className="btn btn--danger btn--small" onClick={() => setStatus(s.id, "ENDED")}>Zakończ</button>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

const SCALE_LABELS: [string, string][] = [
  ["energy", "energia"], ["sleep", "sen"], ["hunger", "głód"],
  ["stress", "stres"], ["recovery", "regeneracja"], ["diet_adherence", "dieta"],
];

function CheckinsTab({ clientId }: { clientId: string }) {
  const [checkins, setCheckins] = useState<CheckinData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [ai, setAi] = useState<Record<string, { loading: boolean; summary?: string;
    draft?: string; flags?: string[]; reason?: string }>>({});

  const load = useCallback(() => {
    api.get<{ checkins: CheckinData[] }>(`/api/clients/${clientId}/checkins`)
      .then((d) => setCheckins(d.checkins)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  async function review(id: string) {
    await api.post(`/api/checkins/${id}/review`, {
      coach_response: responses[id], rating: ratings[id] || null,
    });
    load();
  }

  async function requestAiSummary(id: string) {
    setAi({ ...ai, [id]: { loading: true } });
    try {
      const r = await api.post<{ available: boolean; summary?: string;
        draft_response?: string; flags?: string[]; reason?: string }>(
        `/api/checkins/${id}/ai-summary`
      );
      setAi({ ...ai, [id]: {
        loading: false, summary: r.summary, draft: r.draft_response,
        flags: r.flags, reason: r.reason,
      } });
    } catch (e) {
      setAi({ ...ai, [id]: { loading: false, reason: (e as Error).message } });
    }
  }

  if (error) return <ErrorBox error={error} />;
  if (!checkins) return <Spinner />;
  return (
    <>
      {checkins.length === 0 && <p className="dim">Brak raportów.</p>}
      {checkins.map((c) => {
        const state = ai[c.id];
        return (
          <div className="card" key={c.id}>
            <div className="row row--between">
              <h3 style={{ margin: 0 }}>Tydzień {plDate(c.week_start)}</h3>
              <span className={`badge ${c.status === "REVIEWED" ? "badge--ok" : "badge--warn"}`}>
                {c.status === "REVIEWED" ? "oceniony" : `do oceny${c.revision > 1 ? ` · rew. ${c.revision}` : ""}`}
              </span>
            </div>

            <SectionLabel n={1} title="Ciało i trening" />
            <div className="stat-grid">
              <div className="stat"><b>{String(c.payload.weight_kg ?? "—")}</b><span>masa (kg)</span></div>
              <div className="stat"><b>{String(c.payload.trainings_done ?? "—")}</b><span>treningi</span></div>
            </div>

            <SectionLabel n={2} title="Samopoczucie" />
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {SCALE_LABELS.filter(([k]) => c.payload[k] != null).map(([k, l]) => (
                <span className="badge" key={k}>{l} {String(c.payload[k])}/5</span>
              ))}
            </div>

            {Boolean(c.payload.pain_note || c.payload.comment || c.payload.questions) && (
              <>
                <SectionLabel n={3} title="Ból, komentarz, pytania" />
                {typeof c.payload.pain_note === "string" && c.payload.pain_note && (
                  <p className="alert alert--error">⚠️ Ból/uraz: {c.payload.pain_note}</p>
                )}
                {typeof c.payload.comment === "string" && c.payload.comment && (
                  <p><b>Komentarz:</b> {c.payload.comment}</p>
                )}
                {typeof c.payload.questions === "string" && c.payload.questions && (
                  <p><b>Pytania:</b> {c.payload.questions}</p>
                )}
              </>
            )}

            {c.photo_ids.length > 0 && (
              <div className="photo-grid" style={{ margin: "8px 0" }}>
                {c.photo_ids.map((fid) => <AuthImage key={fid} fileId={fid} alt="zdjęcie raportu" />)}
              </div>
            )}

            {c.coach_response ? (
              <div className="alert alert--info">
                <b>Twoja odpowiedź:</b> {c.coach_response}
                {c.rating != null && (
                  <div style={{ marginTop: 4 }}>
                    <span className="badge badge--accent">Ocena raportu: {c.rating}/5</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ marginTop: 8 }}>
                {!state && (
                  <button type="button" className="btn btn--ghost btn--small"
                    onClick={() => requestAiSummary(c.id)}>
                    ✨ Podsumowanie AI (propozycja)
                  </button>
                )}
                {state?.loading && <p className="dim">Generowanie propozycji…</p>}
                {state && !state.loading && state.reason && (
                  <p className="alert alert--info" style={{ fontSize: "0.85rem" }}>{state.reason}</p>
                )}
                {state?.summary && (
                  <div className="alert alert--info" style={{ marginBottom: 8 }}>
                    <b>Propozycja AI — streszczenie:</b> {state.summary}
                    {state.flags && state.flags.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {state.flags.map((f) => (
                          <span className="badge badge--warn" key={f} style={{ marginRight: 4 }}>{f}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <textarea placeholder="Odpowiedź dla klienta…" value={responses[c.id] ?? ""}
                  onChange={(e) => setResponses({ ...responses, [c.id]: e.target.value })} />
                {state?.draft && (
                  <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
                    onClick={() => setResponses({ ...responses, [c.id]: state.draft! })}>
                    Wstaw szkic AI do edycji
                  </button>
                )}
                <div className="row row--between" style={{ marginTop: 8, alignItems: "center" }}>
                  <label style={{ margin: 0 }}>Ocena raportu (opcjonalnie)</label>
                  <div className="row" style={{ gap: 4 }}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button type="button" key={n}
                        className={`btn btn--ghost btn--small ${ratings[c.id] === n ? "active" : ""}`}
                        style={ratings[c.id] === n ? { background: "var(--accent)", color: "var(--accent-ink)" } : {}}
                        onClick={() => setRatings({ ...ratings, [c.id]: ratings[c.id] === n ? 0 : n })}>
                        {n}
                      </button>
                    ))}
                  </div>
                </div>
                <small className="dim">
                  Ocena dotyczy kompletności/jakości samego raportu — nie jest oceną osoby.
                </small>
                <div style={{ marginTop: 8 }}>
                  <button className="btn btn--small" disabled={!responses[c.id]?.trim()}
                    onClick={() => review(c.id)}>
                    Wyślij odpowiedź i oznacz jako oceniony
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

function MeasurementsTab({ clientId }: { clientId: string }) {
  const [rows, setRows] = useState<MeasurementRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ measurements: MeasurementRow[] }>(`/api/clients/${clientId}/measurements`)
      .then((d) => setRows(d.measurements)).catch((e) => setError(e.message));
  }, [clientId]);
  if (error) return <ErrorBox error={error} />;
  if (!rows) return <Spinner />;
  const kinds = Array.from(new Set(rows.map((r) => r.kind)));
  return (
    <>
      {kinds.length === 0 && <p className="dim">Brak pomiarów.</p>}
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
    </>
  );
}

function PaymentsTab({ clientId }: { clientId: string }) {
  const [schedules, setSchedules] = useState<PaymentScheduleRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ package_name: "", amount: "", first_due_date: "", period: "MONTHLY" });

  const load = useCallback(() => {
    api.get<{ schedules: PaymentScheduleRow[] }>(`/api/clients/${clientId}/payments`)
      .then((d) => setSchedules(d.schedules)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/payments/schedules", {
        client_id: clientId, package_name: form.package_name,
        amount_cents: Math.round(Number(form.amount.replace(",", ".")) * 100),
        period: form.period, first_due_date: form.first_due_date,
      });
      setForm({ package_name: "", amount: "", first_due_date: "", period: "MONTHLY" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function setStatus(recordId: string, status: string) {
    await api.post(`/api/payments/records/${recordId}/status`, { status });
    load();
  }

  async function addRecord(scheduleId: string) {
    const due = prompt("Termin kolejnej płatności (RRRR-MM-DD):");
    if (!due) return;
    await api.post(`/api/payments/schedules/${scheduleId}/records?due_date=${due}`);
    load();
  }

  if (error) return <ErrorBox error={error} />;
  if (!schedules) return <Spinner />;
  return (
    <>
      <form className="card" onSubmit={create}>
        <h3>Nowy pakiet płatności</h3>
        <div className="field-row">
          <div><label>Nazwa pakietu</label>
            <input required value={form.package_name}
              onChange={(e) => setForm({ ...form, package_name: e.target.value })} /></div>
          <div><label>Kwota (PLN)</label>
            <input required type="text" inputMode="decimal" value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
        </div>
        <div className="field-row">
          <div><label>Pierwszy termin</label>
            <input required type="date" value={form.first_due_date}
              onChange={(e) => setForm({ ...form, first_due_date: e.target.value })} /></div>
          <div><label>Okres</label>
            <select value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })}>
              <option value="MONTHLY">miesięczny</option>
              <option value="WEEKLY">tygodniowy</option>
              <option value="ONE_OFF">jednorazowy</option>
            </select></div>
        </div>
        <div style={{ marginTop: 10 }}><button className="btn btn--small">Utwórz</button></div>
      </form>
      {schedules.map((s) => (
        <div className="card" key={s.schedule_id}>
          <div className="row row--between">
            <h3>{s.package_name}</h3>
            <div className="row">
              <b>{money(s.amount_cents, s.currency)}</b>
              <button className="btn btn--ghost btn--small" onClick={() => addRecord(s.schedule_id)}>
                + termin
              </button>
            </div>
          </div>
          <table className="simple">
            <thead><tr><th>Termin</th><th>Status</th><th>Akcje</th></tr></thead>
            <tbody>
              {s.records.map((r) => (
                <tr key={r.id}>
                  <td>{plDate(r.due_date)}</td>
                  <td><span className={`badge ${r.status === "PAID" ? "badge--ok" : r.status === "CANCELLED" ? "" : "badge--warn"}`}>
                    {PAYMENT_LABELS[r.status]}</span></td>
                  <td>
                    {r.status !== "PAID" && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => setStatus(r.id, "PAID")}>Opłacona</button>
                    )}{" "}
                    {r.status === "PENDING" && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => setStatus(r.id, "CANCELLED")}>Anuluj</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

function MonitoringTab({ clientId }: { clientId: string }) {
  const [data, setData] = useState<MonitoringData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<MonitoringData>(`/api/clients/${clientId}/monitoring`)
      .then(setData).catch((e) => setError(e.message));
  }, [clientId]);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Spinner />;

  return (
    <>
      {data.goal && (
        <div className="card card--accent">
          <div className="row row--between">
            <h3>🎯 {data.goal.title}</h3>
            {data.goal.days_remaining !== null && (
              <span className="badge badge--accent">
                {data.goal.days_remaining < 0
                  ? `${Math.abs(data.goal.days_remaining)} dni po terminie`
                  : `${data.goal.days_remaining} dni do celu`}
              </span>
            )}
          </div>
          {data.goal.target_date && <small>Termin: {plDate(data.goal.target_date)}</small>}
        </div>
      )}

      {Object.keys(data.adherence).length > 0 && (
        <div className="card">
          <h3>Realizacja harmonogramu ({data.period_days} dni)</h3>
          {Object.entries(data.adherence).map(([cat, b]) => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div className="row row--between">
                <b style={{ fontSize: "0.9rem" }}>{CATEGORY_LABELS[cat] ?? cat}</b>
                <small>{b.done}/{b.total}{b.pct !== null && ` · ${b.pct}%`}</small>
              </div>
              <div style={{ background: "var(--bg-raised)", borderRadius: 999, height: 8, overflow: "hidden", marginTop: 4 }}>
                <div style={{ width: `${Math.min(100, b.pct ?? 0)}%`, background: "var(--accent)", height: "100%" }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {Object.keys(data.wellbeing_series).length > 0 && (
        <div className="card">
          <h3>Samopoczucie</h3>
          {Object.entries(data.wellbeing_series).map(([key, points]) => (
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

      {data.nutrition.log_series.length >= 2 && (
        <div className="card">
          <div className="row row--between">
            <h3>Dziennik kaloryczny</h3>
            {data.nutrition.target_kcal !== null && (
              <span className="badge">cel: {data.nutrition.target_kcal} kcal</span>
            )}
          </div>
          <Sparkline unit="kcal"
            points={data.nutrition.log_series.map((p) => ({ x: plDate(p.date), y: p.value }))} />
        </div>
      )}

      <div className="card">
        <h3>Obserwacje klienta</h3>
        <p className="dim" style={{ fontSize: "0.85rem", marginTop: -4 }}>
          Deklaracje klienta do przeglądu — nie są diagnozą. Wpisy oznaczone
          jako niepokojące wymagają Twojej uwagi.
        </p>
        {data.observations.length === 0 && <small>Brak obserwacji w tym okresie.</small>}
        {data.observations.map((o) => (
          <div className="exercise" key={o.id}>
            <div>
              <b>{OBSERVATION_CATEGORY_LABELS[o.category] ?? o.category}</b>
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
    </>
  );
}

function HistoryTab({ clientId }: { clientId: string }) {
  const [receipts, setReceipts] = useState<ReceiptRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ receipts: ReceiptRow[] }>(`/api/coach/clients/${clientId}/history`)
      .then((d) => setReceipts(d.receipts)).catch((e) => setError(e.message));
  }, [clientId]);
  if (error) return <ErrorBox error={error} />;
  if (!receipts) return <Spinner />;
  return (
    <div className="card">
      <h3>Historia zmian (pokwitowania z łańcucha audytu Human OS)</h3>
      {receipts.length === 0 && <small>Brak zdarzeń.</small>}
      {receipts.map((r) => (
        <div className="exercise" key={r.id}>
          <div>
            <b>{r.summary}</b>
            <div className="meta">
              {r.action} · {plDateTime(r.created_at)} · hash {r.event_hash.slice(0, 12)}…
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

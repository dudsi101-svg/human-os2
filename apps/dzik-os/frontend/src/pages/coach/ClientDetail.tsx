import { FormEvent, Fragment, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, isCancel, money } from "../../api";
import { WEEKDAYS, plDate, plDateTime } from "../../dates";
import {
  AuthImage,
  dailySparkPoints,
  ErrorBox,
  Icon,
  PersonalRecordsCard,
  PhotoCompare,
  ProgressPhotoRow,
  SectionLabel,
  Sparkline,
  Spinner,
  StrengthChartsCard,
  TabPanel,
  Tabs,
  TopBar,
  wellbeingSparkPoints,
} from "../../components";
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
  PAYMENT_TX_LABELS,
  paymentBadgeClass,
  PaymentHistory,
  PaymentRecordRow,
  PaymentScheduleRow,
  PlanVersion,
  POSE_LABELS,
  ProfileFieldRow,
  ReceiptRow,
  ScheduleItem,
  SEVERITY_LABELS,
  SupplementEntry,
  TrainingPlan,
  WELLBEING_LABELS,
  WorkoutRow,
} from "../../types";
import {
  CONFIDENCE_LABELS,
  fieldLabel,
  OnboardingState,
  ORIGIN_LABELS,
  pendingConfirmation,
  summaryModeNote,
} from "../../onboardingUtils";
import PlanEditor from "./PlanEditor";
import OcrCapture from "../../OcrCapture";
import { appendText } from "../../ocrUtils";

type Tab = "profil" | "rozmowa" | "plan" | "dieta" | "harmonogram" | "raporty"
  | "pomiary" | "monitoring" | "platnosci" | "historia";

const TABS: [Tab, string][] = [
  ["profil", "Profil"], ["rozmowa", "Rozmowa startowa"], ["plan", "Plan"],
  ["dieta", "Dieta"], ["harmonogram", "Harmonogram"], ["raporty", "Raporty"],
  ["pomiary", "Pomiary"], ["monitoring", "Monitoring"], ["platnosci", "Płatności"],
  ["historia", "Historia"],
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
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Zmiana klienta anuluje poprzednie pobranie — spóźniona odpowiedź nie
    // nadpisze nagłówka danymi innej osoby.
    const ac = new AbortController();
    setError(null);
    setNoAccess(false);
    api.get<{ display_name: string }>(
      `/api/coach/clients/${clientId}/overview`, { signal: ac.signal }
    )
      .then((d) => setName(d.display_name))
      .catch((e) => {
        if (isCancel(e)) return;
        if (e.status === 404) setNoAccess(true);
        else setError(e.message);
      });
    return () => ac.abort();
  }, [clientId, attempt]);

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
      <ErrorBox error={error} onRetry={() => setAttempt((a) => a + 1)} />
      <Tabs tabs={TABS} value={tab} onChange={setTab} label="Sekcje karty klienta" />
      <TabPanel id={tab}>
        {tab === "profil" && <ProfileTab clientId={clientId!} />}
        {tab === "rozmowa" && <OnboardingTab clientId={clientId!} />}
        {tab === "plan" && <PlanTab clientId={clientId!} />}
        {tab === "dieta" && <NutritionTab clientId={clientId!} />}
        {tab === "harmonogram" && <ScheduleTab clientId={clientId!} />}
        {tab === "raporty" && <CheckinsTab clientId={clientId!} />}
        {tab === "pomiary" && <MeasurementsTab clientId={clientId!} />}
        {tab === "monitoring" && <MonitoringTab clientId={clientId!} />}
        {tab === "platnosci" && <PaymentsTab clientId={clientId!} />}
        {tab === "historia" && <HistoryTab clientId={clientId!} />}
      </TabPanel>
    </div>
  );
}

function ProfileTab({ clientId }: { clientId: string }) {
  const [fields, setFields] = useState<ProfileFieldRow[] | null>(null);
  const [goals, setGoals] = useState<GoalRow[]>([]);
  const [goalTitle, setGoalTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<{ fields: ProfileFieldRow[] }>(`/api/clients/${clientId}/profile`)
      .then((d) => setFields(d.fields)).catch((e) => setError(e.message));
    api.get<{ goals: GoalRow[] }>(`/api/clients/${clientId}/goals`)
      .then((d) => setGoals(d.goals))
      .catch((e) => setError(`Nie udało się wczytać celów. ${e.message}`));
  }, [clientId]);
  useEffect(load, [load]);

  const [goalError, setGoalError] = useState<string | null>(null);

  async function addGoal(e: FormEvent) {
    e.preventDefault();
    setGoalError(null);
    try {
      await api.post(`/api/clients/${clientId}/goals`, { title: goalTitle, kind: "SECONDARY" });
      setGoalTitle("");
      load();
    } catch (err) {
      // Błąd zapisu celu pokazujemy PRZY formularzu (nie zamiast zakładki) —
      // wpisany tytuł zostaje nietknięty do ponowienia.
      setGoalError((err as Error).message);
    }
  }

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!fields) return <Spinner />;
  return (
    <>
      <div className="card">
        <h2>Profil (z proweniencją pól)</h2>
        <div className="table-wrap">
          <table className="simple table--cards">
            <thead><tr><th>Pole</th><th>Wartość</th><th>Źródło</th><th>Wersja</th></tr></thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.field_key}>
                  <td data-label="Pole">{f.field_key}</td>
                  <td data-label="Wartość">{f.value}</td>
                  <td data-label="Źródło"><small>{f.source === "CLIENT_DECLARED" ? "klient" : "trener"} · {plDate(f.created_at)}</small></td>
                  <td data-label="Wersja">v{f.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h2>Cele</h2>
        {goals.map((g) => (
          <div className="exercise" key={g.id}>
            <div><b>{g.title}</b>{g.target_date && <div className="meta">do {plDate(g.target_date)}</div>}</div>
            <span className="badge">{g.kind === "MAIN" ? "główny" : "dodatkowy"} · {g.status}</span>
          </div>
        ))}
        <ErrorBox error={goalError} />
        <form className="row" style={{ marginTop: 8 }} onSubmit={addGoal}>
          <input className="grow" placeholder="Nowy cel…" aria-label="Nowy cel" required value={goalTitle}
            onChange={(e) => setGoalTitle(e.target.value)} />
          <button className="btn btn--small">Dodaj</button>
        </form>
      </div>
    </>
  );
}

/** Rozmowa startowa oczami trenera: dane źródłowe (odpowiedzi klienta wraz
 * z historią poprawek), podsumowanie, poziom niepewności per pole i pola
 * wymagające potwierdzenia. Trener zatwierdza DOPIERO po kliencie — i
 * dopiero wtedy podsumowanie staje się podstawą planu. */
function OnboardingTab({ clientId }: { clientId: string }) {
  const [state, setState] = useState<OnboardingState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<OnboardingState>(`/api/clients/${clientId}/onboarding/review`)
      .then((d) => { setState(d); setConfirmed(new Set()); })
      .catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  async function approve() {
    setBusy(true);
    setNote(null);
    setError(null);
    try {
      const next = await api.post<OnboardingState>(
        `/api/clients/${clientId}/onboarding/coach-approve`,
        { confirmed_fields: [...confirmed] },
      );
      setState(next);
      setNote("Podsumowanie zatwierdzone jako podstawa planu.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !state) return <ErrorBox error={error} onRetry={load} />;
  if (!state) return <Spinner />;
  const session = state.session;
  if (!session) {
    return (
      <div className="card">
        <h2>Rozmowa startowa</h2>
        <p className="dim">
          Klient nie zaczął jeszcze rozmowy startowej. Może ją przeprowadzić
          w aplikacji („Porozmawiajmy” na ekranie Dzisiaj) albo wypełnić
          klasyczny formularz — obie drogi zapisują te same pola profilu.
        </p>
      </div>
    );
  }
  const summary = state.summary ?? [];
  const answers = state.answers ?? [];
  const pending = pendingConfirmation(summary).filter((r) => !confirmed.has(r.field_key));
  return (
    <>
      {session.safety_flag && (
        <div className="card" role="alert" style={{ borderColor: "var(--warn)" }}>
          <h2>Sygnał do konsultacji medycznej</h2>
          <p>
            W rozmowie pojawił się opis, którego ani trener, ani aplikacja
            nie ocenia. Klient dostał komunikat kierujący do lekarza.
            Wstrzymaj się z planem obciążającym tę okolicę do czasu jego
            konsultacji — poniżej zaznaczono, której odpowiedzi dotyczy.
          </p>
        </div>
      )}

      <div className="card">
        <h2>Status rozmowy</h2>
        <p className="dim">{summaryModeNote(session)}</p>
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          <span className="badge">{STATUS_LABELS[session.status] ?? session.status}</span>
          <span className="badge">
            {session.summary_mode === "AI_DRAFT" ? "podsumowanie: propozycja AI"
              : "podsumowanie: krok po kroku"}
          </span>
          {session.client_approved_at && (
            <span className="badge badge--ok">
              klient zatwierdził {plDateTime(session.client_approved_at)}
            </span>
          )}
          {session.coach_approved_at && (
            <span className="badge badge--ok">
              Ty zatwierdziłeś(-aś) {plDateTime(session.coach_approved_at)}
            </span>
          )}
        </div>
      </div>

      <div className="card">
        <h2>Podsumowanie i poziom niepewności</h2>
        {summary.length === 0 && (
          <p className="dim">Klient nie przygotował jeszcze podsumowania.</p>
        )}
        <div className="table-wrap">
          <table className="simple table--cards">
            <thead>
              <tr>
                <th>Pole</th><th>Wartość</th><th>Źródło</th>
                <th>Pewność</th><th>Potwierdzenie</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((item) => (
                <tr key={item.field_key}>
                  <td data-label="Pole">{fieldLabel(item.field_key)}</td>
                  <td data-label="Wartość">
                    {item.hidden
                      ? <span className="dim">ukryte — brak zgody na tę kategorię</span>
                      : item.value}
                  </td>
                  <td data-label="Źródło">
                    <small>{ORIGIN_LABELS[item.origin] ?? item.origin}</small>
                  </td>
                  <td data-label="Pewność">
                    <span className={item.confidence === "HIGH"
                      ? "badge badge--ok"
                      : item.confidence === "LOW" ? "badge badge--danger" : "badge badge--warn"}>
                      {CONFIDENCE_LABELS[item.confidence] ?? item.confidence}
                    </span>
                  </td>
                  <td data-label="Potwierdzenie">
                    {item.needs_confirmation ? (
                      item.coach_confirmed ? (
                        <span className="badge badge--ok">potwierdzone</span>
                      ) : (
                        <label className="row" style={{ gap: 6 }}>
                          <input type="checkbox" checked={confirmed.has(item.field_key)}
                            onChange={(e) => {
                              const next = new Set(confirmed);
                              if (e.target.checked) next.add(item.field_key);
                              else next.delete(item.field_key);
                              setConfirmed(next);
                            }} />
                          <span>Potwierdzam z klientem</span>
                        </label>
                      )
                    ) : (
                      <small className="dim">nie wymaga</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ErrorBox error={error} />
        {note && <p className="alert alert--info" role="status">{note}</p>}
        {session.status === "COACH_APPROVED" ? (
          <p className="alert alert--info">
            Zatwierdzone. Podsumowanie jest podstawą planu — sam plan
            układasz Ty, aplikacja niczego nie generuje.
          </p>
        ) : (
          <>
            {!state.can_approve && (
              <p className="alert alert--warn">
                Czekamy na zatwierdzenie podsumowania przez klienta. To jego
                dane — kolejność nie jest zamienna.
              </p>
            )}
            {pending.length > 0 && (
              <p className="dim">
                Do potwierdzenia z klientem:{" "}
                {pending.map((r) => fieldLabel(r.field_key)).join(", ")}.
              </p>
            )}
            <button className="btn btn--small" disabled={busy || !state.can_approve}
              onClick={approve}>
              {busy ? "Zapisuję…" : "Zatwierdzam jako podstawę planu"}
            </button>
          </>
        )}
      </div>

      <div className="card">
        <h2>Dane źródłowe — odpowiedzi klienta</h2>
        <p className="dim">
          Dokładnie to, co powiedział klient, wraz z historią poprawek.
          Pominięte pytania są oznaczone — pominięcie to informacja, nie brak.
        </p>
        {answers.length === 0 && <p className="dim">Brak odpowiedzi.</p>}
        {answers.map((row) => (
          <div className="exercise" key={`${row.step_id}-${row.version}`}>
            <div>
              <b>{row.question}</b>
              <div className="meta">
                {row.skipped
                  ? "pominięte przez klienta"
                  : row.hidden
                    ? "ukryte — brak zgody na tę kategorię danych"
                    : row.value}
              </div>
              <div className="meta">
                {row.topic} · v{row.version}
                {!row.is_current && " · wersja wcześniejsza (poprawiona)"}
                {" · "}{plDateTime(row.created_at)}
              </div>
            </div>
            {row.safety_flagged && (
              <span className="badge badge--warn">
                do konsultacji: {row.safety_signals.join(", ")}
              </span>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

const STATUS_LABELS: Record<string, string> = {
  IN_PROGRESS: "rozmowa w toku",
  SUMMARY_READY: "podsumowanie gotowe",
  CLIENT_APPROVED: "zatwierdzone przez klienta",
  COACH_APPROVED: "zatwierdzone przez trenera",
  ABANDONED: "porzucona",
};

function PlanTab({ clientId }: { clientId: string }) {
  const [plans, setPlans] = useState<TrainingPlan[] | null>(null);
  const [versions, setVersions] = useState<PlanVersion[] | null>(null);
  const [workouts, setWorkouts] = useState<WorkoutRow[]>([]);
  const [templates, setTemplates] = useState<TrainingPlan[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [copying, setCopying] = useState(false);
  const [editing, setEditing] = useState<"new" | "version" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const plan = plans?.find((p) => p.status === "ACTIVE" && !p.is_template) ?? null;

  const load = useCallback(() => {
    setEditing(null);
    setVersions(null);
    api.get<{ plans: TrainingPlan[] }>(`/api/clients/${clientId}/plans`)
      .then((d) => setPlans(d.plans)).catch((e) => setError(e.message));
    api.get<{ workouts: WorkoutRow[] }>(`/api/clients/${clientId}/workouts`)
      .then((d) => setWorkouts(d.workouts))
      .catch((e) => setError(`Nie udało się wczytać treningów. ${e.message}`));
    api.get<{ templates: TrainingPlan[] }>("/api/plans/templates")
      .then((d) => setTemplates(d.templates))
      .catch((e) => setError(`Nie udało się wczytać szablonów. ${e.message}`));
  }, [clientId]);
  useEffect(load, [load]);

  async function copyTemplate() {
    if (!templateId) return;
    setCopying(true);
    setError(null);
    try {
      await api.post(`/api/plans/${templateId}/copy-to/${clientId}`);
      setTemplateId("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCopying(false);
    }
  }

  useEffect(() => {
    if (plan && !versions) {
      api.get<{ versions: PlanVersion[] }>(`/api/plans/${plan.id}/versions`)
        .then((d) => setVersions(d.versions))
        .catch((e) => setError(`Nie udało się wczytać historii wersji. ${e.message}`));
    }
  }, [plan, versions]);

  if (error) return <ErrorBox error={error} onRetry={load} />;
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
        <div className="row" style={{ marginBottom: 10, flexWrap: "wrap" }}>
          <button className="btn btn--small" onClick={() => setEditing("new")}>+ Nowy plan</button>
          {plan && (
            <button className="btn btn--ghost btn--small" onClick={() => setEditing("version")}>
              Nowa wersja aktualnego planu
            </button>
          )}
          {templates.length > 0 && (
            <>
              <select value={templateId} style={{ width: "auto" }}
                aria-label="Wybierz szablon planu"
                onChange={(e) => setTemplateId(e.target.value)}>
                <option value="">Z szablonu…</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
              </select>
              {templateId && (
                <button className="btn btn--small" disabled={copying} onClick={copyTemplate}>
                  {copying ? "Kopiowanie…" : "Kopiuj do klienta"}
                </button>
              )}
            </>
          )}
        </div>
      )}
      {plan?.current_version && (
        <div className="card">
          <div className="row row--between">
            <h2>{plan.title}</h2>
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
          <h2>Historia wersji</h2>
          <div className="table-wrap">
            <table className="simple table--cards">
              <thead><tr><th>Wersja</th><th>Data</th><th>Powód</th></tr></thead>
              <tbody>
                {versions.slice().reverse().map((v) => (
                  <tr key={v.id}>
                    <td data-label="Wersja">v{v.version_no}</td>
                    <td data-label="Data">{plDate(v.created_at)}</td>
                    <td data-label="Powód">{v.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {workouts.length > 0 && (
        <div className="card">
          <h2>Wykonane treningi</h2>
          {workouts.slice(0, 12).map((w) => (
            <div className="exercise" key={w.id}>
              <div>
                <b>{plDate(w.performed_on)}</b>
                {w.pain_flag && <span className="badge badge--danger" style={{ marginLeft: 6 }}>ból: {w.pain_note}</span>}
                {w.comment && <div className="meta">{w.comment}</div>}
                {w.entries.filter((e) => e.result || e.sets.length > 0).map((e, i) => (
                  <div className="meta" key={i}>
                    {e.exercise_name}:{" "}
                    {e.sets.length > 0
                      ? e.sets.map((s) => `${s.weight_kg} kg×${s.reps}`).join(", ")
                      : e.result}
                  </div>
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
  const [supplements, setSupplements] = useState<SupplementEntry[]>([]);
  const [allergies, setAllergies] = useState<string | null>(null);
  const [ocrOpen, setOcrOpen] = useState(false);
  const [ocrNote, setOcrNote] = useState<string | null>(null);

  const plan = plans?.[0] ?? null;
  const load = useCallback(() => {
    setEditing(false);
    api.get<{ plans: NutritionPlanRow[] }>(`/api/clients/${clientId}/nutrition`)
      .then((d) => setPlans(d.plans)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  // Zadeklarowane alergie/nietolerancje — pokazywane przy edycji
  // suplementacji, żeby zalecenie nie powstawało w oderwaniu od tego, co
  // klient zgłosił. Brak zgody na dane żywieniowe = pole po prostu się
  // nie pojawia (backend i tak filtruje pola wrażliwe per domena).
  useEffect(() => {
    api.get<{ fields: { field_key: string; value: string; is_current?: boolean }[] }>(
      `/api/clients/${clientId}/profile`
    )
      .then((d) => {
        const row = d.fields.find((f) => f.field_key === "alergie" && f.is_current !== false);
        setAllergies(row?.value ?? null);
      })
      .catch(() => setAllergies(null));
  }, [clientId]);

  const setSupplement = (index: number, patch: Partial<SupplementEntry>) =>
    setSupplements((list) => list.map((s, i) => (i === index ? { ...s, ...patch } : s)));

  async function save(e: FormEvent) {
    e.preventDefault();
    // Pozycja suplementacji bez kompletu wymaganych pól jest błędem, a nie
    // powodem do cichego pominięcia — inaczej trener zapisałby wersję
    // przekonany, że preparat jest w planie.
    const incomplete = supplements.some(
      (s) => !s.name.trim() || !s.dose.trim() || !s.timing.trim()
        || !s.purpose.trim() || !s.source.trim()
    );
    if (incomplete) {
      setError(
        "Każdy suplement wymaga nazwy, dawki, pory, celu i podstawy zalecenia."
      );
      return;
    }
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
      supplements,
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

  if (error) return <ErrorBox error={error} onRetry={load} />;
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
            // Suplementacja przechodzi do nowej wersji — nowa wersja planu
            // nie może po cichu odstawić preparatów; odstawienie ma być
            // świadomym usunięciem pozycji przez trenera.
            setSupplements(v?.content.supplements.map((s) => ({ ...s })) ?? []);
            setEditing(true);
          }}>
          {plan ? "Nowa wersja diety" : "+ Nowa dieta"}
        </button>
      )}
      {editing && (
        <form className="card card--accent" onSubmit={save}>
          {!plan && (
            <>
              <label htmlFor="nt-title">Nazwa planu żywieniowego</label>
              <input id="nt-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </>
          )}
          <label htmlFor="nt-reason">Powód zmiany</label>
          <input id="nt-reason" required value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <div className="field-row">
            <div><label htmlFor="nt-kcal">kcal</label><input id="nt-kcal" type="number" value={form.kcal} onChange={(e) => setForm({ ...form, kcal: e.target.value })} /></div>
            <div><label htmlFor="nt-protein">Białko (g)</label><input id="nt-protein" type="number" value={form.protein_g} onChange={(e) => setForm({ ...form, protein_g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label htmlFor="nt-fat">Tłuszcze (g)</label><input id="nt-fat" type="number" value={form.fat_g} onChange={(e) => setForm({ ...form, fat_g: e.target.value })} /></div>
            <div><label htmlFor="nt-carbs">Węglowodany (g)</label><input id="nt-carbs" type="number" value={form.carbs_g} onChange={(e) => setForm({ ...form, carbs_g: e.target.value })} /></div>
          </div>
          <label htmlFor="nt-zasady">Zalecenia tekstowe</label>
          <textarea id="nt-zasady" value={form.zasady} onChange={(e) => setForm({ ...form, zasady: e.target.value })} />
          <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
            <button type="button" className="btn btn--ghost btn--small"
              aria-expanded={ocrOpen} onClick={() => setOcrOpen(!ocrOpen)}>
              {ocrOpen ? "Zamknij przepisywanie" : "Przepisz ze zdjęcia (kartka z dietą)"}
            </button>
          </div>
          <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }}>
            {ocrNote ?? ""}
          </p>
          {ocrOpen && (
            <OcrCapture
              purpose="PLAN"
              clientId={clientId}
              title="Dieta z kartki"
              hint={"Zrób zdjęcie kartki z dietą. Rozpoznany tekst dopiszemy do "
                + "pola z zaleceniami — poprawisz go tam i zapiszesz jako nową "
                + "wersję planu żywieniowego."}
              approveLabel="Wstaw do zaleceń"
              onApprove={(_task, text) => {
                setForm((f) => ({ ...f, zasady: appendText(f.zasady, text) }));
                setOcrNote(
                  "Tekst ze zdjęcia dopisano do zaleceń. Popraw go i zapisz "
                  + "nową wersję — samo przepisanie niczego nie zapisało."
                );
                setOcrOpen(false);
                return true;
              }}
              onClose={() => setOcrOpen(false)}
            />
          )}
          <label htmlFor="nt-meals">Posiłki (jeden na linię: „Nazwa: opis")</label>
          <textarea id="nt-meals" value={form.meals} onChange={(e) => setForm({ ...form, meals: e.target.value })} />

          <h3 style={{ marginBottom: 4 }}>Suplementacja</h3>
          <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
            Aplikacja niczego nie dobiera — zapisujesz zalecenie, które sam
            wydałeś lub które pochodzi od specjalisty. Podstawa zalecenia jest
            wymagana i widoczna dla klienta.
          </p>
          {allergies && (
            <div className="alert alert--warn" role="status">
              Zadeklarowane alergie i nietolerancje klienta: {allergies}
            </div>
          )}
          {supplements.map((s, i) => (
            <div className="exercise" key={i} style={{ display: "block" }}>
              <div className="field-row">
                <div>
                  <label htmlFor={`sup-name-${i}`}>Preparat</label>
                  <input id={`sup-name-${i}`} value={s.name}
                    onChange={(e) => setSupplement(i, { name: e.target.value })} />
                </div>
                <div>
                  <label htmlFor={`sup-dose-${i}`}>Dawka</label>
                  <input id={`sup-dose-${i}`} value={s.dose} placeholder="np. 1 kapsułka 2000 IU"
                    onChange={(e) => setSupplement(i, { dose: e.target.value })} />
                </div>
              </div>
              <div className="field-row">
                <div>
                  <label htmlFor={`sup-timing-${i}`}>Kiedy</label>
                  <input id={`sup-timing-${i}`} value={s.timing} placeholder="np. rano, do posiłku"
                    onChange={(e) => setSupplement(i, { timing: e.target.value })} />
                </div>
                <div>
                  <label htmlFor={`sup-form-${i}`}>Postać (opcjonalnie)</label>
                  <input id={`sup-form-${i}`} value={s.form ?? ""} placeholder="kapsułki, proszek…"
                    onChange={(e) => setSupplement(i, { form: e.target.value })} />
                </div>
              </div>
              <label htmlFor={`sup-purpose-${i}`}>Cel</label>
              <input id={`sup-purpose-${i}`} value={s.purpose}
                onChange={(e) => setSupplement(i, { purpose: e.target.value })} />
              <label htmlFor={`sup-source-${i}`}>Podstawa zalecenia (kto i na jakiej podstawie)</label>
              <input id={`sup-source-${i}`} value={s.source}
                placeholder="np. zalecenie lekarza z 2026-07-12 / wynik badań"
                onChange={(e) => setSupplement(i, { source: e.target.value })} />
              <div className="field-row">
                <div>
                  <label htmlFor={`sup-duration-${i}`}>Okres (opcjonalnie)</label>
                  <input id={`sup-duration-${i}`} value={s.duration ?? ""} placeholder="np. 8 tygodni"
                    onChange={(e) => setSupplement(i, { duration: e.target.value })} />
                </div>
                <div>
                  <label htmlFor={`sup-notes-${i}`}>Uwagi (opcjonalnie)</label>
                  <input id={`sup-notes-${i}`} value={s.notes ?? ""}
                    onChange={(e) => setSupplement(i, { notes: e.target.value })} />
                </div>
              </div>
              <div className="row row--between" style={{ marginTop: 8 }}>
                <label htmlFor={`sup-spec-${i}`} style={{ margin: 0 }}>
                  <input id={`sup-spec-${i}`} type="checkbox" checked={!!s.specialist_consulted}
                    onChange={(e) => setSupplement(i, { specialist_consulted: e.target.checked })} />
                  {" "}Konsultowane ze specjalistą
                </label>
                <button type="button" className="btn btn--ghost btn--small"
                  aria-label={`Usuń pozycję ${s.name || i + 1}`}
                  onClick={() => setSupplements(supplements.filter((_, j) => j !== i))}>
                  Usuń pozycję
                </button>
              </div>
            </div>
          ))}
          <button type="button" className="btn btn--ghost btn--small"
            onClick={() => setSupplements([...supplements, {
              name: "", dose: "", timing: "", purpose: "", source: "",
              form: "", duration: "", notes: "", specialist_consulted: false,
            }])}>
            + Dodaj suplement
          </button>

          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn">Zapisz</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(false)}>Anuluj</button>
          </div>
        </form>
      )}
      {v && (
        <div className="card">
          <div className="row row--between">
            <h2>{plan!.title}</h2>
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
          {v.content.supplements.length > 0 && (
            <>
              <h3>Suplementacja (v{plan!.current_version_no})</h3>
              {v.content.supplements.map((s, i) => (
                <SupplementRow key={i} planId={plan!.id} supplement={s} onError={setError} />
              ))}
            </>
          )}
        </div>
      )}
    </>
  );
}

/** Pozycja suplementacji w widoku trenera z jednoklikowym utworzeniem
 * przypomnienia. Dawka i sposób przyjmowania są brane po stronie serwera
 * z planu — tutaj wskazujemy wyłącznie godzinę, więc przypomnienie nie może
 * rozjechać się z tym, co klient widzi w diecie. */
function SupplementRow({ planId, supplement, onError }: {
  planId: string;
  supplement: SupplementEntry;
  onError: (message: string) => void;
}) {
  const [time, setTime] = useState("08:00");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  async function addReminder() {
    setBusy(true);
    try {
      const res = await api.post<{ created: number; skipped: number }>(
        `/api/nutrition/${planId}/supplements/reminders`,
        { entries: [{ name: supplement.name, time_of_day: time }] }
      );
      setDone(res.created > 0
        ? `Dodano przypomnienie na ${time}.`
        : "Takie przypomnienie już istnieje w harmonogramie.");
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="exercise" style={{ display: "block" }}>
      <div className="row row--between">
        <b>{supplement.name}{supplement.form ? ` · ${supplement.form}` : ""}</b>
        <span className="badge badge--accent">{supplement.dose}</span>
      </div>
      <div className="meta">Kiedy: {supplement.timing} · Cel: {supplement.purpose}</div>
      <div className="meta">
        Podstawa: {supplement.source}
        {supplement.specialist_consulted && " · konsultowane ze specjalistą"}
      </div>
      {supplement.notes && <div className="meta">Uwagi: {supplement.notes}</div>}
      <div className="row" style={{ marginTop: 8, gap: 6, alignItems: "flex-end" }}>
        <div>
          <label htmlFor={`sup-rem-${planId}-${supplement.name}`}>Godzina przypomnienia</label>
          <input id={`sup-rem-${planId}-${supplement.name}`} type="time" value={time}
            onChange={(e) => setTime(e.target.value)} style={{ width: "auto" }} />
        </div>
        <button type="button" className="btn btn--ghost btn--small" disabled={busy}
          onClick={addReminder}>
          {busy ? "Dodawanie…" : "Dodaj do harmonogramu"}
        </button>
      </div>
      {done && <small className="dim" role="status">{done}</small>}
    </div>
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
    try {
      await api.post(`/api/schedule/${id}/status?status=${status}`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  return (
    <>
      <form className="card" onSubmit={add}>
        <h2>Dodaj element harmonogramu</h2>
        <div className="field-row">
          <div>
            <label htmlFor="sch-name">Nazwa</label>
            <input id="sch-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label htmlFor="sch-category">Kategoria</label>
            <select id="sch-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
        </div>
        <div className="field-row">
          <div>
            <label htmlFor="sch-time">Pora (HH:MM)</label>
            <input id="sch-time" value={form.time_of_day} placeholder="np. 08:00" pattern="\d{2}:\d{2}"
              onChange={(e) => setForm({ ...form, time_of_day: e.target.value })} />
          </div>
          <div>
            <span style={{ display: "block", fontSize: "0.85rem", color: "var(--text-dim)", margin: "10px 0 4px" }} id="sch-days-label">Dni tygodnia</span>
            <div className="row" style={{ flexWrap: "wrap", gap: 4 }} role="group" aria-labelledby="sch-days-label">
              {WEEKDAYS.map((w, i) => (
                <button type="button" key={i}
                  className={`btn btn--ghost btn--small ${form.days.includes(i + 1) ? "active" : ""}`}
                  aria-pressed={form.days.includes(i + 1)}
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
        <label htmlFor="sch-instruction">Instrukcja</label>
        <input id="sch-instruction" value={form.instruction} onChange={(e) => setForm({ ...form, instruction: e.target.value })} />
        {form.category === "SUPLEMENT" && (
          <>
            <label htmlFor="sch-author">Autor zalecenia / źródło (wymagane dla suplementów)</label>
            <input id="sch-author" required value={form.author_note}
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
              {s.author_note && <small className="dim"><Icon name="info" size={14} label="autor zalecenia" /> {s.author_note}</small>}
            </div>
            <div className="row">
              {s.status === "ACTIVE" ? (
                <button className="btn btn--ghost btn--small" aria-label={`Wstrzymaj: ${s.name}`}
                  onClick={() => setStatus(s.id, "PAUSED")}><Icon name="pause" size={18} /></button>
              ) : (
                <button className="btn btn--ghost btn--small" aria-label={`Wznów: ${s.name}`}
                  onClick={() => setStatus(s.id, "ACTIVE")}><Icon name="play" size={18} /></button>
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
    try {
      await api.post(`/api/checkins/${id}/review`, {
        coach_response: responses[id], rating: ratings[id] || null,
      });
      load();
    } catch (err) {
      // Błąd zapisu oceny — komunikat w zakładce; wpisana odpowiedź trenera
      // zostaje w polu (responses/ratings nie są czyszczone).
      setError((err as Error).message);
    }
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

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!checkins) return <Spinner />;
  return (
    <>
      {checkins.length === 0 && <p className="dim">Brak raportów.</p>}
      {checkins.map((c) => {
        const state = ai[c.id];
        return (
          <div className="card" key={c.id}>
            <div className="row row--between">
              <h2 style={{ margin: 0 }}>Tydzień {plDate(c.week_start)}</h2>
              <span className="row" style={{ gap: 4 }}>
                {c.corrected && (
                  <span className="badge badge--warn" title="Klient poprawił raport po wysłaniu — historia w rewizjach">
                    skorygowany
                  </span>
                )}
                {!c.photos_complete && (
                  <span className="badge badge--warn"
                    title="Klient zadeklarował więcej zdjęć, niż zostało zapisanych">
                    częściowy · zdjęcia {c.photos_attached}/{c.photos_expected}
                  </span>
                )}
                <span className={`badge ${c.status === "REVIEWED" ? "badge--ok" : "badge--warn"}`}>
                  {c.status === "REVIEWED" ? "oceniony" : `do oceny${c.revision > 1 ? ` · rew. ${c.revision}` : ""}`}
                </span>
              </span>
            </div>

            <SectionLabel n={1} title="Ciało i trening" />
            <div className="stat-grid">
              <div className="stat"><b>{String(c.payload.weight_kg ?? "—")}</b><span>masa (kg)</span></div>
              <div className="stat"><b>{String(c.payload.trainings_done ?? "—")}</b><span>treningi</span></div>
            </div>

            <SectionLabel n={2} title="Samopoczucie" />
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {SCALE_LABELS.map(([k, l]) => {
                const value = c.payload[k];
                const state = c.payload.scale_states?.[k];
                if (value != null) {
                  return <span className="badge" key={k}>{l} {String(value)}/5</span>;
                }
                if (state === "SKIPPED") {
                  return <span className="badge" key={k} style={{ opacity: 0.65 }}>{l}: pominięte</span>;
                }
                if (state === "NOT_APPLICABLE") {
                  return <span className="badge" key={k} style={{ opacity: 0.65 }}>{l}: nie dotyczy</span>;
                }
                // Brak odpowiedzi — jawnie, zamiast cicho chować pytanie.
                return <span className="badge" key={k} style={{ opacity: 0.45 }}>{l}: brak odpowiedzi</span>;
              })}
            </div>
            {!c.scales_declared && SCALE_LABELS.some(([k]) => c.payload[k] != null) && (
              <small className="dim">
                Raport sprzed aktualizacji formularza — suwaki mogły pozostać
                na wartości domyślnej 3/5 (dane mniej wiarygodne).
              </small>
            )}

            {Boolean(c.payload.pain_note || c.payload.comment || c.payload.questions) && (
              <>
                <SectionLabel n={3} title="Ból, komentarz, pytania" />
                {typeof c.payload.pain_note === "string" && c.payload.pain_note && (
                  <p className="alert alert--error"><Icon name="warn" size={16} /> Ból/uraz: {c.payload.pain_note}</p>
                )}
                {typeof c.payload.comment === "string" && c.payload.comment && (
                  <p><b>Komentarz:</b> {c.payload.comment}</p>
                )}
                {typeof c.payload.questions === "string" && c.payload.questions && (
                  <p><b>Pytania:</b> {c.payload.questions}</p>
                )}
              </>
            )}

            {c.photos.length > 0 && (
              <div className="photo-grid" style={{ margin: "8px 0" }}>
                {c.photos.map((p) => (
                  <div key={p.file_id} style={{ textAlign: "center" }}>
                    <AuthImage fileId={p.file_id}
                      alt={`zdjęcie raportu${p.pose ? ` (${POSE_LABELS[p.pose] ?? p.pose})` : ""}`} />
                    {p.pose && <small className="dim">{POSE_LABELS[p.pose] ?? p.pose}</small>}
                  </div>
                ))}
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
                    <Icon name="sparkle" size={16} /> Podsumowanie AI (propozycja)
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
                <textarea placeholder="Odpowiedź dla klienta…" aria-label="Odpowiedź dla klienta"
                  value={responses[c.id] ?? ""}
                  onChange={(e) => setResponses({ ...responses, [c.id]: e.target.value })} />
                {state?.draft && (
                  <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
                    onClick={() => setResponses({ ...responses, [c.id]: state.draft! })}>
                    Wstaw szkic AI do edycji
                  </button>
                )}
                <div className="row row--between" style={{ marginTop: 8, alignItems: "center" }}>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }} id={`rating-label-${c.id}`}>
                    Ocena raportu (opcjonalnie)
                  </span>
                  <div className="row" style={{ gap: 4 }} role="group" aria-labelledby={`rating-label-${c.id}`}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button type="button" key={n}
                        className={`btn btn--ghost btn--small ${ratings[c.id] === n ? "active" : ""}`}
                        aria-pressed={ratings[c.id] === n}
                        aria-label={`Ocena ${n} na 5`}
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
  const load = useCallback(() => {
    setError(null);
    api.get<{ measurements: MeasurementRow[] }>(`/api/clients/${clientId}/measurements`)
      .then((d) => setRows(d.measurements)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);
  if (error) return <ErrorBox error={error} onRetry={load} />;
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
              <h2>{KIND_LABELS[k] ?? k}</h2>
              <span className="badge">{data[data.length - 1].value} {data[data.length - 1].unit}</span>
            </div>
            <Sparkline unit={data[0].unit} label={KIND_LABELS[k] ?? k}
              points={data.map((r) => ({ x: plDate(r.measured_at), y: r.value }))} />
          </div>
        );
      })}
    </>
  );
}

type PayFilter = "all" | "due" | "upcoming" | "paid";

/** Historia jednego rekordu (przejścia statusu + transakcje) — dociągana
 * na żądanie z dedykowanego endpointu. */
function RecordHistoryPanel({ recordId, onReverse }: {
  recordId: string;
  onReverse: (txId: string) => void;
}) {
  const [data, setData] = useState<PaymentHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    api.get<PaymentHistory>(`/api/payments/records/${recordId}/history`)
      .then(setData).catch((e) => setError(e.message));
  }, [recordId]);
  useEffect(load, [load]);
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!data) return <Spinner />;
  return (
    <div style={{ fontSize: "0.85rem", padding: "6px 0" }}>
      {data.status_changes.length === 0 && data.transactions.length === 0 && (
        <p className="dim">Brak zmian dla tego rekordu.</p>
      )}
      {data.status_changes.length > 0 && (
        <>
          <h3>Zmiany statusu</h3>
          {data.status_changes.map((c) => (
            <div key={c.id} className="dim">
              {plDateTime(c.changed_at)} — {PAYMENT_LABELS[c.from_status] ?? c.from_status}{" "}
              → {PAYMENT_LABELS[c.to_status] ?? c.to_status}
              {c.changed_by_name ? ` (${c.changed_by_name})` : ""}
              {c.reason ? ` — ${c.reason}` : ""}
            </div>
          ))}
        </>
      )}
      {data.transactions.length > 0 && (
        <>
          <h3>Transakcje</h3>
          {data.transactions.map((t) => (
            <div key={t.id} className="row row--between">
              <span className="dim"
                style={t.reversed ? { textDecoration: "line-through" } : undefined}>
                {plDateTime(t.created_at)} — {PAYMENT_TX_LABELS[t.kind] ?? t.kind}{" "}
                {money(Math.abs(t.amount_cents), t.currency)}
                {t.created_by_name ? ` (${t.created_by_name})` : ""}
                {t.document_ref ? `, dok. ${t.document_ref}` : ""}
                {t.note ? ` — ${t.note}` : ""}
                {t.reversed ? " — cofnięta" : ""}
              </span>
              {!t.reversed && t.kind !== "REVERSAL" && (
                <button className="btn btn--ghost btn--small"
                  onClick={() => onReverse(t.id)}>Cofnij</button>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function PaymentsTab({ clientId }: { clientId: string }) {
  const [schedules, setSchedules] = useState<PaymentScheduleRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<PayFilter>("all");
  const [openHistory, setOpenHistory] = useState<string | null>(null);
  const [historyEpoch, setHistoryEpoch] = useState(0);
  const [form, setForm] = useState({ package_name: "", amount: "", first_due_date: "", period: "MONTHLY" });

  const load = useCallback(() => {
    api.get<{ schedules: PaymentScheduleRow[] }>(`/api/clients/${clientId}/payments`)
      .then((d) => setSchedules(d.schedules)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);

  const reload = () => { load(); setHistoryEpoch((n) => n + 1); };

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/payments/schedules", {
        client_id: clientId, package_name: form.package_name,
        amount_cents: Math.round(Number(form.amount.replace(",", ".")) * 100),
        period: form.period, first_due_date: form.first_due_date,
      });
      setForm({ package_name: "", amount: "", first_due_date: "", period: "MONTHLY" });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  // „Opłacona" wyłącznie przez dedykowany endpoint (transakcja ręczna z
  // autorem i momentem); klucz idempotencji chroni przed podwójnym kliknięciem.
  async function markPaid(r: PaymentRecordRow) {
    const doc = prompt("Numer dokumentu (faktura/przelew, opcjonalnie):") ?? undefined;
    if (doc === undefined && !confirm("Oznaczyć jako opłaconą bez numeru dokumentu?")) return;
    try {
      await api.post(`/api/payments/records/${r.id}/mark-paid`, {
        document_ref: doc || null,
        idempotency_key: crypto.randomUUID(),
      });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function refund(r: PaymentRecordRow) {
    const raw = prompt(`Kwota zwrotu w ${r.currency} (np. 150,00):`);
    if (!raw) return;
    const cents = Math.round(Number(raw.replace(",", ".")) * 100);
    if (!Number.isFinite(cents) || cents <= 0) { setError("Nieprawidłowa kwota zwrotu"); return; }
    const note = prompt("Powód zwrotu (opcjonalnie):") || null;
    try {
      await api.post(`/api/payments/records/${r.id}/refund`, {
        amount_cents: cents, note, idempotency_key: crypto.randomUUID(),
      });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function reverse(txId: string) {
    const reason = prompt("Powód cofnięcia (wymagany — ślad zostaje w historii):");
    if (!reason) return;
    try {
      await api.post(`/api/payments/transactions/${txId}/reverse`, {
        reason, idempotency_key: crypto.randomUUID(),
      });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function setStatus(recordId: string, status: string, note?: string) {
    try {
      await api.post(`/api/payments/records/${recordId}/status`, { status, note });
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addRecord(scheduleId: string) {
    const due = prompt("Termin kolejnej płatności (RRRR-MM-DD):");
    if (!due) return;
    try {
      await api.post(`/api/payments/schedules/${scheduleId}/records?due_date=${due}`);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error) return <ErrorBox error={error} onRetry={() => { setError(null); load(); }} />;
  if (!schedules) return <Spinner />;

  const matches = (r: PaymentRecordRow): boolean => {
    const s = r.effective_status;
    if (filter === "due") return ["OVERDUE", "FAILED"].includes(s);
    if (filter === "upcoming") return ["PENDING", "PLANNED", "IN_PROGRESS"].includes(s);
    if (filter === "paid") return ["PAID", "PARTIALLY_REFUNDED", "REFUNDED"].includes(s);
    return true;
  };
  const overdueCount = schedules.flatMap((s) => s.records)
    .filter((r) => ["OVERDUE", "FAILED"].includes(r.effective_status)).length;

  return (
    <>
      <form className="card" onSubmit={create}>
        <h2>Nowy pakiet płatności</h2>
        <div className="field-row">
          <div><label htmlFor="pay-name">Nazwa pakietu</label>
            <input id="pay-name" required value={form.package_name}
              onChange={(e) => setForm({ ...form, package_name: e.target.value })} /></div>
          <div><label htmlFor="pay-amount">Kwota (PLN)</label>
            <input id="pay-amount" required type="text" inputMode="decimal" value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
        </div>
        <div className="field-row">
          <div><label htmlFor="pay-due">Pierwszy termin</label>
            <input id="pay-due" required type="date" value={form.first_due_date}
              onChange={(e) => setForm({ ...form, first_due_date: e.target.value })} /></div>
          <div><label htmlFor="pay-period">Okres</label>
            <select id="pay-period" value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })}>
              <option value="MONTHLY">miesięczny</option>
              <option value="WEEKLY">tygodniowy</option>
              <option value="ONE_OFF">jednorazowy</option>
            </select></div>
        </div>
        <div style={{ marginTop: 10 }}><button className="btn btn--small">Utwórz</button></div>
      </form>

      <div className="row" role="group" aria-label="Filtr płatności" style={{ margin: "8px 0", flexWrap: "wrap" }}>
        {([["all", "Wszystkie"], ["due", `Zaległe (${overdueCount})`],
           ["upcoming", "Nadchodzące"], ["paid", "Opłacone"]] as [PayFilter, string][]).map(([k, label]) => (
          <button key={k} className={`btn btn--small ${filter === k ? "" : "btn--ghost"}`}
            aria-pressed={filter === k} onClick={() => setFilter(k)}>{label}</button>
        ))}
        <Link className="btn btn--ghost btn--small" to="/trener/rozliczenia">Raport pojednania</Link>
      </div>

      {schedules.map((s) => (
        <div className="card" key={s.schedule_id}>
          <div className="row row--between">
            <h2>{s.package_name}</h2>
            <div className="row">
              <b>{money(s.amount_cents, s.currency)}</b>
              <button className="btn btn--ghost btn--small" onClick={() => addRecord(s.schedule_id)}>
                + termin
              </button>
            </div>
          </div>
          <div className="table-wrap">
          <table className="simple table--cards">
            <thead><tr><th>Termin</th><th>Kwota</th><th>Status</th><th>Akcje</th></tr></thead>
            <tbody>
              {s.records.filter(matches).map((r) => {
                const status = r.effective_status;
                return (
                <Fragment key={r.id}>
                <tr>
                  <td data-label="Termin">{plDate(r.due_date)}</td>
                  <td data-label="Kwota">{money(r.amount_cents, r.currency)}</td>
                  <td data-label="Status">
                    <span className={paymentBadgeClass(status)}>
                      {PAYMENT_LABELS[status] ?? status}</span>
                    {r.marked_at && r.marked_by_name && (
                      <div className="dim" style={{ fontSize: "0.75rem" }}>
                        {r.marked_by_name}, {plDate(r.marked_at.slice(0, 10))}
                      </div>
                    )}
                  </td>
                  <td>
                    {["PLANNED", "PENDING", "OVERDUE", "FAILED", "IN_PROGRESS"].includes(r.status) && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => markPaid(r)}>Opłacona</button>
                    )}{" "}
                    {["PAID", "PARTIALLY_REFUNDED"].includes(r.status) && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => refund(r)}>Zwrot</button>
                    )}{" "}
                    {["PLANNED", "PENDING", "OVERDUE", "FAILED"].includes(r.status) && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => setStatus(r.id, "CANCELLED")}>Anuluj</button>
                    )}{" "}
                    {r.status === "CANCELLED" && (
                      <button className="btn btn--ghost btn--small"
                        onClick={() => setStatus(r.id, "PENDING", "przywrócenie należności")}>
                        Przywróć</button>
                    )}{" "}
                    <button className="btn btn--ghost btn--small"
                      aria-expanded={openHistory === r.id}
                      onClick={() => setOpenHistory(openHistory === r.id ? null : r.id)}>
                      Historia</button>
                  </td>
                </tr>
                {openHistory === r.id && (
                  <tr>
                    <td colSpan={4}>
                      <RecordHistoryPanel key={historyEpoch} recordId={r.id} onReverse={reverse} />
                    </td>
                  </tr>
                )}
                </Fragment>
                );
              })}
            </tbody>
          </table>
          </div>
        </div>
      ))}
    </>
  );
}

function MonitoringTab({ clientId }: { clientId: string }) {
  const [data, setData] = useState<MonitoringData | null>(null);
  const [photos, setPhotos] = useState<ProgressPhotoRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    api.get<MonitoringData>(`/api/clients/${clientId}/monitoring`)
      .then(setData).catch((e) => setError(e.message));
    api.get<{ photos: ProgressPhotoRow[] }>(`/api/clients/${clientId}/photos`)
      .then((d) => setPhotos(d.photos))
      .catch((e) => setError(`Nie udało się wczytać zdjęć postępów. ${e.message}`));
  }, [clientId]);
  useEffect(load, [load]);

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!data) return <Spinner />;

  return (
    <>
      {data.goal && (
        <div className="card card--accent">
          <div className="row row--between">
            <h2><Icon name="target" /> {data.goal.title}</h2>
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

      <PersonalRecordsCard clientId={clientId} />
      <StrengthChartsCard clientId={clientId} />

      {photos.length >= 2 && <PhotoCompare photos={photos} formatDate={plDate} />}

      {Object.keys(data.adherence).length > 0 && (
        <div className="card">
          <h2>Realizacja harmonogramu ({data.period_days} dni)</h2>
          {Object.entries(data.adherence).map(([cat, b]) => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div className="row row--between">
                <b style={{ fontSize: "0.9rem" }}>{CATEGORY_LABELS[cat] ?? cat}</b>
                <small>{b.done}/{b.total}{b.pct !== null && ` · ${b.pct}%`}</small>
              </div>
              <div aria-hidden style={{ background: "var(--bg-raised)", borderRadius: 999, height: 8, overflow: "hidden", marginTop: 4 }}>
                <div style={{ width: `${Math.min(100, b.pct ?? 0)}%`, background: "var(--accent)", height: "100%" }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {Object.keys(data.wellbeing_series).length > 0 && (
        <div className="card">
          <h2>Samopoczucie</h2>
          {Object.entries(data.wellbeing_series).map(([key, points]) => (
            <div key={key} style={{ marginTop: 10 }}>
              <div className="row row--between">
                <b style={{ fontSize: "0.9rem" }}>{WELLBEING_LABELS[key] ?? key}</b>
                <span className="badge">{points[points.length - 1].value}/5</span>
              </div>
              <Sparkline unit="/5" label={WELLBEING_LABELS[key] ?? key}
                points={wellbeingSparkPoints(points)} />
            </div>
          ))}
          {Object.values(data.wellbeing_series).some((pts) => pts.some((p) => p.declared === false)) && (
            <small className="dim">
              Tygodnie bez raportu to przerwy w linii (nie są uzupełniane).
              Punkty z raportów sprzed aktualizacji formularza mogą zawierać
              wartość domyślną 3/5.
            </small>
          )}
        </div>
      )}

      {data.nutrition.log_series.length >= 2 && (
        <div className="card">
          <div className="row row--between">
            <h2>Dziennik kaloryczny</h2>
            {data.nutrition.target_kcal !== null && (
              <span className="badge">cel: {data.nutrition.target_kcal} kcal</span>
            )}
          </div>
          <Sparkline unit="kcal" label="Dziennik kaloryczny"
            points={dailySparkPoints(data.nutrition.log_series)} />
        </div>
      )}

      <div className="card">
        <h2>Obserwacje klienta</h2>
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
  const load = useCallback(() => {
    setError(null);
    api.get<{ receipts: ReceiptRow[] }>(`/api/coach/clients/${clientId}/history`)
      .then((d) => setReceipts(d.receipts)).catch((e) => setError(e.message));
  }, [clientId]);
  useEffect(load, [load]);
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!receipts) return <Spinner />;
  return (
    <div className="card">
      <h2>Historia zmian (pokwitowania z łańcucha audytu Human OS)</h2>
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

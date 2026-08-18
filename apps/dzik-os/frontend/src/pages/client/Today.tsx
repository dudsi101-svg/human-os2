import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getUser, money } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Icon, PushContextPrompt, Spinner, TopBar } from "../../components";
import { CATEGORY_LABELS, ConsultSlotRow, TodayData } from "../../types";

export default function Today() {
  const [data, setData] = useState<TodayData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);
  const [markingSchedule, setMarkingSchedule] = useState<string | null>(null);
  const [needsIntake, setNeedsIntake] = useState(false);
  const [nextConsult, setNextConsult] = useState<ConsultSlotRow | null>(null);
  const user = getUser();

  const load = () => {
    setError(null);
    api.get<TodayData>("/api/me/today").then(setData).catch((e) => setError(e.message));
  };
  useEffect(() => {
    load();
    if (user) {
      // Pusty profil = świeże konto — zaproś do wywiadu startowego.
      // Świadome zignorowanie błędu (obie karty poniżej): to opcjonalne
      // PODPOWIEDZI nad właściwym widokiem — przy awarii znikają, a błąd
      // głównych danych i tak pokaże ekran błędu z /api/me/today.
      api.get<{ fields: unknown[] }>(`/api/clients/${user.id}/profile`)
        .then((d) => setNeedsIntake(d.fields.length === 0))
        .catch(() => undefined);
      api.get<{ booked: ConsultSlotRow[] }>("/api/me/consult-slots")
        .then((d) => setNextConsult(d.booked[0] ?? null))
        .catch(() => undefined);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function markDone() {
    if (!data?.workout || !user) return;
    setMarking(true);
    try {
      await api.post(`/api/clients/${user.id}/workouts`, {
        plan_version_id: data.workout.plan_version_id,
        day_index: data.workout.day_index,
        performed_on: data.date,
        status: "DONE",
        entries: [],
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setMarking(false);
    }
  }

  async function markScheduleDone(itemId: string) {
    if (!data || !user) return;
    setMarkingSchedule(itemId);
    try {
      await api.post(`/api/clients/${user.id}/schedule/${itemId}/complete`, {
        completed_on: data.date,
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setMarkingSchedule(null);
    }
  }

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!data) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dzisiaj" />
      {needsIntake && (
        <Link to="/ankieta" className="card card--accent" style={{ display: "block", marginBottom: 10 }}>
          <b style={{ color: "var(--text)" }}>👋 Zacznijmy od wywiadu startowego</b>
          <p className="dim" style={{ margin: "4px 0 0", fontSize: "0.85rem" }}>
            Kilka pytań o cel, doświadczenie i zdrowie — trener od razu
            dopasuje plan do Ciebie. Zajmie 2 minuty.
          </p>
        </Link>
      )}
      {(data.schedule?.length ?? 0) > 0 && (
        <PushContextPrompt context="today"
          benefit="Dostaniesz przypomnienie o treningu i punktach harmonogramu
          dokładnie o zaplanowanej porze — nawet gdy aplikacja jest zamknięta." />
      )}
      {nextConsult && (
        <Link to="/konsultacje" className="card" style={{ display: "block", marginBottom: 10 }}>
          <b style={{ color: "var(--text)", display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="calendar" /> Najbliższa konsultacja
          </b>
          <p className="dim" style={{ margin: "4px 0 0", fontSize: "0.85rem" }}>
            {new Date(nextConsult.starts_at).toLocaleString("pl-PL", {
              weekday: "long", day: "numeric", month: "long",
              hour: "2-digit", minute: "2-digit",
            })} · {nextConsult.duration_min} min
          </p>
        </Link>
      )}
      {data.workout ? (
        <div className="card card--accent">
          <div className="row row--between">
            <h2><Icon name="plan" /> {data.workout.day.name}</h2>
            <span className="badge badge--accent">plan v{data.workout.version_no}</span>
          </div>
          <small>{data.workout.plan_title}</small>
          <div style={{ marginTop: 8 }}>
            {data.workout.day.exercises.map((ex, i) => (
              <div className="exercise" key={i}>
                <div>
                  <b>{ex.name}</b>
                  {ex.comment && <div className="meta">{ex.comment}</div>}
                </div>
                <div className="meta">
                  {[ex.sets && `${ex.sets}×${ex.reps ?? "?"}`, ex.weight, ex.rest]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            {data.workout.done_today ? (
              <p className="alert alert--info">✅ Trening oznaczony jako wykonany.
                {" "}<Link to="/plan">Uzupełnij wyniki</Link></p>
            ) : (
              <button className="btn" onClick={markDone} disabled={marking}>
                {marking ? "Zapisywanie…" : "Wykonane ✓"}
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="card">
          <h2><Icon name="moon" /> Dziś bez treningu</h2>
          <small>Regeneracja też jest częścią planu.</small>
        </div>
      )}

      {data.nutrition && (
        <div className="card">
          <h2><Icon name="diet" /> {data.nutrition.title}</h2>
          <div className="stat-grid" style={{ marginTop: 8 }}>
            <div className="stat"><b>{data.nutrition.kcal ?? "—"}</b><span>kcal</span></div>
            <div className="stat"><b>{data.nutrition.protein_g ?? "—"} g</b><span>białko</span></div>
            <div className="stat"><b>{data.nutrition.carbs_g ?? "—"} g</b><span>węglowodany</span></div>
            <div className="stat"><b>{data.nutrition.fat_g ?? "—"} g</b><span>tłuszcze</span></div>
          </div>
          <div style={{ marginTop: 8 }}><Link to="/dieta">Zobacz pełną dietę →</Link></div>
        </div>
      )}

      {data.schedule.length > 0 && (
        <div className="card">
          <h2><Icon name="clipboard" /> Harmonogram na dziś</h2>
          {data.schedule.map((s) => (
            <div className="exercise" key={s.id}>
              <div>
                <b>{s.name}</b>
                {s.instruction && <div className="meta">{s.instruction}</div>}
                <div className="meta">
                  {s.time_of_day ?? ""} <span className="badge">{CATEGORY_LABELS[s.category] ?? s.category}</span>
                </div>
              </div>
              {s.done_today ? (
                <span className="badge badge--ok">✓ zrobione</span>
              ) : (
                <button className="btn btn--ghost btn--small" disabled={markingSchedule === s.id}
                  onClick={() => markScheduleDone(s.id)}>
                  {markingSchedule === s.id ? "…" : "Wykonane"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {data.reminders.length > 0 && (
        <div className="card">
          <h2><Icon name="bell" /> Przypomnienia</h2>
          {data.reminders.map((r) => (
            <div className="exercise" key={r.id}>
              <div>{r.text}</div>
              <div className="meta">{plDate(r.due_date)}</div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="row row--between">
          <div>
            <h2><Icon name="report" /> Raport tygodniowy</h2>
            <small>
              {data.checkin_due
                ? `Najbliższy termin: ${plDate(data.checkin_due)}`
                : "Wyślij pierwszy raport"}
            </small>
          </div>
          <Link to="/raport" className="btn btn--ghost btn--small">Wypełnij</Link>
        </div>
      </div>

      {data.next_payment && (
        <div className="card">
          <div className="row row--between">
            <div>
              <h2><Icon name="card" /> {data.next_payment.package_name ?? "Płatność"}</h2>
              <small>
                {money(data.next_payment.amount_cents, data.next_payment.currency)} · termin{" "}
                {plDate(data.next_payment.due_date)}
              </small>
            </div>
            <span className={`badge ${data.next_payment.status === "OVERDUE" ? "badge--danger" : "badge--warn"}`}>
              {data.next_payment.status === "OVERDUE" ? "Zaległa" : "Oczekuje"}
            </span>
          </div>
          <div style={{ marginTop: 6 }}><Link to="/platnosci">Szczegóły płatności →</Link></div>
        </div>
      )}

      {data.last_coach_message && (
        <div className="card">
          <h2><Icon name="msg" /> Od trenera {data.last_coach_message.unread && <span className="badge badge--accent">nowa</span>}</h2>
          <p style={{ margin: "6px 0" }}>{data.last_coach_message.body}</p>
          <Link to={`/wiadomosci/${data.last_coach_message.thread_id}`}>Odpowiedz →</Link>
        </div>
      )}

      <div className="card">
        <div className="row row--between">
          <small>Coś Cię boli lub coś nie gra?</small>
          <Link to="/wiadomosci" className="btn btn--ghost btn--small">Zgłoś problem</Link>
        </div>
      </div>
    </div>
  );
}

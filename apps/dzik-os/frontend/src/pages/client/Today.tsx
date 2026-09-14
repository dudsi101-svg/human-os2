import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getUser, money } from "../../api";
import { plDate } from "../../dates";
import {
  ErrorBox, Icon, PushContextPrompt, Spinner, TopBar,
} from "../../components";
import { OpisCwiczenia } from "../../opisCwiczenia";
import { PozycjaBloku, PozycjaCardio, rodzajPozycji } from "../../pozycje";
import { CATEGORY_LABELS, ConsultSlotRow, TodayData } from "../../types";
import { powitanie } from "../../powitanie";
import PanelNawykow from "../nawyki/PanelNawykow";
import Powitanie from "./Powitanie";

export default function Today() {
  const [data, setData] = useState<TodayData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);
  // Cardio (0.73.0): urządzenie wybrane na dziś (lista dozwolonych od trenera).
  const [maszyna, setMaszyna] = useState<string | null>(null);
  const [markingSchedule, setMarkingSchedule] = useState<string | null>(null);
  const [needsIntake, setNeedsIntake] = useState(false);
  const [nextConsult, setNextConsult] = useState<ConsultSlotRow | null>(null);
  // Zaproszenie do głębokiego wywiadu (0.53.12, audyt B6): dopiero po
  // pierwszym wysłanym raporcie i tylko, jeśli wywiad nigdy nie ruszył.
  const [inviteInterview, setInviteInterview] = useState(false);
  const [interviewDismissed, setInterviewDismissed] = useState(false);
  // Samouczek (0.70.0): zamknięty w tej sesji widoku od razu znika; znacznik
  // idzie na serwer w tle (POST idempotentny) — błąd sieci nie wraca oknem
  // w tej samej chwili, a przy następnym wejściu okno po prostu pokaże się
  // ponownie (pomoc, nie bramka).
  const [welcomeClosed, setWelcomeClosed] = useState(false);
  const user = getUser();

  const load = useCallback(() => {
    setError(null);
    api.get<TodayData>("/api/me/today").then(setData).catch((e) => setError(e.message));
  }, []);
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
      // Kolejność wdrażania: rozmowa startowa → pierwszy raport → wywiad.
      // Oba zapytania to podpowiedź — awaria któregokolwiek = brak karty.
      Promise.all([
        api.get<{ checkins: unknown[] }>(`/api/clients/${user.id}/checkins`),
        api.get<{ wywiady: { typ: string; submission_status: string }[] }>(`/api/clients/${user.id}/wywiady`),
      ])
        .then(([c, i]) =>
          setInviteInterview(c.checkins.length > 0
            && (i.wywiady.find((w) => w.typ === "gleboki")?.submission_status ?? "not_started") === "not_started")
        )
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

  function closeWelcome() {
    setWelcomeClosed(true);
    api.post("/api/me/welcome-seen").catch(() => undefined);
  }

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!data) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dzisiaj" />
      {!data.welcome_seen && !welcomeClosed && (
        <Powitanie imie={data.greeting_name} onZamknij={closeWelcome} />
      )}
      {/* Panel rozwojowy (0.63.0): powitanie → hasło dnia → nawyki. */}
      <p className="powitanie" data-testid="powitanie">{powitanie(new Date().getHours(), data.greeting_name)}</p>
      <div className="card card--accent" style={{ marginBottom: 10 }} data-testid="haslo-dnia">
        <p style={{ margin: 0, fontSize: "1.05rem", color: "var(--text)" }}>
          <Icon name="sparkle" /> <i>„{data.daily_message.text}”</i>
        </p>
        <small className="dim">— {data.daily_message.author}{data.daily_message.note ? ` (${data.daily_message.note})` : ""}</small>
      </div>
      {user && <PanelNawykow clientId={user.id} tryb="klient" habits={data.habits} onZmiana={load} />}
      {needsIntake && (
        <div className="card card--accent" style={{ marginBottom: 10 }}>
          <b style={{ color: "var(--text)" }}>👋 Zacznijmy od rozmowy startowej</b>
          <p className="dim" style={{ margin: "4px 0 8px", fontSize: "0.85rem" }}>
            Kilka pytań o cel, doświadczenie i zdrowie — jedno po drugim,
            spokojnie. Każde możesz pominąć, a rozmowę przerwać i dokończyć
            później. Na koniec sam(a) zatwierdzasz podsumowanie.
          </p>
          <div className="row">
            <Link to="/rozmowa" className="btn btn--small">Porozmawiajmy</Link>
            <Link to="/ankieta" className="btn btn--ghost btn--small">
              Wolę formularz
            </Link>
          </div>
        </div>
      )}
      {!needsIntake && inviteInterview && !interviewDismissed && (
        <div className="card card--accent" style={{ marginBottom: 10 }}>
          <b style={{ color: "var(--text)" }}>🎯 Pierwszy raport za Tobą — czas na głęboki wywiad</b>
          <p className="dim" style={{ margin: "4px 0 8px", fontSize: "0.85rem" }}>
            Dłuższa rozmowa o motywacji, śnie, stresie i historii — dzięki
            niej plan przestaje być uniwersalny. Każde pytanie możesz
            pominąć, a rozmowę przerwać i dokończyć kiedy indziej.
          </p>
          <div className="row">
            <Link to="/wywiad" className="btn btn--small">Zacznijmy</Link>
            <button className="btn btn--ghost btn--small"
              onClick={() => setInterviewDismissed(true)}>
              Później
            </button>
          </div>
        </div>
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
      {data.workout_hint?.kind === "stale" && (
        <p className="alert alert--info" role="status" data-testid="dni-nieaktualne">
          Plan się zmienił — <Link to="/plan">sprawdź dni tygodnia</Link>.
        </p>
      )}
      {data.workout ? (
        <div className="card card--accent" data-testid="trening-dzis">
          <div className="row row--between">
            <h2><Icon name="plan" /> {data.workout.day.name}</h2>
            <span className="badge badge--accent">plan v{data.workout.version_no}</span>
          </div>
          <small>{data.workout.plan_title} · <span data-testid="zrodlo-dnia">
            {data.workout.weekday_source === "client" ? "Twój wybór" : "propozycja trenera"}</span></small>
          <div style={{ marginTop: 8 }}>
            {data.workout.day.exercises.map((ex, i) => {
              // Rozgrzewka / rozciąganie / cardio (0.73.0): wspólny renderer z Planem.
              const rodzaj = rodzajPozycji(ex);
              if (rodzaj === "warmup_block" || rodzaj === "stretch_block") return <PozycjaBloku key={i} ex={ex} powrot="/" testid={`dzis-blok-${i}`} />;
              if (rodzaj === "cardio") {
                return (
                  <PozycjaCardio key={i} ex={ex} kompakt testid={`dzis-cardio-${i}`}
                    machine={maszyna} onMachine={setMaszyna}
                    dlaczego={{ plan_id: data.workout!.plan_id, plan_revision: data.workout!.version_no, target_id: `d${data.workout!.day_index}:e${i}` }} />
                );
              }
              return (
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
                <div style={{ gridColumn: "1 / -1", textAlign: "left" }}>
                  <OpisCwiczenia exerciseId={ex.exercise_id} name={ex.name} powrot="/" testid={`dzis-opis-${i}`} />
                </div>
              </div>
              );
            })}
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
      ) : data.workout_hint?.kind === "no_weekdays" ? (
        // Dni treningowe (0.71.0): plan jest, ale żadna jednostka nie ma dnia —
        // system nie zgaduje za człowieka, tylko prowadzi do wyboru.
        <div className="card card--accent" data-testid="ustaw-dni">
          <h2><Icon name="calendar" /> Masz plan, ale nie wybrałeś dni tygodnia</h2>
          <p className="dim" style={{ margin: "4px 0 8px", fontSize: "0.85rem" }}>
            Wybierz, w które dni robisz poszczególne jednostki — trening z dzisiejszego dnia pojawi się tutaj.
          </p>
          <Link to="/plan" className="btn btn--small">Ustaw dni tygodnia</Link>
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

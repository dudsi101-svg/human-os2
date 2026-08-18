// Panel asystenta trenera przy edytorze planu — „szkic planu z Twojej bazy".
//
// Płynność jest tu wymaganiem, nie ozdobnikiem:
// * praca idzie W TLE (zadanie + magistrala SSE + odpytywanie zapasowe),
//   więc edytor planu pozostaje w pełni używalny w trakcie generowania —
//   panel niczego nie nakłada na formularz i niczego nie blokuje;
// * widoczny postęp, jedno kliknięcie „anuluj”, jawny komunikat, gdy trwa
//   dłużej niż zwykle, i twardy timeout zamiast wiszącej kręciołki;
// * propozycja pojawia się OBOK planu, wstawienie to jedno kliknięcie,
//   a zaraz po nim dostępne jest „cofnij wstawienie”;
// * bez przeładowań i skoków — zmiany stanu ogłasza aria-live, wszystkie
//   pola mają etykiety `for`/`id`, całość obsługiwana klawiaturą;
// * powtórne kliknięcie nie mnoży zadań (klucz idempotencji), a szkic
//   roboczy formularza przeżywa chwilową utratę sieci (localStorage);
// * bez dostawcy modelu ten sam przycisk otwiera ŚCIEŻKĘ LOKALNĄ —
//   odfiltrowaną wyszukiwarkę bazy i podpowiedź „skopiuj szablon”.
//
// Granica: asystent PROPONUJE, trener DECYDUJE. Nic nie zapisuje się samo,
// a ciężary (kilogramy) nie są proponowane w ogóle.

import { useEffect, useRef, useState } from "react";
import { api, getUser, isCancel } from "./api";
import { ErrorBox, Spinner } from "./components";
import { EQUIPMENT_SUGGESTIONS } from "./exerciseFilters";
import { connectRealtime } from "./realtime";
import {
  AssistantStatusInfo,
  AssistantTask,
  EMPTY_DRAFT_FORM,
  LocalMatch,
  PlanDraftForm,
  clearFormDraft,
  draftRequest,
  draftStorageKey,
  engineLabel,
  formReady,
  hasLocalPath,
  hasProposal,
  isFinished,
  loadFormDraft,
  localDayToPlanDay,
  matchToExercise,
  proposalToPlanDays,
  saveFormDraft,
  statusMessage,
} from "./assistantUtils";
import { EXERCISE_LEVEL_LABELS, Exercise, PlanDay, muscleLabels } from "./types";

const POLL_MS = 1200;
const STATUS_URL = "/api/coach/assistant/status";
const TASKS_URL = "/api/coach/assistant/tasks";

export interface PlanAssistantProps {
  clientId: string | null;
  /** Wstawienie dni do edytora — jedno kliknięcie, z możliwością cofnięcia. */
  onInsertDays: (days: PlanDay[], label: string) => void;
  /** Dołożenie pojedynczego ćwiczenia (ścieżka lokalna). */
  onInsertExercise: (exercise: Exercise, label: string) => void;
  canUndo: boolean;
  onUndo: () => void;
  onClose: () => void;
}

export default function PlanAssistant({
  clientId,
  onInsertDays,
  onInsertExercise,
  canUndo,
  onUndo,
  onClose,
}: PlanAssistantProps) {
  const userId = getUser()?.id ?? "anon";
  const storageKey = draftStorageKey(userId, clientId);
  const [form, setForm] = useState<PlanDraftForm>(
    () => loadFormDraft(storageKey) ?? EMPTY_DRAFT_FORM
  );
  const [info, setInfo] = useState<AssistantStatusInfo | null>(null);
  const [task, setTask] = useState<AssistantTask | null>(null);
  const [generation, setGeneration] = useState(0);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const startedRef = useRef<number>(0);

  const query = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  useEffect(() => {
    api.get<AssistantStatusInfo>(`${STATUS_URL}${query}`)
      .then(setInfo)
      .catch((e) => { if (!isCancel(e)) setError((e as Error).message); });
  }, [query]);

  // Szkic roboczy formularza przeżywa utratę sieci i zamknięcie panelu.
  useEffect(() => { saveFormDraft(storageKey, form); }, [storageKey, form]);

  useEffect(() => () => {
    if (pollRef.current) window.clearTimeout(pollRef.current);
  }, []);

  // Licznik czasu — po `slow_after_s` mówimy wprost, że trwa dłużej.
  useEffect(() => {
    if (!task || isFinished(task)) return;
    const timer = window.setInterval(
      () => setElapsed(Math.round((Date.now() - startedRef.current) / 1000)),
      1000
    );
    return () => window.clearInterval(timer);
  }, [task]);

  // Magistrala SSE: gotowy wynik pojawia się bez czekania na odpytanie.
  useEffect(() => {
    if (!task || isFinished(task)) return;
    const ctrl = new AbortController();
    const watched = task.id;
    void connectRealtime("/api/threads/events", {
      onEvent: (type, data) => {
        const payload = data as { task_id?: string } | null;
        if (type === "assistant.task" && payload?.task_id === watched) {
          void refresh(watched);
        }
      },
    }, ctrl.signal);
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task?.id, task?.status]);

  async function refresh(taskId: string): Promise<AssistantTask | null> {
    try {
      const fresh = await api.get<AssistantTask>(`${TASKS_URL}/${taskId}`);
      setTask(fresh);
      if (isFinished(fresh)) setBusy(false);
      return fresh;
    } catch (e) {
      if (!isCancel(e)) setError((e as Error).message);
      setBusy(false);
      return null;
    }
  }

  /** Odpytywanie zapasowe (gdy kanał SSE nie dochodzi) + twardy timeout. */
  function poll(taskId: string) {
    pollRef.current = window.setTimeout(async () => {
      const fresh = await refresh(taskId);
      if (!fresh || isFinished(fresh)) return;
      const seconds = (Date.now() - startedRef.current) / 1000;
      if (seconds > (info?.timeout_s ?? 60) + 15) {
        setBusy(false);
        setError(
          "Asystent nie odpowiedział w wyznaczonym czasie. Nic nie zostało "
          + "zapisane — spróbuj ponownie albo wybierz ćwiczenia z bazy ręcznie."
        );
        return;
      }
      poll(taskId);
    }, POLL_MS);
  }

  async function start() {
    setError(null);
    setBusy(true);
    setElapsed(0);
    startedRef.current = Date.now();
    try {
      const created = await api.post<AssistantTask>(
        TASKS_URL, draftRequest(form, clientId, generation)
      );
      setTask(created);
      if (isFinished(created)) setBusy(false);
      else poll(created.id);
    } catch (e) {
      if (!isCancel(e)) setError((e as Error).message);
      setBusy(false);
    }
  }

  async function cancel() {
    if (!task) return;
    if (pollRef.current) window.clearTimeout(pollRef.current);
    try {
      await api.post(`${TASKS_URL}/${task.id}/cancel`, {});
    } catch {
      /* Świadomie: nieudane anulowanie nie może zablokować interfejsu —
       * zadanie i tak niczego nie zapisuje. */
    }
    setBusy(false);
    await refresh(task.id);
  }

  function regenerate() {
    setGeneration(generation + 1);
    setTask(null);
    setError(null);
  }

  async function discard() {
    if (task) {
      try {
        await api.del(`${TASKS_URL}/${task.id}`);
      } catch {
        /* Odrzucenie propozycji nie może blokować zamknięcia panelu. */
      }
    }
    clearFormDraft(storageKey);
    onClose();
  }

  /** Zapis proweniencji po tym, jak trener wstawił propozycję do edytora.
   * Nie tworzy ani nie zmienia planu — zostawia ślad, że powstał z pomocą
   * asystenta (plan zapisuje trener zwykłą, wersjonowaną ścieżką). */
  function markApplied() {
    if (!task || task.approved_at) return;
    void api.post(`${TASKS_URL}/${task.id}/applied`, {}).catch(() => {
      /* Świadomie: brak śladu proweniencji nie może cofnąć wstawienia,
       * które trener już zobaczył w edytorze. */
    });
  }

  function insertProposal() {
    const days = proposalToPlanDays(task?.result);
    if (!days.length) return;
    onInsertDays(days, `Wstawiono ${days.length} dni ze szkicu asystenta.`);
    markApplied();
  }

  function insertLocalDay(index: number) {
    const local = task?.result?.local;
    if (!local) return;
    const day = localDayToPlanDay(local.days[index]);
    if (!day.exercises.length) return;
    onInsertDays([day], `Wstawiono dzień „${day.name}” z Twojej bazy.`);
    markApplied();
  }

  function insertMatch(match: LocalMatch) {
    onInsertExercise(matchToExercise(match), `Dodano „${match.name}” do ostatniego dnia.`);
    markApplied();
  }

  const running = !!task && !isFinished(task);
  const message = statusMessage(task, elapsed, info?.slow_after_s ?? 8);
  const proposal = hasProposal(task) ? task!.result!.days! : null;
  const local = hasLocalPath(task) ? task!.result!.local! : null;

  return (
    <div className="card card--accent" style={{ marginTop: 10 }}>
      <div className="row row--between">
        <b>Asystent: szkic planu z Twojej bazy ćwiczeń</b>
        <button type="button" className="btn btn--ghost btn--small" onClick={discard}>
          Zamknij asystenta
        </button>
      </div>

      <p className="dim" style={{ marginTop: 4 }}>
        Asystent proponuje, decydujesz Ty. <b>Ciężarów nie dobiera</b> —
        proponuje serie, zakresy powtórzeń, tempo i przerwę; kilogramy
        wpisujesz sam. Nic nie zapisuje się samo: plan zapiszesz jak zwykle,
        z powodem zmiany.
      </p>

      {info === null && !error && <Spinner />}

      {info !== null && (
        <p className="dim" style={{ marginTop: 4, fontSize: "0.8rem" }}>
          {info.mode === "MODEL"
            ? "Tryb rozszerzony: szkic przygotuje model, a Ty go sprawdzisz."
            : info.mode_reason}
          {" "}
          Twoja baza: {info.exercise_count} aktywnych ćwiczeń.
          {" "}Zadania dziś: {info.used_today}/{info.daily_limit}.
        </p>
      )}

      {info !== null && clientId && (
        <p className="dim" style={{ marginTop: 2, fontSize: "0.8rem" }}>
          {info.client_data_reason}
        </p>
      )}

      <div className="field-row" style={{ marginTop: 8 }}>
        <div>
          <label htmlFor="asy-days">Dni w tygodniu</label>
          <select id="asy-days" value={form.days_per_week} disabled={running}
            onChange={(e) => setForm({ ...form, days_per_week: Number(e.target.value) })}>
            {[1, 2, 3, 4, 5, 6, 7].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="asy-minutes">Czas jednej sesji (minuty)</label>
          <select id="asy-minutes" value={form.session_minutes} disabled={running}
            onChange={(e) => setForm({ ...form, session_minutes: Number(e.target.value) })}>
            {[30, 45, 60, 75, 90, 120].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      <label htmlFor="asy-level" style={{ marginTop: 6 }}>Poziom</label>
      <select id="asy-level" value={form.level} disabled={running}
        onChange={(e) => setForm({ ...form, level: e.target.value })}>
        {Object.entries(EXERCISE_LEVEL_LABELS).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>

      <fieldset style={{ marginTop: 8, border: "1px solid var(--border)", borderRadius: 8 }}>
        <legend className="meta">Dostępny sprzęt</legend>
        <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
          {EQUIPMENT_SUGGESTIONS.map((item) => {
            const checked = form.equipment.includes(item);
            return (
              <label key={item} htmlFor={`asy-eq-${item}`} className="badge"
                style={{ cursor: "pointer" }}>
                <input id={`asy-eq-${item}`} type="checkbox" checked={checked}
                  disabled={running}
                  onChange={() => setForm({
                    ...form,
                    equipment: checked
                      ? form.equipment.filter((e) => e !== item)
                      : [...form.equipment, item],
                  })} />
                {" "}{item}
              </label>
            );
          })}
        </div>
      </fieldset>

      <label htmlFor="asy-goal" style={{ marginTop: 8 }}>Cel podopiecznego</label>
      <input id="asy-goal" value={form.goal} disabled={running} maxLength={300}
        placeholder="np. wzmocnić plecy i wrócić do biegania"
        onChange={(e) => setForm({ ...form, goal: e.target.value })} />

      <div className="row" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <button type="button" className="btn" disabled={busy || running || !formReady(form)}
          onClick={start}>
          {running ? "Przygotowuję…" : "Przygotuj szkic"}
        </button>
        {running && (
          <button type="button" className="btn btn--ghost btn--small" onClick={cancel}>
            Anuluj
          </button>
        )}
        {task && isFinished(task) && (
          <button type="button" className="btn btn--ghost btn--small" onClick={regenerate}>
            Generuj ponownie
          </button>
        )}
        {canUndo && (
          <button type="button" className="btn btn--ghost btn--small" onClick={onUndo}>
            Cofnij wstawienie
          </button>
        )}
      </div>

      <p className="dim" role="status" aria-live="polite" style={{ marginTop: 6 }}>
        {message}
      </p>
      <ErrorBox error={error} />

      {task?.mode_reason && isFinished(task) && (
        <p className="dim" style={{ fontSize: "0.8rem" }}>{task.mode_reason}</p>
      )}

      {proposal && (
        <div style={{ marginTop: 8 }}>
          <div className="row row--between">
            <b>Propozycja ({engineLabel(task?.engine)})</b>
            <button type="button" className="btn btn--small" onClick={insertProposal}>
              Wstaw wszystkie dni do planu
            </button>
          </div>
          {proposal.map((day, di) => (
            <div key={di} className="card" style={{ marginTop: 6 }}>
              <div className="row row--between">
                <b>{day.name}</b>
                <button type="button" className="btn btn--ghost btn--small"
                  onClick={() => {
                    onInsertDays(proposalToPlanDays({ days: [day] }),
                      `Wstawiono dzień „${day.name}”.`);
                    markApplied();
                  }}>
                  Wstaw ten dzień
                </button>
              </div>
              <p className="dim" style={{ fontSize: "0.82rem" }}>{day.rationale}</p>
              <ul>
                {day.exercises.map((ex, ei) => (
                  <li key={ei}>
                    {ex.name}
                    <span className="meta">
                      {[ex.sets && `${ex.sets} serie`, ex.reps && `${ex.reps} powt.`,
                        ex.tempo && `tempo ${ex.tempo}`, ex.rest && `przerwa ${ex.rest}`]
                        .filter(Boolean).join(" · ")}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <p className="dim" style={{ fontSize: "0.78rem" }}>
            Ciężary nie są proponowane — wpisujesz je sam przy każdej pozycji.
          </p>
        </div>
      )}

      {local && (
        <div style={{ marginTop: 8 }}>
          <b>Tryb lokalny — Twoja baza odfiltrowana po tych warunkach</b>
          <p className="dim" style={{ fontSize: "0.82rem" }}>{local.hint}</p>
          {local.days.map((day, di) => (
            <div key={di} className="card" style={{ marginTop: 6 }}>
              <div className="row row--between">
                <b>{day.name}</b>
                <button type="button" className="btn btn--ghost btn--small"
                  onClick={() => insertLocalDay(di)}>
                  Wstaw ten dzień
                </button>
              </div>
              {day.slots.map((slot) => (
                <div key={slot.pattern} style={{ marginTop: 4 }}>
                  <span className="meta">{slot.pattern_label}</span>
                  {slot.matches.length === 0 ? (
                    <p className="dim" style={{ fontSize: "0.8rem" }}>
                      Brak ćwiczenia o tym wzorcu w Twojej bazie — dodaj je albo
                      wpisz pozycję ręcznie.
                    </p>
                  ) : (
                    <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                      {slot.matches.map((match) => (
                        <button key={match.id} type="button"
                          className="btn btn--ghost btn--small"
                          onClick={() => insertMatch(match)}>
                          {match.name}
                          <span className="meta">
                            {[match.equipment,
                              match.muscles_primary.length
                                ? muscleLabels(match.muscles_primary)
                                : null].filter(Boolean).join(" · ")}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
          {local.templates.length > 0 && (
            <p className="dim" style={{ fontSize: "0.82rem" }}>
              Szybsza droga: skopiuj istniejący szablon i popraw go —
              {" "}{local.templates.map((t) => t.title).join(", ")}.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

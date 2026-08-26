import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, getUser } from "../../api";
import { ErrorBox, Spinner, TopBar } from "../../components";
import {
  canApproveSummary,
  canSubmit,
  changedSummaryItems,
  charsLeft,
  fieldLabel,
  CONFIDENCE_LABELS,
  ORIGIN_LABELS,
  OnboardingState,
  OnboardingStep,
  parseMulti,
  progressAnnouncement,
  progressPercent,
  summaryModeNote,
  toggleMulti,
} from "../../onboardingUtils";

/** Rozmowa startowa — spokojna, jedno pytanie na krok.
 *
 * Scenariusz, kolejność pytań, reguły adaptacji i lista objawów
 * alarmowych są SERWEROWE (dzik_os/onboarding_flow.py, interview_flow.py)
 * — ten ekran ich nie zna i nie odtwarza. Dzięki temu rozmowa wygląda
 * tak samo z modelem językowym i bez niego.
 *
 * Ten sam ekran obsługuje OBA przepływy (rozmowę startową i głęboki
 * wywiad) — różnią się wyłącznie ścieżką API, tytułem i kartą wstępu
 * (`RozmowaPage`); patrz Interview.tsx.
 *
 * Dostępność (P10): jedno pytanie ma widoczną etykietę, zmiana kroku jest
 * ogłaszana przez aria-live, a fokus wędruje na nowe pytanie. */
export default function Onboarding() {
  return (
    <RozmowaPage
      apiPath="onboarding"
      title="Rozmowa startowa"
      introTitle="Porozmawiajmy o Tobie"
      intro={
        <>
          <p className="dim">
            Zadam kilka pytań — jedno po drugim, spokojnie. Przy każdym
            wyjaśniam, po co jest potrzebne. Każde pytanie możesz pominąć,
            wrócić do wcześniejszej odpowiedzi albo przerwać i dokończyć
            później. Na koniec zobaczysz podsumowanie i zdecydujesz, czy
            trafia do Twojego profilu.
          </p>
          <p className="dim">
            To nie jest wywiad medyczny. Trener nie stawia diagnoz —
            w sprawach zdrowia decyduje lekarz.
          </p>
        </>
      }
      formLink
    />
  );
}

export function RozmowaPage({ apiPath, title, introTitle, intro, formLink,
  healthModuleStepId }: {
  apiPath: string;
  title: string;
  introTitle: string;
  intro: React.ReactNode;
  formLink?: boolean;
  /** Krok-znacznik modułu zdrowotnego (0.53.12, przegląd ust. 10):
   * gdy plan rozmowy go nie zawiera, ekran mówi wprost, że scenariusz
   * jest skrócony i dlaczego — zamiast cicho pomijać połowę pytań. */
  healthModuleStepId?: string;
}) {
  const user = getUser()!;
  const base = `/api/clients/${user.id}/${apiPath}`;
  const navigate = useNavigate();
  const [state, setState] = useState<OnboardingState | null>(null);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [safety, setSafety] = useState<{ message: string; signals: string[] } | null>(null);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const questionRef = useRef<HTMLHeadingElement | null>(null);
  const lastStepId = useRef<string | null>(null);

  const applyState = useCallback((next: OnboardingState) => {
    setState(next);
    const previous = next.current_answer && !next.current_answer.skipped
      ? next.current_answer.value : "";
    // Krok informacyjny nie ma czego wpisywać — potwierdzeniem jest „Dalej".
    setValue(
      !previous && next.step?.kind === "INFO" ? next.step.options[0] ?? "" : previous,
    );
    setSafety(next.safety_notice ?? null);
  }, []);

  const load = useCallback(() => {
    setError(null);
    api.get<OnboardingState>(base)
      .then(applyState)
      .catch((e) => setError((e as Error).message));
  }, [base, applyState]);
  useEffect(load, [load]);

  // Fokus na nowym pytaniu — czytnik ekranu i klawiatura zaczynają
  // od treści kroku, a nie od początku strony.
  useEffect(() => {
    const stepId = state?.step?.id ?? null;
    if (stepId && stepId !== lastStepId.current) {
      lastStepId.current = stepId;
      questionRef.current?.focus();
    }
  }, [state?.step?.id]);

  async function call(path: string, body?: unknown, method: "post" | "put" = "post") {
    setBusy(true);
    setError(null);
    try {
      const next = method === "put"
        ? await api.put<OnboardingState>(path, body)
        : await api.post<OnboardingState>(path, body);
      applyState(next);
      return next;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  const session = state?.session ?? null;
  const step = state?.step ?? null;

  if (error && !state) {
    return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  }
  if (!state) return <div className="page"><Spinner /></div>;

  const percent = progressPercent(state);
  const summary = state.summary ?? [];
  const approved = session?.status === "CLIENT_APPROVED"
    || session?.status === "COACH_APPROVED";

  return (
    <div className="page">
      <TopBar title={title} />

      {healthModuleStepId && session && state.planned_steps
        && !state.planned_steps.includes(healthModuleStepId) && (
        <div className="card" style={{ marginBottom: 10 }}>
          <p className="dim" style={{ margin: 0, fontSize: "0.85rem" }}>
            Ta rozmowa jest skrócona: moduły wymagające zgody (m.in.
            zdrowie) są wyłączone — bo nie masz jeszcze przypisanego
            trenera albo zgoda została cofnięta. Włączysz je w{" "}
            <Link to="/profil">Profil → Dokumenty i zgody</Link>; rozmowa
            dopyta wtedy o pominięte moduły.
          </p>
        </div>
      )}
      {/* Ogłoszenie zmiany kroku dla czytników ekranu. */}
      <p className="sr-only" role="status" aria-live="polite">
        {progressAnnouncement(state)}
      </p>

      {!session && (
        <div className="card">
          <h2>{introTitle}</h2>
          {intro}
          <ErrorBox error={error} />
          <button className="btn" disabled={busy}
            onClick={() => call(`${base}/start`)}>
            {busy ? "Chwileczkę…" : "Zacznijmy"}
          </button>
          {formLink && (
            <Link className="btn btn--ghost" to="/ankieta" style={{ marginTop: 8 }}>
              Wolę wypełnić formularz
            </Link>
          )}
        </div>
      )}

      {session && (
        <>
          <div className="card" aria-label="Postęp rozmowy">
            <div className="row row--between" style={{ marginBottom: 6 }}>
              <b>Postęp</b>
              <span className="dim">
                {state.progress.answered} z {state.progress.total}
              </span>
            </div>
            <div className="onb-bar" role="progressbar" aria-valuemin={0}
              aria-valuemax={100} aria-valuenow={percent}
              aria-label={`Postęp rozmowy: ${percent}%`}>
              <span className="onb-bar__fill" style={{ width: `${percent}%` }} />
            </div>
          </div>

          {safety && <SafetyNotice notice={safety} onClose={() => setSafety(null)} />}

          {step && !approved && (
            <StepCard
              step={step}
              value={value}
              onChange={setValue}
              busy={busy}
              error={error}
              canGoBack={state.can_go_back === true}
              questionRef={questionRef}
              onSubmit={() =>
                call(`${base}/answer`, {
                  step_id: step.id, value, skipped: false,
                })}
              onSkip={() =>
                call(`${base}/answer`, {
                  step_id: step.id, value: "", skipped: true,
                })}
              onBack={() => call(`${base}/back`)}
              onPause={async () => {
                await api.post(`${base}/pause`).catch(() => {});
                navigate("/");
              }}
            />
          )}

          {!step && !approved && (
            <div className="card">
              <h2>To wszystko z mojej strony</h2>
              <p className="dim">
                Dziękuję. Przygotuję teraz podsumowanie — przeczytasz je,
                poprawisz co trzeba i dopiero wtedy trafi do Twojego profilu.
              </p>
              <ErrorBox error={error} />
              <button className="btn" disabled={busy}
                onClick={() => call(`${base}/summary`)}>
                {busy ? "Przygotowuję…" : "Pokaż podsumowanie"}
              </button>
              <button className="btn btn--ghost" disabled={busy}
                onClick={() => call(`${base}/back`)}>
                Wróć do ostatniego pytania
              </button>
            </div>
          )}

          {summary.length > 0 && (
            <SummaryCard
              state={state}
              summary={summary}
              edited={edited}
              approved={approved}
              busy={busy}
              saved={saved}
              onEdit={(key, next) => setEdited((prev) => ({ ...prev, [key]: next }))}
              onSave={async () => {
                const items = changedSummaryItems(summary, edited);
                if (items.length === 0) {
                  setSaved("Nic się nie zmieniło — podsumowanie zostaje bez zmian.");
                  return;
                }
                const next = await call(
                  `${base}/summary`, { items }, "put",
                );
                if (next) {
                  setEdited({});
                  setSaved("Poprawki zapisane.");
                }
              }}
              onApprove={async () => {
                const next = await call(`${base}/approve`);
                if (next) setSaved("Podsumowanie zatwierdzone i zapisane w profilu.");
              }}
              onRegenerate={() => call(`${base}/summary`)}
            />
          )}

          <AiModeCard state={state} />
        </>
      )}
    </div>
  );
}

function SafetyNotice({ notice, onClose }: {
  notice: { message: string; signals: string[] };
  onClose: () => void;
}) {
  return (
    <div className="card" role="alert" style={{ borderColor: "var(--warn)" }}>
      <h2>Zatrzymajmy się na chwilę</h2>
      <p>{notice.message}</p>
      {notice.signals.length > 0 && (
        <p className="dim">
          Co zwróciło naszą uwagę: {notice.signals.join(", ")}.
        </p>
      )}
      <button className="btn btn--ghost btn--small" onClick={onClose}>
        Rozumiem, kontynuujmy
      </button>
    </div>
  );
}

function StepCard({
  step, value, onChange, busy, error, canGoBack, questionRef,
  onSubmit, onSkip, onBack, onPause,
}: {
  step: OnboardingStep;
  value: string;
  onChange: (v: string) => void;
  busy: boolean;
  error: string | null;
  canGoBack: boolean;
  questionRef: React.MutableRefObject<HTMLHeadingElement | null>;
  onSubmit: () => void;
  onSkip: () => void;
  onBack: () => void;
  onPause: () => void;
}) {
  const inputId = `onb-${step.id}`;
  const ready = canSubmit(step, value);
  const chosen = parseMulti(value);
  return (
    <div className="card">
      <span className="badge">{step.topic}</span>
      {/* tabIndex=-1: fokus programowy po zmianie kroku, bez wpinania
          nagłówka w normalną kolejność tabulacji. */}
      <h2 id={`${inputId}-label`} ref={questionRef} tabIndex={-1}
        style={{ marginTop: 8 }}>
        {step.question}
      </h2>
      <p className="dim" id={`${inputId}-why`}>{step.why}</p>
      {step.sensitive && (
        <p className="alert alert--info">
          To pytanie dotyczy danych wrażliwych. Pytamy o nie tylko dlatego,
          że wyraziłeś(-aś) na to zgodę — i tylko po to, żeby plan Ci nie
          zaszkodził. Możesz je pominąć.
        </p>
      )}

      {(step.kind === "CHOICE" || step.kind === "BOOL" || step.kind === "SCALE") && (
        <div className="row" role="radiogroup" aria-labelledby={`${inputId}-label`}
          style={{ flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {step.options.map((option) => (
            <button key={option} type="button" role="radio"
              aria-checked={value === option}
              className={value === option ? "btn btn--small" : "btn btn--ghost btn--small"}
              onClick={() => onChange(option)}>
              {option}
            </button>
          ))}
        </div>
      )}

      {step.kind === "MULTI" && (
        <div className="row" role="group" aria-labelledby={`${inputId}-label`}
          style={{ flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {step.options.map((option) => (
            <button key={option} type="button"
              aria-pressed={chosen.includes(option)}
              className={chosen.includes(option)
                ? "btn btn--small" : "btn btn--ghost btn--small"}
              onClick={() => onChange(toggleMulti(value, option, step.options))}>
              {option}
            </button>
          ))}
        </div>
      )}

      {step.kind === "TEXT" && (
        <>
          <label htmlFor={inputId} className="sr-only">{step.question}</label>
          <input id={inputId} value={value} placeholder={step.placeholder}
            maxLength={step.max_len} aria-describedby={`${inputId}-why`}
            onChange={(e) => onChange(e.target.value)} />
        </>
      )}

      {step.kind === "LONGTEXT" && (
        <>
          <label htmlFor={inputId} className="sr-only">{step.question}</label>
          <textarea id={inputId} value={value} placeholder={step.placeholder}
            maxLength={step.max_len} rows={4} aria-describedby={`${inputId}-why`}
            onChange={(e) => onChange(e.target.value)} />
          <small className="dim">Zostało {charsLeft(step, value)} znaków.</small>
        </>
      )}

      <ErrorBox error={error} />

      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={busy || !ready} onClick={onSubmit}>
          {busy ? "Zapisuję…" : "Dalej"}
        </button>
        <button type="button" className="btn btn--ghost btn--small"
          disabled={busy} onClick={onSkip}>
          Pomiń to pytanie
        </button>
        {canGoBack && (
          <button type="button" className="btn btn--ghost btn--small"
            disabled={busy} onClick={onBack}>
            ← Wróć
          </button>
        )}
        <button type="button" className="btn btn--ghost btn--small"
          disabled={busy} onClick={onPause}>
          Przerwij i wróć później
        </button>
      </div>
      <small className="dim">
        Przerwana rozmowa nic nie gubi — wrócisz dokładnie w to miejsce.
      </small>
    </div>
  );
}

function SummaryCard({
  state, summary, edited, approved, busy, saved,
  onEdit, onSave, onApprove, onRegenerate,
}: {
  state: OnboardingState;
  summary: NonNullable<OnboardingState["summary"]>;
  edited: Record<string, string>;
  approved: boolean;
  busy: boolean;
  saved: string | null;
  onEdit: (key: string, value: string) => void;
  onSave: () => void;
  onApprove: () => void;
  onRegenerate: () => void;
}) {
  const session = state.session;
  return (
    <div className="card">
      <h2>Podsumowanie — sprawdź i popraw</h2>
      <p className="dim">{summaryModeNote(session)}</p>
      {session?.summary_stale && (
        <p className="alert alert--warn">
          Po przygotowaniu podsumowania zmieniłeś(-aś) jeszcze odpowiedzi —
          odśwież je, żeby zgadzało się z rozmową.
        </p>
      )}
      {summary.map((item) => {
        const id = `sum-${item.field_key}`;
        const current = edited[item.field_key] ?? item.value;
        return (
          <div key={item.field_key} style={{ marginBottom: 12 }}>
            <label htmlFor={id}>{fieldLabel(item.field_key)}</label>
            {item.hidden ? (
              <p className="dim">
                Ukryte — cofnięto zgodę na tę kategorię danych.
              </p>
            ) : (
              <>
                <textarea id={id} value={current} rows={2} disabled={approved || busy}
                  aria-describedby={`${id}-meta`}
                  onChange={(e) => onEdit(item.field_key, e.target.value)} />
                <small className="dim" id={`${id}-meta`}>
                  {ORIGIN_LABELS[item.origin] ?? item.origin}
                  {" · "}
                  {CONFIDENCE_LABELS[item.confidence] ?? item.confidence}
                  {item.needs_confirmation && " · do potwierdzenia z trenerem"}
                </small>
              </>
            )}
          </div>
        );
      })}
      {saved && <p className="alert alert--info" role="status">{saved}</p>}
      {state.skipped_fields && state.skipped_fields.length > 0 && (
        <p className="alert alert--warn">
          Nie zapisaliśmy pól, na które nie ma już aktywnej zgody:{" "}
          {state.skipped_fields.map(fieldLabel).join(", ")}.
        </p>
      )}
      {approved ? (
        <p className="alert alert--info">
          Podsumowanie zatwierdzone — dane są w Twoim profilu. Teraz trener
          przejrzy je i zatwierdzi jako podstawę planu. Wszystko możesz
          zmienić w Profilu.
        </p>
      ) : (
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn btn--ghost btn--small" disabled={busy} onClick={onSave}>
            Zapisz poprawki
          </button>
          <button className="btn btn--ghost btn--small" disabled={busy}
            onClick={onRegenerate}>
            Odśwież podsumowanie
          </button>
          <button className="btn" disabled={busy || !canApproveSummary(state)}
            onClick={onApprove}>
            Zatwierdzam — zapisz w moim profilu
          </button>
        </div>
      )}
      <small className="dim">
        Plan treningowy i dietę układa trener. Ta rozmowa niczego nie
        publikuje ani nie zaleca.
      </small>
    </div>
  );
}

function AiModeCard({ state }: { state: OnboardingState }) {
  return (
    <div className="card">
      <h2>Skąd bierze się podsumowanie</h2>
      {state.ai.available ? (
        <p className="dim">
          Wersję roboczą podsumowania może przygotować model językowy —
          wyłącznie jako propozycję do Twojej korekty. Wysyłamy do niego
          tylko Twoje odpowiedzi z tej rozmowy, bez imienia, e-maila
          i identyfikatorów.
        </p>
      ) : (
        <p className="dim">{state.ai.reason}</p>
      )}
      <p className="dim">
        Model nigdy nie stawia diagnoz, nie ocenia zdrowia i nie tworzy
        planu ani diety. Zakres danych wysyłanych na zewnątrz ustawiasz
        zgodą „Funkcje AI” w{" "}
        <Link to="/profil">Profilu → Prywatność i zgody</Link>.
      </p>
    </div>
  );
}

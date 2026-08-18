import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { WEEKDAYS } from "../../dates";
import { ErrorBox, ExerciseFilterBar, Spinner } from "../../components";
import {
  EMPTY_FILTERS,
  ExerciseFilters,
  exerciseQuery,
  hasActiveFilters,
} from "../../exerciseFilters";
import {
  KEYBOARD_HINT,
  nextActiveIndex,
  resultsMessage,
  showRecent,
  tabIndexFor,
} from "../../exercisePicker";
import OcrCapture from "../../OcrCapture";
import PlanAssistant from "../../PlanAssistant";
import { appendDays, snapshot } from "../../assistantUtils";
import { linesToExerciseNames } from "../../ocrUtils";
import {
  EXERCISE_LEVEL_LABELS,
  Exercise,
  ExerciseLibraryItem,
  ExerciseListResponse,
  PlanDay,
  TrainingPlan,
  muscleLabels,
} from "../../types";

const emptyExercise = (): Exercise => ({ name: "", sets: "", reps: "", weight: "", rest: "" });
const emptyDay = (): PlanDay => ({ name: "", weekday: null, exercises: [emptyExercise()] });

const PICKER_PAGE = 20;

/** Wyszukiwarka bazy ćwiczeń wbudowana w edytor planu. Jedno kliknięcie
 * dodaje pozycję do bieżącego dnia; wyszukiwarka zostaje otwarta, żeby
 * dało się dodać kilka ćwiczeń pod rząd. Nie zastępuje ręcznego wpisania
 * nazwy — trener zawsze może wpisać coś spoza bazy.
 *
 * Przy katalogu rzędu 250 pozycji liczą się trzy skróty:
 * * „ostatnio używane” nad wynikami (trener korzysta z kilkudziesięciu
 *   ćwiczeń, nie z całej bazy) — widoczne tylko przy pustym wyszukiwaniu;
 * * pełna obsługa klawiaturą: fokus ląduje w polu wyszukiwania, strzałki
 *   chodzą po wynikach (roving tabindex), Enter dodaje, Escape zamyka
 *   i wraca fokusem do przycisku, który wyszukiwarkę otworzył;
 * * komunikat mówiący wprost, ile wyników jeszcze zostało. */
function ExercisePicker({ idPrefix, onPick, onClose }: {
  idPrefix: string;
  onPick: (item: ExerciseLibraryItem) => void;
  onClose: () => void;
}) {
  const [filters, setFilters] = useState<ExerciseFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<ExerciseLibraryItem[] | null>(null);
  const [recent, setRecent] = useState<ExerciseLibraryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<string | null>(null);
  const [active, setActive] = useState(-1);
  const resultRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const load = (offset = 0) => {
    setError(null);
    const query = exerciseQuery(filters, offset, PICKER_PAGE, { status: "ACTIVE" });
    api.get<ExerciseListResponse>(`/api/coach/exercises?${query}`)
      .then((d) => {
        setItems((prev) => (offset > 0 && prev ? [...prev, ...d.items] : d.items));
        setTotal(d.total);
        setHasMore(d.has_more);
        if (offset === 0) setActive(-1);
      })
      .catch((e) => setError(e.message));
  };
  // Krótkie opóźnienie: przy pisaniu nie wysyłamy zapytania z każdą literą.
  useEffect(() => {
    const timer = setTimeout(() => load(0), 200);
    return () => clearTimeout(timer);
  }, [ // eslint-disable-line react-hooks/exhaustive-deps
    filters.q, filters.muscle, filters.equipment, filters.level, filters.pattern,
  ]);

  // Skrót „ostatnio używane” liczy serwer z wersji planów tego trenera.
  // Brak planów = pusta lista i sekcja się po prostu nie pokazuje.
  useEffect(() => {
    api.get<{ items: ExerciseLibraryItem[] }>("/api/coach/exercises/recent")
      .then((d) => setRecent(d.items))
      .catch(() => setRecent([]));
  }, []);

  // Po otwarciu fokus ląduje w polu wyszukiwania — trener od razu pisze.
  useEffect(() => {
    document.getElementById(`${idPrefix}-ex-q`)?.focus();
  }, [idPrefix]);

  const pick = (item: ExerciseLibraryItem) => {
    onPick(item);
    setAdded(item.name);
  };

  /** Strzałki, Enter i Escape działają z dowolnego miejsca wyszukiwarki. */
  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const count = items?.length ?? 0;
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = nextActiveIndex(active, event.key === "ArrowDown" ? 1 : -1, count);
      setActive(next);
      if (next >= 0) resultRefs.current[next]?.focus();
      return;
    }
    if (event.key === "Enter" && active >= 0 && items && items[active]) {
      // Enter w polu wyszukiwania nie może wysłać formularza planu.
      event.preventDefault();
      pick(items[active]);
    }
  }

  const message = resultsMessage({
    loading: items === null,
    error,
    total,
    shown: items?.length ?? 0,
    hasMore,
    hasFilters: hasActiveFilters(filters),
  });

  return (
    <div className="card exercise-picker" style={{ marginTop: 8 }} onKeyDown={onKeyDown}>
      <div className="row row--between">
        <b>Dodaj z bazy ćwiczeń</b>
        <button type="button" className="btn btn--ghost btn--small" onClick={onClose}>
          Zamknij wyszukiwarkę
        </button>
      </div>
      <ExerciseFilterBar idPrefix={idPrefix} value={filters} onChange={setFilters} />
      <p className="dim" style={{ marginTop: 2, fontSize: "0.78rem" }}>{KEYBOARD_HINT}</p>
      {showRecent(hasActiveFilters(filters), recent.length) && (
        <div style={{ marginTop: 6 }}>
          <span className="meta">Ostatnio używane</span>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            {recent.map((item) => (
              <button key={item.id} type="button" className="btn btn--ghost btn--small"
                onClick={() => pick(item)}>
                {item.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="dim" aria-live="polite" style={{ marginTop: 4 }}>
        {message}
        {added && ` Dodano „${added}” do dnia.`}
      </p>
      <ErrorBox error={error} onRetry={() => load(0)} />
      {items === null && !error && <Spinner />}
      {items && items.length > 0 && (
        <ul className="exercise-picker__results">
          {items.map((item, index) => (
            <li key={item.id}>
              <button type="button" className="exercise-picker__hit"
                ref={(node) => { resultRefs.current[index] = node; }}
                tabIndex={tabIndexFor(index, active)}
                aria-current={index === active ? true : undefined}
                onFocus={() => setActive(index)}
                onClick={() => pick(item)}>
                <b>{item.name}</b>
                <span className="meta">
                  {[
                    item.muscles_primary.length ? muscleLabels(item.muscles_primary) : null,
                    item.equipment,
                    item.level ? EXERCISE_LEVEL_LABELS[item.level] ?? item.level : null,
                  ].filter(Boolean).join(" · ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {hasMore && items && (
        <button type="button" className="btn btn--ghost btn--small"
          onClick={() => load(items.length)}>
          Pokaż więcej
        </button>
      )}
    </div>
  );
}

export default function PlanEditor({
  clientId,
  existingPlan,
  initialDays,
  onSaved,
  onCancel,
}: {
  clientId: string | null;
  existingPlan: TrainingPlan | null;
  initialDays?: PlanDay[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(existingPlan?.title ?? "");
  const [reason, setReason] = useState("");
  const [days, setDays] = useState<PlanDay[]>(
    initialDays?.length ? JSON.parse(JSON.stringify(initialDays)) : [emptyDay()]
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pickerDay, setPickerDay] = useState<number | null>(null);
  const [ocrOpen, setOcrOpen] = useState(false);
  const [ocrNote, setOcrNote] = useState<string | null>(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantNote, setAssistantNote] = useState<string | null>(null);
  // Migawka sprzed OSTATNIEGO wstawienia — „cofnij wstawienie" przywraca
  // dokładnie ten stan edytora. Trzymamy jedną: cofnięcie ma być
  // natychmiastowe i zrozumiałe, a nie pełną historią zmian.
  const [undoDays, setUndoDays] = useState<PlanDay[] | null>(null);
  // Przyciski otwierające wyszukiwarkę — Escape wraca fokusem dokładnie
  // tam, skąd trener ją otworzył (bez skoku na początek formularza).
  const pickerButtons = useRef<(HTMLButtonElement | null)[]>([]);

  const setDay = (i: number, day: PlanDay) =>
    setDays(days.map((d, j) => (i === j ? day : d)));

  /** Dodanie ćwiczenia z bazy: uzupełnia wyłącznie PUSTE pola pomocnicze —
   * nigdy nie nadpisuje tego, co trener już wpisał. */
  function addFromLibrary(dayIndex: number, item: ExerciseLibraryItem) {
    const day = days[dayIndex];
    const filled: Exercise = {
      name: item.name,
      exercise_id: item.id,
      sets: "",
      reps: "",
      weight: "",
      tempo: item.tempo_hint ?? "",
      rest: "",
      comment: item.cues[0] ?? "",
      video_url: item.video_url ?? "",
    };
    const last = day.exercises[day.exercises.length - 1];
    const isEmptyRow = last && !last.name?.trim() && !last.sets && !last.reps && !last.weight;
    const exercises = isEmptyRow
      ? day.exercises.map((ex, i) =>
        i === day.exercises.length - 1
          ? {
            ...filled,
            // Wartości już wpisane przez trenera zostają nietknięte.
            tempo: ex.tempo || filled.tempo,
            comment: ex.comment || filled.comment,
            video_url: ex.video_url || filled.video_url,
            rest: ex.rest || "",
          }
          : ex)
      : [...day.exercises, filled];
    setDay(dayIndex, { ...day, exercises });
  }

  /** Wstawienie propozycji asystenta: DOKŁADAMY dni, nigdy nie kasujemy
   * pracy trenera, i zawsze zostawiamy drogę powrotu (migawka do cofnięcia).
   * Bez przeładowania i bez przewijania — zmiana jest ogłaszana aria-live. */
  function insertAssistantDays(incoming: PlanDay[], label: string) {
    setUndoDays(snapshot(days));
    setDays(appendDays(days, incoming));
    setAssistantNote(`${label} Nic nie zostało jeszcze zapisane.`);
  }

  /** Pojedyncze ćwiczenie ze ścieżki lokalnej — do ostatniego dnia. */
  function insertAssistantExercise(exercise: Exercise, label: string) {
    setUndoDays(snapshot(days));
    const target = days.length ? days.length - 1 : 0;
    const base = days.length ? days : [emptyDay()];
    const day = base[target];
    const last = day.exercises[day.exercises.length - 1];
    const isEmptyRow = last && !last.name?.trim() && !last.sets && !last.reps;
    setDays(base.map((d, i) => (i !== target ? d : {
      ...d,
      exercises: isEmptyRow
        ? [...d.exercises.slice(0, -1), exercise]
        : [...d.exercises, exercise],
    })));
    setAssistantNote(`${label} Nic nie zostało jeszcze zapisane.`);
  }

  function undoInsert() {
    if (!undoDays) return;
    setDays(undoDays);
    setUndoDays(null);
    setAssistantNote("Cofnięto wstawienie — edytor wrócił do poprzedniego stanu.");
  }

  /** Tekst z kartki -> nowy dzień do ręcznej obróbki.
   *
   * ŚWIADOMIE nie zgadujemy serii, powtórzeń ani ciężarów: jedna linia to
   * jedna nazwa ćwiczenia do poprawienia. Plan zapisuje dopiero trener
   * przyciskiem „Zapisz" — samo przepisanie niczego nie utrwala. */
  function insertFromPhoto(text: string) {
    const names = linesToExerciseNames(text);
    if (!names.length) return false;
    setDays([
      ...days,
      {
        name: "Z kartki (do uporządkowania)",
        weekday: null,
        exercises: names.map((name) => ({ ...emptyExercise(), name })),
      },
    ]);
    setOcrNote(
      `Dodano dzień z ${names.length} pozycjami przepisanymi ze zdjęcia. `
      + "Popraw nazwy, serie i powtórzenia — nic nie zostało jeszcze zapisane."
    );
    setOcrOpen(false);
    return true;
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const cleanDays = days
      .filter((d) => d.name.trim())
      .map((d) => ({ ...d, exercises: d.exercises.filter((ex) => ex.name.trim()) }));
    try {
      if (existingPlan) {
        await api.post(`/api/plans/${existingPlan.id}/versions`, { reason, days: cleanDays });
      } else {
        await api.post("/api/plans", {
          client_id: clientId, title, version: { reason, days: cleanDays },
        });
      }
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card card--accent" onSubmit={save}>
      <h2>{existingPlan ? `Nowa wersja: ${existingPlan.title}` : "Nowy plan treningowy"}</h2>
      {!existingPlan && (
        <>
          <label htmlFor="pe-title">Nazwa planu</label>
          <input id="pe-title" required value={title} onChange={(e) => setTitle(e.target.value)} />
        </>
      )}
      <label htmlFor="pe-reason">Powód {existingPlan ? "zmiany" : "utworzenia"} (obowiązkowy — trafia do historii)</label>
      <input id="pe-reason" required value={reason} onChange={(e) => setReason(e.target.value)}
        placeholder="np. progresja po raporcie z tygodnia 3" />
      <div className="row" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <button type="button" className="btn btn--ghost btn--small"
          aria-expanded={assistantOpen} onClick={() => setAssistantOpen(!assistantOpen)}>
          {assistantOpen ? "Zamknij asystenta" : "Asystent: szkic planu z bazy"}
        </button>
        <button type="button" className="btn btn--ghost btn--small"
          aria-expanded={ocrOpen} onClick={() => setOcrOpen(!ocrOpen)}>
          {ocrOpen ? "Zamknij przepisywanie" : "Przepisz ze zdjęcia (kartka z planem)"}
        </button>
        {undoDays && (
          <button type="button" className="btn btn--ghost btn--small" onClick={undoInsert}>
            Cofnij wstawienie
          </button>
        )}
      </div>
      <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }}>
        {assistantNote ?? ""}
      </p>
      {assistantOpen && (
        <PlanAssistant
          clientId={clientId}
          onInsertDays={insertAssistantDays}
          onInsertExercise={insertAssistantExercise}
          canUndo={undoDays !== null}
          onUndo={undoInsert}
          onClose={() => setAssistantOpen(false)}
        />
      )}
      <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }}>
        {ocrNote ?? ""}
      </p>
      {ocrOpen && (
        <OcrCapture
          purpose="PLAN"
          clientId={clientId ?? undefined}
          title="Plan z kartki"
          hint={"Zrób zdjęcie kartki z planem. Rozpoznany tekst wstawimy jako "
            + "nowy dzień treningowy — każda linia jako osobna pozycja do "
            + "poprawienia. Zapisujesz go dopiero przyciskiem na dole."}
          approveLabel="Wstaw do edytora planu"
          onApprove={(_task, text) => insertFromPhoto(text)}
          onClose={() => setOcrOpen(false)}
        />
      )}
      {days.map((day, di) => (
        <div key={di} className="card" style={{ marginTop: 10 }}>
          <div className="field-row">
            <div>
              <label htmlFor={`pe-day-name-${di}`}>Nazwa dnia</label>
              <input id={`pe-day-name-${di}`} value={day.name} onChange={(e) => setDay(di, { ...day, name: e.target.value })}
                placeholder="np. Trening A — góra" />
            </div>
            <div>
              <label htmlFor={`pe-day-weekday-${di}`}>Dzień tygodnia</label>
              <select id={`pe-day-weekday-${di}`} value={day.weekday ?? ""}
                onChange={(e) => setDay(di, { ...day, weekday: e.target.value ? Number(e.target.value) : null })}>
                <option value="">— dowolny —</option>
                {WEEKDAYS.map((w, i) => (
                  <option key={i} value={i + 1}>{w}</option>
                ))}
              </select>
            </div>
          </div>
          {day.exercises.map((ex, ei) => (
            <div key={ei} style={{ borderTop: "1px solid var(--border)", paddingTop: 8, marginTop: 8 }}>
              <label htmlFor={`pe-ex-${di}-${ei}`}>
                Ćwiczenie {ei + 1}
                {ex.exercise_id && <span className="badge" style={{ marginLeft: 8 }}>z bazy</span>}
              </label>
              <input id={`pe-ex-${di}-${ei}`} value={ex.name} placeholder="nazwa ćwiczenia"
                onChange={(e) => {
                  const exs = [...day.exercises];
                  // Ręczna zmiana nazwy = własny wpis trenera: odpinamy
                  // link do karty z bazy, żeby nie wskazywał czegoś innego.
                  exs[ei] = {
                    ...ex,
                    name: e.target.value,
                    exercise_id: e.target.value === ex.name ? ex.exercise_id : null,
                  };
                  setDay(di, { ...day, exercises: exs });
                }} />
              <div className="field-row-3" style={{ marginTop: 6 }}>
                {(["sets", "reps", "weight"] as const).map((f) => (
                  <input key={f} value={(ex[f] as string) ?? ""}
                    aria-label={`Ćwiczenie ${ei + 1} — ${{ sets: "serie", reps: "powtórzenia", weight: "ciężar" }[f]}`}
                    placeholder={{ sets: "serie", reps: "powt.", weight: "ciężar" }[f]}
                    onChange={(e) => {
                      const exs = [...day.exercises];
                      exs[ei] = { ...ex, [f]: e.target.value };
                      setDay(di, { ...day, exercises: exs });
                    }} />
                ))}
              </div>
              <div className="field-row" style={{ marginTop: 6 }}>
                <input value={ex.tempo ?? ""} placeholder="tempo (np. 2011)"
                  aria-label={`Ćwiczenie ${ei + 1} — tempo`}
                  onChange={(e) => {
                    const exs = [...day.exercises];
                    exs[ei] = { ...ex, tempo: e.target.value };
                    setDay(di, { ...day, exercises: exs });
                  }} />
                <input value={ex.rest ?? ""} placeholder="przerwa (np. 120 s)"
                  aria-label={`Ćwiczenie ${ei + 1} — przerwa`}
                  onChange={(e) => {
                    const exs = [...day.exercises];
                    exs[ei] = { ...ex, rest: e.target.value };
                    setDay(di, { ...day, exercises: exs });
                  }} />
              </div>
              <input style={{ marginTop: 6 }} value={ex.comment ?? ""} placeholder="komentarz"
                aria-label={`Ćwiczenie ${ei + 1} — komentarz`}
                onChange={(e) => {
                  const exs = [...day.exercises];
                  exs[ei] = { ...ex, comment: e.target.value };
                  setDay(di, { ...day, exercises: exs });
                }} />
              <input style={{ marginTop: 6 }} value={ex.video_url ?? ""}
                aria-label={`Ćwiczenie ${ei + 1} — link do filmu instruktażowego`}
                placeholder="link do filmu instruktażowego (https://…)"
                onChange={(e) => {
                  const exs = [...day.exercises];
                  exs[ei] = { ...ex, video_url: e.target.value };
                  setDay(di, { ...day, exercises: exs });
                }} />
            </div>
          ))}
          <div className="row" style={{ marginTop: 8, flexWrap: "wrap" }}>
            <button type="button" className="btn btn--small"
              ref={(node) => { pickerButtons.current[di] = node; }}
              aria-expanded={pickerDay === di}
              onClick={() => setPickerDay(pickerDay === di ? null : di)}>
              {pickerDay === di ? "Zamknij bazę ćwiczeń" : "Wybierz z bazy ćwiczeń"}
            </button>
            <button type="button" className="btn btn--ghost btn--small"
              onClick={() => setDay(di, { ...day, exercises: [...day.exercises, emptyExercise()] })}>
              + ćwiczenie (wpisz ręcznie)
            </button>
            <button type="button" className="btn btn--danger btn--small"
              onClick={() => setDays(days.filter((_, j) => j !== di))}>
              usuń dzień
            </button>
          </div>
          {pickerDay === di && (
            <ExercisePicker idPrefix={`pe-${di}`}
              onPick={(item) => addFromLibrary(di, item)}
              onClose={() => { setPickerDay(null); pickerButtons.current[di]?.focus(); }} />
          )}
        </div>
      ))}
      <div className="row" style={{ marginTop: 10 }}>
        <button type="button" className="btn btn--ghost btn--small"
          onClick={() => setDays([...days, emptyDay()])}>
          + dzień treningowy
        </button>
      </div>
      <ErrorBox error={error} />
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={busy}>
          {busy ? "Zapisywanie…" : existingPlan ? "Zapisz nową wersję" : "Utwórz plan"}
        </button>
        <button type="button" className="btn btn--ghost" onClick={onCancel}>Anuluj</button>
      </div>
    </form>
  );
}

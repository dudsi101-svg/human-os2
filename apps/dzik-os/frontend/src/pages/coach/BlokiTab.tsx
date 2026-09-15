import { FormEvent, useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, Spinner } from "../../components";
import {
  BLOCK_KIND_LABELS, BLOCK_VARIANT_LABELS, BlockItem, BlockKind, EXERCISE_LEVEL_LABELS, ExerciseBlockRow,
  GOAL_LABELS, GOAL_KEYS, MACHINE_LABELS,
} from "../../types";

/**
 * Zakładka „Bloki” w Szablonach (0.73.0): katalog bloków rozgrzewki (3 poziomy
 * × 3 warianty), aerobów/cardio (3 cele × 3 poziomy, od 0.76.0 — preset liczy
 * serwer tym samym silnikiem co panel suwaków, bez danych klienta) i
 * rozciągania (3 warianty) trenera. „Dodaj wbudowane” ładuje zestaw z pakietu
 * (idempotentnie; treść DO PRZEGLĄDU TRENERA), edycja pozycji w prostym
 * formularzu (jedna linia = „nazwa | dawka | notatka”), archiwizacja zamiast
 * kasowania. Bloki wstawia się do dnia w edytorze planu albo przy przypisywaniu
 * planu klientowi („Przypisz plan”).
 */

const BLOKI = "/api/coach/exercise-blocks";

function liniaDoPozycji(linia: string): BlockItem | null {
  const [name, dose, note] = linia.split("|").map((x) => x.trim());
  if (!name) return null;
  return { name, dose: dose || null, note: note || null, exercise_id: null };
}

function pozycjeDoTekstu(items: BlockItem[]): string {
  return items.map((i) => [i.name, i.dose ?? "", i.note ?? ""].join(" | ").replace(/( \| )+$/, "")).join("\n");
}

function FormularzBloku({ blok, onSaved, onCancel }: { blok: ExerciseBlockRow | null; onSaved: () => void; onCancel: () => void }) {
  const [name, setName] = useState(blok?.name ?? "");
  const [kind, setKind] = useState<BlockKind>(blok?.kind ?? "WARMUP");
  const [level, setLevel] = useState(blok?.level ?? "POCZATKUJACY");
  const [variant, setVariant] = useState<"G" | "D" | "C">(blok?.variant ?? "C");
  // CARDIO (0.76.0): cel dominujący + urządzenia; liczby liczy serwer.
  const [goal, setGoal] = useState<string>(blok?.goal ?? "regeneracja");
  const [machines, setMachines] = useState<string[]>(blok?.cardio?.machines ?? ["rowerek", "bieznia", "wioslarz"]);
  const [duration, setDuration] = useState(blok?.duration_min ? String(blok.duration_min) : "");
  const [tekst, setTekst] = useState(blok ? pozycjeDoTekstu(blok.items) : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Przegląd PR #79, P1: pozycje opisowe i czas bloku aerobowego liczy serwer
  // z presetu. Po zmianie rodzaju, celu, poziomu albo urządzeń stara treść
  // przestaje pasować do nowych liczb (blok mówiłby „RPE 4–5, 40 min”, a preset
  // liczyłby „RPE 2–3, 25 min”) i taka sprzeczność szła migawką do planu klienta.
  // Dlatego przy każdej zmianie tych pól czyścimy oba pola — puste = serwer
  // wypełnia presetem. Pierwsze wejście w formularz (wartości z bloku) zostaje.
  const [osie, setOsie] = useState(`${blok?.kind ?? "WARMUP"}|${blok?.goal ?? ""}|${blok?.level ?? ""}|${(blok?.cardio?.machines ?? []).join(",")}`);
  useEffect(() => {
    const teraz = `${kind}|${kind === "CARDIO" ? goal : ""}|${kind === "STRETCH" ? "" : level}|${kind === "CARDIO" ? machines.join(",") : ""}`;
    if (teraz === osie) return;
    setOsie(teraz);
    if (kind === "CARDIO") { setTekst(""); setDuration(""); }
  }, [kind, goal, level, machines, osie]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const items = tekst.split("\n").map(liniaDoPozycji).filter((x): x is BlockItem => x !== null);
    // Pozycje z karty (exercise_id) zostają, gdy nazwa się nie zmieniła.
    const stare = new Map((blok?.items ?? []).map((i) => [i.name, i.exercise_id ?? null]));
    const body = { name, kind, level: kind === "STRETCH" ? null : level, variant: kind === "CARDIO" ? null : variant,
      duration_min: duration ? Number(duration) : null,
      items: items.map((i) => ({ ...i, exercise_id: stare.get(i.name) ?? null })),
      ...(kind === "CARDIO" ? { goal, machines } : {}) };
    try {
      if (blok) await api.put(`${BLOKI}/${blok.id}`, body);
      else await api.post(BLOKI, body);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card card--accent" onSubmit={save} data-testid="blok-formularz">
      <h2>{blok ? `Edycja: ${blok.name}` : "Nowy blok"}</h2>
      <label htmlFor="bl-name">Nazwa</label>
      <input id="bl-name" required value={name} onChange={(e) => setName(e.target.value)} />
      <div className="field-row-3" style={{ marginTop: 6 }}>
        <div>
          <label htmlFor="bl-kind">Rodzaj</label>
          <select id="bl-kind" value={kind} onChange={(e) => setKind(e.target.value as BlockKind)}>
            {Object.entries(BLOCK_KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          {kind === "CARDIO" ? (
            <>
              <label htmlFor="bl-goal">Cel dominujący</label>
              <select id="bl-goal" value={goal} onChange={(e) => setGoal(e.target.value)}>
                {GOAL_KEYS.map((k) => <option key={k} value={k}>{GOAL_LABELS[k]}</option>)}
              </select>
            </>
          ) : (
            <>
              <label htmlFor="bl-variant">Wariant</label>
              <select id="bl-variant" value={variant} onChange={(e) => setVariant(e.target.value as "G" | "D" | "C")}>
                {Object.entries(BLOCK_VARIANT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </>
          )}
        </div>
        <div>
          <label htmlFor="bl-level">Poziom</label>
          <select id="bl-level" value={level} disabled={kind === "STRETCH"} onChange={(e) => setLevel(e.target.value)}>
            {Object.entries(EXERCISE_LEVEL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>
      {kind === "CARDIO" && (
        <fieldset className="list-editor" style={{ marginTop: 6 }}>
          <legend>Dozwolone urządzenia (klient wybiera w dniu treningu)</legend>
          {Object.entries(MACHINE_LABELS).map(([k, v]) => (
            <label key={k} className="row" style={{ alignItems: "center", minHeight: 44 }}>
              <input type="checkbox" checked={machines.includes(k)}
                onChange={(e) => setMachines(e.target.checked ? [...machines, k] : machines.filter((m) => m !== k))} />
              <span>{v}</span>
            </label>
          ))}
          <p className="dim" style={{ fontSize: "0.85rem", margin: "4px 0 0" }}>
            Zakres tętna, RPE, czas i strukturę liczy silnik z celu i poziomu — bez danych klienta (bez ud./min).
            Puste pozycje niżej = opis wygenerowany automatycznie. Czas: pusty = z silnika.
          </p>
        </fieldset>
      )}
      <label htmlFor="bl-duration" style={{ marginTop: 6 }}>Czas (min)</label>
      <input id="bl-duration" type="number" min={1} max={60} value={duration} onChange={(e) => setDuration(e.target.value)} />
      <label htmlFor="bl-items" style={{ marginTop: 6 }}>Pozycje — jedna w linii: nazwa | dawka | notatka</label>
      <textarea id="bl-items" rows={7} value={tekst} onChange={(e) => setTekst(e.target.value)}
        placeholder={"Marsz w miejscu z wysokim kolanem | 3 min | RPE 3–4\nKrążenia ramion | 2×10"} />
      <ErrorBox error={error} />
      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn" disabled={busy}>{busy ? "Zapisywanie…" : "Zapisz blok"}</button>
        <button type="button" className="btn btn--ghost" onClick={onCancel}>Anuluj</button>
      </div>
    </form>
  );
}

export default function BlokiTab() {
  const [items, setItems] = useState<ExerciseBlockRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"ACTIVE" | "all">("ACTIVE");
  const [note, setNote] = useState<string | null>(null);
  const [edit, setEdit] = useState<ExerciseBlockRow | null | "nowy">(null);

  const load = () => {
    setError(null);
    api.get<{ items: ExerciseBlockRow[] }>(`${BLOKI}?status=${status}`)
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  };
  useEffect(load, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function wbudowane() {
    setNote(null);
    try {
      const r = await api.post<{ created: number; skipped: number; items_without_card: number }>(`${BLOKI}/load-builtin`, {});
      setNote(r.created
        ? `Dodano ${r.created} wbudowanych bloków (pominięto ${r.skipped} już obecnych). Treść jest do Twojego przeglądu przed użyciem u klientów.`
        : `Wszystkie wbudowane bloki (${r.skipped}) są już w Twoim katalogu.`);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function zmienStatus(b: ExerciseBlockRow) {
    try {
      await api.post(`${BLOKI}/${b.id}/status`, { status: b.status === "ACTIVE" ? "ARCHIVED" : "ACTIVE" });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error && !items) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;

  return (
    <div data-testid="bloki-tab">
      <div className="card">
        <div className="row row--between">
          <div>
            <b>Bloki rozgrzewki, aerobów i rozciągania</b>
            <div className="dim" style={{ fontSize: "0.85rem" }}>
              9 rozgrzewek (3 poziomy × góra/dół/całe ciało), 9 bloków aerobów (3 cele × 3 poziomy — preset z silnika
              bez danych klienta) i 3 bloki rozciągania po treningu. Wstawiasz je do dnia w edytorze planu albo
              dokładasz przy przypisywaniu planu klientowi („Przypisz plan” w karcie klienta — jak szablon);
              plan niesie migawkę treści, więc późniejsza edycja bloku nie zmienia opublikowanych planów.
              Treść wbudowana jest <b>do Twojego przeglądu</b> — to propozycja, nie zalecenie.
            </div>
          </div>
        </div>
        <div className="row" style={{ marginTop: 8, flexWrap: "wrap" }}>
          <button type="button" className="btn btn--small" onClick={wbudowane}>Dodaj wbudowane</button>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => setEdit("nowy")}>+ Nowy blok</button>
          <label className="row" style={{ alignItems: "center" }}>
            <input type="checkbox" checked={status === "all"} onChange={(e) => setStatus(e.target.checked ? "all" : "ACTIVE")} />
            <span>pokaż zarchiwizowane</span>
          </label>
        </div>
        <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }}>{note ?? ""}</p>
        <ErrorBox error={error} />
      </div>
      {edit && (
        <FormularzBloku blok={edit === "nowy" ? null : edit} onSaved={() => { setEdit(null); load(); }} onCancel={() => setEdit(null)} />
      )}
      {items.length === 0 && <p className="dim">Brak bloków — kliknij „Dodaj wbudowane” albo utwórz własny.</p>}
      {items.map((b) => (
        <div className="card" key={b.id} data-testid="blok-karta">
          <div className="row row--between">
            <div>
              <b>{b.name}</b>{" "}
              <span className="badge">{b.kind_label}</span>{" "}
              {b.variant_label && <span className="badge">{b.variant_label}</span>}
              {b.goal_label && <span className="badge">{b.goal_label}</span>}
              {b.level && <> <span className="badge">{EXERCISE_LEVEL_LABELS[b.level] ?? b.level}</span></>}
              {b.status === "ARCHIVED" && <> <span className="badge badge--warn">zarchiwizowany</span></>}
              <div className="meta">{b.duration_min ? `≈${b.duration_min} min · ` : ""}{b.items.length} pozycji · źródło: {b.source}</div>
            </div>
            <div className="row" style={{ gap: 6 }}>
              <button type="button" className="btn btn--ghost btn--small" onClick={() => setEdit(b)}>Edytuj</button>
              <button type="button" className={`btn btn--small ${b.status === "ACTIVE" ? "btn--danger" : ""}`} onClick={() => zmienStatus(b)}>
                {b.status === "ACTIVE" ? "Archiwizuj" : "Przywróć"}
              </button>
            </div>
          </div>
          <ol style={{ margin: "6px 0 0", paddingLeft: 20, fontSize: "0.9rem" }}>
            {b.items.map((it, i) => (
              <li key={i}>{it.name}{it.dose && <> — <b>{it.dose}</b></>}{it.note && <span className="dim"> ({it.note})</span>}
                {!it.exercise_id && b.kind !== "CARDIO" && it.name.indexOf("wprowadzająca") < 0 && <span className="dim"> · bez karty w bazie</span>}</li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}

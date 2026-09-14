import { useEffect, useRef, useState } from "react";
import { Icon } from "./components";
import { RolaOpisu } from "./nazwy";
import { OpisCwiczenia } from "./opisCwiczenia";
import { zGoalMix } from "./suwaki";
import {
  BLOCK_KIND_LABELS,
  BLOCK_VARIANT_LABELS,
  CardioItem,
  CardioMachineParams,
  Exercise,
  EXERCISE_LEVEL_LABELS,
  GOAL_KEYS,
  GOAL_SHORT,
  MACHINE_LABELS,
} from "./types";
import { Dlaczego } from "./wiedza/Dlaczego";

/**
 * Wspólny renderer pozycji planu (0.73.0) dla „Dzisiaj” i „Planu”: siłowa
 * (jak dotąd), blok rozgrzewki/rozciągania (rozwijana lista z dawką) i
 * cardio z suwakami (paski wag, urządzenie, „zacznij od…”, zakres tętna
 * i RPE + test mowy, czas, struktura z timerem, zastrzeżenie, „Dlaczego?”).
 * Nic tu nie liczy — pokazuje to, co trener opublikował.
 */

export const KIND_BADGE: Record<string, string> = {
  warmup_block: "rozgrzewka",
  stretch_block: "rozciąganie",
  cardio: "cardio",
};

export function rodzajPozycji(ex: Pick<Exercise, "kind">): "strength" | "warmup_block" | "stretch_block" | "cardio" {
  return ex.kind && ex.kind !== "strength" ? ex.kind : "strength";
}

/** "120 s" / "2 min" / "90" → sekundy (null, gdy nie da się odczytać). */
export function parseRestSeconds(rest: string | null | undefined): number | null {
  if (!rest) return null;
  const m = rest.replace(",", ".").match(/([\d.]+)\s*(min|m\b)?/i);
  if (!m) return null;
  const value = parseFloat(m[1]);
  if (!isFinite(value) || value <= 0) return null;
  return Math.round(m[2] ? value * 60 : value);
}

/** Timer przerwy/odcinka — czysto lokalny, niczego nie zapisuje. */
export function RestTimer({ seconds, label = "przerwa" }: { seconds: number; label?: string }) {
  const [left, setLeft] = useState<number | null>(null);
  const interval = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (interval.current) clearInterval(interval.current); }, []);

  function start() {
    if (interval.current) clearInterval(interval.current);
    setLeft(seconds);
    interval.current = setInterval(() => {
      setLeft((prev) => {
        if (prev === null) return null;
        if (prev <= 1) {
          if (interval.current) clearInterval(interval.current);
          if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function stop() {
    if (interval.current) clearInterval(interval.current);
    setLeft(null);
  }

  if (left === null) {
    return (
      <button type="button" className="btn btn--ghost btn--small" onClick={start}>
        <Icon name="timer" size={16} /> {label} {seconds >= 60 ? `${Math.round(seconds / 60)} min` : `${seconds} s`}
      </button>
    );
  }
  const done = left === 0;
  return (
    <button
      type="button"
      className="btn btn--small"
      style={done
        ? { background: "var(--accent)", color: "var(--accent-ink)" }
        : { background: "var(--bg-raised)", color: "var(--accent)", fontVariantNumeric: "tabular-nums" }}
      onClick={done ? () => start() : stop}
    >
      {done
        ? "✓ Koniec — jeszcze raz?"
        : <><Icon name="timer" size={16} /> {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")} (stop)</>}
    </button>
  );
}

/** Trzy paski wag celów — odczyt, bez suwaków (klient nic nie przestawia). */
export function PaskiCelow({ mix, testid }: { mix: CardioItem["goal_mix"]; testid?: string }) {
  const wagi = zGoalMix(mix);
  return (
    <div data-testid={testid} aria-label={GOAL_KEYS.map((k, i) => `${GOAL_SHORT[k]} ${wagi[i]} %`).join(", ")}
      style={{ display: "grid", gap: 4, marginTop: 6 }}>
      {GOAL_KEYS.map((k, i) => (
        <div key={k} className="row" style={{ gap: 8 }}>
          <span style={{ width: 96, fontSize: "0.8rem" }}>{GOAL_SHORT[k]}</span>
          <div aria-hidden style={{ flex: 1, height: 8, background: "var(--bg-raised)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ width: `${wagi[i]}%`, height: "100%", background: "var(--accent)" }} />
          </div>
          <span style={{ width: 40, textAlign: "right", fontSize: "0.8rem", fontVariantNumeric: "tabular-nums" }}>{wagi[i]} %</span>
        </div>
      ))}
    </div>
  );
}

function zakres(r: [number, number] | null | undefined, jednostka: string): string | null {
  if (!r) return null;
  return `${r[0]}–${r[1]} ${jednostka}`;
}

/** Blok rozgrzewki/rozciągania: rozwijana lista pozycji z dawką. */
export function PozycjaBloku({ ex, otwarty = false, rola = "klient", powrot, testid }: {
  ex: Exercise; otwarty?: boolean; rola?: RolaOpisu; powrot?: string | null; testid?: string;
}) {
  const [open, setOpen] = useState(otwarty);
  const b = ex.block;
  if (!b) return <div className="exercise"><div><b>{ex.name}</b></div></div>;
  const opis = [BLOCK_KIND_LABELS[b.kind] ?? b.kind, b.variant ? BLOCK_VARIANT_LABELS[b.variant] : null,
    b.level ? EXERCISE_LEVEL_LABELS[b.level] ?? b.level : null, b.duration_min ? `≈${b.duration_min} min` : null]
    .filter(Boolean).join(" · ");
  return (
    <div className="exercise" data-testid={testid}>
      <div>
        <b>{ex.name}</b> <span className="badge">{KIND_BADGE[rodzajPozycji(ex)]}</span>
        <div className="meta">{opis}</div>
        <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
          aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Zwiń pozycje" : `Pokaż pozycje (${b.items.length})`}
        </button>
        {open && (
          <ol style={{ margin: "6px 0 0", paddingLeft: 20 }}>
            {b.items.map((it, i) => (
              <li key={i} style={{ fontSize: "0.9rem", marginBottom: 2 }}>
                {it.name}{it.dose && <> — <b>{it.dose}</b></>}
                {it.note && <span className="dim"> ({it.note})</span>}
                {/* Opis z bazy (0.75.0): po id, a bez id po nazwie pozycji. */}
                <OpisCwiczenia exerciseId={it.exercise_id} name={it.name} rola={rola} powrot={powrot} />
              </li>
            ))}
          </ol>
        )}
      </div>
      <div className="meta">{b.duration_min ? `${b.duration_min} min` : ""}</div>
    </div>
  );
}

function ParametryUrzadzenia({ p, interwaly }: { p: CardioMachineParams; interwaly: boolean }) {
  return (
    <div className="meta" style={{ marginTop: 4 }}>
      Zacznij od: {p.tempo_name} <b>{p.tempo}</b> {p.tempo_unit}, {p.load_name} <b>{p.load}</b>
      {p.load_unit && p.load_unit !== "poziom" ? ` ${p.load_unit}` : ""}
      {interwaly && p.rest_tempo && <> · w przerwie: {p.tempo_name} {p.rest_tempo}, {p.load_name} {p.rest_load}</>}
      {" "}— dojdź do tętna / RPE z zakresu, urządzenia różnią się kalibracją.
    </div>
  );
}

/** Pozycja cardio u klienta. `machine`/`onMachine` — wybór urządzenia w dniu treningu (gdy lista). */
export function PozycjaCardio({ ex, machine, onMachine, dlaczego, kompakt = false, testid }: {
  ex: Exercise;
  machine?: string | null;
  onMachine?: (m: string) => void;
  dlaczego?: { plan_id: string; plan_revision: number; target_id: string };
  kompakt?: boolean;
  testid?: string;
}) {
  const c = ex.cardio;
  const rx = c?.prescription;
  // Strażnik: pozycja bez pełnej propozycji (stara/uszkodzona treść) nie wywraca widoku planu.
  if (!c || !rx || !Array.isArray(rx.hr_pct_range) || !rx.structure || !Array.isArray(rx.rpe_range)) {
    return (
      <div className="exercise" data-testid={testid}>
        <div><b>{ex.name}</b> <span className="badge badge--accent">{KIND_BADGE.cardio}</span>
          <div className="meta">Pozycja cardio bez pełnej propozycji — zapytaj trenera o zakres tętna i czas.</div></div>
      </div>
    );
  }
  const machines = Array.isArray(c.machines) && c.machines.length ? c.machines : ["rowerek"];
  const paramsList = Array.isArray(rx.machine_params) ? rx.machine_params : [];
  // Cardio z bloku (0.76.0): nagłówek jak u bloków (rodzaj · poziom · ≈min) + pozycje opisowe.
  const blok = ex.block && ex.block.kind === "CARDIO" ? ex.block : null;
  const opisBloku = blok
    ? [BLOCK_KIND_LABELS.CARDIO, blok.level ? EXERCISE_LEVEL_LABELS[blok.level] ?? blok.level : null,
      blok.duration_min ? `≈${blok.duration_min} min` : null].filter(Boolean).join(" · ")
    : null;
  const wybrane = machine && machines.includes(machine) ? machine : machines[0];
  const params = paramsList.find((p) => p.machine === wybrane) ?? paramsList[0];
  const interwaly = rx.structure.type === "interwaly";
  // Bez ud./min (brak wieku albo tryb bez tętna — powód nie jest zapisywany): prowadzi RPE i test mowy.
  const bezTetna = !rx.hr_bpm_range;
  const tetno = bezTetna
    ? `${zakres(rx.hr_pct_range, "% HRmax")} (orientacyjnie) — prowadź według RPE i testu mowy`
    : [zakres(rx.hr_bpm_range, "ud./min"), `${zakres(rx.hr_pct_range, "% HRmax")}`].filter(Boolean).join(" · ");
  return (
    <div className="exercise" data-testid={testid} style={{ gridTemplateColumns: "1fr" }}>
      <div>
        <b>{ex.name}</b> <span className="badge badge--accent">{KIND_BADGE.cardio}</span>
        {blok && <span className="badge" style={{ marginLeft: 6 }}>z bloku</span>}
        {opisBloku && <div className="meta" data-testid={testid ? `${testid}-blok` : undefined}>{opisBloku}</div>}
        {blok && blok.items.length > 0 && (
          <ol style={{ margin: "4px 0 0", paddingLeft: 20, fontSize: "0.85rem" }}>
            {blok.items.map((it, i) => (
              <li key={i}>{it.name}{it.dose && <> — <b>{it.dose}</b></>}{it.note && <span className="dim"> ({it.note})</span>}</li>
            ))}
          </ol>
        )}
        <PaskiCelow mix={c.goal_mix} testid={testid ? `${testid}-cele` : undefined} />
        {machines.length > 1 && onMachine ? (
          <div style={{ marginTop: 8 }}>
            <label htmlFor={`${testid ?? "cardio"}-urzadzenie`}>Urządzenie na dziś</label>
            <select id={`${testid ?? "cardio"}-urzadzenie`} value={wybrane} onChange={(e) => onMachine(e.target.value)}>
              {machines.map((m) => <option key={m} value={m}>{MACHINE_LABELS[m] ?? m}</option>)}
            </select>
          </div>
        ) : (
          <div className="meta" style={{ marginTop: 6 }}>
            Urządzenie: {machines.map((m) => MACHINE_LABELS[m] ?? m).join(" / ")}
          </div>
        )}
        {params && <ParametryUrzadzenia p={params} interwaly={interwaly} />}
        <div style={{ marginTop: 8, display: "grid", gap: 2, fontSize: "0.9rem" }} data-testid={testid ? `${testid}-zakresy` : undefined}>
          <div><b>Tętno:</b> {tetno}{interwaly && rx.hr_pct_rest_range && (
            <> (praca) · przerwa {(!bezTetna && zakres(rx.hr_bpm_rest_range, "ud./min")) || zakres(rx.hr_pct_rest_range, "% HRmax")}</>)}</div>
          <div><b>RPE:</b> {rx.rpe_range[0]}–{rx.rpe_range[1]} / 10{interwaly && rx.rpe_rest_range && <> (praca) · {rx.rpe_rest_range[0]}{rx.rpe_rest_range[1] !== rx.rpe_rest_range[0] ? `–${rx.rpe_rest_range[1]}` : ""} w przerwie</>} · <b>test mowy:</b> {rx.talk_test}</div>
          <div><b>Czas:</b> {rx.duration_min} min · <b>struktura:</b> {rx.structure.label}</div>
          {rx.kcal_estimate != null && params?.kcal_estimate != null && (
            <div className="dim">Szacowany wydatek: ok. {params.kcal_estimate} kcal (tabele MET — przybliżenie).</div>
          )}
        </div>
        {!kompakt && (
          <div className="row" style={{ marginTop: 6, gap: 6 }}>
            {interwaly ? (
              <>
                <RestTimer seconds={rx.structure.work_min * 60} label="praca" />
                <RestTimer seconds={rx.structure.rest_min * 60} label="przerwa" />
              </>
            ) : (
              <RestTimer seconds={rx.duration_min * 60} label="czas" />
            )}
          </div>
        )}
        <p className="dim" style={{ margin: "6px 0 0", fontSize: "0.8rem" }}>
          {(rx.hr_bpm_range
              ? "Zakres, nie jedna liczba: tętno z wzoru wiekowego ma błąd ±10 ud./min — kieruj się też RPE i testem mowy. "
              : "Bez tętna prowadź wysiłek według RPE i testu mowy — to równoprawny wariant. ")
              + ((c.goal_mix?.redukcja ?? 0) > 0
                ? "Udział tłuszczu jako paliwa w strefie nie przesądza o utracie tkanki — decyduje bilans energii w skali tygodni."
                : "To propozycja trenera — zakres, nie jedna liczba.")}
        </p>
        {dlaczego && (
          <div style={{ marginTop: 6 }}>
            <Dlaczego naglowek={`${ex.name} — skąd te liczby`} etykieta="Dlaczego takie cardio?"
              cel={{ plan_id: dlaczego.plan_id, plan_revision: dlaczego.plan_revision,
                target_type: "cardio_prescription", target_id: dlaczego.target_id }} />
          </div>
        )}
      </div>
    </div>
  );
}

/** Jednolinijkowy opis pozycji nie-siłowej do widoków trenera (odczyt). */
export function opisPozycji(ex: Exercise): string {
  const rodzaj = rodzajPozycji(ex);
  if (rodzaj === "cardio" && ex.cardio) {
    const rx = ex.cardio.prescription;
    const w = zGoalMix(ex.cardio.goal_mix);
    const urz = (Array.isArray(ex.cardio.machines) ? ex.cardio.machines : []).map((m) => MACHINE_LABELS[m] ?? m).join(" / ");
    if (!rx || !Array.isArray(rx.hr_pct_range) || !Array.isArray(rx.rpe_range) || !rx.structure) {
      return `${urz} · R ${w[0]} % / W ${w[1]} % / G ${w[2]} % · bez pełnej propozycji`;
    }
    return (ex.block?.kind === "CARDIO" ? "z bloku · " : "")
      + `${urz} · R ${w[0]} % / W ${w[1]} % / G ${w[2]} % · `
      + `${rx.hr_pct_range[0]}–${rx.hr_pct_range[1]} % HRmax · RPE ${rx.rpe_range[0]}–${rx.rpe_range[1]} · ${rx.duration_min} min · ${rx.structure.label}`;
  }
  if ((rodzaj === "warmup_block" || rodzaj === "stretch_block") && ex.block) {
    const b = ex.block;
    return [b.variant ? BLOCK_VARIANT_LABELS[b.variant] : null, b.level ? EXERCISE_LEVEL_LABELS[b.level] ?? b.level : null,
      b.duration_min ? `≈${b.duration_min} min` : null, `${b.items.length} pozycji`].filter(Boolean).join(" · ");
  }
  return [ex.sets && `${ex.sets}×${ex.reps ?? "?"}`, ex.weight, ex.rest].filter(Boolean).join(" · ");
}

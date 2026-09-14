import { useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox } from "../../components";
import { WAGI_DOMYSLNE, naGoalMix, opisWagi, przesun } from "../../suwaki";
import {
  CardioItem,
  CardioPodglad,
  CardioPrescription,
  EXERCISE_LEVEL_LABELS,
  Exercise,
  GOAL_KEYS,
  GOAL_LABELS,
  GOAL_SHORT,
  MACHINE_LABELS,
} from "../../types";

/**
 * Panel cardio z suwakami (0.73.0) w edytorze planu — propose-only.
 *
 * Trzy sprzężone suwaki (`suwaki.ts`: przesunięcie jednego zabiera pozostałym
 * proporcjonalnie, kłódka, suma zawsze 100), poziom, dozwolone urządzenia
 * (klient wybierze w dniu treningu), bramka zdrowotna jak w konfiguratorze +
 * leki wpływające na tętno, „Policz propozycję” (`POST …/cardio/podglad`,
 * nic nie zapisuje) → tabela zakresów, edytowalne liczby (nadpisanie trenera
 * zapisuje się w śladzie jako `overridden_by_coach`) i „Wstaw do dnia”.
 * Klient nie widzi niczego, dopóki trener nie zapisze/nie opublikuje wersji.
 */

/** Klucze pytań bramki w kolejności ekranu; treść pytań przychodzi z `GET /api/cardio/katalog`
 * (ta sama, co w konfiguratorze) — bez kopii na sztywno. */
const KLUCZE_PYTAN = ["current_red_flag", "unexplained_exertional_symptoms", "known_condition",
  "acute_injury_or_surgery", "pregnancy_postpartum", "active_rehabilitation", "hr_medication"] as const;
const MASZYNY = Object.keys(MACHINE_LABELS);

type Zdrowie = Record<string, boolean | null>;

export default function CardioPanel({ clientId, onInsert, onClose }: {
  clientId: string | null;
  onInsert: (ex: Exercise) => void;
  onClose: () => void;
}) {
  const [wagi, setWagi] = useState<number[]>([...WAGI_DOMYSLNE]);
  const [pytania, setPytania] = useState<Record<string, string>>({});
  const [klodki, setKlodki] = useState<boolean[]>([false, false, false]);
  const [level, setLevel] = useState("SREDNIOZAAWANSOWANY");
  const [maszyny, setMaszyny] = useState<string[]>(["rowerek"]);
  const [zdrowie, setZdrowie] = useState<Zdrowie>(Object.fromEntries(KLUCZE_PYTAN.map((k) => [k, null])));
  useEffect(() => {
    api.get<{ health_questions: Record<string, string> }>("/api/cardio/katalog")
      .then((d) => setPytania(d.health_questions))
      .catch(() => setPytania({}));
  }, []);
  const [age, setAge] = useState("");
  const [restingHr, setRestingHr] = useState("");
  const [weight, setWeight] = useState("");
  const [healthAccess, setHealthAccess] = useState<boolean | null>(null);
  const [wynik, setWynik] = useState<CardioPodglad | null>(null);
  const [rx, setRx] = useState<CardioPrescription | null>(null);
  const [nadpisane, setNadpisane] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Prefill z danych klienta (tylko przy dostępie trenera do domeny zdrowotnej).
  useEffect(() => {
    if (!clientId) return;
    api.get<{ age: number | null; resting_hr: number | null; weight_kg: number | null; health_access: boolean }>(`/api/clients/${clientId}/cardio/prefill`)
      .then((d) => {
        setHealthAccess(d.health_access);
        if (d.age != null) setAge(String(Math.round(d.age)));
        if (d.resting_hr != null) setRestingHr(String(d.resting_hr));
        if (d.weight_kg != null) setWeight(String(Math.round(d.weight_kg)));
      })
      .catch(() => setHealthAccess(null));
  }, [clientId]);

  const liczba = (v: string): number | null => { const n = Number(v.replace(",", ".")); return v.trim() && isFinite(n) ? n : null; };

  async function policz() {
    setBusy(true); setError(null); setWynik(null); setRx(null); setNadpisane([]);
    try {
      const body = { goal_mix: naGoalMix(wagi), level, machines: maszyny, health: zdrowie,
        age: liczba(age), resting_hr: liczba(restingHr), weight_kg: liczba(weight) };
      // Szablon bez klienta: bramka zdrowotna i prefill nie mają podmiotu — liczymy na kliencie
      // dopiero po przypisaniu; tu panel wymaga klienta.
      const r = await api.post<CardioPodglad>(`/api/clients/${clientId}/cardio/podglad`, body);
      setWynik(r);
      if (r.prescription) setRx(r.prescription);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function nadpisz(pole: string, zmien: (p: CardioPrescription) => CardioPrescription) {
    if (!rx) return;
    setRx(zmien(rx));
    setNadpisane((n) => (n.includes(pole) ? n : [...n, pole]));
  }

  function wstaw() {
    if (!rx || !wynik) return;
    const mix = naGoalMix(wagi);
    const nazwa = `Cardio — ${maszyny.map((m) => MACHINE_LABELS[m]).join(" / ")} `
      + `(${GOAL_KEYS.map((k, i) => `${GOAL_SHORT[k]} ${wagi[i]} %`).join(" / ")})`;
    const cardio: CardioItem = { goal_mix: mix, level, machines: maszyny, prescription: rx,
      trace: wynik.trace ?? {}, model_version: wynik.model_version ?? "cardio_model_v1", overridden_by_coach: nadpisane };
    onInsert({ name: nazwa, kind: "cardio", cardio, sets: "", reps: "", weight: "", rest: "",
      comment: rx.hr_bpm_range ? "" : "Prowadź według RPE i testu mowy." });
  }

  /** Pole liczbowe: puste albo nieliczbowe nie zmienia wartości (nie daje 0). */
  const liczbaZ = (v: string, dotychczas: number): number => { const n = Number(v); return v.trim() && isFinite(n) ? n : dotychczas; };
  /** Zmiana % tętna przelicza ud./min (i odwrotnie), gdy znane HRmax z wzoru; przy rezerwie tętna
   * (Karvonen) przeliczenie wymaga tętna spoczynkowego — wtedy pola są niezależne. */
  const pctNaBpm = (pct: number, p: CardioPrescription) => (p.hrmax_estimate && !p.hrr_used ? Math.floor(pct / 100 * p.hrmax_estimate + 0.5) : null);
  const bpmNaPct = (bpm: number, p: CardioPrescription) => (p.hrmax_estimate && !p.hrr_used ? Math.floor(bpm / p.hrmax_estimate * 100 + 0.5) : null);
  const zakresInput = (etykieta: string, pole: string, get: () => [number, number], set: (lo: number, hi: number) => void) => (
    <div className="row" style={{ gap: 6 }}>
      <span style={{ width: 150, fontSize: "0.85rem" }}>{etykieta}</span>
      <input type="number" style={{ width: 80 }} aria-label={`${etykieta} — od`} value={get()[0]}
        onChange={(e) => set(liczbaZ(e.target.value, get()[0]), get()[1])} />
      <span aria-hidden>–</span>
      <input type="number" style={{ width: 80 }} aria-label={`${etykieta} — do`} value={get()[1]}
        onChange={(e) => set(get()[0], liczbaZ(e.target.value, get()[1]))} />
      {nadpisane.includes(pole) && <span className="badge badge--warn">zmienione ręcznie</span>}
    </div>
  );

  if (!clientId) {
    return (
      <div className="card" style={{ marginTop: 8 }}>
        <p className="dim">Cardio z suwakami liczy się dla konkretnego klienta (bramka zdrowotna, wiek, tętno spoczynkowe).
          W szablonie bez klienta wstaw pozycję po przypisaniu planu.</p>
        <button type="button" className="btn btn--ghost btn--small" onClick={onClose}>Zamknij</button>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 8 }} data-testid="cardio-panel">
      <div className="row row--between">
        <b>Cardio z suwakami celów</b>
        <button type="button" className="btn btn--ghost btn--small" onClick={onClose}>Zamknij panel</button>
      </div>
      <p className="dim" style={{ fontSize: "0.85rem" }}>
        Trzy cele sumują się do 100 % — przesunięcie jednego zabiera pozostałym. Wynik to propozycja struktury
        sesji (zakres tętna, RPE, czas, urządzenie) z modelu stref wg progów i rezerwy tętna; Ty decydujesz i możesz
        każdą liczbę zmienić. To nie jest porada medyczna.
      </p>
      {GOAL_KEYS.map((k, i) => (
        <div key={k} className="scale-row">
          <div className="row row--between">
            <label htmlFor={`suwak-${k}`}>{GOAL_LABELS[k]}: <b data-testid={`waga-${k}`}>{wagi[i]} %</b></label>
            <label className="row" style={{ alignItems: "center", fontSize: "0.8rem" }}>
              <input type="checkbox" checked={klodki[i]} aria-label={`Zablokuj ${GOAL_SHORT[k]}`}
                onChange={(e) => setKlodki(klodki.map((z, j) => (j === i ? e.target.checked : z)))} />
              <span>kłódka</span>
            </label>
          </div>
          <input id={`suwak-${k}`} type="range" min={0} max={100} step={5} value={wagi[i]} disabled={klodki[i]}
            style={{ width: "100%" }} aria-valuemin={0} aria-valuemax={100} aria-valuenow={wagi[i]} aria-valuetext={opisWagi(GOAL_SHORT[k], wagi[i])}
            onChange={(e) => setWagi(przesun(wagi, i, Number(e.target.value), klodki))} />
        </div>
      ))}
      <div className="field-row">
        <div>
          <label htmlFor="cardio-level">Poziom klienta</label>
          <select id="cardio-level" value={level} onChange={(e) => setLevel(e.target.value)}>
            {Object.entries(EXERCISE_LEVEL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend>Dozwolone urządzenia (klient wybierze w dniu treningu)</legend>
          {MASZYNY.map((m) => (
            <label key={m} className="row" style={{ alignItems: "center", fontSize: "0.9rem" }}>
              <input type="checkbox" checked={maszyny.includes(m)}
                onChange={(e) => setMaszyny(e.target.checked ? [...maszyny, m] : maszyny.filter((x) => x !== m))} />
              <span>{MACHINE_LABELS[m]}</span>
            </label>
          ))}
        </fieldset>
      </div>
      <fieldset style={{ border: 0, padding: 0, marginTop: 8 }}>
        <legend><b>Kwalifikacja zdrowotna</b> (jak w konfiguratorze; brak odpowiedzi = brak propozycji; nie zapisuje się w planie)</legend>
        {KLUCZE_PYTAN.map((k) => { const q = pytania[k] ?? k; return (
          <div key={k} className="row row--between" style={{ margin: "4px 0", gap: 8 }}>
            <span style={{ flex: 1, fontSize: "0.85rem" }}>{q}</span>
            <span className="row" role="group" aria-label={q} style={{ gap: 4 }}>
              {([["tak", true], ["nie", false]] as const).map(([et, v]) => (
                <button key={et} type="button" className={`btn btn--small ${zdrowie[k] === v ? "" : "btn--ghost"}`}
                  aria-pressed={zdrowie[k] === v} onClick={() => setZdrowie({ ...zdrowie, [k]: v })}>{et}</button>
              ))}
            </span>
          </div>
        ); })}
      </fieldset>
      <div className="field-row-3" style={{ marginTop: 8 }}>
        <div><label htmlFor="cardio-age">Wiek (lata)</label>
          <input id="cardio-age" type="number" inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} placeholder="brak → tylko RPE" /></div>
        <div><label htmlFor="cardio-rhr">Tętno spoczynkowe (ud./min)</label>
          <input id="cardio-rhr" type="number" inputMode="numeric" value={restingHr} onChange={(e) => setRestingHr(e.target.value)} placeholder="opcjonalnie" /></div>
        <div><label htmlFor="cardio-weight">Masa ciała (kg)</label>
          <input id="cardio-weight" type="number" inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="do szacunku kcal" /></div>
      </div>
      {healthAccess === false && (
        <p className="dim" style={{ fontSize: "0.8rem" }}>Bez zgody klienta na dane zdrowotne wiek i tętno spoczynkowe nie są odczytywane — wpisz je, jeśli klient je podał, albo licz w trybie RPE.</p>
      )}
      <div className="row" style={{ marginTop: 8 }}>
        <button type="button" className="btn" disabled={busy || maszyny.length === 0} onClick={policz} data-testid="cardio-policz">
          {busy ? "Liczę…" : "Policz propozycję"}
        </button>
      </div>
      <ErrorBox error={error} />
      {wynik && (
        <div style={{ marginTop: 10 }} data-testid="cardio-wynik">
          {wynik.issues.map((i, n) => (
            <p key={n} className={`alert ${i.severity === "critical" || i.severity === "error" ? "alert--error" : "alert--warn"}`} role="alert">{i.message}</p>
          ))}
          {wynik.questions.length > 0 && (
            <ul className="dim" style={{ fontSize: "0.85rem" }}>{wynik.questions.map((q) => <li key={q}>{q}</li>)}</ul>
          )}
          {rx && (
            <>
              <div className="stat-grid" style={{ marginTop: 6 }}>
                <div className="stat"><b>{`${rx.hr_pct_range[0]}–${rx.hr_pct_range[1]} %`}</b><span>tętna maks.</span></div>
                <div className="stat"><b>{rx.hr_bpm_range ? `${rx.hr_bpm_range[0]}–${rx.hr_bpm_range[1]}` : "—"}</b><span>ud./min {rx.hrr_used ? "(rezerwa tętna)" : rx.hrmax_estimate ? "(wzór wiekowy)" : "(brak wieku)"}</span></div>
                <div className="stat"><b>{rx.rpe_range[0]}–{rx.rpe_range[1]}</b><span>RPE / 10{rx.rpe_rest_range ? ` (przerwa ${rx.rpe_rest_range[0]})` : ""}</span></div>
                <div className="stat"><b>{rx.duration_min} min</b><span>{rx.structure.label}</span></div>
              </div>
              <p className="dim" style={{ fontSize: "0.85rem" }}>Test mowy: {rx.talk_test}{rx.kcal_estimate != null && <> · szacunek {rx.kcal_estimate} kcal (MET)</>}</p>
              <div className="table-wrap">
                <table className="simple">
                  <thead><tr><th>Urządzenie</th><th>Zacznij od</th><th>W przerwie</th></tr></thead>
                  <tbody>
                    {rx.machine_params.map((p) => (
                      <tr key={p.machine}>
                        <td>{p.label}</td>
                        <td>{p.tempo_name} {p.tempo} {p.tempo_unit}, {p.load_name} {p.load}</td>
                        <td>{p.rest_tempo ? `${p.tempo_name} ${p.rest_tempo}, ${p.load_name} ${p.rest_load}` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details style={{ marginTop: 6 }}>
                <summary>Zmień liczby ręcznie (zapisze się jako Twoja decyzja)</summary>
                <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
                  {zakresInput("% tętna maks.", "hr_pct_range", () => rx.hr_pct_range, (lo, hi) => nadpisz("hr_pct_range", (p) => {
                    const bpm = p.hr_bpm_range && pctNaBpm(lo, p) !== null ? [pctNaBpm(lo, p)!, pctNaBpm(hi, p)!] as [number, number] : p.hr_bpm_range;
                    return { ...p, hr_pct_range: [lo, hi], hr_bpm_range: bpm };
                  }))}
                  {rx.hr_bpm_range && zakresInput("ud./min", "hr_bpm_range", () => rx.hr_bpm_range as [number, number], (lo, hi) => nadpisz("hr_bpm_range", (p) => {
                    const pct = bpmNaPct(lo, p) !== null ? [bpmNaPct(lo, p)!, bpmNaPct(hi, p)!] as [number, number] : p.hr_pct_range;
                    return { ...p, hr_bpm_range: [lo, hi], hr_pct_range: pct };
                  }))}
                  {zakresInput("RPE", "rpe_range", () => rx.rpe_range, (lo, hi) => nadpisz("rpe_range", (p) => ({ ...p, rpe_range: [lo, hi] })))}
                  <div className="row" style={{ gap: 6 }}>
                    <span style={{ width: 150, fontSize: "0.85rem" }}>Czas (min)</span>
                    <input type="number" style={{ width: 80 }} aria-label="Czas w minutach" value={rx.duration_min}
                      onChange={(e) => nadpisz("duration_min", (p) => ({ ...p, duration_min: liczbaZ(e.target.value, p.duration_min) }))} />
                    {nadpisane.includes("duration_min") && <span className="badge badge--warn">zmienione ręcznie</span>}
                  </div>
                </div>
              </details>
              <ul className="dim" style={{ fontSize: "0.8rem", marginTop: 6 }}>{rx.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
              <div className="row" style={{ marginTop: 8 }}>
                <button type="button" className="btn" onClick={wstaw} data-testid="cardio-wstaw">Wstaw do dnia</button>
                {wynik.status === "needs_review" && <span className="badge badge--warn">wymaga oceny specjalisty — widoczne tylko dla Ciebie</span>}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

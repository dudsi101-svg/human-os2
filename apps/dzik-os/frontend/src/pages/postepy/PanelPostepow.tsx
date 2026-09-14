import { ReactNode, useEffect, useState } from "react";
import { api } from "../../api";
import { plDate } from "../../dates";
import { AuthImage, ErrorBox, Icon, PhotoCompare, Sparkline, Spinner } from "../../components";
import {
  GRUPA_LABELS, KIND_LABELS, PostepyBody, PostepyCwiczenie, PostepyRekord, PostepyRekordy, PostepySummary,
  PostepyTrening, PostepyTydzien,
} from "../../types";

/* Zakładka Postępy / Monitoring (0.66.0, spec docs/monitoring-tab §4–6):
   trzy niezależne osie — Forma → Konsekwencja → Sylwetka — w tej kolejności,
   bo sylwetka jest najbardziej opóźniona i zaszumiona. Jeden komponent dla
   klienta (dane własne) i trenera (dane wskazanego klienta, pełne).
   Klient z flagą zdrowotną nie dostaje sekcji „Sylwetka” ani kafelka wagi —
   filtruje serwer (brak pola), nie ten komponent. */

export interface DanePostepow {
  summary: PostepySummary;
  records: PostepyRekordy;
  training: PostepyTrening;
  body: PostepyBody | null;
}

export function useDanePostepow(tryb: "klient" | "trener", clientId: string) {
  const [dane, setDane] = useState<DanePostepow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wersja, setWersja] = useState(0);
  useEffect(() => {
    let aktywne = true;
    setError(null);
    const q = tryb === "trener" ? `?client_id=${encodeURIComponent(clientId)}` : "";
    Promise.all([
      api.get<PostepySummary>(`/api/monitoring/summary${q}`),
      api.get<PostepyRekordy>(`/api/monitoring/records${q}`),
      api.get<PostepyTrening>(`/api/monitoring/training${q}${q ? "&" : "?"}range=12w`),
    ]).then(async ([summary, records, training]) => {
      // Sylwetka: 404 = klient z flagą zdrowotną (sekcja nie renderuje się wcale).
      let body: PostepyBody | null = null;
      try {
        body = await api.get<PostepyBody>(`/api/monitoring/body${q}`);
      } catch (e) {
        if (!/404|Nie znaleziono/.test((e as Error).message)) throw e;
      }
      if (aktywne) setDane({ summary, records, training, body });
    }).catch((e) => { if (aktywne) setError((e as Error).message); });
    return () => { aktywne = false; };
  }, [tryb, clientId, wersja]);
  return { dane, error, odswiez: () => setWersja((w) => w + 1) };
}

export function kgLabel(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${Number.isInteger(v) ? v : v.toFixed(1)} kg`;
}

function trendLabel(kg: number | null): string {
  if (kg === null) return "—";
  const znak = kg > 0 ? "+" : kg < 0 ? "−" : "";
  return `${znak}${Math.abs(kg).toFixed(1)} kg/tydz.`;
}

/* 6.1 Nagłówek tygodnia — trzy kafelki, zawsze ta sama kolejność. */
export function KafelkiTygodnia({ s }: { s: PostepySummary }) {
  return (
    <div className="postepy-kafelki" role="list" aria-label="Ten tydzień">
      <div className="stat" role="listitem">
        <span>Treningi</span>
        {s.week.planned > 0 ? <b>{s.week.done} / {s.week.planned}</b> : <b>{s.week.done}</b>}
        <div className="postepy-dni" aria-label={`Dni z treningiem: ${s.week.days.filter((d) => d.done).length} z 7`}>
          {s.week.days.map((d) => <i key={d.date} className={d.done ? "done" : ""} title={plDate(d.date)} />)}
        </div>
        {s.week.message && <small>{s.week.message}</small>}
      </div>
      <div className="stat" role="listitem">
        <span>Konsekwencja</span>
        <b>{s.streak.weeks > 0 ? `${s.streak.weeks} ${tygodnie(s.streak.weeks)}` : "—"}</b>
        <small>{s.streak.message ?? `najdłuższa: ${s.streak.longest}`}</small>
      </div>
      {s.weight && (
        <div className="stat" role="listitem">
          <span>Trend wagi</span>
          <b>{s.weight.kg_per_week !== null ? trendLabel(s.weight.kg_per_week) : "—"}</b>
          <small>{s.weight.message ?? (s.weight.average !== null ? `średnia 7 dni: ${kgLabel(s.weight.average)}` : "")}</small>
        </div>
      )}
    </div>
  );
}

function pomiary(n: number): string {
  if (n === 1) return "pomiar";
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return "pomiary";
  return "pomiarów";
}

function tygodnie(n: number): string {
  if (n === 1) return "tydzień";
  if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) return "tygodnie";
  return "tygodni";
}

function typLabel(r: PostepyRekord): string {
  switch (r.record_type) {
    case "WEIGHT": return "ciężar";
    case "E1RM": return "szac. 1RM";
    case "REPS_AT_WEIGHT": return `powtórzenia przy ${kgLabel(r.secondary_value)}`;
    case "SET_VOLUME": return "objętość serii";
    case "SESSION_VOLUME": return "tonaż sesji";
    default: return r.record_type;
  }
}

function wartosc(r: PostepyRekord): string {
  return r.record_type === "REPS_AT_WEIGHT" ? `${r.value} powt.` : kgLabel(r.value);
}

/* 6.2 Rekordy: wstęga z 30 dni, lista ćwiczeń, archiwum. e1RM zawsze „szacowany”. */
export function SekcjaRekordy({ r }: { r: PostepyRekordy }) {
  const [archiwum, setArchiwum] = useState(false);
  return (
    <section className="card" aria-labelledby="h-rekordy">
      <h2 id="h-rekordy"><Icon name="trophy" /> Rekordy</h2>
      {r.recent.length > 0 ? (
        <div className="postepy-wstega" aria-label="Rekordy z ostatnich 30 dni">
          {r.recent.map((x) => (
            <div className="card card--accent" key={x.id}>
              <b>{x.exercise_name}</b>
              <div>{x.previous_value !== null ? `${kgLabel(x.previous_value)} → ` : ""}{wartosc(x)}
                {x.delta !== null && x.delta > 0 && <span className="badge badge--accent" style={{ marginLeft: 6 }}>+{x.delta}</span>}</div>
              <small className="dim">{typLabel(x)}{x.estimated ? " (szacowany)" : ""} · {plDate(x.achieved_on)}
                {x.days_since_previous ? ` · ${x.days_since_previous} dni od poprzedniego` : ""}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="dim">Brak nowych rekordów w ostatnich 30 dni. Rekord liczy się od drugiego wykonania ćwiczenia — pierwsza sesja to punkt odniesienia.</p>
      )}
      {r.exercises.length === 0 && r.archive.length === 0 && <p className="dim">Zapisz serie (ciężar × powtórzenia) w treningu, a pojawią się tu Twoje ćwiczenia.</p>}
      {r.exercises.map((c) => <WierszCwiczenia key={c.exercise_key} c={c} note={r.e1rm_note} />)}
      {r.archive.length > 0 && (
        <details open={archiwum} onToggle={(e) => setArchiwum((e.target as HTMLDetailsElement).open)}>
          <summary>Archiwum ({r.archive.length}) — niewykonywane od ponad 90 dni</summary>
          {r.archive.map((c) => <WierszCwiczenia key={c.exercise_key} c={c} note={r.e1rm_note} />)}
        </details>
      )}
    </section>
  );
}

function WierszCwiczenia({ c, note }: { c: PostepyCwiczenie; note: string }) {
  return (
    <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
      <div className="row row--between">
        <b>{c.exercise_name}</b>
        <small className="dim">ostatnio {plDate(c.last_performed_on)}</small>
      </div>
      <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
        <small>Rekord ciężaru: <b>{c.max_weight ? kgLabel(c.max_weight.value) : "—"}</b>{c.max_weight && ` (${plDate(c.max_weight.achieved_on)})`}</small>
        <small title={note}>Szacowany 1RM: <b>{c.e1rm ? kgLabel(c.e1rm.value) : "—"}</b> <span className="dim">(szacunek)</span></small>
      </div>
      {c.e1rm_series.length >= 2 && (
        <Sparkline unit="kg" label={`Szacowany 1RM — ${c.exercise_name}`}
          points={c.e1rm_series.map((p) => ({ x: plDate(p.date), y: p.value }))} />
      )}
      {c.history && c.history.length > 0 && (
        <details><summary>Historia rekordów ({c.history.length})</summary>
          <ul style={{ paddingLeft: 18, margin: "4px 0" }}>
            {c.history.map((h) => <li key={h.id}><small>{plDate(h.achieved_on)} · {typLabel(h)}: {wartosc(h)}{h.superseded_at ? ` (pobity ${plDate(h.superseded_at)})` : ""}</small></li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

/* 6.3 Trening: tonaż 12 tyg. + średnia 4-tyg., serie/grupa, heatmapa. */
export function SekcjaTrening({ t, planChanges }: { t: PostepyTrening; planChanges?: { date: string; version_no: number; reason: string }[] }) {
  const maxTon = Math.max(1, ...t.weeks.map((w) => w.tonnage_kg));
  const grupy = Array.from(new Set([...Object.keys(t.sets_by_group.current), ...Object.keys(t.sets_by_group.previous)]));
  const maxSerie = Math.max(1, ...grupy.map((g) => Math.max(t.sets_by_group.current[g] ?? 0, t.sets_by_group.previous[g] ?? 0)));
  const dni = new Set(t.calendar.session_days);
  const brakDanych = t.weeks.every((w) => w.sessions === 0);
  return (
    <section className="card" aria-labelledby="h-trening">
      <h2 id="h-trening"><Icon name="chart" /> Trening</h2>
      {brakDanych ? <p className="dim">Brak zapisanych treningów w ostatnich 12 tygodniach — zapisz trening w zakładce Plan.</p> : (
        <>
          <h3>Tonaż tygodniowy <small className="dim">(suma ciężar × powtórzenia; linia = średnia 4 tyg.)</small></h3>
          <div className="postepy-slupki" role="img" aria-label={`Tonaż tygodniowy: ${t.weeks.map((w) => `${plDate(w.week_start)} ${Math.round(w.tonnage_kg)} kg`).join(", ")}`}>
            {t.weeks.map((w, i) => (
              <div key={w.week_start} className={`slupek${i === t.weeks.length - 1 ? " biezacy" : ""}`}
                style={{ height: `${Math.max(2, Math.round(100 * w.tonnage_kg / maxTon))}%` }} title={`${plDate(w.week_start)}: ${Math.round(w.tonnage_kg)} kg`}>
                {w.avg4_tonnage_kg !== undefined && <span className="postepy-srednia" style={{ top: `${100 - Math.round(100 * w.avg4_tonnage_kg / maxTon)}%`, bottom: "auto" }} />}
              </div>
            ))}
          </div>
          {planChanges && planChanges.length > 0 && (
            <small className="dim">Zmiany planu: {planChanges.map((z) => `${plDate(z.date)} (v${z.version_no})`).join(", ")}</small>
          )}
          <h3>Serie na grupę mięśniową <small className="dim">(ten tydzień; kreska = poprzedni)</small></h3>
          {grupy.length === 0 ? <p className="dim">W tym tygodniu brak serii.</p> : (
            <div className="postepy-grupy">
              {grupy.sort((a, b) => (t.sets_by_group.current[b] ?? 0) - (t.sets_by_group.current[a] ?? 0)).map((g) => (
                <div key={g}>
                  <span>{GRUPA_LABELS[g] ?? g}</span>
                  <span className="pasek" aria-hidden="true">
                    <i style={{ width: `${Math.round(100 * (t.sets_by_group.current[g] ?? 0) / maxSerie)}%` }} />
                    {t.sets_by_group.previous[g] ? <i className="poprzedni" style={{ width: `${Math.round(100 * t.sets_by_group.previous[g] / maxSerie)}%` }} /> : null}
                  </span>
                  <small>{t.sets_by_group.current[g] ?? 0}{t.sets_by_group.previous[g] !== undefined ? ` (${t.sets_by_group.previous[g]})` : ""}</small>
                </div>
              ))}
            </div>
          )}
          <h3>Kalendarz aktywności <small className="dim">(12 tygodni)</small></h3>
          <Heatmapa weeks={t.weeks} dni={dni} />
        </>
      )}
    </section>
  );
}

function Heatmapa({ weeks, dni }: { weeks: PostepyTydzien[]; dni: Set<string> }) {
  return (
    <div className="postepy-heat" role="img" aria-label={`Dni z treningiem: ${dni.size} w 12 tygodniach`}>
      {weeks.map((w) => {
        const start = new Date(w.week_start + "T00:00:00");
        return (
          <div className="tydz" key={w.week_start}>
            {Array.from({ length: 7 }, (_, i) => {
              const d = new Date(start); d.setDate(start.getDate() + i);
              const iso = d.toISOString().slice(0, 10);
              return <i key={iso} className={dni.has(iso) ? "on" : ""} title={plDate(iso)} />;
            })}
          </div>
        );
      })}
    </div>
  );
}

/* 6.4 Konsekwencja: frekwencja 8 tyg., seria najdłuższa vs aktualna, dieta. */
export function SekcjaKonsekwencja({ s, t }: { s: PostepySummary; t: PostepyTrening }) {
  const osiem = t.weeks.slice(-8);
  return (
    <section className="card" aria-labelledby="h-konsekwencja">
      <h2 id="h-konsekwencja"><Icon name="calendar" /> Konsekwencja</h2>
      <h3>Frekwencja <small className="dim">(wykonane / zaplanowane, 8 tygodni)</small></h3>
      {osiem.every((w) => w.planned === 0) ? <p className="dim">Brak zaplanowanych treningów w harmonogramie — poproś trenera o wpisanie dni treningowych.</p> : (
        <div className="postepy-slupki" role="img" aria-label={`Frekwencja: ${osiem.map((w) => `${plDate(w.week_start)} ${w.sessions}/${w.planned}`).join(", ")}`}>
          {osiem.map((w, i) => (
            <div key={w.week_start} className={`slupek${i === osiem.length - 1 ? " biezacy" : ""}`}
              style={{ height: `${w.planned ? Math.min(100, Math.max(2, Math.round(100 * w.sessions / w.planned))) : 2}%` }}
              title={`${plDate(w.week_start)}: ${w.sessions} / ${w.planned}`} />
          ))}
        </div>
      )}
      <div className="stat-grid" style={{ marginTop: 10 }}>
        <div className="stat"><b>{s.streak.weeks}</b><span>aktualna seria tygodni</span></div>
        <div className="stat"><b>{s.streak.longest}</b><span>najdłuższa seria</span></div>
      </div>
      {s.diet && (
        <p style={{ marginTop: 8 }}>Realizacja diety: <b>{s.diet.pct} %</b> <small className="dim">({s.diet.days_logged} z {s.diet.days} dni z zapisanym jadłospisem)</small></p>
      )}
    </section>
  );
}

/* 6.5 Sylwetka: waga jako średnia (nigdy ostatni pomiar), obwody, zdjęcia. */
export function SekcjaSylwetka({ b, tryb, children }: { b: PostepyBody; tryb: "klient" | "trener"; children?: ReactNode }) {
  const [surowe, setSurowe] = useState(tryb === "trener");
  const [wybrane, setWybrane] = useState<string[]>(() => b.circumferences.slice(0, 2).map((c) => c.kind));
  const [pokazSrednia, setPokazSrednia] = useState(true);
  const w = b.weight;
  const punkty = (pokazSrednia ? w.average_points : w.raw_points).map((p) => ({ x: plDate(p.date), y: p.value }));
  return (
    <section className="card" aria-labelledby="h-sylwetka">
      <h2 id="h-sylwetka"><Icon name="user" /> Sylwetka</h2>
      <h3>Waga <small className="dim" data-testid="waga-pomiary">({w.raw_points.length} {pomiary(w.raw_points.length)} w {w.days} dniach)</small></h3>
      {w.raw_points.length === 0 ? <p className="dim">Brak pomiarów wagi z ostatnich {w.days} dni.</p> : (
        <>
          <div className="stat-grid">
            <div className="stat"><b>{w.average !== null ? kgLabel(w.average) : "—"}</b><span>średnia z 7 dni{w.average === null ? " (min. 3 pomiary)" : ""}</span></div>
            <div className="stat"><b>{w.trend.kg_per_week !== null ? trendLabel(w.trend.kg_per_week) : "—"}</b><span>{w.trend.message ?? "trend z 28 dni"}</span></div>
          </div>
          {tryb === "trener" ? (
            <label className="row" style={{ gap: 6, marginTop: 6 }}>
              <input type="checkbox" checked={pokazSrednia} onChange={(e) => setPokazSrednia(e.target.checked)} /> pokaż średnią zamiast surowych pomiarów
            </label>
          ) : (
            <label className="row" style={{ gap: 6, marginTop: 6 }}>
              <input type="checkbox" checked={surowe} onChange={(e) => setSurowe(e.target.checked)} /> pokaż pojedyncze pomiary
            </label>
          )}
          {punkty.length >= 2 ? <Sparkline unit="kg" label="Masa ciała — średnia krocząca" points={punkty} /> : <p className="dim">Za mało pomiarów na wykres średniej (min. 3 w 7 dniach).</p>}
          {tryb === "klient" && surowe && w.raw_points.length >= 2 && (
            <Sparkline unit="kg" label="Masa ciała — pojedyncze pomiary" points={w.raw_points.map((p) => ({ x: plDate(p.date), y: p.value }))} />
          )}
        </>
      )}
      {children}
      {b.circumferences.length > 0 && (
        <>
          <h3>Obwody</h3>
          <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
            {b.circumferences.map((c) => (
              <label key={c.kind} className="badge" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={wybrane.includes(c.kind)}
                  onChange={(e) => setWybrane(e.target.checked ? [...wybrane, c.kind].slice(-4) : wybrane.filter((k) => k !== c.kind))} /> {KIND_LABELS[c.kind] ?? c.kind}
              </label>
            ))}
          </div>
          {b.circumferences.filter((c) => wybrane.includes(c.kind)).map((c) => (
            <div key={c.kind} style={{ marginTop: 8 }}>
              <div className="row row--between"><b>{KIND_LABELS[c.kind] ?? c.kind}</b>
                <small>{c.current} {c.unit}{c.delta_from_first !== null ? ` · ${c.delta_from_first > 0 ? "+" : ""}${c.delta_from_first} ${c.unit} od pierwszego pomiaru` : ""}</small></div>
              <Sparkline unit={c.unit} label={KIND_LABELS[c.kind] ?? c.kind} points={c.points.map((p) => ({ x: plDate(p.date), y: p.value }))} />
            </div>
          ))}
        </>
      )}
      <h3>Zdjęcia</h3>
      {b.photos.length === 0 ? <p className="dim">Brak zdjęć postępów. Dodasz je przy raporcie tygodniowym.</p> : (
        <>
          {b.photos.length >= 2 && <PhotoCompare photos={b.photos} formatDate={plDate} />}
          <div className="photo-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6, marginTop: 8 }}>
            {b.photos.map((p) => (
              <figure key={p.id} style={{ margin: 0 }}>
                <AuthImage fileId={p.file_id} alt={`Zdjęcie sylwetki z ${plDate(p.taken_at)}`} />
                <figcaption><small>{plDate(p.taken_at)}</small></figcaption>
              </figure>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export function PanelPostepow({ tryb, clientId, dodatki, planChanges }: {
  tryb: "klient" | "trener"; clientId: string; dodatki?: ReactNode;
  planChanges?: { date: string; version_no: number; reason: string }[];
}) {
  const { dane, error, odswiez } = useDanePostepow(tryb, clientId);
  if (error) return <ErrorBox error={error} onRetry={odswiez} />;
  if (!dane) return <Spinner />;
  return (
    <>
      <KafelkiTygodnia s={dane.summary} />
      <SekcjaRekordy r={dane.records} />
      <SekcjaTrening t={dane.training} planChanges={planChanges} />
      <SekcjaKonsekwencja s={dane.summary} t={dane.training} />
      {dane.body && <SekcjaSylwetka b={dane.body} tryb={tryb}>{dodatki}</SekcjaSylwetka>}
    </>
  );
}

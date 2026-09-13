import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { DietProductRow, DietProfileRow, DietSweep, DietWeekFull } from "../../types";

/**
 * Panel wprowadzania szablonów diet (0.60.0, etap 6 — minimalny):
 * profile, odsłony, dni, posiłki, składniki (produkt z bazy + reguły
 * skalowania), „Testuj skalowanie” (sweep 1400–3200, flagi per posiłek),
 * publikacja tylko przy ≥ 95 % dni OK, import odsłony z JSON.
 */
export default function SzablonyDiet() {
  const [profile, setProfile] = useState<DietProfileRow[] | null>(null);
  const [produkty, setProdukty] = useState<DietProductRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [nowyProfil, setNowyProfil] = useState({ name: "", description: "", p: "25", f: "30", c: "45" });
  const [wybrany, setWybrany] = useState<string | null>(null);
  const [importJson, setImportJson] = useState("");
  const [busy, setBusy] = useState(false);

  const zaladuj = useCallback(() => {
    setError(null);
    api.get<{ profiles: DietProfileRow[] }>("/api/diet/profiles").then((d) => setProfile(d.profiles)).catch((e) => setError((e as Error).message));
    api.get<{ products: DietProductRow[] }>("/api/diet/products").then((d) => setProdukty(d.products)).catch(() => setProdukty([]));
  }, []);
  useEffect(zaladuj, [zaladuj]);

  // Jedna operacja naraz: podwójne kliknięcie dawało 409 po udanym zapisie.
  async function akcja(f: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(null);
    try { await f(); } catch (e) { setError(e instanceof SyntaxError ? "To nie jest poprawny JSON." : (e as Error).message); } finally { setBusy(false); }
  }
  const dodajProfil = () => akcja(async () => {
    await api.post("/api/diet/profiles", { name: nowyProfil.name, description: nowyProfil.description,
      base_p_pct: Number(nowyProfil.p) / 100, base_f_pct: Number(nowyProfil.f) / 100, base_c_pct: Number(nowyProfil.c) / 100 });
    setNowyProfil({ name: "", description: "", p: "25", f: "30", c: "45" }); zaladuj();
  });
  const dodajOdslone = (p: DietProfileRow) => akcja(async () => {
    const next = (Math.max(0, ...p.weeks.map((w) => w.variant_no)) || 0) + 1;
    await api.post("/api/diet/weeks", { profile_id: p.id, variant_no: next, name: `${p.name} — odsłona ${next}` });
    zaladuj();
  });
  const importuj = () => akcja(async () => {
    const dane = JSON.parse(importJson);
    const r = await api.post<{ week_id: string; name: string }>("/api/diet/weeks/import", dane);
    setInfo(`Zaimportowano odsłonę „${r.name}” jako szkic — uruchom test skalowania i opublikuj.`); setImportJson(""); zaladuj();
  });

  if (error && !profile) return <div className="page"><TopBar title="Szablony diet" /><ErrorBox error={error} onRetry={zaladuj} /></div>;
  if (!profile) return <div className="page"><TopBar title="Szablony diet" /><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Szablony diet (skalowanie)" right={<Link className="btn btn--ghost btn--small" to="/trener/szablony">← Szablony</Link>} />
      {info && <p className="alert alert--info" role="status">{info}</p>}
      <ErrorBox error={error} />
      {wybrany ? (
        <EdytorOdslony weekId={wybrany} produkty={produkty} onWroc={() => { setWybrany(null); zaladuj(); }} />
      ) : (
        <>
          {profile.map((p) => (
            <div className="card" key={p.id}>
              <div className="row row--between">
                <h2 style={{ margin: 0 }}>{p.name}</h2>
                <small className="dim">B {Math.round(p.base_macro_pct.P * 100)} / T {Math.round(p.base_macro_pct.F * 100)} / W {Math.round(p.base_macro_pct.C * 100)} % · opublikowane odsłony: {p.published_weeks}</small>
              </div>
              {p.description && <p className="dim">{p.description}</p>}
              <ul style={{ paddingLeft: 18 }}>
                {p.weeks.map((w) => (
                  <li key={w.id}>
                    Odsłona {w.variant_no}{w.name ? ` · ${w.name}` : ""} <span className={w.status === "PUBLISHED" ? "badge badge--ok" : "badge badge--warn"}>{w.status === "PUBLISHED" ? "opublikowana" : "szkic"}</span>{" "}
                    <small className="dim">{w.kcal_min}–{w.kcal_max} kcal, baza {w.base_kcal}</small>{" "}
                    <button type="button" className="btn btn--ghost btn--small" onClick={() => setWybrany(w.id)}>Edytuj / testuj</button>
                  </li>
                ))}
              </ul>
              <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void dodajOdslone(p)}>Dodaj odsłonę</button>
            </div>
          ))}
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Nowy profil</h3>
            <div className="field-row">
              <div><label htmlFor="np-name">Nazwa</label><input id="np-name" value={nowyProfil.name} onChange={(e) => setNowyProfil({ ...nowyProfil, name: e.target.value })} /></div>
              <div><label htmlFor="np-desc">Opis</label><input id="np-desc" value={nowyProfil.description} onChange={(e) => setNowyProfil({ ...nowyProfil, description: e.target.value })} /></div>
            </div>
            <div className="field-row-3">
              {(["p", "f", "c"] as const).map((k) => (
                <div key={k}><label htmlFor={`np-${k}`}>{{ p: "Białko % kcal", f: "Tłuszcz % kcal", c: "Węgle % kcal" }[k]}</label>
                  <input id={`np-${k}`} inputMode="numeric" value={nowyProfil[k]} onChange={(e) => setNowyProfil({ ...nowyProfil, [k]: e.target.value })} /></div>
              ))}
            </div>
            <button type="button" className="btn btn--small" style={{ marginTop: 8 }} disabled={busy || nowyProfil.name.length < 2} onClick={() => void dodajProfil()}>Dodaj profil</button>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Import odsłony z JSON</h3>
            <p className="dim">Format jak `template_standard_v1.json` (profil, wariant, macro_pct, dni → posiłki → składniki po nazwie produktu z bazy). Nieznany produkt = odrzucenie importu.</p>
            <label htmlFor="imp-json">JSON</label>
            <textarea id="imp-json" rows={6} value={importJson} onChange={(e) => setImportJson(e.target.value)} />
            <button type="button" className="btn btn--small" style={{ marginTop: 8 }} disabled={busy || !importJson.trim()} onClick={() => void importuj()}>Importuj jako szkic</button>
          </div>
        </>
      )}
    </div>
  );
}

const KLASY = ["", "LINIOWY", "DYSKRETNY", "TŁUMIONY", "STAŁY"];
const SLOTY = ["śniadanie", "obiad", "przekąska", "kolacja", "drugie śniadanie", "podwieczorek"];

function EdytorOdslony({ weekId, produkty, onWroc }: { weekId: string; produkty: DietProductRow[]; onWroc: () => void }) {
  const [w, setW] = useState<DietWeekFull | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sweep, setSweep] = useState<DietSweep | null>(null);
  const [busy, setBusy] = useState(false);
  const [dzien, setDzien] = useState(1);
  const [nowyPosilek, setNowyPosilek] = useState({ slot: "śniadanie", name: "", kcal_share: "0.25", flexible: false, recipe_steps: "" });
  const [nowySkladnik, setNowySkladnik] = useState<Record<string, { product_id: string; base_grams: string; macro_role: string; scaling_class: string; unit_g: string; group_name: string }>>({});

  const zaladuj = useCallback(() => {
    api.get<DietWeekFull>(`/api/diet/weeks/${weekId}/full`).then(setW).catch((e) => setError((e as Error).message));
  }, [weekId]);
  useEffect(zaladuj, [zaladuj]);

  async function akcja(f: () => Promise<unknown>, ok?: string) {
    setBusy(true); setError(null);
    try { await f(); if (ok) setError(null); zaladuj(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function testuj() {
    setBusy(true);
    try { setSweep(await api.post<DietSweep>(`/api/diet/weeks/${weekId}/sweep`)); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function publikuj() {
    setBusy(true); setError(null);
    try {
      const r = await api.post<{ status: string; sweep: DietSweep }>(`/api/diet/weeks/${weekId}/publish`);
      setSweep(r.sweep); zaladuj();
    } catch (e) {
      const err = e as ApiError;
      setError(err.message);
      const body = err.body as { sweep?: DietSweep } | undefined;
      if (body?.sweep) setSweep(body.sweep);
    } finally { setBusy(false); }
  }

  if (error && !w) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (!w) return <Spinner />;
  const d = w.days.find((x) => x.day === dzien) ?? w.days[0];
  const suma = d ? d.meals.reduce((s, m) => s + m.kcal_share, 0) : 0;

  return (
    <div>
      <div className="card">
        <div className="row row--between">
          <h2 style={{ margin: 0 }}>{w.name || `${w.profile} — odsłona ${w.variant}`}</h2>
          <span className={w.status === "PUBLISHED" ? "badge badge--ok" : "badge badge--warn"}>{w.status === "PUBLISHED" ? "opublikowana" : "szkic"}</span>
        </div>
        <small className="dim">Baza {w.base_kcal} kcal · zakres {w.kcal_min}–{w.kcal_max} · makro {w.macro_pct.map((x) => Math.round(x * 100)).join("/")}</small>
        <div className="row" style={{ gap: 6, marginTop: 8 }}>
          <button type="button" className="btn btn--small" disabled={busy} onClick={() => void testuj()}>Testuj skalowanie (1400–3200)</button>
          {w.status !== "PUBLISHED"
            ? <button type="button" className="btn btn--small" disabled={busy} onClick={() => void publikuj()}>Opublikuj (≥ 95 % dni OK)</button>
            : <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void akcja(() => api.post(`/api/diet/weeks/${weekId}/unpublish`))}>Cofnij publikację</button>}
          <button type="button" className="btn btn--ghost btn--small" onClick={onWroc}>← Profile</button>
        </div>
        <ErrorBox error={error} />
        {sweep && (
          <div style={{ marginTop: 8 }}>
            <b>Wynik testu:</b> dni OK {sweep.days_ok}/{sweep.days} ({sweep.ok_pct} %) · {sweep.publishable ? <span className="badge badge--ok">gotowa do publikacji</span> : <span className="badge badge--warn">poniżej progu 95 %</span>}
            {sweep.error && <p className="alert alert--warn">{sweep.error}</p>}
            {sweep.meals.filter((m) => m.flags > 0).length > 0 && (
              <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
                {sweep.meals.filter((m) => m.flags > 0).map((m) => <li key={m.meal_id}>D{m.day} {m.slot}: {m.name} — flag {m.flags}/19{m.out_of_range ? ` (poza zakresem ${m.out_of_range})` : ""}</li>)}
              </ul>
            )}
          </div>
        )}
      </div>
      <div className="row" style={{ gap: 6 }} role="tablist" aria-label="Dzień">
        {w.days.map((x) => <button key={x.day} type="button" role="tab" aria-selected={x.day === d?.day} className={x.day === d?.day ? "btn btn--small" : "btn btn--ghost btn--small"} onClick={() => setDzien(x.day)}>D{x.day} <small>({x.meals.length})</small></button>)}
      </div>
      {d && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Dzień {d.day} <small className="dim">udziały kcal: {Math.round(suma * 100)} %{Math.abs(suma - 1) > 0.01 ? " (powinno być 100 %)" : ""}</small></h3>
          {d.meals.map((m) => (
            <div key={m.meal_id} style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
              <div className="row row--between">
                <b>{m.slot}: {m.name}</b>
                <span className="row" style={{ gap: 6 }}>
                  <small className="dim">{Math.round(m.kcal_share * 100)} %{m.flexible ? " · elastyczny" : ""}</small>
                  <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void akcja(() => api.del(`/api/diet/meals/${m.meal_id}`))}>Usuń posiłek</button>
                </span>
              </div>
              <table className="simple" style={{ fontSize: "0.85rem" }}>
                <tbody>
                  {m.ingredients.map((i) => (
                    <tr key={i.ingredient_id}>
                      <td>{i.product}</td>
                      <td>{i.grams} g</td>
                      <td className="dim">{i.class ?? "domyślna"}{i.role !== "NONE" ? ` · ${i.role}` : ""}{i.unit_g ? ` · ${i.unit_g} g/szt` : ""}{i.group ? ` · grupa ${i.group}` : ""}{i.min_factor != null || i.max_factor != null ? ` · ${i.min_factor ?? "—"}–${i.max_factor ?? "—"}×` : ""}</td>
                      <td><button type="button" className="btn btn--ghost btn--small" disabled={busy} aria-label={`Usuń ${i.product}`} onClick={() => void akcja(() => api.del(`/api/diet/ingredients/${i.ingredient_id}`))}>×</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <details>
                <summary>Dodaj składnik</summary>
                <SkladnikForm produkty={produkty} value={nowySkladnik[m.meal_id]} onChange={(v) => setNowySkladnik({ ...nowySkladnik, [m.meal_id]: v })}
                  onSubmit={(v) => void akcja(() => api.post(`/api/diet/meals/${m.meal_id}/ingredients`, {
                    product_id: v.product_id, base_grams: Number(v.base_grams), macro_role: v.macro_role,
                    scaling_class: v.scaling_class || null, unit_g: v.unit_g ? Number(v.unit_g) : null, group_name: v.group_name || null,
                  }))} />
              </details>
            </div>
          ))}
          <details style={{ marginTop: 10 }}>
            <summary>Dodaj posiłek</summary>
            <div className="field-row">
              <div><label htmlFor="pm-slot">Slot</label>
                <select id="pm-slot" value={nowyPosilek.slot} onChange={(e) => setNowyPosilek({ ...nowyPosilek, slot: e.target.value })}>{SLOTY.map((s) => <option key={s}>{s}</option>)}</select></div>
              <div><label htmlFor="pm-share">Udział kcal dnia (0–1)</label><input id="pm-share" inputMode="decimal" value={nowyPosilek.kcal_share} onChange={(e) => setNowyPosilek({ ...nowyPosilek, kcal_share: e.target.value })} /></div>
            </div>
            <label htmlFor="pm-name">Nazwa</label><input id="pm-name" value={nowyPosilek.name} onChange={(e) => setNowyPosilek({ ...nowyPosilek, name: e.target.value })} />
            <label htmlFor="pm-steps">Przepis</label><textarea id="pm-steps" rows={2} value={nowyPosilek.recipe_steps} onChange={(e) => setNowyPosilek({ ...nowyPosilek, recipe_steps: e.target.value })} />
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={nowyPosilek.flexible} onChange={(e) => setNowyPosilek({ ...nowyPosilek, flexible: e.target.checked })} /> elastyczny (domyka resztę dnia)</label>
            <button type="button" className="btn btn--small" style={{ marginTop: 6 }} disabled={busy || !nowyPosilek.name}
              onClick={() => void akcja(() => api.post(`/api/diet/weeks/${weekId}/days/${d.day}/meals`, { ...nowyPosilek, kcal_share: Number(nowyPosilek.kcal_share) }).then(() => setNowyPosilek({ ...nowyPosilek, name: "", recipe_steps: "" })))}>Dodaj posiłek</button>
          </details>
        </div>
      )}
    </div>
  );
}

type SkladnikVal = { product_id: string; base_grams: string; macro_role: string; scaling_class: string; unit_g: string; group_name: string };
const PUSTY: SkladnikVal = { product_id: "", base_grams: "100", macro_role: "NONE", scaling_class: "", unit_g: "", group_name: "" };

function SkladnikForm({ produkty, value, onChange, onSubmit }: { produkty: DietProductRow[]; value?: SkladnikVal; onChange: (v: SkladnikVal) => void; onSubmit: (v: SkladnikVal) => void }) {
  const v = value ?? PUSTY;
  const set = (k: keyof SkladnikVal, x: string) => onChange({ ...v, [k]: x });
  const wybrany = produkty.find((p) => p.id === v.product_id);
  return (
    <div>
      <div className="field-row">
        <div><label>Produkt (z bazy)</label>
          <select value={v.product_id} onChange={(e) => set("product_id", e.target.value)} aria-label="Produkt">
            <option value="">— wybierz —</option>
            {produkty.map((p) => <option key={p.id} value={p.id}>{p.name_pl} ({p.category})</option>)}
          </select>
          {wybrany && <small className="dim">{wybrany.kcal_100} kcal · B {wybrany.protein_100} T {wybrany.fat_100} W {wybrany.carbs_100} /100 g · domyślnie {wybrany.default_scaling}</small>}</div>
        <div><label>Gramy bazowe</label><input inputMode="decimal" aria-label="Gramy bazowe" value={v.base_grams} onChange={(e) => set("base_grams", e.target.value)} /></div>
      </div>
      <div className="field-row-3">
        <div><label>Rola makro</label><select aria-label="Rola makro" value={v.macro_role} onChange={(e) => set("macro_role", e.target.value)}>{["NONE", "P", "C", "F"].map((r) => <option key={r}>{r}</option>)}</select></div>
        <div><label>Klasa (puste = domyślna produktu)</label><select aria-label="Klasa skalowania" value={v.scaling_class} onChange={(e) => set("scaling_class", e.target.value)}>{KLASY.map((k) => <option key={k} value={k}>{k || "domyślna"}</option>)}</select></div>
        <div><label>g / szt. (DYSKRETNY)</label><input inputMode="decimal" aria-label="Gramy na sztukę" value={v.unit_g} onChange={(e) => set("unit_g", e.target.value)} /></div>
      </div>
      <label>Grupa (składniki skalowane razem, np. ciasto)</label><input aria-label="Grupa" value={v.group_name} onChange={(e) => set("group_name", e.target.value)} />
      <button type="button" className="btn btn--small" style={{ marginTop: 6 }} disabled={!v.product_id || !Number(v.base_grams)} onClick={() => onSubmit(v)}>Dodaj</button>
    </div>
  );
}

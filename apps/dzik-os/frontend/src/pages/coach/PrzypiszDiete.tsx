import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox, Spinner } from "../../components";
import {
  DietAssignedOut, DietDayOut, DietIngredientOut, DietLibraryMeal, DietMacroIn, DietMealOut, DietPlanOut, DietProfileRow,
  DietTemplatePreview, DietWeekRow, alergenLabel, slotLabel,
  ZapotrzebowanieMakro,
} from "../../types";
import { Alergeny, gramatura, KartaDnia, makro, NotatkiOdslony, odchylenie, StatusDiety, TagiPosilku } from "../dieta/wspolne";
import { useZapotrzebowanie } from "../wywiad/Zapotrzebowanie";

/**
 * Przepływ trenera „Przypisz dietę” (0.60.0, instrukcja §9): kafelki
 * profili → odsłony z podglądem posiłków → cel (kcal, preset makro, masa,
 * wykluczenia) → podgląd tygodnia z kolorowymi statusami, zamianą posiłku
 * z biblioteki i edycją gramatur inline (przeliczenie przez `preview`,
 * debounce) → „Przypisz” z potwierdzeniem; blokada przy dniu POZA
 * TOLERANCJĄ, chyba że trener jawnie zaznaczy „przypisz mimo ostrzeżeń”
 * (fakt zapisany w overrides).
 */
export default function PrzypiszDiete({ clientId, onPrzypisano, onAnuluj }: {
  clientId: string; onPrzypisano: (a: DietAssignedOut) => void; onAnuluj: () => void;
}) {
  const [profile, setProfile] = useState<DietProfileRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [profil, setProfil] = useState<DietProfileRow | null>(null);
  const [week, setWeek] = useState<DietWeekRow | null>(null);
  const [szablon, setSzablon] = useState<DietTemplatePreview | null>(null);
  const [kcal, setKcal] = useState("2000");
  const [mode, setMode] = useState<DietMacroIn["mode"]>("profile");
  const [manual, setManual] = useState({ P: "", F: "", C: "" });
  const [perKg, setPerKg] = useState({ protein_per_kg: "2.0", fat_per_kg: "1.0" });
  const [masa, setMasa] = useState("");
  const [alergeny, setAlergeny] = useState<Set<string>>(new Set());
  const [nielubiane, setNielubiane] = useState("");
  const [plan, setPlan] = useState<DietPlanOut | null>(null);
  const [liczenie, setLiczenie] = useState(false);
  const [overrides, setOverrides] = useState<Record<string, { grams: number }>>({});
  const [zamiany, setZamiany] = useState<Record<string, string>>({});
  const [biblioteka, setBiblioteka] = useState<{ klucz: string; slot: string; meals: DietLibraryMeal[] } | null>(null);
  const [potwierdz, setPotwierdz] = useState(false);
  const [mimo, setMimo] = useState(false);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);
  // Numer ostatniego żądania podglądu / odsłony: starsza odpowiedź, która
  // wróci po nowszej, nie może nadpisać planu (wyścig przy szybkich edycjach).
  const zadanie = useRef(0);
  const wybranaOdslona = useRef<string | null>(null);
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  useEffect(() => {
    api.get<{ profiles: DietProfileRow[] }>("/api/diet/profiles").then((d) => setProfile(d.profiles))
      .catch((e) => setError((e as Error).message));
  }, []);

  const macroBody = useCallback((): DietMacroIn => {
    if (mode === "manual") return { mode, P: Number(manual.P), F: Number(manual.F), C: Number(manual.C) };
    if (mode === "per_kg") return { mode, protein_per_kg: Number(perKg.protein_per_kg), fat_per_kg: Number(perKg.fat_per_kg) };
    return { mode: "profile" };
  }, [mode, manual, perKg]);

  const wykluczenia = useCallback(() => [
    ...alergeny, ...nielubiane.split(/[,;\n]+/).map((x) => x.trim()).filter(Boolean),
  ], [alergeny, nielubiane]);

  const przelicz = useCallback(async (ov = overrides, zm = zamiany) => {
    if (!week) return;
    const nr = ++zadanie.current;
    setLiczenie(true); setError(null);
    try {
      const r = await api.post<DietPlanOut>(`/api/diet/templates/${week.id}/preview`, {
        kcal: Number(kcal), macro: macroBody(), body_weight: masa ? Number(masa) : null,
        exclusions: wykluczenia(), overrides: ov, meal_replacements: zm,
      });
      if (nr === zadanie.current) setPlan(r);
    } catch (e) {
      if (nr === zadanie.current) setError((e as Error).message);
    } finally {
      if (nr === zadanie.current) setLiczenie(false);
    }
  }, [week, kcal, macroBody, masa, wykluczenia, overrides, zamiany]);

  function zmienGramature(day: number, m: DietMealOut, ingredientId: string, g: number) {
    const next = { ...overrides, [`${day}:${m.meal_id}:${ingredientId}`]: { grams: g } };
    setOverrides(next);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void przelicz(next, zamiany); }, 700);
  }

  async function otworzBiblioteke(day: number, m: DietMealOut) {
    if (!week) return;
    setError(null);
    try {
      const r = await api.get<{ meals: DietLibraryMeal[] }>(`/api/diet/templates/${week.id}/meals?slot=${encodeURIComponent(m.slot)}`);
      setBiblioteka({ klucz: `${day}:${m.meal_id}`, slot: m.slot, meals: r.meals.filter((x) => x.meal_id !== m.meal_id) });
    } catch (e) {
      // Błąd pobrania to nie „pusta biblioteka” — pokazujemy błąd, nie fałszywy komunikat.
      setError(`Nie udało się pobrać biblioteki posiłków: ${(e as Error).message}`);
    }
  }

  function zamienPosilek(klucz: string, mealId: string | null) {
    const next = { ...zamiany };
    if (mealId) next[klucz] = mealId; else delete next[klucz];
    setZamiany(next);
    setBiblioteka(null);
    void przelicz(overrides, next);
  }

  async function przypisz() {
    if (!week || !plan) return;
    setBusy(true); setError(null);
    try {
      const r = await api.post<DietAssignedOut>("/api/diet/assign", {
        client_id: clientId, week_id: week.id, kcal: Number(kcal), macro: macroBody(),
        body_weight: masa ? Number(masa) : null, exclusions: wykluczenia(), overrides, meal_replacements: zamiany,
        accept_warnings: mimo,
      });
      onPrzypisano(r);
    } catch (e) {
      const err = e as ApiError;
      setError(err.code === "DAY_OUT_OF_TOLERANCE" ? err.message + " Zaznacz „przypisz mimo ostrzeżeń”, jeśli to świadoma decyzja." : err.message);
      setPotwierdz(false);
    } finally { setBusy(false); }
  }

  if (error && !profile) return <ErrorBox error={error} onRetry={() => window.location.reload()} />;
  if (!profile) return <Spinner />;
  const zleDni = plan ? plan.days.filter((d) => d.status !== "OK").map((d) => d.day) : [];

  return (
    <div>
      <div className="card">
        <div className="row row--between">
          <h2 style={{ margin: 0 }}>Przypisz dietę z szablonu</h2>
          <button type="button" className="btn btn--ghost btn--small" onClick={onAnuluj}>Anuluj</button>
        </div>
        <p className="dim" style={{ marginBottom: 0 }}>Jeden szablon przelicza się na dowolną kaloryczność; klient dostaje pełny tydzień z przepisami i może wymieniać produkty.</p>
      </div>

      {/* 1. profile */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>1. Profil diety</h3>
        <div className="row" style={{ gap: 8, alignItems: "stretch" }}>
          {profile.map((p) => (
            <button key={p.id} type="button" aria-pressed={profil?.id === p.id}
              className={profil?.id === p.id ? "btn btn--small" : "btn btn--ghost btn--small"}
              style={{ whiteSpace: "normal", textAlign: "left", maxWidth: "100%" }}
              disabled={p.published_weeks === 0}
              onClick={() => { setProfil(p); setWeek(null); setSzablon(null); setPlan(null); }}>
              <b>{p.name}</b><br />
              <small>B {Math.round(p.base_macro_pct.P * 100)} / T {Math.round(p.base_macro_pct.F * 100)} / W {Math.round(p.base_macro_pct.C * 100)} % · odsłon: {p.published_weeks}</small>
            </button>
          ))}
        </div>
        {profile.every((p) => p.published_weeks === 0) && <p className="dim">Brak opublikowanych odsłon — dodaj je w panelu szablonów diet.</p>}
      </div>

      {/* 2. odsłony */}
      {profil && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>2. Odsłona tygodnia</h3>
          <div className="row" style={{ gap: 6 }}>
            {profil.weeks.filter((w) => w.status === "PUBLISHED").map((w) => (
              <button key={w.id} type="button" aria-pressed={week?.id === w.id}
                className={week?.id === w.id ? "btn btn--small" : "btn btn--ghost btn--small"}
                style={{ whiteSpace: "normal", textAlign: "left", maxWidth: "100%" }}
                onClick={() => {
                  setWeek(w); setPlan(null); setOverrides({}); setZamiany({}); setSzablon(null);
                  wybranaOdslona.current = w.id;
                  api.get<DietTemplatePreview>(`/api/diet/templates/${w.id}`)
                    .then((r) => { if (wybranaOdslona.current === w.id) setSzablon(r); })
                    .catch((e) => { if (wybranaOdslona.current === w.id) setError((e as Error).message); });
                }}>
                Odsłona {w.variant_no}{w.name ? ` · ${w.name}` : ""} <small>({w.kcal_min}–{w.kcal_max} kcal)</small>
              </button>
            ))}
          </div>
          {szablon && szablon.week_id === week?.id && <NotatkiOdslony n={szablon} />}
          {szablon && szablon.week_id === week?.id && (
            <details style={{ marginTop: 8 }}>
              <summary>Posiłki tygodnia (podgląd bez gramatur)</summary>
              {szablon.days.map((d) => (
                <div key={d.day} style={{ fontSize: "0.85rem", marginTop: 4 }}>
                  <b>Dzień {d.day}:</b> {d.meals.map((m) => `${slotLabel(m.slot)}: ${m.name}${m.allergens && m.allergens.length > 0 ? ` (${m.allergens.map(alergenLabel).join(", ")})` : ""}`).join(" · ")}
                </div>
              ))}
            </details>
          )}
        </div>
      )}

      {/* 3. cel */}
      {week && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>3. Cel</h3>
          <div className="field-row">
            <div><label htmlFor="pd-kcal">kcal / dzień</label>
              <input id="pd-kcal" inputMode="numeric" value={kcal} onChange={(e) => setKcal(e.target.value)} />
              <ZaproponujKcal clientId={clientId} onPropozycja={(k, m, mk) => {
                setKcal(String(k));
                if (m && !masa) setMasa(String(m));
                // Makro z wywiadu wchodzi jako preset „ręcznie” (gramy) — specyfikacja §5.5.
                if (mk) { setMode("manual"); setManual({ P: String(mk.bialko_g), F: String(mk.tluszcz_g), C: String(mk.wegle_g) }); }
              }} /></div>
            <div><label htmlFor="pd-masa">Masa ciała (kg, do presetu na kg)</label>
              <input id="pd-masa" inputMode="decimal" value={masa} onChange={(e) => setMasa(e.target.value)} /></div>
          </div>
          {(Number(kcal) < week.kcal_min || Number(kcal) > week.kcal_max) && (
            <p className="alert alert--warn">Poza zakresem ważności szablonu ({week.kcal_min}–{week.kcal_max} kcal) — silnik policzy, ale wynik może wymagać ręcznej korekty.</p>
          )}
          <label>Preset makro</label>
          <div className="row" role="radiogroup" aria-label="Preset makro" style={{ gap: 6 }}>
            {([["profile", "z profilu"], ["per_kg", "na kg masy ciała"], ["manual", "ręcznie (g)"]] as const).map(([k, l]) => (
              <button key={k} type="button" role="radio" aria-checked={mode === k}
                className={mode === k ? "btn btn--small" : "btn btn--ghost btn--small"} onClick={() => setMode(k)}>{l}</button>
            ))}
          </div>
          {mode === "manual" && (
            <div className="field-row-3">
              {(["P", "F", "C"] as const).map((k) => (
                <div key={k}><label htmlFor={`pd-${k}`}>{{ P: "Białko (g)", F: "Tłuszcz (g)", C: "Węgle (g)" }[k]}</label>
                  <input id={`pd-${k}`} inputMode="numeric" value={manual[k]} onChange={(e) => setManual({ ...manual, [k]: e.target.value })} /></div>
              ))}
            </div>
          )}
          {mode === "per_kg" && (
            <div className="field-row">
              <div><label htmlFor="pd-pkg">Białko g/kg</label><input id="pd-pkg" inputMode="decimal" value={perKg.protein_per_kg} onChange={(e) => setPerKg({ ...perKg, protein_per_kg: e.target.value })} /></div>
              <div><label htmlFor="pd-fkg">Tłuszcz g/kg</label><input id="pd-fkg" inputMode="decimal" value={perKg.fat_per_kg} onChange={(e) => setPerKg({ ...perKg, fat_per_kg: e.target.value })} /></div>
            </div>
          )}
          <label>Wykluczenia (alergeny / diety)</label>
          <div className="row" style={{ gap: 6 }}>
            {(["gluten", "mleko", "lactose", "jaja", "orzechy", "orzechy_ziemne", "ryby", "skorupiaki", "soja", "sezam", "gorczyca", "meat", "dairy", "fish", "egg"] as const).map((a) => (
              <button key={a} type="button" aria-pressed={alergeny.has(a)} className={alergeny.has(a) ? "btn btn--small" : "btn btn--ghost btn--small"}
                onClick={() => setAlergeny((s) => { const n = new Set(s); if (n.has(a)) n.delete(a); else n.add(a); return n; })}>{a}</button>
            ))}
          </div>
          <label htmlFor="pd-nielubiane">Nielubiane produkty (nazwy z bazy, po przecinku)</label>
          <input id="pd-nielubiane" value={nielubiane} placeholder="np. Brokuł, Awokado" onChange={(e) => setNielubiane(e.target.value)} />
          <button type="button" className="btn" style={{ marginTop: 10 }} disabled={liczenie || !Number(kcal)} onClick={() => void przelicz()}>
            {liczenie ? "Liczę…" : plan ? "Przelicz ponownie" : "Przelicz tydzień"}
          </button>
          <ErrorBox error={error} />
        </div>
      )}

      {/* 4–6. podgląd tygodnia */}
      {plan && week && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>4. Podgląd tygodnia</h3>
            <p className="dim">Cel dnia: {makro(plan.target)}. Dni OK: {plan.summary.days_ok}/{plan.summary.days}; posiłki z flagą: {plan.summary.meals_flagged}/{plan.summary.meals}.
              {liczenie && " Przeliczam…"}</p>
            {plan.warnings.map((w) => <p key={w} className="alert alert--warn">{w}</p>)}
          </div>
          {plan.days.map((d) => (
            <KartaDnia key={d.day} d={d}>
              {d.status !== "OK" && <small className="dim"> {odchylenie(d.deviation)}</small>}
              {d.meals.map((m) => (
                <PosilekEdycja key={m.meal_id} d={d} m={m} overrides={overrides} zamiana={zamiany[`${d.day}:${m.meal_id}`]}
                  onGram={(iid, g) => zmienGramature(d.day, m, iid, g)}
                  onBiblioteka={() => void otworzBiblioteke(d.day, m)}
                  onCofnij={() => zamienPosilek(`${d.day}:${m.meal_id}`, null)} />
              ))}
            </KartaDnia>
          ))}
          {biblioteka && (
            <div className="card" role="dialog" aria-label="Zamień na inny posiłek">
              <div className="row row--between"><h3 style={{ margin: 0 }}>Zamień na inny posiłek ({slotLabel(biblioteka.slot)})</h3>
                <button type="button" className="btn btn--ghost btn--small" onClick={() => setBiblioteka(null)}>Zamknij</button></div>
              {biblioteka.meals.length === 0 && <p className="dim">Brak innych posiłków w tym slocie w bibliotece tego profilu.</p>}
              <ul style={{ paddingLeft: 18 }}>
                {biblioteka.meals.map((x) => (
                  <li key={x.meal_id} style={{ marginBottom: 6 }}>
                    <b>{x.name}</b> <small className="dim">(odsłona {x.variant_no}, dzień {x.day_no}; {x.ingredients.slice(0, 4).join(", ")}{x.ingredients.length > 4 ? "…" : ""})</small>{" "}
                    <button type="button" className="btn btn--small" onClick={() => zamienPosilek(biblioteka.klucz, x.meal_id)}>Wybierz i przelicz</button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="card">
            <h3 style={{ marginTop: 0 }}>6. Przypisz</h3>
            {zleDni.length > 0 && (
              <p className="alert alert--warn">Dni poza tolerancją: {zleDni.join(", ")}. Popraw gramatury lub zamień posiłki — albo przypisz świadomie mimo ostrzeżeń (fakt zostanie zapisany).</p>
            )}
            {zleDni.length > 0 && (
              <label style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--text)" }}>
                <input type="checkbox" checked={mimo} onChange={(e) => setMimo(e.target.checked)} /> przypisz mimo ostrzeżeń
              </label>
            )}
            {!potwierdz ? (
              <button type="button" className="btn" disabled={liczenie || (zleDni.length > 0 && !mimo)} onClick={() => setPotwierdz(true)}>Przypisz</button>
            ) : (
              <div role="alertdialog" aria-labelledby="pd-potwierdz" className="alert alert--info">
                <span id="pd-potwierdz">Przypisać dietę „{week.name || `odsłona ${week.variant_no}`}” ({kcal} kcal) klientowi? Poprzednia dieta z szablonu (jeśli była) trafi do archiwum, klient zobaczy nową od razu.</span>
                <div className="row" style={{ marginTop: 6, gap: 6 }}>
                  <button type="button" className="btn btn--small" disabled={busy} onClick={() => void przypisz()}>{busy ? "Przypisuję…" : "Tak, przypisz"}</button>
                  <button type="button" className="btn btn--ghost btn--small" onClick={() => setPotwierdz(false)}>Wróć</button>
                </div>
              </div>
            )}
            <ErrorBox error={error} />
          </div>
        </>
      )}
    </div>
  );
}

function PosilekEdycja({ d, m, overrides, zamiana, onGram, onBiblioteka, onCofnij }: {
  d: DietDayOut; m: DietMealOut; overrides: Record<string, { grams: number }>; zamiana?: string;
  onGram: (ingredientId: string, grams: number) => void; onBiblioteka: () => void; onCofnij: () => void;
}) {
  const [otwarte, setOtwarte] = useState(m.status !== "OK");
  // Surowy tekst pól gramatur: pozwala wpisać „12,5” i chwilowo puste pole,
  // a do podglądu trafia tylko poprawna liczba > 0.
  const [tekst, setTekst] = useState<Record<string, string>>({});
  function wpisz(i: DietIngredientOut, key: string, v: string) {
    setTekst((t) => ({ ...t, [key]: v }));
    const g = Number(v.replace(",", "."));
    if (v.trim() !== "" && Number.isFinite(g) && g > 0) onGram(i.ingredient_id, g);
  }
  return (
    <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
      <div className="row row--between">
        <div><b>{slotLabel(m.slot)}: {m.name}</b> <TagiPosilku m={m} /> {zamiana && <span className="badge badge--accent">zamieniony</span>}</div>
        <StatusDiety s={m.status} />
      </div>
      <small className="dim">{makro(m.macros)} · cel {makro(m.target)}{m.status !== "OK" ? ` · ${odchylenie(m.deviation)}` : ""}</small>
      <Alergeny a={m.allergens} />
      <div className="row" style={{ gap: 6, marginTop: 4 }}>
        <button type="button" className="btn btn--ghost btn--small" aria-expanded={otwarte} onClick={() => setOtwarte((o) => !o)}>{otwarte ? "Ukryj składniki" : "Składniki i gramatury"}</button>
        <button type="button" className="btn btn--ghost btn--small" onClick={onBiblioteka}>Zamień na inny posiłek</button>
        {zamiana && <button type="button" className="btn btn--ghost btn--small" onClick={onCofnij}>Cofnij zamianę</button>}
      </div>
      {otwarte && (
        <table className="simple" style={{ marginTop: 6, fontSize: "0.85rem" }}>
          <tbody>
            {m.ingredients.map((i) => {
              const key = `${d.day}:${m.meal_id}:${i.ingredient_id}`;
              const staly = i.class === "STAŁY";
              return (
                <tr key={i.ingredient_id}>
                  <td>{i.product} <small className="dim">({i.class.toLowerCase()}{i.role !== "NONE" ? `, rola ${i.role}` : ""})</small></td>
                  <td style={{ width: 130 }}>
                    {staly ? <span className="dim">{gramatura(i)}</span> : (
                      <input inputMode="decimal" aria-label={`${i.product} — gramy`}
                        value={tekst[key] ?? String(overrides[key]?.grams ?? Math.round(i.grams))}
                        onChange={(e) => wpisz(i, key, e.target.value)} style={{ padding: "4px 6px" }} />
                    )}
                  </td>
                  <td className="dim">{i.units != null ? gramatura(i) : ""}{overrides[key] ? " · korekta" : ""}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function PrzypisanaDietaTrenera({ clientId, onZmiana }: { clientId: string; onZmiana: () => void }) {
  const [dane, setDane] = useState<{ assigned: DietAssignedOut | null; history: { id: string; version: number; status: string; kcal: number; created_at: string }[];
    swap_events: { id: string; day: number; from: string; to: string; from_grams: number; to_grams: number; created_at: string; tier?: 1 | 2 | null }[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bladZapisu, setBladZapisu] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dzien, setDzien] = useState(1);
  const zaladuj = useCallback(() => {
    api.get<typeof dane>(`/api/diet/clients/${clientId}/current`).then((d) => setDane(d as NonNullable<typeof dane>)).catch((e) => setError((e as Error).message));
  }, [clientId]);
  useEffect(zaladuj, [zaladuj]);
  if (error) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (!dane || !dane.assigned) return null;
  const a = dane.assigned;
  const d = a.plan.days.find((x) => x.day === dzien) ?? a.plan.days[0];
  // Zapis blokady: rodzic przeładowuje komponent (key) dopiero po sukcesie —
  // inaczej komunikat błędu znikałby razem ze stanem.
  async function zapisz(body: Record<string, unknown>) {
    setBusy(true); setBladZapisu(null);
    try {
      await api.patch(`/api/diet/assigned/${a.id}`, body);
      zaladuj(); onZmiana();
    } catch (e) { setBladZapisu((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="card">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}>Dieta z szablonu: {a.profile} — {a.week_name || `odsłona`}</h2>
        <span className="badge badge--ok">v{a.version}</span>
      </div>
      <small className="dim">{makro(a.target)} · przypisano {plDateTime(a.created_at)} · preset: {a.macro_mode}{a.exclusions.length ? ` · wykluczenia: ${a.exclusions.join(", ")}` : ""}</small>
      {a.plan.overrides?.accepted_warnings && <p className="alert alert--warn">Przypisano mimo ostrzeżeń (dni: {(a.plan.overrides.accepted_days ?? []).join(", ")}).</p>}
      <div className="row" style={{ gap: 6, marginTop: 8 }}>
        {a.plan.days.map((x) => <button key={x.day} type="button" aria-pressed={x.day === d.day} className={x.day === d.day ? "btn btn--small" : "btn btn--ghost btn--small"} onClick={() => setDzien(x.day)}>D{x.day}</button>)}
        <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void zapisz({ swaps_enabled: !a.swaps_enabled })}>{a.swaps_enabled ? "Zablokuj wymiany klienta" : "Odblokuj wymiany klienta"}</button>
      </div>
      <ErrorBox error={bladZapisu} />
      <KartaDnia d={d}>
        {d.meals.map((m) => (
          <div key={m.meal_id} style={{ marginTop: 6, fontSize: "0.9rem" }}>
            <b>{slotLabel(m.slot)}: {m.name}</b> <StatusDiety s={m.status} /> <small className="dim">{makro(m.macros)}</small>
            {m.swaps_locked && <span className="badge badge--warn" style={{ marginLeft: 4 }}>wymiany zablokowane</span>}{" "}
            <button type="button" className="btn btn--ghost btn--small" disabled={busy} aria-label={`${m.swaps_locked ? "Odblokuj" : "Zablokuj"} wymiany w posiłku ${m.name}`}
              onClick={() => void zapisz({ day: d.day, meal_id: m.meal_id, meal_swaps_enabled: !!m.swaps_locked })}>{m.swaps_locked ? "odblokuj wymiany" : "zablokuj wymiany"}</button>
            <div className="dim" style={{ fontSize: "0.85rem" }}>{m.ingredients.map((i) => `${i.product} ${gramatura(i)}${i.override ? " (zm.)" : ""}`).join(" · ")}</div>
          </div>
        ))}
      </KartaDnia>
      {dane.swap_events.length > 0 && (
        <details>
          <summary>Historia wymian klienta ({dane.swap_events.length})</summary>
          <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
            {dane.swap_events.map((s) => <li key={s.id}>D{s.day}: {s.from} {Math.round(s.from_grams)} g → {s.to} {Math.round(s.to_grams)} g
              {s.tier ? <span className={s.tier === 2 ? "badge" : "badge badge--ok"} style={{ marginLeft: 4 }}>{s.tier === 2 ? "grupa pokrewna" : "ta sama grupa"}</span> : null} · {plDateTime(s.created_at)}</li>)}
          </ul>
        </details>
      )}
      {dane.history.length > 1 && <small className="dim">Wersje: {dane.history.map((h) => `v${h.version} (${h.kcal} kcal, ${h.status.toLowerCase()})`).join(", ")}</small>}
    </div>
  );
}

/** „Użyj w przypisaniu diety” (specyfikacja §6.2): wypełnia pole kcal wynikiem
 * wywiadu (nadpisanie trenera ma pierwszeństwo), masę ciała i — gdy bilans ma
 * makro startowe — preset „ręcznie” z gramami. Nie przypisuje diety: to nadal
 * decyzja i osobny przycisk trenera. Brak wyniku / moduł wyłączony = przycisk
 * się nie pokazuje. */
function ZaproponujKcal({ clientId, onPropozycja }: {
  clientId: string;
  onPropozycja: (kcal: number, masaKg: number | null, makro: ZapotrzebowanieMakro | null) => void;
}) {
  const { dane } = useZapotrzebowanie(clientId);
  const e = dane?.status === "ok" ? dane.estimate : null;
  if (!e) return null;
  const makro = e.macro ?? null;
  return (
    <small className="dim" style={{ display: "block", marginTop: 4 }}>
      Z wywiadu: ≈ {e.kcal_effective} kcal{e.override ? " (ustalenie trenera)" : " (wzór)"}
      {makro ? ` · makro B ${makro.bialko_g} / T ${makro.tluszcz_g} / W ${makro.wegle_g} g` : ""}
      {" "}— samo wstawienie nie przypisuje diety.{" "}
      <button type="button" className="btn btn--ghost btn--small"
        aria-label={`Użyj w przypisaniu diety: wstaw ${e.kcal_effective} kcal${makro ? " i makro" : ""} do formularza`}
        onClick={() => onPropozycja(e.kcal_effective, e.inputs.masa_kg ?? null, makro)}>
        {makro ? "Użyj w przypisaniu diety" : "Zaproponuj kcal"}
      </button>
    </small>
  );
}

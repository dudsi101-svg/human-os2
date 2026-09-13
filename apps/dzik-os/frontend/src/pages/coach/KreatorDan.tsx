import { useEffect, useState } from "react";
import { api, ApiError } from "../../api";
import { ErrorBox } from "../../components";
import {
  CoachClientRow,
  KulinariaPlan,
  KulinariaProfil,
  KulinariaReceptura,
  KulinariaRecepturaPelna,
  KulinariaStatus,
  KulinariaWynik,
  KulinariaZamianaPodglad,
} from "../../types";

/**
 * Kreator dań (0.57.0): menu z CAŁYCH receptur w zatwierdzonych porcjach —
 * silnik referencyjny właściciela, bez modelu językowego.
 *
 * Wszystko tutaj jest propozycją: „Policz” niczego nie zapisuje; „Zapisz do
 * klienta” tworzy nową wersję planu diety ze śladem decyzji (klient zobaczy
 * „Dlaczego to danie?”). Statusy silnika są odpowiedzią, nie błędem:
 * brak pokrycia po filtrach pokazujemy słowami zamiast omijać filtr
 * publikacji. Tryb produkcyjny liczy makro wyłącznie z receptur
 * opublikowanych po testach — dopóki nie ma żadnej, uczciwie zwraca
 * „za mało receptur”.
 */

const STATUSY: Record<KulinariaStatus, [string, string, "ok" | "warn" | "danger"]> = {
  draft_preview: ["Podgląd kulinarny (szkice)",
    "Menu ułożone ze szkiców receptur — bez wartości odżywczych, bo nie ma jeszcze receptur "
    + "opublikowanych po testach. Do przeglądu i pracy kuchennej, nie do oceny makro.", "warn"],
  ready_within_declared_bounds: ["Gotowe w zadeklarowanych granicach",
    "Każdy dzień mieści się w granicach z celów klienta i tolerancji trenera; wartości z "
    + "opublikowanych receptur i wbudowanej bazy produktów.", "ok"],
  needs_input: ["Brakuje danych wejściowych", "Silnik nie policzył menu — popraw wskazane pole.", "danger"],
  needs_review: ["Wymaga przeglądu specjalisty",
    "Zakres nie został potwierdzony (dorosły, bez ciąży/karmienia, bez diety leczniczej, przy "
    + "ograniczeniu węglowodanów — bez leków glikemicznych). Kreator nie układa menu poza zakresem.", "warn"],
  nutrition_unverified: ["Bez zweryfikowanych wartości",
    "Menu low carb / keto wymaga wartości odżywczych z opublikowanych receptur — podgląd ze szkiców "
    + "nie może twierdzić, że limit węglowodanów jest spełniony.", "warn"],
  insufficient_catalog: ["Za mało receptur po filtrach",
    "Po zastosowaniu diety, alergenów, wykluczeń, czasu i statusu publikacji któryś posiłek nie ma "
    + "kandydatów. To brak pokrycia, nie błąd — poluzuj filtry albo opublikuj receptury.", "danger"],
  search_exhausted: ["Nie znaleziono układu w ograniczonym przeszukiwaniu",
    "Silnik przeszukał ograniczoną liczbę kombinacji i nie złożył dnia w granicach. To nie dowód, "
    + "że menu jest niemożliwe — poszerz tolerancję, limit powtórzeń rodzin albo katalog.", "warn"],
  validation_failed: ["Niezależna kontrola odrzuciła plan", "Zgłoś to jako błąd — plan nie został zwrócony.", "danger"],
};

const ALERGENY_PL: Record<string, string> = {
  gluten: "gluten", milk: "mleko", eggs: "jaja", fish: "ryby", soy: "soja", nuts: "orzechy", sesame: "sezam",
};
const OSIE_PL: Record<string, Record<string, string>> = {
  animal_policy: { omnivore: "wszystko", vegetarian: "wegetariańska", pescetarian: "peskatariańska", vegan: "wegańska" },
  pattern: { balanced: "zbilansowana", mediterranean: "śródziemnomorska", paleo_classic_v1: "paleo (klasyczne)" },
  carb_policy: { standard: "standardowe", low_carb: "low carb", ketogenic: "ketogeniczne" },
};
const ZAKRES_PL: Record<string, string> = {
  adult: "klient jest osobą dorosłą",
  no_pregnancy_or_breastfeeding: "nie jest w ciąży ani nie karmi piersią",
  no_medical_diet: "nie ma zaleconej diety leczniczej",
  no_glucose_meds_or_diabetes: "nie ma cukrzycy ani leków wpływających na glikemię",
};

interface Formularz {
  tryb: "preview" | "production";
  client_id: string;
  days: string;
  meal_count: string;
  animal_policy: string;
  pattern: string;
  carb_policy: string;
  carb_limit_g: string;
  carb_basis: string;
  start_date: string;
  max_total_minutes: string;
  max_active_minutes: string;
  max_family_uses_per_week: string;
  allergens: Set<string>;
  equipment: Set<string>;
  excluded: string;
  zakres: Record<string, boolean>;
  tol_kcal: string;
  tol_macro: string;
}

const START: Formularz = {
  tryb: "preview", client_id: "", days: "7", meal_count: "3", animal_policy: "omnivore", pattern: "balanced",
  carb_policy: "standard", carb_limit_g: "", carb_basis: "available_excluding_fiber", start_date: "",
  max_total_minutes: "30", max_active_minutes: "20", max_family_uses_per_week: "2",
  allergens: new Set(), equipment: new Set(["scale", "hob", "pan", "bowl", "pot", "lid"]), excluded: "",
  zakres: { adult: false, no_pregnancy_or_breastfeeding: false, no_medical_diet: false, no_glucose_meds_or_diabetes: false },
  tol_kcal: "5", tol_macro: "10",
};

function cialo(f: Formularz) {
  return {
    tryb: f.tryb, client_id: f.client_id || null, days: Number(f.days), meal_count: Number(f.meal_count),
    animal_policy: f.animal_policy, pattern: f.pattern, carb_policy: f.carb_policy,
    carb_limit_g: f.carb_policy === "standard" || !f.carb_limit_g ? null : Number(f.carb_limit_g),
    carb_basis: f.carb_policy === "standard" ? null : f.carb_basis,
    start_date: f.start_date || null,
    max_total_minutes: Number(f.max_total_minutes), max_active_minutes: Number(f.max_active_minutes),
    max_family_uses_per_week: Number(f.max_family_uses_per_week),
    allergens: Array.from(f.allergens), equipment: Array.from(f.equipment),
    excluded_ingredient_ids: f.excluded.split(/[,\s]+/).map((x) => x.trim()).filter(Boolean),
    zakres: f.zakres,
    tolerance_pct: f.tryb === "production" ? { kcal: Number(f.tol_kcal), macro: Number(f.tol_macro) } : null,
  };
}

function uwagi(issues: unknown[]): string[] {
  return issues.map((x) => {
    if (typeof x === "string") return x;
    if (x && typeof x === "object") {
      const o = x as Record<string, unknown>;
      const odrzucone = o.rejected && typeof o.rejected === "object"
        ? Object.entries(o.rejected as Record<string, number>).map(([k, v]) => `${k}: ${v}`).join(", ") : "";
      return [o.code, o.message, o.day_index !== undefined ? `dzień ${Number(o.day_index) + 1}` : "", odrzucone]
        .filter(Boolean).join(" · ");
    }
    return String(x);
  });
}

export default function KreatorDan() {
  const [profil, setProfil] = useState<KulinariaProfil | null>(null);
  const [clients, setClients] = useState<CoachClientRow[]>([]);
  const [f, setF] = useState<Formularz>(START);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wynik, setWynik] = useState<KulinariaWynik | null>(null);
  const [potwierdzam, setPotwierdzam] = useState(false);
  const [tytul, setTytul] = useState("");
  const [zapisano, setZapisano] = useState<{ id: string; version_no: number; traces: number } | null>(null);
  const [zapisMsg, setZapisMsg] = useState<string | null>(null);
  const [otwarte, setOtwarte] = useState<string | null>(null);
  const [sekcja, setSekcja] = useState<"kreator" | "receptury">("kreator");

  useEffect(() => {
    api.get<KulinariaProfil>("/api/coach/kulinaria/profile").then(setProfil).catch((e) => setError((e as Error).message));
    api.get<{ clients: CoachClientRow[] }>("/api/coach/clients").then((r) => setClients(r.clients)).catch(() => setClients([]));
  }, []);

  const set = <K extends keyof Formularz>(k: K, v: Formularz[K]) => setF((s) => ({ ...s, [k]: v }));
  const toggleSet = (k: "allergens" | "equipment", id: string) => setF((s) => {
    const n = new Set(s[k]); if (n.has(id)) n.delete(id); else n.add(id); return { ...s, [k]: n };
  });

  async function policz() {
    setBusy(true); setError(null); setWynik(null); setZapisano(null); setZapisMsg(null);
    try {
      setWynik(await api.post<KulinariaWynik>("/api/coach/kulinaria/generuj", cialo(f)));
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function zapisz() {
    if (!f.client_id) { setZapisMsg("Wybierz klienta, żeby zapisać menu jako wersję jego planu diety."); return; }
    setBusy(true); setZapisMsg(null);
    try {
      const r = await api.post<{ id: string; version_no: number; traces: number }>("/api/coach/kulinaria/zapisz", {
        ...cialo(f), client_id: f.client_id, title: tytul || null, potwierdzam_szkice: potwierdzam,
      });
      setZapisano(r);
      setZapisMsg(`Zapisano jako wersja v${r.version_no} planu diety klienta (${r.traces} śladów decyzji — klient zobaczy „Dlaczego to danie?”).`);
    } catch (e) {
      const err = e as ApiError;
      setZapisMsg(err.code === "DRAFT_CONFIRMATION_REQUIRED"
        ? "To podgląd ze szkiców bez wartości odżywczych — zaznacz potwierdzenie, jeśli mimo to chcesz go zapisać klientowi."
        : err.message);
    } finally { setBusy(false); }
  }

  const st = wynik ? STATUSY[wynik.status] ?? [wynik.status, "", "warn"] : null;
  const tryb = f.tryb;

  return (
    <>
      <div className="card card--accent">
        <h2>Ułóż z dań</h2>
        <p className="dim" style={{ marginTop: -6, fontSize: "0.85rem" }}>
          Całe receptury w zatwierdzonych porcjach, bez dokładania składników pod makro.
          Podgląd nic nie zapisuje; zapis tworzy nową wersję planu diety klienta ze śladem decyzji.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(["kreator", "receptury"] as const).map((id) => (
            <button key={id} className={"btn btn--small" + (sekcja === id ? "" : " btn--ghost")}
              aria-pressed={sekcja === id} onClick={() => setSekcja(id)}>
              {id === "kreator" ? "Menu dla klienta" : "Biblioteka receptur"}
            </button>
          ))}
        </div>
        {profil && (
          <p className="dim" style={{ fontSize: "0.85rem", marginBottom: 0 }}>
            Receptury: {profil.receptury.razem} (opublikowane po testach: {profil.receptury.wg_statusu.published ?? 0},
            szkice: {profil.receptury.wg_statusu.draft ?? 0}). Produkty pakietu z wartościami z wbudowanej
            bazy: {profil.mapowanie.z_wartosciami}/{profil.mapowanie.produkty} (mapowanie: {profil.mapowanie.status}).
            Silnik {profil.versions.engine}.
          </p>
        )}
      </div>
      {error && <ErrorBox error={error} />}

      {sekcja === "receptury" && profil && <Receptury profil={profil} onZmiana={() =>
        api.get<KulinariaProfil>("/api/coach/kulinaria/profile").then(setProfil).catch(() => undefined)} />}

      {sekcja === "kreator" && (
        <>
          <div className="card">
            <h2>Parametry</h2>
            <div className="field-row">
              <div><label htmlFor="kd-tryb">Tryb</label>
                <select id="kd-tryb" value={f.tryb} onChange={(e) => set("tryb", e.target.value as Formularz["tryb"])}>
                  <option value="preview">podgląd kulinarny (szkice, bez makro)</option>
                  <option value="production">produkcyjny (tylko opublikowane, z makro)</option>
                </select></div>
              <div><label htmlFor="kd-klient">Klient {tryb === "production" ? "(wymagany — cele z jego planu)" : "(do zapisu)"}</label>
                <select id="kd-klient" value={f.client_id} onChange={(e) => set("client_id", e.target.value)}>
                  <option value="">— wybierz —</option>
                  {clients.map((c) => <option key={c.client_id} value={c.client_id}>{c.display_name}</option>)}
                </select></div>
            </div>
            <div className="field-row-3">
              <div><label htmlFor="kd-dni">Dni</label>
                <input id="kd-dni" type="number" min="1" max="31" value={f.days} onChange={(e) => set("days", e.target.value)} /></div>
              <div><label htmlFor="kd-posilki">Posiłków dziennie</label>
                <select id="kd-posilki" value={f.meal_count} onChange={(e) => set("meal_count", e.target.value)}>
                  {["2", "3", "4", "5", "6"].map((n) => <option key={n}>{n}</option>)}
                </select></div>
              <div><label htmlFor="kd-start">Start (opcjonalnie)</label>
                <input id="kd-start" type="date" value={f.start_date} onChange={(e) => set("start_date", e.target.value)} /></div>
            </div>
            <div className="field-row-3">
              {(["animal_policy", "pattern", "carb_policy"] as const).map((os) => (
                <div key={os}><label htmlFor={`kd-${os}`}>
                  {os === "animal_policy" ? "Produkty zwierzęce" : os === "pattern" ? "Wzorzec" : "Węglowodany"}</label>
                  <select id={`kd-${os}`} value={f[os]} onChange={(e) => set(os, e.target.value)}>
                    {(profil?.osie[os] ?? Object.keys(OSIE_PL[os])).map((v) => <option key={v} value={v}>{OSIE_PL[os][v] ?? v}</option>)}
                  </select></div>
              ))}
            </div>
            {f.carb_policy !== "standard" && (
              <div className="field-row">
                <div><label htmlFor="kd-limit">Limit węglowodanów (g/dzień)</label>
                  <input id="kd-limit" type="number" min="1" max="600" value={f.carb_limit_g}
                    onChange={(e) => set("carb_limit_g", e.target.value)} /></div>
                <div><label htmlFor="kd-basis">Definicja</label>
                  <select id="kd-basis" value={f.carb_basis} onChange={(e) => set("carb_basis", e.target.value)}>
                    <option value="available_excluding_fiber">dostępne (bez błonnika)</option>
                    <option value="total_including_fiber">ogółem (z błonnikiem)</option>
                  </select></div>
              </div>
            )}
            <div className="field-row-3">
              <div><label htmlFor="kd-czas">Maks. czas posiłku (min)</label>
                <input id="kd-czas" type="number" min="5" max="240" value={f.max_total_minutes}
                  onChange={(e) => set("max_total_minutes", e.target.value)} /></div>
              <div><label htmlFor="kd-aktywny">W tym aktywnie (min)</label>
                <input id="kd-aktywny" type="number" min="5" max="240" value={f.max_active_minutes}
                  onChange={(e) => set("max_active_minutes", e.target.value)} /></div>
              <div><label htmlFor="kd-rodziny">Ta sama rodzina dań maks. razy / tydz.</label>
                <input id="kd-rodziny" type="number" min="1" max="42" value={f.max_family_uses_per_week}
                  onChange={(e) => set("max_family_uses_per_week", e.target.value)} /></div>
            </div>
            <label>Alergeny klienta</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {(profil?.alergeny ?? Object.keys(ALERGENY_PL)).map((a) => (
                <label key={a} className="badge" style={{ cursor: "pointer", opacity: f.allergens.has(a) ? 1 : 0.6 }}>
                  <input type="checkbox" checked={f.allergens.has(a)} onChange={() => toggleSet("allergens", a)}
                    style={{ marginRight: 4 }} aria-label={`Alergen: ${ALERGENY_PL[a] ?? a}`} />
                  {ALERGENY_PL[a] ?? a}
                </label>
              ))}
            </div>
            <p className="dim" style={{ fontSize: "0.8rem" }}>
              Produkty złożone bez etykiety (pieczywo, hummus, tortilla…) mają nieznany skład alergenów —
              przy zadeklarowanej alergii odpadają, bo „nieznane” nie znaczy „bezpieczne”.
            </p>
            <label>Sprzęt w kuchni</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {(profil?.sprzet ?? []).map((s) => (
                <label key={s.id} className="badge" style={{ cursor: "pointer", opacity: f.equipment.has(s.id) ? 1 : 0.6 }}>
                  <input type="checkbox" checked={f.equipment.has(s.id)} onChange={() => toggleSet("equipment", s.id)}
                    style={{ marginRight: 4 }} aria-label={`Sprzęt: ${s.label}`} />
                  {s.label}
                </label>
              ))}
            </div>
            <label htmlFor="kd-wykluczone" style={{ marginTop: 8 }}>Wykluczone produkty (identyfikatory, po przecinku)</label>
            <input id="kd-wykluczone" value={f.excluded} placeholder="np. mushroom, tofu"
              onChange={(e) => set("excluded", e.target.value)} list="kd-produkty" />
            <datalist id="kd-produkty">{(profil?.produkty ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</datalist>

            <h3 style={{ marginBottom: 4 }}>Zakres — poświadczenia trenera</h3>
            <p className="dim" style={{ marginTop: 0, fontSize: "0.85rem" }}>
              Silnik układa menu tylko w zakresie ogólnym. Bez każdego z tych potwierdzeń wynik to
              „wymaga przeglądu specjalisty” — nie jest to kwestionariusz kliniczny.
            </p>
            {Object.keys(ZAKRES_PL).map((k) => (
              <label key={k} style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
                <input type="checkbox" checked={f.zakres[k]}
                  onChange={(e) => set("zakres", { ...f.zakres, [k]: e.target.checked })} />
                {ZAKRES_PL[k]}
              </label>
            ))}
            {tryb === "production" && (
              <>
                <h3 style={{ marginBottom: 4 }}>Granice dzienne</h3>
                <p className="dim" style={{ marginTop: 0, fontSize: "0.85rem" }}>
                  Cele (kcal, białko, tłuszcz, węglowodany) pochodzą z aktywnej wersji planu diety klienta;
                  Ty podajesz tolerancję. Węglowodany planu są traktowane jako dostępne (bez błonnika).
                </p>
                <div className="field-row">
                  <div><label htmlFor="kd-tk">Tolerancja kcal (%)</label>
                    <input id="kd-tk" type="number" min="1" max="50" value={f.tol_kcal} onChange={(e) => set("tol_kcal", e.target.value)} /></div>
                  <div><label htmlFor="kd-tm">Tolerancja makro (%)</label>
                    <input id="kd-tm" type="number" min="1" max="50" value={f.tol_macro} onChange={(e) => set("tol_macro", e.target.value)} /></div>
                </div>
              </>
            )}
            <div style={{ marginTop: 10 }}>
              <button className="btn btn--small" disabled={busy} onClick={policz}>{busy ? "Liczenie…" : "Policz menu"}</button>
            </div>
          </div>

          {wynik && st && (
            <div className="card">
              <div className="row row--between" style={{ alignItems: "baseline" }}>
                <h2 style={{ margin: 0 }}>Wynik</h2>
                <span className={`badge badge--${st[2]}`}>{st[0]}</span>
              </div>
              <p className="dim" style={{ fontSize: "0.85rem" }}>{st[1]}</p>
              {uwagi(wynik.issues).length > 0 && (
                <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
                  {uwagi(wynik.issues).map((u, i) => <li key={i}>{u}</li>)}
                </ul>
              )}
              {wynik.coverage && (
                <p className="dim" style={{ fontSize: "0.8rem" }}>
                  Pokrycie po filtrach: {Object.entries(wynik.coverage.slots).map(([s, v]) =>
                    `${profil?.sloty[s] ?? s} ${v.recipes} receptur / ${v.families} rodzin`).join(" · ")}.
                  {Object.keys(wynik.coverage.rejected).length > 0 && " Odrzucone: "
                    + Object.entries(wynik.coverage.rejected).map(([k, v]) => `${k} ${v}`).join(", ") + "."}
                </p>
              )}
              {wynik.meta.targets_source && (
                <p className="dim" style={{ fontSize: "0.8rem" }}>
                  Cele z planu klienta: {Object.entries(wynik.meta.targets_source.targets).map(([k, v]) => `${k} ${v}`).join(", ")}.
                </p>
              )}
              {wynik.plan && (
                <>
                  <Menu plan={wynik.plan} otwarte={otwarte} setOtwarte={setOtwarte} />
                  {wynik.shopping_list && wynik.shopping_list.length > 0 && (
                    <details style={{ marginTop: 10 }}>
                      <summary>Lista zakupów ({wynik.shopping_list.length} pozycji, gramy jadalne)</summary>
                      <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
                        {wynik.shopping_list.map((z) => <li key={z.food_id}>{z.name} — {Math.round(z.edible_grams)} g ({z.state})</li>)}
                      </ul>
                    </details>
                  )}
                  <h3>Zapisz do klienta</h3>
                  <div className="field-row">
                    <div><label htmlFor="kd-tytul">Tytuł planu (przy nowym planie)</label>
                      <input id="kd-tytul" value={tytul} placeholder="Menu z kreatora dań" onChange={(e) => setTytul(e.target.value)} /></div>
                  </div>
                  {wynik.plan.mode === "preview" && (
                    <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
                      <input type="checkbox" checked={potwierdzam} onChange={(e) => setPotwierdzam(e.target.checked)} />
                      Rozumiem, że to podgląd ze szkiców bez wartości odżywczych; zapisuję go klientowi jako materiał kulinarny.
                    </label>
                  )}
                  <div style={{ marginTop: 8 }}>
                    <button className="btn btn--small" disabled={busy || !!zapisano} onClick={zapisz}>Zapisz jako wersję planu diety</button>
                  </div>
                  {zapisMsg && <p className={zapisano ? "alert alert--info" : "alert alert--warn"}>{zapisMsg}</p>}
                  {zapisano && f.client_id && (
                    <Zamiana planId={zapisano.id} versionNo={zapisano.version_no} plan={wynik.plan}
                      onZamieniono={(v) => { setZapisano({ ...zapisano, version_no: v }); setZapisMsg(`Zamiana zatwierdzona — wersja v${v}.`); }} />
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}

function Menu({ plan, otwarte, setOtwarte }: { plan: KulinariaPlan; otwarte: string | null; setOtwarte: (k: string | null) => void }) {
  return (
    <>
      {plan.limitations.length > 0 && (
        <p className="dim" style={{ fontSize: "0.8rem" }}>{plan.limitations.join(" ")}</p>
      )}
      {plan.days.map((d, di) => (
        <div key={d.date} style={{ marginTop: 8 }}>
          <b>Dzień {di + 1} · {d.date}</b>
          {d.nutrition && (
            <span className="dim" style={{ fontSize: "0.8rem", marginLeft: 8 }}>
              {Math.round(d.nutrition.energy_kcal)} kcal · B {Math.round(d.nutrition.protein_g)} g · T {Math.round(d.nutrition.fat_g)} g · W {Math.round(d.nutrition.carbs_available_g)} g
            </span>
          )}
          {d.meals.map((m, mi) => {
            const k = `${di}:${mi}`;
            return (
              <div className="exercise" key={k}>
                <div style={{ width: "100%" }}>
                  <div className="row row--between">
                    <span><b>{m.slot_label}:</b> {m.recipe_name} <span className="dim">(porcja {m.portion_variant} ×{m.factor})</span></span>
                    {m.draft && <span className="badge badge--warn">szkic</span>}
                  </div>
                  <button className="btn btn--small btn--ghost" aria-expanded={otwarte === k}
                    onClick={() => setOtwarte(otwarte === k ? null : k)}>
                    {otwarte === k ? "Zwiń recepturę" : "Receptura"}
                  </button>
                  {otwarte === k && (
                    <div className="meta" style={{ whiteSpace: "pre-wrap" }}>
                      Składniki: {m.skladniki.join("; ")}
                      {"\n"}Kroki: {m.kroki.map((s, i) => `${i + 1}. ${s}`).join(" ")}
                      {m.nutrition && `\nWartości porcji: ${Object.entries(m.nutrition).map(([a, b]) => `${a} ${Math.round(b)}`).join(", ")}`}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </>
  );
}

function Zamiana({ planId, versionNo, plan, onZamieniono }: {
  planId: string; versionNo: number; plan: KulinariaPlan; onZamieniono: (v: number) => void;
}) {
  const [receptury, setReceptury] = useState<KulinariaReceptura[]>([]);
  const [mealIndex, setMealIndex] = useState("0");
  const [recipeId, setRecipeId] = useState("");
  const [podglad, setPodglad] = useState<KulinariaZamianaPodglad | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const posilki = plan.days.flatMap((d, di) => d.meals.map((m, mi) => ({ label: `Dzień ${di + 1} · ${m.slot_label}: ${m.recipe_name}`, slot: m.slot, i: di * d.meals.length + mi })));
  useEffect(() => {
    api.get<{ items: KulinariaReceptura[] }>("/api/coach/kulinaria/receptury").then((r) => setReceptury(r.items)).catch(() => setReceptury([]));
  }, []);
  const slot = posilki[Number(mealIndex)]?.slot;
  const kandydaci = receptury.filter((r) => (!slot || r.meal_slots.includes(slot)) && r.status !== "retired");

  async function sprawdz() {
    setBusy(true); setMsg(null); setPodglad(null);
    try {
      setPodglad(await api.post<KulinariaZamianaPodglad>("/api/coach/kulinaria/zamiana/podglad",
        { plan_id: planId, version_no: versionNo, meal_index: Number(mealIndex), recipe_id: recipeId, variant_id: "base" }));
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }
  async function zatwierdz() {
    setBusy(true); setMsg(null);
    try {
      const r = await api.post<{ version_no: number }>("/api/coach/kulinaria/zamiana/zatwierdz",
        { plan_id: planId, version_no: versionNo, meal_index: Number(mealIndex), recipe_id: recipeId, variant_id: "base" });
      setPodglad(null); onZamieniono(r.version_no);
    } catch (e) {
      const err = e as ApiError;
      setMsg(err.code === "STALE_PLAN" ? "Plan ma już nowszą wersję — odśwież i sprawdź zamianę ponownie." : err.message);
    } finally { setBusy(false); }
  }
  return (
    <details style={{ marginTop: 10 }}>
      <summary>Zamień danie (podgląd bez zmian, potem zatwierdzenie z kontrolą wersji)</summary>
      <div className="field-row">
        <div><label htmlFor="kd-zam-posilek">Posiłek</label>
          <select id="kd-zam-posilek" value={mealIndex} onChange={(e) => { setMealIndex(e.target.value); setPodglad(null); }}>
            {posilki.map((p) => <option key={p.i} value={p.i}>{p.label}</option>)}
          </select></div>
        <div><label htmlFor="kd-zam-receptura">Nowa receptura</label>
          <select id="kd-zam-receptura" value={recipeId} onChange={(e) => { setRecipeId(e.target.value); setPodglad(null); }}>
            <option value="">— wybierz —</option>
            {kandydaci.map((r) => <option key={r.id} value={r.id}>{r.name} ({r.status === "published" ? "opublikowana" : "szkic"})</option>)}
          </select></div>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <button className="btn btn--small btn--ghost" disabled={busy || !recipeId} onClick={sprawdz}>Sprawdź zamianę</button>
        {podglad?.ok && <button className="btn btn--small" disabled={busy} onClick={zatwierdz}>Zatwierdź zamianę</button>}
      </div>
      {podglad && (
        <p className={podglad.ok ? "alert alert--info" : "alert alert--warn"}>
          {podglad.ok
            ? `${podglad.przed.name} → ${podglad.po.recipe_name} (${podglad.dzien}). Dzień przeszedł ponowną kontrolę.`
            : `Zamiana odrzucona: ${podglad.problemy.join("; ")}`}
        </p>
      )}
      {msg && <p className="alert alert--warn">{msg}</p>}
    </details>
  );
}

function Receptury({ profil, onZmiana }: { profil: KulinariaProfil; onZmiana: () => void }) {
  const [items, setItems] = useState<KulinariaReceptura[]>([]);
  const [filtr, setFiltr] = useState("");
  const [status, setStatus] = useState("");
  const [otwarta, setOtwarta] = useState<KulinariaRecepturaPelna | null>(null);
  const [pub, setPub] = useState({ kitchen: false, dietitian: false, allergens_checked: false, expires_on: "", warianty: new Set<string>() });
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const laduj = () => api.get<{ items: KulinariaReceptura[] }>("/api/coach/kulinaria/receptury").then((r) => setItems(r.items)).catch(() => setItems([]));
  useEffect(() => { laduj(); }, []);

  const widoczne = items.filter((r) => (!status || r.status === status)
    && (!filtr || r.name.toLowerCase().includes(filtr.toLowerCase()) || r.family_id.includes(filtr.toLowerCase()))).slice(0, 60);

  async function otworz(id: string) {
    setMsg(null);
    try {
      const r = await api.get<KulinariaRecepturaPelna>(`/api/coach/kulinaria/receptury/${id}`);
      setOtwarta(r);
      setPub({ kitchen: false, dietitian: false, allergens_checked: false, expires_on: r.review.expires_on ?? "",
        warianty: new Set(r.portion_variants.filter((v) => v.validated).map((v) => v.id)) });
    } catch (e) { setMsg((e as Error).message); }
  }
  async function publikuj() {
    if (!otwarta) return;
    setBusy(true); setMsg(null);
    try {
      await api.post(`/api/coach/kulinaria/receptury/${otwarta.id}/publikuj`, {
        kitchen: pub.kitchen, dietitian: pub.dietitian, allergens_checked: pub.allergens_checked,
        expires_on: pub.expires_on, validated_variants: Array.from(pub.warianty),
      });
      setMsg("Opublikowano — receptura jest dostępna w trybie produkcyjnym w zatwierdzonych wariantach.");
      await laduj(); await otworz(otwarta.id); onZmiana();
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }
  async function wycofaj() {
    if (!otwarta) return;
    setBusy(true); setMsg(null);
    try {
      await api.post(`/api/coach/kulinaria/receptury/${otwarta.id}/wycofaj`);
      setMsg("Wycofano — tryb produkcyjny nie użyje tej receptury.");
      await laduj(); await otworz(otwarta.id); onZmiana();
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="card">
      <h2>Biblioteka receptur</h2>
      <p className="dim" style={{ marginTop: -6, fontSize: "0.85rem" }}>
        {profil.receptury.razem} szkiców wariantów w {profil.rodziny.length} rodzinach — bez testu kuchennego
        i bez recenzji dietetycznej. Publikujesz tylko to, co naprawdę sprawdziłeś; kreator nie wpisuje
        za Ciebie ani dat, ani nazwisk.
      </p>
      <div className="field-row">
        <div><label htmlFor="kd-rec-szukaj">Szukaj</label>
          <input id="kd-rec-szukaj" value={filtr} onChange={(e) => setFiltr(e.target.value)} placeholder="nazwa albo rodzina" /></div>
        <div><label htmlFor="kd-rec-status">Status</label>
          <select id="kd-rec-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">wszystkie</option><option value="draft">szkice</option>
            <option value="published">opublikowane</option><option value="retired">wycofane</option>
          </select></div>
      </div>
      {widoczne.map((r) => (
        <div className="exercise" key={r.id}>
          <div style={{ width: "100%" }}>
            <div className="row row--between">
              <span><b>{r.name}</b> <span className="dim">{r.meal_slots.map((s) => profil.sloty[s] ?? s).join(", ")} · {r.total_minutes} min</span></span>
              <span className={"badge" + (r.status === "published" ? " badge--ok" : r.status === "retired" ? " badge--danger" : " badge--warn")}>
                {r.status === "published" ? "opublikowana" : r.status === "retired" ? "wycofana" : "szkic"}
              </span>
            </div>
            <button className="btn btn--small btn--ghost" onClick={() => otworz(r.id)}>Otwórz</button>
          </div>
        </div>
      ))}
      {widoczne.length === 0 && <p className="dim">Brak receptur dla tego filtra.</p>}
      {otwarta && (
        <div className="card" style={{ marginTop: 10 }}>
          <h3 style={{ marginTop: 0 }}>{otwarta.name} <span className="dim">(rewizja {otwarta.revision})</span></h3>
          <p className="meta" style={{ whiteSpace: "pre-wrap" }}>
            Składniki: {otwarta.skladniki_opis.skladniki.join("; ")}
            {"\n"}Kroki: {otwarta.skladniki_opis.kroki.map((s, i) => `${i + 1}. ${s}`).join(" ")}
            {"\n"}Sprzęt: {otwarta.equipment.join(", ") || "—"} · czas {otwarta.total_minutes} min (aktywnie {otwarta.active_minutes})
          </p>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            {otwarta.nutrition_base
              ? `Wartości porcji bazowej z wbudowanej bazy produktów (${otwarta.source}): ${Object.entries(otwarta.nutrition_base).map(([k, v]) => `${k} ${Math.round(v)}`).join(", ")} — obliczone, nie zweryfikowane kuchennie.`
              : `Wartości nieobliczalne: ${otwarta.nutrition_problem ?? "brak danych produktu"}.`}
          </p>
          {otwarta.status === "published" ? (
            <>
              <p className="dim" style={{ fontSize: "0.85rem" }}>
                Opublikowana przez {otwarta.review.reviewer_id} · ważna do {otwarta.review.expires_on} ·
                warianty: {otwarta.portion_variants.filter((v) => v.validated).map((v) => v.id).join(", ") || "brak"}.
              </p>
              <button className="btn btn--small btn--ghost" disabled={busy} onClick={wycofaj}>Wycofaj z produkcji</button>
            </>
          ) : (
            <>
              <h4 style={{ marginBottom: 4 }}>Publikacja — poświadczenia trenera</h4>
              {([["kitchen", "przetestowałem tę recepturę w kuchni (wykonalność, gramatury po ugotowaniu)"],
                ["dietitian", "przegląd dietetyczny wykonany (ja albo wskazany specjalista)"],
                ["allergens_checked", "sprawdziłem alergeny składników złożonych z etykiet"]] as const).map(([k, t]) => (
                <label key={k} style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
                  <input type="checkbox" checked={pub[k]} onChange={(e) => setPub({ ...pub, [k]: e.target.checked })} />{t}
                </label>
              ))}
              <div className="field-row">
                <div><label htmlFor="kd-pub-do">Ważność przeglądu do</label>
                  <input id="kd-pub-do" type="date" value={pub.expires_on} onChange={(e) => setPub({ ...pub, expires_on: e.target.value })} /></div>
                <div><label>Zatwierdzone warianty porcji</label>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {otwarta.portion_variants.map((v) => (
                      <label key={v.id} className="badge" style={{ cursor: "pointer", opacity: pub.warianty.has(v.id) ? 1 : 0.6 }}>
                        <input type="checkbox" checked={pub.warianty.has(v.id)} style={{ marginRight: 4 }}
                          aria-label={`Wariant ${v.id}`}
                          onChange={() => { const n = new Set(pub.warianty); if (n.has(v.id)) n.delete(v.id); else n.add(v.id); setPub({ ...pub, warianty: n }); }} />
                        {v.id} ×{v.factor}
                      </label>
                    ))}
                  </div></div>
              </div>
              <button className="btn btn--small" disabled={busy || !pub.kitchen || !pub.dietitian || !pub.expires_on || pub.warianty.size === 0}
                onClick={publikuj}>Opublikuj</button>
            </>
          )}
          {msg && <p className="alert alert--info">{msg}</p>}
        </div>
      )}
    </div>
  );
}

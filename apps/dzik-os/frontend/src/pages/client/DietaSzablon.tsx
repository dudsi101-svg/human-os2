import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox } from "../../components";
import { DietAssignedOut, DietIngredientOut, DietMealOut, DietSwapCandidate } from "../../types";
import { gramatura, KartaDnia, makro, StatusDiety } from "../dieta/wspolne";

/**
 * Widok klienta diety z szablonu (0.60.0): dzień z posiłkami, gramatury
 * (dyskretne jako „2 szt. (~110 g)”), makro posiłku, przepis rozwijany;
 * P1: wymiana składnika oznaczonego `swappable` — arkusz z 1–3 zamiennikami
 * (gramatury policzone przez serwer), brak kandydatów → „napisz do trenera”.
 */
export default function DietaSzablon({ onStan }: { onStan?: (jest: boolean) => void } = {}) {
  const [a, setA] = useState<DietAssignedOut | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [dzien, setDzien] = useState(1);
  const [arkusz, setArkusz] = useState<{ m: DietMealOut; i: DietIngredientOut; cands: DietSwapCandidate[] | null; blocked: string | null } | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const zaladuj = useCallback(() => {
    setError(null);
    api.get<{ assigned: DietAssignedOut | null }>("/api/diet/assigned/current")
      .then((d) => { setA(d.assigned); onStan?.(d.assigned !== null); })
      .catch((e) => { if ((e as ApiError).status === 404) { setA(null); onStan?.(false); } else setError((e as Error).message); });
  }, [onStan]);
  useEffect(zaladuj, [zaladuj]);

  // Błąd inny niż „moduł wyłączony” (404) musi być widoczny — inaczej dieta
  // „znika” bez słowa i klient widzi tylko komunikat o braku planu.
  if (a === undefined && error) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (a === undefined || a === null) return null;
  const d = a.plan.days.find((x) => x.day === dzien) ?? a.plan.days[0];

  async function otworz(m: DietMealOut, i: DietIngredientOut) {
    setArkusz({ m, i, cands: null, blocked: null });
    try {
      const r = await api.get<{ candidates: DietSwapCandidate[]; blocked: string | null }>(
        `/api/diet/assigned/${a!.id}/swaps?day=${d.day}&meal=${encodeURIComponent(m.meal_id)}&ingredient=${encodeURIComponent(i.ingredient_id)}`);
      setArkusz({ m, i, cands: r.candidates, blocked: r.blocked });
    } catch (e) { setError((e as Error).message); setArkusz(null); }
  }

  async function wymien(c: DietSwapCandidate) {
    if (!arkusz || busy) return;
    setBusy(true); setError(null);
    try {
      await api.post(`/api/diet/assigned/${a!.id}/swaps`, {
        day: d.day, meal_id: arkusz.m.meal_id, ingredient_id: arkusz.i.ingredient_id, to_product_id: c.product_id,
      });
      setInfo(`Wymieniono: ${arkusz.i.product} → ${c.product} (${Math.round(c.grams)} g). Posiłek nadal mieści się w celu.`);
      setArkusz(null);
      zaladuj();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="card">
        <div className="row row--between">
          <h2 style={{ margin: 0 }}>Twoja dieta: {a.profile}</h2>
          <span className="badge badge--ok">v{a.version}</span>
        </div>
        <small className="dim">Cel dnia: {makro(a.target)} · od {plDate(a.created_at)}{a.swaps_enabled ? " · możesz wymieniać produkty oznaczone ↔" : " · wymiany wyłączone przez trenera"}</small>
        <div className="row" style={{ gap: 6, marginTop: 8 }} role="tablist" aria-label="Dzień tygodnia">
          {a.plan.days.map((x) => (
            <button key={x.day} type="button" role="tab" aria-selected={x.day === d.day}
              className={x.day === d.day ? "btn btn--small" : "btn btn--ghost btn--small"} onClick={() => setDzien(x.day)}>Dzień {x.day}</button>
          ))}
        </div>
      </div>
      {info && <p className="alert alert--info" role="status">{info} <button type="button" className="btn btn--ghost btn--small" aria-label="Zamknij" onClick={() => setInfo(null)}>×</button></p>}
      <ErrorBox error={error} />
      <KartaDnia d={d}>
        {d.meals.map((m) => (
          <div key={m.meal_id} style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
            <div className="row row--between">
              <b>{m.slot.charAt(0).toUpperCase() + m.slot.slice(1)}: {m.name}</b>
              <StatusDiety s={m.status} />
            </div>
            <small className="dim">{makro(m.macros)}</small>
            <ul style={{ paddingLeft: 18, margin: "4px 0" }}>
              {m.ingredients.map((i) => (
                <li key={i.ingredient_id}>
                  {i.product} — <b>{gramatura(i)}</b>
                  {i.override?.kind === "swap" && <small className="dim"> (wymienione)</small>}
                  {i.swappable && a.swaps_enabled && !m.swaps_locked && i.class !== "STAŁY" && (
                    <button type="button" className="btn btn--ghost btn--small" style={{ marginLeft: 6 }} aria-label={`Wymień ${i.product}`}
                      onClick={() => void otworz(m, i)}>↔ wymień</button>
                  )}
                </li>
              ))}
            </ul>
            {m.steps && <details><summary>Przepis</summary><p style={{ whiteSpace: "pre-wrap" }}>{m.steps}</p></details>}
          </div>
        ))}
      </KartaDnia>
      {arkusz && (
        <div className="card" role="dialog" aria-label={`Zamienniki: ${arkusz.i.product}`}>
          <div className="row row--between"><h3 style={{ margin: 0 }}>Wymień: {arkusz.i.product} ({gramatura(arkusz.i)})</h3>
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setArkusz(null)}>Zamknij</button></div>
          {arkusz.cands === null && <p className="dim">Szukam zamienników…</p>}
          {arkusz.blocked && <p className="alert alert--warn">{arkusz.blocked}</p>}
          {arkusz.cands && !arkusz.blocked && arkusz.cands.length === 0 && (
            <p className="alert alert--warn">Brak bezpiecznego zamiennika, napisz do trenera. <Link to="/wiadomosci" className="btn btn--small" style={{ marginLeft: 6 }}>Napisz do trenera</Link></p>
          )}
          {arkusz.cands && arkusz.cands.length > 0 && (
            <ul style={{ paddingLeft: 18 }}>
              {arkusz.cands.map((c) => (
                <li key={c.product_id} style={{ marginBottom: 6 }}>
                  <b>{c.product}</b> — {Math.round(c.grams)} g <small className="dim">(posiłek po wymianie: {makro(c.macros)})</small>{" "}
                  <button type="button" className="btn btn--small" disabled={busy} onClick={() => void wymien(c)}>{busy ? "Zapisuję…" : "Wybierz"}</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}

import { alergenLabel, DietDayOut, DietIngredientOut, DietMacros, DietMealOut, DietNotatkiOdslony, DietStatus } from "../../types";

/** Wspólne elementy modułu szablonów diet (0.60.0): etykiety statusów,
 * formatowanie gramatur (dyskretne jako „2 szt. (~110 g)”), makro. */

export const STATUS_LABEL: Record<DietStatus, string> = {
  OK: "OK", "OSTRZEŻENIE": "ostrzeżenie", POZA_ZAKRESEM: "poza zakresem", "POZA_TOLERANCJĄ": "poza tolerancją",
};

export function statusKlasa(s: DietStatus): string {
  if (s === "OK") return "badge badge--ok";
  if (s === "OSTRZEŻENIE") return "badge badge--warn";
  return "badge badge--danger";
}

export function StatusDiety({ s }: { s: DietStatus }) {
  return <span className={statusKlasa(s)}>{STATUS_LABEL[s]}</span>;
}

export function gramatura(i: DietIngredientOut): string {
  if (i.units != null && i.unit_g) {
    const u = Number.isInteger(i.units) ? String(i.units) : i.units.toFixed(1).replace(".", ",");
    return `${u} szt. (~${Math.round(i.grams)} g)`;
  }
  return `${Math.round(i.grams)} g`;
}

export function makro(m: DietMacros): string {
  return `${Math.round(m.kcal)} kcal · B ${Math.round(m.P)} · T ${Math.round(m.F)} · W ${Math.round(m.C)}`;
}

export function odchylenie(d: DietMacros): string {
  const f = (x: number) => (x >= 0 ? "+" : "") + Math.round(x);
  return `Δ kcal ${f(d.kcal)} · B ${f(d.P)} · T ${f(d.F)} · W ${f(d.C)}`;
}

export function KartaDnia({ d, children }: { d: DietDayOut; children?: React.ReactNode }) {
  return (
    <div className="card" style={{ borderColor: d.status === "OK" ? undefined : "var(--warn)" }}>
      <div className="row row--between">
        <h3 style={{ margin: 0 }}>Dzień {d.day}</h3>
        <StatusDiety s={d.status} />
      </div>
      <small className="dim">{makro(d.macros)} · cel {makro(d.target)}</small>
      {children}
    </div>
  );
}

export function TagiPosilku({ m }: { m: DietMealOut }) {
  return (
    <span className="row" style={{ gap: 4, display: "inline-flex" }}>
      {m.flexible && <span className="badge" style={{ fontSize: "0.7rem" }}>elastyczny</span>}
      {m.tags.map((t) => <span key={t} className="badge" style={{ fontSize: "0.7rem" }}>{t.replace(/_/g, " ")}</span>)}
    </span>
  );
}

/** Notatki odsłony z biblioteki (0.64.0): suplementacja, sód, pochodzenie.
 * Treść informacyjna od autora szablonu — nie jest zaleceniem ani dawką ustaloną
 * przez aplikację (R-10). Klientowi API nie zwraca uwag o suplementacji ani
 * pochodzenia (tylko trener je widzi). */
export function NotatkiOdslony({ n }: { n: Partial<DietNotatkiOdslony> | null | undefined }) {
  if (!n) return null;
  const supl = n.supplements_note ?? [];
  if (supl.length === 0 && !n.sodium_note && !n.derived_from) return null;
  return (
    <section className="alert alert--info" aria-label="Notatki autora szablonu" style={{ marginTop: 8, fontSize: "0.85rem" }}>
      <b>Notatki autora szablonu</b> <small className="dim">— informacja, nie zalecenie; o suplementach decydujesz z trenerem lub lekarzem.</small>
      {n.derived_from && <div>Odsłona na bazie: {n.derived_from}.</div>}
      {supl.length > 0 && (
        <div>Uwagi o suplementacji:
          <ul style={{ paddingLeft: 18, margin: "2px 0" }}>{supl.map((x, i) => <li key={i}>{x}</li>)}</ul>
        </div>
      )}
      {n.sodium_note && <div>Sód: {n.sodium_note}</div>}
    </section>
  );
}

/** Alergeny posiłku (policzone z bieżących składników) — odznaki, nie tylko kolor. */
export function Alergeny({ a }: { a?: string[] | null }) {
  if (!a || a.length === 0) return null;
  return (
    <div style={{ marginTop: 2 }}>
      <small>Alergeny: {a.map((x) => <span key={x} className="badge" style={{ marginRight: 4 }}>{alergenLabel(x)}</span>)}</small>
    </div>
  );
}

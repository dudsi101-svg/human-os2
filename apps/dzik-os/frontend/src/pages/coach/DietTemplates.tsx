import { useEffect, useState } from "react";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner } from "../../components";

/** Zakładka „Dieta" ekranu Szablony (0.54.0).
 *
 * Katalog gotowych (autorskie szablony trenera wbudowane w aplikację)
 * + moje szablony. Import z katalogu tworzy MÓJ szablon — dalej
 * edytowalny i kopiowalny do podopiecznego z karty klienta (Dieta →
 * „Z szablonu"). Makro w katalogu jest celowo puste: ustawia je trener
 * przy kopiowaniu, pod konkretnego podopiecznego. */

interface DietTemplateContent {
  kcal: number | null;
  protein_g: number | null;
  fat_g: number | null;
  carbs_g: number | null;
  sections: { title: string; body: string }[];
  meals: { name: string; description: string; swaps?: string }[];
}

export interface DietTemplateRow {
  id: string;
  title: string;
  content: DietTemplateContent;
  created_at: string;
  updated_at: string;
}

interface CatalogRow {
  id: string;
  title: string;
  description: string;
  meals: number;
  sections: number;
}

export default function DietTemplatesTab() {
  const [mine, setMine] = useState<DietTemplateRow[] | null>(null);
  const [catalog, setCatalog] = useState<CatalogRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([
      api.get<{ templates: DietTemplateRow[] }>("/api/nutrition-templates"),
      api.get<{ templates: CatalogRow[] }>("/api/nutrition-templates/catalog"),
    ])
      .then(([m, c]) => { setMine(m.templates); setCatalog(c.templates); })
      .catch((e) => setError((e as Error).message));
  };
  useEffect(load, []);

  async function importFromCatalog(id: string) {
    setBusy(id);
    try {
      await api.post(`/api/nutrition-templates/catalog/${id}/import`);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Usunąć szablon? Diety podopiecznych zostają bez zmian.")) return;
    setBusy(id);
    try {
      await api.del(`/api/nutrition-templates/${id}`);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (error && !mine) return <ErrorBox error={error} onRetry={load} />;
  if (!mine) return <Spinner />;

  const mineIds = new Set(mine.map((t) => t.title));

  return (
    <>
      <div className="card" style={{ marginBottom: 12 }}>
        <b>Gotowe szablony diety</b>
        <p className="dim" style={{ margin: "4px 0 8px" }}>
          Autorskie układy wbudowane w aplikację. „Dodaj do moich" tworzy
          Twoją kopię — możesz ją edytować, a z karty podopiecznego
          (Dieta → „Z szablonu") skopiować jako jego dietę, ustawiając
          wtedy makro.
        </p>
        {catalog.map((c) => (
          <div className="row row--between" key={c.id} style={{ gap: 8, alignItems: "flex-start" }}>
            <div>
              <b>{c.title}</b>
              <p className="dim" style={{ margin: "2px 0", fontSize: "0.85rem" }}>{c.description}</p>
              <small className="dim">{c.meals} posiłki · {c.sections} sekcje wskazówek</small>
            </div>
            <button className="btn btn--small" disabled={busy === c.id}
              onClick={() => importFromCatalog(c.id)}>
              {busy === c.id ? "Chwileczkę…" : mineIds.has(c.title) ? "Dodaj ponownie" : "Dodaj do moich"}
            </button>
          </div>
        ))}
      </div>

      <ErrorBox error={error} />
      {mine.length === 0 && (
        <p className="dim">Nie masz jeszcze szablonów diety — dodaj gotowy z katalogu powyżej.</p>
      )}
      {mine.map((t) => (
        <div className="card" key={t.id}>
          <div className="row row--between">
            <h2>{t.title}</h2>
            <small>{plDate(t.updated_at)}</small>
          </div>
          <small className="dim">
            {t.content.kcal
              ? `${t.content.kcal} kcal · B ${t.content.protein_g ?? "—"} g · T ${t.content.fat_g ?? "—"} g · W ${t.content.carbs_g ?? "—"} g`
              : "Makro nieustawione — podasz je przy kopiowaniu do podopiecznego."}
          </small>
          <div className="row" style={{ gap: 6, margin: "8px 0" }}>
            <button className="btn btn--ghost btn--small"
              onClick={() => setOpen(open === t.id ? null : t.id)}>
              {open === t.id ? "Zwiń podgląd" : "Podgląd"}
            </button>
            <button className="btn btn--ghost btn--small" disabled={busy === t.id}
              onClick={() => remove(t.id)}>
              Usuń
            </button>
          </div>
          {open === t.id && (
            <div>
              {t.content.meals.map((m, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <b>{m.name}</b>
                  <p className="dim" style={{ whiteSpace: "pre-line", margin: "2px 0", fontSize: "0.85rem" }}>
                    {m.description}
                  </p>
                  {m.swaps && <small className="dim">{m.swaps}</small>}
                </div>
              ))}
              {t.content.sections.map((s, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <b>{s.title}</b>
                  <p className="dim" style={{ whiteSpace: "pre-line", margin: "2px 0", fontSize: "0.85rem" }}>
                    {s.body}
                  </p>
                </div>
              ))}
            </div>
          )}
          <small className="dim">
            Kopiowanie do podopiecznego: karta klienta → Dieta → „Z szablonu".
          </small>
        </div>
      ))}
    </>
  );
}

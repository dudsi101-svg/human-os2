import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import {
  DietSuggestionResult,
  ExerciseLibraryItem,
  FoodProductRow,
  KNOWLEDGE_CATEGORY_SUGGESTIONS,
  KnowledgeItemRow,
  MUSCLE_GROUP_LABELS,
} from "../../types";

type Tab = "artykuly" | "cwiczenia" | "produkty" | "dieta";
const TABS: [Tab, string][] = [
  ["artykuly", "Artykuły"], ["cwiczenia", "Ćwiczenia"],
  ["produkty", "Produkty"], ["dieta", "Kompozytor diety"],
];

export default function Knowledge() {
  const [tab, setTab] = useState<Tab>("artykuly");
  return (
    <div className="page page--wide">
      <TopBar title="Baza wiedzy" right={<LogoutButton />} />
      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "artykuly" && <ArticlesTab />}
      {tab === "cwiczenia" && <ExercisesTab />}
      {tab === "produkty" && <ProductsTab />}
      {tab === "dieta" && <DietComposerTab />}
    </div>
  );
}

const EMPTY_ARTICLE_FORM = {
  title: "", category: "Trening", body: "", external_url: "", pinned: false,
};

function ArticlesTab() {
  const [items, setItems] = useState<KnowledgeItemRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<typeof EMPTY_ARTICLE_FORM>(EMPTY_ARTICLE_FORM);
  const [file, setFile] = useState<File | null>(null);
  const [existingFileId, setExistingFileId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const load = useCallback(() => {
    api.get<{ items: KnowledgeItemRow[] }>("/api/coach/knowledge")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  function startNew() {
    setForm(EMPTY_ARTICLE_FORM);
    setFile(null);
    setExistingFileId(null);
    setEditing("new");
  }

  function startEdit(item: KnowledgeItemRow) {
    setForm({
      title: item.title, category: item.category, body: item.body ?? "",
      external_url: item.external_url ?? "", pinned: item.pinned,
    });
    setFile(null);
    setExistingFileId(item.file_id);
    setEditing(item.id);
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let file_id = existingFileId;
      if (file) {
        const up = await api.upload<{ id: string }>("/api/files", file);
        file_id = up.id;
      }
      const payload = { ...form, body: form.body || null,
        external_url: form.external_url || null, file_id };
      if (editing === "new") {
        await api.post("/api/coach/knowledge", payload);
      } else {
        await api.put(`/api/coach/knowledge/${editing}`, payload);
      }
      setEditing(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    try {
      await api.post(`/api/coach/knowledge/${id}/status?status=${status}`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error && !items) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;

  const visible = items.filter((i) => (showArchived ? i.status === "ARCHIVED" : i.status === "ACTIVE"));

  return (
    <>
      <ErrorBox error={error} />
      <p className="dim" style={{ marginTop: -8 }}>
        Materiały widoczne dla wszystkich aktywnie prowadzonych klientów —
        artykuły, linki, pliki. Treść i jej poprawność są po Twojej stronie.
      </p>

      {editing && (
        <form className="card card--accent" onSubmit={save}>
          <h3>{editing === "new" ? "Nowy materiał" : "Edytuj materiał"}</h3>
          <label>Tytuł</label>
          <input required value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div className="field-row">
            <div>
              <label>Kategoria</label>
              <input list="knowledge-categories" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <datalist id="knowledge-categories">
                {KNOWLEDGE_CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
              </datalist>
            </div>
            <div className="row" style={{ alignItems: "center", marginTop: 24 }}>
              <input type="checkbox" id="pinned" checked={form.pinned}
                onChange={(e) => setForm({ ...form, pinned: e.target.checked })}
                style={{ width: "auto" }} />
              <label htmlFor="pinned" style={{ margin: 0 }}>Przypnij jako polecane</label>
            </div>
          </div>
          <label>Treść</label>
          <textarea value={form.body} style={{ minHeight: 140 }}
            onChange={(e) => setForm({ ...form, body: e.target.value })} />
          <label>Link zewnętrzny (opcjonalnie)</label>
          <input type="url" placeholder="https://…" value={form.external_url}
            onChange={(e) => setForm({ ...form, external_url: e.target.value })} />
          <label>Załącznik (PDF/obraz/wideo, opcjonalnie)</label>
          <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf,video/mp4"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          {existingFileId && !file && <small>Obecny załącznik zostanie zachowany.</small>}
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy}>{busy ? "Zapisywanie…" : "Zapisz"}</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(null)}>
              Anuluj
            </button>
          </div>
        </form>
      )}

      {!editing && (
        <div className="row" style={{ marginBottom: 10 }}>
          <button className="btn btn--small" onClick={startNew}>+ Nowy materiał</button>
          <button className="btn btn--ghost btn--small" onClick={() => setShowArchived(!showArchived)}>
            {showArchived ? "Pokaż aktywne" : "Pokaż zarchiwizowane"}
          </button>
        </div>
      )}

      <div className="list">
        {visible.length === 0 && <p className="dim">Brak materiałów.</p>}
        {visible.map((i) => (
          <div className="card" key={i.id}>
            <div className="row row--between">
              <div>
                <b>{i.title}</b> <span className="badge">{i.category}</span>
                {i.pinned && <span className="badge badge--accent" style={{ marginLeft: 4 }}>przypięte</span>}
              </div>
              <div className="row">
                <button className="btn btn--ghost btn--small" onClick={() => startEdit(i)}>Edytuj</button>
                {i.status === "ACTIVE" ? (
                  <button className="btn btn--danger btn--small" onClick={() => setStatus(i.id, "ARCHIVED")}>
                    Archiwizuj
                  </button>
                ) : (
                  <button className="btn btn--ghost btn--small" onClick={() => setStatus(i.id, "ACTIVE")}>
                    Przywróć
                  </button>
                )}
              </div>
            </div>
            {i.body && <p className="meta" style={{ marginTop: 6 }}>{i.body.slice(0, 160)}{i.body.length > 160 ? "…" : ""}</p>}
          </div>
        ))}
      </div>
    </>
  );
}

const EMPTY_EXERCISE_FORM = {
  name: "", muscle_group: "NOGI", how_to: "", benefit: "", equipment: "", video_url: "",
};

function ExercisesTab() {
  const [items, setItems] = useState<ExerciseLibraryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState(EMPTY_EXERCISE_FORM);
  const [busy, setBusy] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const load = useCallback(() => {
    api.get<{ items: ExerciseLibraryItem[] }>("/api/coach/exercises")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  function startNew() {
    setForm(EMPTY_EXERCISE_FORM);
    setEditing("new");
  }

  function startEdit(item: ExerciseLibraryItem) {
    setForm({
      name: item.name, muscle_group: item.muscle_group, how_to: item.how_to,
      benefit: item.benefit ?? "", equipment: item.equipment ?? "", video_url: item.video_url ?? "",
    });
    setEditing(item.id);
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        ...form, benefit: form.benefit || null, equipment: form.equipment || null,
        video_url: form.video_url || null,
      };
      if (editing === "new") {
        await api.post("/api/coach/exercises", payload);
      } else {
        await api.put(`/api/coach/exercises/${editing}`, payload);
      }
      setEditing(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    try {
      await api.post(`/api/coach/exercises/${id}/status?status=${status}`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error && !items) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;

  const visible = items.filter((i) => (showArchived ? i.status === "ARCHIVED" : i.status === "ACTIVE"));
  const byGroup = new Map<string, ExerciseLibraryItem[]>();
  for (const i of visible) {
    if (!byGroup.has(i.muscle_group)) byGroup.set(i.muscle_group, []);
    byGroup.get(i.muscle_group)!.push(i);
  }

  return (
    <>
      <ErrorBox error={error} />
      <p className="dim" style={{ marginTop: -8 }}>
        Know-how: technika wykonania i efekt każdego ćwiczenia, z podziałem
        na partie mięśniowe — widoczne dla wszystkich aktywnie prowadzonych klientów.
      </p>

      {editing && (
        <form className="card card--accent" onSubmit={save}>
          <h3>{editing === "new" ? "Nowe ćwiczenie" : "Edytuj ćwiczenie"}</h3>
          <label>Nazwa</label>
          <input required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div className="field-row">
            <div>
              <label>Partia mięśniowa</label>
              <select value={form.muscle_group}
                onChange={(e) => setForm({ ...form, muscle_group: e.target.value })}>
                {Object.entries(MUSCLE_GROUP_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label>Sprzęt (opcjonalnie)</label>
              <input value={form.equipment}
                onChange={(e) => setForm({ ...form, equipment: e.target.value })} />
            </div>
          </div>
          <label>Jak wykonać</label>
          <textarea required value={form.how_to} style={{ minHeight: 100 }}
            onChange={(e) => setForm({ ...form, how_to: e.target.value })} />
          <label>Co to daje (efekt)</label>
          <textarea value={form.benefit}
            onChange={(e) => setForm({ ...form, benefit: e.target.value })} />
          <label>Link do wideo (opcjonalnie)</label>
          <input type="url" placeholder="https://…" value={form.video_url}
            onChange={(e) => setForm({ ...form, video_url: e.target.value })} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy}>{busy ? "Zapisywanie…" : "Zapisz"}</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(null)}>
              Anuluj
            </button>
          </div>
        </form>
      )}

      {!editing && (
        <div className="row" style={{ marginBottom: 10 }}>
          <button className="btn btn--small" onClick={startNew}>+ Nowe ćwiczenie</button>
          <button className="btn btn--ghost btn--small" onClick={() => setShowArchived(!showArchived)}>
            {showArchived ? "Pokaż aktywne" : "Pokaż zarchiwizowane"}
          </button>
        </div>
      )}

      {visible.length === 0 && <p className="dim">Brak ćwiczeń.</p>}
      {Array.from(byGroup.entries()).map(([group, list]) => (
        <div key={group} style={{ marginBottom: 14 }}>
          <h3 style={{ margin: "0 0 6px" }}>{MUSCLE_GROUP_LABELS[group] ?? group}</h3>
          <div className="list">
            {list.map((i) => (
              <div className="card" key={i.id}>
                <div className="row row--between">
                  <b>{i.name}</b>
                  <div className="row">
                    <button className="btn btn--ghost btn--small" onClick={() => startEdit(i)}>Edytuj</button>
                    {i.status === "ACTIVE" ? (
                      <button className="btn btn--danger btn--small" onClick={() => setStatus(i.id, "ARCHIVED")}>
                        Archiwizuj
                      </button>
                    ) : (
                      <button className="btn btn--ghost btn--small" onClick={() => setStatus(i.id, "ACTIVE")}>
                        Przywróć
                      </button>
                    )}
                  </div>
                </div>
                <p className="meta" style={{ marginTop: 6 }}>{i.how_to}</p>
                {i.benefit && <p className="meta"><b>Efekt:</b> {i.benefit}</p>}
                {i.equipment && <span className="badge">{i.equipment}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

const EMPTY_PRODUCT_FORM = {
  name: "", category: "Inne", kcal_100g: "", protein_100g: "", fat_100g: "", carbs_100g: "",
  default_portion_g: "",
};

function ProductsTab() {
  const [items, setItems] = useState<FoodProductRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState(EMPTY_PRODUCT_FORM);
  const [busy, setBusy] = useState(false);
  const [portionByProduct, setPortionByProduct] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");

  const load = useCallback(() => {
    api.get<{ items: FoodProductRow[] }>("/api/coach/food-products")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  function startNew() {
    setForm(EMPTY_PRODUCT_FORM);
    setEditing("new");
  }

  function startEdit(item: FoodProductRow) {
    setForm({
      name: item.name, category: item.category,
      kcal_100g: String(item.kcal_100g), protein_100g: String(item.protein_100g),
      fat_100g: String(item.fat_100g), carbs_100g: String(item.carbs_100g),
      default_portion_g: item.default_portion_g != null ? String(item.default_portion_g) : "",
    });
    setEditing(item.id);
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        name: form.name, category: form.category,
        kcal_100g: Number(form.kcal_100g), protein_100g: Number(form.protein_100g),
        fat_100g: Number(form.fat_100g), carbs_100g: Number(form.carbs_100g),
        default_portion_g: form.default_portion_g ? Number(form.default_portion_g) : null,
      };
      if (editing === "new") {
        await api.post("/api/coach/food-products", payload);
      } else {
        await api.put(`/api/coach/food-products/${editing}`, payload);
      }
      setEditing(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    try {
      await api.post(`/api/coach/food-products/${id}/status?status=${status}`);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error && !items) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;

  const visible = items.filter((i) => i.status === "ACTIVE" &&
    (!query || i.name.toLowerCase().includes(query.toLowerCase())));

  return (
    <>
      <ErrorBox error={error} />
      <p className="dim" style={{ marginTop: -8 }}>
        Gotowa baza produktów z makroskładnikami na 100 g — wpisz gramaturę
        porcji, żeby zobaczyć automatycznie przeliczone kalorie i makro.
      </p>

      {editing && (
        <form className="card card--accent" onSubmit={save}>
          <h3>{editing === "new" ? "Nowy produkt" : "Edytuj produkt"}</h3>
          <div className="field-row">
            <div>
              <label>Nazwa</label>
              <input required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label>Kategoria</label>
              <input value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div><label>kcal / 100 g</label>
              <input required type="number" step="0.1" min="0" value={form.kcal_100g}
                onChange={(e) => setForm({ ...form, kcal_100g: e.target.value })} /></div>
            <div><label>Białko (g) / 100 g</label>
              <input required type="number" step="0.1" min="0" value={form.protein_100g}
                onChange={(e) => setForm({ ...form, protein_100g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label>Tłuszcz (g) / 100 g</label>
              <input required type="number" step="0.1" min="0" value={form.fat_100g}
                onChange={(e) => setForm({ ...form, fat_100g: e.target.value })} /></div>
            <div><label>Węgle (g) / 100 g</label>
              <input required type="number" step="0.1" min="0" value={form.carbs_100g}
                onChange={(e) => setForm({ ...form, carbs_100g: e.target.value })} /></div>
          </div>
          <label>Domyślna porcja (g, opcjonalnie)</label>
          <input type="number" step="1" min="0" value={form.default_portion_g}
            onChange={(e) => setForm({ ...form, default_portion_g: e.target.value })} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy}>{busy ? "Zapisywanie…" : "Zapisz"}</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(null)}>
              Anuluj
            </button>
          </div>
        </form>
      )}

      <div className="row" style={{ marginBottom: 10 }}>
        <input className="grow" placeholder="Szukaj produktu…" value={query}
          onChange={(e) => setQuery(e.target.value)} />
        {!editing && (
          <button className="btn btn--small" onClick={startNew}>+ Nowy produkt</button>
        )}
      </div>

      <div className="list">
        {visible.length === 0 && <p className="dim">Brak produktów.</p>}
        {visible.map((p) => {
          const portionStr = portionByProduct[p.id] ??
            (p.default_portion_g != null ? String(p.default_portion_g) : "100");
          const portion = Number(portionStr) || 0;
          const factor = portion / 100;
          return (
            <div className="card" key={p.id}>
              <div className="row row--between">
                <div>
                  <b>{p.name}</b> <span className="badge">{p.category}</span>
                </div>
                <div className="row">
                  <button className="btn btn--ghost btn--small" onClick={() => startEdit(p)}>Edytuj</button>
                  <button className="btn btn--danger btn--small" onClick={() => setStatus(p.id, "ARCHIVED")}>
                    Archiwizuj
                  </button>
                </div>
              </div>
              <div className="meta" style={{ marginTop: 4 }}>
                Na 100 g: {p.kcal_100g} kcal · B {p.protein_100g} g · T {p.fat_100g} g · W {p.carbs_100g} g
              </div>
              <div className="row" style={{ marginTop: 6, alignItems: "center", gap: 6 }}>
                <label style={{ margin: 0 }}>Porcja (g)</label>
                <input type="number" min="0" style={{ width: 90 }} value={portionStr}
                  onChange={(e) => setPortionByProduct({ ...portionByProduct, [p.id]: e.target.value })} />
                <span className="badge badge--accent">
                  {Math.round(p.kcal_100g * factor)} kcal · B {Math.round(p.protein_100g * factor * 10) / 10} g ·
                  {" "}T {Math.round(p.fat_100g * factor * 10) / 10} g · W {Math.round(p.carbs_100g * factor * 10) / 10} g
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function DietComposerTab() {
  const [items, setItems] = useState<FoodProductRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [target, setTarget] = useState({ kcal: "3000", protein_g: "180", fat_g: "80", carbs_g: "350" });
  const [result, setResult] = useState<DietSuggestionResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<{ items: FoodProductRow[] }>("/api/coach/food-products")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  }, []);

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  }

  async function compose() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.post<DietSuggestionResult>("/api/coach/diet-suggestion", {
        target_kcal: Number(target.kcal) || 0,
        target_protein_g: Number(target.protein_g) || 0,
        target_fat_g: Number(target.fat_g) || 0,
        target_carbs_g: Number(target.carbs_g) || 0,
        product_ids: Array.from(selected),
      });
      setResult(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function asMealsText(): string {
    if (!result) return "";
    return result.items.map((i) => `${i.name}: ${i.grams} g (${i.kcal} kcal)`).join("\n");
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card card--accent">
        <h3>Cel diety</h3>
        <p className="dim" style={{ marginTop: -6, fontSize: "0.85rem" }}>
          Wybierz produkty poniżej i wpisz cel. Wynik to wyłącznie przejrzysta
          arytmetyka podziału celu na gramaturę — nic nie zapisuje się
          automatycznie w planie klienta. Ty decydujesz, co i jak wpisać do diety.
        </p>
        <div className="field-row">
          <div><label>Cel kcal</label>
            <input type="number" min="0" value={target.kcal}
              onChange={(e) => setTarget({ ...target, kcal: e.target.value })} /></div>
          <div><label>Białko (g)</label>
            <input type="number" min="0" value={target.protein_g}
              onChange={(e) => setTarget({ ...target, protein_g: e.target.value })} /></div>
        </div>
        <div className="field-row">
          <div><label>Tłuszcz (g)</label>
            <input type="number" min="0" value={target.fat_g}
              onChange={(e) => setTarget({ ...target, fat_g: e.target.value })} /></div>
          <div><label>Węglowodany (g)</label>
            <input type="number" min="0" value={target.carbs_g}
              onChange={(e) => setTarget({ ...target, carbs_g: e.target.value })} /></div>
        </div>
        <div style={{ marginTop: 8 }}>
          <button className="btn btn--small" disabled={busy || selected.size === 0} onClick={compose}>
            {busy ? "Liczenie…" : `Ułóż sugestię (${selected.size} wybranych produktów)`}
          </button>
        </div>
      </div>

      {result && (
        <div className="card">
          <h3>Sugestia</h3>
          {result.warnings.map((w, i) => (
            <p className="alert alert--warn" key={i}>{w}</p>
          ))}
          <div className="stat-grid">
            <div className="stat"><b>{result.totals.kcal}</b><span>kcal (cel {result.target.kcal})</span></div>
            <div className="stat"><b>{result.totals.protein_g} g</b><span>białko (cel {result.target.protein_g})</span></div>
            <div className="stat"><b>{result.totals.fat_g} g</b><span>tłuszcz (cel {result.target.fat_g})</span></div>
            <div className="stat"><b>{result.totals.carbs_g} g</b><span>węgle (cel {result.target.carbs_g})</span></div>
          </div>
          {result.items.map((i) => (
            <div className="exercise" key={i.product_id}>
              <div><b>{i.name}</b><div className="meta">{i.grams} g · {i.kcal} kcal</div></div>
              <span className="badge">
                {i.macro_role === "PROTEIN" ? "białko" : i.macro_role === "FAT" ? "tłuszcz" : "węgle"}
              </span>
            </div>
          ))}
          <p className="dim" style={{ fontSize: "0.85rem" }}>{result.note}</p>
          <label>Do skopiowania w zakładkę Dieta klienta</label>
          <textarea readOnly value={asMealsText()} style={{ minHeight: 100 }} />
        </div>
      )}

      <h3>Produkty (zaznacz do kompozycji)</h3>
      {!items && <Spinner />}
      {items && (
        <ProductsTabSelector items={items} selected={selected} onToggle={toggle} />
      )}
    </>
  );
}

function ProductsTabSelector({ items, selected, onToggle }: {
  items: FoodProductRow[]; selected: Set<string>; onToggle: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const visible = items.filter((i) => i.status === "ACTIVE" &&
    (!query || i.name.toLowerCase().includes(query.toLowerCase())));
  return (
    <>
      <input placeholder="Szukaj produktu…" value={query}
        onChange={(e) => setQuery(e.target.value)} style={{ marginBottom: 8 }} />
      <div className="list">
        {visible.map((p) => (
          <label className="card" key={p.id} style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
            <input type="checkbox" checked={selected.has(p.id)} onChange={() => onToggle(p.id)}
              style={{ width: "auto" }} />
            <div>
              <b>{p.name}</b> <span className="badge">{p.category}</span>
              <div className="meta">{p.kcal_100g} kcal · B {p.protein_100g} g · T {p.fat_100g} g · W {p.carbs_100g} g /100 g</div>
            </div>
          </label>
        ))}
      </div>
    </>
  );
}

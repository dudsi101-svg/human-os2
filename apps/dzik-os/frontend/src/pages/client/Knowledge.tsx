import { useEffect, useState } from "react";
import { api } from "../../api";
import { AuthAttachment, ErrorBox, Spinner, TopBar } from "../../components";
import {
  ExerciseLibraryItem,
  FoodProductRow,
  KnowledgeItemRow,
  MUSCLE_GROUP_LABELS,
} from "../../types";

type Tab = "artykuly" | "cwiczenia" | "produkty";
const TABS: [Tab, string][] = [
  ["artykuly", "Artykuły"], ["cwiczenia", "Ćwiczenia"], ["produkty", "Produkty"],
];

export default function Knowledge() {
  const [tab, setTab] = useState<Tab>("artykuly");
  return (
    <div className="page">
      <TopBar title="Baza wiedzy" />
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
    </div>
  );
}

function ArticlesTab() {
  const [items, setItems] = useState<KnowledgeItemRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<{ items: KnowledgeItemRow[] }>("/api/me/knowledge")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;

  const pinned = items.filter((i) => i.pinned);
  const rest = items.filter((i) => !i.pinned);
  const byCategory = new Map<string, KnowledgeItemRow[]>();
  for (const i of rest) {
    if (!byCategory.has(i.category)) byCategory.set(i.category, []);
    byCategory.get(i.category)!.push(i);
  }

  return (
    <>
      {items.length === 0 && (
        <p className="dim">
          Trener nie dodał jeszcze żadnych materiałów. Zajrzyj tu ponownie
          później.
        </p>
      )}

      {pinned.length > 0 && (
        <div className="list" style={{ marginBottom: 18 }}>
          <h2 style={{ margin: "0 0 4px" }}>📌 Polecane</h2>
          {pinned.map((i) => <KnowledgeCard key={i.id} item={i} />)}
        </div>
      )}

      {Array.from(byCategory.entries()).map(([category, list]) => (
        <div className="list" key={category} style={{ marginBottom: 18 }}>
          <h2 style={{ margin: "0 0 4px" }}>{category}</h2>
          {list.map((i) => <KnowledgeCard key={i.id} item={i} />)}
        </div>
      ))}
    </>
  );
}

function KnowledgeCard({ item }: { item: KnowledgeItemRow }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button type="button" className="knowledge-card__toggle" onClick={() => setOpen(!open)}>
        <b>{item.title}</b>
        <span className="dim">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          {item.body && <p style={{ whiteSpace: "pre-wrap" }}>{item.body}</p>}
          {item.external_url && (
            <p>
              <a href={item.external_url} target="_blank" rel="noreferrer">
                🔗 {item.external_url}
              </a>
            </p>
          )}
          {item.file_id && (
            <div style={{ marginTop: 8, maxWidth: 320 }}>
              <AuthAttachment fileId={item.file_id} filename={item.title} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ExercisesTab() {
  const [items, setItems] = useState<ExerciseLibraryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const load = () => {
    setError(null);
    api.get<{ items: ExerciseLibraryItem[] }>("/api/me/exercises")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  if (items.length === 0) return <p className="dim">Trener nie dodał jeszcze bazy ćwiczeń.</p>;

  const visible = items.filter((i) => !query || i.name.toLowerCase().includes(query.toLowerCase()));
  const byGroup = new Map<string, ExerciseLibraryItem[]>();
  for (const i of visible) {
    if (!byGroup.has(i.muscle_group)) byGroup.set(i.muscle_group, []);
    byGroup.get(i.muscle_group)!.push(i);
  }

  return (
    <>
      <input placeholder="Szukaj ćwiczenia…" value={query}
        onChange={(e) => setQuery(e.target.value)} style={{ marginBottom: 10 }} />
      {Array.from(byGroup.entries()).map(([group, list]) => (
        <div className="list" key={group} style={{ marginBottom: 18 }}>
          <h2 style={{ margin: "0 0 4px" }}>{MUSCLE_GROUP_LABELS[group] ?? group}</h2>
          {list.map((i) => <ExerciseCard key={i.id} item={i} />)}
        </div>
      ))}
    </>
  );
}

function ExerciseCard({ item }: { item: ExerciseLibraryItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button type="button" className="knowledge-card__toggle" onClick={() => setOpen(!open)}>
        <b>{item.name}</b>
        <span className="dim">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          <p><b>Jak wykonać:</b> {item.how_to}</p>
          {item.benefit && <p><b>Co to daje:</b> {item.benefit}</p>}
          {item.equipment && <span className="badge">{item.equipment}</span>}
          {item.video_url && (
            <p>
              <a href={item.video_url} target="_blank" rel="noreferrer">🔗 Wideo z techniką</a>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ProductsTab() {
  const [items, setItems] = useState<FoodProductRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [portionByProduct, setPortionByProduct] = useState<Record<string, string>>({});

  const load = () => {
    setError(null);
    api.get<{ items: FoodProductRow[] }>("/api/me/food-products")
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  if (items.length === 0) return <p className="dim">Trener nie dodał jeszcze bazy produktów.</p>;

  const visible = items.filter((i) => !query || i.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <>
      <input placeholder="Szukaj produktu…" value={query}
        onChange={(e) => setQuery(e.target.value)} style={{ marginBottom: 10 }} />
      <div className="list">
        {visible.map((p) => {
          const portionStr = portionByProduct[p.id] ??
            (p.default_portion_g != null ? String(p.default_portion_g) : "100");
          const portion = Number(portionStr) || 0;
          const factor = portion / 100;
          return (
            <div className="card" key={p.id}>
              <div className="row row--between">
                <b>{p.name}</b>
                <span className="badge">{p.category}</span>
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

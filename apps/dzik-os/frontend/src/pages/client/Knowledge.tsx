import { useEffect, useState } from "react";
import { api } from "../../api";
import { AuthAttachment, ErrorBox, Icon, Spinner, TabPanel, Tabs, TopBar } from "../../components";
import {
  FoodDisclaimer,
  FoodFilters,
  FoodLoadMore,
  FoodProductCard,
  useFoodCatalog,
} from "../../FoodCatalog";
import {
  ExerciseLibraryItem,
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
      <Tabs tabs={TABS} value={tab} onChange={setTab} label="Sekcje bazy wiedzy" />
      <TabPanel id={tab}>
        {tab === "artykuly" && <ArticlesTab />}
        {tab === "cwiczenia" && <ExercisesTab />}
        {tab === "produkty" && <ProductsTab />}
      </TabPanel>
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
          <h2 style={{ margin: "0 0 4px", display: "flex", alignItems: "center", gap: 8 }}><Icon name="star" size={18} /> Polecane</h2>
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
      <button type="button" className="knowledge-card__toggle" aria-expanded={open}
        onClick={() => setOpen(!open)}>
        <b>{item.title}</b>
        <span className="dim"><Icon name={open ? "chevron-up" : "chevron-down"} size={18} /></span>
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          {item.body && <p style={{ whiteSpace: "pre-wrap" }}>{item.body}</p>}
          {item.external_url && (
            <p>
              <a href={item.external_url} target="_blank" rel="noreferrer"
                style={{ display: "inline-flex", alignItems: "center", gap: 6, wordBreak: "break-all" }}>
                <Icon name="link" size={16} /> {item.external_url}
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
      <input placeholder="Szukaj ćwiczenia…" aria-label="Szukaj ćwiczenia" value={query}
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
      <button type="button" className="knowledge-card__toggle" aria-expanded={open}
        onClick={() => setOpen(!open)}>
        <b>{item.name}</b>
        <span className="dim"><Icon name={open ? "chevron-up" : "chevron-down"} size={18} /></span>
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          <p><b>Jak wykonać:</b> {item.how_to}</p>
          {item.benefit && <p><b>Co to daje:</b> {item.benefit}</p>}
          {item.equipment && <span className="badge">{item.equipment}</span>}
          {item.video_url && (
            <p>
              <a href={item.video_url} target="_blank" rel="noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="film" size={16} /> Wideo z techniką
            </a>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ProductsTab() {
  // Katalog trenera potrafi mieć setki pozycji — filtrujemy i stronicujemy
  // po stronie API, zamiast wciągać wszystko do widoku.
  const catalog = useFoodCatalog("/api/me/food-products");

  if (catalog.error && catalog.items.length === 0) {
    return <ErrorBox error={catalog.error} onRetry={catalog.reload} />;
  }
  if (catalog.loading && catalog.items.length === 0 && !catalog.query && !catalog.category) {
    return <Spinner />;
  }
  if (catalog.total === 0 && !catalog.query && !catalog.category) {
    return <p className="dim">Trener nie dodał jeszcze bazy produktów.</p>;
  }

  return (
    <>
      <FoodDisclaimer text={catalog.disclaimer} />
      <FoodFilters catalog={catalog} idPrefix="client-food" />
      <div className="list">
        {catalog.items.map((p) => (
          <FoodProductCard key={p.id} product={p} idPrefix="portion" />
        ))}
      </div>
      <FoodLoadMore catalog={catalog} />
    </>
  );
}

import { useEffect, useState } from "react";
import { api } from "../../api";
import {
  AuthAttachment, ErrorBox, ExerciseDetail, ExerciseFilterBar, Icon, Spinner,
  TabPanel, Tabs, TopBar,
} from "../../components";
import { EMPTY_FILTERS, ExerciseFilters, exerciseQuery } from "../../exerciseFilters";
import {
  FoodDisclaimer,
  FoodFilters,
  FoodLoadMore,
  FoodProductCard,
  useFoodCatalog,
} from "../../FoodCatalog";
import {
  ExerciseLibraryItem,
  ExerciseListResponse,
  KnowledgeItemRow,
  MUSCLE_GROUP_LABELS,
  muscleLabels,
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

const PAGE_SIZE = 30;

function ExercisesTab() {
  const [items, setItems] = useState<ExerciseLibraryItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ExerciseFilters>(EMPTY_FILTERS);
  const [loadingMore, setLoadingMore] = useState(false);

  // Wyszukiwanie i filtry liczy API (baza ma >150 pozycji, a szukanie ma
  // być odporne na polskie znaki — tego przeglądarka sama nie zrobi
  // spójnie z serwerem).
  const load = (offset = 0) => {
    setError(null);
    if (offset > 0) setLoadingMore(true);
    api.get<ExerciseListResponse>(
      `/api/me/exercises?${exerciseQuery(filters, offset, PAGE_SIZE)}`,
    )
      .then((d) => {
        setItems((prev) => (offset > 0 && prev ? [...prev, ...d.items] : d.items));
        setTotal(d.total);
        setHasMore(d.has_more);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingMore(false));
  };
  // Krótkie opóźnienie: przy pisaniu nie wysyłamy zapytania z każdą literą.
  useEffect(() => {
    const timer = setTimeout(() => load(0), 200);
    return () => clearTimeout(timer);
  }, [ // eslint-disable-line react-hooks/exhaustive-deps
    filters.q, filters.muscle, filters.equipment, filters.level, filters.pattern,
  ]);

  if (error) return <ErrorBox error={error} onRetry={() => load(0)} />;
  if (!items) return <Spinner />;

  const byGroup = new Map<string, ExerciseLibraryItem[]>();
  for (const i of items) {
    if (!byGroup.has(i.muscle_group)) byGroup.set(i.muscle_group, []);
    byGroup.get(i.muscle_group)!.push(i);
  }

  return (
    <>
      <ExerciseFilterBar idPrefix="cl" value={filters} onChange={setFilters} />
      <p className="dim" aria-live="polite" style={{ marginTop: 4 }}>
        {total === 0
          ? "Brak ćwiczeń pasujących do wyszukiwania."
          : `Znaleziono ${total} ćwiczeń — pokazano ${items.length}.`}
      </p>
      {Array.from(byGroup.entries()).map(([group, list]) => (
        <div className="list" key={group} style={{ marginBottom: 18 }}>
          <h2 style={{ margin: "0 0 4px" }}>{MUSCLE_GROUP_LABELS[group] ?? group}</h2>
          {list.map((i) => <ExerciseCard key={i.id} item={i} />)}
        </div>
      ))}
      {hasMore && (
        <button className="btn btn--ghost" disabled={loadingMore}
          onClick={() => load(items.length)}>
          {loadingMore ? "Wczytywanie…" : "Pokaż więcej"}
        </button>
      )}
    </>
  );
}

function ExerciseCard({ item }: { item: ExerciseLibraryItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button type="button" className="knowledge-card__toggle" aria-expanded={open}
        onClick={() => setOpen(!open)}>
        <span>
          <b>{item.name}</b>
          {item.muscles_primary.length > 0 && (
            <span className="meta" style={{ display: "block" }}>
              {muscleLabels(item.muscles_primary)}
            </span>
          )}
        </span>
        <span className="dim"><Icon name={open ? "chevron-up" : "chevron-down"} size={18} /></span>
      </button>
      {open && (
        <div style={{ marginTop: 10 }}>
          <ExerciseDetail item={item} />
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

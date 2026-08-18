// Wspólne elementy bazy produktów spożywczych: pobieranie stronicowanej
// listy z API, pasek filtrów i karta produktu z kalkulatorem porcji.
//
// Katalog liczy 400+ pozycji, więc widok NIGDY nie ładuje go w całości —
// filtruje i stronicuje API (`q`, `category`, `sort`, `limit`, `offset`),
// a „Pokaż więcej” dokłada kolejną stronę.
//
// Uczciwość danych: informacja o przybliżonym charakterze wartości jest
// pokazywana przy katalogu i przy kalkulatorze porcji — nie ukrywamy jej
// w dokumentacji. Katalog jest neutralny: nie ocenia produktów.

import { ReactNode, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import {
  FOOD_APPROXIMATION_HINT,
  computePortion,
  defaultPortionGrams,
  formatPortion,
  unitHint,
  unitsToGrams,
} from "./foodUtils";
import { FOOD_SORT_LABELS, FoodProductPage, FoodProductRow, FoodSort } from "./types";

const PAGE_SIZE = 30;

export interface FoodCatalogState {
  items: FoodProductRow[];
  total: number;
  hasMore: boolean;
  categories: string[];
  disclaimer: string;
  loading: boolean;
  error: string | null;
  query: string;
  setQuery: (value: string) => void;
  category: string;
  setCategory: (value: string) => void;
  sort: FoodSort;
  setSort: (value: FoodSort) => void;
  loadMore: () => void;
  /** Ponowne pobranie pierwszej strony (po edycji, imporcie, archiwizacji). */
  reload: () => void;
}

/** Stan katalogu: filtry + stronicowanie po stronie API. */
export function useFoodCatalog(path: string, status?: string): FoodCatalogState {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<FoodSort>("name");
  const [items, setItems] = useState<FoodProductRow[]>([]);
  const [meta, setMeta] = useState<FoodProductPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  // Wpisywanie w wyszukiwarkę nie ma generować żądania na każdą literę.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const fetchPage = useCallback(
    (offset: number, append: boolean) => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort,
      });
      if (debounced) params.set("q", debounced);
      if (category) params.set("category", category);
      if (status) params.set("status", status);
      setLoading(true);
      api
        .get<FoodProductPage>(`${path}?${params.toString()}`)
        .then((data) => {
          setMeta(data);
          setItems((prev) => (append ? [...prev, ...data.items] : data.items));
          setError(null);
        })
        .catch((e) => setError((e as Error).message))
        .finally(() => setLoading(false));
    },
    [path, debounced, category, sort, status]
  );

  useEffect(() => {
    fetchPage(0, false);
  }, [fetchPage, version]);

  return {
    items,
    total: meta?.total ?? 0,
    hasMore: meta?.has_more ?? false,
    categories: meta?.categories ?? [],
    disclaimer: meta?.disclaimer ?? FOOD_APPROXIMATION_HINT,
    loading,
    error,
    query,
    setQuery,
    category,
    setCategory,
    sort,
    setSort,
    loadMore: () => fetchPage(items.length, true),
    reload: () => setVersion((v) => v + 1),
  };
}

/** Widoczna przy katalogu i kalkulatorze informacja o przybliżeniu danych. */
export function FoodDisclaimer({ text }: { text?: string }) {
  return (
    <p className="alert alert--info" style={{ fontSize: "0.85rem" }}>
      {text || FOOD_APPROXIMATION_HINT}
    </p>
  );
}

/** Wyszukiwarka + filtr kategorii + sortowanie + licznik wyników. */
export function FoodFilters({ catalog, idPrefix }: {
  catalog: FoodCatalogState;
  idPrefix: string;
}) {
  return (
    <>
      <div className="row" style={{ marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
        <input
          className="grow"
          id={`${idPrefix}-search`}
          placeholder="Szukaj produktu…"
          aria-label="Szukaj produktu"
          value={catalog.query}
          onChange={(e) => catalog.setQuery(e.target.value)}
        />
        <select
          id={`${idPrefix}-category`}
          aria-label="Filtr kategorii"
          value={catalog.category}
          onChange={(e) => catalog.setCategory(e.target.value)}
          style={{ width: "auto" }}
        >
          <option value="">Wszystkie kategorie</option>
          {catalog.categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          id={`${idPrefix}-sort`}
          aria-label="Sortowanie"
          value={catalog.sort}
          onChange={(e) => catalog.setSort(e.target.value as FoodSort)}
          style={{ width: "auto" }}
        >
          {(Object.keys(FOOD_SORT_LABELS) as FoodSort[]).map((key) => (
            <option key={key} value={key}>{FOOD_SORT_LABELS[key]}</option>
          ))}
        </select>
      </div>
      <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
        {catalog.total === 0
          ? "Brak produktów spełniających kryteria."
          : `Pokazano ${catalog.items.length} z ${catalog.total} produktów.`}
      </p>
    </>
  );
}

/** Przycisk „Pokaż więcej” — kolejna strona z API, nie cała baza naraz. */
export function FoodLoadMore({ catalog }: { catalog: FoodCatalogState }) {
  if (!catalog.hasMore) return null;
  return (
    <div className="row" style={{ justifyContent: "center", margin: "10px 0" }}>
      <button className="btn btn--ghost btn--small" disabled={catalog.loading}
        onClick={catalog.loadMore}>
        {catalog.loading ? "Wczytywanie…" : "Pokaż więcej produktów"}
      </button>
    </div>
  );
}

/** Karta produktu z kalkulatorem porcji (gramy albo sztuki). */
export function FoodProductCard({ product, idPrefix, actions }: {
  product: FoodProductRow;
  idPrefix: string;
  actions?: ReactNode;
}) {
  const hint = unitHint(product);
  const [mode, setMode] = useState<"g" | "unit">("g");
  const [amount, setAmount] = useState(String(defaultPortionGrams(product)));

  const parsed = Number(amount.replace(",", "."));
  const grams =
    mode === "unit" ? unitsToGrams(product, parsed) ?? 0 : Number.isFinite(parsed) ? parsed : 0;
  const values = computePortion(product, grams);

  function switchMode(next: "g" | "unit") {
    if (next === mode) return;
    setMode(next);
    setAmount(next === "unit" ? "1" : String(defaultPortionGrams(product)));
  }

  return (
    <div className="card">
      <div className="row row--between">
        <div>
          <b>{product.name}</b> <span className="badge">{product.category}</span>
        </div>
        {actions}
      </div>
      <div className="meta" style={{ marginTop: 4 }}>
        Na 100 g: {product.kcal_100g} kcal · B {product.protein_100g} g ·
        {" "}T {product.fat_100g} g · W {product.carbs_100g} g
        {product.fiber_100g != null && <> · Bł {product.fiber_100g} g</>}
      </div>
      {product.note && <div className="meta">Uwaga: {product.note}</div>}
      {product.source && <div className="meta">Źródło wartości: {product.source}</div>}
      <div className="row" style={{ marginTop: 6, alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        <label style={{ margin: 0 }} htmlFor={`${idPrefix}-amount-${product.id}`}>
          {mode === "unit" ? "Liczba sztuk" : "Porcja (g)"}
        </label>
        <input
          id={`${idPrefix}-amount-${product.id}`}
          type="number"
          min="0"
          step={mode === "unit" ? "0.5" : "1"}
          style={{ width: 90 }}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        {hint && (
          <button
            type="button"
            className="btn btn--ghost btn--small"
            onClick={() => switchMode(mode === "unit" ? "g" : "unit")}
          >
            {mode === "unit" ? "Licz w gramach" : `Licz w sztukach (${product.unit_name})`}
          </button>
        )}
        <span className="badge badge--accent">{formatPortion(values)}</span>
      </div>
      {hint && (
        <div className="meta">
          {hint}
          {mode === "unit" && grams > 0 && <> — wpisana porcja to {values.grams} g</>}
        </div>
      )}
    </div>
  );
}

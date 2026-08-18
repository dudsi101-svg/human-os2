import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, saveBlobAs } from "../../api";
import {
  ErrorBox, ExerciseDetail, ExerciseFilterBar, LogoutButton, SheetImportPanel,
  Spinner, TabPanel, Tabs, TopBar,
} from "../../components";
import { EMPTY_FILTERS, ExerciseFilters, exerciseQuery } from "../../exerciseFilters";
import {
  ExerciseImportReport,
  hasChanges,
  importSummary,
  noChangesHint,
  unmappedLine,
} from "../../exerciseImport";
import OcrCapture from "../../OcrCapture";
import {
  OcrTask,
  appendText,
  missingProductFields,
  modeLabel,
  productFormFromProposal,
} from "../../ocrUtils";
import {
  ExerciseFormValues,
  ExerciseProposal,
  ParseDescriptionResponse,
  fieldLabels,
  fieldsToInsert,
  mergeProposalIntoForm,
  proposalMessage,
  provenanceFor,
} from "../../exerciseParser";
import {
  FoodDisclaimer,
  FoodFilters,
  FoodLoadMore,
  FoodProductCard,
  useFoodCatalog,
} from "../../FoodCatalog";
import {
  DietSuggestionResult,
  EXERCISE_LEVEL_LABELS,
  ExerciseLibraryItem,
  FoodImportResult,
  ExerciseListResponse,
  FoodProductRow,
  KNOWLEDGE_CATEGORY_SUGGESTIONS,
  KnowledgeItemRow,
  MOVEMENT_PATTERN_LABELS,
  MUSCLE_GROUP_LABELS,
  MUSCLE_LABELS,
  muscleLabels,
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
      <Tabs tabs={TABS} value={tab} onChange={setTab} label="Sekcje bazy wiedzy" />
      <TabPanel id={tab}>
        {tab === "artykuly" && <ArticlesTab />}
        {tab === "cwiczenia" && <ExercisesTab />}
        {tab === "produkty" && <ProductsTab />}
        {tab === "dieta" && <DietComposerTab />}
      </TabPanel>
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
          <h2>{editing === "new" ? "Nowy materiał" : "Edytuj materiał"}</h2>
          <label htmlFor="art-title">Tytuł</label>
          <input id="art-title" required value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div className="field-row">
            <div>
              <label htmlFor="art-category">Kategoria</label>
              <input id="art-category" list="knowledge-categories" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <datalist id="knowledge-categories">
                {KNOWLEDGE_CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
              </datalist>
            </div>
            <div className="row" style={{ alignItems: "center", marginTop: 24 }}>
              <input type="checkbox" id="pinned" checked={form.pinned}
                onChange={(e) => setForm({ ...form, pinned: e.target.checked })} />
              <label htmlFor="pinned" style={{ margin: 0 }}>Przypnij jako polecane</label>
            </div>
          </div>
          <label htmlFor="art-body">Treść</label>
          <textarea id="art-body" value={form.body} style={{ minHeight: 140 }}
            onChange={(e) => setForm({ ...form, body: e.target.value })} />
          <label htmlFor="art-url">Link zewnętrzny (opcjonalnie)</label>
          <input id="art-url" type="url" placeholder="https://…" value={form.external_url}
            onChange={(e) => setForm({ ...form, external_url: e.target.value })} />
          <label htmlFor="art-file">Załącznik (PDF/obraz/wideo, opcjonalnie)</label>
          <input id="art-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf,video/mp4"
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
          <button className="btn btn--ghost btn--small" aria-pressed={showArchived}
            onClick={() => setShowArchived(!showArchived)}>
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

/** Kształt formularza mieszka w `exerciseParser.ts` — ta sama definicja
 * służy scalaniu propozycji z opisu (jedno źródło prawdy). */
type ExerciseForm = ExerciseFormValues;

const EMPTY_EXERCISE_FORM: ExerciseForm = {
  name: "", muscle_group: "NOGI", how_to: "", benefit: "", equipment: "", video_url: "",
  muscles_primary: [], muscles_secondary: [], level: "", pattern: "",
  steps: [""], mistakes: [""], cues: [""], safety: "", easier: "", harder: "",
  tempo_hint: "", breathing: "",
};

/** Pola, których nie dotyka czytanie opisu: nazwa angielska, tagi i ślad
 * po imporcie biblioteki. Trzymamy je osobno, żeby kontrakt formularza
 * dzielony z parserem (`ExerciseFormValues`) się nie rozjechał. */
interface ExerciseExtra {
  name_en: string;
  tags: string;
  source_ref: string | null;
  review_reason: string | null;
}

const EMPTY_EXTRA: ExerciseExtra = {
  name_en: "", tags: "", source_ref: null, review_reason: null,
};

/** Tagi w interfejsie to jedno pole tekstowe rozdzielone przecinkami —
 * krótsze niż osobny edytor listy, a i tak zapisujemy listę. */
function splitTags(value: string): string[] {
  return value.split(",").map((t) => t.trim()).filter(Boolean).slice(0, 12);
}

/** Edytor listy pozycji (kroki techniki / błędy / wskazówki): dodawanie
 * i usuwanie pojedynczych wierszy. Każde pole ma własną etykietę dla
 * czytników ekranu. */
function ListEditor({ id, label, hint, values, onChange, addLabel }: {
  id: string;
  label: string;
  hint?: string;
  values: string[];
  onChange: (next: string[]) => void;
  addLabel: string;
}) {
  return (
    <fieldset className="list-editor">
      <legend>{label}</legend>
      {hint && <p className="dim" style={{ margin: "0 0 6px", fontSize: "0.85rem" }}>{hint}</p>}
      {values.map((value, i) => (
        <div className="row" key={i} style={{ marginBottom: 6, alignItems: "center" }}>
          <label className="sr-only" htmlFor={`${id}-${i}`}>{label} — pozycja {i + 1}</label>
          <input id={`${id}-${i}`} value={value} style={{ flex: 1 }}
            onChange={(e) => onChange(values.map((v, j) => (j === i ? e.target.value : v)))} />
          <button type="button" className="btn btn--ghost btn--small"
            aria-label={`Usuń pozycję ${i + 1} z listy „${label}”`}
            onClick={() => onChange(values.filter((_, j) => j !== i))}>
            Usuń
          </button>
        </div>
      ))}
      <button type="button" className="btn btn--ghost btn--small"
        onClick={() => onChange([...values, ""])}>
        + {addLabel}
      </button>
    </fieldset>
  );
}

/** Wybór partii mięśniowych ze SŁOWNIKA (te same klucze co rysunek
 * sylwetki) — nic nie jest dobierane automatycznie, decyduje trener. */
function MusclePicker({ id, label, selected, onChange }: {
  id: string; label: string; selected: string[]; onChange: (next: string[]) => void;
}) {
  const toggle = (key: string) =>
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  return (
    <fieldset className="muscle-picker">
      <legend>{label}</legend>
      <div className="muscle-picker__grid">
        {Object.entries(MUSCLE_LABELS).map(([key, name]) => (
          <label key={key} htmlFor={`${id}-${key}`} className="muscle-picker__item">
            <input type="checkbox" id={`${id}-${key}`} checked={selected.includes(key)}
              onChange={() => toggle(key)} />
            <span>{name}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

const EX_PAGE_SIZE = 40;

function ExercisesTab() {
  const [items, setItems] = useState<ExerciseLibraryItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<ExerciseForm>(EMPTY_EXERCISE_FORM);
  const [busy, setBusy] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [filters, setFilters] = useState<ExerciseFilters>(EMPTY_FILTERS);
  const [loadingMore, setLoadingMore] = useState(false);
  // Proweniencja wpisu: `null` = trener wypełnił tabelę sam (w bazie
  // zostaje NULL — nie deklarujemy za nikogo, skąd wzięły się dane).
  const [provenance, setProvenance] = useState<
    { source_kind: string; source_engine: string | null } | null
  >(null);
  const [extra, setExtra] = useState<ExerciseExtra>(EMPTY_EXTRA);

  const load = useCallback((offset = 0) => {
    if (offset > 0) setLoadingMore(true);
    const query = exerciseQuery(filters, offset, EX_PAGE_SIZE, {
      status: showArchived ? "ARCHIVED" : "ACTIVE",
    });
    api.get<ExerciseListResponse>(`/api/coach/exercises?${query}`)
      .then((d) => {
        setItems((prev) => (offset > 0 && prev ? [...prev, ...d.items] : d.items));
        setTotal(d.total);
        setHasMore(d.has_more);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingMore(false));
  }, [filters, showArchived]);
  // Krótkie opóźnienie: przy pisaniu nie wysyłamy zapytania z każdą literą.
  useEffect(() => {
    const timer = setTimeout(() => load(0), 200);
    return () => clearTimeout(timer);
  }, [load]);

  function startNew() {
    setForm(EMPTY_EXERCISE_FORM);
    setProvenance(null);
    setExtra(EMPTY_EXTRA);
    setEditing("new");
  }

  function startEdit(item: ExerciseLibraryItem) {
    // Zwykła edycja nie ma prawa skasować proweniencji zapisanej wcześniej.
    setProvenance(
      item.source_kind
        ? { source_kind: item.source_kind, source_engine: item.source_engine }
        : null
    );
    setExtra({
      name_en: item.name_en ?? "",
      tags: item.tags.join(", "),
      source_ref: item.source_ref,
      review_reason: item.review_reason ?? null,
    });
    setForm({
      name: item.name, muscle_group: item.muscle_group, how_to: item.how_to,
      benefit: item.benefit ?? "", equipment: item.equipment ?? "",
      video_url: item.video_url ?? "",
      muscles_primary: item.muscles_primary, muscles_secondary: item.muscles_secondary,
      level: item.level ?? "", pattern: item.pattern ?? "",
      steps: item.steps.length ? item.steps : [""],
      mistakes: item.mistakes.length ? item.mistakes : [""],
      cues: item.cues.length ? item.cues : [""],
      safety: item.safety ?? "", easier: item.easier ?? "", harder: item.harder ?? "",
      tempo_hint: item.tempo_hint ?? "", breathing: item.breathing ?? "",
    });
    setEditing(item.id);
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const clean = (list: string[]) => list.map((v) => v.trim()).filter(Boolean);
    try {
      const steps = clean(form.steps);
      const payload = {
        name: form.name,
        muscle_group: form.muscle_group,
        // Pole zgodności wstecznej: gdy trener wypełnił kroki, a nie
        // wpisał skróconego opisu, składamy go z kroków.
        how_to: form.how_to.trim() || steps.join(" "),
        benefit: form.benefit || null,
        equipment: form.equipment || null,
        video_url: form.video_url || null,
        muscles_primary: form.muscles_primary,
        muscles_secondary: form.muscles_secondary,
        level: form.level || null,
        pattern: form.pattern || null,
        steps,
        mistakes: clean(form.mistakes),
        cues: clean(form.cues),
        safety: form.safety || null,
        easier: form.easier || null,
        harder: form.harder || null,
        tempo_hint: form.tempo_hint || null,
        breathing: form.breathing || null,
        name_en: extra.name_en.trim() || null,
        tags: splitTags(extra.tags),
        source_ref: extra.source_ref,
        // Notatka „opis ogólny” znika, gdy trener ją zdejmie — to jego
        // notatka robocza, nie flaga wystawiona przez system.
        review_reason: extra.review_reason,
        ...(provenance ?? {}),
      };
      if (editing === "new") {
        await api.post("/api/coach/exercises", payload);
      } else {
        await api.put(`/api/coach/exercises/${editing}`, payload);
      }
      setEditing(null);
      load(0);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    try {
      await api.post(`/api/coach/exercises/${id}/status?status=${status}`);
      load(0);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (error && !items) return <ErrorBox error={error} onRetry={() => load(0)} />;
  if (!items) return <Spinner />;

  const byGroup = new Map<string, ExerciseLibraryItem[]>();
  for (const i of items) {
    if (!byGroup.has(i.muscle_group)) byGroup.set(i.muscle_group, []);
    byGroup.get(i.muscle_group)!.push(i);
  }

  return (
    <>
      <ErrorBox error={error} />
      <p className="dim" style={{ marginTop: -8 }}>
        Know-how: technika wykonania, najczęstsze błędy, wskazówki i warianty —
        widoczne dla wszystkich aktywnie prowadzonych klientów. To materiał
        treningowy, nie porada medyczna: aplikacja niczego nie dobiera
        automatycznie, ćwiczenia do planu wybierasz Ty.
      </p>

      {editing && (
        <form className="card card--accent" onSubmit={save}>
          <h2>{editing === "new" ? "Nowe ćwiczenie" : "Edytuj ćwiczenie"}</h2>
          <DescriptionAssist
            form={form}
            onInsert={(next, engine) => {
              setForm(next);
              setProvenance(provenanceFor(engine));
            }}
          />
          {extra.review_reason && (
            <div className="card card--accent" style={{ marginBottom: 10 }}>
              <p className="meta" style={{ marginTop: 0 }}>
                <b>Notatka robocza:</b> {extra.review_reason}
              </p>
              <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
                Widzisz ją tylko Ty — klient nigdy nie dostaje tej informacji.
              </p>
              <button type="button" className="btn btn--ghost btn--small"
                onClick={() => setExtra({ ...extra, review_reason: null })}>
                Zdejmij notatkę (opis dopracowany)
              </button>
            </div>
          )}
          <label htmlFor="ex-name">Nazwa</label>
          <input id="ex-name" required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div className="field-row">
            <div>
              <label htmlFor="ex-name-en">Nazwa angielska (opcjonalnie)</label>
              <input id="ex-name-en" value={extra.name_en} placeholder="np. Barbell Bench Press"
                onChange={(e) => setExtra({ ...extra, name_en: e.target.value })} />
            </div>
            <div>
              <label htmlFor="ex-tags">Tagi (po przecinku)</label>
              <input id="ex-tags" value={extra.tags} placeholder="np. klatka piersiowa, wielostawowe"
                onChange={(e) => setExtra({ ...extra, tags: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div>
              <label htmlFor="ex-group">Grupa (widok listy)</label>
              <select id="ex-group" value={form.muscle_group}
                onChange={(e) => setForm({ ...form, muscle_group: e.target.value })}>
                {Object.entries(MUSCLE_GROUP_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="ex-equipment">Sprzęt (opcjonalnie)</label>
              <input id="ex-equipment" value={form.equipment}
                onChange={(e) => setForm({ ...form, equipment: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div>
              <label htmlFor="ex-level">Poziom</label>
              <select id="ex-level" value={form.level}
                onChange={(e) => setForm({ ...form, level: e.target.value })}>
                <option value="">— nie określono —</option>
                {Object.entries(EXERCISE_LEVEL_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="ex-pattern">Wzorzec ruchu</label>
              <select id="ex-pattern" value={form.pattern}
                onChange={(e) => setForm({ ...form, pattern: e.target.value })}>
                <option value="">— nie określono —</option>
                {Object.entries(MOVEMENT_PATTERN_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <MusclePicker id="ex-primary" label="Mięśnie główne"
            selected={form.muscles_primary}
            onChange={(next) => setForm({ ...form, muscles_primary: next })} />
          <MusclePicker id="ex-secondary" label="Mięśnie pomocnicze"
            selected={form.muscles_secondary}
            onChange={(next) => setForm({ ...form, muscles_secondary: next })} />

          <ListEditor id="ex-steps" label="Kroki techniki" addLabel="krok"
            hint="3–6 punktów: ustawienie, ruch, zakończenie."
            values={form.steps}
            onChange={(next) => setForm({ ...form, steps: next })} />
          <ListEditor id="ex-mistakes" label="Najczęstsze błędy" addLabel="błąd"
            values={form.mistakes}
            onChange={(next) => setForm({ ...form, mistakes: next })} />
          <ListEditor id="ex-cues" label="Wskazówki („cue”)" addLabel="wskazówkę"
            hint="Krótkie hasła, które klient ma sobie powiedzieć w trakcie serii."
            values={form.cues}
            onChange={(next) => setForm({ ...form, cues: next })} />

          <div className="field-row">
            <div>
              <label htmlFor="ex-tempo">Tempo (opcjonalnie)</label>
              <input id="ex-tempo" value={form.tempo_hint} placeholder="np. 3010"
                onChange={(e) => setForm({ ...form, tempo_hint: e.target.value })} />
            </div>
            <div>
              <label htmlFor="ex-breathing">Oddech (opcjonalnie)</label>
              <input id="ex-breathing" value={form.breathing}
                onChange={(e) => setForm({ ...form, breathing: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div>
              <label htmlFor="ex-easier">Wariant łatwiejszy</label>
              <input id="ex-easier" value={form.easier}
                onChange={(e) => setForm({ ...form, easier: e.target.value })} />
            </div>
            <div>
              <label htmlFor="ex-harder">Wariant trudniejszy</label>
              <input id="ex-harder" value={form.harder}
                onChange={(e) => setForm({ ...form, harder: e.target.value })} />
            </div>
          </div>
          <label htmlFor="ex-safety">Uwagi bezpieczeństwa</label>
          <textarea id="ex-safety" value={form.safety}
            placeholder="Na co uważać przy wykonaniu; przy bólu lub urazie — konsultacja ze specjalistą."
            onChange={(e) => setForm({ ...form, safety: e.target.value })} />
          <label htmlFor="ex-howto">Skrócony opis (zgodność wsteczna)</label>
          <textarea id="ex-howto" value={form.how_to} style={{ minHeight: 70 }}
            placeholder="Zostaw puste — złożymy go z kroków techniki."
            onChange={(e) => setForm({ ...form, how_to: e.target.value })} />
          <label htmlFor="ex-benefit">Co to daje (efekt)</label>
          <textarea id="ex-benefit" value={form.benefit}
            onChange={(e) => setForm({ ...form, benefit: e.target.value })} />
          <label htmlFor="ex-video">Link do wideo (opcjonalnie)</label>
          <input id="ex-video" type="url" placeholder="https://…" value={form.video_url}
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
        <>
          <LibraryImport onImported={() => load(0)} />
          <SheetImportPanel
            kind="EXERCISES"
            title="Importuj bazę ćwiczeń z pliku"
            description={
              <>
                Masz swoją bazę w arkuszu? Wgraj ją jako <b>CSV lub XLSX</b> —
                zamiast przepisywać pozycje ręcznie. Najpierw zobaczysz raport:
                co powstanie, co się zmieni i które wiersze odpadły oraz
                dlaczego. Zapis jest osobnym kliknięciem. Wartości spoza
                słownika (partie mięśniowe, poziom, wzorzec ruchu) nie są
                zgadywane — pole zostaje puste, a informacja trafia do raportu.
              </>
            }
            schemaUrl="/api/coach/exercises/import-schema"
            importUrl="/api/coach/exercises/import-file"
            exampleUrl="/api/coach/exercises/import-example"
            exportUrl="/api/coach/exercises/export-file"
            exampleFileName="dzik-os-cwiczenia-wzor.csv"
            exportFileName="dzik-os-cwiczenia.csv"
            onImported={() => load(0)}
          />
          <div className="row" style={{ marginBottom: 10 }}>
            <button className="btn btn--small" onClick={startNew}>+ Nowe ćwiczenie</button>
            <button className="btn btn--ghost btn--small" aria-pressed={showArchived}
              onClick={() => setShowArchived(!showArchived)}>
              {showArchived ? "Pokaż aktywne" : "Pokaż zarchiwizowane"}
            </button>
          </div>
          <ExerciseFilterBar idPrefix="co" value={filters} onChange={setFilters} />
          <p className="dim" aria-live="polite">
            {total === 0
              ? "Brak ćwiczeń pasujących do wyszukiwania."
              : `Znaleziono ${total} ćwiczeń — pokazano ${items.length}.`}
          </p>
        </>
      )}

      {Array.from(byGroup.entries()).map(([group, list]) => (
        <div key={group} style={{ marginBottom: 14 }}>
          <h2 style={{ margin: "0 0 6px" }}>{MUSCLE_GROUP_LABELS[group] ?? group}</h2>
          <div className="list">
            {list.map((i) => <CoachExerciseCard key={i.id} item={i} onEdit={startEdit}
              onStatus={setStatus} />)}
          </div>
        </div>
      ))}
      {hasMore && !editing && (
        <button className="btn btn--ghost" disabled={loadingMore}
          onClick={() => load(items.length)}>
          {loadingMore ? "Wczytywanie…" : "Pokaż więcej"}
        </button>
      )}
    </>
  );
}

/** Panel „Importuj bibliotekę ćwiczeń”.
 *
 * Te same reguły interfejsu co przy czytaniu opisu i przy OCR:
 * * najpierw PODGLĄD (`dry_run=true`) — nic się nie zapisuje, dopóki
 *   trener nie kliknie „Zaimportuj”;
 * * raport pokazuje wprost, ile pozycji powstanie, ile zostanie tylko
 *   uzupełnionych (pola puste) i czego NIE udało się zmapować;
 * * import nigdy nie nadpisuje opisów pisanych pod konkretne ćwiczenie —
 *   piszemy to w interfejsie, a nie tylko w dokumentacji.
 */
function LibraryImport({ onImported }: { onImported: () => void }) {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<ExerciseImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(dryRun: boolean) {
    setBusy(true);
    setError(null);
    try {
      const data = await api.post<ExerciseImportReport>(
        `/api/coach/exercises/import-library?dry_run=${dryRun}`
      );
      setReport(data);
      setSaved(!dryRun);
      if (!dryRun) onImported();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="row row--between">
        <b>Importuj bibliotekę ćwiczeń</b>
        <button type="button" className="btn btn--ghost btn--small" aria-expanded={open}
          onClick={() => setOpen(!open)}>
          {open ? "Zwiń" : "Rozwiń"}
        </button>
      </div>
      {open && (
        <>
          <p className="dim" style={{ marginTop: 4 }}>
            Dokłada do Twojej bazy pozycje z gotowej biblioteki. Ćwiczenia,
            które już masz, <b>zostają nietknięte</b> — import uzupełnia w nich
            wyłącznie pola, które są puste, i nigdy nie nadpisuje Twoich
            opisów. Najpierw zobaczysz raport, zapis jest osobnym kliknięciem.
          </p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            <button type="button" className="btn btn--small" disabled={busy}
              onClick={() => run(true)}>
              {busy ? "Liczenie…" : "Pokaż, co się zmieni"}
            </button>
            {report && !saved && hasChanges(report) && (
              <button type="button" className="btn btn--small" disabled={busy}
                onClick={() => run(false)}>
                Zaimportuj do mojej bazy
              </button>
            )}
            {report && (
              <button type="button" className="btn btn--ghost btn--small"
                onClick={() => { setReport(null); setSaved(false); }}>
                Zamknij raport
              </button>
            )}
          </div>
          <ErrorBox error={error} />
          {report && (
            <div className="card card--accent" style={{ marginTop: 8 }}>
              <p className="meta" style={{ marginTop: 0 }} aria-live="polite">
                {importSummary(report)}
              </p>
              <p className="dim" style={{ fontSize: "0.85rem" }}>
                Źródło: {report.library}.
              </p>
              {!hasChanges(report) && (
                <p className="meta">{noChangesHint(report)}</p>
              )}
              {report.created > 0 && (
                <p className="meta">
                  Nowe pozycje dostaną notatkę roboczą „opis ogólny”: technika w
                  bibliotece jest wspólna dla całego wzorca ruchu, więc warto
                  opisać je po swojemu. Notatkę widzisz tylko Ty.
                </p>
              )}
              {report.unmapped_muscles.length > 0 && (
                <p className="meta">
                  <b>Nie rozpoznano partii mięśniowych:</b>{" "}
                  {unmappedLine(report.unmapped_muscles)} — te pola zostają
                  puste, uzupełnij je sam.
                </p>
              )}
              {report.unmapped_patterns.length > 0 && (
                <p className="meta">
                  <b>Nie rozpoznano wzorców ruchu:</b>{" "}
                  {unmappedLine(report.unmapped_patterns)} — te pola zostają
                  puste, uzupełnij je sam.
                </p>
              )}
              {report.errors.length > 0 && (
                <ul className="meta" style={{ margin: "0 0 6px 18px" }}>
                  {report.errors.map((e, i) => (
                    <li key={i}>{e.exercise}: {e.message}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Panel „Uzupełnij z opisu”: wklejony opis ćwiczenia → propozycja pól.
 *
 * Reguły interfejsu (te same co przy OCR):
 * * wynik jest PROPOZYCJĄ — nic nie trafia do formularza bez kliknięcia
 *   „Wstaw do formularza”, a do bazy dopiero po zapisaniu ćwiczenia;
 * * domyślnie uzupełniamy WYŁĄCZNIE puste pola (praca trenera nie znika);
 * * widać, który tryb zadziałał i dlaczego, czego nie udało się odczytać i
 *   co warto potwierdzić — brak nigdy nie udaje wartości;
 * * pojawienie się propozycji ogłasza `aria-live`, a każde pole ma
 *   etykietę powiązaną `for`/`id` (runda P10). */
function DescriptionAssist({ form, onInsert }: {
  form: ExerciseFormValues;
  onInsert: (next: ExerciseFormValues, engine: "LOCAL" | "EXTENDED") => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [result, setResult] = useState<ParseDescriptionResponse | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocrOpen, setOcrOpen] = useState(false);

  async function read() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.post<ParseDescriptionResponse>(
        "/api/coach/exercises/parse-description", { description: text }
      );
      setResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const willInsert = result ? fieldsToInsert(form, result.proposal, overwrite) : [];

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="row row--between">
        <b>Uzupełnij z opisu</b>
        <button type="button" className="btn btn--ghost btn--small" aria-expanded={open}
          onClick={() => setOpen(!open)}>
          {open ? "Zwiń" : "Rozwiń"}
        </button>
      </div>
      {open && (
        <>
          <p className="dim" style={{ marginTop: 4 }}>
            Wklej jednolity opis ćwiczenia — wyciągniemy z niego, co się da, i
            pokażemy propozycję do zatwierdzenia. Czego nie da się odczytać,
            zostaje puste i jest wypisane wprost. Nic nie zapisuje się samo.
          </p>
          <label htmlFor="ex-src-desc">Opis ćwiczenia (wklej tekst)</label>
          <textarea id="ex-src-desc" value={text} style={{ minHeight: 130 }}
            placeholder={"Np.\nPrzysiad ze sztangą\nMięśnie: głównie czworogłowy uda "
              + "i pośladki, wspomagająco core\nWykonanie:\n1. …"}
            onChange={(e) => setText(e.target.value)} />
          <div className="row" style={{ flexWrap: "wrap" }}>
            <button type="button" className="btn btn--small" disabled={busy || !text.trim()}
              onClick={read}>
              {busy ? "Czytanie…" : "Uzupełnij z opisu"}
            </button>
            <button type="button" className="btn btn--ghost btn--small" aria-expanded={ocrOpen}
              onClick={() => setOcrOpen(!ocrOpen)}>
              {ocrOpen ? "Zamknij przepisywanie" : "Przepisz ze zdjęcia"}
            </button>
            {text && (
              <button type="button" className="btn btn--ghost btn--small"
                onClick={() => { setText(""); setResult(null); }}>
                Wyczyść opis
              </button>
            )}
          </div>
          <ErrorBox error={error} />
          {ocrOpen && (
            <OcrCapture
              purpose="PLAN"
              title="Opis ćwiczenia ze zdjęcia"
              hint={"Zrób zdjęcie kartki albo strony z książki. Przepisany tekst "
                + "wstawimy do pola opisu powyżej — stamtąd uzupełnisz tabelę."}
              approveLabel="Wstaw tekst do opisu"
              onApprove={(_task, recognized) => {
                // Dopisujemy na końcu — nigdy nie kasujemy tego, co już jest.
                setText((current) => appendText(current, recognized));
                setOcrOpen(false);
                return true;
              }}
              onClose={() => setOcrOpen(false)}
            />
          )}
          <p className="dim" aria-live="polite" style={{ marginTop: 8 }}>
            {proposalMessage(result, form, modeLabel(result?.engine), overwrite)}
          </p>
          {result && (
            <div className="card card--accent" style={{ marginTop: 6 }}>
              <p className="meta" style={{ marginTop: 0 }}>
                Odczytano w trybie: {modeLabel(result.engine)}.
                {result.mode_reason ? ` ${result.mode_reason}` : ""}
              </p>
              <ProposalPreview title="Zostanie wstawione" keys={willInsert}
                proposal={result.proposal} labels={result.field_labels}
                empty="Nic — wszystkie odczytane pola są już wypełnione." />
              {result.needs_confirmation.length > 0 && (
                <p className="meta">
                  <b>Sprawdź szczególnie:</b>{" "}
                  {fieldLabels(result.needs_confirmation, result.field_labels).join(", ")}
                  {result.needs_confirmation.includes("muscles_primary")
                    ? " — w opisie nie było podziału na mięśnie główne i pomocnicze, "
                      + "więc wszystko trafiło do głównych."
                    : ""}
                </p>
              )}
              {result.unrecognized.length > 0 && (
                <p className="meta">
                  <b>Nie udało się odczytać:</b>{" "}
                  {fieldLabels(result.unrecognized, result.field_labels).join(", ")} —
                  te pola zostają puste, uzupełnij je sam.
                </p>
              )}
              <div className="row" style={{ alignItems: "center" }}>
                <input type="checkbox" id="ex-src-overwrite" checked={overwrite}
                  onChange={(e) => setOverwrite(e.target.checked)} />
                <label htmlFor="ex-src-overwrite" style={{ margin: 0 }}>
                  Nadpisz także pola, które już wypełniłem
                </label>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <button type="button" className="btn btn--small"
                  disabled={willInsert.length === 0}
                  onClick={() => onInsert(
                    mergeProposalIntoForm(form, result.proposal, overwrite), result.engine
                  )}>
                  Wstaw do formularza
                </button>
                <button type="button" className="btn btn--ghost btn--small"
                  onClick={() => setResult(null)}>
                  Odrzuć propozycję
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/** Podgląd propozycji: etykieta pola + wartość, którą wstawimy. */
function ProposalPreview({ title, keys, proposal, labels, empty }: {
  title: string;
  keys: string[];
  proposal: ExerciseProposal;
  labels: Record<string, string>;
  empty: string;
}) {
  if (keys.length === 0) return <p className="meta">{empty}</p>;
  return (
    <>
      <p className="meta" style={{ marginBottom: 4 }}><b>{title}:</b></p>
      <ul className="meta" style={{ margin: "0 0 6px 18px" }}>
        {keys.map((key) => (
          <li key={key}>
            {labels[key] ?? key}: {proposalValue(key, proposal)}
          </li>
        ))}
      </ul>
    </>
  );
}

function proposalValue(key: string, proposal: ExerciseProposal): string {
  const value = proposal[key as keyof ExerciseProposal];
  if (key === "muscles_primary" || key === "muscles_secondary") {
    return muscleLabels(value as string[]);
  }
  if (key === "level") return EXERCISE_LEVEL_LABELS[value as string] ?? String(value);
  if (key === "pattern") return MOVEMENT_PATTERN_LABELS[value as string] ?? String(value);
  if (Array.isArray(value)) return value.join(" • ");
  return String(value ?? "");
}

function CoachExerciseCard({ item, onEdit, onStatus }: {
  item: ExerciseLibraryItem;
  onEdit: (item: ExerciseLibraryItem) => void;
  onStatus: (id: string, status: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <div className="row row--between">
        <b>{item.name}</b>
        <div className="row">
          <button className="btn btn--ghost btn--small" aria-expanded={open}
            onClick={() => setOpen(!open)}>
            {open ? "Zwiń" : "Podgląd"}
          </button>
          <button className="btn btn--ghost btn--small" onClick={() => onEdit(item)}>Edytuj</button>
          {item.status === "ACTIVE" ? (
            <button className="btn btn--danger btn--small"
              onClick={() => onStatus(item.id, "ARCHIVED")}>
              Archiwizuj
            </button>
          ) : (
            <button className="btn btn--ghost btn--small"
              onClick={() => onStatus(item.id, "ACTIVE")}>
              Przywróć
            </button>
          )}
        </div>
      </div>
      {item.muscles_primary.length > 0 && (
        <p className="meta" style={{ marginTop: 4 }}>{muscleLabels(item.muscles_primary)}</p>
      )}
      {open ? (
        <div style={{ marginTop: 8 }}><ExerciseDetail item={item} /></div>
      ) : (
        <>
          <p className="meta" style={{ marginTop: 6 }}>
            {item.steps[0] ?? item.how_to}
          </p>
          {item.equipment && <span className="badge">{item.equipment}</span>}
          {item.review_reason && (
            <p className="meta" style={{ marginTop: 6 }}>
              <b>Do dopracowania:</b> {item.review_reason}
            </p>
          )}
        </>
      )}
    </div>
  );
}

const EMPTY_PRODUCT_FORM = {
  name: "", category: "Inne", kcal_100g: "", protein_100g: "", fat_100g: "", carbs_100g: "",
  fiber_100g: "", default_portion_g: "", unit_name: "", unit_grams: "", source: "", note: "",
};

function numberOrNull(value: string): number | null {
  const trimmed = value.trim().replace(",", ".");
  return trimmed === "" ? null : Number(trimmed);
}

function ProductsTab() {
  const catalog = useFoodCatalog("/api/coach/food-products");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState(EMPTY_PRODUCT_FORM);
  const [busy, setBusy] = useState(false);
  const [importResult, setImportResult] = useState<FoodImportResult | null>(null);
  // Zdjęcie etykiety: identyfikator zadania OCR, z którego pochodzi
  // wstępnie wypełniony formularz. Zapis idzie wtedy ścieżką zatwierdzenia
  // propozycji, żeby produkt niósł proweniencję (skąd wzięły się wartości).
  const [ocrOpen, setOcrOpen] = useState(false);
  const [ocrTaskId, setOcrTaskId] = useState<string | null>(null);
  const [ocrMissing, setOcrMissing] = useState<string[]>([]);

  function startNew() {
    setForm(EMPTY_PRODUCT_FORM);
    setOcrTaskId(null);
    setOcrMissing([]);
    setEditing("new");
  }

  /** Zatwierdzona propozycja ze zdjęcia etykiety: wypełniamy formularz
   * i oddajemy go trenerowi do poprawienia. Nic nie jest jeszcze zapisane. */
  function fillFromOcr(task: OcrTask) {
    const filled = productFormFromProposal(task.proposal);
    setForm({ ...EMPTY_PRODUCT_FORM, ...filled });
    setOcrMissing(missingProductFields(filled));
    setOcrTaskId(task.id);
    setEditing("new");
    setOcrOpen(false);
    return true;
  }

  function startEdit(item: FoodProductRow) {
    setForm({
      name: item.name, category: item.category,
      kcal_100g: String(item.kcal_100g), protein_100g: String(item.protein_100g),
      fat_100g: String(item.fat_100g), carbs_100g: String(item.carbs_100g),
      fiber_100g: item.fiber_100g != null ? String(item.fiber_100g) : "",
      default_portion_g: item.default_portion_g != null ? String(item.default_portion_g) : "",
      unit_name: item.unit_name ?? "",
      unit_grams: item.unit_grams != null ? String(item.unit_grams) : "",
      source: item.source ?? "", note: item.note ?? "",
    });
    setOcrTaskId(null);
    setOcrMissing([]);
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
        fiber_100g: numberOrNull(form.fiber_100g),
        default_portion_g: numberOrNull(form.default_portion_g),
        unit_name: form.unit_name.trim() || null,
        unit_grams: numberOrNull(form.unit_grams),
        source: form.source.trim() || null,
        note: form.note.trim() || null,
      };
      if (ocrTaskId) {
        // Propozycja ze zdjęcia staje się produktem DOPIERO tutaj —
        // z zapisaną proweniencją (plik źródłowy + użyty silnik).
        await api.post(`/api/ocr/tasks/${ocrTaskId}/approve`, { product: payload });
        setOcrTaskId(null);
        setOcrMissing([]);
      } else if (editing === "new") {
        await api.post("/api/coach/food-products", payload);
      } else {
        await api.put(`/api/coach/food-products/${editing}`, payload);
      }
      setEditing(null);
      catalog.reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(id: string, status: string) {
    try {
      await api.post(`/api/coach/food-products/${id}/status?status=${status}`);
      catalog.reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function exportCsv() {
    setError(null);
    try {
      const blob = await api.get<Blob>("/api/coach/food-products/export");
      saveBlobAs(blob, "dzik-os-produkty.csv");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function importCsv(file: File) {
    setBusy(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await api.upload<FoodImportResult>(
        "/api/coach/food-products/import", file
      );
      setImportResult(result);
      catalog.reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (catalog.error && catalog.items.length === 0) {
    return <ErrorBox error={catalog.error} onRetry={catalog.reload} />;
  }

  return (
    <>
      <ErrorBox error={error} />
      <p className="dim" style={{ marginTop: -8 }}>
        Baza produktów z makroskładnikami na 100 g — wpisz gramaturę albo liczbę
        sztuk, żeby zobaczyć przeliczone kalorie i makro.
      </p>
      <FoodDisclaimer text={catalog.disclaimer} />

      {editing && (
        <form className="card card--accent" onSubmit={save}>
          <h2>{editing === "new" ? "Nowy produkt" : "Edytuj produkt"}</h2>
          {ocrTaskId && (
            <p className="alert alert--info" role="status" aria-live="polite">
              Formularz wypełniono wstępnie ze zdjęcia etykiety. Sprawdź każdą
              wartość — zapisuje się dopiero po Twoim zatwierdzeniu.
              {ocrMissing.length > 0
                && ` Nie udało się odczytać: ${ocrMissing.join(", ")} — uzupełnij ręcznie.`}
            </p>
          )}
          <div className="field-row">
            <div>
              <label htmlFor="fp-name">Nazwa</label>
              <input id="fp-name" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label htmlFor="fp-category">Kategoria</label>
              <input id="fp-category" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div><label htmlFor="fp-kcal">kcal / 100 g</label>
              <input id="fp-kcal" required type="number" step="0.1" min="0" value={form.kcal_100g}
                onChange={(e) => setForm({ ...form, kcal_100g: e.target.value })} /></div>
            <div><label htmlFor="fp-protein">Białko (g) / 100 g</label>
              <input id="fp-protein" required type="number" step="0.1" min="0"
                value={form.protein_100g}
                onChange={(e) => setForm({ ...form, protein_100g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label htmlFor="fp-fat">Tłuszcz (g) / 100 g</label>
              <input id="fp-fat" required type="number" step="0.1" min="0" value={form.fat_100g}
                onChange={(e) => setForm({ ...form, fat_100g: e.target.value })} /></div>
            <div><label htmlFor="fp-carbs">Węgle (g) / 100 g</label>
              <input id="fp-carbs" required type="number" step="0.1" min="0" value={form.carbs_100g}
                onChange={(e) => setForm({ ...form, carbs_100g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label htmlFor="fp-fiber">Błonnik (g) / 100 g — opcjonalnie</label>
              <input id="fp-fiber" type="number" step="0.1" min="0" value={form.fiber_100g}
                onChange={(e) => setForm({ ...form, fiber_100g: e.target.value })} /></div>
            <div><label htmlFor="fp-portion">Typowa porcja (g, opcjonalnie)</label>
              <input id="fp-portion" type="number" step="1" min="0" value={form.default_portion_g}
                onChange={(e) => setForm({ ...form, default_portion_g: e.target.value })} /></div>
          </div>
          <div className="field-row">
            <div><label htmlFor="fp-unit">Jednostka sztukowa (np. kromka, jajko)</label>
              <input id="fp-unit" value={form.unit_name} maxLength={60}
                onChange={(e) => setForm({ ...form, unit_name: e.target.value })} /></div>
            <div><label htmlFor="fp-unit-grams">Ile waży 1 sztuka (g)</label>
              <input id="fp-unit-grams" type="number" step="0.1" min="0" value={form.unit_grams}
                onChange={(e) => setForm({ ...form, unit_grams: e.target.value })} /></div>
          </div>
          <label htmlFor="fp-source">Źródło wartości (opcjonalnie)</label>
          <input id="fp-source" maxLength={200} value={form.source}
            placeholder="np. etykieta producenta, tabele wartości odżywczych"
            onChange={(e) => setForm({ ...form, source: e.target.value })} />
          <label htmlFor="fp-note">Uwagi (opcjonalnie)</label>
          <input id="fp-note" maxLength={300} value={form.note}
            placeholder="np. wartości dla produktu ugotowanego"
            onChange={(e) => setForm({ ...form, note: e.target.value })} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy}>{busy ? "Zapisywanie…" : "Zapisz"}</button>
            <button type="button" className="btn btn--ghost" onClick={() => setEditing(null)}>
              Anuluj
            </button>
          </div>
        </form>
      )}

      <div className="card">
        <h2>Własne produkty: import i eksport (CSV)</h2>
        <p className="dim" style={{ fontSize: "0.85rem", marginTop: -6 }}>
          Eksport zabiera Twój katalog w otwartym formacie — możesz go trzymać
          u siebie albo przenieść gdzie indziej. Import dopisuje i aktualizuje
          wyłącznie Twoje produkty (dopasowanie po nazwie); cudzych katalogów
          nigdy nie dotyka. Kolumny: nazwa, kategoria, kcal_100g, bialko_100g,
          tluszcz_100g, wegle_100g, blonnik_100g, porcja_g, jednostka,
          jednostka_g, zrodlo, uwagi.
        </p>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn--ghost btn--small" onClick={exportCsv}>
            Pobierz katalog (CSV)
          </button>
          <label className="btn btn--ghost btn--small" style={{ cursor: "pointer" }}>
            {busy ? "Wczytywanie…" : "Wgraj plik CSV"}
            <input type="file" accept=".csv,text/csv" style={{ display: "none" }}
              aria-label="Wgraj plik CSV z produktami"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) importCsv(file);
              }} />
          </label>
        </div>
        {importResult && (
          <div style={{ marginTop: 10 }}>
            <p className={importResult.errors.length ? "alert alert--warn" : "alert alert--info"}>
              Zaimportowano: {importResult.created} nowych,
              {" "}{importResult.updated} zaktualizowanych,
              {" "}{importResult.skipped} pominiętych.
            </p>
            {importResult.unknown_columns.length > 0 && (
              <p className="dim" style={{ fontSize: "0.85rem" }}>
                Pominięte nieznane kolumny: {importResult.unknown_columns.join(", ")}.
              </p>
            )}
            {importResult.errors.length > 0 && (
              <ul className="dim" style={{ fontSize: "0.85rem" }}>
                {importResult.errors.map((err, i) => (
                  <li key={i}>Wiersz {err.row} ({err.field}): {err.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <FoodFilters catalog={catalog} idPrefix="coach-food" />
      {!editing && (
        <div className="row" style={{ marginBottom: 10, flexWrap: "wrap" }}>
          <button className="btn btn--small" onClick={startNew}>+ Nowy produkt</button>
          <button className="btn btn--ghost btn--small" aria-expanded={ocrOpen}
            onClick={() => setOcrOpen(!ocrOpen)}>
            {ocrOpen ? "Zamknij przepisywanie" : "Przepisz ze zdjęcia (etykieta)"}
          </button>
        </div>
      )}
      {ocrOpen && !editing && (
        <OcrCapture
          purpose="PRODUKT"
          title="Etykieta produktu ze zdjęcia"
          hint={"Zrób zdjęcie tabeli wartości odżywczych. Odczytane wartości "
            + "trafią do formularza nowego produktu — sprawdzasz je i "
            + "zatwierdzasz Ty. Czego nie da się odczytać, zostaje puste."}
          approveLabel="Wypełnij formularz produktu"
          onApprove={(task) => fillFromOcr(task)}
          onClose={() => setOcrOpen(false)}
        />
      )}

      {catalog.loading && catalog.items.length === 0 && <Spinner />}
      <div className="list">
        {catalog.items.map((p) => (
          <FoodProductCard key={p.id} product={p} idPrefix="coach-portion" actions={
            <div className="row">
              <button className="btn btn--ghost btn--small" onClick={() => startEdit(p)}>
                Edytuj
              </button>
              <button className="btn btn--danger btn--small"
                onClick={() => setStatus(p.id, "ARCHIVED")}>
                Archiwizuj
              </button>
            </div>
          } />
        ))}
      </div>
      <FoodLoadMore catalog={catalog} />
    </>
  );
}

function DietComposerTab() {
  const catalog = useFoodCatalog("/api/coach/food-products");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Map<string, string>>(new Map());
  const [target, setTarget] = useState({
    kcal: "3000", protein_g: "180", fat_g: "80", carbs_g: "350",
  });
  const [result, setResult] = useState<DietSuggestionResult | null>(null);
  const [busy, setBusy] = useState(false);

  function toggle(item: FoodProductRow) {
    const next = new Map(selected);
    if (next.has(item.id)) next.delete(item.id);
    else next.set(item.id, item.name);
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
        product_ids: Array.from(selected.keys()),
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
    return result.items
      .map((i) => {
        const units = i.units && i.unit_name ? ` ≈ ${i.units} × ${i.unit_name}` : "";
        return `${i.name}: ${i.grams} g${units} (${i.kcal} kcal)`;
      })
      .join("\n");
  }

  return (
    <>
      <ErrorBox error={error} />
      <div className="card card--accent">
        <h2>Cel diety</h2>
        <p className="dim" style={{ marginTop: -6, fontSize: "0.85rem" }}>
          Wybierz produkty poniżej i wpisz cel. Wynik to wyłącznie przejrzysta
          arytmetyka podziału celu na gramaturę — nic nie zapisuje się
          automatycznie w planie klienta. Ty decydujesz, co i jak wpisać do diety.
        </p>
        <div className="field-row">
          <div><label htmlFor="dc-kcal">Cel kcal</label>
            <input id="dc-kcal" type="number" min="0" value={target.kcal}
              onChange={(e) => setTarget({ ...target, kcal: e.target.value })} /></div>
          <div><label htmlFor="dc-protein">Białko (g)</label>
            <input id="dc-protein" type="number" min="0" value={target.protein_g}
              onChange={(e) => setTarget({ ...target, protein_g: e.target.value })} /></div>
        </div>
        <div className="field-row">
          <div><label htmlFor="dc-fat">Tłuszcz (g)</label>
            <input id="dc-fat" type="number" min="0" value={target.fat_g}
              onChange={(e) => setTarget({ ...target, fat_g: e.target.value })} /></div>
          <div><label htmlFor="dc-carbs">Węglowodany (g)</label>
            <input id="dc-carbs" type="number" min="0" value={target.carbs_g}
              onChange={(e) => setTarget({ ...target, carbs_g: e.target.value })} /></div>
        </div>
        <div style={{ marginTop: 8 }}>
          <button className="btn btn--small" disabled={busy || selected.size === 0}
            onClick={compose}>
            {busy ? "Liczenie…" : `Ułóż sugestię (${selected.size} wybranych produktów)`}
          </button>
        </div>
      </div>

      {result && (
        <div className="card">
          <h2>Sugestia</h2>
          {result.warnings.map((w, i) => (
            <p className="alert alert--warn" key={i}>{w}</p>
          ))}
          <div className="stat-grid">
            <div className="stat"><b>{result.totals.kcal}</b>
              <span>kcal (cel {result.target.kcal})</span></div>
            <div className="stat"><b>{result.totals.protein_g} g</b>
              <span>białko (cel {result.target.protein_g})</span></div>
            <div className="stat"><b>{result.totals.fat_g} g</b>
              <span>tłuszcz (cel {result.target.fat_g})</span></div>
            <div className="stat"><b>{result.totals.carbs_g} g</b>
              <span>węgle (cel {result.target.carbs_g})</span></div>
            {result.totals.fiber_g != null && (
              <div className="stat"><b>{result.totals.fiber_g} g</b><span>błonnik</span></div>
            )}
          </div>
          {result.items.map((i) => (
            <div className="exercise" key={i.product_id}>
              <div><b>{i.name}</b><div className="meta">
                {i.grams} g
                {i.units && i.unit_name ? ` ≈ ${i.units} × ${i.unit_name}` : ""}
                {" · "}{i.kcal} kcal
                {i.fiber_g != null ? ` · Bł ${i.fiber_g} g` : ""}
              </div></div>
              <span className="badge">
                {i.macro_role === "PROTEIN" ? "białko" : i.macro_role === "FAT" ? "tłuszcz" : "węgle"}
              </span>
            </div>
          ))}
          <FoodDisclaimer text={result.disclaimer} />
          <p className="dim" style={{ fontSize: "0.85rem" }}>{result.note}</p>
          <label htmlFor="dc-result">Do skopiowania w zakładkę Dieta klienta</label>
          <textarea id="dc-result" readOnly value={asMealsText()} style={{ minHeight: 100 }} />
        </div>
      )}

      <h2>Produkty (zaznacz do kompozycji)</h2>
      {selected.size > 0 && (
        <p className="dim" style={{ fontSize: "0.85rem" }}>
          Wybrane: {Array.from(selected.values()).join(", ")}.
        </p>
      )}
      {catalog.error && <ErrorBox error={catalog.error} onRetry={catalog.reload} />}
      <FoodFilters catalog={catalog} idPrefix="diet-food" />
      {catalog.loading && catalog.items.length === 0 && <Spinner />}
      <div className="list">
        {catalog.items.map((p) => (
          <label className="card" key={p.id}
            style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
            <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p)}
              aria-label={`Zaznacz produkt: ${p.name}`} />
            <div>
              <b>{p.name}</b> <span className="badge">{p.category}</span>
              <div className="meta">
                {p.kcal_100g} kcal · B {p.protein_100g} g · T {p.fat_100g} g ·
                {" "}W {p.carbs_100g} g
                {p.fiber_100g != null ? ` · Bł ${p.fiber_100g} g` : ""} /100 g
              </div>
              {p.note && <div className="meta">Uwaga: {p.note}</div>}
            </div>
          </label>
        ))}
      </div>
      <FoodLoadMore catalog={catalog} />
    </>
  );
}

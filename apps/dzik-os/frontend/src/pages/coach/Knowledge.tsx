import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import { KNOWLEDGE_CATEGORY_SUGGESTIONS, KnowledgeItemRow } from "../../types";

const EMPTY_FORM = {
  title: "", category: "Trening", body: "", external_url: "", pinned: false,
};

export default function Knowledge() {
  const [items, setItems] = useState<KnowledgeItemRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<typeof EMPTY_FORM>(EMPTY_FORM);
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
    setForm(EMPTY_FORM);
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
    await api.post(`/api/coach/knowledge/${id}/status?status=${status}`);
    load();
  }

  if (error && !items) return <div className="page"><ErrorBox error={error} /></div>;
  if (!items) return <div className="page"><Spinner /></div>;

  const visible = items.filter((i) => (showArchived ? i.status === "ARCHIVED" : i.status === "ACTIVE"));

  return (
    <div className="page page--wide">
      <TopBar title="Baza wiedzy" right={<LogoutButton />} />
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
    </div>
  );
}

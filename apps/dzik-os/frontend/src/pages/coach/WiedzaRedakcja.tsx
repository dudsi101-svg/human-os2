import { useEffect, useState } from "react";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Icon, Spinner } from "../../components";
import { WiedzaKarta, WiedzaKartaPelna } from "../../types";

/**
 * Redakcja kart wiedzy (0.56.0): trener jest recenzentem i wydawcą.
 * Szkice z pakietu są niewidoczne dla klientów na produkcji, dopóki
 * trener ich nie opublikuje — a publikacja wymaga źródeł i daty
 * kolejnego przeglądu (serwer odmawia bez nich). Opublikowanej rewizji
 * nie edytuje się w miejscu: „Nowy szkic” tworzy kolejną rewizję.
 */

interface Lista {
  items: WiedzaKarta[];
  liczby: Record<string, number>;
  pokrycie: Record<string, boolean>;
  szkice_widoczne: boolean;
  zrodla: string[];
}

const STATUS_LABEL: Record<string, string> = {
  draft: "szkic", in_review: "w przeglądzie", published: "opublikowana", retired: "wycofana",
};

export default function WiedzaRedakcja() {
  const [lista, setLista] = useState<Lista | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wylaczone, setWylaczone] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [filtr, setFiltr] = useState<string>("wszystkie");
  const [otwarty, setOtwarty] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<Lista>("/api/coach/wiedza/artykuly")
      .then(setLista)
      .catch((e) => {
        if ((e as { status?: number }).status === 404) setWylaczone(true);
        else setError(e.message);
      });
  };
  useEffect(() => { load(); }, []);

  if (wylaczone) {
    return (
      <p className="dim">
        Nowa Wiedza jest wyłączona flagą <code>DZIK_WIEDZA_V2</code>. Klienci
        widzą poprzednią zakładkę; karty i ślady decyzji pozostają w bazie.
      </p>
    );
  }
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!lista) return <Spinner />;

  // Jedna pozycja na artykuł: najnowsza rewizja + status wszystkich.
  const wgArtykulu = new Map<string, WiedzaKarta[]>();
  for (const k of lista.items) {
    if (!wgArtykulu.has(k.id)) wgArtykulu.set(k.id, []);
    wgArtykulu.get(k.id)!.push(k);
  }
  const wiersze = Array.from(wgArtykulu.entries())
    .map(([id, rewizje]) => ({ id, rewizje, ostatnia: rewizje[rewizje.length - 1] }))
    .filter((w) => filtr === "wszystkie" || w.rewizje.some((r) => r.status === filtr))
    .sort((a, b) => a.ostatnia.category.localeCompare(b.ostatnia.category)
      || a.ostatnia.title.localeCompare(b.ostatnia.title, "pl"));
  const brakPokrycia = Object.entries(lista.pokrycie).filter(([, ok]) => !ok).map(([t]) => t);

  return (
    <>
      <div className="card">
        <h2><Icon name="knowledge" size={18} /> Karty wiedzy — redakcja</h2>
        <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
          Treści startowe to szkice bez przeglądu eksperckiego. Publikujesz je
          jako recenzent: sprawdź treść i źródła, ustaw datę kolejnego
          przeglądu. Na produkcji klient widzi wyłącznie opublikowane karty.
        </p>
        <div className="row">
          {Object.entries(lista.liczby).map(([s, n]) => (
            <span className="badge" key={s}>{STATUS_LABEL[s] ?? s}: {n}</span>
          ))}
          {lista.szkice_widoczne && <span className="badge badge--warn">tryb demonstracyjny: szkice widoczne</span>}
        </div>
        <p className="dim" style={{ fontSize: "0.85rem", margin: "8px 0 0" }}>
          Pokrycie typów elementów planu: {Object.values(lista.pokrycie).filter(Boolean).length}
          /{Object.keys(lista.pokrycie).length}
          {brakPokrycia.length > 0 && <> — brak: {brakPokrycia.join(", ")}</>}
        </p>
        <label htmlFor="wiedza-filtr">Pokaż</label>
        <select id="wiedza-filtr" value={filtr} onChange={(e) => setFiltr(e.target.value)}>
          <option value="wszystkie">wszystkie</option>
          <option value="draft">szkice</option>
          <option value="published">opublikowane</option>
          <option value="retired">wycofane</option>
        </select>
      </div>
      {status && <p role="status" className="alert alert--info">{status}</p>}
      <div className="list">
        {wiersze.map((w) => (
          <div className="card" key={w.id}>
            <div className="row row--between">
              <div>
                <b>{w.ostatnia.title}</b>
                <div className="meta">
                  {w.ostatnia.category_label} · {w.id} · rewizje: {w.rewizje.map((r) =>
                    `${r.revision} (${STATUS_LABEL[r.status] ?? r.status})`).join(", ")}
                  {w.ostatnia.next_review_at && <> · przegląd do {plDate(w.ostatnia.next_review_at)}</>}
                  {w.ostatnia.przeglad_po_terminie && <> · <span className="badge badge--warn">po terminie przeglądu</span></>}
                </div>
              </div>
              <button className="btn btn--ghost btn--small" aria-expanded={otwarty === w.id}
                onClick={() => setOtwarty(otwarty === w.id ? null : w.id)}>
                {otwarty === w.id ? "Zwiń" : "Otwórz"}
              </button>
            </div>
            {otwarty === w.id && (
              <Rewizja articleId={w.id} rewizja={w.ostatnia} zrodla={lista.zrodla}
                artykuly={Array.from(wgArtykulu.keys())}
                onDone={(msg) => { setStatus(msg); load(); }} />
            )}
          </div>
        ))}
      </div>
    </>
  );
}

function Rewizja({ articleId, rewizja, zrodla, artykuly, onDone }: {
  articleId: string; rewizja: WiedzaKarta; zrodla: string[]; artykuly: string[];
  onDone: (msg: string) => void;
}) {
  const [pelna, setPelna] = useState<WiedzaKartaPelna | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [edycja, setEdycja] = useState(false);
  const [form, setForm] = useState({ summary: "", detail: "", limits: "", steps: "", source_ids: "" });
  const [termin, setTermin] = useState("");
  const [zamiennik, setZamiennik] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<WiedzaKartaPelna>(`/api/coach/wiedza/artykuly/${articleId}/${rewizja.revision}`)
      .then((k) => {
        setPelna(k);
        setForm({ summary: k.summary, detail: k.detail, limits: k.limits,
          steps: k.steps.join("\n"), source_ids: k.sources.map((s) => s.id).join(", ") });
      })
      .catch((e) => setError(e.message));
  }, [articleId, rewizja.revision]);

  async function publikuj() {
    setBusy(true); setError(null);
    try {
      const r = await api.post<WiedzaKarta>(`/api/coach/wiedza/artykuly/${articleId}/publikuj`,
        { revision: rewizja.revision, next_review_at: termin || null });
      onDone(`Opublikowano „${r.title}” (rewizja ${r.revision}); kolejny przegląd do ${plDate(r.next_review_at)}.`);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function wycofaj() {
    setBusy(true); setError(null);
    try {
      await api.post(`/api/coach/wiedza/artykuly/${articleId}/wycofaj`, { zamiennik_id: zamiennik || null });
      onDone(`Wycofano „${rewizja.title}”. Zapisane zakładki pokażą „Materiał jest aktualizowany”.`);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function nowySzkic() {
    setBusy(true); setError(null);
    try {
      const r = await api.post<WiedzaKarta>(`/api/coach/wiedza/artykuly/${articleId}/rewizje`, {
        summary: form.summary, detail: form.detail, limits: form.limits,
        steps: form.steps.split("\n").map((s) => s.trim()).filter(Boolean),
        source_ids: form.source_ids.split(",").map((s) => s.trim()).filter(Boolean),
      });
      onDone(`Utworzono szkic „${r.title}” (rewizja ${r.revision}). Opublikowana rewizja pozostaje bez zmian.`);
      setEdycja(false);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  if (error && !pelna) return <ErrorBox error={error} />;
  if (!pelna) return <Spinner />;
  return (
    <div style={{ marginTop: 10 }}>
      <p style={{ margin: "0 0 6px" }}><b>W skrócie:</b> {pelna.summary}</p>
      {pelna.steps.length > 0 && (
        <ol className="wiedza-karta__kroki">{pelna.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      )}
      <p style={{ whiteSpace: "pre-wrap" }}>{pelna.detail}</p>
      <p className="dim" style={{ fontSize: "0.85rem" }}>Ograniczenia: {pelna.limits}</p>
      <p className="dim" style={{ fontSize: "0.85rem" }}>
        Autor: {pelna.author_label} · dowód: {pelna.evidence_kind} · źródła:{" "}
        {pelna.sources.map((s) => `${s.id} (${s.rola === "inspiracja_produktowa" ? "inspiracja produktowa" : s.title})`).join("; ")}
      </p>
      {pelna.media === null && pelna.exercise_id && (
        <p className="dim" style={{ fontSize: "0.85rem" }}>Multimedia: brak (film nie został dołączony).</p>
      )}
      <ErrorBox error={error} />
      {rewizja.status !== "published" && rewizja.status !== "retired" && (
        <div className="row" style={{ marginTop: 8, alignItems: "flex-end" }}>
          <div>
            <label htmlFor={`termin-${articleId}`}>Kolejny przegląd (opcjonalnie; domyślnie 12 mies., bezpieczeństwo 6)</label>
            <input id={`termin-${articleId}`} type="date" value={termin} onChange={(e) => setTermin(e.target.value)} />
          </div>
          <button className="btn btn--small" disabled={busy} onClick={publikuj}>
            Opublikuj jako recenzent
          </button>
        </div>
      )}
      {rewizja.status !== "retired" && (
        <div className="row" style={{ marginTop: 8, alignItems: "flex-end" }}>
          <div>
            <label htmlFor={`zam-${articleId}`}>Zamiennik po wycofaniu (opcjonalnie)</label>
            <select id={`zam-${articleId}`} value={zamiennik} onChange={(e) => setZamiennik(e.target.value)}>
              <option value="">— brak —</option>
              {artykuly.filter((a) => a !== articleId).map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <button className="btn btn--danger btn--small" disabled={busy} onClick={wycofaj}>Wycofaj</button>
          <button className="btn btn--ghost btn--small" onClick={() => setEdycja(!edycja)} aria-expanded={edycja}>
            {edycja ? "Anuluj szkic" : "Nowy szkic"}
          </button>
        </div>
      )}
      {edycja && (
        <div style={{ marginTop: 8 }}>
          <label htmlFor={`sum-${articleId}`}>W skrócie</label>
          <textarea id={`sum-${articleId}`} value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
          <label htmlFor={`steps-${articleId}`}>Praktyczne kroki (jeden na linię)</label>
          <textarea id={`steps-${articleId}`} value={form.steps} onChange={(e) => setForm({ ...form, steps: e.target.value })} />
          <label htmlFor={`det-${articleId}`}>Dowiedz się więcej</label>
          <textarea id={`det-${articleId}`} value={form.detail} onChange={(e) => setForm({ ...form, detail: e.target.value })} />
          <label htmlFor={`lim-${articleId}`}>Ograniczenia zastosowania</label>
          <textarea id={`lim-${articleId}`} value={form.limits} onChange={(e) => setForm({ ...form, limits: e.target.value })} />
          <label htmlFor={`src-${articleId}`}>Źródła (id z rejestru, po przecinku): {zrodla.join(", ")}</label>
          <input id={`src-${articleId}`} value={form.source_ids} onChange={(e) => setForm({ ...form, source_ids: e.target.value })} />
          <button className="btn btn--small" style={{ marginTop: 8 }} disabled={busy} onClick={nowySzkic}>
            Zapisz jako nowy szkic
          </button>
        </div>
      )}
    </div>
  );
}

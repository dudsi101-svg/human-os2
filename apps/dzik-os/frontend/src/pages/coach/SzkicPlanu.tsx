import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, ApiError } from "../../api";
import { WEEKDAYS } from "../../dates";
import { KIND_BADGE, opisPozycji, rodzajPozycji } from "../../pozycje";
import { Exercise } from "../../types";
import { ErrorBox, Spinner } from "../../components";
import {
  PlanKind,
  Roznice,
  Szkic,
  SzkicCwiczenie,
  SzkicDieta,
  SzkicOperacja,
  SzkicTrening,
  WynikPublikacji,
} from "../../types";

/**
 * Edytor szkicu planu (0.58.0): Edytuj → autozapis szkicu → Sprawdź
 * zmiany → Opublikuj zmiany i powiadom. Osobno: Odrzuć szkic.
 *
 * Zasady ze specyfikacji właściciela, które ten ekran egzekwuje:
 * * klient nic nie widzi do publikacji („Szkic — klient jeszcze nie widzi
 *   zmian”), a stan zapisu jest potwierdzany dopiero odpowiedzią serwera;
 * * każda karta ma menu działań dostępne z klawiatury i na telefonie
 *   (przycisk „Działania”, nie hover);
 * * usunięcie pojedynczego elementu jest natychmiastowe z „Cofnij”
 *   (przywraca pozycję i elementy podrzędne, bo wraca ten sam element
 *   z tym samym `id`); usunięcie dnia wymaga potwierdzenia z liczbą
 *   elementów;
 * * konflikt rewizji (inne urządzenie) i konflikt wersji bazowej są
 *   pokazywane wprost — nic nie jest nadpisywane po cichu.
 */

type Zapis = "zapisano" | "zapisywanie" | "blad" | "konflikt";

const POLA_CWICZENIA: [keyof SzkicCwiczenie, string, string][] = [
  ["sets", "serie", "np. 4"], ["reps", "powtórzenia", "np. 8"], ["weight", "obciążenie", "np. 70 kg"],
  ["rest", "przerwa", "np. 120 s"], ["tempo", "tempo", "np. 2011"], ["target_rir", "RIR/RPE", "np. 2"],
];

function useDebounced<T extends unknown[]>(fn: (...a: T) => void, ms: number) {
  const t = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cb = useRef(fn);
  cb.current = fn;
  return useCallback((...a: T) => {
    if (t.current) clearTimeout(t.current);
    t.current = setTimeout(() => cb.current(...a), ms);
  }, [ms]);
}

/** Menu działań karty: jeden przycisk otwiera listę, działa z klawiatury
 * (Escape zamyka, fokus wraca) i na telefonie (bez najechania myszką).
 *
 * Lista jest renderowana przez portal do `body` z pozycją `fixed`: karty
 * mają animację wejścia z `transform`, która tworzy kontekst warstw —
 * menu zagnieżdżone w karcie byłoby przykryte przez KOLEJNĄ kartę
 * (sprawdzone na żywo: „Dzień 2” przechwytywał kliknięcia w „Usuń”). */
function MenuDzialan({ etykieta, akcje }: {
  etykieta: string;
  akcje: { label: string; onClick: () => void; danger?: boolean; disabled?: string }[];
}) {
  const [open, setOpen] = useState(false);
  const [poz, setPoz] = useState<{ top: number; right: number } | null>(null);
  const btn = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  function przelacz() {
    if (open) { setOpen(false); return; }
    const r = btn.current?.getBoundingClientRect();
    if (r) setPoz({ top: r.bottom + 4, right: Math.max(8, window.innerWidth - r.right) });
    setOpen(true);
  }
  useEffect(() => {
    if (!open) return;
    // Pierwsza pozycja dostaje fokus (klawiatura); klik poza menu zamyka.
    menuRef.current?.querySelector<HTMLButtonElement>("[role=menuitem]:not(:disabled)")?.focus();
    const zamknij = (e: MouseEvent) => {
      if (menuRef.current?.contains(e.target as Node) || btn.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    const naEscape = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); btn.current?.focus(); } };
    document.addEventListener("mousedown", zamknij);
    document.addEventListener("keydown", naEscape);
    return () => { document.removeEventListener("mousedown", zamknij); document.removeEventListener("keydown", naEscape); };
  }, [open]);

  return (
    <div>
      <button type="button" ref={btn} className="btn btn--ghost btn--small" aria-haspopup="menu"
        aria-expanded={open} aria-label={`Działania: ${etykieta}`} onClick={przelacz}>
        Działania ▾
      </button>
      {open && poz && createPortal(
        <div role="menu" ref={menuRef} className="card" aria-label={`Działania: ${etykieta}`}
          style={{ position: "fixed", top: poz.top, right: poz.right, zIndex: 600, minWidth: 220, padding: 6, margin: 0, maxHeight: "60vh", overflowY: "auto" }}>
          {akcje.map((a) => (
            <button key={a.label} type="button" role="menuitem" title={a.disabled}
              className={"btn btn--small " + (a.danger ? "btn--danger" : "btn--ghost")}
              style={{ display: "block", width: "100%", textAlign: "left", marginBottom: 4 }}
              disabled={!!a.disabled}
              onClick={() => { setOpen(false); btn.current?.focus(); a.onClick(); }}>
              {a.label}{a.disabled ? ` — ${a.disabled}` : ""}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}

export default function SzkicPlanu({ planKind, planId, onZamknij, onOpublikowano }: {
  planKind: PlanKind;
  planId: string;
  onZamknij: () => void;
  onOpublikowano: (wynik: WynikPublikacji) => void;
}) {
  const [szkic, setSzkic] = useState<Szkic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zapis, setZapis] = useState<Zapis>("zapisano");
  const [komunikat, setKomunikat] = useState<string | null>(null);
  const [cofnij, setCofnij] = useState<{ label: string; op: SzkicOperacja } | null>(null);
  const [potwierdz, setPotwierdz] = useState<{ id: string; label: string; count: number } | null>(null);
  const [roznice, setRoznice] = useState<Roznice | null>(null);
  const [notatka, setNotatka] = useState("");
  const [publikacja, setPublikacja] = useState<"idle" | "busy">("idle");
  const kluczRef = useRef<string>("");
  // Kolejka operacji: edycje w polach są łączone i wysyłane po chwili ciszy
  // z BIEŻĄCĄ rewizją; odpowiedź serwera ustawia nową rewizję.
  const kolejka = useRef<SzkicOperacja[]>([]);
  const wysylka = useRef<Promise<void> | null>(null);
  const szkicRef = useRef<Szkic | null>(null);
  szkicRef.current = szkic;

  const zaladuj = useCallback(() => {
    setError(null);
    api.post<Szkic>(`/api/szkice/plan/${planKind}/${planId}`)
      .then((s) => { setSzkic(s); setZapis("zapisano"); })
      .catch((e) => setError((e as Error).message));
  }, [planKind, planId]);
  useEffect(zaladuj, [zaladuj]);

  async function wyslij(ops: SzkicOperacja[]): Promise<Szkic | null> {
    const s = szkicRef.current;
    if (!s) return null;
    setZapis("zapisywanie");
    try {
      const nowy = await api.patch<Szkic>(`/api/szkice/${s.id}`, { revision: s.revision, operations: ops });
      setSzkic(nowy);
      szkicRef.current = nowy;
      setZapis("zapisano");
      setRoznice(null);
      return nowy;
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "REVISION_CONFLICT") {
        setZapis("konflikt");
        setKomunikat("Szkic zmienił się na innym urządzeniu. Odśwież, żeby zobaczyć aktualną wersję — Twoja ostatnia zmiana nie została zapisana.");
      } else {
        setZapis("blad");
        setKomunikat(`Nie udało się zapisać: ${err.message}`);
      }
      return null;
    }
  }

  /** Wyślij zebrane operacje jedna po drugiej (nigdy równolegle — rewizja). */
  const oproznij = useCallback(async () => {
    if (wysylka.current) return;
    wysylka.current = (async () => {
      while (kolejka.current.length) {
        const paczka = kolejka.current.splice(0, kolejka.current.length);
        const ok = await wyslij(paczka);
        if (!ok) { kolejka.current = []; break; }
      }
    })();
    await wysylka.current;
    wysylka.current = null;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const oproznijPozniej = useDebounced(() => { void oproznij(); }, 600);

  /** Optymistyczna edycja pola + kolejka zapisu. */
  function ustaw(id: string | null, fields: Record<string, unknown>) {
    setSzkic((s) => s ? { ...s, content: zastosujLokalnie(s.content, id, fields) } : s);
    // Kolejne zmiany tego samego elementu sklejamy w jedną operację.
    const ostatnia = kolejka.current[kolejka.current.length - 1];
    if (ostatnia && ostatnia.op === "set" && (ostatnia.id ?? null) === id) {
      ostatnia.fields = { ...ostatnia.fields, ...fields };
    } else {
      kolejka.current.push({ op: "set", ...(id ? { id } : {}), fields });
    }
    setZapis("zapisywanie");
    oproznijPozniej();
  }

  async function operacja(op: SzkicOperacja) {
    await oproznij();
    kolejka.current.push(op);
    await oproznij();
  }

  async function usun(id: string, label: string, collection: string, count: number, potwierdzone = false) {
    const s = szkicRef.current;
    if (!s) return;
    if (count > 1 && !potwierdzone) { setPotwierdz({ id, label, count }); return; }
    setPotwierdz(null);
    await oproznij();
    try {
      setZapis("zapisywanie");
      const r = await api.del<Szkic & { removed: { collection: string; index: number; parent_id: string | null; item: Record<string, unknown> } }>(
        `/api/szkice/${s.id}/elementy/${id}?revision=${szkicRef.current?.revision ?? s.revision}`);
      setSzkic(r); szkicRef.current = r; setZapis("zapisano"); setRoznice(null);
      setCofnij({ label, op: { op: "add", collection: r.removed.collection as SzkicOperacja["collection"], parent_id: r.removed.parent_id, item: r.removed.item, index: r.removed.index } });
      setKomunikat(`Usunięto: ${label}${count > 1 ? ` (${count} elementów)` : ""}. Klient zobaczy to dopiero po publikacji.`);
    } catch (e) {
      const err = e as ApiError;
      setZapis(err.code === "REVISION_CONFLICT" ? "konflikt" : "blad");
      setKomunikat(err.message);
    }
    void collection;
  }

  async function sprawdzZmiany() {
    await oproznij();
    const s = szkicRef.current;
    if (!s) return;
    try { setRoznice(await api.get<Roznice>(`/api/szkice/${s.id}/roznice`)); }
    catch (e) { setKomunikat((e as Error).message); }
  }

  async function opublikuj() {
    await oproznij();
    const s = szkicRef.current;
    if (!s) return;
    if (!kluczRef.current) kluczRef.current = `pub-${s.id}-${Date.now().toString(36)}`;
    setPublikacja("busy");
    try {
      const w = await api.post<WynikPublikacji>(`/api/szkice/${s.id}/publikuj`, {
        revision: s.revision, base_version_no: s.base_version_no, note: notatka || null,
        idempotency_key: kluczRef.current,
      });
      if (!w.published) {
        setKomunikat("Brak różnic względem aktywnej wersji — nic nie opublikowano i klient nie dostał powiadomienia.");
        setPublikacja("idle");
        return;
      }
      onOpublikowano(w);
    } catch (e) {
      const err = e as ApiError;
      setPublikacja("idle");
      kluczRef.current = "";
      if (err.code === "BASE_VERSION_CONFLICT" || err.code === "REVISION_CONFLICT") setZapis("konflikt");
      setKomunikat(err.message);
      void sprawdzZmiany();
    }
  }

  async function odrzuc() {
    const s = szkicRef.current;
    if (!s) return;
    if (!window.confirm("Odrzucić szkic? Niezapisane u klienta zmiany przepadną; aktywna wersja planu zostaje.")) return;
    try {
      await api.del(`/api/szkice/${s.id}?revision=${s.revision}`);
      onZamknij();
    } catch (e) { setKomunikat((e as Error).message); }
  }

  if (error) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (!szkic) return <Spinner />;
  const stan = { zapisano: "Zapisano ✓", zapisywanie: "Zapisywanie…", blad: "Błąd zapisu", konflikt: "Konflikt — odśwież" }[zapis];

  return (
    <div className="card card--accent" aria-label="Edytor szkicu planu">
      <div className="row row--between" style={{ alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <div>
          <span className="badge badge--warn">Szkic — klient jeszcze nie widzi zmian</span>
          <span className="dim" style={{ marginLeft: 8, fontSize: "0.85rem" }} role="status" aria-live="polite">
            {stan} · zmian: {szkic.changes} · wersja bazowa v{szkic.base_version_no}
          </span>
        </div>
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          {zapis === "konflikt" && <button type="button" className="btn btn--small" onClick={zaladuj}>Odśwież szkic</button>}
          <button type="button" className="btn btn--ghost btn--small" onClick={sprawdzZmiany} aria-expanded={!!roznice}>Sprawdź zmiany</button>
          <button type="button" className="btn btn--ghost btn--small" onClick={odrzuc}>Odrzuć szkic</button>
          <button type="button" className="btn btn--ghost btn--small" onClick={onZamknij}>Zamknij (szkic zostaje)</button>
        </div>
      </div>
      {komunikat && (
        <p className="alert alert--info" role="status">
          {komunikat}
          {cofnij && (
            <button type="button" className="btn btn--small" style={{ marginLeft: 8 }}
              onClick={async () => { const c = cofnij; setCofnij(null); setKomunikat(null); await operacja(c.op); }}>
              Cofnij
            </button>
          )}
          <button type="button" className="btn btn--ghost btn--small" style={{ marginLeft: 8 }} aria-label="Zamknij komunikat"
            onClick={() => { setKomunikat(null); setCofnij(null); }}>×</button>
        </p>
      )}
      {potwierdz && (
        <div role="alertdialog" aria-labelledby="szkic-potwierdz" className="alert alert--warn">
          <b id="szkic-potwierdz">Usunąć „{potwierdz.label}”?</b> Znikną {potwierdz.count} elementy (razem z zawartością). Klient zobaczy to dopiero po publikacji.
          <div className="row" style={{ marginTop: 6, gap: 6 }}>
            <button type="button" className="btn btn--danger btn--small" onClick={() => usun(potwierdz.id, potwierdz.label, "", potwierdz.count, true)}>Usuń</button>
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setPotwierdz(null)}>Anuluj</button>
          </div>
        </div>
      )}

      <label htmlFor="szkic-title">Nazwa planu</label>
      <input id="szkic-title" value={szkic.content.title ?? ""} onChange={(e) => ustaw(null, { title: e.target.value })} />

      {planKind === "training"
        ? <EdytorTreningu tresc={szkic.content as SzkicTrening} ustaw={ustaw} operacja={operacja} usun={usun} />
        : <EdytorDiety tresc={szkic.content as SzkicDieta} ustaw={ustaw} operacja={operacja} usun={usun} />}

      {roznice && (
        <div className="card" style={{ marginTop: 10 }} aria-label="Sprawdź zmiany">
          <h3 style={{ marginTop: 0 }}>Sprawdź zmiany</h3>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            {roznice.plan_title} · {roznice.client_id ? "plan klienta" : "szablon (bez powiadomienia)"} · wersja bazowa v{roznice.base_version_no} → nowa v{(roznice.current_version_no ?? 0) + 1} · obowiązuje: {roznice.effective}
          </p>
          {roznice.stale_base && <p className="alert alert--warn">Plan ma już nowszą wersję niż ta, na której powstał szkic — publikacja zostanie odrzucona; odrzuć szkic i zacznij od aktualnej wersji.</p>}
          <p><b>{roznice.summary}</b></p>
          <ListaRoznic r={roznice} />
          {roznice.total > 0 && (
            <>
              <label htmlFor="szkic-notatka">Co i dlaczego zmieniłem (opcjonalnie, klient to zobaczy)</label>
              <textarea id="szkic-notatka" rows={2} value={notatka} onChange={(e) => setNotatka(e.target.value)} />
              <div className="row" style={{ marginTop: 8 }}>
                <button type="button" className="btn" disabled={publikacja === "busy" || !!roznice.stale_base || zapis === "konflikt"} onClick={opublikuj}>
                  {publikacja === "busy" ? "Publikowanie…" : "Opublikuj zmiany i powiadom"}
                </button>
              </div>
            </>
          )}
          {roznice.total === 0 && <p className="dim">Brak różnic — nie ma czego publikować.</p>}
        </div>
      )}
    </div>
  );
}

function zastosujLokalnie<T extends SzkicTrening | SzkicDieta>(tresc: T, id: string | null, fields: Record<string, unknown>): T {
  if (id === null) return { ...tresc, ...fields };
  const t = tresc as unknown as Record<string, unknown>;
  const out: Record<string, unknown> = { ...t };
  for (const kol of ["days", "sections", "meals", "supplements"] as const) {
    const lista = t[kol] as Record<string, unknown>[] | undefined;
    if (!lista) continue;
    out[kol] = lista.map((el) => {
      if (el.id === id) return { ...el, ...fields };
      const ex = el.exercises as Record<string, unknown>[] | undefined;
      if (ex) return { ...el, exercises: ex.map((x) => (x.id === id ? { ...x, ...fields } : x)) };
      return el;
    });
  }
  return out as unknown as T;
}

export function ListaRoznic({ r }: { r: Roznice }) {
  const pole = (v: unknown) => (v === null || v === undefined || v === "" ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));
  return (
    <div style={{ fontSize: "0.9rem" }}>
      {r.root.map((x) => <div key={x.field}>✎ {x.field}: {pole(x.before)} → <b>{pole(x.after)}</b></div>)}
      {r.added.map((x) => <div key={x.id} style={{ color: "var(--ok)" }}>+ {x.label}{x.children ? ` (z ${x.children} elementami)` : ""}</div>)}
      {r.changed.map((x) => (
        <div key={x.id}>✎ {x.label_before !== x.label ? `${x.label_before} → ${x.label}` : x.label}:{" "}
          {x.fields.map((f) => `${f.field}: ${pole(f.before)} → ${pole(f.after)}`).join("; ")}</div>
      ))}
      {r.removed.map((x) => <div key={x.id} style={{ color: "var(--danger)" }}>− {x.label}{x.children ? ` (z ${x.children} elementami)` : ""}</div>)}
      {r.moved.map((x, i) => <div key={x.id + i}>⇅ {x.label}{x.from_parent !== undefined ? " (przeniesione do innego dnia)" : ` (pozycja ${(x.from ?? 0) + 1} → ${(x.to ?? 0) + 1})`}</div>)}
    </div>
  );
}

type Ustaw = (id: string | null, fields: Record<string, unknown>) => void;
type Operacja = (op: SzkicOperacja) => Promise<void>;
type Usun = (id: string, label: string, collection: string, count: number) => Promise<void>;

function EdytorTreningu({ tresc, ustaw, operacja, usun }: { tresc: SzkicTrening; ustaw: Ustaw; operacja: Operacja; usun: Usun }) {
  return (
    <>
      {tresc.days.map((day, di) => (
        <div key={day.id} className="card" style={{ marginTop: 10 }}>
          <div className="row row--between" style={{ alignItems: "flex-start", gap: 8 }}>
            <div className="field-row" style={{ flex: 1 }}>
              <div><label htmlFor={`sz-day-${day.id}`}>Dzień {di + 1}</label>
                <input id={`sz-day-${day.id}`} value={day.name} onChange={(e) => ustaw(day.id, { name: e.target.value })} placeholder="np. Trening A — góra" /></div>
              <div><label htmlFor={`sz-wd-${day.id}`}>Dzień tygodnia</label>
                <select id={`sz-wd-${day.id}`} value={day.weekday ?? ""} onChange={(e) => ustaw(day.id, { weekday: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">— dowolny —</option>
                  {WEEKDAYS.map((w, i) => <option key={i} value={i + 1}>{w}</option>)}
                </select></div>
            </div>
            <MenuDzialan etykieta={day.name || `dzień ${di + 1}`} akcje={[
              { label: "Duplikuj dzień", onClick: () => operacja({ op: "duplicate", id: day.id }) },
              { label: "Przenieś wyżej", onClick: () => operacja({ op: "move", id: day.id, index: di - 1 }), disabled: di === 0 ? "to już pierwszy dzień" : undefined },
              { label: "Przenieś niżej", onClick: () => operacja({ op: "move", id: day.id, index: di + 1 }), disabled: di === tresc.days.length - 1 ? "to już ostatni dzień" : undefined },
              { label: "Usuń dzień", danger: true, onClick: () => usun(day.id, day.name || `dzień ${di + 1}`, "days", 1 + day.exercises.length) },
            ]} />
          </div>
          {day.exercises.map((ex, ei) => rodzajPozycji(ex as unknown as Exercise) !== "strength" ? (
            // Rozgrzewka / rozciąganie / cardio (0.73.0): w szkicu tylko odczyt i usunięcie —
            // treść pochodzi z katalogu bloków albo z panelu suwaków w edytorze nowej wersji.
            <div key={ex.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 8, marginTop: 8 }}>
              <div className="row row--between" style={{ gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <b>{ex.name}</b> <span className="badge">{KIND_BADGE[rodzajPozycji(ex as unknown as Exercise)]}</span>
                  <div className="meta">{opisPozycji(ex as unknown as Exercise)}</div>
                </div>
                <MenuDzialan etykieta={ex.name || `pozycja ${ei + 1}`} akcje={[
                  { label: "Wyżej", onClick: () => operacja({ op: "move", id: ex.id, index: ei - 1 }), disabled: ei === 0 ? "pierwsze w dniu" : undefined },
                  { label: "Niżej", onClick: () => operacja({ op: "move", id: ex.id, index: ei + 1 }), disabled: ei === day.exercises.length - 1 ? "ostatnie w dniu" : undefined },
                  { label: "Usuń pozycję", danger: true, onClick: () => usun(ex.id, ex.name || `pozycja ${ei + 1}`, "exercises", 1) },
                ]} />
              </div>
            </div>
          ) : (
            <div key={ex.id} style={{ borderTop: "1px solid var(--border)", paddingTop: 8, marginTop: 8 }}>
              <div className="row row--between" style={{ alignItems: "flex-end", gap: 8 }}>
                <div style={{ flex: 1 }}>
                  <label htmlFor={`sz-ex-${ex.id}`}>Ćwiczenie {ei + 1}{ex.exercise_id && <span className="badge" style={{ marginLeft: 8 }}>z bazy</span>}</label>
                  <input id={`sz-ex-${ex.id}`} value={ex.name} placeholder="nazwa ćwiczenia"
                    onChange={(e) => ustaw(ex.id, { name: e.target.value, exercise_id: e.target.value === ex.name ? ex.exercise_id ?? null : null })} />
                </div>
                <MenuDzialan etykieta={ex.name || `ćwiczenie ${ei + 1}`} akcje={[
                  { label: "Duplikuj", onClick: () => operacja({ op: "duplicate", id: ex.id }) },
                  { label: "Wyżej", onClick: () => operacja({ op: "move", id: ex.id, index: ei - 1 }), disabled: ei === 0 ? "pierwsze w dniu" : undefined },
                  { label: "Niżej", onClick: () => operacja({ op: "move", id: ex.id, index: ei + 1 }), disabled: ei === day.exercises.length - 1 ? "ostatnie w dniu" : undefined },
                  ...tresc.days.filter((d) => d.id !== day.id).map((d) => ({ label: `Przenieś do: ${d.name || "(bez nazwy)"}`, onClick: () => operacja({ op: "move", id: ex.id, index: 999, parent_id: d.id }) })),
                  { label: "Usuń ćwiczenie", danger: true, onClick: () => usun(ex.id, ex.name || `ćwiczenie ${ei + 1}`, "exercises", 1) },
                ]} />
              </div>
              <div className="field-row-3" style={{ marginTop: 6 }}>
                {POLA_CWICZENIA.map(([f, label, ph]) => (
                  <input key={f} value={(ex[f] as string) ?? ""} placeholder={ph} aria-label={`Ćwiczenie ${ei + 1} — ${label}`}
                    onChange={(e) => ustaw(ex.id, { [f]: e.target.value })} />
                ))}
              </div>
              <input style={{ marginTop: 6 }} value={ex.comment ?? ""} placeholder="notatka dla klienta" aria-label={`Ćwiczenie ${ei + 1} — notatka`}
                onChange={(e) => ustaw(ex.id, { comment: e.target.value })} />
            </div>
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            <button type="button" className="btn btn--ghost btn--small"
              onClick={() => operacja({ op: "add", collection: "exercises", parent_id: day.id, item: { name: "Nowe ćwiczenie" } })}>
              + ćwiczenie
            </button>
          </div>
        </div>
      ))}
      <div className="row" style={{ marginTop: 10 }}>
        <button type="button" className="btn btn--ghost btn--small"
          onClick={() => operacja({ op: "add", collection: "days", item: { name: `Dzień ${tresc.days.length + 1}`, exercises: [] } })}>
          + dzień treningowy
        </button>
      </div>
    </>
  );
}

function EdytorDiety({ tresc, ustaw, operacja, usun }: { tresc: SzkicDieta; ustaw: Ustaw; operacja: Operacja; usun: Usun }) {
  return (
    <>
      <div className="field-row" style={{ marginTop: 8 }}>
        {(["kcal", "protein_g", "fat_g", "carbs_g"] as const).map((k) => (
          <div key={k}><label htmlFor={`sz-${k}`}>{{ kcal: "kcal / dzień", protein_g: "białko (g)", fat_g: "tłuszcze (g)", carbs_g: "węglowodany (g)" }[k]}</label>
            <input id={`sz-${k}`} inputMode="numeric" value={tresc[k] ?? ""} onChange={(e) => ustaw(null, { [k]: e.target.value === "" ? null : Number(e.target.value) })} /></div>
        ))}
      </div>
      <h3>Zalecenia</h3>
      {tresc.sections.map((s, i) => (
        <div key={s.id} className="card" style={{ marginTop: 6 }}>
          <div className="row row--between" style={{ gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}><label htmlFor={`sz-sec-${s.id}`}>Sekcja {i + 1}</label>
              <input id={`sz-sec-${s.id}`} value={s.title} onChange={(e) => ustaw(s.id, { title: e.target.value })} /></div>
            <MenuDzialan etykieta={s.title || `sekcja ${i + 1}`} akcje={[
              { label: "Wyżej", onClick: () => operacja({ op: "move", id: s.id, index: i - 1 }), disabled: i === 0 ? "pierwsza" : undefined },
              { label: "Niżej", onClick: () => operacja({ op: "move", id: s.id, index: i + 1 }), disabled: i === tresc.sections.length - 1 ? "ostatnia" : undefined },
              { label: "Usuń sekcję", danger: true, onClick: () => usun(s.id, s.title || `sekcja ${i + 1}`, "sections", 1) },
            ]} />
          </div>
          <textarea rows={3} value={s.body} aria-label={`Treść sekcji ${i + 1}`} onChange={(e) => ustaw(s.id, { body: e.target.value })} style={{ marginTop: 6 }} />
        </div>
      ))}
      <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
        onClick={() => operacja({ op: "add", collection: "sections", item: { title: "Nowa sekcja", body: "" } })}>+ sekcja</button>
      <h3>Posiłki</h3>
      {tresc.meals.map((m, i) => (
        <div key={m.id} className="card" style={{ marginTop: 6 }}>
          <div className="row row--between" style={{ gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}><label htmlFor={`sz-meal-${m.id}`}>Posiłek {i + 1}
              {m.recipe_id && <span className="badge" style={{ marginLeft: 8 }}>{m.edited_manually ? "z kreatora dań — zmieniony ręcznie" : "z kreatora dań"}</span>}</label>
              <input id={`sz-meal-${m.id}`} value={m.name} onChange={(e) => ustaw(m.id, { name: e.target.value })} /></div>
            <MenuDzialan etykieta={m.name || `posiłek ${i + 1}`} akcje={[
              { label: "Duplikuj", onClick: () => operacja({ op: "duplicate", id: m.id }) },
              { label: "Wyżej", onClick: () => operacja({ op: "move", id: m.id, index: i - 1 }), disabled: i === 0 ? "pierwszy" : undefined },
              { label: "Niżej", onClick: () => operacja({ op: "move", id: m.id, index: i + 1 }), disabled: i === tresc.meals.length - 1 ? "ostatni" : undefined },
              { label: "Usuń posiłek", danger: true, onClick: () => usun(m.id, m.name || `posiłek ${i + 1}`, "meals", 1) },
            ]} />
          </div>
          <textarea rows={2} value={m.description ?? ""} placeholder="składniki, gramatury, sposób przygotowania" aria-label={`Opis posiłku ${i + 1}`}
            onChange={(e) => ustaw(m.id, { description: e.target.value })} style={{ marginTop: 6 }} />
          <input value={m.swaps ?? ""} placeholder="zamienniki" aria-label={`Zamienniki posiłku ${i + 1}`} onChange={(e) => ustaw(m.id, { swaps: e.target.value })} style={{ marginTop: 6 }} />
          {m.recipe_id && m.edited_manually && (
            <p className="dim" style={{ fontSize: "0.8rem", margin: "4px 0 0" }}>
              Ręczna zmiana: wartości odżywcze i wcześniejsze sprawdzenie receptury nie obowiązują dla tej wersji posiłku.
            </p>
          )}
        </div>
      ))}
      <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
        onClick={() => operacja({ op: "add", collection: "meals", item: { name: "Nowy posiłek", description: "" } })}>+ posiłek</button>
      <h3>Suplementacja</h3>
      {tresc.supplements.map((s, i) => (
        <div key={s.id} className="card" style={{ marginTop: 6 }}>
          <div className="row row--between" style={{ gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}><label htmlFor={`sz-sup-${s.id}`}>Suplement {i + 1}</label>
              <input id={`sz-sup-${s.id}`} value={s.name} onChange={(e) => ustaw(s.id, { name: e.target.value })} /></div>
            <MenuDzialan etykieta={s.name || `suplement ${i + 1}`} akcje={[
              { label: "Usuń suplement", danger: true, onClick: () => usun(s.id, s.name || `suplement ${i + 1}`, "supplements", 1) },
            ]} />
          </div>
          <div className="field-row-3" style={{ marginTop: 6 }}>
            {(["dose", "timing", "purpose"] as const).map((k) => (
              <input key={k} value={(s[k] as string) ?? ""} placeholder={{ dose: "dawka", timing: "pora", purpose: "cel" }[k]}
                aria-label={`Suplement ${i + 1} — ${{ dose: "dawka", timing: "pora", purpose: "cel" }[k]}`} onChange={(e) => ustaw(s.id, { [k]: e.target.value })} />
            ))}
          </div>
          <input style={{ marginTop: 6 }} value={s.source ?? ""} placeholder="podstawa zalecenia (kto, na jakiej podstawie)" aria-label={`Suplement ${i + 1} — podstawa`}
            onChange={(e) => ustaw(s.id, { source: e.target.value })} />
        </div>
      ))}
      <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 6 }}
        onClick={() => operacja({ op: "add", collection: "supplements", item: { name: "", dose: "", timing: "", purpose: "", source: "" } })}>+ suplement</button>
    </>
  );
}

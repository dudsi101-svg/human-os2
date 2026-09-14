import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDate } from "../../dates";
import {
  AuthAttachment, ErrorBox, Icon, Spinner, TabPanel, Tabs, TopBar,
} from "../../components";
import {
  WIEDZA_CZESCI,
  WIEDZA_TYP_ELEMENTU,
  WiedzaHistoriaWpis,
  WiedzaKarta,
  WiedzaKartaPelna,
  WiedzaOdTrenera,
  WiedzaStart,
  WiedzaWynikSzukania,
} from "../../types";
import { Dlaczego } from "../../wiedza/Dlaczego";
import { bezpiecznyPowrot } from "../../nazwy";
import KnowledgeLegacy, { ExercisesTab, KartaCwiczeniaTrenera, ProductsTab } from "./KnowledgeLegacy";

/**
 * Wiedza (0.56.0, P0 pakietu właściciela): „Zrozum swój trening i odżywianie”.
 *
 * Pięć części (Dla Ciebie, Trening, Odżywianie, Postępy i regeneracja,
 * Podstawy i źródła), wyszukiwanie po opublikowanych tekstach, zapisane,
 * karty wiedzy i atlas, historia rzeczywistych zmian planu. Wyjaśnienia
 * indywidualne pochodzą WYŁĄCZNIE z zapisanego śladu decyzji (panel
 * „Dlaczego?”); brak śladu to uczciwy komunikat, nie wymyślony powód.
 *
 * Mapa migracji: materiały trenera (dotychczasowa zakładka) pokazują się
 * jako „Od trenera” we właściwej części; baza ćwiczeń trenera = część
 * Atlasu; katalog produktów = w Odżywianiu. Przy wyłączonej fladze
 * serwer odpowiada `wlaczone: false` i renderuje się poprzednia zakładka.
 */

type Czesc = "dla-ciebie" | "training" | "nutrition" | "progress" | "basics";
const CZESCI = WIEDZA_CZESCI as [Czesc, string][];

export default function Knowledge() {
  const [start, setStart] = useState<WiedzaStart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    api.get<WiedzaStart>("/api/wiedza/start").then(setStart).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []);

  if (error) return <div className="page"><TopBar title="Wiedza" /><ErrorBox error={error} onRetry={load} /></div>;
  if (!start) return <div className="page"><TopBar title="Wiedza" /><Spinner /></div>;
  if (!start.wlaczone) return <KnowledgeLegacy />;
  return <Wiedza start={start} reload={load} />;
}

function Wiedza({ start, reload }: { start: WiedzaStart; reload: () => void }) {
  const [params, setParams] = useSearchParams();
  const czesc = (CZESCI.some(([k]) => k === params.get("czesc")) ? params.get("czesc") : "dla-ciebie") as Czesc;
  const karta = params.get("karta");
  const widok = params.get("widok"); // zapisane | historia
  // Karta ćwiczenia z bazy trenera (0.75.0): cel linku z planu; ma pierwszeństwo,
  // bo przychodzi z zewnątrz Wiedzy (z Planu / Dzisiaj).
  const cwiczenie = params.get("cwiczenie");
  const scrollRef = useRef(0);

  function ustaw(zmiany: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(zmiany)) {
      if (v === null) next.delete(k); else next.set(k, v);
    }
    setParams(next, { replace: false });
  }
  function otworzKarte(id: string) {
    scrollRef.current = window.scrollY;
    ustaw({ karta: id });
  }
  function wroc() {
    ustaw({ karta: null });
    requestAnimationFrame(() => window.scrollTo({ top: scrollRef.current }));
  }

  return (
    <div className="page">
      <TopBar title="Wiedza" />
      {start.szkice_widoczne && (
        <p className="wiedza-demo" role="note">
          Tryb demonstracyjny: widzisz treści robocze bez przeglądu eksperckiego.
          Na produkcji pojawiają się wyłącznie karty opublikowane po recenzji.
        </p>
      )}
      {cwiczenie ? (
        <KartaCwiczeniaTrenera id={cwiczenie} url={`/api/me/exercises/${encodeURIComponent(cwiczenie)}`}
          powrot={bezpiecznyPowrot(params.get("powrot"))}
          onZamknij={() => ustaw({ cwiczenie: null, powrot: null, czesc: "training" })} />
      ) : karta ? (
        <KartaWidok id={karta} start={start} onBack={wroc} onOpen={otworzKarte} />
      ) : (
        <>
          <Szukajka onOpen={otworzKarte} />
          <div className="row" style={{ marginBottom: 12 }}>
            <button className="btn btn--ghost btn--small" aria-pressed={widok === "zapisane"}
              onClick={() => ustaw({ widok: widok === "zapisane" ? null : "zapisane" })}>
              <Icon name="star" size={16} /> Zapisane{start.zakladki && start.zakladki.length > 0 ? ` (${start.zakladki.length})` : ""}
            </button>
            {start.plan && (
              <button className="btn btn--ghost btn--small" aria-pressed={widok === "historia"}
                onClick={() => ustaw({ widok: widok === "historia" ? null : "historia" })}>
                <Icon name="clipboard" size={16} /> Historia zmian
              </button>
            )}
          </div>
          {widok === "zapisane" && <Zapisane onOpen={otworzKarte} />}
          {widok === "historia" && start.plan && <Historia planId={start.plan.plan_id} />}
          {!widok && (
            <>
              <Tabs tabs={CZESCI} value={czesc} onChange={(c) => ustaw({ czesc: c })} label="Części Wiedzy" />
              <TabPanel id={czesc}>
                {czesc === "dla-ciebie"
                  ? <DlaCiebie start={start} reload={reload} onOpen={otworzKarte} onCzesc={(c) => ustaw({ czesc: c })} />
                  : <Biblioteka kategoria={czesc} start={start} onOpen={otworzKarte} />}
              </TabPanel>
            </>
          )}
        </>
      )}
    </div>
  );
}

// --- W7: wyszukiwanie ---------------------------------------------------------

function Szukajka({ onOpen }: { onOpen: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [wyniki, setWyniki] = useState<WiedzaWynikSzukania[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function szukaj(e?: FormEvent) {
    e?.preventDefault();
    const zapytanie = q.trim();
    if (!zapytanie) { setWyniki(null); return; }
    setBusy(true); setError(null);
    try {
      const r = await api.post<{ items: WiedzaWynikSzukania[] }>("/api/wiedza/szukaj", { q: zapytanie.slice(0, 200) });
      setWyniki(r.items);
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }

  return (
    <form className="card" onSubmit={szukaj} role="search" style={{ marginBottom: 12 }}>
      <label htmlFor="wiedza-q" style={{ marginTop: 0 }}>Czego chcesz dowiedzieć się o swoim planie?</label>
      <div className="wiedza-szukaj">
        <input id="wiedza-q" type="search" value={q} maxLength={200} autoComplete="off"
          placeholder="np. zapas, RIR, kalorie" onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn--small" type="submit" disabled={busy}>Szukaj</button>
      </div>
      <ErrorBox error={error} onRetry={() => void szukaj()} />
      {wyniki && (
        <div className="wiedza-lista" aria-live="polite">
          {wyniki.length === 0 && (
            <p className="dim" style={{ margin: 0 }}>
              Nie znaleźliśmy materiału. Spróbuj krótszego hasła lub wybierz temat.
            </p>
          )}
          {wyniki.map((w) => (
            <button type="button" className="card" key={w.id} onClick={() => onOpen(w.id)}>
              <b>{w.title}</b>{w.szkic && <span className="badge badge--warn" style={{ marginLeft: 8 }}>szkic</span>}
              <div className="meta">{w.category_label} · {w.fragment}</div>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

// --- W1: Dla Ciebie -----------------------------------------------------------

function DlaCiebie({ start, reload, onOpen, onCzesc }: {
  start: WiedzaStart; reload: () => void; onOpen: (id: string) => void; onCzesc: (c: Czesc) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function personalizacja(on: boolean) {
    setBusy(true);
    try { await api.put("/api/wiedza/ustawienia", { personalizacja: on }); reload(); } finally { setBusy(false); }
  }
  const plan = start.plan;
  const feed = start.dla_ciebie ?? [];
  const zmiany = start.ostatnie_zmiany ?? [];
  return (
    <>
      <h2 style={{ margin: "0 0 10px" }}>Zrozum swój trening i odżywianie</h2>
      <div className="card">
        <h2><Icon name="plan" size={18} /> Twój plan w prostych słowach</h2>
        {plan ? (
          <>
            <p style={{ margin: "0 0 6px" }}>
              <b>{plan.title}</b> — wersja {plan.version_no} z {plDate(plan.version_created_at)},
              {" "}{plan.days} {plan.days === 1 ? "dzień" : plan.days < 5 ? "dni" : "dni"} treningowe w planie.
            </p>
            <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>Powód ostatniej zmiany: {plan.reason}</p>
            <div className="row">
              <Dlaczego etykieta="Dlaczego ta wersja?" naglowek={`Wersja ${plan.version_no} planu`}
                cel={{ plan_id: plan.plan_id, plan_revision: plan.version_no, target_type: "plan_change", target_id: "plan" }} />
              <Dlaczego etykieta="Dlaczego tyle dni?" naglowek="Liczba treningów w tygodniu"
                cel={{ plan_id: plan.plan_id, plan_revision: plan.version_no, target_type: "training_frequency", target_id: "plan" }} />
              <Link className="btn btn--ghost btn--small" to="/plan">Otwórz plan</Link>
            </div>
          </>
        ) : (
          <>
            <p style={{ margin: "0 0 8px" }}>
              Poznaj podstawy treningu i odżywiania. Gdy dodasz plan, znajdziesz tu także jego wyjaśnienia.
            </p>
            <div className="row">
              <button className="btn btn--small" onClick={() => onCzesc("basics")}>Przeglądaj podstawy</button>
            </div>
          </>
        )}
      </div>

      <div className="card">
        <h2><Icon name="sparkle" size={18} /> Warto poznać teraz</h2>
        {feed.length === 0 && <p className="dim" style={{ margin: 0 }}>Brak rekomendacji — zajrzyj do części tematycznych.</p>}
        <div className="wiedza-lista">
          {feed.map((k) => (
            <button type="button" className="card" key={k.id} onClick={() => onOpen(k.id)}>
              <b>{k.title}</b>{k.szkic && <span className="badge badge--warn" style={{ marginLeft: 8 }}>szkic</span>}
              <div className="meta">{k.powod} · {k.estimated_read_minutes ?? 1} min czytania</div>
            </button>
          ))}
        </div>
        <label className="row" style={{ alignItems: "center", marginTop: 8 }}>
          <input type="checkbox" checked={start.personalizacja !== false} disabled={busy}
            onChange={(e) => void personalizacja(e.target.checked)} />
          <span>Dopasowuj rekomendacje do mojego planu (po wyłączeniu: podstawy w stałej kolejności)</span>
        </label>
      </div>

      {zmiany.length > 0 && (
        <div className="card">
          <h2><Icon name="clipboard" size={18} /> Ostatnie zmiany</h2>
          {zmiany.map((z) => (
            <div className="exercise" key={`${z.plan_id}-${z.version_no}`}>
              <div>
                <b>{z.plan_title}</b> · v{z.version_no}
                <div className="meta">{z.reason}</div>
              </div>
              <div className="meta">
                {plDate(z.created_at)}
                {z.ma_slad ? <span className="badge badge--ok" style={{ marginLeft: 6 }}>z uzasadnieniem</span>
                  : <span className="badge" style={{ marginLeft: 6 }}>bez zapisanego powodu</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="dim" style={{ fontSize: "0.85rem" }}>
        <button className="btn btn--ghost btn--small" onClick={() => onCzesc("basics")}>Cała biblioteka</button>
      </p>
    </>
  );
}

// --- W2 / W5: biblioteka i atlas -----------------------------------------------

function Biblioteka({ kategoria, start, onOpen }: {
  kategoria: Czesc; start: WiedzaStart; onOpen: (id: string) => void;
}) {
  const [items, setItems] = useState<WiedzaKarta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    api.get<{ items: WiedzaKarta[]; total: number }>(`/api/wiedza/artykuly?kategoria=${kategoria}&limit=50`)
      .then((d) => setItems(d.items)).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, [kategoria]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  const ogolne = items.filter((i) => !i.exercise_id);
  const atlas = items.filter((i) => i.exercise_id);
  const odTrenera = (start.od_trenera ?? []).filter((m) => m.czesc === kategoria);
  const wPlanie = new Set(start.plan?.exercise_ids ?? []);
  return (
    <>
      {ogolne.length === 0 && atlas.length === 0 && odTrenera.length === 0 && (
        <p className="dim">Nie ma jeszcze opublikowanych materiałów w tej części. Zobacz pozostałe tematy.</p>
      )}
      {ogolne.length > 0 && (
        <div className="wiedza-lista" style={{ marginBottom: 14 }}>
          {ogolne.map((k) => <KartaNaglowek key={k.id} k={k} onOpen={onOpen} />)}
        </div>
      )}
      {odTrenera.length > 0 && (
        <div className="card">
          <h2><Icon name="user" size={18} /> Od trenera</h2>
          {odTrenera.map((m) => <OdTrenera key={m.id} m={m} />)}
        </div>
      )}
      {kategoria === "training" && (
        <>
          {atlas.length > 0 && (
            <div className="card">
              <h2><Icon name="templates" size={18} /> Atlas ćwiczeń z konfiguratora</h2>
              <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
                Karty dla ćwiczeń z katalogu konfiguratora (do przeglądu trenera). Instrukcje
                tekstowe — filmy nie zostały dołączone.
              </p>
              <div className="wiedza-lista">
                {atlas.map((k) => (
                  <button type="button" className="card" key={k.id} onClick={() => onOpen(k.id)}>
                    <b>{k.title}</b>
                    {wPlanie.has(k.exercise_id!) && <span className="badge badge--accent" style={{ marginLeft: 8 }}>w Twoim planie</span>}
                    {k.szkic && <span className="badge badge--warn" style={{ marginLeft: 8 }}>szkic</span>}
                    <div className="meta">{k.summary}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="card">
            <h2><Icon name="templates" size={18} /> Baza ćwiczeń trenera</h2>
            <ExercisesTab />
          </div>
        </>
      )}
      {kategoria === "nutrition" && (
        <div className="card">
          <h2><Icon name="diet" size={18} /> Produkty i porcje</h2>
          <ProductsTab />
        </div>
      )}
    </>
  );
}

function KartaNaglowek({ k, onOpen }: { k: WiedzaKarta; onOpen: (id: string) => void }) {
  return (
    <button type="button" className="card" onClick={() => onOpen(k.id)}>
      <b>{k.title}</b>
      {k.szkic && <span className="badge badge--warn" style={{ marginLeft: 8 }}>szkic</span>}
      {k.przeglad_po_terminie && <span className="badge" style={{ marginLeft: 8 }}>oczekuje na przegląd</span>}
      <div className="meta">{k.summary}</div>
      <div className="meta">{k.estimated_read_minutes ?? 1} min czytania · {k.evidence_kind === "product_rule" ? "reguła aplikacji" : k.evidence_kind === "research" ? "badania" : k.evidence_kind === "guideline" ? "wytyczne" : "preferencja"}</div>
    </button>
  );
}

function OdTrenera({ m }: { m: WiedzaOdTrenera }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: 8 }}>
      <button type="button" className="knowledge-card__toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <b>{m.title}</b>
        <span className="dim"><Icon name={open ? "chevron-up" : "chevron-down"} size={18} /></span>
      </button>
      {open && (
        <div style={{ marginTop: 6 }}>
          {m.body && <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{m.body}</p>}
          {m.external_url && (
            <p><a href={m.external_url} target="_blank" rel="noreferrer"><Icon name="link" size={16} /> {m.external_url}</a></p>
          )}
          {m.file_id && <div style={{ marginTop: 8, maxWidth: 320 }}><AuthAttachment fileId={m.file_id} filename={m.title} /></div>}
        </div>
      )}
    </div>
  );
}

// --- W3: karta wiedzy ---------------------------------------------------------

function KartaWidok({ id, start, onBack, onOpen }: {
  id: string; start: WiedzaStart; onBack: () => void; onOpen: (id: string) => void;
}) {
  const [karta, setKarta] = useState<WiedzaKartaPelna | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wycofana, setWycofana] = useState(false);
  const [zapisany, setZapisany] = useState(false);
  const [opinia, setOpinia] = useState<boolean | null>(null);
  const backRef = useRef<HTMLButtonElement | null>(null);

  const load = () => {
    setError(null); setWycofana(false);
    api.get<WiedzaKartaPelna>(`/api/wiedza/artykuly/${encodeURIComponent(id)}`)
      .then((k) => {
        setKarta(k); setZapisany(k.zapisany);
        void api.post(`/api/wiedza/odczyty/${encodeURIComponent(id)}`, {}).catch(() => undefined);
      })
      .catch((e) => {
        const err = e as ApiError;
        if (err.status === 410) setWycofana(true); else setError(err.message);
      });
  };
  useEffect(() => { load(); backRef.current?.focus(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function zapisz() {
    if (zapisany) { await api.del(`/api/wiedza/zakladki/${encodeURIComponent(id)}`); setZapisany(false); }
    else { await api.put(`/api/wiedza/zakladki/${encodeURIComponent(id)}`); setZapisany(true); }
  }
  async function pomoglo(useful: boolean) {
    if (!karta) return;
    setOpinia(useful);
    await api.post("/api/wiedza/opinie", { article_id: karta.id, revision: karta.revision, useful }).catch(() => undefined);
  }

  const wPlanie = !!(karta?.exercise_id && start.plan?.exercise_ids.includes(karta.exercise_id));
  return (
    <>
      <button ref={backRef} className="btn btn--ghost btn--small" onClick={onBack} style={{ marginBottom: 10 }}>
        <Icon name="chevron-up" size={16} /> Wróć
      </button>
      {wycofana && (
        <div className="card">
          <p style={{ margin: 0 }}>Materiał jest aktualizowany. Zamiennik redakcyjny znajdziesz w Zapisanych albo w bibliotece.</p>
        </div>
      )}
      {error && <ErrorBox error={error} onRetry={load} />}
      {!karta && !error && !wycofana && <Spinner />}
      {karta && (
        <article className="card">
          <h2 style={{ fontSize: "1.1rem" }}>{karta.title}</h2>
          <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
            {karta.category_label} · {karta.estimated_read_minutes ?? 1} min czytania
            {karta.szkic && <> · <span className="badge badge--warn">szkic — bez przeglądu</span></>}
            {karta.przeglad_po_terminie && <> · <span className="badge">oczekuje na przegląd</span></>}
          </p>
          <h3>W skrócie</h3>
          <p style={{ margin: "0 0 8px" }}>{karta.summary}</p>
          {karta.steps.length > 0 && (<><h3>Praktyczne kroki</h3><ol className="wiedza-karta__kroki">{karta.steps.map((s, i) => <li key={i}>{s}</li>)}</ol></>)}
          {wPlanie && start.plan && (
            <div className="alert alert--info">
              <b>W Twoim planie:</b> to ćwiczenie jest w planie „{start.plan.title}” (wersja {start.plan.version_no}).
              Dokładna dawka i powód są przy ćwiczeniu w zakładce Plan („Dlaczego?”).
              {" "}<Link to="/plan">Otwórz plan</Link>
            </div>
          )}
          <h3>Dowiedz się więcej</h3>
          <p style={{ whiteSpace: "pre-wrap", margin: "0 0 8px" }}>{karta.detail}</p>
          <h3>Ograniczenia zastosowania</h3>
          <p style={{ margin: "0 0 8px" }}>{karta.limits}</p>
          {karta.media === null && karta.exercise_id && (
            <p className="dim" style={{ fontSize: "0.85rem" }}>Instrukcja tekstowa — film nie został jeszcze dodany.</p>
          )}
          <h3>Autor i recenzja</h3>
          <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
            {karta.author_label}. {karta.review.approved
              ? `Recenzja ${plDate(karta.review.reviewed_at)}, kolejny przegląd do ${plDate(karta.review.next_review_at)}.`
              : "Bez zatwierdzenia eksperckiego — treść robocza."}
          </p>
          <h3>Źródła</h3>
          <ul className="wiedza-karta__kroki">
            {karta.sources.map((s) => (
              <li key={s.id}>
                {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.title ?? s.id}</a> : (s.title ?? s.id)}
                {s.authors && <> — {s.authors}{s.year ? ` (${s.year})` : ""}</>}
                {s.rola === "inspiracja_produktowa" && <span className="badge" style={{ marginLeft: 6 }}>inspiracja produktowa, nie dowód</span>}
                {s.rola === "merytoryczne" && s.type && <span className="badge" style={{ marginLeft: 6 }}>{s.type}</span>}
              </li>
            ))}
          </ul>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btn--ghost btn--small" onClick={() => void zapisz()} aria-pressed={zapisany}>
              <Icon name="star" size={16} /> {zapisany ? "Zapisane" : "Zapisz"}
            </button>
          </div>
          <div className="row" style={{ marginTop: 12, alignItems: "center" }}>
            <span className="dim" style={{ fontSize: "0.85rem" }}>Czy to wyjaśnienie pomogło?</span>
            {opinia === null ? (
              <>
                <button className="btn btn--ghost btn--small" onClick={() => void pomoglo(true)}>Tak</button>
                <button className="btn btn--ghost btn--small" onClick={() => void pomoglo(false)}>Nie</button>
              </>
            ) : <span role="status" className="dim" style={{ fontSize: "0.85rem" }}>Dziękujemy za odpowiedź.</span>}
          </div>
          {karta.exercise_id && (
            <p className="dim" style={{ fontSize: "0.85rem", marginTop: 10 }}>
              Zamienniki: zamianę ćwiczenia wykonuje trener w planie po walidacji — Wiedza nie zmienia planu.
              {" "}<button className="btn btn--ghost btn--small" onClick={() => onOpen("k-replacement")}>Jak działa zamiana ćwiczenia</button>
            </p>
          )}
        </article>
      )}
    </>
  );
}

// --- W7: zapisane ---------------------------------------------------------------

function Zapisane({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<(WiedzaKarta & { aktualizowany?: boolean; zamiennik?: string | null })[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    api.get<{ items: (WiedzaKarta & { aktualizowany?: boolean; zamiennik?: string | null })[] }>("/api/wiedza/zakladki")
      .then((d) => setItems(d.items)).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []);
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  return (
    <div className="card">
      <h2><Icon name="star" size={18} /> Zapisane</h2>
      {items.length === 0 && <p className="dim" style={{ margin: 0 }}>Nie masz jeszcze zapisanych materiałów.</p>}
      <div className="wiedza-lista">
        {items.map((k) => k.aktualizowany ? (
          <div className="card" key={k.id}>
            <b>{k.title}</b>
            <div className="meta">Materiał jest aktualizowany.
              {k.zamiennik && <> Zamiennik: <button className="btn btn--ghost btn--small" onClick={() => onOpen(k.zamiennik!)}>{k.zamiennik}</button></>}
            </div>
          </div>
        ) : (
          <button type="button" className="card" key={k.id} onClick={() => onOpen(k.id)}>
            <b>{k.title}</b><div className="meta">{k.category_label} · {k.summary}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

// --- W6: historia zmian ---------------------------------------------------------

function Historia({ planId }: { planId: string }) {
  const [items, setItems] = useState<WiedzaHistoriaWpis[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setError(null);
    api.get<{ items: WiedzaHistoriaWpis[] }>(`/api/wiedza/plany/training/${planId}/historia-decyzji`)
      .then((d) => setItems(d.items)).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, [planId]); // eslint-disable-line react-hooks/exhaustive-deps
  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!items) return <Spinner />;
  return (
    <div className="card">
      <h2><Icon name="clipboard" size={18} /> Historia rzeczywistych zmian</h2>
      <p className="dim" style={{ margin: "0 0 8px", fontSize: "0.85rem" }}>
        Tylko decyzje z zapisanym śladem. Wpis historyczny pokazuje stan z chwili decyzji.
      </p>
      {items.length === 0 && <p className="dim" style={{ margin: 0 }}>Ten plan nie ma jeszcze zapisanych decyzji (starsze wersje powstały przed wprowadzeniem śladu).</p>}
      {items.map((w) => (
        <div className="exercise" key={w.trace_id}>
          <div>
            <b>{WIEDZA_TYP_ELEMENTU[w.target_type] ?? w.target_type}</b> · v{w.plan_revision}
            {!w.aktualna && <span className="badge" style={{ marginLeft: 6 }}>Historia</span>}
            <div className="meta">{w.autor}{w.reason_note ? `: „${w.reason_note}”` : ""}</div>
            {w.version_reason && <div className="meta">Powód wersji: {w.version_reason}</div>}
            <div style={{ marginTop: 4 }}>
              <Dlaczego naglowek={`${WIEDZA_TYP_ELEMENTU[w.target_type] ?? w.target_type} (v${w.plan_revision})`}
                cel={{ plan_id: planId, plan_revision: w.plan_revision, target_type: w.target_type,
                  target_id: w.target_id, tryb: w.aktualna ? "current" : "history" }} />
            </div>
          </div>
          <div className="meta">{plDate(w.created_at)}</div>
        </div>
      ))}
    </div>
  );
}

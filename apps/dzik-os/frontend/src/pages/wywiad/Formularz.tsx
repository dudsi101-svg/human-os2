import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox, Spinner } from "../../components";
import {
  WywiadDefinicja, WywiadDoprecyzowanie, WywiadPostep, WywiadPytanie, WywiadTyp,
} from "../../types";
import { TYP_LABEL } from "./wspolne";

/**
 * Formularz wywiadu (0.59.0) — wspólny dla klienta („Rozpocznij /
 * Kontynuuj / Aktualizuj odpowiedzi”) i trenera („Uzupełnij wspólnie”,
 * `collection_mode=WSPOLNIE`, widoczne dla klienta).
 *
 * Widoczność i wymagalność pytań przychodzą Z SERWERA po każdym zapisie
 * (`active`, `required`) — formularz tylko rysuje. Autozapis z rewizją:
 * „Zapisano ✓” pojawia się dopiero po odpowiedzi serwera; konflikt
 * rewizji (inne urządzenie) = komunikat i przeładowanie, nigdy ciche
 * nadpisanie. Etykiety pól są stałe; błędy pokazują się przy polu.
 */

type Odp = { value: string; skipped: boolean };
type Zapis = { stan: "idle" | "saving" | "saved" | "error"; at?: string; msg?: string };

const KONTEKST_FAKTOW: Record<string, { section: string; label: string }> = {
  cel_glowny: { section: "motywacja", label: "cel" },
  cel_termin: { section: "motywacja", label: "termin" },
  urazy_deklaracja: { section: "ograniczenia", label: "urazy/dolegliwości" },
  urazy: { section: "ograniczenia", label: "opis urazów" },
  bol_biezacy: { section: "ograniczenia", label: "ból obecnie" },
  alergie: { section: "historia_odzywiania", label: "alergie" },
  alergie_status: { section: "historia_odzywiania", label: "status alergii" },
  preferencje_zywieniowe: { section: "historia_odzywiania", label: "jak dziś jesz" },
};

const DOMENA_LABEL: Record<string, string> = {
  health_data: "dane zdrowotne", nutrition_data: "żywienie i alergie",
};

export default function Formularz({ clientId, typ, tryb, doprecyzowania, maWersje, onZamknij, onPrzeslano }: {
  clientId: string;
  typ: WywiadTyp;
  tryb: "klient" | "trener";
  doprecyzowania: WywiadDoprecyzowanie[];
  maWersje: boolean;
  onZamknij: () => void;
  onPrzeslano: (r: { version_no: number; changed_facts: string[]; review_tasks: string[] }) => void;
}) {
  const base = `/api/clients/${clientId}/wywiady/${typ}`;
  const [def, setDef] = useState<WywiadDefinicja | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [odp, setOdp] = useState<Record<string, Odp>>({});
  const [bledy, setBledy] = useState<Record<string, string>>({});
  const [aktywne, setAktywne] = useState<Set<string>>(new Set());
  const [wymagane, setWymagane] = useState<Set<string>>(new Set());
  const [postep, setPostep] = useState<WywiadPostep | null>(null);
  const [zapis, setZapis] = useState<Zapis>({ stan: "idle" });
  const [konflikt, setKonflikt] = useState<string | null>(null);
  const [braki, setBraki] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const rev = useRef(1);
  const oczekujace = useRef<Record<string, Odp>>({});
  const timer = useRef<number | null>(null);
  const wToku = useRef<Promise<void> | null>(null);
  const idemKey = useRef<string>(losowyKlucz());

  const zaladuj = useCallback(() => {
    setError(null);
    api.get<WywiadDefinicja>(`${base}/definicja`).then((d) => {
      setDef(d);
      rev.current = d.draft?.revision ?? 1;
      const o: Record<string, Odp> = {};
      for (const a of d.answers) if (!a.hidden) o[a.question_id] = { value: a.value ?? "", skipped: a.skipped };
      setOdp(o);
      setAktywne(new Set(d.questions.filter((q) => q.active).map((q) => q.question_id)));
      setWymagane(new Set(d.questions.filter((q) => q.required).map((q) => q.question_id)));
      setPostep(d.progress);
      oczekujace.current = {};
      setKonflikt(null);
    }).catch((e) => setError((e as Error).message));
  }, [base]);
  useEffect(zaladuj, [zaladuj]);

  /** Wysyła zebrane zmiany; kolejne zmiany w trakcie zapisu czekają na
   * następną turę (jeden zapis w locie, rewizja zawsze aktualna). */
  const wyslij = useCallback(async (): Promise<void> => {
    if (wToku.current) { await wToku.current; }
    const paczka = oczekujace.current;
    if (Object.keys(paczka).length === 0) return;
    oczekujace.current = {};
    setZapis({ stan: "saving" });
    const p = (async () => {
      try {
        const r = await api.patch<{ revision: number; saved_at: string; errors: Record<string, string>;
          progress: WywiadPostep; active: string[]; required: string[] }>(`${base}/szkic`, {
          revision: rev.current, answers: paczka, ...(tryb === "trener" ? { collection_mode: "WSPOLNIE" } : {}),
        });
        rev.current = r.revision;
        setAktywne(new Set(r.active));
        setWymagane(new Set(r.required));
        setPostep(r.progress);
        setBledy((b) => {
          const n = { ...b };
          for (const k of Object.keys(paczka)) delete n[k];
          return { ...n, ...r.errors };
        });
        setZapis({ stan: "saved", at: r.saved_at });
      } catch (e) {
        const err = e as ApiError;
        if (err.status === 409) {
          setKonflikt("Szkic został zmieniony na innym urządzeniu (albo przez trenera). Wczytuję aktualną wersję — Twoje ostatnie niezapisane zmiany trzeba wpisać ponownie.");
          setZapis({ stan: "idle" });
          zaladuj();
          return;
        }
        oczekujace.current = { ...paczka, ...oczekujace.current };
        setZapis({ stan: "error", msg: err.message });
      }
    })();
    wToku.current = p;
    await p;
    wToku.current = null;
    if (Object.keys(oczekujace.current).length > 0) await wyslij();
  }, [base, tryb, zaladuj]);

  const zaplanuj = useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { timer.current = null; void wyslij(); }, 900);
  }, [wyslij]);

  const zmien = (qid: string, o: Odp) => {
    setOdp((s) => ({ ...s, [qid]: o }));
    oczekujace.current[qid] = o;
    setZapis((z) => (z.stan === "saving" ? z : { stan: "idle" }));
    zaplanuj();
  };

  const zapiszTeraz = async () => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    await wyslij();
  };

  async function przeslij() {
    setBusy(true); setBraki([]);
    try {
      await zapiszTeraz();
      if (zapis.stan === "error") return;
      const r = await api.post<{ version_no: number; changed_facts: string[]; review_tasks: string[] }>(
        `${base}/przeslij`, { revision: rev.current, idempotency_key: idemKey.current });
      idemKey.current = losowyKlucz();
      onPrzeslano(r);
    } catch (e) {
      const err = e as ApiError;
      if (err.status === 422) {
        // Lista braków z serwera — przewijamy do pierwszego.
        const body = err.body as { missing?: string[]; errors?: Record<string, string> } | undefined;
        const missing = body?.missing ?? [];
        setBraki(missing);
        setBledy((b) => ({ ...b, ...(body?.errors ?? {}) }));
        if (missing[0]) document.getElementById(`wyw-${missing[0]}`)?.focus();
        else setError(err.message);
      } else if (err.status === 409) {
        setKonflikt("Szkic zmienił się od ostatniego zapisu — wczytuję aktualną wersję, sprawdź odpowiedzi i prześlij ponownie.");
        zaladuj();
      } else setError(err.message);
    } finally { setBusy(false); }
  }

  const pytaniaDoprec = useMemo(() => new Set(doprecyzowania.flatMap((d) => d.question_ids)), [doprecyzowania]);
  const wpisaneNieprzezKlienta = useMemo(() => new Set(
    (def?.answers ?? []).filter((a) => a.entered_by && a.entered_by !== clientId).map((a) => a.question_id),
  ), [def, clientId]);

  if (error && !def) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (!def) return <Spinner />;

  const pytaniaSekcji = (key: string) => def.questions.filter((q) => q.section === key && aktywne.has(q.question_id));
  const ukryteSekcji = (key: string) => {
    const dom = new Set(def.questions.filter((q) => q.section === key && q.consent_domain && def.hidden_domains.includes(q.consent_domain)).map((q) => q.consent_domain!));
    return [...dom];
  };
  const faktyDla = (key: string) => Object.entries(def.facts)
    .filter(([k]) => KONTEKST_FAKTOW[k]?.section === key)
    .map(([k, f]) => ({ label: KONTEKST_FAKTOW[k].label, value: f.value, at: f.created_at }));

  return (
    <div>
      <div className="card">
        <div className="row row--between">
          <h2 style={{ margin: 0 }}>{TYP_LABEL[typ]}{tryb === "trener" ? " — uzupełniacie wspólnie" : ""}</h2>
          <StanZapisu z={zapis} onRetry={() => void zapiszTeraz()} />
        </div>
        <p className="dim" style={{ marginBottom: 0 }}>{def.opis}</p>
        {tryb === "trener" && (
          <p className="alert alert--info">Wpisy w tym trybie są oznaczone jako wprowadzone przez trenera podczas wspólnego uzupełniania — klient je widzi i może poprawić.</p>
        )}
        {def.hidden_domains.length > 0 && (
          <p className="alert alert--warn">
            Pytania o {def.hidden_domains.map((d) => DOMENA_LABEL[d] ?? d).join(" i ")} są wyłączone:
            {tryb === "klient" ? " nie wyraziłeś(-aś) zgody na tę kategorię danych (Profil → Prywatność i zgody). " : " klient nie udzielił zgody na tę kategorię danych. "}
            To nie jest błąd — formularz jest po prostu krótszy.
          </p>
        )}
        {!def.has_coach && tryb === "klient" && (
          <p className="alert alert--warn">Nie masz jeszcze przypisanego trenera — możesz wypełniać, ale przesłanie trafi do trenera dopiero po nawiązaniu współpracy.</p>
        )}
        {konflikt && <p className="alert alert--warn" role="alert">{konflikt}</p>}
        {doprecyzowania.length > 0 && (
          <div className="alert alert--info" role="status">
            <b>Trener prosi o uzupełnienie:</b>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {doprecyzowania.map((d) => <li key={d.id}>{d.message || "wskazane pytania"} <small className="dim">({plDateTime(d.created_at)})</small></li>)}
            </ul>
          </div>
        )}
        {postep && (
          <small className="dim">Wymagane odpowiedzi: {postep.required_answered}/{postep.required_total} · możesz zapisać część i wrócić później.</small>
        )}
      </div>

      {def.sections.map((s) => {
        const pyt = pytaniaSekcji(s.key);
        const ukryte = ukryteSekcji(s.key);
        const fakty = faktyDla(s.key);
        if (pyt.length === 0 && ukryte.length === 0) return null;
        return (
          <section key={s.key} className="card" aria-labelledby={`sek-${s.key}`}>
            <h3 id={`sek-${s.key}`} style={{ marginTop: 0 }}>{s.label}</h3>
            <p className="dim" style={{ marginTop: 0 }}>{s.opis}</p>
            {fakty.length > 0 && (
              <p className="alert alert--info" style={{ fontSize: "0.85rem" }}>
                <b>We wstępnym wskazano:</b> {fakty.map((f) => `${f.label}: ${f.value}`).join(" · ")}.
                Poniżej możesz to rozwinąć — nie musisz przepisywać.
              </p>
            )}
            {ukryte.length > 0 && pyt.length === 0 && (
              <p className="dim">Sekcja wyłączona — brak zgody: {ukryte.map((d) => DOMENA_LABEL[d] ?? d).join(", ")}.</p>
            )}
            {pyt.map((q) => (
              <Pytanie key={q.question_id} q={q} odp={odp[q.question_id]} wymagane={wymagane.has(q.question_id)}
                blad={bledy[q.question_id] ?? (braki.includes(q.question_id) ? "To pytanie jest wymagane." : undefined)}
                doprec={pytaniaDoprec.has(q.question_id)}
                wpisalTrener={wpisaneNieprzezKlienta.has(q.question_id)}
                onChange={(o) => zmien(q.question_id, o)} />
            ))}
          </section>
        );
      })}

      <div className="card">
        {braki.length > 0 && (
          <p className="alert alert--error" role="alert">
            Uzupełnij wymagane odpowiedzi ({braki.length}):{" "}
            {braki.map((b, i) => <span key={b}>{i > 0 ? ", " : ""}<a href={`#wyw-${b}`}>{def.questions.find((q) => q.question_id === b)?.label ?? b}</a></span>)}
          </p>
        )}
        <ErrorBox error={def ? error : null} />
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn" disabled={busy || (postep ? !postep.ready : false)} onClick={() => void przeslij()}>
            {busy ? "Przesyłam…" : maWersje ? "Aktualizuj odpowiedzi" : "Prześlij trenerowi"}
          </button>
          <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => void zapiszTeraz()}>Zapisz szkic</button>
          <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => { void zapiszTeraz().then(onZamknij); }}>Wróć</button>
        </div>
        <small className="dim">
          {maWersje ? "Aktualizacja tworzy nową wersję — poprzednia zostaje w historii; trener przegląda nową od nowa."
            : "Przesłanie tworzy wersję, którą trener przegląda. Później możesz aktualizować odpowiedzi."}
          {postep && !postep.ready ? " Przycisk odblokuje się po uzupełnieniu wymaganych pytań." : ""}
        </small>
      </div>
    </div>
  );
}

function StanZapisu({ z, onRetry }: { z: Zapis; onRetry: () => void }) {
  if (z.stan === "saving") return <span className="dim" role="status">Zapisuję…</span>;
  if (z.stan === "saved") return <span className="dim" role="status">Zapisano ✓ {z.at ? plDateTime(z.at) : ""}</span>;
  if (z.stan === "error") return (
    <span role="alert" style={{ color: "var(--danger)", fontSize: "0.85rem" }}>
      Nie zapisano{z.msg ? `: ${z.msg}` : ""} <button type="button" className="btn btn--ghost btn--small" onClick={onRetry}>Ponów</button>
    </span>
  );
  return null;
}

function Pytanie({ q, odp, wymagane, blad, doprec, wpisalTrener, onChange }: {
  q: WywiadPytanie; odp?: Odp; wymagane: boolean; blad?: string; doprec: boolean; wpisalTrener: boolean;
  onChange: (o: Odp) => void;
}) {
  const id = `wyw-${q.question_id}`;
  const value = odp?.skipped ? "" : (odp?.value ?? "");
  const skipped = !!odp?.skipped;
  const chosen = q.type === "MULTI" ? value.split(",").map((x) => x.trim()).filter(Boolean) : [];
  const toggle = (opt: string) => {
    const next = chosen.includes(opt) ? chosen.filter((c) => c !== opt) : [...chosen, opt];
    onChange({ value: q.options.filter((o) => next.includes(o)).join(", "), skipped: false });
  };
  return (
    <div style={{ marginTop: 14, paddingLeft: doprec ? 10 : 0, borderLeft: doprec ? "3px solid var(--accent)" : "none", minWidth: 0, maxWidth: "100%" }}>
      <label htmlFor={id} id={`${id}-label`} style={{ margin: 0, color: "var(--text)", fontSize: "0.95rem" }}>
        {q.label}{" "}
        {wymagane && <span className="badge badge--warn" style={{ fontSize: "0.7rem" }}>wymagane</span>}
        {q.sensitive && <span className="badge" style={{ fontSize: "0.7rem", marginLeft: 4 }}>dane wrażliwe</span>}
        {doprec && <span className="badge badge--accent" style={{ fontSize: "0.7rem", marginLeft: 4 }}>trener prosi o doprecyzowanie</span>}
      </label>
      <small className="dim" id={`${id}-why`} style={{ display: "block", marginBottom: 4 }}>{q.why}</small>
      {q.type === "INFO" && (
        <label style={{ display: "flex", gap: 8, alignItems: "center", margin: 0, color: "var(--text)" }}>
          <input id={id} type="checkbox" checked={value === q.options[0]}
            onChange={(e) => onChange({ value: e.target.checked ? q.options[0] : "", skipped: false })} />
          {q.options[0] ?? "Rozumiem"}
        </label>
      )}
      {(q.type === "CHOICE" || q.type === "BOOL" || q.type === "SCALE") && (
        <div className="row" role="radiogroup" aria-labelledby={`${id}-label`} id={id} tabIndex={-1} style={{ gap: 6 }}>
          {q.options.map((opt) => (
            <button key={opt} type="button" role="radio" aria-checked={value === opt}
              className={value === opt ? "btn btn--small" : "btn btn--ghost btn--small"}
              style={{ whiteSpace: "normal", maxWidth: "100%", textAlign: "left" }}
              onClick={() => onChange({ value: opt, skipped: false })}>{opt}</button>
          ))}
        </div>
      )}
      {q.type === "MULTI" && (
        <div className="row" role="group" aria-labelledby={`${id}-label`} id={id} tabIndex={-1} style={{ gap: 6 }}>
          {q.options.map((opt) => (
            <button key={opt} type="button" aria-pressed={chosen.includes(opt)}
              className={chosen.includes(opt) ? "btn btn--small" : "btn btn--ghost btn--small"}
              style={{ whiteSpace: "normal", maxWidth: "100%", textAlign: "left" }}
              onClick={() => toggle(opt)}>{opt}</button>
          ))}
        </div>
      )}
      {q.type === "TEXT" && (
        <input id={id} value={value} placeholder={q.placeholder} maxLength={q.max_len} aria-describedby={`${id}-why`}
          aria-invalid={!!blad} onChange={(e) => onChange({ value: e.target.value, skipped: false })} />
      )}
      {q.type === "LONGTEXT" && (
        <textarea id={id} value={value} placeholder={q.placeholder} maxLength={q.max_len} rows={3} aria-describedby={`${id}-why`}
          aria-invalid={!!blad} onChange={(e) => onChange({ value: e.target.value, skipped: false })} />
      )}
      <div className="row" style={{ gap: 8, marginTop: 4 }}>
        {!wymagane && q.type !== "INFO" && (
          <button type="button" className="btn btn--ghost btn--small" aria-pressed={skipped}
            onClick={() => onChange(skipped ? { value: "", skipped: false } : { value: "", skipped: true })}>
            {skipped ? "Pominięte — odpowiedz" : "Pomiń"}
          </button>
        )}
        {wpisalTrener && <small className="dim">wpisane przez trenera (wspólnie)</small>}
        {blad && <small role="alert" style={{ color: "var(--danger)" }}>{blad}</small>}
      </div>
    </div>
  );
}

function losowyKlucz(): string {
  const c = globalThis.crypto;
  if (c && "randomUUID" in c) return c.randomUUID();
  return `k${Date.now()}${Math.random().toString(16).slice(2)}`;
}

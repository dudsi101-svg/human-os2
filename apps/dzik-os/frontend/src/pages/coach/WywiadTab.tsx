import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox, Spinner } from "../../components";
import {
  WywiadPodpowiedzi, WywiadPodsumowanie, WywiadPrzeslanie, WywiadStan, WywiadTyp, WywiadyPrzeglad, ZadanieSprawdzenia,
} from "../../types";
import Formularz from "../wywiad/Formularz";
import { opisWersji, PasekPostepu, PodsumowanieWywiadu, SEKCJA_LABEL, StatusBadges } from "../wywiad/wspolne";

/**
 * Zakładka „Wywiad” w karcie klienta (0.59.0). Trzy ODRĘBNE stany zamiast
 * jednego „klient nie zaczął”: (1) pusto — klient nic nie wypełnił,
 * (2) brak dostępu z POWODEM (zgody), (3) błąd pobierania z ponowieniem.
 * Działania: Przejrzyj, Poproś o uzupełnienie, Uzupełnij wspólnie, Oznacz
 * jako przejrzane (to potwierdzenie zapoznania się — nie „dopuszczenie”),
 * Poproś o wypełnienie / Przypomnij. Notatki wewnętrzne widzi tylko trener.
 */
export default function WywiadTab({ clientId }: { clientId: string }) {
  const [dane, setDane] = useState<WywiadyPrzeglad | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pods, setPods] = useState<WywiadPodsumowanie | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [wspolnie, setWspolnie] = useState<WywiadTyp | null>(null);

  const zaladuj = useCallback(() => {
    setError(null);
    api.get<WywiadyPrzeglad>(`/api/clients/${clientId}/wywiady`).then((d) => {
      setDane(d);
      if (d.access.ok) {
        api.get<WywiadPodsumowanie>(`/api/clients/${clientId}/wywiady/podsumowanie`).then(setPods).catch(() => setPods(null));
      }
    }).catch((e) => setError((e as Error).message));
  }, [clientId]);
  useEffect(zaladuj, [zaladuj]);

  if (error && !dane) return <ErrorBox error={error} onRetry={zaladuj} />;
  if (!dane) return <Spinner />;
  if (!dane.access.ok) {
    return (
      <div className="card">
        <h2>Wywiad — brak dostępu</h2>
        <p className="alert alert--warn" role="status">{dane.access.reason}</p>
        <p className="dim">Odpowiedzi klienta istnieją niezależnie od Twojego dostępu — zobaczysz je, gdy klient potwierdzi zgody w aplikacji.</p>
      </div>
    );
  }
  if (wspolnie) {
    const stan = dane.wywiady.find((w) => w.typ === wspolnie);
    return (
      <Formularz clientId={clientId} typ={wspolnie} tryb="trener" doprecyzowania={stan?.open_clarifications ?? []}
        maWersje={(stan?.submissions_count ?? 0) > 0}
        onZamknij={() => { setWspolnie(null); zaladuj(); }}
        onPrzeslano={(r) => { setWspolnie(null); setInfo(`Przesłano wersję ${r.version_no} (wspólnie z klientem).`); zaladuj(); }} />
    );
  }
  const pusto = dane.wywiady.every((w) => w.submission_status === "not_started");
  return (
    <>
      {info && <p className="alert alert--info" role="status">{info} <button type="button" className="btn btn--ghost btn--small" aria-label="Zamknij komunikat" onClick={() => setInfo(null)}>×</button></p>}
      {dane.access.missing_domains.length > 0 && (
        <p className="alert alert--warn">
          Klient nie udzielił zgody na: {dane.access.missing_domains.map((d) => d === "health_data" ? "dane zdrowotne" : "żywienie i alergie").join(", ")}.
          Pytania tych kategorii nie są zadawane, a odpowiedzi z nich są ukryte — to nie jest błąd.
        </p>
      )}
      {pusto && (
        <div className="card">
          <h2>Klient nie wypełnił jeszcze wywiadu</h2>
          <p className="dim">Oba formularze są dostępne w aplikacji klienta (zakładka „Wywiad”). Możesz poprosić o wypełnienie
            (jeden wpis w aplikacji klienta) albo uzupełnić wywiad wspólnie podczas konsultacji.</p>
        </div>
      )}
      {dane.review_tasks.length > 0 && <Zadania zadania={dane.review_tasks} onZmiana={zaladuj} />}
      {dane.wywiady.map((w) => (
        <KartaTrenera key={w.typ} w={w} clientId={clientId} onZmiana={zaladuj} onInfo={setInfo} onWspolnie={() => setWspolnie(w.typ)} />
      ))}
      {pods && (
        <div className="card">
          <h2>Podsumowanie</h2>
          <PodsumowanieWywiadu d={pods} klientId={clientId} />
        </div>
      )}
      <Podpowiedzi clientId={clientId} />
    </>
  );
}

function Zadania({ zadania, onZmiana }: { zadania: ZadanieSprawdzenia[]; onZmiana: () => void }) {
  const [note, setNote] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  async function rozstrzygnij(id: string) {
    setErr(null);
    try {
      await api.post(`/api/wywiady/zadania/${id}/rozstrzygnij`, { note: note[id] ?? "" });
      onZmiana();
    } catch (e) { setErr((e as Error).message); }
  }
  return (
    <div className="card" role="region" aria-label="Wymaga sprawdzenia">
      <h2>Wymaga sprawdzenia ({zadania.length})</h2>
      <p className="dim">Klient zmienił w wywiadzie fakty istotne dla planu. Plan NIE został zmieniony automatycznie;
        publikacja nowej wersji tego planu jest zablokowana do rozstrzygnięcia.</p>
      <ErrorBox error={err} />
      {zadania.map((t) => (
        <div key={t.id} style={{ marginBottom: 10 }}>
          <b>{t.plan_kind === "training" ? "Plan treningowy" : "Plan żywieniowy"}</b> · zmienione: {t.changed_facts.join(", ")} · {plDateTime(t.created_at)}
          <input value={note[t.id] ?? ""} placeholder="Co sprawdziłem (opcjonalnie)" aria-label="Notatka rozstrzygnięcia"
            onChange={(e) => setNote((n) => ({ ...n, [t.id]: e.target.value }))} style={{ marginTop: 4 }} />
          <button type="button" className="btn btn--small" style={{ marginTop: 6 }} onClick={() => void rozstrzygnij(t.id)}>Sprawdziłem plan — rozstrzygnij</button>
        </div>
      ))}
    </div>
  );
}

function KartaTrenera({ w, clientId, onZmiana, onInfo, onWspolnie }: {
  w: WywiadStan; clientId: string; onZmiana: () => void; onInfo: (s: string) => void; onWspolnie: () => void;
}) {
  const [hist, setHist] = useState<WywiadPrzeslanie[] | null>(null);
  const [otwarte, setOtwarte] = useState<"przeglad" | "doprec" | null>(null);
  const [nota, setNota] = useState("");
  const [wybrane, setWybrane] = useState<Set<string>>(new Set());
  const [wiadomosc, setWiadomosc] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const last = w.last_submission;

  const wczytajHistorie = useCallback(() => api
    .get<{ submissions: WywiadPrzeslanie[] }>(`/api/clients/${clientId}/wywiady/${w.typ}/historia`)
    .then((r) => setHist(r.submissions)).catch((e) => setErr((e as Error).message)), [clientId, w.typ]);

  async function przejrzane() {
    if (!last) return;
    setBusy(true); setErr(null);
    try {
      await api.post(`/api/wywiady/zgloszenia/${last.id}/przeglad`, { outcome: "REVIEWED", internal_note: nota });
      onInfo(`Oznaczono wersję ${last.version_no} jako przejrzaną — klient dostał informację. To nie jest dopuszczenie do treningu.`);
      setNota(""); onZmiana();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function popros() {
    if (!last) return;
    setBusy(true); setErr(null);
    try {
      await api.post(`/api/wywiady/zgloszenia/${last.id}/doprecyzowania`, { question_ids: [...wybrane], message: wiadomosc });
      onInfo("Wysłano prośbę o uzupełnienie — klient ma jeden wpis w aplikacji.");
      setOtwarte(null); setWybrane(new Set()); setWiadomosc(""); onZmiana();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function przypomnij() {
    setBusy(true); setErr(null);
    try {
      const r = await api.post<{ sent: boolean; note: string | null }>(`/api/clients/${clientId}/wywiady/${w.typ}/przypomnij`);
      onInfo(r.sent ? "Wysłano prośbę — klient ma jeden wpis w aplikacji." : (r.note ?? "Prośba została już dziś wysłana."));
    } catch (e) {
      const a = e as ApiError;
      setErr(a.message);
    } finally { setBusy(false); }
  }

  const ostatnia = hist?.find((s) => s.id === last?.id) ?? null;
  const sekcje = ostatnia ? [...new Set(ostatnia.answers.map((a) => a.section))] : [];
  return (
    <div className="card">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}>{w.title}</h2>
        <StatusBadges s={w} />
      </div>
      <small className="dim">{opisWersji(w)}</small>
      <PasekPostepu p={w.progress} />
      {last?.safety_flag && (
        <p className="alert alert--warn" role="alert">W odpowiedziach pojawił się sygnał do konsultacji medycznej — wstrzymaj się z planem obciążającym do czasu konsultacji klienta z lekarzem.</p>
      )}
      {w.open_clarifications.length > 0 && (
        <small className="dim">Otwarta prośba o uzupełnienie ({w.open_clarifications.length}) — zamknie ją kolejne przesłanie klienta.</small>
      )}
      <ErrorBox error={err} />
      <div className="row" style={{ marginTop: 10, gap: 6 }}>
        {last && (
          <button type="button" className="btn btn--small" aria-expanded={otwarte === "przeglad"}
            onClick={() => { setOtwarte(otwarte === "przeglad" ? null : "przeglad"); if (!hist) void wczytajHistorie(); }}>
            {otwarte === "przeglad" ? "Zwiń" : "Przejrzyj"}
          </button>
        )}
        {last && w.review_status === "not_reviewed" && (
          <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void przejrzane()}>Oznacz jako przejrzane</button>
        )}
        {last && (
          <button type="button" className="btn btn--ghost btn--small" aria-expanded={otwarte === "doprec"}
            onClick={() => { setOtwarte(otwarte === "doprec" ? null : "doprec"); if (!hist) void wczytajHistorie(); }}>Poproś o uzupełnienie</button>
        )}
        <button type="button" className="btn btn--ghost btn--small" onClick={onWspolnie}>Uzupełnij wspólnie</button>
        {(w.submission_status !== "submitted" || w.freshness_status === "update_requested") && (
          <button type="button" className="btn btn--ghost btn--small" disabled={busy} onClick={() => void przypomnij()}>
            {w.submission_status === "not_started" ? "Poproś o wypełnienie" : "Przypomnij o dokończeniu"}
          </button>
        )}
      </div>
      {last && w.review_status === "not_reviewed" && (
        <div style={{ marginTop: 8 }}>
          <label htmlFor={`nota-${w.typ}`}>Notatka wewnętrzna do przeglądu (klient jej nie widzi)</label>
          <textarea id={`nota-${w.typ}`} value={nota} rows={2} maxLength={4000} onChange={(e) => setNota(e.target.value)} />
        </div>
      )}
      {otwarte === "przeglad" && (hist === null ? <Spinner /> : ostatnia && (
        <div style={{ marginTop: 10 }}>
          <h3 style={{ marginBottom: 4 }}>Wersja {ostatnia.version_no} · {plDateTime(ostatnia.submitted_at)}{ostatnia.migrated ? " · przeniesiona z rozmowy" : ""}</h3>
          {sekcje.map((s) => (
            <div key={s} style={{ marginBottom: 8 }}>
              <small className="dim" style={{ textTransform: "uppercase" }}>{SEKCJA_LABEL[s] ?? s}</small>
              <ul style={{ margin: "2px 0 0", paddingLeft: 18 }}>
                {ostatnia.answers.filter((a) => a.section === s && a.active).map((a) => (
                  <li key={a.question_id}>
                    <b>{a.label}</b>{" "}
                    {a.hidden ? <span className="dim">ukryte — brak zgody na tę kategorię</span>
                      : a.skipped ? <span className="dim">pominięte</span>
                        : <span style={{ color: a.to_discuss ? "var(--warn)" : undefined }}>{a.value}</span>}
                    {a.entered_by && a.entered_by !== clientId && <small className="dim"> · wpisał trener (wspólnie)</small>}
                    {a.at && <small className="dim"> · {plDateTime(a.at)}</small>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {ostatnia.reviews.length > 0 && (
            <small className="dim">Przeglądy tej wersji: {ostatnia.reviews.map((r) => `${r.outcome === "REVIEWED" ? "przejrzana" : "prośba o doprecyzowanie"} ${plDateTime(r.created_at)}${r.internal_note ? ` — „${r.internal_note}”` : ""}${r.migrated ? " (z rozmowy)" : ""}`).join("; ")}</small>
          )}
          {hist && hist.length > 1 && (
            <details style={{ marginTop: 6 }}>
              <summary>Wcześniejsze wersje ({hist.length - 1})</summary>
              <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
                {hist.filter((s) => s.id !== ostatnia.id).map((s) => (
                  <li key={s.id}>wersja {s.version_no} · {plDateTime(s.submitted_at)} · {s.review ? (s.review.outcome === "REVIEWED" ? "przejrzana" : "doprecyzowanie") : "nieprzejrzana"} · odpowiedzi: {s.answers.filter((a) => !a.skipped && a.value).length}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
      {otwarte === "doprec" && (hist === null ? <Spinner /> : ostatnia && (
        <div style={{ marginTop: 10 }}>
          <b>Które odpowiedzi wymagają doprecyzowania?</b>
          <div className="row" style={{ gap: 6, marginTop: 6 }}>
            {ostatnia.answers.filter((a) => a.active && !a.hidden).map((a) => (
              <button key={a.question_id} type="button" aria-pressed={wybrane.has(a.question_id)}
                className={wybrane.has(a.question_id) ? "btn btn--small" : "btn btn--ghost btn--small"}
                onClick={() => setWybrane((s) => { const n = new Set(s); if (n.has(a.question_id)) n.delete(a.question_id); else n.add(a.question_id); return n; })}>
                {a.label.length > 60 ? a.label.slice(0, 57) + "…" : a.label}
              </button>
            ))}
          </div>
          <label htmlFor={`msg-${w.typ}`}>Wiadomość dla klienta</label>
          <textarea id={`msg-${w.typ}`} value={wiadomosc} rows={2} maxLength={2000} onChange={(e) => setWiadomosc(e.target.value)}
            placeholder="np. Które kolano i od kiedy? Czy ból pojawia się przy schodzeniu ze schodów?" />
          <button type="button" className="btn btn--small" disabled={busy || (wybrane.size === 0 && !wiadomosc.trim())} onClick={() => void popros()}>Wyślij prośbę</button>
        </div>
      ))}
    </div>
  );
}

function Podpowiedzi({ clientId }: { clientId: string }) {
  const [p, setP] = useState<WywiadPodpowiedzi | null>(null);
  useEffect(() => {
    api.get<WywiadPodpowiedzi>(`/api/clients/${clientId}/wywiady/podpowiedzi`).then(setP).catch(() => setP(null));
  }, [clientId]);
  if (!p || !p.available) return null;
  const t = p.training as Record<string, unknown>;
  const n = p.nutrition;
  return (
    <details className="card">
      <summary>Podpowiedzi do konfiguratorów (z wywiadu, z pochodzeniem)</summary>
      <p className="dim">Mapowanie deterministyczne faktów → pola konfiguratora. Każdą podpowiedź możesz odrzucić; brak informacji nigdy nie jest traktowany jak zgoda.</p>
      {p.warnings && p.warnings.length > 0 && p.warnings.map((w) => <p key={w} className="alert alert--warn">{w}</p>)}
      <h3>Konfigurator treningu</h3>
      <ul style={{ paddingLeft: 18 }}>
        {"goal_text" in t && <li>cel: {String(t.goal_text)}</li>}
        {"level" in t && <li>poziom: {String(t.level)}</li>}
        {"days_per_week" in t && <li>dni w tygodniu: {String(t.days_per_week)}</li>}
        {"available_weekdays" in t && <li>dni: {(t.available_weekdays as number[]).join(", ")}</li>}
        {"equipment_text" in t && <li>sprzęt: {String(t.equipment_text)}</li>}
        {"health" in t && <li>zdrowie: {JSON.stringify(t.health)}</li>}
        {"week_map" in t && <li>mapa tygodnia: {String(t.week_map)}</li>}
      </ul>
      <h3>Kreator dań</h3>
      <ul style={{ paddingLeft: 18 }}>
        <li>alergeny (ograniczenie): {n.allergens.length ? n.allergens.join(", ") : "brak rozpoznanych"}{n.allergens_text ? ` — z odpowiedzi: „${n.allergens_text}”` : ""}{n.allergen_status ? ` (status: ${n.allergen_status})` : ""}</li>
        {n.intolerances && <li>nietolerancje (preferencja): {n.intolerances}</li>}
        {n.exclusions && <li>wykluczenia z wyboru (preferencja): {n.exclusions}</li>}
        {n.preferences.length > 0 && <li>styl: {n.preferences.join("; ")}</li>}
        {n.cooking && <li>gotowanie: {n.cooking}</li>}
      </ul>
      <small className="dim">Źródła: {p.sources.map((s) => `${s.label} (v${s.version_no})`).join("; ")}. <Link to="/trener/szablony">Kreator dań</Link> podpowiada te alergeny po wybraniu klienta.</small>
    </details>
  );
}

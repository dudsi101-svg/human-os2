import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import { Icon, Spinner } from "../components";
import { WiedzaKartaPelna, Wyjasnienie, WyjasnienieAkcja } from "../types";

/**
 * „Dlaczego?” (ekran W4 pakietu Wiedza, 0.56.0).
 *
 * Panel czyta ZAPISANY ślad decyzji przez `/api/wiedza/wyjasnij` i pokazuje
 * jeden z siedmiu statusów kontraktu. Nie ma tu przycisku „wygeneruj powód”:
 * brak śladu to uczciwy komunikat plus zasada ogólna. Panel jest nakładką
 * (dolny arkusz na telefonie, boczny na tablecie/desktopie): ekran pod
 * spodem nie jest odmontowywany, więc timer przerwy, wpisane serie
 * i formularz posiłku zostają. Zamknięcie (Escape, przycisk, tło)
 * przywraca fokus do przycisku, który panel otworzył.
 *
 * Pełna karta wiedzy otwiera się WEWNĄTRZ panelu (przycisk „Wróć do
 * wyjaśnienia”), a osobny link prowadzi do zakładki Wiedza.
 */

export interface DlaczegoCel {
  plan_kind?: "training" | "nutrition";
  plan_id: string;
  plan_revision: number;
  target_type: string;
  target_id: string;
  tryb?: "current" | "history";
}

const STATUS_TEKST: Record<string, string> = {
  explained: "Wyjaśnienie z zapisanej decyzji",
  general_only: "Tylko zasada ogólna",
  missing_trace: "Brak zapisanego uzasadnienia",
  insufficient_data: "Za mało danych",
  inconsistent_data: "Dane sprzeczne",
  stale_context: "Nieaktualna wersja planu",
  restricted: "Ścieżka bezpieczeństwa",
};

export function Dlaczego({ cel, naglowek, etykieta = "Dlaczego?" }: {
  cel: DlaczegoCel; naglowek: string; etykieta?: string;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [wynik, setWynik] = useState<Wyjasnienie | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [karta, setKarta] = useState<WiedzaKartaPelna | null>(null);
  const [kartaBlad, setKartaBlad] = useState<string | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const closeBtn = useRef<HTMLButtonElement | null>(null);

  async function wczytaj() {
    setLoading(true); setError(null); setWynik(null);
    try {
      const w = await api.post<Wyjasnienie>("/api/wiedza/wyjasnij", {
        plan_kind: cel.plan_kind ?? "training", plan_id: cel.plan_id,
        plan_revision: cel.plan_revision, target_type: cel.target_type,
        target_id: cel.target_id, tryb: cel.tryb ?? "current",
      });
      setWynik(w);
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "STALE_PLAN" || err.status === 409) {
        setWynik({ status: "stale_context", trace_id: null, plan_revision: cel.plan_revision,
          paragraphs: ["To wyjaśnienie dotyczy wcześniejszej wersji planu."],
          used_fact_keys: [], article_refs: [], actions: [], historical: false });
      } else if (err.status === 404) {
        // Brak dostępu / brak planu: neutralny komunikat bez danych elementu.
        setError("Nie znaleziono tego elementu planu.");
      } else {
        setError(err.message || "Nie udało się wczytać wyjaśnienia.");
      }
    } finally {
      setLoading(false);
    }
  }

  function otworz() {
    setOpen(true);
    setKarta(null);
    void wczytaj();
  }
  function zamknij() {
    setOpen(false);
    setKarta(null);
    // Fokus wraca do przycisku wywołującego (K23).
    requestAnimationFrame(() => trigger.current?.focus());
  }
  useEffect(() => {
    if (open) requestAnimationFrame(() => closeBtn.current?.focus());
  }, [open]);
  // Escape działa niezależnie od tego, gdzie jest fokus (po powrocie z
  // karty przycisk, który miał fokus, znika z drzewa — nasłuch na
  // dokumencie nie zależy od tego, który element jest aktywny).
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); zamknij(); }
    };
    document.addEventListener("keydown", onDoc);
    return () => document.removeEventListener("keydown", onDoc);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") { e.stopPropagation(); zamknij(); }
  }
  function wrocDoWyjasnienia() {
    setKarta(null);
    requestAnimationFrame(() => closeBtn.current?.focus());
  }

  async function otworzKarte(id: string) {
    setKartaBlad(null); setKarta(null);
    try {
      const k = await api.get<WiedzaKartaPelna>(`/api/wiedza/artykuly/${encodeURIComponent(id)}`);
      setKarta(k);
      void api.post(`/api/wiedza/odczyty/${encodeURIComponent(id)}`, {}).catch(() => undefined);
    } catch (e) {
      const err = e as ApiError;
      setKartaBlad(err.status === 410 ? "Materiał jest aktualizowany — sprawdź zamiennik w zakładce Wiedza."
        : err.message);
    }
  }

  return (
    <>
      <button type="button" ref={trigger} className="btn btn--ghost btn--small"
        aria-haspopup="dialog" aria-expanded={open} onClick={otworz}>
        <Icon name="info" size={16} /> {etykieta}
      </button>
      {open && (
        <div className="dlaczego" onKeyDown={onKeyDown}
          onMouseDown={(e) => { if (e.target === e.currentTarget) zamknij(); }}>
          <div className="dlaczego__panel" role="dialog" aria-modal="true"
            aria-labelledby="dlaczego-tytul">
            <div className="dlaczego__head">
              <div>
                <h2 id="dlaczego-tytul">{karta ? karta.title : naglowek}</h2>
                {!karta && (
                  <div className="dlaczego__status">
                    wersja planu {cel.plan_revision}
                    {cel.tryb === "history" && " · Historia"}
                    {wynik && <> · {STATUS_TEKST[wynik.status] ?? wynik.status}</>}
                  </div>
                )}
              </div>
              <button type="button" ref={closeBtn} className="btn btn--ghost btn--small"
                onClick={zamknij} aria-label="Zamknij panel Dlaczego">
                <Icon name="close" size={18} />
              </button>
            </div>
            {karta ? (
              <KartaWPanelu karta={karta} onBack={wrocDoWyjasnienia} />
            ) : (
              <>
                {loading && <Spinner />}
                {error && (
                  <div>
                    <p className="dlaczego__akapit">{error}</p>
                    <div className="dlaczego__akcje">
                      <button className="btn btn--small" onClick={() => void wczytaj()}>Ponów</button>
                    </div>
                  </div>
                )}
                {kartaBlad && <p className="dlaczego__akapit alert alert--warn">{kartaBlad}</p>}
                {wynik && (
                  <>
                    {wynik.historical && (
                      <p className="dlaczego__status"><span className="badge">Historia</span> stan z chwili
                        podjęcia decyzji — dziennik z późniejszych dni nie jest tu podstawiany.</p>
                    )}
                    {wynik.paragraphs.map((p, i) => (
                      <p className="dlaczego__akapit" key={i}>{p}</p>
                    ))}
                    {wynik.status === "explained" && wynik.used_fact_keys.length > 0 && (
                      <p className="dlaczego__status">Na podstawie zapisanych faktów: {wynik.used_fact_keys.join(", ")}.</p>
                    )}
                    <div className="dlaczego__akcje">
                      {wynik.actions.map((a, i) => <Akcja key={i} akcja={a} onArticle={otworzKarte} onRetry={() => void wczytaj()} />)}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function Akcja({ akcja, onArticle, onRetry }: {
  akcja: WyjasnienieAkcja; onArticle: (id: string) => void; onRetry: () => void;
}) {
  if (akcja.type === "open_article" && akcja.target_id) {
    return (
      <button type="button" className="btn btn--ghost btn--small" onClick={() => onArticle(akcja.target_id!)}>
        <Icon name="knowledge" size={16} /> {akcja.label}
      </button>
    );
  }
  if (akcja.type === "open_safety_flow" && akcja.target_id) {
    return <Link className="btn btn--small" to={akcja.target_id}><Icon name="msg" size={16} /> {akcja.label}</Link>;
  }
  if (akcja.type === "open_source_view" && akcja.target_id) {
    return <Link className="btn btn--ghost btn--small" to={akcja.target_id}>{akcja.label}</Link>;
  }
  if (akcja.type === "retry") {
    return <button type="button" className="btn btn--ghost btn--small" onClick={onRetry}>{akcja.label}</button>;
  }
  return null;
}

/** Karta wiedzy wyświetlona wewnątrz panelu — bez opuszczania ekranu planu. */
export function KartaWPanelu({ karta, onBack }: { karta: WiedzaKartaPelna; onBack: () => void }) {
  return (
    <div>
      <div className="dlaczego__akcje" style={{ marginTop: 6 }}>
        <button type="button" className="btn btn--ghost btn--small" onClick={onBack}>
          <Icon name="chevron-up" size={16} /> Wróć do wyjaśnienia
        </button>
        <Link className="btn btn--ghost btn--small" to={`/wiedza?karta=${encodeURIComponent(karta.id)}`}>
          Otwórz w Wiedzy
        </Link>
      </div>
      {karta.szkic && (
        <p className="wiedza-demo" style={{ marginTop: 10 }}>
          Treść robocza (tryb demonstracyjny) — bez przeglądu eksperckiego.
        </p>
      )}
      <p className="dlaczego__akapit"><b>W skrócie:</b> {karta.summary}</p>
      {karta.steps.length > 0 && (
        <ol className="wiedza-karta__kroki">{karta.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      )}
      <p className="dlaczego__akapit" style={{ whiteSpace: "pre-wrap" }}>{karta.detail}</p>
      <p className="dlaczego__status">Ograniczenia: {karta.limits}</p>
      {karta.media === null && karta.exercise_id && (
        <p className="dlaczego__status">Instrukcja tekstowa — film nie został jeszcze dodany.</p>
      )}
      <p className="dlaczego__status">
        {karta.author_label} · {karta.review.approved
          ? `recenzja ${karta.review.reviewed_at ?? ""}`
          : "bez zatwierdzenia eksperckiego"} · czas czytania {karta.estimated_read_minutes ?? 1} min
      </p>
    </div>
  );
}

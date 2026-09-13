import { Link } from "react-router-dom";
import { plDateTime } from "../../dates";
import {
  FreshnessStatus, ReviewStatus, SubmissionStatus, WywiadPodsumowanie, WywiadStan, WywiadTyp,
} from "../../types";

/** Wspólne elementy zakładki „Wywiad” (0.59.0) dla klienta i trenera:
 * etykiety trzech ROZDZIELONYCH statusów, pasek postępu, podsumowanie
 * deterministyczne (każdy punkt wskazuje odpowiedź, wersję, autora i czas). */

export const TYP_LABEL: Record<WywiadTyp, string> = { wstepny: "Wywiad wstępny", gleboki: "Wywiad głęboki" };

/** Etykiety sekcji (klucze z `wywiad/definicje.py`). */
export const SEKCJA_LABEL: Record<string, string> = {
  cel: "Cel", punkt_wyjscia: "Punkt wyjścia", trening: "Trening", zdrowie: "Zdrowie i ograniczenia",
  odzywianie: "Odżywianie", codziennosc: "Codzienność", wspolpraca: "Współpraca",
  motywacja: "Motywacja", historia_treningowa: "Historia treningowa", ograniczenia: "Pogłębienie ograniczeń",
  regeneracja: "Regeneracja", historia_odzywiania: "Historia odżywiania", organizacja: "Organizacja",
  preferencje: "Preferencje szczegółowe", pytania_trenera: "Pytania trenera",
};

export const SUBMISSION_LABEL: Record<SubmissionStatus, string> = {
  not_started: "nierozpoczęty", draft: "szkic", submitted: "przesłany",
};
export const REVIEW_LABEL: Record<ReviewStatus, string> = {
  not_reviewed: "nieprzejrzany", needs_clarification: "wymaga doprecyzowania", reviewed: "przejrzany",
};
export const FRESHNESS_LABEL: Record<FreshnessStatus, string> = {
  current: "aktualny", update_requested: "prośba o aktualizację",
};

export function StatusBadges({ s, showReview = true }: { s: WywiadStan; showReview?: boolean }) {
  return (
    <span className="row" style={{ gap: 6, display: "inline-flex" }}>
      <span className={"badge " + (s.submission_status === "submitted" ? "badge--ok" : s.submission_status === "draft" ? "badge--warn" : "")}
        title="Status wypełnienia">{SUBMISSION_LABEL[s.submission_status]}</span>
      {showReview && s.submission_status !== "not_started" && (
        <span className={"badge " + (s.review_status === "reviewed" ? "badge--ok" : s.review_status === "needs_clarification" ? "badge--warn" : "")}
          title="Status przeglądu ostatniej wersji">{REVIEW_LABEL[s.review_status]}</span>
      )}
      {s.freshness_status === "update_requested" && (
        <span className="badge badge--accent" title="Aktualność">{FRESHNESS_LABEL.update_requested}</span>
      )}
    </span>
  );
}

export function PasekPostepu({ p }: { p: WywiadStan["progress"] }) {
  const pct = Math.max(0, Math.min(100, p.percent));
  return (
    <div style={{ marginTop: 6 }}>
      <div role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
        aria-label={`Wymagane odpowiedzi: ${p.required_answered} z ${p.required_total}`}
        style={{ height: 6, borderRadius: 3, background: "var(--bg-raised)", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: pct === 100 ? "var(--ok)" : "var(--accent)" }} />
      </div>
      <small className="dim">
        Wymagane: {p.required_answered}/{p.required_total}{p.required_total === 0 ? " (brak pytań wymaganych)" : ""} ·
        wszystkie aktywne: {p.active_answered}/{p.active_total}
        {p.ready && !p.data_ready ? " · część odpowiedzi „do omówienia z trenerem”" : ""}
      </small>
    </div>
  );
}

export function opisWersji(s: WywiadStan): string {
  const last = s.last_submission;
  if (!last) return s.draft ? `szkic zapisany ${plDateTime(s.draft.updated_at)}` : "brak odpowiedzi";
  const kto = last.collection_mode === "WSPOLNIE" ? ", wspólnie z trenerem" : last.migrated ? ", przeniesiona z rozmowy" : "";
  return `wersja ${last.version_no} przesłana ${plDateTime(last.submitted_at)}${kto}`
    + (s.draft?.dirty && s.submission_status === "draft" ? ` · szkic zmieniony ${plDateTime(s.draft.updated_at)}` : "");
}

function Zrodlo({ p, klientId }: { p: { source: WywiadPodsumowanie["cele"][number]["source"] }; klientId: string }) {
  const s = p.source;
  return (
    <small className="dim">
      {" "}({TYP_LABEL[s.typ].toLowerCase()} v{s.version_no}
      {s.at ? `, ${plDateTime(s.at)}` : ""}
      {s.entered_by && s.entered_by !== klientId ? ", wpisał trener" : ""})
    </small>
  );
}

export function PodsumowanieWywiadu({ d, klientId, linkDoWywiadu }: {
  d: WywiadPodsumowanie; klientId: string; linkDoWywiadu?: (typ: WywiadTyp) => string;
}) {
  const pusto = !d.cele.length && !d.ograniczenia.length && !d.preferencje.length && !d.do_wyjasnienia.length && !d.do_aktualizacji.length;
  if (pusto) return <p className="dim">Podsumowanie pojawi się po przesłaniu wywiadu.</p>;
  const Sekcja = ({ tytul, items }: { tytul: string; items: WywiadPodsumowanie["cele"] }) => items.length === 0 ? null : (
    <>
      <h3 style={{ marginBottom: 4 }}>{tytul}</h3>
      <ul style={{ marginTop: 0, paddingLeft: 18 }}>
        {items.map((p, i) => <li key={i}><b>{p.source.label}:</b> {p.text}<Zrodlo p={p} klientId={klientId} /></li>)}
      </ul>
    </>
  );
  return (
    <div>
      <Sekcja tytul="Cele" items={d.cele} />
      <Sekcja tytul="Ograniczenia" items={d.ograniczenia} />
      <Sekcja tytul="Preferencje" items={d.preferencje} />
      <Sekcja tytul="Do wyjaśnienia z trenerem" items={d.do_wyjasnienia} />
      {d.do_aktualizacji.length > 0 && (
        <>
          <h3 style={{ marginBottom: 4 }}>Do aktualizacji</h3>
          <ul style={{ marginTop: 0, paddingLeft: 18 }}>
            {d.do_aktualizacji.map((p) => (
              <li key={p.clarification_id}>
                {p.text} <small className="dim">({TYP_LABEL[p.typ].toLowerCase()}, {plDateTime(p.created_at)}, pytań: {p.question_ids.length})</small>
                {linkDoWywiadu && <> · <Link to={linkDoWywiadu(p.typ)}>Uzupełnij</Link></>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDate } from "../../dates";
import { PlanKind, Szkic, WynikPublikacji, ZestawZmian } from "../../types";
import SzkicPlanu from "./SzkicPlanu";

/**
 * Panel publikacji dla planu / diety / szablonu (0.58.0): znacznik
 * aktywnego szkicu, „Edytuj (szkic)”, działania planu (duplikuj, odepnij,
 * archiwizuj — trzy różne rzeczy, nie synonimy) oraz lista opublikowanych
 * zmian ze stanem doręczenia i odczytu wpisu klienta.
 *
 * Gdy szkice są wyłączone na serwerze (DZIK_SZKICE_PUBLIKACJA=false),
 * panel zgłasza to rodzicowi (`onDostepne(false)`), a rodzic pokazuje
 * poprzedni edytor „Nowa wersja”.
 */
export default function PublikacjaPanel({ planKind, planId, clientId, onZmiana, onDostepne }: {
  planKind: PlanKind;
  planId: string;
  clientId: string | null;
  onZmiana: () => void;
  onDostepne?: (dostepne: boolean) => void;
}) {
  const [szkic, setSzkic] = useState<Szkic | null | undefined>(undefined);
  const [edycja, setEdycja] = useState(false);
  const [zmiany, setZmiany] = useState<ZestawZmian[]>([]);
  const [info, setInfo] = useState<string | null>(null);
  const [potwierdz, setPotwierdz] = useState<"archiwizuj" | "odepnij" | null>(null);

  const zaladuj = useCallback(() => {
    api.get<{ draft: Szkic | null }>(`/api/szkice/plan/${planKind}/${planId}/aktywny`)
      .then((d) => { setSzkic(d.draft); onDostepne?.(true); })
      .catch((e) => {
        const err = e as ApiError;
        if (err.status === 404) onDostepne?.(false);
        setSzkic(null);
      });
    api.get<{ changes: ZestawZmian[] }>(`/api/plany/${planKind}/${planId}/zmiany`)
      .then((d) => setZmiany(d.changes)).catch(() => setZmiany([]));
  }, [planKind, planId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(zaladuj, [zaladuj]);

  async function akcja(nazwa: "archiwizuj" | "odepnij" | "duplikuj") {
    setPotwierdz(null);
    const baza = planKind === "training" ? "/api/plans" : "/api/nutrition";
    try {
      const r = await api.post<{ status?: string; title?: string }>(`${baza}/${planId}/${nazwa}`);
      setInfo(nazwa === "duplikuj" ? `Utworzono duplikat „${r.title}” (nowe identyfikatory elementów).`
        : nazwa === "odepnij" ? "Plan odpięty od klienta — historia i wykonania zostają."
          : "Plan zarchiwizowany — znika z aktywnych, historia zostaje.");
      onZmiana();
    } catch (e) { setInfo((e as Error).message); }
  }

  function poPublikacji(w: WynikPublikacji) {
    setEdycja(false);
    setInfo(clientId
      ? `Opublikowano wersję v${w.version_no}: ${w.summary} Klient dostał jeden wpis w aplikacji.`
      : `Opublikowano wersję v${w.version_no} szablonu: ${w.summary}`);
    zaladuj();
    onZmiana();
  }

  if (szkic === undefined) return null;

  return (
    <div style={{ marginBottom: 10 }}>
      {info && <p className="alert alert--info" role="status">{info} <button type="button" className="btn btn--ghost btn--small" aria-label="Zamknij komunikat" onClick={() => setInfo(null)}>×</button></p>}
      {!edycja && (
        <div className="row" style={{ gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <button type="button" className="btn btn--small" onClick={() => setEdycja(true)}>
            {szkic ? `Kontynuuj szkic (${szkic.changes} zm.)` : "Edytuj (szkic)"}
          </button>
          {szkic && <span className="badge badge--warn">Szkic — klient jeszcze nie widzi zmian</span>}
          <button type="button" className="btn btn--ghost btn--small" onClick={() => akcja("duplikuj")}>Duplikuj</button>
          {clientId && <button type="button" className="btn btn--ghost btn--small" onClick={() => setPotwierdz("odepnij")}>Odepnij od klienta</button>}
          <button type="button" className="btn btn--ghost btn--small" onClick={() => setPotwierdz("archiwizuj")}>Archiwizuj</button>
        </div>
      )}
      {potwierdz && (
        <div role="alertdialog" className="alert alert--warn">
          {potwierdz === "archiwizuj"
            ? "Archiwizacja kończy plan: znika z aktywnych, a historia wersji i wykonań zostaje. To nie jest odpięcie od klienta."
            : "Odpięcie zdejmuje plan z klienta (przestaje go widzieć); plan i jego historia zostają. To nie jest archiwizacja."}
          <div className="row" style={{ marginTop: 6, gap: 6 }}>
            <button type="button" className="btn btn--danger btn--small" onClick={() => akcja(potwierdz)}>
              {potwierdz === "archiwizuj" ? "Archiwizuj" : "Odepnij"}
            </button>
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setPotwierdz(null)}>Anuluj</button>
          </div>
        </div>
      )}
      {edycja && (
        <SzkicPlanu planKind={planKind} planId={planId}
          onZamknij={() => { setEdycja(false); zaladuj(); }}
          onOpublikowano={poPublikacji} />
      )}
      {zmiany.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary>Opublikowane zmiany ({zmiany.length})</summary>
          <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
            {zmiany.map((z) => (
              <li key={z.id}>
                <Link to={`/zmiany/${z.id}`}>v{z.old_version_no} → v{z.new_version_no}</Link> · {plDate(z.published_at)} · {z.summary}
                {clientId && (
                  <span className="dim">
                    {" · "}{z.notification ? (z.notification.read_at ? `odczytane ${plDate(z.notification.read_at)}` : "wpis utworzony, nieodczytany") : "wpis jeszcze niedoręczony"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

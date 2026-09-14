/**
 * Karta „Zapotrzebowanie kaloryczne” (0.62.0) — wspólna dla aplikacji klienta
 * (zakładki Wywiad i Dieta) i panelu trenera (Wywiad, Dieta). Źródło:
 * GET /api/clients/{id}/zapotrzebowanie. Filtr flagi zdrowotnej jest po
 * stronie serwera: przy status="hidden" klient dostaje tylko komunikat.
 * 404 = moduł wyłączony w tej instalacji → karta nie renderuje się wcale.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox } from "../../components";
import { ZapotrzebowanieOut } from "../../types";

export function useZapotrzebowanie(clientId: string) {
  const [dane, setDane] = useState<ZapotrzebowanieOut | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const zaladuj = useCallback(() => {
    setError(null);
    api.get<ZapotrzebowanieOut>(`/api/clients/${clientId}/zapotrzebowanie`).then(setDane).catch((e) => {
      if (e instanceof ApiError && e.status === 404) { setDane(null); return; }
      setError((e as Error).message);
    });
  }, [clientId]);
  useEffect(zaladuj, [zaladuj]);
  return { dane, error, zaladuj };
}

export default function ZapotrzebowanieKarta({ clientId, tryb, linkDoWywiadu, onOtworz, kompakt = false }: {
  clientId: string;
  tryb: "klient" | "trener";
  /** Link do formularza (klient: /wywiad?typ=zapotrzebowanie). */
  linkDoWywiadu?: string;
  /** Trener: otwarcie formularza w trybie „wspólnie”. */
  onOtworz?: () => void;
  /** Zakładka Dieta: bez historii i podstawienia w nagłówku. */
  kompakt?: boolean;
}) {
  const { dane, error, zaladuj } = useZapotrzebowanie(clientId);
  const [pokazPodstawienie, setPokazPodstawienie] = useState(!kompakt);
  const [nadpisanie, setNadpisanie] = useState<{ kcal: string; reason: string } | null>(null);
  const [zapis, setZapis] = useState(false);
  const [blad, setBlad] = useState<string | null>(null);

  if (dane === null) return null; // moduł wyłączony
  if (error) return <div className="card"><ErrorBox error={error} onRetry={zaladuj} /></div>;
  if (dane === undefined) return null;
  if (!dane.access.ok) return null; // trener bez zgód — komunikat pokazuje zakładka Wywiad

  async function wyslijNadpisanie(kcal: number | null) {
    if (!nadpisanie) return;
    setZapis(true); setBlad(null);
    try {
      await api.put(`/api/clients/${clientId}/zapotrzebowanie/nadpisanie`, { kcal, reason: nadpisanie.reason });
      setNadpisanie(null); zaladuj();
    } catch (e) { setBlad((e as Error).message); } finally { setZapis(false); }
  }
  async function odblokuj() {
    setZapis(true); setBlad(null);
    try { await api.post(`/api/clients/${clientId}/zapotrzebowanie/odblokuj`, {}); zaladuj(); }
    catch (e) { setBlad((e as Error).message); } finally { setZapis(false); }
  }

  const e = dane.estimate;
  return (
    <div className="card" role="region" aria-label="Zapotrzebowanie kaloryczne" data-testid="zapotrzebowanie-karta">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}>Zapotrzebowanie kaloryczne</h2>
        {e && <span className="badge">wersja {e.version_no}</span>}
      </div>
      {dane.status === "none" && (
        <>
          <p className="dim" style={{ marginBottom: 6 }}>
            {tryb === "klient"
              ? "Kilka pytań o ciało, aktywność i cel — wzór policzy szacunkowe dzienne zapotrzebowanie, a trener je potwierdzi."
              : "Klient nie wypełnił jeszcze wywiadu zapotrzebowania. Możesz uzupełnić go wspólnie podczas konsultacji."}
          </p>
          {linkDoWywiadu && <Link className="btn btn--small" to={linkDoWywiadu}>Wypełnij wywiad</Link>}
          {onOtworz && <button type="button" className="btn btn--ghost btn--small" onClick={onOtworz}>Uzupełnij wspólnie</button>}
        </>
      )}
      {dane.status === "hidden" && (
        <p className="alert alert--info" role="status">{dane.message}</p>
      )}
      {dane.status === "ok" && e && (
        <>
          <p style={{ fontSize: "1.4rem", margin: "6px 0 2px" }}>
            <b data-testid="zapotrzebowanie-kcal">≈ {e.kcal_effective} kcal / dzień</b>
          </p>
          {e.override ? (
            <p className="dim" style={{ marginTop: 0 }}>
              Ustalone przez trenera ({plDateTime(e.override.at)}): {e.override.reason}. Wzór dawał {e.kcal} kcal.
            </p>
          ) : (
            <p className="dim" style={{ marginTop: 0 }}>
              Szacunek ze wzoru (PPM {e.ppm} kcal × PAL {String(e.pal).replace(".", ",")} = CPM {e.cpm} kcal
              {e.korekta_pct !== 0 ? `, korekta ${e.korekta_pct > 0 ? "+" : "−"}${Math.abs(e.korekta_pct)} %` : ""}).
              {tryb === "klient" ? " To punkt wyjścia — zalecenie potwierdza trener." : ""}
            </p>
          )}
          {e.ostrzezenia.map((o) => <p key={o} className="alert alert--warn">{o}</p>)}
          {tryb === "trener" && e.hidden_for_client && (
            <p className="alert alert--warn" role="status">
              Klient wskazał doświadczenie z zaburzeniami odżywiania (albo wolał to omówić) — liczby są przed nim ukryte.
              Po rozmowie możesz je odsłonić.
              {" "}<button type="button" className="btn btn--small" disabled={zapis} onClick={() => void odblokuj()}>Odsłoń wynik klientowi</button>
            </p>
          )}
          <button type="button" className="btn btn--ghost btn--small" aria-expanded={pokazPodstawienie}
            onClick={() => setPokazPodstawienie((v) => !v)}>
            {pokazPodstawienie ? "Ukryj podstawienie" : "Skąd ta liczba?"}
          </button>
          {pokazPodstawienie && (
            <ol style={{ fontSize: "0.9rem", paddingLeft: 20, marginBottom: 4 }} aria-label="Podstawienie do wzoru">
              {e.podstawienie.map((w) => <li key={w}>{w}</li>)}
            </ol>
          )}
          {tryb === "trener" && (
            <div style={{ marginTop: 8 }}>
              {nadpisanie ? (
                <div className="field-row" style={{ alignItems: "end" }}>
                  <div><label htmlFor="zk-nadpisz-kcal">kcal / dzień (Twoja decyzja)</label>
                    <input id="zk-nadpisz-kcal" inputMode="numeric" value={nadpisanie.kcal}
                      onChange={(ev) => setNadpisanie({ ...nadpisanie, kcal: ev.target.value })} /></div>
                  <div><label htmlFor="zk-nadpisz-powod">Powód (klient go zobaczy)</label>
                    <input id="zk-nadpisz-powod" value={nadpisanie.reason} maxLength={500}
                      onChange={(ev) => setNadpisanie({ ...nadpisanie, reason: ev.target.value })} /></div>
                  <div className="row" style={{ gap: 6 }}>
                    <button type="button" className="btn btn--small" disabled={zapis || !Number(nadpisanie.kcal) || !nadpisanie.reason.trim()}
                      onClick={() => void wyslijNadpisanie(Number(nadpisanie.kcal))}>Zapisz</button>
                    <button type="button" className="btn btn--ghost btn--small" onClick={() => setNadpisanie(null)}>Anuluj</button>
                  </div>
                </div>
              ) : (
                <div className="row" style={{ gap: 6 }}>
                  <button type="button" className="btn btn--ghost btn--small"
                    onClick={() => setNadpisanie({ kcal: String(e.kcal_effective), reason: e.override?.reason ?? "" })}>
                    {e.override ? "Zmień ustalenie" : "Nadpisz wynik"}
                  </button>
                  {e.override && (
                    <button type="button" className="btn btn--ghost btn--small" disabled={zapis}
                      onClick={() => { setNadpisanie({ kcal: "", reason: "powrót do wzoru" }); void (async () => {
                        setZapis(true); setBlad(null);
                        try { await api.put(`/api/clients/${clientId}/zapotrzebowanie/nadpisanie`, { kcal: null, reason: "powrót do wzoru" }); setNadpisanie(null); zaladuj(); }
                        catch (err) { setBlad((err as Error).message); } finally { setZapis(false); }
                      })(); }}>
                      Wróć do wzoru
                    </button>
                  )}
                  {onOtworz && <button type="button" className="btn btn--ghost btn--small" onClick={onOtworz}>Zaktualizuj wywiad wspólnie</button>}
                </div>
              )}
              {blad && <p className="alert alert--error" role="alert">{blad}</p>}
              {!kompakt && dane.history && dane.history.length > 1 && (
                <small className="dim">Historia: {dane.history.map((h) => `v${h.version_no} — ${h.kcal_effective} kcal`).join(", ")}</small>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

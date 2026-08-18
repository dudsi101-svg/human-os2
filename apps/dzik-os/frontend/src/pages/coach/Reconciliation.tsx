import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money } from "../../api";
import { localToday, plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import {
  PAYMENT_LABELS, paymentBadgeClass, ReconciliationRow, ReconciliationSummary,
} from "../../types";

interface ReconciliationData {
  month: string;
  provider: string;
  records: ReconciliationRow[];
  summary_by_currency: Record<string, ReconciliationSummary>;
}

const SOURCE_LABELS: Record<string, string> = {
  MANUAL: "adnotacja ręczna",
  PROVIDER: "operator",
  MIXED: "mieszane",
  LEGACY: "oznaczenie sprzed historii transakcji",
  NONE: "brak transakcji",
};

/** Raport pojednania: należności vs zarejestrowane transakcje/korekty per
 * okres. Dziś „operatorem" są adnotacje ręczne trenera; format jest gotowy
 * pod przyszłego operatora online (kolumna źródła, sumy per waluta). */
export default function Reconciliation() {
  const [month, setMonth] = useState(localToday().slice(0, 7));
  const [data, setData] = useState<ReconciliationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    setData(null);
    api.get<ReconciliationData>(`/api/payments/reconciliation?month=${month}`)
      .then(setData).catch((e) => setError(e.message));
  }, [month]);
  useEffect(load, [load]);

  return (
    <div className="page">
      <TopBar title="Pojednanie płatności" />
      <div className="card">
        <label htmlFor="rec-month">Okres (miesiąc terminu płatności)</label>
        <input id="rec-month" type="month" value={month}
          onChange={(e) => setMonth(e.target.value)} />
      </div>
      {error && <ErrorBox error={error} onRetry={load} />}
      {!error && !data && <Spinner />}
      {data && (
        <>
          {Object.entries(data.summary_by_currency).map(([currency, s]) => (
            <div className="card" key={currency}>
              <h2>Podsumowanie {currency}</h2>
              <div className="row" style={{ flexWrap: "wrap", gap: 12 }}>
                <div className="stat"><b>{money(s.expected_cents, currency)}</b><span>należne</span></div>
                <div className="stat"><b>{money(s.collected_cents, currency)}</b><span>zebrane</span></div>
                <div className="stat"><b>{money(s.refunded_cents, currency)}</b><span>zwroty</span></div>
                <div className="stat"><b>{money(s.adjustments_cents, currency)}</b><span>korekty</span></div>
                <div className="stat">
                  <b className={s.difference_cents < 0 ? "danger" : undefined}>
                    {money(s.difference_cents, currency)}</b>
                  <span>różnica</span>
                </div>
              </div>
              {s.legacy_marks > 0 && (
                <small className="dim">
                  {s.legacy_marks} rekord(y) oznaczone jako opłacone przed
                  wprowadzeniem rejestru transakcji — liczone po kwocie należności.
                </small>
              )}
            </div>
          ))}
          <div className="card">
            <h2>Rekordy ({data.records.length})</h2>
            {data.records.length === 0 && (
              <p className="dim">Brak należności z terminem w tym okresie.</p>
            )}
            {data.records.length > 0 && (
              <div className="table-wrap">
                <table className="simple table--cards">
                  <thead><tr>
                    <th>Klient</th><th>Termin</th><th>Status</th>
                    <th>Należne</th><th>Zebrane</th><th>Różnica</th><th>Źródło</th>
                  </tr></thead>
                  <tbody>
                    {data.records.map((r) => (
                      <tr key={r.record_id}>
                        <td data-label="Klient">
                          <Link to={`/trener/klient/${r.client_id}`}>
                            {r.client_name ?? r.client_id}
                          </Link>
                          <div className="dim" style={{ fontSize: "0.75rem" }}>{r.package_name}</div>
                        </td>
                        <td data-label="Termin">{plDate(r.due_date)}</td>
                        <td data-label="Status">
                          <span className={paymentBadgeClass(r.status)}>
                            {PAYMENT_LABELS[r.status] ?? r.status}</span>
                        </td>
                        <td data-label="Należne">{money(r.expected_cents, r.currency)}</td>
                        <td data-label="Zebrane">
                          {money(r.collected_cents, r.currency)}
                          {r.refunded_cents > 0 && (
                            <div className="dim" style={{ fontSize: "0.75rem" }}>
                              zwroty: {money(r.refunded_cents, r.currency)}
                            </div>
                          )}
                        </td>
                        <td data-label="Różnica">
                          <span className={r.difference_cents < 0 ? "danger" : undefined}>
                            {money(r.difference_cents, r.currency)}
                          </span>
                        </td>
                        <td data-label="Źródło">{SOURCE_LABELS[r.source] ?? r.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <p className="dim" style={{ fontSize: "0.78rem" }}>
            Zestawienie porównuje należności (harmonogram) z zarejestrowanymi
            transakcjami i korektami. Obecnie wszystkie wpisy pochodzą z
            adnotacji ręcznych — po podłączeniu operatora płatności online
            pojawią się tu w tej samej tabeli (kolumna „Źródło").
          </p>
        </>
      )}
    </div>
  );
}

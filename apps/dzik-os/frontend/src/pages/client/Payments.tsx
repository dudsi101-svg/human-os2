import { useEffect, useState } from "react";
import { api, getUser, money } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import {
  PAYMENT_LABELS, PAYMENT_TX_LABELS, PaymentRecordRow, PaymentScheduleRow,
  paymentBadgeClass,
} from "../../types";

/** Historia rekordu: zarejestrowane transakcje (wpłaty, zwroty, korekty) —
 * zawsze pełny ślad, wpisy odwrócone pozostają widoczne jako przekreślone. */
function RecordHistory({ record }: { record: PaymentRecordRow }) {
  if (record.transactions.length === 0 && !record.marked_at) return null;
  return (
    <div className="dim" style={{ fontSize: "0.82rem", marginTop: 4 }}>
      {record.marked_at && record.marked_by_name && (
        <div>
          Oznaczona jako opłacona przez {record.marked_by_name},{" "}
          {plDate(record.marked_at.slice(0, 10))}
          {record.note ? ` — ${record.note}` : ""}
        </div>
      )}
      {record.transactions.map((t) => (
        <div key={t.id} style={t.reversed ? { textDecoration: "line-through" } : undefined}>
          {plDate(t.created_at.slice(0, 10))} — {PAYMENT_TX_LABELS[t.kind] ?? t.kind}{" "}
          {money(Math.abs(t.amount_cents), t.currency)}
          {t.created_by_name ? ` (${t.created_by_name})` : ""}
          {t.document_ref ? `, dok. ${t.document_ref}` : ""}
          {t.reversed ? " — cofnięta" : ""}
        </div>
      ))}
    </div>
  );
}

export default function Payments() {
  const user = getUser()!;
  const [schedules, setSchedules] = useState<PaymentScheduleRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<{ schedules: PaymentScheduleRow[] }>(`/api/clients/${user.id}/payments`)
      .then((d) => setSchedules(d.schedules))
      .catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, [user.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!schedules) return <div className="page"><Spinner /></div>;

  const allRecords = schedules.flatMap((s) => s.records);
  const due = allRecords.filter((r) =>
    ["PENDING", "OVERDUE", "FAILED", "IN_PROGRESS"].includes(r.effective_status));
  const history = allRecords.filter((r) =>
    !["PENDING", "OVERDUE", "FAILED", "IN_PROGRESS", "PLANNED"].includes(r.effective_status));

  const renderRow = (r: PaymentRecordRow) => {
    const status = r.effective_status;
    return (
      <tr key={r.id}>
        <td data-label="Termin">{plDate(r.due_date)}</td>
        <td data-label="Kwota">{money(r.amount_cents, r.currency)}</td>
        <td data-label="Status">
          <span className={paymentBadgeClass(status)}>{PAYMENT_LABELS[status] ?? status}</span>
        </td>
        <td>
          {!["PAID", "REFUNDED", "PARTIALLY_REFUNDED", "CANCELLED"].includes(status)
            && r.payment_link && (
            <a href={r.payment_link} target="_blank" rel="noreferrer">Opłać</a>
          )}
        </td>
      </tr>
    );
  };

  return (
    <div className="page">
      <TopBar title="Płatności" />
      {schedules.length === 0 && <p className="dim">Brak ustawionych płatności.</p>}
      {schedules.map((s) => (
        <div className="card" key={s.schedule_id}>
          <div className="row row--between">
            <h2>{s.package_name}</h2>
            <b>{money(s.amount_cents, s.currency)}</b>
          </div>
          <small>
            {s.period === "MONTHLY" ? "rozliczenie miesięczne"
              : s.period === "WEEKLY" ? "rozliczenie tygodniowe" : "płatność jednorazowa"}
          </small>

          {s.records.some((r) => due.includes(r) || r.effective_status === "PLANNED") && (
            <>
              <h3 style={{ marginTop: 10 }}>Należności</h3>
              <div className="table-wrap">
                <table className="simple table--cards">
                  <thead><tr><th>Termin</th><th>Kwota</th><th>Status</th>
                    <th><span className="sr-only">Akcje</span></th></tr></thead>
                  <tbody>
                    {s.records
                      .filter((r) => due.includes(r) || r.effective_status === "PLANNED")
                      .map(renderRow)}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {s.records.some((r) => history.includes(r)) && (
            <>
              <h3 style={{ marginTop: 10 }}>Historia</h3>
              <div className="table-wrap">
                <table className="simple table--cards">
                  <thead><tr><th>Termin</th><th>Kwota</th><th>Status</th>
                    <th><span className="sr-only">Akcje</span></th></tr></thead>
                  <tbody>
                    {s.records.filter((r) => history.includes(r)).map(renderRow)}
                  </tbody>
                </table>
              </div>
              {s.records.filter((r) => history.includes(r)).map((r) => (
                <RecordHistory key={r.id} record={r} />
              ))}
            </>
          )}

          {!s.records.some((r) => r.payment_link) && (
            <small>Szczegóły płatności (np. numer konta) otrzymasz od trenera w wiadomości.</small>
          )}
        </div>
      ))}
      <p className="dim" style={{ fontSize: "0.8rem" }}>
        Aplikacja nie przechowuje danych kart płatniczych — jedynie terminy,
        statusy i historię rozliczeń.
      </p>
    </div>
  );
}

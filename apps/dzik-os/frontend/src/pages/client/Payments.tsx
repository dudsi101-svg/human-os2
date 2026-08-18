import { useEffect, useState } from "react";
import { api, getUser, money } from "../../api";
import { localToday, plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { PAYMENT_LABELS, PaymentScheduleRow } from "../../types";

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
  // Zaległość liczona względem LOKALNEJ daty kalendarzowej (nie UTC).
  const today = localToday();

  return (
    <div className="page">
      <TopBar title="Płatności" />
      {schedules.length === 0 && <p className="dim">Brak ustawionych płatności.</p>}
      {schedules.map((s) => (
        <div className="card" key={s.schedule_id}>
          <div className="row row--between">
            <h3>{s.package_name}</h3>
            <b>{money(s.amount_cents, s.currency)}</b>
          </div>
          <small>
            {s.period === "MONTHLY" ? "rozliczenie miesięczne"
              : s.period === "WEEKLY" ? "rozliczenie tygodniowe" : "płatność jednorazowa"}
          </small>
          <table className="simple" style={{ marginTop: 8 }}>
            <thead><tr><th>Termin</th><th>Kwota</th><th>Status</th><th /></tr></thead>
            <tbody>
              {s.records.map((r) => {
                const overdue = r.status === "PENDING" && r.due_date < today;
                const status = overdue ? "OVERDUE" : r.status;
                return (
                  <tr key={r.id}>
                    <td>{plDate(r.due_date)}</td>
                    <td>{money(r.amount_cents, r.currency)}</td>
                    <td>
                      <span className={`badge ${status === "PAID" ? "badge--ok" : status === "OVERDUE" ? "badge--danger" : "badge--warn"}`}>
                        {PAYMENT_LABELS[status]}
                      </span>
                    </td>
                    <td>
                      {status !== "PAID" && r.payment_link && (
                        <a href={r.payment_link} target="_blank" rel="noreferrer">Opłać</a>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!s.records.some((r) => r.payment_link) && (
            <small>Szczegóły płatności (np. numer konta) otrzymasz od trenera w wiadomości.</small>
          )}
        </div>
      ))}
      <p className="dim" style={{ fontSize: "0.8rem" }}>
        Aplikacja nie przechowuje danych kart płatniczych — jedynie terminy i statusy.
      </p>
    </div>
  );
}

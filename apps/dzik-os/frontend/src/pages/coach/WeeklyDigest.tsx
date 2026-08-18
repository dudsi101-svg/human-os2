import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { plDate, plDateTime } from "../../dates";
import { ErrorBox, Icon, Spinner, TopBar } from "../../components";
import { WeeklyDigestData, WeeklyDigestRow } from "../../types";

/** Podsumowanie tygodnia trenera — metadane operacyjne WŁASNEJ pracy:
 *  kto zaraportował, co czeka na ocenę, kto zalega, gdzie zgłoszono coś
 *  niepokojącego i jakie konsultacje są umówione.
 *
 *  Zasada Human OS: to nie jest ranking podopiecznych. Nie ma punktów,
 *  ocen ani porównań między ludźmi — grupy są uporządkowane alfabetycznie,
 *  a liczby opisują pracę trenera, nie „wynik" klienta. */
export default function WeeklyDigest() {
  const [data, setData] = useState<WeeklyDigestData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<WeeklyDigestData>("/api/coach/weekly-digest")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  if (error) {
    return (
      <div className="page page--wide">
        <TopBar title="Podsumowanie tygodnia" />
        <ErrorBox error={error} onRetry={load} />
      </div>
    );
  }
  if (!data) {
    return (
      <div className="page page--wide">
        <TopBar title="Podsumowanie tygodnia" />
        <Spinner />
      </div>
    );
  }

  const nothingPending =
    data.awaiting_review.length === 0 &&
    data.checkin_overdue.length === 0 &&
    data.payment_overdue.length === 0 &&
    data.flagged.length === 0;

  return (
    <div className="page page--wide">
      <TopBar title="Podsumowanie tygodnia" />
      <p className="dim" style={{ marginTop: 0 }}>
        Tydzień od {plDate(data.week_start)} · {data.active_clients}{" "}
        {data.active_clients === 1 ? "aktywna współpraca" : "aktywnych współprac"}
      </p>

      {nothingPending && (
        <div className="alert alert--info" role="status">
          Nic nie czeka na Twoją reakcję — wszystkie raporty ocenione,
          płatności i zgłoszenia bez zaległości.
        </div>
      )}

      <DigestGroup
        title="Raporty do oceny"
        icon="report"
        rows={data.awaiting_review}
        empty="Brak raportów czekających na ocenę."
      />
      <DigestGroup
        title="Zaraportowali w tym tygodniu"
        icon="check"
        rows={data.reported_this_week}
        empty="Nikt jeszcze nie wysłał raportu w tym tygodniu."
      />
      <DigestGroup
        title="Zaległe raporty"
        icon="warn"
        rows={data.checkin_overdue}
        empty="Brak zaległych raportów."
      />
      <DigestGroup
        title="Zaległe płatności"
        icon="card"
        rows={data.payment_overdue}
        empty="Brak zaległych płatności."
        // Data ostatniego raportu nie ma tu nic do rzeczy — podpis
        // „brak raportów" pod zaległą płatnością tylko myli.
        showLastCheckin={false}
      />

      <div className="card">
        <h2><Icon name="info" size={18} /> Zgłoszenia wymagające uwagi</h2>
        {data.flagged.length === 0 && (
          <p className="dim">Brak zgłoszeń bólu i niepokojących obserwacji.</p>
        )}
        {data.flagged.map((row) => (
          <div className="exercise" key={row.client_id}>
            <div>
              <Link to={`/trener/klient/${row.client_id}`}>{row.display_name}</Link>
              <div className="meta">
                {row.recent_pain_reports > 0 && (
                  <>zgłoszenia bólu: {row.recent_pain_reports}</>
                )}
                {row.recent_pain_reports > 0 && row.flagged_observations > 0 && " · "}
                {row.flagged_observations > 0 && (
                  <>niepokojące obserwacje: {row.flagged_observations}</>
                )}
                {" "}· ostatnie 14 dni
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2><Icon name="calendar" size={18} /> Nadchodzące konsultacje</h2>
        {data.upcoming_consultations.length === 0 && (
          <p className="dim">Brak umówionych konsultacji.</p>
        )}
        {data.upcoming_consultations.map((slot) => (
          <div className="exercise" key={slot.id}>
            <div>
              <b>{plDateTime(slot.starts_at)}</b>
              <div className="meta">
                {slot.client_name ?? "wolny termin"} · {slot.duration_min} min
              </div>
            </div>
          </div>
        ))}
        <div style={{ marginTop: 8 }}>
          <Link className="btn btn--ghost btn--small" to="/trener/konsultacje">
            Terminarz konsultacji
          </Link>
        </div>
      </div>

      <p className="dim" style={{ fontSize: "0.8rem" }}>
        Zestawienie opisuje pracę do wykonania, a nie ludzi: nie ma tu
        punktacji ani porównań między podopiecznymi. Te same liczby widzisz
        na pulpicie i w karcie klienta.
      </p>
    </div>
  );
}

function DigestGroup({ title, icon, rows, empty, showLastCheckin = true }: {
  title: string;
  icon: string;
  rows: WeeklyDigestRow[];
  empty: string;
  /** Podpis z ostatnim raportem ma sens tylko dla grup raportowych. */
  showLastCheckin?: boolean;
}) {
  return (
    <div className="card">
      <div className="row row--between">
        <h2><Icon name={icon} size={18} /> {title}</h2>
        {rows.length > 0 && <span className="badge badge--accent">{rows.length}</span>}
      </div>
      {rows.length === 0 && <p className="dim">{empty}</p>}
      {rows.map((row) => (
        <div className="exercise" key={row.client_id}>
          <div>
            <Link to={`/trener/klient/${row.client_id}`}>{row.display_name}</Link>
            {showLastCheckin && (
              <div className="meta">
                {row.last_checkin_week
                  ? `ostatni raport: tydzień ${plDate(row.last_checkin_week)}`
                  : "brak raportów"}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

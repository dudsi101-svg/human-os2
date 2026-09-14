import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { PostepyKlientTrenera } from "../../types";
import { KafelkiTygodnia, SekcjaKonsekwencja, SekcjaRekordy, SekcjaSylwetka, SekcjaTrening } from "./PanelPostepow";

/* Widok pojedynczego klienta w Monitoringu (0.66.0, §7.2): ten sam układ co u
   klienta + pełne dane niezależnie od flag klienta (filtrowanie dotyczy tylko
   roli klienta), surowe pomiary z przełącznikiem średniej, notatki trenera,
   zmiany planu na tle tonażu. */
export default function KlientMonitoring() {
  const { clientId } = useParams();
  const [dane, setDane] = useState<PostepyKlientTrenera | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wersja, setWersja] = useState(0);
  useEffect(() => {
    setError(null);
    api.get<PostepyKlientTrenera>(`/api/monitoring/clients/${clientId}`).then(setDane).catch((e) => setError(e.message));
  }, [clientId, wersja]);
  return (
    <div className="page">
      <TopBar title="Monitoring klienta" right={<Link className="btn btn--ghost btn--small" to="/monitoring">← Lista</Link>} />
      <ErrorBox error={error} onRetry={() => setWersja((w) => w + 1)} />
      {!dane && !error && <Spinner />}
      {dane && (
        <>
          {/* `health_flag` przychodzi tylko ze zgodą na dane zdrowotne (razem z `body`). */}
          {dane.health_flag && dane.body && (
            <p className="alert alert--info" role="status">
              Klient ma flagę zdrowotną z wywiadu: w jego aplikacji sekcja „Sylwetka” i trend wagi są ukryte. Ty widzisz pełne dane.
            </p>
          )}
          <p><Link to={`/trener/klient/${clientId}`}>Karta klienta</Link></p>
          <KafelkiTygodnia s={dane.summary} />
          <SekcjaRekordy r={dane.records} />
          <SekcjaTrening t={dane.training} planChanges={dane.plan_changes} />
          <SekcjaKonsekwencja s={dane.summary} t={dane.training} />
          {dane.body && (
            <SekcjaSylwetka b={dane.body} tryb="trener">
              {dane.notes && dane.notes.length > 0 && (
                <>
                  <h3>Notatki trenera</h3>
                  <ul style={{ paddingLeft: 18, margin: "4px 0" }}>
                    {dane.notes.map((n, i) => <li key={i}><small><b>{plDate(n.date)}</b> · {n.text}</small></li>)}
                  </ul>
                </>
              )}
            </SekcjaSylwetka>
          )}
        </>
      )}
    </div>
  );
}

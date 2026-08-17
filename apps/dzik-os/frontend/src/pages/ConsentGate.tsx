import { useEffect, useState } from "react";
import { api, plDate } from "../api";
import { ErrorBox, Logo, Spinner } from "../components";
import { ConsentRow } from "../types";

/** Brama zgód: klient przy pierwszym logowaniu widzi zgody zarejestrowane
 *  przy onboardingu i musi je jawnie potwierdzić (albo cofnąć). Decyzja
 *  o dostępie i tak zapada w backendzie — ta strona tylko zbiera
 *  świadome potwierdzenie podmiotu danych. */
export default function ConsentGate({
  pending,
  onResolved,
}: {
  pending: ConsentRow[];
  onResolved: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirmAll() {
    setBusy(true);
    setError(null);
    try {
      for (const c of pending) {
        await api.post(`/api/me/consents/${c.id}/confirm`);
      }
      onResolved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function revokeAll() {
    if (!confirm(
      "Bez zgody trener nie będzie widzieć Twoich danych i nie poprowadzi " +
      "współpracy w aplikacji. Na pewno odmówić?"
    )) return;
    setBusy(true);
    try {
      for (const c of pending) {
        await api.post(`/api/me/consents/${c.id}/revoke`);
      }
      onResolved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="row" style={{ justifyContent: "center", marginBottom: 18 }}>
          <Logo size={44} />
          <h1>Twoje dane, Twoja zgoda</h1>
        </div>
        <div className="card">
          <p style={{ marginTop: 0 }}>
            Aby trener mógł prowadzić Cię w aplikacji, potrzebuje dostępu do
            danych, które podasz (m.in. pomiary, raporty, zdjęcia, informacje
            o zdrowiu). Przy zakładaniu konta zarejestrowano poniższe zgody —
            potwierdź je, aby korzystać z aplikacji:
          </p>
          {pending.map((c) => (
            <div className="exercise" key={c.id}>
              <div>
                <b>{c.grantee_name ?? c.grantee_id}</b>
                <div className="meta">
                  cel: prowadzenie trenerskie · zakres: dane zdrowotne
                  {" "}· zarejestrowana {plDate(c.granted_at)}
                </div>
              </div>
            </div>
          ))}
          <ul style={{ fontSize: "0.85rem", color: "var(--text-dim)", paddingLeft: 18 }}>
            <li>zgodę możesz cofnąć w każdej chwili (Profil → Zgody);</li>
            <li>cofnięcie działa natychmiast — trener traci dostęp;</li>
            <li>możesz wyeksportować i usunąć swoje dane;</li>
            <li>dane nie są nikomu dalej przekazywane.</li>
          </ul>
          <ErrorBox error={error} />
          <button className="btn" onClick={confirmAll} disabled={busy}>
            Potwierdzam zgodę
          </button>
          <div style={{ marginTop: 8 }}>
            <button className="btn btn--danger" onClick={revokeAll} disabled={busy}>
              Nie wyrażam zgody
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Hak: pobiera zgody klienta i zwraca te wymagające potwierdzenia. */
export function usePendingConsents(enabled: boolean) {
  const [pending, setPending] = useState<ConsentRow[] | null>(enabled ? null : []);
  const reload = () => {
    api.get<{ consents: ConsentRow[] }>("/api/me/consents")
      .then((d) =>
        setPending(d.consents.filter((c) => !c.revoked_at && !c.confirmed_at))
      )
      .catch(() => setPending([]));
  };
  useEffect(() => {
    if (enabled) reload();
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps
  return { pending, reload };
}

export function ConsentSpinner() {
  return <div className="page"><Spinner /></div>;
}

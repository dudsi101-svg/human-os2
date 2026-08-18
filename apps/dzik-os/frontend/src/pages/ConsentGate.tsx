import { useEffect, useState } from "react";
import { api } from "../api";
import { plDate } from "../dates";
import { ErrorBox, Logo, Spinner } from "../components";
import { ConsentCategoryInfo, ConsentRow, ConsentsResponse } from "../types";

/** Pełny opis kategorii zgody (cel / zakres / odbiorcy / okres /
 *  dobrowolność / wycofanie / podstawa / wersja) — wspólny dla bramy
 *  zgód i Profilu. Nic nie jest ukryte za „szczegółami prawnymi":
 *  najważniejsze pola widać od razu, reszta w rozwijanym bloku. */
export function ConsentDetails({ cat }: { cat: ConsentCategoryInfo }) {
  return (
    <details className="consent-details" style={{ marginTop: 6 }}>
      <summary style={{ cursor: "pointer", fontSize: "0.85rem" }}>
        Pełna informacja: cel, zakres, odbiorcy, okres, wycofanie
      </summary>
      <dl style={{ fontSize: "0.82rem", color: "var(--text-dim)", margin: "6px 0 0" }}>
        <dt><b>Cel</b></dt><dd>{cat.cel}</dd>
        <dt><b>Zakres danych</b></dt><dd>{cat.zakres}</dd>
        <dt><b>Odbiorcy</b></dt><dd>{cat.odbiorcy}</dd>
        <dt><b>Okres przechowywania</b></dt><dd>{cat.okres}</dd>
        <dt><b>Dobrowolność</b></dt><dd>{cat.dobrowolnosc}</dd>
        <dt><b>Wycofanie</b></dt><dd>{cat.wycofanie}</dd>
        <dt><b>Podstawa prawna</b></dt><dd>{cat.legal_basis}</dd>
        <dt><b>Wersja dokumentu</b></dt><dd>{cat.document_version}</dd>
      </dl>
    </details>
  );
}

/** Brama zgód: klient przy pierwszym logowaniu widzi deklaracje
 *  zarejestrowane przy onboardingu — OSOBNO warunki wymagane do
 *  współpracy (jedna umowa, potwierdzane razem) i OSOBNO każdą zgodę
 *  opcjonalną (indywidualna decyzja Tak/Nie; żadnego „zaakceptuj
 *  wszystko" dla niezależnych celów). Decyzja o dostępie i tak zapada
 *  w backendzie — ta strona zbiera świadome decyzje podmiotu danych. */
export default function ConsentGate({
  pending,
  catalog,
  onResolved,
}: {
  pending: ConsentRow[];
  catalog: ConsentCategoryInfo[];
  onResolved: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const byKey = Object.fromEntries(catalog.map((c) => [c.key, c]));
  const requiredPending = pending.filter(
    (c) => c.category && byKey[c.category]?.required
  );
  const optionalPending = pending.filter(
    (c) => !c.category || !byKey[c.category]?.required
  );

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  /** Warunki wymagane (wszystkie: podstawa umowna — jedna współpraca),
   *  potwierdzane łącznie jako przyjęcie warunków tej samej umowy. */
  const confirmRequired = () =>
    run(async () => {
      for (const c of requiredPending) {
        await api.post(`/api/me/consents/${c.id}/confirm`);
      }
      onResolved();
    });

  const refuseRequired = () => {
    if (!confirm(
      "Bez tych warunków trener nie może prowadzić współpracy w aplikacji " +
      "(nie zobaczy Twoich danych). Na pewno odmówić?"
    )) return;
    run(async () => {
      for (const c of requiredPending) {
        await api.post(`/api/me/consents/${c.id}/revoke`);
      }
      onResolved();
    });
  };

  const confirmOne = (c: ConsentRow) =>
    run(async () => {
      await api.post(`/api/me/consents/${c.id}/confirm`);
      onResolved();
    });

  const refuseOne = (c: ConsentRow) =>
    run(async () => {
      await api.post(`/api/me/consents/${c.id}/revoke`);
      if (c.category) {
        // Zapisz jawną odmowę w historii (opcjonalna kategoria).
        await api.post(`/api/me/consents/decline`, {
          category: c.category, grantee_id: c.grantee_id,
        });
      }
      onResolved();
    });

  const label = (c: ConsentRow) =>
    (c.category && byKey[c.category]?.label) || `${c.purpose}/${c.domain}`;

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="row" style={{ justifyContent: "center", marginBottom: 18 }}>
          <Logo size={44} />
          <h1>Twoje dane, Twoja zgoda</h1>
        </div>

        {requiredPending.length > 0 && (
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Wymagane do współpracy</h3>
            <p style={{ fontSize: "0.9rem" }}>
              Te punkty wynikają z umowy o prowadzenie trenerskie (jedna
              współpraca — potwierdzasz je razem). Bez nich aplikacja nie
              może świadczyć usługi.
            </p>
            {requiredPending.map((c) => (
              <div className="exercise" key={c.id}>
                <div style={{ width: "100%" }}>
                  <b>{label(c)}</b>
                  <div className="meta">
                    odbiorca: {c.grantee_name ?? c.grantee_id} · zarejestrowana{" "}
                    {plDate(c.granted_at)}
                  </div>
                  {c.category && byKey[c.category] && (
                    <ConsentDetails cat={byKey[c.category]} />
                  )}
                </div>
              </div>
            ))}
            <button className="btn" onClick={confirmRequired} disabled={busy}>
              Potwierdzam warunki wymagane
            </button>
            <div style={{ marginTop: 8 }}>
              <button className="btn btn--danger btn--small" onClick={refuseRequired} disabled={busy}>
                Nie wyrażam zgody (kończy współpracę w aplikacji)
              </button>
            </div>
          </div>
        )}

        {optionalPending.length > 0 && (
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Zgody opcjonalne — zdecyduj o każdej osobno</h3>
            <p style={{ fontSize: "0.9rem" }}>
              Każda z tych zgód dotyczy innego celu i jest w pełni
              dobrowolna. Odmowa nie blokuje pozostałych funkcji aplikacji.
            </p>
            {optionalPending.map((c) => (
              <div className="exercise" key={c.id}>
                <div style={{ width: "100%" }}>
                  <b>{label(c)}</b>
                  <div className="meta">
                    odbiorca: {c.grantee_name ?? c.grantee_id} · zarejestrowana{" "}
                    {plDate(c.granted_at)}
                  </div>
                  {c.category && byKey[c.category] && (
                    <ConsentDetails cat={byKey[c.category]} />
                  )}
                  <div className="row" style={{ marginTop: 8 }}>
                    <button className="btn btn--small" onClick={() => confirmOne(c)} disabled={busy}>
                      Wyrażam zgodę
                    </button>
                    <button className="btn btn--ghost btn--small" onClick={() => refuseOne(c)} disabled={busy}>
                      Odmawiam
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="card">
          <ul style={{ fontSize: "0.85rem", color: "var(--text-dim)", paddingLeft: 18, margin: 0 }}>
            <li>każdą zgodę możesz cofnąć w każdej chwili (Profil → Prywatność i zgody);</li>
            <li>cofnięcie działa natychmiast — trener traci dostęp do danych tej kategorii;</li>
            <li>możesz wyeksportować i usunąć swoje dane;</li>
            <li>
              dane przetwarzają wyłącznie podmioty opisane w polityce
              prywatności (m.in. hosting w UE) — szczegóły w opisie każdej
              zgody powyżej.
            </li>
          </ul>
          <ErrorBox error={error} />
        </div>
      </div>
    </div>
  );
}

/** Hak: pobiera zgody klienta i zwraca te wymagające decyzji podmiotu
 *  (niepotwierdzone, niecofnięte, bez jawnej odmowy) + katalog opisów. */
export function usePendingConsents(enabled: boolean) {
  const [pending, setPending] = useState<ConsentRow[] | null>(enabled ? null : []);
  const [catalog, setCatalog] = useState<ConsentCategoryInfo[]>([]);
  const reload = () => {
    api.get<ConsentsResponse>("/api/me/consents")
      .then((d) => {
        setCatalog(d.catalog);
        setPending(
          d.consents.filter((c) => !c.revoked_at && !c.confirmed_at && !c.denied_at)
        );
      })
      .catch(() => setPending([]));
  };
  useEffect(() => {
    if (enabled) reload();
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps
  return { pending, catalog, reload };
}

export function ConsentSpinner() {
  return <div className="page"><Spinner /></div>;
}

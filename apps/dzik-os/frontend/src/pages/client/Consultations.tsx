import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { ConsultSlotRow } from "../../types";

const fmt = (startsAt: string) => {
  const d = new Date(startsAt);
  return d.toLocaleString("pl-PL", {
    weekday: "short", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit",
  });
};

export default function Consultations() {
  const [data, setData] = useState<{ open: ConsultSlotRow[]; booked: ConsultSlotRow[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.get<{ open: ConsultSlotRow[]; booked: ConsultSlotRow[] }>("/api/me/consult-slots")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function book(id: string) {
    setBusy(id);
    setError(null);
    try {
      await api.post(`/api/consult-slots/${id}/book`);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function unbook(id: string) {
    setBusy(id);
    setError(null);
    try {
      await api.post(`/api/consult-slots/${id}/unbook`);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (error && !data) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!data) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Konsultacje" />
      <ErrorBox error={error} />

      {data.booked.length > 0 && (
        <>
          <h2>Twoje rezerwacje</h2>
          {data.booked.map((s) => (
            <div className="card card--accent" key={s.id}>
              <div className="row row--between">
                <div>
                  <b>{fmt(s.starts_at)}</b>
                  <div className="meta">{s.duration_min} min rozmowy z trenerem</div>
                </div>
                <button className="btn btn--ghost btn--small" disabled={busy === s.id}
                  onClick={() => unbook(s.id)}>
                  Odwołaj
                </button>
              </div>
            </div>
          ))}
          <p className="dim" style={{ fontSize: "0.8rem" }}>
            Rezerwację możesz odwołać do 12 h przed terminem — później napisz
            do trenera wiadomość.
          </p>
        </>
      )}

      <h2>Wolne terminy</h2>
      {data.open.length === 0 && (
        <p className="dim">
          Trener nie wystawił jeszcze wolnych terminów. Zajrzyj później albo
          napisz wiadomość.
        </p>
      )}
      {data.open.map((s) => (
        <div className="card" key={s.id}>
          <div className="row row--between">
            <div>
              <b>{fmt(s.starts_at)}</b>
              <div className="meta">{s.duration_min} min</div>
            </div>
            <button className="btn btn--small" disabled={busy === s.id}
              onClick={() => book(s.id)}>
              {busy === s.id ? "…" : "Rezerwuję"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

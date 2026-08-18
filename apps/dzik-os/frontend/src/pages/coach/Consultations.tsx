import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, LogoutButton, Spinner, TopBar } from "../../components";
import { ConsultSlotRow } from "../../types";

const fmt = (startsAt: string) => {
  const d = new Date(startsAt);
  return d.toLocaleString("pl-PL", {
    weekday: "short", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit",
  });
};

export default function Consultations() {
  const [slots, setSlots] = useState<ConsultSlotRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [duration, setDuration] = useState("30");

  const load = useCallback(() => {
    api.get<{ slots: ConsultSlotRow[] }>("/api/coach/consult-slots")
      .then((d) => setSlots(d.slots))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function create(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/coach/consult-slots", {
        starts_at: `${date}T${time}`, duration_min: Number(duration),
      });
      setDate("");
      setTime("");
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function cancel(id: string) {
    await api.post(`/api/coach/consult-slots/${id}/cancel`);
    load();
  }

  if (error && !slots) return <div className="page"><ErrorBox error={error} /></div>;
  if (!slots) return <div className="page"><Spinner /></div>;

  const upcoming = slots.filter((s) => s.starts_at > new Date().toISOString().slice(0, 16));

  return (
    <div className="page">
      <TopBar title="Konsultacje" right={<LogoutButton />} />
      <p className="dim" style={{ marginTop: -8 }}>
        Wystaw wolne terminy — klienci rezerwują je w aplikacji. Rezerwacja
        jest zawsze odwoływalna (klient do 12 h przed terminem, Ty w każdej
        chwili z powiadomieniem).
      </p>
      <form className="card" onSubmit={create}>
        <h3>Nowy termin</h3>
        <div className="field-row">
          <div>
            <label>Data</label>
            <input type="date" required value={date}
              onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label>Godzina</label>
            <input type="time" required value={time}
              onChange={(e) => setTime(e.target.value)} />
          </div>
        </div>
        <label>Czas trwania</label>
        <select value={duration} onChange={(e) => setDuration(e.target.value)}>
          <option value="15">15 min</option>
          <option value="30">30 min</option>
          <option value="45">45 min</option>
          <option value="60">60 min</option>
        </select>
        <ErrorBox error={error} />
        <div style={{ marginTop: 10 }}>
          <button className="btn btn--small">Dodaj termin</button>
        </div>
      </form>

      <h2>Nadchodzące terminy</h2>
      {upcoming.length === 0 && <p className="dim">Brak terminów — dodaj pierwszy powyżej.</p>}
      {upcoming.map((s) => (
        <div className="card" key={s.id}>
          <div className="row row--between">
            <div>
              <b>{fmt(s.starts_at)}</b>
              <div className="meta">
                {s.duration_min} min
                {s.client_name && ` · ${s.client_name}`}
              </div>
            </div>
            <div className="row">
              <span className={`badge ${s.status === "BOOKED" ? "badge--accent" : ""}`}>
                {s.status === "BOOKED" ? "zarezerwowany" : "wolny"}
              </span>
              <button className="btn btn--danger btn--small" onClick={() => cancel(s.id)}>
                Odwołaj
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

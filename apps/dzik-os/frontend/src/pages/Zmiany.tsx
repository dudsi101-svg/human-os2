import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, getUser } from "../api";
import { plDate } from "../dates";
import { ErrorBox, Spinner, TopBar } from "../components";
import { ZestawZmian } from "../types";
import { ListaRoznic } from "./coach/SzkicPlanu";

/**
 * „Zobacz zmiany” (0.58.0): jedna publikacja = jedno podsumowanie.
 * Pokazuje przed/po, autora, czas publikacji, notatkę trenera i link do
 * aktualnego planu. Usunięte elementy pozostają tu czytelne, choć nie ma
 * ich w bieżącym planie. Otwarcie wpisu oznacza „przeczytane” — nie
 * „zaakceptowane” ani „zastosowane”.
 */
export default function Zmiany() {
  const { id } = useParams<{ id: string }>();
  const [z, setZ] = useState<ZestawZmian | null>(null);
  const [error, setError] = useState<string | null>(null);
  const user = getUser();

  const load = () => {
    setError(null);
    api.get<ZestawZmian>(`/api/zmiany/${id}`).then(setZ).catch((e) => setError(e.message));
  };
  useEffect(load, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="page"><TopBar title="Zmiany planu" /><ErrorBox error={error} onRetry={load} /></div>;
  if (!z) return <div className="page"><TopBar title="Zmiany planu" /><Spinner /></div>;
  const trener = user?.id === z.author_id;
  const nowsza = (z.current_version_no ?? z.new_version_no) > z.new_version_no;
  return (
    <div className="page">
      <TopBar title="Zmiany planu" />
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{z.plan_title}</h2>
        <p className="dim" style={{ fontSize: "0.85rem" }}>
          {z.plan_kind === "training" ? "Plan treningowy" : "Plan żywieniowy"} · wersja {z.old_version_no} → <b>{z.new_version_no}</b> ·
          opublikowano {plDate(z.published_at)} · autor: {trener ? "Ty" : "trener"} · obowiązuje od publikacji
        </p>
        <p><b>{z.summary}</b></p>
        {z.note && (
          <p className="alert alert--info" style={{ whiteSpace: "pre-wrap" }}><b>Co i dlaczego zmieniłem:</b> {z.note}</p>
        )}
        {z.diff && <ListaRoznic r={z.diff} />}
        {nowsza && (
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Od tej publikacji plan zmienił się ponownie (aktualna wersja {z.current_version_no}) — to podsumowanie pozostaje historią.
          </p>
        )}
        <div className="row" style={{ marginTop: 10, gap: 8 }}>
          <Link className="btn btn--small" to={z.plan_url ?? "/plan"}>Otwórz aktualny plan</Link>
        </div>
        {trener && z.notification && (
          <p className="dim" style={{ fontSize: "0.8rem", marginTop: 10 }}>
            Wpis klienta utworzony {plDate(z.notification.created_at)} ·
            {z.notification.read_at ? ` odczytany ${plDate(z.notification.read_at)}` : " jeszcze nieodczytany"}
            {z.notification.channels?.includes("push") ? " · push wysłany (to nie dowód odczytu)" : ""}
          </p>
        )}
        {trener && !z.notification && z.client_id && (
          <p className="dim" style={{ fontSize: "0.8rem", marginTop: 10 }}>Wpis klienta jeszcze nie został doręczony — zostanie ponowiony automatycznie.</p>
        )}
      </div>
    </div>
  );
}

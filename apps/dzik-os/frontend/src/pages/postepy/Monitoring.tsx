import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { PostepyKlientSygnaly, PostepyProgi, SYGNAL_LEVEL_LABELS } from "../../types";

/* Monitoring trenera (0.66.0, §7.1): lista klientów z sygnałami, sortowana po
   priorytecie; progi konfigurowalne. Sygnał pozytywny (nowy rekord) obok
   negatywnych — powód do kontaktu, nie ocena. Bez rankingów między ludźmi. */
const POLA: [keyof PostepyProgi, string][] = [
  ["dni_bez_treningu", "Brak treningu (dni)"], ["frekwencja_pct", "Frekwencja poniżej (%)"],
  ["dni_bez_wazenia", "Brak ważeń (dni)"], ["spadek_tonazu_pct", "Spadek tonażu (%)"],
  ["trend_wzrost_kg", "Trend + przy redukcji (kg/tydz.)"], ["dni_rekordu", "Nowy rekord (dni)"],
];

export default function Monitoring() {
  const [dane, setDane] = useState<{ clients: PostepyKlientSygnaly[]; thresholds: PostepyProgi } | null>(null);
  // Pola progów jako tekst (przecinek dozwolony, „0.” w trakcie pisania nie znika);
  // do zapytania trafiają dopiero po 300 ms ciszy i tylko poprawne liczby.
  const [progi, setProgi] = useState<Partial<Record<keyof PostepyProgi, string>>>({});
  const [zapytanie, setZapytanie] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [wersja, setWersja] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => {
      const q = Object.entries(progi)
        .map(([k, v]) => [k, (v ?? "").replace(",", ".").trim()] as const)
        .filter(([, v]) => v !== "" && !Number.isNaN(Number(v)))
        .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
      setZapytanie(q);
    }, 300);
    return () => clearTimeout(t);
  }, [progi]);
  useEffect(() => {
    let aktywne = true;
    setError(null);
    api.get<{ clients: PostepyKlientSygnaly[]; thresholds: PostepyProgi }>(`/api/monitoring/clients${zapytanie ? `?${zapytanie}` : ""}`)
      .then((d) => { if (aktywne) setDane(d); })
      .catch((e) => { if (aktywne) setError((e as Error).message); });
    return () => { aktywne = false; };
  }, [zapytanie, wersja]);
  return (
    <div className="page">
      <TopBar title="Monitoring" />
      <ErrorBox error={error} onRetry={() => setWersja((w) => w + 1)} />
      <details className="card">
        <summary>Progi sygnałów <small className="dim">(zmiana działa do końca sesji, nie zapisuje się)</small></summary>
        {dane && (
          <div className="postepy-progi" style={{ marginTop: 8 }}>
            {POLA.map(([k, label]) => (
              <label key={k}>{label}
                <input inputMode="decimal" value={progi[k] ?? String(dane.thresholds[k])}
                  onChange={(e) => setProgi({ ...progi, [k]: e.target.value })} />
              </label>
            ))}
          </div>
        )}
      </details>
      {!dane && !error && <Spinner />}
      {dane && dane.clients.length === 0 && <p className="dim">Brak aktywnych klientów.</p>}
      {dane && dane.clients.map((c) => (
        <Link className="card card--nav" to={`/monitoring/klient/${c.client_id}`} key={c.client_id}
          style={{ borderColor: c.signals.some((s) => s.level === "high") ? "var(--warn)" : undefined }}>
          <div className="row row--between">
            <b>{c.display_name}</b>
            <small className="dim">{c.last_activity ? `ostatnia aktywność ${plDate(c.last_activity)}` : "brak aktywności"}</small>
          </div>
          <small className="dim">
            {c.attendance_4w
              ? <>Frekwencja 4 tyg.: {c.attendance_4w.pct !== null ? `${c.attendance_4w.pct} % (${c.attendance_4w.done}/${c.attendance_4w.planned})` : `${c.attendance_4w.done} treningów (bez planu)`}</>
              : "Brak zgody na dane treningowe"}
            {c.consents.health && <> · trend wagi: {c.weight_trend_kg_week !== null ? `${c.weight_trend_kg_week > 0 ? "+" : ""}${c.weight_trend_kg_week} kg/tydz.` : "za mało danych"}</>}
          </small>
          <div className="postepy-sygnaly" style={{ marginTop: 4 }}>
            {c.signals.length === 0 && <span className="badge badge--ok">bez sygnałów</span>}
            {c.signals.map((s) => (
              <span key={s.key} className={`badge ${s.level === "high" ? "badge--warn" : s.level === "info" ? "badge--accent" : ""}`}
                title={`Priorytet: ${SYGNAL_LEVEL_LABELS[s.level]}`}>{s.label}</span>
            ))}
          </div>
        </Link>
      ))}
    </div>
  );
}

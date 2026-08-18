import { ReactNode, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { api, clearSession, fetchFileBlob, fetchFileUrl, getUser, plDate } from "./api";
import { applyUpdate, onUpdateAvailable } from "./pwa";
import { KIND_LABELS, PersonalRecordsData, StrengthSeriesRow } from "./types";

/** Głowa dzika — marka Dzik OS. */
export function Logo({ size = 26 }: { size?: number }) {
  return (
    <img
      src="/icons/boar-mark.png"
      alt=""
      width={size}
      height={size}
      style={{ width: size, height: size, objectFit: "contain" }}
    />
  );
}

const icons: Record<string, ReactNode> = {
  today: <path d="M8 2v4M16 2v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" />,
  plan: <path d="M6.5 6.5v11M17.5 6.5v11M3 9v6M21 9v6M6.5 12h11" />,
  diet: <path d="M12 3a7 7 0 0 1 7 7c0 5-3 8-7 11-4-3-7-6-7-11a7 7 0 0 1 7-7zM12 7v5" />,
  report: <path d="M9 3h6l1 2h3v16H5V5h3l1-2zM9 12l2 2 4-4" />,
  msg: <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z" />,
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" strokeWidth="3" />,
  clients: <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />,
  templates: <path d="M4 4h16v4H4zM4 12h10v8H4zM18 12h2v8h-2z" />,
  knowledge: <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22.5v-18z" />,
};

export function Icon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" width="22" height="22" aria-hidden>
      {icons[name] ?? icons.more}
    </svg>
  );
}

export function Nav() {
  const user = getUser();
  const roles = user?.roles ?? [];
  const items = roles.includes("COACH")
    ? [
        { to: "/trener", label: "Klienci", icon: "clients" },
        { to: "/trener/szablony", label: "Szablony", icon: "templates" },
        { to: "/trener/wiedza", label: "Wiedza", icon: "knowledge" },
        { to: "/wiadomosci", label: "Wiadomości", icon: "msg" },
        { to: "/wiecej", label: "Więcej", icon: "more" },
      ]
    : roles.includes("ADMIN")
      ? [
          { to: "/admin", label: "Konta", icon: "clients" },
          { to: "/wiecej", label: "Więcej", icon: "more" },
        ]
      : [
          { to: "/", label: "Dzisiaj", icon: "today" },
          { to: "/plan", label: "Plan", icon: "plan" },
          { to: "/dieta", label: "Dieta", icon: "diet" },
          { to: "/raport", label: "Raport", icon: "report" },
          { to: "/wiecej", label: "Więcej", icon: "more" },
        ];
  return (
    <nav className="nav">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.to === "/" || i.to === "/trener"}
          className={({ isActive }) => (isActive ? "active" : "")}>
          <Icon name={i.icon} />
          <span>{i.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

/** Baner "nowa wersja dostępna" — użytkownik decyduje, kiedy odświeżyć,
 * zamiast dostać podmieniony kod aplikacji bez ostrzeżenia w trakcie pracy. */
export function UpdateBanner() {
  const [available, setAvailable] = useState(false);
  useEffect(() => onUpdateAvailable(() => setAvailable(true)), []);
  if (!available) return null;
  return (
    <div className="update-banner">
      <span>🐗 Dostępna nowa wersja Dzik OS</span>
      <button className="btn btn--small" onClick={applyUpdate}>Odśwież</button>
    </div>
  );
}

export function TopBar({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <div className="topbar">
      <div className="brand">
        <Logo />
        <div>
          <h1>{title}</h1>
        </div>
      </div>
      {right}
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="alert alert--error">{error}</div>;
}

export function Spinner() {
  return <p className="dim">Wczytywanie…</p>;
}

/** Numerowany nagłówek sekcji formularza/przeglądu — dzieli treść na
 * jasne bloki zamiast jednej długiej listy pól (raporty, formularze). */
export function SectionLabel({ n, title }: { n: number; title: string }) {
  return (
    <div className="section-label">
      <span className="section-label__num">{n}</span>
      <span>{title}</span>
    </div>
  );
}

export function LogoutButton() {
  return (
    <button
      className="btn btn--ghost btn--small"
      onClick={async () => {
        try {
          await fetch("/api/auth/logout", { method: "POST" });
        } finally {
          clearSession();
          location.assign("/login");
        }
      }}
    >
      Wyloguj
    </button>
  );
}

/** Miniaturka zdjęcia pobieranego przez uwierzytelnione API. */
export function AuthImage({ fileId, alt }: { fileId: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let revoke: string | null = null;
    fetchFileUrl(fileId).then((u) => {
      revoke = u;
      setUrl(u);
    }).catch(() => setUrl(null));
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [fileId]);
  if (!url) return <div className="stat" style={{ aspectRatio: "3/4" }} />;
  return <img src={url} alt={alt} />;
}

/** Opt-in powiadomień push — status + włącz/wyłącz jednym przyciskiem. */
export function PushNotificationsCard() {
  const [state, setState] = useState<"unsupported" | "off" | "on" | "busy">("busy");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    import("./push").then(async (push) => {
      if (!push.pushSupported()) return setState("unsupported");
      const sub = await push.currentSubscription();
      setState(sub ? "on" : "off");
    }).catch(() => setState("unsupported"));
  }, []);

  async function toggle() {
    setError(null);
    const push = await import("./push");
    const prev = state;
    setState("busy");
    try {
      if (prev === "on") {
        await push.disablePush();
        setState("off");
      } else {
        await push.enablePush();
        setState("on");
      }
    } catch (e) {
      setError((e as Error).message);
      setState(prev);
    }
  }

  return (
    <div className="card">
      <h3>Przypomnienia push</h3>
      {state === "unsupported" ? (
        <p className="dim" style={{ fontSize: "0.85rem" }}>
          Ta przeglądarka nie obsługuje powiadomień push. Na iPhonie
          zainstaluj aplikację na ekranie głównym (Udostępnij → „Do ekranu
          początkowego") i spróbuj ponownie.
        </p>
      ) : (
        <>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Przypomnienia o harmonogramie i powiadomienia o wiadomościach,
            raportach i planie — bez treści zdrowotnych. Możesz wyłączyć w
            każdej chwili.
          </p>
          <ErrorBox error={error} />
          <button className={`btn btn--small ${state === "on" ? "btn--ghost" : ""}`}
            disabled={state === "busy"} onClick={toggle}>
            {state === "busy" ? "…" : state === "on" ? "Wyłącz powiadomienia" : "Włącz powiadomienia"}
          </button>
          {state === "on" && <span className="badge badge--ok" style={{ marginLeft: 8 }}>włączone</span>}
        </>
      )}
    </div>
  );
}

export interface ProgressPhotoRow {
  id: string;
  file_id: string;
  taken_at: string;
  note: string | null;
}

/** Porównywarka zdjęć sylwetki „przed / po" — zestawienie wyłącznie
 * z WŁASNĄ historią (nigdy z innymi osobami). Domyślnie: najstarsze vs
 * najnowsze zdjęcie. */
export function PhotoCompare({ photos, formatDate }: {
  photos: ProgressPhotoRow[];
  formatDate: (iso: string) => string;
}) {
  // photos przychodzą posortowane malejąco po taken_at (API).
  const oldestFirst = photos.slice().reverse();
  const [leftId, setLeftId] = useState(oldestFirst[0]?.id ?? "");
  const [rightId, setRightId] = useState(photos[0]?.id ?? "");
  if (photos.length < 2) return null;
  const left = photos.find((p) => p.id === leftId) ?? oldestFirst[0];
  const right = photos.find((p) => p.id === rightId) ?? photos[0];
  return (
    <div className="card">
      <h3>Przed / po</h3>
      <div className="field-row">
        <div>
          <label>Zdjęcie „przed"</label>
          <select value={left.id} onChange={(e) => setLeftId(e.target.value)}>
            {oldestFirst.map((p) => (
              <option key={p.id} value={p.id}>{formatDate(p.taken_at)}</option>
            ))}
          </select>
        </div>
        <div>
          <label>Zdjęcie „po"</label>
          <select value={right.id} onChange={(e) => setRightId(e.target.value)}>
            {photos.map((p) => (
              <option key={p.id} value={p.id}>{formatDate(p.taken_at)}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="field-row" style={{ marginTop: 8 }}>
        <div style={{ textAlign: "center" }}>
          <AuthImage fileId={left.file_id} alt={`Zdjęcie ${formatDate(left.taken_at)}`} />
          <small className="dim">{formatDate(left.taken_at)}</small>
        </div>
        <div style={{ textAlign: "center" }}>
          <AuthImage fileId={right.file_id} alt={`Zdjęcie ${formatDate(right.taken_at)}`} />
          <small className="dim">{formatDate(right.taken_at)}</small>
        </div>
      </div>
    </div>
  );
}

/** Załącznik dowolnego typu (obraz/audio/wideo/plik) pobierany przez
 * uwierzytelnione API — typ rozpoznawany po pobraniu (Content-Type), nie
 * po nazwie pliku, więc działa niezależnie od tego, kto go wgrał. */
export function AuthAttachment({ fileId, filename }: { fileId: string; filename?: string }) {
  const [state, setState] = useState<{ url: string; type: string } | null>(null);
  useEffect(() => {
    let revoke: string | null = null;
    fetchFileBlob(fileId)
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        revoke = url;
        setState({ url, type: blob.type });
      })
      .catch(() => setState(null));
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [fileId]);
  if (!state) return <div className="stat" style={{ minHeight: 40 }} />;
  if (state.type.startsWith("image/")) return <img src={state.url} alt="załącznik" />;
  if (state.type.startsWith("audio/")) {
    return <audio controls src={state.url} style={{ width: "100%", maxWidth: 260 }} />;
  }
  if (state.type.startsWith("video/")) {
    return <video controls src={state.url} style={{ width: "100%", borderRadius: 10 }} />;
  }
  return (
    <a href={state.url} target="_blank" rel="noreferrer" download={filename}
      className="btn btn--ghost btn--small">
      📎 {filename ?? "Pobierz załącznik"}
    </a>
  );
}

let sparkGradientSeq = 0;

/** Wykres liniowy (SVG) dla pomiarów w czasie — cienka linia akcentu z
 * zanikającym wypełnieniem pod spodem (wzorem paneli Whoop/Oura), bez
 * osi i siatki, żeby trend czytało się od razu. */
export function Sparkline({ points, unit }: { points: { x: string; y: number }[]; unit: string }) {
  const [gradientId] = useState(() => `spark-fill-${++sparkGradientSeq}`);
  if (points.length < 2) return <p className="dim">Za mało danych na wykres.</p>;
  const ys = points.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const range = max - min || 1;
  const w = 300;
  const h = 64;
  const coords = points.map((p, i) => ({
    cx: (i / (points.length - 1)) * (w - 10) + 5,
    cy: h - 6 - ((p.y - min) / range) * (h - 16),
  }));
  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.cx.toFixed(1)},${c.cy.toFixed(1)}`).join(" ");
  const areaPath = `${path} L${coords[coords.length - 1].cx.toFixed(1)},${h} L${coords[0].cx.toFixed(1)},${h} Z`;
  return (
    <div>
      <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path className="spark__area" d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2.5"
          strokeLinecap="round" strokeLinejoin="round" />
        {coords.map((c, i) => (
          <circle key={i} cx={c.cx} cy={c.cy} r="2.5" fill="var(--accent)" />
        ))}
      </svg>
      <div className="row row--between">
        <small>{points[0].x}</small>
        <small>
          {min.toFixed(1)}–{max.toFixed(1)} {unit}
        </small>
        <small>{points[points.length - 1].x}</small>
      </div>
    </div>
  );
}

/** Rekordy osobiste i postęp od startu — rywalizacja wyłącznie z własną
 * historią (zasada Human OS: żadnych porównań między ludźmi ani
 * rankingów; punktem odniesienia jest wcześniejsze „ja"). */
/** Wykresy siły per ćwiczenie (szacowany 1RM + objętość dnia) — dane
 * wyłącznie ze strukturalnych zapisów serii; porównanie tylko z własną
 * historią. e1RM (Epley) to szacunek do obserwacji trendu, nie zalecenie
 * obciążenia. */
export function StrengthChartsCard({ clientId }: { clientId: string }) {
  const [series, setSeries] = useState<StrengthSeriesRow[] | null>(null);
  const [exercise, setExercise] = useState("");
  useEffect(() => {
    api.get<{ series: StrengthSeriesRow[] }>(`/api/clients/${clientId}/strength-series`)
      .then((d) => {
        setSeries(d.series);
        if (d.series.length > 0) setExercise(d.series[0].exercise_name);
      })
      .catch(() => setSeries([]));
  }, [clientId]);
  if (!series || series.length === 0) return null;
  const row = series.find((s) => s.exercise_name === exercise) ?? series[0];
  const enough = row.points.length >= 2;
  return (
    <div className="card">
      <div className="row row--between">
        <h3>Siła w czasie</h3>
        <select value={row.exercise_name} style={{ width: "auto" }}
          onChange={(e) => setExercise(e.target.value)}>
          {series.map((s) => (
            <option key={s.exercise_name} value={s.exercise_name}>{s.exercise_name}</option>
          ))}
        </select>
      </div>
      {!enough && (
        <p className="dim" style={{ fontSize: "0.85rem" }}>
          Zapisz serie (ciężar × powtórzenia) z co najmniej dwóch treningów,
          żeby zobaczyć trend.
        </p>
      )}
      {enough && (
        <>
          <div className="row row--between" style={{ marginTop: 6 }}>
            <b style={{ fontSize: "0.9rem" }}>Szacowany 1RM</b>
            <span className="badge">{row.points[row.points.length - 1].e1rm_kg} kg</span>
          </div>
          <Sparkline unit="kg"
            points={row.points.map((p) => ({ x: plDate(p.date), y: p.e1rm_kg }))} />
          <div className="row row--between" style={{ marginTop: 10 }}>
            <b style={{ fontSize: "0.9rem" }}>Objętość treningu</b>
            <span className="badge">{row.points[row.points.length - 1].volume_kg} kg</span>
          </div>
          <Sparkline unit="kg"
            points={row.points.map((p) => ({ x: plDate(p.date), y: p.volume_kg }))} />
          <small className="dim">
            1RM to szacunek (wzór Epleya) do obserwacji trendu — nie jest
            zaleceniem obciążenia.
          </small>
        </>
      )}
    </div>
  );
}

export function PersonalRecordsCard({ clientId }: { clientId: string }) {
  const [data, setData] = useState<PersonalRecordsData | null>(null);
  useEffect(() => {
    api.get<PersonalRecordsData>(`/api/clients/${clientId}/personal-records`)
      .then(setData)
      .catch(() => undefined);
  }, [clientId]);

  if (!data || (data.records.length === 0 && data.since_start.length === 0)) return null;

  return (
    <div className="card">
      <h3>🏆 Rekordy osobiste</h3>
      <p className="dim" style={{ fontSize: "0.85rem", marginTop: -4 }}>
        Porównanie wyłącznie z własną historią — nie z innymi.
      </p>
      {data.since_start.length > 0 && (
        <div className="row" style={{ flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {data.since_start.map((s) => (
            <span className="badge" key={s.kind}>
              {KIND_LABELS[s.kind] ?? s.kind}: {s.delta > 0 ? "+" : ""}{s.delta} {s.unit} od startu
            </span>
          ))}
        </div>
      )}
      {data.records.map((r) => (
        <div className="exercise" key={r.exercise_name}>
          <div>
            <b>{r.exercise_name}</b>
            {r.is_new && <span className="badge badge--accent" style={{ marginLeft: 6 }}>nowy rekord!</span>}
            <div className="meta">
              {plDate(r.achieved_on)}
              {r.previous_best_kg !== null && ` · poprzednio ${r.previous_best_kg} kg`}
              {` · ${r.attempts} zapisów`}
            </div>
          </div>
          <span className="badge" style={{ alignSelf: "center", whiteSpace: "nowrap" }}>
            {r.best_kg} kg
          </span>
        </div>
      ))}
    </div>
  );
}

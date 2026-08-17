import { ReactNode, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { clearSession, fetchFileUrl, getUser } from "./api";

export function Logo({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <rect width="64" height="64" rx="14" fill="#191c1f" />
      <path
        d="M14 44 L24 20 L32 36 L40 20 L50 44"
        fill="none" stroke="var(--accent)" strokeWidth="5"
        strokeLinecap="round" strokeLinejoin="round"
      />
      <circle cx="32" cy="48" r="3" fill="var(--accent)" />
    </svg>
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

/** Prosty wykres liniowy (SVG) dla pomiarów w czasie. */
export function Sparkline({ points, unit }: { points: { x: string; y: number }[]; unit: string }) {
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
  return (
    <div>
      <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
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

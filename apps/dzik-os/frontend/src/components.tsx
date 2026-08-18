import { Component, ErrorInfo, ReactNode, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  api, ApiError, AuthSessionRow, fetchFile, fetchFileBlob, fetchFileUrl,
  getMfaStatus, getToken, getUser, isCancel, listSecurityEvents, listSessions,
  logout, MfaStatus, mfaDisable, mfaEnable, mfaRegenerateRecoveryCodes, mfaSetup,
  openBlobInNewTab, reportFrontendError, revokeOtherSessions, revokeSession,
  saveBlobAs, SecurityEventRow, setSession,
} from "./api";
import { plDate, plDateTime } from "./dates";
import { applyUpdate, onUpdateAvailable } from "./pwa";
import { withGaps } from "./seriesUtils";
import { KIND_LABELS, PersonalRecordsData, SeriesPoint, StrengthSeriesRow } from "./types";

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

/** Dedykowany ekran offline — pełnoekranowa nakładka nad aplikacją.
 *
 * Dzik OS celowo NIE cache'uje żadnych danych z /api (dane zdrowotne nigdy
 * nie trafiają do Cache Storage), więc bez sieci nie ma czego pokazać —
 * zamiast wiecznego spinnera albo starych danych udających aktualne,
 * użytkownik dostaje jasny komunikat. Nakładka NIE odmontowuje widoków
 * pod spodem (drzewo React zostaje zamontowane), dzięki czemu wypełniany
 * formularz przeżywa chwilową utratę połączenia. */
export function OfflineScreen() {
  const [online, setOnline] = useState(() => navigator.onLine);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);
  if (online) return null;
  const check = async () => {
    setChecking(true);
    try {
      // Prawdziwy test łącza (navigator.onLine bywa zbyt optymistyczny):
      // /api/health jest network-only, więc odpowiedź = realne połączenie.
      const resp = await fetch("/api/health", { cache: "no-store" });
      if (resp.ok) setOnline(true);
    } catch {
      /* nadal offline */
    } finally {
      setChecking(false);
    }
  };
  return (
    <div className="offline-screen" role="alert" data-testid="offline-screen">
      <Logo size={52} />
      <h1>Brak połączenia z internetem</h1>
      <p>
        Twoje dane zdrowotne nie są przechowywane na tym urządzeniu, dlatego
        plan dnia, dieta, raporty, postępy, wiadomości, dokumenty i płatności
        wymagają połączenia z siecią.
      </p>
      <p className="dim">
        Gdy połączenie wróci, ekran zniknie automatycznie i zobaczysz aktualne
        dane. Formularz wypełniany przed utratą sieci pozostaje zachowany.
      </p>
      <button className="btn" onClick={check} disabled={checking}>
        {checking ? "Sprawdzanie…" : "Sprawdź połączenie"}
      </button>
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

export function ErrorBox({ error, onRetry }: {
  error: string | null;
  /** Podane = błąd odwracalny: pokazujemy przycisk „Spróbuj ponownie". */
  onRetry?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="alert alert--error" role="alert">
      {error}
      {onRetry && (
        <div style={{ marginTop: 8 }}>
          <button type="button" className="btn btn--ghost btn--small" onClick={onRetry}>
            Spróbuj ponownie
          </button>
        </div>
      )}
    </div>
  );
}

export function Spinner() {
  return <p className="dim">Wczytywanie…</p>;
}

/** Granica błędów React: awaria renderowania nie wygasza całej aplikacji
 * na biało. Błąd jest raportowany do backendu w formie zredagowanej
 * (typ + komponent + pliki własne — nigdy treść danych, patrz
 * reportFrontendError), a użytkownik dostaje czytelny ekran z możliwością
 * ponowienia. Montowana globalnie (main.tsx) i per trasa (App.tsx —
 * key=pathname resetuje granicę przy nawigacji). */
export class ErrorBoundary extends Component<
  { children: ReactNode; scope: string },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // componentStack zawiera tylko nazwy komponentów (bez danych) — bierzemy
    // pierwszy wpis jako wskazówkę miejsca awarii.
    const top = (info.componentStack ?? "")
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.startsWith("at "));
    reportFrontendError(error, `${this.props.scope}:${top ?? "?"}`);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="page">
        <div className="card">
          <h3>Coś poszło nie tak</h3>
          <p className="dim">
            Ten widok napotkał nieoczekiwany błąd. Twoje dane są bezpieczne —
            spróbuj ponownie albo wróć do ekranu głównego.
          </p>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn--small" onClick={() => this.setState({ failed: false })}>
              Spróbuj ponownie
            </button>
            <a className="btn btn--ghost btn--small" href="/">
              Ekran główny
            </a>
          </div>
        </div>
      </div>
    );
  }
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
  // Wylogowanie przez wspólnego klienta API (z nagłówkiem Authorization) —
  // serwer unieważnia sesję; lokalny stan czyszczony też bez sieci.
  return (
    <button className="btn btn--ghost btn--small" onClick={() => logout()}>
      Wyloguj
    </button>
  );
}

/** Krótki, ludzki opis urządzenia na podstawie User-Agent (bez zewnętrznych
 * bibliotek — tylko orientacyjna etykieta). */
function deviceLabel(ua: string | null): string {
  if (!ua) return "Nieznane urządzenie";
  const browser = /Edg\//.test(ua) ? "Edge"
    : /OPR\//.test(ua) ? "Opera"
    : /Firefox\//.test(ua) ? "Firefox"
    : /Chrome\//.test(ua) ? "Chrome"
    : /Safari\//.test(ua) ? "Safari"
    : "Przeglądarka";
  const system = /iPhone|iPad/.test(ua) ? "iOS"
    : /Android/.test(ua) ? "Android"
    : /Windows/.test(ua) ? "Windows"
    : /Mac OS X/.test(ua) ? "macOS"
    : /Linux/.test(ua) ? "Linux"
    : "";
  return system ? `${browser} · ${system}` : browser;
}

/** Aktywne sesje (urządzenia) konta: kiedy utworzona, ostatnie użycie,
 * przeglądarka; bieżąca oznaczona. Zakończenie wybranej sesji lub
 * wszystkich pozostałych — unieważnienie następuje po stronie serwera. */
export function SessionsCard() {
  const [sessions, setSessions] = useState<AuthSessionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setError(null);
    listSessions().then((d) => setSessions(d.sessions)).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function endSession(id: string) {
    setBusy(true);
    setError(null);
    try {
      await revokeSession(id);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function endOthers() {
    if (!confirm("Wylogować konto ze wszystkich pozostałych urządzeń?")) return;
    setBusy(true);
    setError(null);
    try {
      await revokeOtherSessions();
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const others = (sessions ?? []).filter((s) => !s.current);
  return (
    <div className="card">
      <h3>Aktywne sesje</h3>
      <p className="dim" style={{ fontSize: "0.85rem" }}>
        Urządzenia zalogowane na Twoje konto. Jeśli widzisz sesję, której nie
        rozpoznajesz — zakończ ją i zmień hasło.
      </p>
      <ErrorBox error={error} onRetry={load} />
      {!sessions && !error && <Spinner />}
      {sessions?.map((s) => (
        <div className="exercise" key={s.id}>
          <div>
            <b>{deviceLabel(s.user_agent)}</b>
            {s.current && <span className="badge badge--ok" style={{ marginLeft: 6 }}>to urządzenie</span>}
            <div className="meta">
              zalogowano {plDateTime(s.created_at)}
              {s.last_used_at && ` · ostatnio ${plDateTime(s.last_used_at)}`}
            </div>
          </div>
          {!s.current && (
            <button className="btn btn--ghost btn--small" disabled={busy}
              style={{ alignSelf: "center" }} onClick={() => endSession(s.id)}>
              Zakończ
            </button>
          )}
        </div>
      ))}
      {others.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <button className="btn btn--danger btn--small" disabled={busy} onClick={endOthers}>
            Wyloguj z pozostałych urządzeń ({others.length})
          </button>
        </div>
      )}
    </div>
  );
}

const SECURITY_EVENT_LABELS: Record<string, string> = {
  LOGIN_SUCCEEDED: "Zalogowanie",
  LOGIN_MFA_FAILED: "Nieudana weryfikacja MFA",
  MFA_ENABLED: "Włączenie MFA",
  MFA_DISABLED: "Wyłączenie MFA",
  MFA_RECOVERY_CODES_REGENERATED: "Nowe kody odzyskiwania",
  MFA_RECOVERY_CODE_USED: "Użyto kodu odzyskiwania",
  PASSWORD_CHANGED: "Zmiana hasła",
  PASSWORD_RESET_REQUESTED: "Żądanie resetu hasła",
  PASSWORD_RESET_COMPLETED: "Reset hasła",
  ACCOUNT_ACTIVATED: "Aktywacja konta",
  SESSION_LOGGED_OUT: "Wylogowanie",
  SESSION_REVOKED: "Zakończenie sesji",
  SESSIONS_REVOKED: "Wylogowanie z pozostałych urządzeń",
};

/** Historia istotnych zdarzeń bezpieczeństwa konta (bez tokenów). */
export function SecurityEventsCard() {
  const [events, setEvents] = useState<SecurityEventRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    listSecurityEvents().then((d) => setEvents(d.events)).catch((e) => setError(e.message));
  }, [open]);

  return (
    <div className="card">
      <div className="row row--between">
        <h3 style={{ margin: 0 }}>Historia bezpieczeństwa</h3>
        <button className="btn btn--ghost btn--small" onClick={() => setOpen(!open)}>
          {open ? "Zwiń" : "Pokaż"}
        </button>
      </div>
      {open && (
        <>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Logowania, nieudane próby MFA, resety hasła i kody odzyskiwania —
            jeśli widzisz coś, czego nie rozpoznajesz, zakończ sesje i zmień
            hasło.
          </p>
          <ErrorBox error={error} />
          {!events && !error && <Spinner />}
          {events?.length === 0 && <small>Brak zdarzeń.</small>}
          {events?.map((e, i) => (
            <div className="exercise" key={`${e.created_at}-${i}`}>
              <div>
                <b>{SECURITY_EVENT_LABELS[e.action] ?? e.action}</b>
                <div className="meta">{plDateTime(e.created_at)}</div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

/** Lista kodów odzyskiwania — pokazywana wyłącznie raz po wygenerowaniu. */
export function RecoveryCodesBox({ codes }: { codes: string[] }) {
  return (
    <div className="alert alert--info" style={{ marginTop: 10 }}>
      <b>Kody odzyskiwania — zapisz je teraz.</b>
      <p style={{ margin: "6px 0" }}>
        Każdy działa tylko raz i zastępuje kod z aplikacji, gdy stracisz
        telefon. Nie pokażemy ich ponownie.
      </p>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
        gap: 6, fontFamily: "monospace", fontSize: "0.95rem",
      }}>
        {codes.map((c) => <span key={c}>{c}</span>)}
      </div>
      <div style={{ marginTop: 8 }}>
        <button className="btn btn--ghost btn--small"
          onClick={() => navigator.clipboard?.writeText(codes.join("\n"))}>
          Kopiuj wszystkie
        </button>
      </div>
    </div>
  );
}

/** Konfiguracja MFA (TOTP): sekret + otpauth:// do aplikacji
 * uwierzytelniającej, potwierdzenie kodem, kody odzyskiwania.
 * Sekret pojawia się wyłącznie tutaj — nigdy więcej. */
export function MfaCard({ forced = false }: { forced?: boolean }) {
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    getMfaStatus().then(setStatus).catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function startSetup() {
    setBusy(true); setError(null);
    try {
      setSetup(await mfaSetup());
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function confirmSetup() {
    setBusy(true); setError(null);
    try {
      const r = await mfaEnable(code.trim());
      setRecoveryCodes(r.recovery_codes);
      setSetup(null);
      setCode("");
      setOk("MFA włączone. Od teraz logowanie wymaga kodu z aplikacji.");
      // Zdejmij lokalną flagę wymuszenia (serwer i tak już przepuszcza).
      const user = getUser();
      const token = getToken();
      if (user && token) setSession(token, { ...user, mfa_setup_required: false, mfa_enabled: true });
      load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function regenerate() {
    const c = prompt("Podaj aktualny kod z aplikacji, aby wygenerować nowe kody odzyskiwania (stare przestaną działać):");
    if (!c) return;
    setBusy(true); setError(null); setOk(null);
    try {
      const r = await mfaRegenerateRecoveryCodes(c.trim());
      setRecoveryCodes(r.recovery_codes);
      setOk("Wygenerowano nowe kody odzyskiwania — stare są nieważne.");
      load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function disable() {
    const c = prompt("Podaj aktualny kod z aplikacji, aby wyłączyć MFA:");
    if (!c) return;
    setBusy(true); setError(null); setOk(null);
    try {
      await mfaDisable(c.trim());
      setRecoveryCodes(null);
      setOk("MFA wyłączone.");
      const user = getUser();
      const token = getToken();
      if (user && token) setSession(token, { ...user, mfa_enabled: false });
      load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const roles = getUser()?.roles ?? [];
  const mandatory = roles.includes("COACH") || roles.includes("ADMIN");

  return (
    <div className="card">
      <h3>Weryfikacja dwuetapowa (MFA)</h3>
      {forced && (
        <p className="alert alert--info">
          Twoja rola wymaga MFA. Skonfiguruj je teraz — do tego czasu konto ma
          dostęp wyłącznie do tego ekranu.
        </p>
      )}
      <ErrorBox error={error} />
      {ok && <div className="alert alert--info">{ok}</div>}
      {!status && !error && <Spinner />}
      {status && !status.enabled && !setup && (
        <>
          <p className="dim" style={{ fontSize: "0.85rem" }}>
            Drugi składnik logowania: kod z aplikacji uwierzytelniającej
            (np. Aegis, Google Authenticator, 1Password).
            {mandatory ? " Dla roli trenera/administratora MFA jest obowiązkowe." : ""}
          </p>
          <button className="btn" disabled={busy} onClick={startSetup}>
            Skonfiguruj MFA
          </button>
        </>
      )}
      {setup && (
        <div>
          <p style={{ fontSize: "0.9rem" }}>
            1. Dodaj konto w aplikacji uwierzytelniającej — zeskanuj lub
            otwórz link albo przepisz sekret ręcznie:
          </p>
          <p>
            <a href={setup.otpauth_uri} style={{ wordBreak: "break-all", fontSize: "0.82rem" }}>
              {setup.otpauth_uri}
            </a>
          </p>
          <p style={{ fontFamily: "monospace", fontSize: "1.05rem", letterSpacing: 1, wordBreak: "break-all" }}>
            {setup.secret.replace(/(.{4})/g, "$1 ").trim()}
          </p>
          <div className="row">
            <button className="btn btn--ghost btn--small"
              onClick={() => navigator.clipboard?.writeText(setup.secret)}>
              Kopiuj sekret
            </button>
          </div>
          <label htmlFor="mfa-code" style={{ marginTop: 10 }}>
            2. Wpisz kod z aplikacji, aby potwierdzić
          </label>
          <input id="mfa-code" inputMode="numeric" autoComplete="one-time-code"
            placeholder="123456" value={code} maxLength={6}
            onChange={(e) => setCode(e.target.value)} />
          <div style={{ marginTop: 10 }}>
            <button className="btn" disabled={busy || code.trim().length !== 6}
              onClick={confirmSetup}>
              Potwierdź i włącz MFA
            </button>
          </div>
        </div>
      )}
      {status?.enabled && (
        <>
          <p>
            <span className="badge badge--ok">MFA aktywne</span>{" "}
            <small className="dim">
              kody odzyskiwania: {status.recovery_codes_left}
            </small>
          </p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            <button className="btn btn--ghost btn--small" disabled={busy} onClick={regenerate}>
              Nowe kody odzyskiwania
            </button>
            {!mandatory && (
              <button className="btn btn--danger btn--small" disabled={busy} onClick={disable}>
                Wyłącz MFA
              </button>
            )}
          </div>
        </>
      )}
      {recoveryCodes && <RecoveryCodesBox codes={recoveryCodes} />}
    </div>
  );
}

function downloadErrorMessage(e: unknown): string {
  const err = e as ApiError;
  if (err instanceof ApiError && (err.status === 403 || err.status === 404)) {
    return "Brak dostępu do pliku lub plik nie istnieje.";
  }
  return `Nie udało się pobrać pliku${err?.message ? ` (${err.message})` : ""}.`;
}

/** Wspólny przycisk pobierania/otwierania chronionego pliku.
 * Pobiera przez uwierzytelnione API (Bearer) do Blob, zapisuje/otwiera
 * klikiem w <a> (bez window.open po await — nie wpada w blokadę popupów)
 * i pokazuje stan: pobieranie / sukces / błąd / brak dostępu. */
export function FileDownloadButton({ fileId, filename, label = "Pobierz", openInTab = false,
  className = "btn btn--ghost btn--small" }: {
  fileId: string;
  /** Wymuszona nazwa zapisu; domyślnie nazwa z Content-Disposition backendu. */
  filename?: string;
  label?: ReactNode;
  /** true = otwórz w nowej karcie (podgląd PDF), false = zapisz na dysk. */
  openInTab?: boolean;
  className?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setError(null);
    setBusy(true);
    try {
      const { blob, filename: served } = await fetchFile(fileId);
      if (openInTab) openBlobInNewTab(blob);
      else saveBlobAs(blob, filename ?? served ?? "plik");
      setDone(true);
      setTimeout(() => setDone(false), 2500);
    } catch (e) {
      setError(downloadErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 4, alignItems: "flex-start" }}>
      <button type="button" className={className} disabled={busy} onClick={run}>
        {busy ? "Pobieranie…" : done ? "✓ Gotowe" : label}
      </button>
      {error && (
        <small role="alert" style={{ color: "var(--danger)" }}>{error}</small>
      )}
    </span>
  );
}

/** Miniaturka zdjęcia pobieranego przez uwierzytelnione API. Zmiana fileId
 * anuluje poprzednie pobranie (spóźniona odpowiedź nie nadpisze nowego
 * zdjęcia), a błąd jest widoczny zamiast pustego kwadratu bez wyjaśnienia. */
export function AuthImage({ fileId, alt }: { fileId: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const ac = new AbortController();
    let revoke: string | null = null;
    setUrl(null);
    setFailed(false);
    fetchFileUrl(fileId, { signal: ac.signal }).then((u) => {
      revoke = u;
      setUrl(u);
    }).catch((e) => {
      if (!isCancel(e)) setFailed(true);
    });
    return () => {
      ac.abort();
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [fileId]);
  if (failed) {
    return (
      <div className="stat" style={{ aspectRatio: "3/4", display: "grid", placeItems: "center" }}>
        <small role="alert" className="dim">Nie udało się wczytać zdjęcia</small>
      </div>
    );
  }
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
    }).catch(() =>
      // Świadome zignorowanie szczegółów: brak modułu push / brak service
      // workera / stara przeglądarka — z punktu widzenia użytkownika to
      // dokładnie stan „nieobsługiwane" i taki komunikat widzi na karcie.
      setState("unsupported")
    );
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
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    let revoke: string | null = null;
    setError(null);
    fetchFileBlob(fileId, { signal: ac.signal })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        revoke = url;
        setState({ url, type: blob.type });
      })
      .catch((e) => {
        if (isCancel(e)) return; // zmiana załącznika — nie pokazuj błędu
        setState(null);
        setError(downloadErrorMessage(e));
      });
    return () => {
      ac.abort();
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [fileId]);
  if (error) {
    return <small role="alert" style={{ color: "var(--danger)" }}>📎 {error}</small>;
  }
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

/** Punkty Sparkline dla serii TYGODNIOWEJ (raporty) z przerwami w linii
 * zamiast interpolacji przez tygodnie bez danych. */
export function wellbeingSparkPoints(points: SeriesPoint[]) {
  return withGaps(points.map((p) => ({ date: p.date, value: p.value })), 7)
    .map((p) => ({ x: p.date ? plDate(p.date) : "", y: p.value }));
}

/** Punkty Sparkline dla serii DZIENNEJ (dziennik kaloryczny) z przerwami
 * w linii zamiast łączenia przez dni bez wpisu. */
export function dailySparkPoints(points: SeriesPoint[]) {
  return withGaps(points.map((p) => ({ date: p.date, value: p.value })), 1)
    .map((p) => ({ x: p.date ? plDate(p.date) : "", y: p.value }));
}

let sparkGradientSeq = 0;

/** Wykres liniowy (SVG) dla pomiarów w czasie — cienka linia akcentu z
 * zanikającym wypełnieniem pod spodem (wzorem paneli Whoop/Oura), bez
 * osi i siatki, żeby trend czytało się od razu.
 *
 * Jakość danych: punkt z `y: null` to PRZERWA (brak danych, np. tydzień
 * bez raportu — patrz seriesUtils.withGaps). Linia jest wtedy przerywana
 * zamiast łączyć przez dziurę — brakujące dane nigdy nie są rysowane tak,
 * jakby były rzeczywistymi pomiarami. */
export function Sparkline({ points, unit }: {
  points: { x: string; y: number | null }[];
  unit: string;
}) {
  const [gradientId] = useState(() => `spark-fill-${++sparkGradientSeq}`);
  const valid = points.filter((p): p is { x: string; y: number } => p.y !== null);
  if (valid.length < 2) return <p className="dim">Za mało danych na wykres.</p>;
  const ys = valid.map((p) => p.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const range = max - min || 1;
  const w = 300;
  const h = 64;
  const denominator = Math.max(points.length - 1, 1);
  const coords = points.map((p, i) => ({
    cx: (i / denominator) * (w - 10) + 5,
    cy: p.y === null ? null : h - 6 - ((p.y - min) / range) * (h - 16),
  }));
  // Segmenty ciągłych danych rozdzielone punktami-przerwami (cy === null).
  const segments: { cx: number; cy: number }[][] = [];
  let current: { cx: number; cy: number }[] = [];
  for (const c of coords) {
    if (c.cy === null) {
      if (current.length > 0) segments.push(current);
      current = [];
    } else {
      current.push({ cx: c.cx, cy: c.cy });
    }
  }
  if (current.length > 0) segments.push(current);
  const segPath = (seg: { cx: number; cy: number }[]) =>
    seg.map((c, i) => `${i === 0 ? "M" : "L"}${c.cx.toFixed(1)},${c.cy.toFixed(1)}`).join(" ");
  const firstX = valid[0].x;
  const lastX = valid[valid.length - 1].x;
  return (
    <div>
      <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {segments.map((seg, s) => seg.length >= 2 && (
          <g key={`seg-${s}`}>
            <path className="spark__area"
              d={`${segPath(seg)} L${seg[seg.length - 1].cx.toFixed(1)},${h} L${seg[0].cx.toFixed(1)},${h} Z`}
              fill={`url(#${gradientId})`} stroke="none" />
            <path d={segPath(seg)} fill="none" stroke="var(--accent)" strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round" />
          </g>
        ))}
        {segments.flat().map((c, i) => (
          <circle key={i} cx={c.cx} cy={c.cy} r="2.5" fill="var(--accent)" />
        ))}
      </svg>
      <div className="row row--between">
        <small>{firstX}</small>
        <small>
          {min.toFixed(1)}–{max.toFixed(1)} {unit}
        </small>
        <small>{lastX}</small>
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
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const ac = new AbortController();
    setError(null);
    api.get<{ series: StrengthSeriesRow[] }>(
      `/api/clients/${clientId}/strength-series`, { signal: ac.signal }
    )
      .then((d) => {
        setSeries(d.series);
        if (d.series.length > 0) setExercise(d.series[0].exercise_name);
      })
      .catch((e) => {
        if (!isCancel(e)) setError(e.message);
      });
    return () => ac.abort();
  }, [clientId, attempt]);
  if (error) {
    return (
      <div className="card">
        <h3>Siła w czasie</h3>
        <ErrorBox error={error} onRetry={() => setAttempt((a) => a + 1)} />
      </div>
    );
  }
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
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const ac = new AbortController();
    setError(null);
    api.get<PersonalRecordsData>(
      `/api/clients/${clientId}/personal-records`, { signal: ac.signal }
    )
      .then(setData)
      .catch((e) => {
        if (!isCancel(e)) setError(e.message);
      });
    return () => ac.abort();
  }, [clientId, attempt]);

  if (error) {
    return (
      <div className="card">
        <h3>🏆 Rekordy osobiste</h3>
        <ErrorBox error={error} onRetry={() => setAttempt((a) => a + 1)} />
      </div>
    );
  }
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

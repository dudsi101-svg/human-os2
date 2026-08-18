// Centrum powiadomień + ustawienia doręczeń (P13).
//
// Lista pokazuje PEŁNĄ treść powiadomień (użytkownik jest uwierzytelniony);
// na ekran blokady (push/e-mail) backend wysyła wyłącznie neutralne
// wezwanie — patrz docs/POWIADOMIENIA.md. Otwarta aplikacja dostaje nowe
// wpisy na żywo kanałem SSE (zdarzenie notification.new z P12).
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  NotificationRowApi,
  NotificationSettingsData,
  getNotificationSettings,
  handleSessionExpired,
  isCancel,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationSettings,
} from "../api";
import { plDateTime } from "../dates";
import { ErrorBox, PushNotificationsCard, Spinner, TopBar } from "../components";
import { connectRealtime } from "../realtime";
import {
  CHANNEL_LABELS,
  DAY_LABELS,
  TIMEZONE_CHOICES,
  mergeNotification,
  notificationTargetUrl,
  parseActiveDays,
  quietHoursValid,
  toggleActiveDay,
} from "../notificationsUtils";

export default function Notifications() {
  const [rows, setRows] = useState<NotificationRowApi[] | null>(null);
  const [unread, setUnread] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = () => {
    setError(null);
    listNotifications(filter ? { category: filter } : undefined)
      .then((d) => {
        setRows(d.notifications);
        setUnread(d.unread);
      })
      .catch((e) => {
        if (!isCancel(e)) setError(e.message);
      });
  };
  useEffect(load, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Żywe aktualizacje, gdy ekran jest otwarty (SSE z P12); przy problemach
  // z kanałem lista i tak odświeża się przy każdej zmianie filtra/wejściu.
  const filterRef = useRef(filter);
  filterRef.current = filter;
  useEffect(() => {
    const ac = new AbortController();
    void connectRealtime("/api/threads/events", {
      onEvent: (type, data) => {
        if (type !== "notification.new") return;
        const n = data as NotificationRowApi;
        if (filterRef.current && n.category !== filterRef.current) return;
        setRows((prev) => (prev ? mergeNotification(prev, n) : prev));
        setUnread((u) => u + 1);
      },
      onSessionExpired: handleSessionExpired,
    }, ac.signal);
    return () => ac.abort();
  }, []);

  async function openNotification(n: NotificationRowApi) {
    if (!n.read_at) {
      // Best-effort: nawigacja nie może czekać na zapis znacznika.
      markNotificationRead(n.id).catch(() => undefined);
      setUnread((u) => Math.max(0, u - 1));
    }
    navigate(notificationTargetUrl(n));
  }

  async function markAll() {
    try {
      await markAllNotificationsRead();
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const categories = useMemo(() => {
    const seen = new Map<string, string>();
    for (const n of rows ?? []) seen.set(n.category, n.category_label);
    return Array.from(seen.entries());
  }, [rows]);

  return (
    <div className="page">
      <TopBar
        title="Powiadomienia"
        right={
          unread > 0 ? (
            <button className="btn btn--small btn--ghost" onClick={markAll}>
              Oznacz przeczytane
            </button>
          ) : undefined
        }
      />
      <ErrorBox error={error} onRetry={load} />
      {(categories.length > 1 || filter) && (
        <div className="row" role="group" aria-label="Filtr kategorii"
          style={{ flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
          <button className={`btn btn--small ${filter === "" ? "" : "btn--ghost"}`}
            aria-pressed={filter === ""} onClick={() => setFilter("")}>
            Wszystkie
          </button>
          {categories.map(([key, label]) => (
            <button key={key}
              className={`btn btn--small ${filter === key ? "" : "btn--ghost"}`}
              aria-pressed={filter === key} onClick={() => setFilter(key)}>
              {label}
            </button>
          ))}
        </div>
      )}
      {!rows ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <p className="dim">Brak powiadomień.</p>
      ) : (
        <div className="list">
          {rows.map((n) => (
            <button key={n.id} className="card card--nav"
              style={{ textAlign: "left", width: "100%" }}
              onClick={() => openNotification(n)}>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span className="row row--between" style={{ gap: 8 }}>
                  <b style={{ color: "var(--text)" }}>{n.title}</b>
                  {!n.read_at && (
                    <span className="badge badge--accent">nowe</span>
                  )}
                </span>
                {n.body && <small style={{ display: "block" }}>{n.body}</small>}
                <small className="dim">
                  {n.category_label} · {plDateTime(n.sent_at ?? n.created_at)}
                </small>
              </span>
            </button>
          ))}
        </div>
      )}
      <NotificationSettingsCard />
      <PushNotificationsCard />
    </div>
  );
}

/** Preferencje per kategoria × kanał + ciche godziny, dni aktywne,
 * strefa czasowa i częstotliwość przypomnień o raporcie. */
function NotificationSettingsCard() {
  const [data, setData] = useState<NotificationSettingsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  // Lokalny stan edycji.
  const [prefs, setPrefs] = useState<Record<string, boolean>>({});
  const [quietStart, setQuietStart] = useState("");
  const [quietEnd, setQuietEnd] = useState("");
  const [activeDays, setActiveDays] = useState("1,2,3,4,5,6,7");
  const [tz, setTz] = useState("");
  const [raportFreq, setRaportFreq] = useState("DAILY");

  const load = () => {
    setError(null);
    getNotificationSettings()
      .then((d) => {
        setData(d);
        setPrefs(d.preferences);
        setQuietStart(d.settings.quiet_hours_start ?? "");
        setQuietEnd(d.settings.quiet_hours_end ?? "");
        setActiveDays(d.settings.active_days);
        setTz(d.settings.timezone ?? "Europe/Warsaw");
        setRaportFreq(d.settings.raport_frequency);
      })
      .catch((e) => setError(e.message));
  };
  useEffect(() => {
    if (open && !data) load();
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const quietOk = quietHoursValid(quietStart, quietEnd);

  async function save() {
    if (!data || !quietOk) return;
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      await updateNotificationSettings({
        quiet_hours_start: quietStart || null,
        quiet_hours_end: quietEnd || null,
        active_days: activeDays,
        raport_frequency: raportFreq,
        timezone: tz,
        preferences: Object.entries(prefs).map(([key, enabled]) => {
          const [category, channel] = key.split(":");
          return { category, channel, enabled };
        }),
      });
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const days = parseActiveDays(activeDays);

  return (
    <div className="card">
      <div className="row row--between">
        <h2>Ustawienia powiadomień</h2>
        <button className="btn btn--small btn--ghost" aria-expanded={open}
          onClick={() => setOpen(!open)}>
          {open ? "Zwiń" : "Zmień"}
        </button>
      </div>
      {!open ? (
        <p className="dim" style={{ fontSize: "0.85rem" }}>
          Kanały per kategoria (push / w aplikacji / e-mail), ciche godziny,
          dni przypomnień, strefa czasowa i częstotliwość raportu.
        </p>
      ) : !data && !error ? (
        <Spinner />
      ) : (
        <>
          <ErrorBox error={error} onRetry={load} />
          {data && (
            <>
              <h3>Kategorie i kanały</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Kategoria</th>
                      {data.channels.map((ch) => (
                        <th key={ch}>{CHANNEL_LABELS[ch] ?? ch}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.categories.map((cat) => (
                      <tr key={cat.key}>
                        <td data-label="Kategoria">{cat.label}</td>
                        {data.channels.map((ch) => {
                          const key = `${cat.key}:${ch}`;
                          return (
                            <td key={ch} data-label={CHANNEL_LABELS[ch] ?? ch}>
                              <input type="checkbox"
                                aria-label={`${cat.label} — ${CHANNEL_LABELS[ch] ?? ch}`}
                                checked={prefs[key] ?? false}
                                onChange={(e) =>
                                  setPrefs({ ...prefs, [key]: e.target.checked })
                                }
                              />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="dim" style={{ fontSize: "0.78rem" }}>
                E-mail to opcjonalny kanał awaryjny — działa, gdy operator
                skonfigurował dostawcę. Push i e-mail nigdy nie zawierają
                danych zdrowotnych ani kwot — szczegóły widzisz dopiero tu,
                po zalogowaniu.
              </p>
              <h3>Ciche godziny</h3>
              <p className="dim" style={{ fontSize: "0.85rem" }}>
                W tym przedziale push i e-mail są wyciszone; powiadomienia
                czekają w aplikacji. Zakres może przechodzić przez północ.
              </p>
              <div className="field-row field-row--keep">
                <label>
                  Od
                  <input type="time" value={quietStart}
                    onChange={(e) => setQuietStart(e.target.value)} />
                </label>
                <label>
                  Do
                  <input type="time" value={quietEnd}
                    onChange={(e) => setQuietEnd(e.target.value)} />
                </label>
              </div>
              {!quietOk && (
                <small role="alert" style={{ color: "var(--danger)" }}>
                  Podaj obie godziny (różne) albo zostaw oba pola puste.
                </small>
              )}
              <h3>Dni przypomnień z harmonogramu</h3>
              <div className="row" role="group" aria-label="Dni aktywne"
                style={{ flexWrap: "wrap", gap: 6 }}>
                {Object.entries(DAY_LABELS).map(([day, label]) => (
                  <button key={day} type="button"
                    className={`btn btn--small ${days.has(day) ? "" : "btn--ghost"}`}
                    aria-pressed={days.has(day)}
                    onClick={() => setActiveDays(toggleActiveDay(activeDays, day))}>
                    {label}
                  </button>
                ))}
              </div>
              <div className="field-row">
                <label>
                  Strefa czasowa
                  <select value={tz} onChange={(e) => setTz(e.target.value)}>
                    {!TIMEZONE_CHOICES.includes(tz) && (
                      <option value={tz}>{tz}</option>
                    )}
                    {TIMEZONE_CHOICES.map((z) => (
                      <option key={z} value={z}>{z}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Przypomnienie o raporcie
                  <select value={raportFreq}
                    onChange={(e) => setRaportFreq(e.target.value)}>
                    <option value="DAILY">Codziennie (gdy zaplanowane)</option>
                    <option value="WEEKLY">Raz w tygodniu</option>
                  </select>
                </label>
              </div>
              <div className="row" style={{ gap: 8, marginTop: 10 }}>
                <button className="btn" disabled={busy || !quietOk} onClick={save}>
                  {busy ? "Zapisywanie…" : "Zapisz ustawienia"}
                </button>
                {saved && (
                  <span role="status" className="badge badge--ok">zapisano</span>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

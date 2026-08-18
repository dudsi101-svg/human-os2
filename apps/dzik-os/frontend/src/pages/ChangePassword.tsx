import { FormEvent, useState } from "react";
import { changePassword, getUser, logout } from "../api";
import { ErrorBox, Logo } from "../components";

export default function ChangePassword() {
  const user = getUser();
  const forced = user?.must_change_password === true;
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (next !== repeat) {
      setError("Nowe hasła nie są identyczne");
      return;
    }
    if (next.length < 10) {
      setError("Nowe hasło musi mieć co najmniej 10 znaków");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // Rotacja tokenu: serwer unieważnia wszystkie stare sesje i wydaje
      // nowy token — changePassword podmienia go w bieżącej sesji.
      await changePassword(current, next);
      const roles = user?.roles ?? [];
      location.assign(roles.includes("COACH") ? "/trener" : roles.includes("ADMIN") ? "/admin" : "/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="row" style={{ justifyContent: "center", marginBottom: 18 }}>
          <Logo size={44} />
          <div>
            <h1>Zmiana hasła</h1>
            {forced && <small>Wymagana przed pierwszym użyciem aplikacji</small>}
          </div>
        </div>
        {forced && (
          <p className="alert alert--info">
            Hasło startowe otrzymane od trenera trzeba zmienić na własne —
            dopiero wtedy uzyskasz dostęp do swoich danych.
          </p>
        )}
        <form onSubmit={submit} className="card">
          <label htmlFor="current">Obecne hasło</label>
          <input id="current" type="password" autoComplete="current-password" required
            value={current} onChange={(e) => setCurrent(e.target.value)} />
          <label htmlFor="next">Nowe hasło (min. 10 znaków)</label>
          <input id="next" type="password" autoComplete="new-password" required
            value={next} onChange={(e) => setNext(e.target.value)} />
          <label htmlFor="repeat">Powtórz nowe hasło</label>
          <input id="repeat" type="password" autoComplete="new-password" required
            value={repeat} onChange={(e) => setRepeat(e.target.value)} />
          <ErrorBox error={error} />
          <div style={{ marginTop: 14 }}>
            <button className="btn" disabled={busy}>
              {busy ? "Zapisywanie…" : "Zmień hasło"}
            </button>
          </div>
        </form>
        {!forced && (
          <p style={{ textAlign: "center" }}>
            <a href="/">← Wróć do aplikacji</a>
          </p>
        )}
        <p style={{ textAlign: "center" }}>
          <button className="btn btn--ghost btn--small" onClick={() => logout()}>
            Wyloguj
          </button>
        </p>
      </div>
    </div>
  );
}

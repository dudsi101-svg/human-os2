import { FormEvent, useState } from "react";
import { ApiError, confirmPasswordReset, requestPasswordReset } from "../api";
import { ErrorBox, Logo } from "../components";

/** Reset hasła: bez tokenu (fragmentu w adresie) — formularz żądania z
 * ogólnym komunikatem (niezależnym od istnienia konta); z tokenem
 * (/reset-hasla#TOKEN z e-maila) — ustawienie nowego hasła. */
export default function ResetPassword() {
  const token = location.hash.startsWith("#") ? location.hash.slice(1) : "";
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function submitRequest(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await requestPasswordReset(email);
      setMessage(r.message);
    } catch (err) {
      // 429 (limit prób) albo brak sieci — bez ujawniania niczego więcej.
      setError(err instanceof ApiError ? err.message : "Brak połączenia z serwerem");
    } finally {
      setBusy(false);
    }
  }

  async function submitConfirm(e: FormEvent) {
    e.preventDefault();
    if (password !== repeat) {
      setError("Hasła nie są identyczne");
      return;
    }
    if (password.length < 10) {
      setError("Hasło musi mieć co najmniej 10 znaków");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Brak połączenia z serwerem");
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
            <h1>Reset hasła</h1>
            {!token && <small>Wyślemy link na Twój e-mail</small>}
          </div>
        </div>
        {!token && (
          <form onSubmit={submitRequest} className="card">
            <label htmlFor="email">E-mail konta</label>
            <input id="email" type="email" autoComplete="username" required
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <ErrorBox error={error} />
            {message && <div className="alert alert--info">{message}</div>}
            <div style={{ marginTop: 14 }}>
              <button className="btn" disabled={busy}>
                {busy ? "Wysyłanie…" : "Wyślij link do resetu"}
              </button>
            </div>
          </form>
        )}
        {token && done && (
          <div className="card">
            <p className="alert alert--info">
              Hasło zmienione. Ze względów bezpieczeństwa wylogowaliśmy Cię ze
              wszystkich urządzeń — zaloguj się nowym hasłem.
            </p>
            <a className="btn" href="/login">Przejdź do logowania</a>
          </div>
        )}
        {token && !done && (
          <form onSubmit={submitConfirm} className="card">
            <label htmlFor="pass">Nowe hasło (min. 10 znaków)</label>
            <input id="pass" type="password" autoComplete="new-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <label htmlFor="repeat">Powtórz hasło</label>
            <input id="repeat" type="password" autoComplete="new-password" required
              value={repeat} onChange={(e) => setRepeat(e.target.value)} />
            <ErrorBox error={error} />
            <div style={{ marginTop: 14 }}>
              <button className="btn" disabled={busy}>
                {busy ? "Zapisywanie…" : "Ustaw nowe hasło"}
              </button>
            </div>
          </form>
        )}
        <p style={{ textAlign: "center" }}>
          <a href="/login">← Wróć do logowania</a>
        </p>
      </div>
    </div>
  );
}

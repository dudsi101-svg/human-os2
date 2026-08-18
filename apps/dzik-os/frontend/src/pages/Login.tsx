import { FormEvent, useState } from "react";
import { ApiError, consumeLoginNotice, login, SessionUser, verifyMfa } from "../api";
import { ErrorBox } from "../components";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Powód powrotu do logowania (np. wygaśnięcie sesji) — jednorazowy
  // komunikat zapisany przed przekierowaniem w api.ts.
  const [notice] = useState(consumeLoginNotice);

  function goHome(user: SessionUser) {
    if (user.must_change_password) {
      location.assign("/haslo");
      return;
    }
    if (user.mfa_setup_required) {
      location.assign("/mfa");
      return;
    }
    location.assign(
      user.roles.includes("COACH") ? "/trener" : user.roles.includes("ADMIN") ? "/admin" : "/"
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await login(email, password);
      if (result.kind === "mfa") {
        // Konto z MFA: hasło poprawne, sesja powstanie po kodzie.
        setMfaToken(result.mfaToken);
        return;
      }
      goHome(result.user);
    } catch (err) {
      // Serwer odpowiada jednym komunikatem niezależnie od istnienia konta.
      setError(err instanceof ApiError ? err.message : "Brak połączenia z serwerem");
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(e: FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setBusy(true);
    setError(null);
    try {
      const user = await verifyMfa(mfaToken, code.trim());
      goHome(user);
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null;
      if (apiErr && apiErr.status === 401 && apiErr.message.includes("wygasła")) {
        // Wyzwanie MFA wygasło — wróć do kroku hasła.
        setMfaToken(null);
        setCode("");
      }
      setError(apiErr ? apiErr.message : "Brak połączenia z serwerem");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div style={{ textAlign: "center", marginBottom: 14 }}>
          <h1 className="sr-only">Dzik OS — logowanie</h1>
          <img src="/icons/logo-full.png" alt="Dzik OS" className="login-logo" />
          <small className="dim">Panel Podopiecznego</small>
          {!mfaToken && (
            <>
              <p style={{ margin: "14px 0 0", fontWeight: 600 }}>
                Cześć, dobrze Cię widzieć! 💪
              </p>
              <p className="dim" style={{ margin: "4px 0 0", fontSize: "0.88rem" }}>
                Zaloguj się — Twój plan, dieta i wiadomości od trenera
                czekają w jednym miejscu.
              </p>
            </>
          )}
        </div>
        {notice && <div className="alert alert--info" role="status">{notice}</div>}
        {!mfaToken && (
          <form onSubmit={submit} className="card">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" autoComplete="username" required
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <label htmlFor="password">Hasło</label>
            <input id="password" type="password" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <ErrorBox error={error} />
            <div style={{ marginTop: 14 }}>
              <button className="btn" disabled={busy}>
                {busy ? "Logowanie…" : "Zaloguj się"}
              </button>
            </div>
            <p style={{ margin: "10px 0 0", textAlign: "center" }}>
              <a href="/reset-hasla" style={{ fontSize: "0.85rem" }}>
                Nie pamiętasz hasła?
              </a>
            </p>
          </form>
        )}
        {mfaToken && (
          <form onSubmit={submitCode} className="card">
            <h2 style={{ marginTop: 0 }}>Weryfikacja dwuetapowa</h2>
            <p className="dim" style={{ fontSize: "0.88rem" }}>
              Wpisz kod z aplikacji uwierzytelniającej albo jeden z kodów
              odzyskiwania.
            </p>
            <label htmlFor="mfa">Kod</label>
            <input id="mfa" inputMode="numeric" autoComplete="one-time-code"
              autoFocus placeholder="123456 albo XXXXX-XXXXX" required
              value={code} onChange={(e) => setCode(e.target.value)} />
            <ErrorBox error={error} />
            <div className="row" style={{ marginTop: 14 }}>
              <button className="btn" disabled={busy || code.trim().length < 6}>
                {busy ? "Sprawdzanie…" : "Potwierdź"}
              </button>
              <button type="button" className="btn btn--ghost"
                onClick={() => { setMfaToken(null); setCode(""); setError(null); }}>
                Wróć
              </button>
            </div>
          </form>
        )}
        <p className="dim" style={{ textAlign: "center", fontSize: "0.8rem" }}>
          Twoje dane należą do Ciebie. Trener widzi je tylko za Twoją zgodą,
          którą możesz cofnąć w każdej chwili.
        </p>
      </div>
    </div>
  );
}

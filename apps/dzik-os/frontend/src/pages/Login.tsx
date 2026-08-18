import { FormEvent, useState } from "react";
import { ApiError, consumeLoginNotice, login } from "../api";
import { ErrorBox } from "../components";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Powód powrotu do logowania (np. wygaśnięcie sesji) — jednorazowy
  // komunikat zapisany przed przekierowaniem w api.ts.
  const [notice] = useState(consumeLoginNotice);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await login(email, password);
      if (user.must_change_password) {
        location.assign("/haslo");
        return;
      }
      location.assign(
        user.roles.includes("COACH") ? "/trener" : user.roles.includes("ADMIN") ? "/admin" : "/"
      );
    } catch (err) {
      // Serwer odpowiada jednym komunikatem niezależnie od istnienia konta.
      setError(err instanceof ApiError ? err.message : "Brak połączenia z serwerem");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div style={{ textAlign: "center", marginBottom: 14 }}>
          <img
            src="/icons/logo-full.png"
            alt="Dzik OS"
            style={{ width: "min(78%, 300px)", height: "auto", display: "block", margin: "0 auto 8px" }}
          />
          <small className="dim">Panel Podopiecznego</small>
          <p style={{ margin: "14px 0 0", fontWeight: 600 }}>
            Cześć, dobrze Cię widzieć! 💪
          </p>
          <p className="dim" style={{ margin: "4px 0 0", fontSize: "0.88rem" }}>
            Zaloguj się — Twój plan, dieta i wiadomości od trenera
            czekają w jednym miejscu.
          </p>
        </div>
        {notice && <div className="alert alert--info" role="status">{notice}</div>}
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
        </form>
        <p className="dim" style={{ textAlign: "center", fontSize: "0.8rem" }}>
          Twoje dane należą do Ciebie. Trener widzi je tylko za Twoją zgodą,
          którą możesz cofnąć w każdej chwili.
        </p>
      </div>
    </div>
  );
}

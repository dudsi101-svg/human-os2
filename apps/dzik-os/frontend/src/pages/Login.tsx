import { FormEvent, useState } from "react";
import { setSession, SessionUser } from "../api";
import { ErrorBox } from "../components";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Błąd logowania");
        return;
      }
      setSession(data.token as string, data.user as SessionUser);
      if (data.user.must_change_password) {
        location.assign("/haslo");
        return;
      }
      const roles: string[] = data.user.roles;
      location.assign(roles.includes("COACH") ? "/trener" : roles.includes("ADMIN") ? "/admin" : "/");
    } catch {
      setError("Brak połączenia z serwerem");
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

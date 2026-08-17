import { FormEvent, useState } from "react";
import { setSession, SessionUser } from "../api";
import { ErrorBox, Logo } from "../components";

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
        <div className="row" style={{ justifyContent: "center", marginBottom: 18 }}>
          <Logo size={44} />
          <div>
            <h1>Dzik OS</h1>
            <small>Panel Podopiecznego</small>
          </div>
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

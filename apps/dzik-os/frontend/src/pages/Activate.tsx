import { FormEvent, useEffect, useState } from "react";
import { activateAccount, ApiError, inspectActivation } from "../api";
import { ErrorBox, Logo, Spinner } from "../components";

/** Aktywacja konta z jednorazowego linku zaproszenia.
 *
 * Token przychodzi we FRAGMENCIE adresu (/aktywacja#TOKEN) — fragment nie
 * jest wysyłany do serwera HTTP, więc token nie trafia do logów
 * dostępowych; do API idzie wyłącznie w body POST. */
export default function Activate() {
  const token = location.hash.startsWith("#") ? location.hash.slice(1) : "";
  const [who, setWho] = useState<{ email: string; display_name: string } | null>(null);
  const [invalid, setInvalid] = useState(false);
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setInvalid(true);
      return;
    }
    inspectActivation(token)
      .then(setWho)
      .catch(() => setInvalid(true));
  }, [token]);

  async function submit(e: FormEvent) {
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
      await activateAccount(token, password);
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
            <h1>Aktywacja konta</h1>
            <small>Ustaw własne hasło — nikt inny go nie zna</small>
          </div>
        </div>
        {invalid && (
          <div className="card">
            <p className="alert alert--error">
              To zaproszenie jest nieważne — mogło wygasnąć, zostać anulowane
              albo już użyte.
            </p>
            <p className="dim" style={{ fontSize: "0.85rem" }}>
              Poproś trenera o nowe zaproszenie. Jeśli konto jest już
              aktywowane, po prostu <a href="/login">zaloguj się</a>.
            </p>
          </div>
        )}
        {!invalid && !who && !done && <Spinner />}
        {done && (
          <div className="card">
            <p className="alert alert--info">
              Konto aktywowane! Możesz się zalogować swoim nowym hasłem.
            </p>
            <a className="btn" href="/login">Przejdź do logowania</a>
          </div>
        )}
        {who && !done && (
          <form onSubmit={submit} className="card">
            <p>
              Cześć <b>{who.display_name}</b>! Aktywujesz konto{" "}
              <b>{who.email}</b>.
            </p>
            <label htmlFor="pass">Nowe hasło (min. 10 znaków)</label>
            <input id="pass" type="password" autoComplete="new-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <label htmlFor="repeat">Powtórz hasło</label>
            <input id="repeat" type="password" autoComplete="new-password" required
              value={repeat} onChange={(e) => setRepeat(e.target.value)} />
            <ErrorBox error={error} />
            <div style={{ marginTop: 14 }}>
              <button className="btn" disabled={busy}>
                {busy ? "Aktywowanie…" : "Aktywuj konto"}
              </button>
            </div>
          </form>
        )}
        <p className="dim" style={{ textAlign: "center", fontSize: "0.8rem" }}>
          Hasło ustawiasz wyłącznie Ty — trener ani nikt inny go nie widzi.
        </p>
      </div>
    </div>
  );
}

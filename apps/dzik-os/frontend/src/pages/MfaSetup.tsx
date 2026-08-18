import { getUser, logout } from "../api";
import { Logo, MfaCard } from "../components";

/** Wymuszona konfiguracja MFA (rola COACH/ADMIN bez skonfigurowanego
 * TOTP): serwer i tak blokuje wszystko poza konfiguracją MFA
 * (403 MFA_SETUP_REQUIRED) — ten ekran to jedyna droga dalej. */
export default function MfaSetup() {
  const user = getUser();
  const roles = user?.roles ?? [];
  const done = () => {
    location.assign(roles.includes("COACH") ? "/trener" : roles.includes("ADMIN") ? "/admin" : "/");
  };
  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="row" style={{ justifyContent: "center", marginBottom: 18 }}>
          <Logo size={44} />
          <div>
            <h1>Zabezpiecz konto</h1>
            <small>Weryfikacja dwuetapowa jest wymagana dla Twojej roli</small>
          </div>
        </div>
        <MfaCard forced />
        <p style={{ textAlign: "center", marginTop: 10 }}>
          <button className="btn btn--ghost btn--small" onClick={done}>
            Przejdź do aplikacji →
          </button>{" "}
          <button className="btn btn--ghost btn--small" onClick={() => logout()}>
            Wyloguj
          </button>
        </p>
      </div>
    </div>
  );
}

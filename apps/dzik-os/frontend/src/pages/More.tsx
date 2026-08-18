import { Link } from "react-router-dom";
import { getUser } from "../api";
import {
  LogoutButton, MfaCard, PushNotificationsCard, SecurityEventsCard,
  SessionsCard, TopBar,
} from "../components";

export default function More() {
  const user = getUser()!;
  const isClient = user.roles.includes("CLIENT");
  return (
    <div className="page">
      <TopBar title="Więcej" right={<LogoutButton />} />
      <div className="card">
        <b>{user.display_name}</b>
        <div><small>{user.email}</small></div>
        <div><small>Rola: {user.roles.join(", ")}</small></div>
      </div>
      {!isClient && <PushNotificationsCard />}
      {/* Klient ma sekcje bezpieczeństwa (MFA, sesje, historia) w Profilu;
          trener/admin tutaj. */}
      {!isClient && <MfaCard />}
      {!isClient && <SessionsCard />}
      {!isClient && <SecurityEventsCard />}
      {user.roles.includes("COACH") && (
        <div className="list" style={{ marginBottom: 10 }}>
          <Link className="card" to="/trener/konsultacje">📅 Terminarz konsultacji</Link>
        </div>
      )}
      <div className="list">
        {isClient && (
          <>
            <Link className="card" to="/postepy">📈 Monitoring i postępy</Link>
            <Link className="card" to="/wiedza">📚 Baza wiedzy</Link>
            <Link className="card" to="/konsultacje">📅 Konsultacje z trenerem</Link>
            <Link className="card" to="/dokumenty">📄 Dokumenty i harmonogram</Link>
            <Link className="card" to="/platnosci">💳 Płatności</Link>
            <Link className="card" to="/wiadomosci">💬 Wiadomości</Link>
            <Link className="card" to="/profil">👤 Profil, zgody i moje dane</Link>
          </>
        )}
        <Link className="card" to="/haslo">🔑 Zmień hasło</Link>
      </div>
      <p className="dim" style={{ fontSize: "0.78rem" }}>
        Dzik OS działa na fundamentach Human OS: Twoje dane są Twoją
        własnością, każda istotna zmiana ma autora, powód i pozostaje w
        historii, a zgody można cofnąć w każdej chwili.
      </p>
    </div>
  );
}

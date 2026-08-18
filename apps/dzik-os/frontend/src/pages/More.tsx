import { Link } from "react-router-dom";
import { getUser } from "../api";
import {
  Icon, LogoutButton, MfaCard, PushNotificationsCard, SecurityEventsCard,
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
          <Link className="card card--nav" to="/trener/konsultacje">
            <Icon name="calendar" /><span>Terminarz konsultacji</span>
          </Link>
          <Link className="card card--nav" to="/trener/wyzwania">
            <Icon name="trophy" /><span>Wyzwania grupowe</span>
          </Link>
          <Link className="card card--nav" to="/trener/rozliczenia">
            <Icon name="card" /><span>Pojednanie płatności</span>
          </Link>
        </div>
      )}
      <div className="list">
        {isClient && (
          <>
            <Link className="card card--nav" to="/postepy">
              <Icon name="chart" /><span>Monitoring i postępy</span>
            </Link>
            <Link className="card card--nav" to="/wiedza">
              <Icon name="knowledge" /><span>Baza wiedzy</span>
            </Link>
            <Link className="card card--nav" to="/konsultacje">
              <Icon name="calendar" /><span>Konsultacje z trenerem</span>
            </Link>
            <Link className="card card--nav" to="/wyzwania">
              <Icon name="trophy" /><span>Wyzwania</span>
            </Link>
            <Link className="card card--nav" to="/dokumenty">
              <Icon name="file" /><span>Dokumenty i harmonogram</span>
            </Link>
            <Link className="card card--nav" to="/platnosci">
              <Icon name="card" /><span>Płatności</span>
            </Link>
            <Link className="card card--nav" to="/wiadomosci">
              <Icon name="msg" /><span>Wiadomości</span>
            </Link>
            <Link className="card card--nav" to="/profil">
              <Icon name="user" /><span>Profil, zgody i moje dane</span>
            </Link>
          </>
        )}
        <Link className="card card--nav" to="/haslo">
          <Icon name="key" /><span>Zmień hasło</span>
        </Link>
      </div>
      <p className="dim" style={{ fontSize: "0.78rem" }}>
        Dzik OS działa na fundamentach Human OS: Twoje dane są Twoją
        własnością, każda istotna zmiana ma autora, powód i pozostaje w
        historii, a zgody można cofnąć w każdej chwili.
      </p>
    </div>
  );
}

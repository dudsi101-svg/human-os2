import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { lazy, Suspense } from "react";
// Ekrany za logowaniem ładują się leniwie (audyt B3): klient na
// telefonie nie pobiera panelu trenera ani admina. Ekrany publiczne
// i bramki (hasło/MFA/zgody) zostają eager — pierwsza farba bez
// dodatkowej rundy sieciowej.
const Today = lazy(() => import("./pages/client/Today"));
const Intake = lazy(() => import("./pages/client/Intake"));
const Interview = lazy(() => import("./pages/client/Interview"));
const Onboarding = lazy(() => import("./pages/client/Onboarding"));
const Plan = lazy(() => import("./pages/client/Plan"));
const Nutrition = lazy(() => import("./pages/client/Nutrition"));
const Checkin = lazy(() => import("./pages/client/Checkin"));
const Progress = lazy(() => import("./pages/client/Progress"));
const Payments = lazy(() => import("./pages/client/Payments"));
const Profile = lazy(() => import("./pages/client/Profile"));
const Documents = lazy(() => import("./pages/client/Documents"));
const ClientKnowledge = lazy(() => import("./pages/client/Knowledge"));
const ClientConsultations = lazy(() => import("./pages/client/Consultations"));
const ClientChallenges = lazy(() => import("./pages/client/Challenges"));
const CoachConsultations = lazy(() => import("./pages/coach/Consultations"));
const CoachChallenges = lazy(() => import("./pages/coach/Challenges"));
const More = lazy(() => import("./pages/More"));
const Notifications = lazy(() => import("./pages/Notifications"));
const Messages = lazy(() => import("./pages/Messages"));
const Thread = lazy(() => import("./pages/Thread"));
const Clients = lazy(() => import("./pages/coach/Clients"));
const ClientDetail = lazy(() => import("./pages/coach/ClientDetail"));
const Reconciliation = lazy(() => import("./pages/coach/Reconciliation"));
const WeeklyDigest = lazy(() => import("./pages/coach/WeeklyDigest"));
const Templates = lazy(() => import("./pages/coach/Templates"));
const CoachKnowledge = lazy(() => import("./pages/coach/Knowledge"));
const Admin = lazy(() => import("./pages/Admin"));
import { getUser } from "./api";
import { ErrorBoundary, Nav } from "./components";
import { maskPathIds } from "./errorUtils";
import Login from "./pages/Login";
import Landing from "./pages/Landing";
import Privacy from "./pages/Privacy";
import ChangePassword from "./pages/ChangePassword";
import Activate from "./pages/Activate";
import ResetPassword from "./pages/ResetPassword";
import MfaSetup from "./pages/MfaSetup";
import ConsentGate, { ConsentSpinner, usePendingConsents } from "./pages/ConsentGate";

export default function App() {
  const user = getUser();
  const location = useLocation();
  const roles = user?.roles ?? [];
  const isClient = roles.includes("CLIENT");
  const needsPassword = user?.must_change_password === true;
  const needsMfaSetup = user?.mfa_setup_required === true;
  const { pending, catalog, reload } = usePendingConsents(
    !!user && isClient && !needsPassword && !needsMfaSetup
  );
  // Ekrany publiczne (bez zalogowania): strona marketingowa, logowanie,
  // aktywacja konta z zaproszenia, reset hasła (żądanie + ustawienie nowego).
  const publicPaths = ["/", "/login", "/aktywacja", "/reset-hasla", "/prywatnosc"];
  if (!user && !publicPaths.includes(location.pathname)) {
    return <Navigate to="/login" replace />;
  }
  if (user && needsPassword && location.pathname !== "/haslo") {
    return <Navigate to="/haslo" replace />;
  }
  // Rola z obowiązkowym MFA bez konfiguracji: serwer blokuje wszystko poza
  // konfiguracją MFA — prowadź od razu na dedykowany ekran.
  if (user && !needsPassword && needsMfaSetup && location.pathname !== "/mfa") {
    return <Navigate to="/mfa" replace />;
  }
  if (user && isClient && !needsPassword && location.pathname !== "/haslo") {
    if (pending === null) return <main id="main"><ConsentSpinner /></main>;
    if (pending.length > 0) {
      return (
        <main id="main">
          <ConsentGate pending={pending} catalog={catalog} onResolved={reload} />
        </main>
      );
    }
  }
  const home = roles.includes("COACH") ? "/trener" : roles.includes("ADMIN") ? "/admin" : "/";
  return (
    <>
      {/* Link pomijający nawigację — pierwszy element w porządku fokusu. */}
      <a href="#main" className="skip-link">Przejdź do treści</a>
      {user && !needsPassword && !needsMfaSetup && <Nav />}
      {/* Landmark main: cała treść trasy (nawigacja jest osobnym <nav>). */}
      <main id="main">
      {/* Granica błędów per trasa: key=pathname resetuje ją przy nawigacji,
          więc awaria jednego widoku nie „przykleja się" do kolejnych. */}
      <ErrorBoundary scope={`route:${maskPathIds(location.pathname)}`} key={location.pathname}>
      <Suspense fallback={<ConsentSpinner />}>
      <Routes>
        {/* Publiczna strona marketingowa: gość na "/" widzi wizytówkę,
            zalogowany — swój ekran startowy jak dotąd. */}
        {!user && <Route path="/" element={<Landing />} />}
        <Route path="/login" element={user ? <Navigate to={home} replace /> : <Login />} />
        <Route path="/aktywacja" element={<Activate />} />
        <Route path="/reset-hasla" element={<ResetPassword />} />
        <Route path="/prywatnosc" element={<Privacy />} />
        {user && <Route path="/haslo" element={<ChangePassword />} />}
        {user && <Route path="/mfa" element={<MfaSetup />} />}
        {roles.includes("CLIENT") && (
          <>
            <Route path="/" element={<Today />} />
            <Route path="/rozmowa" element={<Onboarding />} />
            <Route path="/wywiad" element={<Interview />} />
            <Route path="/ankieta" element={<Intake />} />
            <Route path="/plan" element={<Plan />} />
            <Route path="/dieta" element={<Nutrition />} />
            <Route path="/raport" element={<Checkin />} />
            <Route path="/postepy" element={<Progress />} />
            <Route path="/platnosci" element={<Payments />} />
            <Route path="/profil" element={<Profile />} />
            <Route path="/dokumenty" element={<Documents />} />
            <Route path="/wiedza" element={<ClientKnowledge />} />
            <Route path="/konsultacje" element={<ClientConsultations />} />
            <Route path="/wyzwania" element={<ClientChallenges />} />
          </>
        )}
        {roles.includes("COACH") && (
          <>
            <Route path="/trener" element={<Clients />} />
            <Route path="/trener/klient/:clientId" element={<ClientDetail />} />
            <Route path="/trener/szablony" element={<Templates />} />
            <Route path="/trener/wiedza" element={<CoachKnowledge />} />
            <Route path="/trener/konsultacje" element={<CoachConsultations />} />
            <Route path="/trener/wyzwania" element={<CoachChallenges />} />
            <Route path="/trener/rozliczenia" element={<Reconciliation />} />
            <Route path="/trener/podsumowanie" element={<WeeklyDigest />} />
          </>
        )}
        {roles.includes("ADMIN") && <Route path="/admin" element={<Admin />} />}
        {user && (
          <>
            <Route path="/wiadomosci" element={<Messages />} />
            <Route path="/wiadomosci/:threadId" element={<Thread />} />
            <Route path="/powiadomienia" element={<Notifications />} />
            <Route path="/wiecej" element={<More />} />
          </>
        )}
        <Route path="*" element={<Navigate to={user ? home : "/login"} replace />} />
      </Routes>
      </Suspense>
      </ErrorBoundary>
      </main>
    </>
  );
}

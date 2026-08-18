import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { getUser } from "./api";
import { ErrorBoundary, Nav } from "./components";
import { maskPathIds } from "./errorUtils";
import Login from "./pages/Login";
import ChangePassword from "./pages/ChangePassword";
import ConsentGate, { ConsentSpinner, usePendingConsents } from "./pages/ConsentGate";
import Today from "./pages/client/Today";
import Intake from "./pages/client/Intake";
import Plan from "./pages/client/Plan";
import Nutrition from "./pages/client/Nutrition";
import Checkin from "./pages/client/Checkin";
import Progress from "./pages/client/Progress";
import Payments from "./pages/client/Payments";
import Profile from "./pages/client/Profile";
import Documents from "./pages/client/Documents";
import ClientKnowledge from "./pages/client/Knowledge";
import ClientConsultations from "./pages/client/Consultations";
import CoachConsultations from "./pages/coach/Consultations";
import More from "./pages/More";
import Messages from "./pages/Messages";
import Thread from "./pages/Thread";
import Clients from "./pages/coach/Clients";
import ClientDetail from "./pages/coach/ClientDetail";
import Templates from "./pages/coach/Templates";
import CoachKnowledge from "./pages/coach/Knowledge";
import Admin from "./pages/Admin";

export default function App() {
  const user = getUser();
  const location = useLocation();
  const roles = user?.roles ?? [];
  const isClient = roles.includes("CLIENT");
  const needsPassword = user?.must_change_password === true;
  const { pending, reload } = usePendingConsents(
    !!user && isClient && !needsPassword
  );
  if (!user && location.pathname !== "/login") {
    return <Navigate to="/login" replace />;
  }
  if (user && needsPassword && location.pathname !== "/haslo") {
    return <Navigate to="/haslo" replace />;
  }
  if (user && isClient && !needsPassword && location.pathname !== "/haslo") {
    if (pending === null) return <ConsentSpinner />;
    if (pending.length > 0) {
      return <ConsentGate pending={pending} onResolved={reload} />;
    }
  }
  const home = roles.includes("COACH") ? "/trener" : roles.includes("ADMIN") ? "/admin" : "/";
  return (
    <>
      {user && !needsPassword && <Nav />}
      {/* Granica błędów per trasa: key=pathname resetuje ją przy nawigacji,
          więc awaria jednego widoku nie „przykleja się" do kolejnych. */}
      <ErrorBoundary scope={`route:${maskPathIds(location.pathname)}`} key={location.pathname}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to={home} replace /> : <Login />} />
        {user && <Route path="/haslo" element={<ChangePassword />} />}
        {roles.includes("CLIENT") && (
          <>
            <Route path="/" element={<Today />} />
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
          </>
        )}
        {roles.includes("COACH") && (
          <>
            <Route path="/trener" element={<Clients />} />
            <Route path="/trener/klient/:clientId" element={<ClientDetail />} />
            <Route path="/trener/szablony" element={<Templates />} />
            <Route path="/trener/wiedza" element={<CoachKnowledge />} />
            <Route path="/trener/konsultacje" element={<CoachConsultations />} />
          </>
        )}
        {roles.includes("ADMIN") && <Route path="/admin" element={<Admin />} />}
        {user && (
          <>
            <Route path="/wiadomosci" element={<Messages />} />
            <Route path="/wiadomosci/:threadId" element={<Thread />} />
            <Route path="/wiecej" element={<More />} />
          </>
        )}
        <Route path="*" element={<Navigate to={user ? home : "/login"} replace />} />
      </Routes>
      </ErrorBoundary>
    </>
  );
}

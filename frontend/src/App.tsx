import { Navigate, Route, Routes } from "react-router-dom";

import { getToken } from "./api";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { PublicLessonPage } from "./pages/PublicLessonPage";

function HomePage() {
  return <Navigate to={getToken() ? "/admin" : "/admin/login"} replace />;
}

function ProtectedAdminRoute() {
  return getToken() ? <AdminDashboardPage /> : <Navigate to="/admin/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<ProtectedAdminRoute />} />
      <Route path="/lesson/:slug" element={<PublicLessonPage />} />
    </Routes>
  );
}


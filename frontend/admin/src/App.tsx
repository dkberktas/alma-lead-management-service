import { Routes, Route, Navigate, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import EnvBadge from "./components/EnvBadge";
import LoginPage from "./pages/LoginPage";
import LeadsPage from "./pages/LeadsPage";
import AttorneysPage from "./pages/AttorneysPage";

function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "ADMIN";

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium transition-colors ${
      isActive
        ? "text-indigo-600"
        : "text-stone-500 hover:text-stone-700"
    }`;

  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <NavLink
            to="/"
            className="text-base font-semibold tracking-tight text-stone-800"
          >
            Alma Admin
          </NavLink>

          {isAuthenticated && (
            <nav className="flex items-center gap-4">
              <NavLink to="/" end className={linkClass}>
                Leads
              </NavLink>
              {isAdmin && (
                <NavLink to="/attorneys" className={linkClass}>
                  Attorneys
                </NavLink>
              )}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-3">
          <EnvBadge />
          {isAuthenticated && (
            <>
              {user && (
                <div className="flex items-center gap-2 border-l border-stone-200 pl-3">
                  <span className="text-sm text-stone-600">{user.email}</span>
                  <span className="rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-stone-500">
                    {user.role}
                  </span>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="rounded-md px-3 py-1 text-sm text-stone-500 hover:bg-stone-100 hover:text-stone-700"
              >
                Log out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <LeadsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/attorneys"
          element={
            <ProtectedRoute>
              <AttorneysPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

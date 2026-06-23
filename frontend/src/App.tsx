import { Link, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { Button } from "./components/ui";
import { useAuth } from "./lib/auth";
import { CreateTicketPage } from "./pages/CreateTicketPage";
import { LoginPage } from "./pages/LoginPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { TicketsPage } from "./pages/TicketsPage";

/** Gate routes only when the backend has auth enabled — otherwise the
 *  single-agent demo stays fully usable without signing in. */
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { authEnabled, user, loading } = useAuth();
  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (authEnabled && !user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function HeaderAuth() {
  const { authEnabled, user, logout } = useAuth();
  if (!authEnabled) return null;
  if (user) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-600">{user.display_name}</span>
        <Button variant="ghost" onClick={logout}>
          Sign out
        </Button>
      </div>
    );
  }
  return (
    <Link to="/login">
      <Button variant="secondary">Sign in</Button>
    </Link>
  );
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-tight">TriageAI</span>
            <span className="rounded bg-violet-100 px-1.5 py-0.5 text-xs font-medium text-violet-700">
              helpdesk
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/new">
              <Button>New ticket</Button>
            </Link>
            <HeaderAuth />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-6">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <TicketsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/new"
            element={
              <ProtectedRoute>
                <CreateTicketPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tickets/:id"
            element={
              <ProtectedRoute>
                <TicketDetailPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

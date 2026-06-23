import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api, getToken, setToken } from "./api";
import type { LoginRequest, User } from "../types";

interface AuthState {
  user: User | null;
  authEnabled: boolean;
  loading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const health = await api.health();
        if (active) setAuthEnabled(health.auth_enabled);
        // Restore session if a token is already stored.
        if (getToken()) {
          const me = await api.me();
          if (active) setUser(me);
        }
      } catch {
        // health unreachable or token invalid — stay logged out
        setToken(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function login(payload: LoginRequest) {
    const result = await api.login(payload);
    setToken(result.access_token);
    setUser(result.user);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, authEnabled, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

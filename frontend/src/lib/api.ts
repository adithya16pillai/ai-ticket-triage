import type {
  AuthToken,
  LoginRequest,
  Ticket,
  TicketCreate,
  TicketEvent,
  TicketFilters,
  TicketUpdate,
  User,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

const TOKEN_KEY = "triage_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    if (res.status === 401) setToken(null); // stale/invalid token — drop it
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function toQuery(filters: TicketFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  listTickets: (filters: TicketFilters = {}) =>
    request<Ticket[]>(`/tickets${toQuery(filters)}`),

  getTicket: (id: string) => request<Ticket>(`/tickets/${id}`),

  createTicket: (payload: TicketCreate) =>
    request<Ticket>("/tickets", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateTicket: (id: string, payload: TicketUpdate) =>
    request<Ticket>(`/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteTicket: (id: string) =>
    request<void>(`/tickets/${id}`, { method: "DELETE" }),

  retriageTicket: (id: string) =>
    request<Ticket>(`/tickets/${id}/retriage`, { method: "POST" }),

  listTicketEvents: (id: string) =>
    request<TicketEvent[]>(`/tickets/${id}/events`),

  health: () =>
    request<{ auth_enabled: boolean; triage_enabled: boolean }>("/health", {
      // /health lives at the API root, not under /tickets
    }),

  login: (payload: LoginRequest) =>
    request<AuthToken>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => request<User>("/auth/me"),
};

import type {
  Ticket,
  TicketCreate,
  TicketFilters,
  TicketUpdate,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
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
};

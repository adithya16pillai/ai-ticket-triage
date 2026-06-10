import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./api";
import type { TicketCreate, TicketFilters, TicketUpdate } from "../types";

const keys = {
  all: ["tickets"] as const,
  list: (filters: TicketFilters) => ["tickets", "list", filters] as const,
  detail: (id: string) => ["tickets", "detail", id] as const,
};

export function useTickets(filters: TicketFilters) {
  return useQuery({
    queryKey: keys.list(filters),
    queryFn: () => api.listTickets(filters),
  });
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: () => api.getTicket(id),
    enabled: Boolean(id),
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TicketCreate) => api.createTicket(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });
}

export function useUpdateTicket(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TicketUpdate) => api.updateTicket(id, payload),
    onSuccess: (ticket) => {
      qc.setQueryData(keys.detail(id), ticket);
      qc.invalidateQueries({ queryKey: keys.all });
    },
  });
}

export function useDeleteTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteTicket(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all }),
  });
}

export function useRetriage(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.retriageTicket(id),
    onSuccess: (ticket) => {
      qc.setQueryData(keys.detail(id), ticket);
      qc.invalidateQueries({ queryKey: keys.all });
    },
  });
}

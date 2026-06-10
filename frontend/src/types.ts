export type TicketStatus = "open" | "in_progress" | "resolved";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TriageSource = "ai" | "manual" | "fallback";

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: string;
  suggested_team: string | null;
  assignee: string | null;
  triage_source: TriageSource;
  created_at: string;
  updated_at: string;
}

export interface TicketCreate {
  title: string;
  description: string;
}

export interface TicketUpdate {
  title?: string;
  description?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: string;
  suggested_team?: string | null;
  assignee?: string | null;
}

export interface TicketFilters {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: string;
  assignee?: string;
}

export const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved"];
export const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];

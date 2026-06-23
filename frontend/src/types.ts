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
  triage_confidence: number | null;
  triage_reason: string | null;
  triaged_at: string | null;
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

export type TicketEventType =
  | "created"
  | "triaged"
  | "triage_fallback"
  | "manual_override"
  | "status_changed"
  | "retriaged"
  | "draft_generated"
  | "comment";

export interface TicketEvent {
  id: string;
  ticket_id: string;
  event_type: TicketEventType;
  summary: string;
  payload: Record<string, unknown> | null;
  actor: string | null;
  created_at: string;
}

export interface TicketFilters {
  status?: TicketStatus;
  priority?: TicketPriority;
  category?: string;
  assignee?: string;
}

export type CommentSource = "human" | "ai_assisted";

export interface Comment {
  id: string;
  ticket_id: string;
  author: string | null;
  body: string;
  source: CommentSource;
  created_at: string;
}

export interface CommentCreate {
  body: string;
  source?: CommentSource;
}

export interface ReplyDraft {
  reply_text: string;
  tone: string | null;
  needs_human_review: boolean;
  triage_source: TriageSource;
  confidence: number | null;
  reason: string | null;
}

export type UserRole = "agent" | "admin";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved"];
export const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];

/** Colour-coded badges for status, priority, and triage source. */
import type { TicketPriority, TicketStatus, TriageSource } from "../types";

function Pill({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color}`}
    >
      {children}
    </span>
  );
}

const STATUS_COLORS: Record<TicketStatus, string> = {
  open: "bg-blue-100 text-blue-700",
  in_progress: "bg-amber-100 text-amber-700",
  resolved: "bg-emerald-100 text-emerald-700",
};

const PRIORITY_COLORS: Record<TicketPriority, string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-sky-100 text-sky-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};

const SOURCE_COLORS: Record<TriageSource, string> = {
  ai: "bg-violet-100 text-violet-700",
  manual: "bg-slate-100 text-slate-600",
  fallback: "bg-yellow-100 text-yellow-800",
};

const SOURCE_LABELS: Record<TriageSource, string> = {
  ai: "AI triaged",
  manual: "Manual",
  fallback: "Needs triage",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <Pill color={STATUS_COLORS[status]}>{status.replace("_", " ")}</Pill>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <Pill color={PRIORITY_COLORS[priority]}>{priority}</Pill>;
}

export function TriageSourceBadge({ source }: { source: TriageSource }) {
  return <Pill color={SOURCE_COLORS[source]}>{SOURCE_LABELS[source]}</Pill>;
}

/** Shows the AI's self-reported confidence. Amber below the 0.6 gate that would
 *  have triggered a fallback, green above it. */
export function ConfidenceBadge({ value }: { value: number }) {
  const color = value < 0.6 ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-700";
  return <Pill color={color}>confidence {value.toFixed(2)}</Pill>;
}

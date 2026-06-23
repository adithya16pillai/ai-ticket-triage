import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ConfidenceBadge, TriageSourceBadge } from "../components/badges";
import { Button, Input, Label, Select } from "../components/ui";
import {
  useDeleteTicket,
  useRetriage,
  useTicket,
  useTicketEvents,
  useUpdateTicket,
} from "../lib/queries";
import { PRIORITIES, STATUSES } from "../types";
import type { TicketEventType, TicketUpdate } from "../types";

const EVENT_STYLES: Record<TicketEventType, { dot: string; label: string }> = {
  created: { dot: "bg-slate-400", label: "Created" },
  triaged: { dot: "bg-violet-500", label: "AI triaged" },
  triage_fallback: { dot: "bg-yellow-500", label: "Fallback" },
  manual_override: { dot: "bg-sky-500", label: "Manual override" },
  status_changed: { dot: "bg-emerald-500", label: "Status" },
  retriaged: { dot: "bg-violet-500", label: "Re-triaged" },
  draft_generated: { dot: "bg-indigo-500", label: "AI draft" },
  comment: { dot: "bg-slate-500", label: "Comment" },
};

export function TicketDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data: ticket, isLoading, isError, error } = useTicket(id);
  const update = useUpdateTicket(id);
  const del = useDeleteTicket();
  const retriage = useRetriage(id);
  const { data: events } = useTicketEvents(id);

  // Local draft so the agent edits, then commits with Save.
  const [draft, setDraft] = useState<TicketUpdate>({});
  useEffect(() => {
    if (ticket) {
      setDraft({
        status: ticket.status,
        priority: ticket.priority,
        category: ticket.category,
        suggested_team: ticket.suggested_team ?? "",
        assignee: ticket.assignee ?? "",
      });
    }
  }, [ticket]);

  if (isLoading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (isError)
    return <p className="text-sm text-red-600">{(error as Error).message}</p>;
  if (!ticket) return null;

  function field<K extends keyof TicketUpdate>(key: K, value: TicketUpdate[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function save() {
    update.mutate({
      ...draft,
      suggested_team: draft.suggested_team || null,
      assignee: draft.assignee || null,
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="mb-2 flex items-start justify-between gap-4">
          <h1 className="text-lg font-semibold text-slate-900">{ticket.title}</h1>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <TriageSourceBadge source={ticket.triage_source} />
            {ticket.triage_confidence != null && (
              <ConfidenceBadge value={ticket.triage_confidence} />
            )}
          </div>
        </div>
        {ticket.triage_reason && (
          <p className="mb-2 text-xs text-slate-500">
            Triage note: {ticket.triage_reason}
          </p>
        )}
        <p className="whitespace-pre-wrap text-sm text-slate-600">
          {ticket.description}
        </p>
        <p className="mt-3 text-xs text-slate-400">
          Created {new Date(ticket.created_at).toLocaleString()} · Updated{" "}
          {new Date(ticket.updated_at).toLocaleString()}
        </p>
      </div>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-sm font-semibold text-slate-800">Triage &amp; assignment</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Status</Label>
            <Select
              value={draft.status ?? ""}
              onChange={(e) => field("status", e.target.value as TicketUpdate["status"])}
              className="w-full"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Priority</Label>
            <Select
              value={draft.priority ?? ""}
              onChange={(e) =>
                field("priority", e.target.value as TicketUpdate["priority"])
              }
              className="w-full"
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Category</Label>
            <Input
              value={draft.category ?? ""}
              onChange={(e) => field("category", e.target.value)}
            />
          </div>
          <div>
            <Label>Suggested team</Label>
            <Input
              value={draft.suggested_team ?? ""}
              onChange={(e) => field("suggested_team", e.target.value)}
            />
          </div>
          <div>
            <Label>Assignee</Label>
            <Input
              value={draft.assignee ?? ""}
              onChange={(e) => field("assignee", e.target.value)}
              placeholder="unassigned"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button onClick={save} disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => retriage.mutate()}
            disabled={retriage.isPending}
          >
            {retriage.isPending ? "Re-triaging…" : "Re-run AI triage"}
          </Button>
          <div className="flex-1" />
          <Button
            variant="danger"
            onClick={() => {
              if (confirm("Delete this ticket?")) {
                del.mutate(ticket.id, { onSuccess: () => navigate("/") });
              }
            }}
          >
            Delete
          </Button>
        </div>
        {update.isSuccess && (
          <p className="text-xs text-emerald-600">Saved.</p>
        )}
      </div>

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-sm font-semibold text-slate-800">History</h2>
        {!events || events.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <ol className="space-y-3">
            {events.map((ev) => {
              const style = EVENT_STYLES[ev.event_type];
              return (
                <li key={ev.id} className="flex gap-3">
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.dot}`}
                  />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700">
                      <span className="font-medium">{style.label}</span> ·{" "}
                      {ev.summary}
                    </p>
                    <p className="text-xs text-slate-400">
                      {new Date(ev.created_at).toLocaleString()}
                      {ev.actor ? ` · ${ev.actor}` : ""}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
}

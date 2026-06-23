import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import {
  PriorityBadge,
  TriageSourceBadge,
} from "../components/badges";
import { Button, Input, Label, Textarea } from "../components/ui";
import { useCreateTicket } from "../lib/queries";
import type { TicketCreate } from "../types";

export function CreateTicketPage() {
  const navigate = useNavigate();
  const create = useCreateTicket();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TicketCreate>();

  function onSubmit(values: TicketCreate) {
    create.mutate(values);
  }

  // After creation we show the triage result inline so the agent can see what
  // the AI suggested before navigating to edit it — human-in-the-loop.
  const created = create.data;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
      >
        <div>
          <Label>Title</Label>
          <Input
            placeholder="Short summary of the issue"
            {...register("title", { required: "Title is required" })}
          />
          {errors.title && (
            <p className="mt-1 text-xs text-red-600">{errors.title.message}</p>
          )}
        </div>
        <div>
          <Label>Description</Label>
          <Textarea
            rows={6}
            placeholder="What is happening? Who is affected? Any error messages?"
            {...register("description", { required: "Description is required" })}
          />
          {errors.description && (
            <p className="mt-1 text-xs text-red-600">{errors.description.message}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Creating & triaging…" : "Create ticket"}
          </Button>
          {create.isError && (
            <span className="text-sm text-red-600">
              {(create.error as Error).message}
            </span>
          )}
        </div>
      </form>

      {created && (
        <div className="space-y-3 rounded-lg border border-violet-200 bg-violet-50 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">
              Ticket created — AI first-pass triage
            </h2>
            <TriageSourceBadge source={created.triage_source} />
          </div>
          {created.triage_source === "fallback" ? (
            <p className="text-sm text-slate-600">
              The model was unavailable or unsure, so this ticket landed as{" "}
              <strong>uncategorised</strong> for manual triage. Open it to set the
              fields yourself.
              {created.triage_reason && (
                <span className="block text-xs text-slate-500">
                  Reason: {created.triage_reason}
                </span>
              )}
            </p>
          ) : (
            <dl className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="text-xs uppercase text-slate-500">Category</dt>
                <dd className="font-medium">{created.category}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Priority</dt>
                <dd><PriorityBadge priority={created.priority} /></dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-slate-500">Suggested team</dt>
                <dd className="font-medium">{created.suggested_team ?? "—"}</dd>
              </div>
            </dl>
          )}
          <p className="text-xs text-slate-500">
            These are suggestions. Confirm or override them on the ticket page.
          </p>
          <div className="flex gap-3">
            <Button onClick={() => navigate(`/tickets/${created.id}`)}>
              Review &amp; confirm
            </Button>
            <Button variant="secondary" onClick={() => navigate("/")}>
              Back to list
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";

import {
  PriorityBadge,
  StatusBadge,
  TriageSourceBadge,
} from "../components/badges";
import { Button, Input, Select } from "../components/ui";
import { useTickets } from "../lib/queries";
import { PRIORITIES, STATUSES } from "../types";
import type { TicketFilters } from "../types";

export function TicketsPage() {
  const [filters, setFilters] = useState<TicketFilters>({});
  const { data: tickets, isLoading, isError, error } = useTickets(filters);

  function set<K extends keyof TicketFilters>(key: K, value: string) {
    setFilters((f) => ({ ...f, [key]: value || undefined }));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">Status</p>
          <Select value={filters.status ?? ""} onChange={(e) => set("status", e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">Priority</p>
          <Select value={filters.priority ?? ""} onChange={(e) => set("priority", e.target.value)}>
            <option value="">All</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">Category</p>
          <Input
            placeholder="e.g. VPN"
            value={filters.category ?? ""}
            onChange={(e) => set("category", e.target.value)}
          />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">Assignee</p>
          <Input
            placeholder="e.g. alice"
            value={filters.assignee ?? ""}
            onChange={(e) => set("assignee", e.target.value)}
          />
        </div>
        <Button variant="ghost" onClick={() => setFilters({})}>
          Clear
        </Button>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading tickets…</p>}
      {isError && (
        <p className="text-sm text-red-600">Failed to load: {(error as Error).message}</p>
      )}

      {tickets && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Priority</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2">Team</th>
                <th className="px-4 py-2">Assignee</th>
                <th className="px-4 py-2">Triage</th>
              </tr>
            </thead>
            <tbody>
              {tickets.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                    No tickets match these filters.
                  </td>
                </tr>
              )}
              {tickets.map((t) => (
                <tr key={t.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <Link to={`/tickets/${t.id}`} className="font-medium text-slate-900 hover:underline">
                      {t.title}
                    </Link>
                  </td>
                  <td className="px-4 py-2"><StatusBadge status={t.status} /></td>
                  <td className="px-4 py-2"><PriorityBadge priority={t.priority} /></td>
                  <td className="px-4 py-2 text-slate-600">{t.category}</td>
                  <td className="px-4 py-2 text-slate-600">{t.suggested_team ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{t.assignee ?? "—"}</td>
                  <td className="px-4 py-2"><TriageSourceBadge source={t.triage_source} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

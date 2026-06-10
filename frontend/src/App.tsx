import { Link, Route, Routes } from "react-router-dom";

import { Button } from "./components/ui";
import { CreateTicketPage } from "./pages/CreateTicketPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { TicketsPage } from "./pages/TicketsPage";

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-tight">TriageAI</span>
            <span className="rounded bg-violet-100 px-1.5 py-0.5 text-xs font-medium text-violet-700">
              helpdesk
            </span>
          </Link>
          <Link to="/new">
            <Button>New ticket</Button>
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-6">
        <Routes>
          <Route path="/" element={<TicketsPage />} />
          <Route path="/new" element={<CreateTicketPage />} />
          <Route path="/tickets/:id" element={<TicketDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}

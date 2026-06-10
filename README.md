# TriageAI

An internal IT support helpdesk where agents own the full ticket lifecycle and an
LLM does the **first-pass triage** of every new ticket — suggesting a category,
priority, and target team. Every AI output is a *suggestion with a human in the
loop*: the agent confirms or overrides it, and the app stays fully usable when the
model is down.

This repo is the v1 (MVP) described in the PRD: ticket CRUD + a responsible AI
triage layer.

## Stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | React + Vite + TypeScript, TanStack Query, React Hook Form, Tailwind |
| Backend   | FastAPI, Pydantic, SQLAlchemy 2.0, Alembic |
| Database  | PostgreSQL |
| AI        | Anthropic Claude API, tool use for structured output |
| Infra     | Docker Compose (Postgres + API) |

## Architecture

```
React SPA  ──HTTP/JSON──▶  FastAPI  ──▶  PostgreSQL
                              │
                              └──▶  Triage service ──▶  Anthropic API
                                   (validation + fallback)   (tool output)
```

The **triage service** (`backend/app/triage/`) is the single, isolated boundary to
the non-deterministic LLM. It is the only place that talks to Anthropic, it never
raises, and it always returns either a schema-valid `ai` suggestion or an explicit
`fallback`. That keeps the route handlers plain CRUD and makes the fallback logic
unit-testable without a network (`backend/tests/test_triage.py`).

### Responsible-AI design (the part that matters)

1. **Structured output, not free text** — the model is forced to call a
   `submit_triage` tool with a JSON schema; the response is parsed as data.
2. **Schema validation at the boundary** — output is validated against a Pydantic
   model (`TriageSuggestion`) before it can touch the database.
3. **Confidence-gated fallback** — low confidence, a timeout, an API error, or
   off-schema output → the ticket is still created, as `uncategorised` with
   `triage_source = fallback`. **Ticket creation never depends on the LLM.**
4. **Human in the loop** — suggestions are pre-filled and editable; the agent's
   save is what commits them. Editing a triage field flips `triage_source` to
   `manual`.
5. **Bounded & cheap** — one call per ticket, capped tokens, no retry loops.

## Running it

### 1. Backend + database (Docker Compose)

```bash
# Optional: enable real triage. Without a key, every ticket falls back to manual.
export ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

This starts Postgres and the API (which runs `alembic upgrade head` on boot).
API at <http://localhost:8000>, interactive docs at <http://localhost:8000/docs>.

### 2. Frontend (local dev)

```bash
cd frontend
npm install
npm run dev
```

SPA at <http://localhost:5173>. The Vite dev server proxies `/api` → the API.

### Running the backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set DATABASE_URL + ANTHROPIC_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pip install pytest
python -m pytest                # triage fallback contract, no network needed
```

## API

| Method | Path                      | Purpose |
|--------|---------------------------|---------|
| POST   | `/tickets`                | Create ticket; runs triage; returns ticket with suggestions |
| GET    | `/tickets`                | List with filters: `status`, `priority`, `category`, `assignee` |
| GET    | `/tickets/{id}`           | Ticket detail |
| PATCH  | `/tickets/{id}`           | Update status / priority / category / team / assignee |
| DELETE | `/tickets/{id}`           | Delete |
| POST   | `/tickets/{id}/retriage`  | Re-run triage on demand |
| GET    | `/health`                 | Liveness + triage config |

## Configuration

Backend env vars (see `backend/.env.example`):

| Var | Default | Notes |
|-----|---------|-------|
| `DATABASE_URL` | local Postgres | SQLAlchemy URL |
| `TRIAGE_ENABLED` | `true` | Set `false` to disable the LLM entirely (always fallback) |
| `ANTHROPIC_API_KEY` | — | Without it, triage always falls back |
| `TRIAGE_MODEL` | `claude-haiku-4-5-20251001` | Cheap, bounded classification |
| `TRIAGE_TIMEOUT_SECONDS` | `12` | Hard wall on the external call |
| `TRIAGE_CONFIDENCE_THRESHOLD` | `0.6` | Below this → manual fallback |

## Out of scope (v1)

Auth, reply drafting, comments/activity log, and Redis-backed async triage are
deliberately deferred to v2 — see the PRD. v1 runs triage synchronously on create,
which is fine for a single-agent demo.

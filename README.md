# AI Ticket Triage

An internal IT support helpdesk where agents own the full ticket lifecycle and an
LLM does the **first-pass triage** of every new ticket - suggesting a category,
priority, and target team. Every AI output is a *suggestion with a human in the
loop*: the agent confirms or overrides it, and the app stays fully usable when the
model is down.


## Stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | React + Vite + TypeScript, React Hook Form, Tailwind |
| Backend   | FastAPI, Pydantic, SQLAlchemy 2.0, Alembic |
| Database  | PostgreSQL |
| AI        | Anthropic Claude API |
| Auth      | JWT |
| Async     | Redis |
| Infra     | Docker Compose (Postgres + Redis + API + worker) |

The **triage service** (`backend/app/triage/`) is the single, isolated boundary to
the non-deterministic LLM. It is the only place that talks to Anthropic, it never
raises, and it always returns either a schema-valid `ai` suggestion or an explicit
`fallback`. That keeps the route handlers plain CRUD and makes the fallback logic
unit-testable without a network (`backend/tests/test_triage.py`).

### Features & Design

1. **Structured output, not free text** - the model is forced to call a
   `submit_triage` tool with a JSON schema; the response is parsed as data.
2. **Schema validation at the boundary** - output is validated against a Pydantic
   model (`TriageSuggestion`) before it can touch the database.
3. **Confidence-gated fallback** - low confidence, a timeout, an API error, or
   off-schema output → the ticket is still created, as `uncategorised` with
   `triage_source = fallback`. **Ticket creation never depends on the LLM.**
4. **Human in the loop** - suggestions are pre-filled and editable; the agent's
   save is what commits them. Editing a triage field flips `triage_source` to
   `manual`.
5. **Bounded & cheap** - one call per ticket, capped tokens, no retry loops.
6. **Triage evidence** - the confidence and fallback reason the service computes
   are now persisted on the ticket and shown in the UI (a confidence chip + a
   triage note), so a low-confidence fallback explains itself.
7. **Audit / activity log** - an append-only `ticket_events` timeline records
   every AI suggestion, fallback, manual override, status change, re-triage,
   reply draft, and comment (`GET /tickets/{id}/events`). Events are written in
   the same transaction as the change, so the log can never disagree with state.
8. **Auth** - feature-flagged JWT auth (`AUTH_ENABLED`). When on, mutations
   require a bearer token and the audit log records the real agent as the actor;
   when off, the single-agent demo runs open. Password hashing is pbkdf2_sha256.
9. **AI reply drafting** - a second responsible-AI feature that *mirrors the
   triage boundary verbatim* (forced structured output via a `submit_draft`
   tool, Pydantic validation, a never-raises confidence-gated fallback). It only
   ever returns a draft for the agent to edit - `POST /tickets/{id}/draft-reply`.
10. **Comments** - a reply thread (`/tickets/{id}/comments`). A reply that began
   as an AI draft is marked `ai_assisted`, closing the human-in-the-loop loop.
11. **Async triage** - with `ASYNC_TRIAGE_ENABLED`, create returns instantly as a
   `fallback` ("queued for triage"), enqueues a job to Redis, and an RQ worker
   runs the **unchanged** triage service and fills it in. This makes the
   "creation never depends on the LLM" invariant structural; the triage service
   itself is untouched - only the caller moves to a worker thread.

## Installation

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
| GET    | `/tickets/{id}/events`    | Activity log (audit timeline) |
| POST   | `/tickets/{id}/draft-reply` | AI-draft a reply (suggestion only) |
| GET    | `/tickets/{id}/comments`  | List replies |
| POST   | `/tickets/{id}/comments`  | Post a reply (`human` or `ai_assisted`) |
| POST   | `/auth/register`          | Create an agent account |
| POST   | `/auth/login`             | Exchange credentials for a JWT |
| GET    | `/auth/me`                | Current authenticated agent |
| GET    | `/health`                 | Liveness + triage/auth config |

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
| `REPLY_ENABLED` | `true` | Toggle AI reply drafting |
| `REPLY_MODEL` | `claude-haiku-4-5-20251001` | Model for draft replies |
| `REPLY_CONFIDENCE_THRESHOLD` | `0.5` | Below this → empty editable draft |
| `AUTH_ENABLED` | `false` | Require JWT on mutations; record actor in the log |
| `JWT_SECRET` | dev default | HMAC secret — set a real one in production |
| `ASYNC_TRIAGE_ENABLED` | `false` | Defer triage to the Redis/RQ worker |
| `REDIS_URL` | `redis://localhost:6379/0` | Broker for async triage |


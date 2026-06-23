"""Data-access layer. Route handlers call these; they stay free of LLM concerns
except for the one explicit call into the triage service on create."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import TicketPriority, TicketStatus, TriageSource
from app.models import Ticket
from app.schemas import TicketCreate, TicketUpdate
from app.triage import TriageOutcome, triage_ticket


def _apply_triage_outcome(ticket: Ticket, outcome: TriageOutcome) -> None:
    """Copy a triage outcome onto a ticket, including the evidence
    (confidence + reason) the service computes. Persisting these makes the
    schema-validation + low-confidence-fallback story auditable in the product."""
    ticket.priority = outcome.priority
    ticket.category = outcome.category
    ticket.suggested_team = outcome.suggested_team
    ticket.triage_source = outcome.source
    ticket.triage_confidence = outcome.confidence
    ticket.triage_reason = outcome.reason
    ticket.triaged_at = func.now()


def create_ticket(db: Session, payload: TicketCreate) -> Ticket:
    """Create a ticket. Triage runs here but creation never depends on it
    succeeding — a failed/low-confidence triage just yields a fallback outcome."""
    outcome = triage_ticket(payload.title, payload.description)

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        status=TicketStatus.open,
    )
    _apply_triage_outcome(ticket, outcome)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category: str | None = None,
    assignee: str | None = None,
) -> list[Ticket]:
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if category is not None:
        stmt = stmt.where(Ticket.category == category)
    if assignee is not None:
        stmt = stmt.where(Ticket.assignee == assignee)
    stmt = stmt.order_by(Ticket.created_at.desc())
    return list(db.scalars(stmt).all())


def get_ticket(db: Session, ticket_id: uuid.UUID) -> Ticket | None:
    return db.get(Ticket, ticket_id)


def update_ticket(db: Session, ticket: Ticket, payload: TicketUpdate) -> Ticket:
    """Apply a partial update. Any agent edit to a triage field flips
    triage_source to `manual` — the human is now the source of truth."""
    data = payload.model_dump(exclude_unset=True)

    triage_fields = {"priority", "category", "suggested_team"}
    if triage_fields & data.keys():
        ticket.triage_source = TriageSource.manual
        # The AI's confidence no longer describes the stored value — keep the
        # data honest about the human now being the source of truth.
        ticket.triage_confidence = None
        ticket.triage_reason = "manual override"

    for field, value in data.items():
        setattr(ticket, field, value)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket: Ticket) -> None:
    db.delete(ticket)
    db.commit()


def retriage_ticket(db: Session, ticket: Ticket) -> Ticket:
    """Re-run triage on demand for an existing ticket."""
    outcome = triage_ticket(ticket.title, ticket.description)
    _apply_triage_outcome(ticket, outcome)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

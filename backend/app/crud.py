"""Data-access layer. Route handlers call these; they stay free of LLM concerns
except for the one explicit call into the triage service on create."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TicketPriority, TicketStatus, TriageSource
from app.models import Ticket
from app.schemas import TicketCreate, TicketUpdate
from app.triage import triage_ticket


def create_ticket(db: Session, payload: TicketCreate) -> Ticket:
    """Create a ticket. Triage runs here but creation never depends on it
    succeeding — a failed/low-confidence triage just yields a fallback outcome."""
    outcome = triage_ticket(payload.title, payload.description)

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        status=TicketStatus.open,
        priority=outcome.priority,
        category=outcome.category,
        suggested_team=outcome.suggested_team,
        triage_source=outcome.source,
    )
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
    ticket.priority = outcome.priority
    ticket.category = outcome.category
    ticket.suggested_team = outcome.suggested_team
    ticket.triage_source = outcome.source
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

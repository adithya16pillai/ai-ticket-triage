"""Activity log — a thin, deterministic helper. No LLM, no commit of its own.

Events are added to the session by the CRUD function performing a mutation, so
they land in the *same* transaction and the audit trail can never disagree with
the ticket state it describes.
"""
from sqlalchemy.orm import Session

from app.enums import TicketEventType
from app.models import Ticket, TicketEvent
from app.triage import TriageOutcome


def record_event(
    db: Session,
    ticket: Ticket,
    event_type: TicketEventType,
    summary: str,
    *,
    payload: dict | None = None,
    actor: str | None = None,
) -> TicketEvent:
    """Append an audit entry. Uses the relationship so the FK resolves on flush
    even for a still-pending (just-created) ticket."""
    event = TicketEvent(
        ticket=ticket,
        event_type=event_type,
        summary=summary,
        payload=payload,
        actor=actor,
    )
    db.add(event)
    return event


def triage_payload(outcome: TriageOutcome) -> dict:
    """Structured snapshot of a triage outcome for an event's payload."""
    return {
        "category": outcome.category,
        "priority": outcome.priority.value,
        "suggested_team": outcome.suggested_team,
        "source": outcome.source.value,
        "confidence": outcome.confidence,
        "reason": outcome.reason,
    }

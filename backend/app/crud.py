"""Data-access layer. Route handlers call these; they stay free of LLM concerns
except for the one explicit call into the triage service on create."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activity import record_event, triage_payload
from app.enums import TicketEventType, TicketPriority, TicketStatus, TriageSource
from app.models import Ticket, TicketEvent
from app.reply import ReplyDraftOutcome, draft_reply
from app.schemas import TicketCreate, TicketUpdate
from app.triage import TriageOutcome, triage_ticket


def _triage_summary(outcome: TriageOutcome) -> str:
    if outcome.source == TriageSource.ai:
        conf = f"{outcome.confidence:.2f}" if outcome.confidence is not None else "n/a"
        return (
            f"AI triaged as {outcome.category} / {outcome.priority.value} "
            f"(confidence {conf})"
        )
    return f"Triage fell back to manual: {outcome.reason or 'unknown'}"


def _record_triage_event(
    db: Session,
    ticket: Ticket,
    outcome: TriageOutcome,
    *,
    event_type: TicketEventType,
    actor: str | None,
) -> None:
    """Audit a triage outcome. AI outcomes use the given event type; fallbacks
    are always logged as triage_fallback so the manual queue is visible."""
    etype = (
        event_type if outcome.source == TriageSource.ai else TicketEventType.triage_fallback
    )
    record_event(
        db,
        ticket,
        etype,
        _triage_summary(outcome),
        payload=triage_payload(outcome),
        actor=actor,
    )


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


def create_ticket(
    db: Session, payload: TicketCreate, *, actor: str | None = None
) -> Ticket:
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
    # One event on create so the timeline opens with an unambiguous first entry
    # (no two-events-share-a-timestamp ordering question).
    etype = (
        TicketEventType.triaged
        if outcome.source == TriageSource.ai
        else TicketEventType.triage_fallback
    )
    record_event(
        db,
        ticket,
        etype,
        f"Ticket created — {_triage_summary(outcome)}",
        payload=triage_payload(outcome),
        actor=actor,
    )
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


def _enum_value(v):
    return v.value if hasattr(v, "value") else v


def update_ticket(
    db: Session, ticket: Ticket, payload: TicketUpdate, *, actor: str | None = None
) -> Ticket:
    """Apply a partial update. Any agent edit to a triage field flips
    triage_source to `manual` — the human is now the source of truth."""
    data = payload.model_dump(exclude_unset=True)

    triage_fields = {"priority", "category", "suggested_team"}
    overridden = triage_fields & data.keys()

    # Snapshot before/after for the audit trail of human-in-the-loop edits.
    before = {k: _enum_value(getattr(ticket, k)) for k in data}

    if overridden:
        ticket.triage_source = TriageSource.manual
        # The AI's confidence no longer describes the stored value — keep the
        # data honest about the human now being the source of truth.
        ticket.triage_confidence = None
        ticket.triage_reason = "manual override"

    for field, value in data.items():
        setattr(ticket, field, value)

    after = {k: _enum_value(getattr(ticket, k)) for k in data}

    if overridden:
        record_event(
            db,
            ticket,
            TicketEventType.manual_override,
            "Agent overrode triage fields",
            payload={
                "before": {k: before[k] for k in triage_fields & data.keys()},
                "after": {k: after[k] for k in triage_fields & data.keys()},
            },
            actor=actor,
        )
    if "status" in data and before["status"] != after["status"]:
        record_event(
            db,
            ticket,
            TicketEventType.status_changed,
            f"Status {before['status']} -> {after['status']}",
            payload={"before": before["status"], "after": after["status"]},
            actor=actor,
        )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket: Ticket) -> None:
    db.delete(ticket)
    db.commit()


def retriage_ticket(
    db: Session, ticket: Ticket, *, actor: str | None = None
) -> Ticket:
    """Re-run triage on demand for an existing ticket."""
    outcome = triage_ticket(ticket.title, ticket.description)
    _apply_triage_outcome(ticket, outcome)
    db.add(ticket)
    _record_triage_event(
        db, ticket, outcome, event_type=TicketEventType.retriaged, actor=None
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def draft_ticket_reply(
    db: Session, ticket: Ticket, *, actor: str | None = None
) -> ReplyDraftOutcome:
    """Generate an AI reply draft for an agent to edit. Persists/sends nothing —
    it only returns the suggestion and records that a draft was produced."""
    outcome = draft_reply(ticket.title, ticket.description)

    if outcome.source == TriageSource.ai:
        conf = f"{outcome.confidence:.2f}" if outcome.confidence is not None else "n/a"
        summary = f"AI drafted a reply (confidence {conf})"
    else:
        summary = f"Reply draft fell back: {outcome.reason or 'unknown'}"

    record_event(
        db,
        ticket,
        TicketEventType.draft_generated,
        summary,
        payload={
            "source": outcome.source.value,
            "confidence": outcome.confidence,
            "reason": outcome.reason,
            "needs_human_review": outcome.needs_human_review,
            "tone": outcome.tone,
        },
        actor=actor,
    )
    db.commit()
    return outcome


def list_ticket_events(db: Session, ticket_id: uuid.UUID) -> list[TicketEvent]:
    stmt = (
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at.desc(), TicketEvent.id.desc())
    )
    return list(db.scalars(stmt).all())

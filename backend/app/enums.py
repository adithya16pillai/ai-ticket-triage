"""Domain enums shared by the ORM model, Pydantic schemas, and triage service."""
from enum import Enum


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TriageSource(str, Enum):
    ai = "ai"          # suggestion came from a validated LLM call
    manual = "manual"  # an agent set / overrode the triage
    fallback = "fallback"  # LLM unavailable or low-confidence -> manual queue


class TicketEventType(str, Enum):
    """Append-only audit trail entries — the readable record of the AI
    suggestion + human-in-the-loop story for a ticket."""
    created = "created"
    triaged = "triaged"                # validated AI suggestion applied
    triage_fallback = "triage_fallback"  # AI unavailable/low-confidence -> manual
    manual_override = "manual_override"  # agent edited a triage field
    status_changed = "status_changed"
    retriaged = "retriaged"            # triage re-run on demand
    draft_generated = "draft_generated"  # AI reply draft produced (F4)
    comment = "comment"               # a reply was posted (F5)


UNCATEGORISED = "uncategorised"

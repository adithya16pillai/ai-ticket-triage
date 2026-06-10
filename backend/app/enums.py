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


UNCATEGORISED = "uncategorised"

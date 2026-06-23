"""Pydantic request/response models — the API boundary."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import TicketEventType, TicketPriority, TicketStatus, TriageSource


class TicketCreate(BaseModel):
    """Minimum to open a ticket. Triage fills the rest, agent can override."""
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)


class TicketUpdate(BaseModel):
    """Partial update — any field an agent can edit on the detail view.

    Setting any of these marks the ticket as manually triaged.
    """
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, min_length=1)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = Field(default=None, min_length=1, max_length=120)
    suggested_team: str | None = Field(default=None, max_length=120)
    assignee: str | None = Field(default=None, max_length=120)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str
    suggested_team: str | None
    assignee: str | None
    triage_source: TriageSource
    triage_confidence: float | None
    triage_reason: str | None
    triaged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TicketEventRead(BaseModel):
    """One audit-trail entry for a ticket."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    event_type: TicketEventType
    summary: str
    payload: dict | None
    actor: str | None
    created_at: datetime

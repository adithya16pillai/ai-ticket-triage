"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import monotonic_now
from app.database import Base
from app.enums import (
    TicketEventType,
    TicketPriority,
    TicketStatus,
    TriageSource,
    UNCATEGORISED,
)

# JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB, "postgresql")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        nullable=False,
        default=TicketStatus.open,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"),
        nullable=False,
        default=TicketPriority.medium,
    )
    category: Mapped[str] = mapped_column(
        String(120), nullable=False, default=UNCATEGORISED
    )
    suggested_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)

    triage_source: Mapped[TriageSource] = mapped_column(
        Enum(TriageSource, name="triage_source"),
        nullable=False,
        default=TriageSource.fallback,
    )

    # Triage evidence — the confidence and reason the service already computes.
    # Persisted (not just logged) so the validation + fallback story is auditable.
    triage_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    triage_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
    )


class TicketEvent(Base):
    """One append-only audit entry for a ticket. Written in the same transaction
    as the mutation it describes, so the log can never disagree with state."""

    __tablename__ = "ticket_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[TicketEventType] = mapped_column(
        Enum(TicketEventType, name="ticket_event_type"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured detail: triage outcome, before/after diffs, draft confidence, etc.
    payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Process-monotonic default so the timeline orders deterministically even
    # when several events share a transaction / OS clock tick.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=monotonic_now,
        server_default=func.now(),
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="events")

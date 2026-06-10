"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import TicketPriority, TicketStatus, TriageSource, UNCATEGORISED


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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

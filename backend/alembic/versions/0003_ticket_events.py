"""ticket events audit log

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ticket_event_type = postgresql.ENUM(
        "created",
        "triaged",
        "triage_fallback",
        "manual_override",
        "status_changed",
        "retriaged",
        "draft_generated",
        "comment",
        name="ticket_event_type",
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", ticket_event_type, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_events_ticket_id", table_name="ticket_events")
    op.drop_table("ticket_events")
    sa.Enum(name="ticket_event_type").drop(op.get_bind(), checkfirst=True)

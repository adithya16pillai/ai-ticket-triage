"""initial tickets table

Revision ID: 0001
Revises:
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ticket_status = postgresql.ENUM(
        "open", "in_progress", "resolved", name="ticket_status"
    )
    ticket_priority = postgresql.ENUM(
        "low", "medium", "high", "urgent", name="ticket_priority"
    )
    triage_source = postgresql.ENUM(
        "ai", "manual", "fallback", name="triage_source"
    )

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="open"),
        sa.Column(
            "priority", ticket_priority, nullable=False, server_default="medium"
        ),
        sa.Column(
            "category",
            sa.String(length=120),
            nullable=False,
            server_default="uncategorised",
        ),
        sa.Column("suggested_team", sa.String(length=120), nullable=True),
        sa.Column("assignee", sa.String(length=120), nullable=True),
        sa.Column(
            "triage_source",
            triage_source,
            nullable=False,
            server_default="fallback",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_assignee", "tickets", ["assignee"])


def downgrade() -> None:
    op.drop_index("ix_tickets_assignee", table_name="tickets")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
    sa.Enum(name="triage_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticket_priority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticket_status").drop(op.get_bind(), checkfirst=True)

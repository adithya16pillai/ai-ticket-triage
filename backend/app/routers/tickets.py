"""Ticket CRUD routes. Plain handlers — the only non-determinism (the LLM)
lives behind crud.create_ticket -> triage service."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.auth.deps import current_actor
from app.database import get_db
from app.enums import TicketPriority, TicketStatus
from app.schemas import (
    CommentCreate,
    CommentRead,
    ReplyDraftRead,
    TicketCreate,
    TicketEventRead,
    TicketRead,
    TicketUpdate,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    actor: str | None = Depends(current_actor),
) -> TicketRead:
    return crud.create_ticket(db, payload, actor=actor)


@router.get("", response_model=list[TicketRead])
def list_tickets(
    db: Session = Depends(get_db),
    status_: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: str | None = None,
    assignee: str | None = None,
) -> list[TicketRead]:
    return crud.list_tickets(
        db, status=status_, priority=priority, category=category, assignee=assignee
    )


def _get_or_404(db: Session, ticket_id: uuid.UUID):
    ticket = crud.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db)) -> TicketRead:
    return _get_or_404(db, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    actor: str | None = Depends(current_actor),
) -> TicketRead:
    ticket = _get_or_404(db, ticket_id)
    return crud.update_ticket(db, ticket, payload, actor=actor)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    ticket = _get_or_404(db, ticket_id)
    crud.delete_ticket(db, ticket)


@router.post("/{ticket_id}/retriage", response_model=TicketRead)
def retriage_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: str | None = Depends(current_actor),
) -> TicketRead:
    ticket = _get_or_404(db, ticket_id)
    return crud.retriage_ticket(db, ticket, actor=actor)


@router.post("/{ticket_id}/draft-reply", response_model=ReplyDraftRead)
def draft_reply(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: str | None = Depends(current_actor),
) -> ReplyDraftRead:
    ticket = _get_or_404(db, ticket_id)
    outcome = crud.draft_ticket_reply(db, ticket, actor=actor)
    return ReplyDraftRead(
        reply_text=outcome.reply_text,
        tone=outcome.tone,
        needs_human_review=outcome.needs_human_review,
        triage_source=outcome.source,
        confidence=outcome.confidence,
        reason=outcome.reason,
    )


@router.get("/{ticket_id}/events", response_model=list[TicketEventRead])
def list_ticket_events(
    ticket_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[TicketEventRead]:
    _get_or_404(db, ticket_id)
    return crud.list_ticket_events(db, ticket_id)


@router.get("/{ticket_id}/comments", response_model=list[CommentRead])
def list_comments(
    ticket_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[CommentRead]:
    _get_or_404(db, ticket_id)
    return crud.list_comments(db, ticket_id)


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    actor: str | None = Depends(current_actor),
) -> CommentRead:
    ticket = _get_or_404(db, ticket_id)
    return crud.add_comment(db, ticket, payload, actor=actor)

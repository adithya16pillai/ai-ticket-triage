"""Comment thread tests (Feature 5)."""
from app import crud
from app.enums import CommentSource, TicketEventType, TicketPriority, TriageSource
from app.schemas import CommentCreate, TicketCreate
from app.triage import TriageOutcome


def _make_ticket(db, monkeypatch):
    monkeypatch.setattr(
        crud,
        "triage_ticket",
        lambda *a, **k: TriageOutcome(
            category="VPN",
            priority=TicketPriority.high,
            suggested_team="Networking",
            source=TriageSource.ai,
            confidence=0.9,
            reason="ok",
        ),
    )
    return crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))


def test_add_and_list_comments_in_order(db, monkeypatch):
    ticket = _make_ticket(db, monkeypatch)
    crud.add_comment(db, ticket, CommentCreate(body="first"), actor="alice")
    crud.add_comment(db, ticket, CommentCreate(body="second"), actor="bob")

    comments = crud.list_comments(db, ticket.id)
    assert [c.body for c in comments] == ["first", "second"]
    assert comments[0].author == "alice"


def test_ai_assisted_flag_persists(db, monkeypatch):
    ticket = _make_ticket(db, monkeypatch)
    crud.add_comment(
        db,
        ticket,
        CommentCreate(body="edited AI draft", source=CommentSource.ai_assisted),
    )
    comment = crud.list_comments(db, ticket.id)[0]
    assert comment.source == CommentSource.ai_assisted


def test_comment_writes_event(db, monkeypatch):
    ticket = _make_ticket(db, monkeypatch)
    crud.add_comment(db, ticket, CommentCreate(body="hi"))

    events = crud.list_ticket_events(db, ticket.id)
    assert events[0].event_type == TicketEventType.comment


def test_comments_cascade_delete(db, monkeypatch):
    ticket = _make_ticket(db, monkeypatch)
    crud.add_comment(db, ticket, CommentCreate(body="hi"))
    tid = ticket.id

    crud.delete_ticket(db, ticket)
    assert crud.list_comments(db, tid) == []

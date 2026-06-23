"""Audit-log tests (Feature 2). Triage is monkeypatched; assert the right
TicketEvent rows and payloads are written in the same transaction as the change.
"""
from app import crud
from app.enums import TicketEventType, TicketPriority, TicketStatus, TriageSource
from app.schemas import TicketCreate, TicketUpdate
from app.triage import TriageOutcome


def _ai_outcome():
    return TriageOutcome(
        category="VPN",
        priority=TicketPriority.high,
        suggested_team="Networking",
        source=TriageSource.ai,
        confidence=0.92,
        reason="ok",
    )


def test_create_ai_writes_triaged_event(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    events = crud.list_ticket_events(db, ticket.id)
    assert len(events) == 1
    assert events[0].event_type == TicketEventType.triaged
    assert events[0].payload["confidence"] == 0.92
    assert events[0].payload["source"] == "ai"


def test_create_fallback_writes_fallback_event(db, monkeypatch):
    monkeypatch.setattr(
        crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("low confidence 0.20")
    )
    ticket = crud.create_ticket(db, TicketCreate(title="help", description="broke"))

    events = crud.list_ticket_events(db, ticket.id)
    assert len(events) == 1
    assert events[0].event_type == TicketEventType.triage_fallback
    assert "low confidence" in events[0].summary


def test_manual_override_writes_event_with_diff(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    crud.update_ticket(
        db, ticket, TicketUpdate(priority=TicketPriority.urgent), actor="alice"
    )

    events = crud.list_ticket_events(db, ticket.id)  # newest first
    override = events[0]
    assert override.event_type == TicketEventType.manual_override
    assert override.actor == "alice"
    assert override.payload["before"]["priority"] == "high"
    assert override.payload["after"]["priority"] == "urgent"


def test_status_change_writes_event(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"))

    crud.update_ticket(db, ticket, TicketUpdate(status=TicketStatus.resolved))

    types = [e.event_type for e in crud.list_ticket_events(db, ticket.id)]
    assert TicketEventType.status_changed in types


def test_retriage_writes_event(db, monkeypatch):
    monkeypatch.setattr(
        crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("no key")
    )
    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"))

    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    crud.retriage_ticket(db, ticket)

    types = [e.event_type for e in crud.list_ticket_events(db, ticket.id)]
    assert types[0] == TicketEventType.retriaged


def test_events_cascade_delete_with_ticket(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"))
    tid = ticket.id
    assert crud.list_ticket_events(db, tid)

    crud.delete_ticket(db, ticket)
    assert crud.list_ticket_events(db, tid) == []

"""CRUD-level tests for triage evidence persistence (Feature 1).

The triage service is monkeypatched to return a known outcome, so these assert
the persistence wiring — that confidence/reason/source land on the row, and that
a manual override keeps the data honest.
"""
from app import crud
from app.enums import TicketPriority, TriageSource
from app.triage import TriageOutcome
from app.schemas import TicketCreate, TicketUpdate


def _ai_outcome():
    return TriageOutcome(
        category="VPN",
        priority=TicketPriority.high,
        suggested_team="Networking",
        source=TriageSource.ai,
        confidence=0.92,
        reason="ok",
    )


def test_create_persists_ai_evidence(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    assert ticket.triage_source == TriageSource.ai
    assert ticket.category == "VPN"
    assert ticket.triage_confidence == 0.92
    assert ticket.triage_reason == "ok"
    assert ticket.triaged_at is not None


def test_create_persists_fallback_reason(db, monkeypatch):
    monkeypatch.setattr(
        crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("low confidence 0.20")
    )
    ticket = crud.create_ticket(db, TicketCreate(title="help", description="it broke"))

    assert ticket.triage_source == TriageSource.fallback
    assert ticket.triage_confidence is None
    assert ticket.triage_reason == "low confidence 0.20"


def test_manual_override_clears_confidence(db, monkeypatch):
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    updated = crud.update_ticket(db, ticket, TicketUpdate(priority=TicketPriority.urgent))

    assert updated.triage_source == TriageSource.manual
    assert updated.triage_confidence is None
    assert updated.triage_reason == "manual override"


def test_retriage_refreshes_evidence(db, monkeypatch):
    monkeypatch.setattr(
        crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("no anthropic api key configured")
    )
    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"))
    assert ticket.triage_source == TriageSource.fallback

    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    retriaged = crud.retriage_ticket(db, ticket)

    assert retriaged.triage_source == TriageSource.ai
    assert retriaged.triage_confidence == 0.92
    assert retriaged.triage_reason == "ok"

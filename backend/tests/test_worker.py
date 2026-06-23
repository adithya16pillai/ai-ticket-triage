"""Async triage tests (Feature 6). No real Redis: enqueue is mocked, and the
job's core (crud.apply_triage_job) is tested directly with the test session.

The key invariant under test: in async mode, ticket creation never calls the LLM.
"""
import pytest

from app import crud
from app.config import settings
from app.enums import TicketEventType, TicketPriority, TriageSource
from app.schemas import TicketCreate
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


def test_async_create_is_fallback_and_enqueues_without_llm(db, monkeypatch):
    monkeypatch.setattr(settings, "async_triage_enabled", True)

    def _boom(*a, **k):
        raise AssertionError("triage_ticket must not be called on async create")

    monkeypatch.setattr(crud, "triage_ticket", _boom)

    enqueued = []
    monkeypatch.setattr(crud, "enqueue_triage", lambda tid: enqueued.append(tid))

    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    assert ticket.triage_source == TriageSource.fallback
    assert ticket.triage_reason == "queued for triage"
    assert ticket.category == "uncategorised"
    assert enqueued == [ticket.id]

    # The audit trail shows the queued creation.
    events = crud.list_ticket_events(db, ticket.id)
    assert events[0].event_type == TicketEventType.created


def test_apply_triage_job_transitions_fallback_to_ai(db, monkeypatch):
    monkeypatch.setattr(settings, "async_triage_enabled", True)
    monkeypatch.setattr(crud, "enqueue_triage", lambda tid: None)
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("x"))

    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))
    assert ticket.triage_source == TriageSource.fallback

    # The worker runs the (now mocked-AI) triage service against the ticket.
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: _ai_outcome())
    crud.apply_triage_job(db, ticket)

    assert ticket.triage_source == TriageSource.ai
    assert ticket.category == "VPN"
    assert ticket.triage_confidence == 0.92

    types = [e.event_type for e in crud.list_ticket_events(db, ticket.id)]
    assert types[0] == TicketEventType.triaged  # newest


def test_apply_triage_job_records_fallback_event(db, monkeypatch):
    monkeypatch.setattr(settings, "async_triage_enabled", True)
    monkeypatch.setattr(crud, "enqueue_triage", lambda tid: None)
    monkeypatch.setattr(crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("x"))
    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"))

    monkeypatch.setattr(
        crud, "triage_ticket", lambda *a, **k: TriageOutcome.fallback("no key")
    )
    crud.apply_triage_job(db, ticket)

    types = [e.event_type for e in crud.list_ticket_events(db, ticket.id)]
    assert types[0] == TicketEventType.triage_fallback


def test_enqueue_failure_is_swallowed(monkeypatch):
    """If Redis/RQ is unavailable, enqueue returns False rather than raising."""
    from app import queue

    def _broken():
        raise RuntimeError("redis down")

    monkeypatch.setattr(queue, "_get_queue", _broken)
    assert queue.enqueue_triage("some-id") is False

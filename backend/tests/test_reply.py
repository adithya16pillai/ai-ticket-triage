"""Tests for the reply-draft service's fallback contract — mirrors
test_triage.py. No network: the Anthropic client is stubbed.
"""
import types

from app.enums import TriageSource
from app.reply import service


def _fake_response(blocks):
    return types.SimpleNamespace(content=blocks)


def _tool_block(payload):
    return types.SimpleNamespace(type="tool_use", name="submit_draft", input=payload)


def _install_client(monkeypatch, response=None, exc=None):
    class FakeMessages:
        def create(self, **kwargs):
            if exc is not None:
                raise exc
            return response

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(service.settings, "reply_enabled", True)
    monkeypatch.setattr(service.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(service.settings, "reply_confidence_threshold", 0.5)
    monkeypatch.setattr(service, "_build_client", lambda: FakeClient())


def test_valid_high_confidence_is_ai(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [
                _tool_block(
                    {
                        "reply_text": "Hi, please try reconnecting to the VPN…",
                        "tone": "reassuring",
                        "needs_human_review": False,
                        "confidence": 0.88,
                    }
                )
            ]
        ),
    )
    out = service.draft_reply("VPN down", "drops every minute")
    assert out.source == TriageSource.ai
    assert out.reply_text.startswith("Hi")
    assert out.tone == "reassuring"


def test_low_confidence_falls_back(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [
                _tool_block(
                    {
                        "reply_text": "maybe try turning it off and on",
                        "tone": "neutral",
                        "needs_human_review": True,
                        "confidence": 0.20,
                    }
                )
            ]
        ),
    )
    out = service.draft_reply("help", "it broke")
    assert out.source == TriageSource.fallback
    assert out.reply_text == ""
    assert out.needs_human_review is True


def test_invalid_schema_falls_back(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [_tool_block({"reply_text": "hi", "confidence": 2.0})]  # bad confidence + missing
        ),
    )
    out = service.draft_reply("x", "y")
    assert out.source == TriageSource.fallback


def test_api_error_falls_back(monkeypatch):
    _install_client(monkeypatch, exc=RuntimeError("boom"))
    out = service.draft_reply("x", "y")
    assert out.source == TriageSource.fallback
    assert out.reply_text == ""


def test_disabled_skips_call(monkeypatch):
    monkeypatch.setattr(service.settings, "reply_enabled", False)
    out = service.draft_reply("x", "y")
    assert out.source == TriageSource.fallback


def test_draft_records_event(db, monkeypatch):
    """The crud seam records a draft_generated event in its own commit."""
    from app import crud
    from app.enums import TicketEventType, TicketPriority
    from app.schemas import TicketCreate
    from app.triage import TriageOutcome

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
    ticket = crud.create_ticket(db, TicketCreate(title="VPN down", description="drops"))

    monkeypatch.setattr(
        crud,
        "draft_reply",
        lambda *a, **k: service.ReplyDraftOutcome(
            reply_text="Hi there…",
            tone="neutral",
            needs_human_review=False,
            source=TriageSource.ai,
            confidence=0.8,
            reason="ok",
        ),
    )
    outcome = crud.draft_ticket_reply(db, ticket)
    assert outcome.reply_text == "Hi there…"

    events = crud.list_ticket_events(db, ticket.id)
    assert events[0].event_type == TicketEventType.draft_generated

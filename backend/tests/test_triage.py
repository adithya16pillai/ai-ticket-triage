"""Tests for the triage service's fallback contract — the testable payoff of
isolating the LLM boundary. No network: the Anthropic client is stubbed.

Run from the backend/ dir:  python -m pytest
"""
import types

import pytest

from app.enums import TriageSource, UNCATEGORISED
from app.triage import service


def _fake_response(blocks):
    return types.SimpleNamespace(content=blocks)


def _tool_block(payload):
    return types.SimpleNamespace(type="tool_use", name="submit_triage", input=payload)


def _install_client(monkeypatch, response=None, exc=None):
    class FakeMessages:
        def create(self, **kwargs):
            if exc is not None:
                raise exc
            return response

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(service.settings, "triage_enabled", True)
    monkeypatch.setattr(service.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(service.settings, "triage_confidence_threshold", 0.6)
    monkeypatch.setattr(service, "_build_client", lambda: FakeClient())


def test_valid_high_confidence_is_ai(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [
                _tool_block(
                    {
                        "category": "VPN",
                        "priority": "high",
                        "suggested_team": "Networking",
                        "confidence": 0.92,
                    }
                )
            ]
        ),
    )
    out = service.triage_ticket("Cannot connect to VPN", "VPN drops every minute")
    assert out.source == TriageSource.ai
    assert out.category == "VPN"
    assert out.priority.value == "high"


def test_low_confidence_falls_back(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [
                _tool_block(
                    {
                        "category": "Unclear",
                        "priority": "low",
                        "suggested_team": "General IT",
                        "confidence": 0.20,
                    }
                )
            ]
        ),
    )
    out = service.triage_ticket("help", "it broke")
    assert out.source == TriageSource.fallback
    assert out.category == UNCATEGORISED


def test_invalid_schema_falls_back(monkeypatch):
    _install_client(
        monkeypatch,
        response=_fake_response(
            [_tool_block({"category": "VPN", "priority": "EMERGENCY"})]  # bad enum + missing
        ),
    )
    out = service.triage_ticket("x", "y")
    assert out.source == TriageSource.fallback


def test_api_error_falls_back(monkeypatch):
    _install_client(monkeypatch, exc=RuntimeError("boom"))
    out = service.triage_ticket("x", "y")
    assert out.source == TriageSource.fallback
    assert out.category == UNCATEGORISED


def test_disabled_skips_call(monkeypatch):
    monkeypatch.setattr(service.settings, "triage_enabled", False)
    out = service.triage_ticket("x", "y")
    assert out.source == TriageSource.fallback

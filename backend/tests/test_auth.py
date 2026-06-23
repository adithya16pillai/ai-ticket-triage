"""Auth tests (Feature 3): hashing, token round-trip, and the actor wiring into
the audit log when auth is enabled.
"""
import jwt
import pytest

from app import crud
from app.auth import deps, service
from app.auth.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.enums import TicketEventType, TicketPriority, TriageSource
from app.schemas import TicketCreate, TicketUpdate
from app.triage import TriageOutcome


def test_password_hash_round_trip():
    hashed = hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed)
    assert not verify_password("wrong", hashed)


def test_token_round_trip():
    token = create_access_token("alice@example.com", {"name": "Alice"})
    payload = decode_token(token)
    assert payload["sub"] == "alice@example.com"
    assert payload["name"] == "Alice"


def test_decode_rejects_tampered_token():
    token = create_access_token("alice@example.com")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tampered")


def test_authenticate(db):
    service.create_user(
        db, email="a@b.com", password="password123", display_name="Agent A"
    )
    assert service.authenticate(db, "a@b.com", "password123") is not None
    assert service.authenticate(db, "a@b.com", "nope") is None
    assert service.authenticate(db, "missing@b.com", "password123") is None


def test_get_current_user_resolves_token(db):
    user = service.create_user(
        db, email="a@b.com", password="password123", display_name="Agent A"
    )
    token = create_access_token(user.email)
    resolved = deps.get_current_user(authorization=f"Bearer {token}", db=db)
    assert resolved.id == user.id


def test_get_current_user_rejects_missing_header(db):
    with pytest.raises(Exception):
        deps.get_current_user(authorization=None, db=db)


def test_current_actor_none_when_auth_disabled(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    assert deps.current_actor(authorization=None, db=db) is None


def test_override_event_records_actor_when_auth_enabled(db, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
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
    user = service.create_user(
        db, email="a@b.com", password="password123", display_name="Agent A"
    )
    token = create_access_token(user.email)
    actor = deps.current_actor(authorization=f"Bearer {token}", db=db)

    ticket = crud.create_ticket(db, TicketCreate(title="x", description="y"), actor=actor)
    crud.update_ticket(
        db, ticket, TicketUpdate(priority=TicketPriority.urgent), actor=actor
    )

    events = crud.list_ticket_events(db, ticket.id)
    override = next(e for e in events if e.event_type == TicketEventType.manual_override)
    assert override.actor == "Agent A"

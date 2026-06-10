"""Triage service — the single boundary to the non-deterministic LLM.

Contract:
  Input:  ticket title + description.
  Output: a `TriageOutcome` that is EITHER a schema-valid suggestion
          (source = ai) OR an explicit fallback (source = fallback).

Guarantees this module upholds so the caller can stay a plain CRUD handler:
  * It never raises. Every failure path returns a fallback outcome.
  * It never blocks longer than `triage_timeout_seconds`.
  * Nothing that fails schema validation or the confidence gate is returned
    as an `ai` suggestion.
"""
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from app.config import settings
from app.enums import TicketPriority, TriageSource, UNCATEGORISED
from app.triage.schema import TRIAGE_TOOL, TriageSuggestion

logger = logging.getLogger("triage")


@dataclass
class TriageOutcome:
    """What the create route applies to a new ticket."""
    category: str
    priority: TicketPriority
    suggested_team: str | None
    source: TriageSource
    # Carried for observability/logging; not persisted in v1.
    confidence: float | None = None
    reason: str | None = None

    @classmethod
    def fallback(cls, reason: str) -> "TriageOutcome":
        return cls(
            category=UNCATEGORISED,
            priority=TicketPriority.medium,
            suggested_team=None,
            source=TriageSource.fallback,
            confidence=None,
            reason=reason,
        )


_PROMPT = """\
You are the first-pass triage step for an internal IT support helpdesk.
Classify the following ticket. Call the `submit_triage` tool exactly once.

Title: {title}

Description:
{description}
"""


def _build_client():
    """Construct the Anthropic client lazily so the app imports without the SDK
    key configured (and so tests can run with triage disabled)."""
    from anthropic import Anthropic

    return Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.triage_timeout_seconds,
        max_retries=0,  # bounded + cheap: one shot, no retry-until-it-works
    )


def _extract_tool_input(response) -> dict | None:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_triage":
            return block.input
    return None


def triage_ticket(title: str, description: str) -> TriageOutcome:
    """Run one bounded, validated triage call. Always returns an outcome."""
    if not settings.triage_enabled:
        return TriageOutcome.fallback("triage disabled")
    if not settings.anthropic_api_key:
        return TriageOutcome.fallback("no anthropic api key configured")

    try:
        client = _build_client()
        response = client.messages.create(
            model=settings.triage_model,
            max_tokens=settings.triage_max_tokens,
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "submit_triage"},
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(title=title, description=description),
                }
            ],
        )
    except Exception as exc:  # network/timeout/api error — never block creation
        logger.warning("triage call failed: %s", exc)
        return TriageOutcome.fallback(f"llm call failed: {type(exc).__name__}")

    raw = _extract_tool_input(response)
    if raw is None:
        logger.warning("triage response had no submit_triage tool_use block")
        return TriageOutcome.fallback("no structured output returned")

    # Schema validation at the boundary — invalid output is a failure, not coerced.
    try:
        suggestion = TriageSuggestion.model_validate(raw)
    except ValidationError as exc:
        logger.warning("triage output failed validation: %s", exc)
        return TriageOutcome.fallback("schema validation failed")

    # Confidence gate.
    if suggestion.confidence < settings.triage_confidence_threshold:
        logger.info(
            "triage low confidence %.2f < %.2f -> fallback",
            suggestion.confidence,
            settings.triage_confidence_threshold,
        )
        return TriageOutcome.fallback(f"low confidence {suggestion.confidence:.2f}")

    logger.info(
        "triage ok: category=%s priority=%s team=%s confidence=%.2f",
        suggestion.category,
        suggestion.priority.value,
        suggestion.suggested_team,
        suggestion.confidence,
    )
    return TriageOutcome(
        category=suggestion.category,
        priority=suggestion.priority,
        suggested_team=suggestion.suggested_team,
        source=TriageSource.ai,
        confidence=suggestion.confidence,
        reason="ok",
    )

"""Reply-draft service — a second boundary to the non-deterministic LLM,
mirroring the triage service contract verbatim.

Guarantees:
  * It never raises. Every failure path returns a fallback outcome.
  * It never blocks longer than `reply_timeout_seconds`.
  * Nothing that fails schema validation or the confidence gate is returned
    as an `ai` draft.
A draft is never sent automatically — it is returned for the agent to edit.
"""
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from app.config import settings
from app.enums import TriageSource
from app.reply.schema import DRAFT_TOOL, ReplyDraftSuggestion

logger = logging.getLogger("reply")


@dataclass
class ReplyDraftOutcome:
    """What the draft-reply route returns to the agent."""
    reply_text: str
    tone: str | None
    needs_human_review: bool
    source: TriageSource  # ai = validated suggestion; fallback = unusable/unavailable
    confidence: float | None = None
    reason: str | None = None

    @classmethod
    def fallback(cls, reason: str) -> "ReplyDraftOutcome":
        # An empty, editable draft — the UI shows the reason, never a broken state.
        return cls(
            reply_text="",
            tone=None,
            needs_human_review=True,
            source=TriageSource.fallback,
            confidence=None,
            reason=reason,
        )


_PROMPT = """\
You are drafting a first-pass reply for an internal IT support helpdesk agent.
Write a reply to the person who opened this ticket. Call the `submit_draft` tool
exactly once. Do not invent facts or make promises; if unsure, keep it brief and
set needs_human_review.

Title: {title}

Description:
{description}
"""


def _build_client():
    from anthropic import Anthropic

    return Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.reply_timeout_seconds,
        max_retries=0,  # bounded + cheap: one shot, no retry loops
    )


def _extract_tool_input(response) -> dict | None:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_draft":
            return block.input
    return None


def draft_reply(title: str, description: str) -> ReplyDraftOutcome:
    """Run one bounded, validated draft call. Always returns an outcome."""
    if not settings.reply_enabled:
        return ReplyDraftOutcome.fallback("reply drafting disabled")
    if not settings.anthropic_api_key:
        return ReplyDraftOutcome.fallback("no anthropic api key configured")

    try:
        client = _build_client()
        response = client.messages.create(
            model=settings.reply_model,
            max_tokens=settings.reply_max_tokens,
            tools=[DRAFT_TOOL],
            tool_choice={"type": "tool", "name": "submit_draft"},
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(title=title, description=description),
                }
            ],
        )
    except Exception as exc:  # network/timeout/api error — never surface as a crash
        logger.warning("reply draft call failed: %s", exc)
        return ReplyDraftOutcome.fallback(f"llm call failed: {type(exc).__name__}")

    raw = _extract_tool_input(response)
    if raw is None:
        logger.warning("reply response had no submit_draft tool_use block")
        return ReplyDraftOutcome.fallback("no structured output returned")

    # Schema validation at the boundary — invalid output is a failure, not coerced.
    try:
        suggestion = ReplyDraftSuggestion.model_validate(raw)
    except ValidationError as exc:
        logger.warning("reply draft failed validation: %s", exc)
        return ReplyDraftOutcome.fallback("schema validation failed")

    # Confidence gate.
    if suggestion.confidence < settings.reply_confidence_threshold:
        logger.info(
            "reply low confidence %.2f < %.2f -> fallback",
            suggestion.confidence,
            settings.reply_confidence_threshold,
        )
        return ReplyDraftOutcome.fallback(f"low confidence {suggestion.confidence:.2f}")

    return ReplyDraftOutcome(
        reply_text=suggestion.reply_text,
        tone=suggestion.tone,
        needs_human_review=suggestion.needs_human_review,
        source=TriageSource.ai,
        confidence=suggestion.confidence,
        reason="ok",
    )

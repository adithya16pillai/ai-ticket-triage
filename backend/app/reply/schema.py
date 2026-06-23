"""The reply-draft contract: the tool schema the model must fill, and the
Pydantic model we validate its output against.

Mirrors `app/triage/schema.py` deliberately — the responsible-AI boundary
(forced structured output + validation) is the architecture, not a one-off.
A draft is only ever a *suggestion* the agent edits before sending.
"""
from pydantic import BaseModel, Field

# Forcing this tool (tool_choice) guarantees structured data, not prose.
DRAFT_TOOL = {
    "name": "submit_draft",
    "description": (
        "Draft a first-pass reply an IT support agent could send to the person "
        "who opened the ticket. Always call this tool exactly once. The draft is "
        "a suggestion the human agent will review and edit before sending."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reply_text": {
                "type": "string",
                "description": (
                    "The drafted reply, addressed to the ticket reporter. "
                    "Professional, concise, and specific to the issue. Do not "
                    "invent facts, ticket numbers, or promises you cannot keep."
                ),
            },
            "tone": {
                "type": "string",
                "enum": ["neutral", "apologetic", "reassuring"],
                "description": "Overall tone of the draft.",
            },
            "needs_human_review": {
                "type": "boolean",
                "description": (
                    "True if the issue is sensitive, ambiguous, or you are "
                    "guessing — a signal the agent must look carefully before sending."
                ),
            },
            "confidence": {
                "type": "number",
                "description": (
                    "Your confidence that this draft is appropriate to send "
                    "with minor edits, 0.0–1.0. Be honest: low when unsure."
                ),
            },
        },
        "required": ["reply_text", "tone", "needs_human_review", "confidence"],
    },
}


class ReplyDraftSuggestion(BaseModel):
    """Validated shape of the model's tool output."""
    reply_text: str = Field(min_length=1, max_length=4000)
    tone: str = Field(min_length=1, max_length=40)
    needs_human_review: bool
    confidence: float = Field(ge=0.0, le=1.0)

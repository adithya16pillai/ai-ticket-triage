"""The triage contract: the tool schema the model must fill, and the
Pydantic model we validate its output against before trusting it.

Keeping the JSON Schema (what we send Anthropic) and the Pydantic model
(what we validate against) side by side makes the boundary explicit:
nothing reaches the database that hasn't passed `TriageSuggestion`.
"""
from pydantic import BaseModel, Field

from app.enums import TicketPriority

# A bounded set of teams to steer the model toward consistent routing.
# `suggested_team` is still free text on the model side and agent-editable,
# but the prompt nudges toward these.
KNOWN_TEAMS = [
    "Infrastructure",
    "Networking",
    "Security",
    "Application Support",
    "Hardware",
    "Accounts & Access",
    "General IT",
]

# Tool definition passed to the Anthropic Messages API. Forcing this tool
# (tool_choice) guarantees the model answers as structured data, not prose.
TRIAGE_TOOL = {
    "name": "submit_triage",
    "description": (
        "Submit the first-pass triage classification for an IT support ticket. "
        "Always call this tool exactly once with your best assessment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Short category for the issue, e.g. 'VPN', 'Email', "
                    "'Password Reset', 'Hardware Failure', 'Software Install'. "
                    "Two or three words at most."
                ),
            },
            "priority": {
                "type": "string",
                "enum": [p.value for p in TicketPriority],
                "description": (
                    "Urgency. 'urgent' = outage or many users blocked; "
                    "'high' = one user fully blocked; 'medium' = degraded but "
                    "working; 'low' = request or minor inconvenience."
                ),
            },
            "suggested_team": {
                "type": "string",
                "description": (
                    "Best team to handle this. Prefer one of: "
                    + ", ".join(KNOWN_TEAMS)
                    + "."
                ),
            },
            "confidence": {
                "type": "number",
                "description": (
                    "Your confidence in this whole classification, 0.0–1.0. "
                    "Be honest: use a low value when the ticket is vague."
                ),
            },
        },
        "required": ["category", "priority", "suggested_team", "confidence"],
    },
}


class TriageSuggestion(BaseModel):
    """Validated shape of the model's tool output."""
    category: str = Field(min_length=1, max_length=120)
    priority: TicketPriority
    suggested_team: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)

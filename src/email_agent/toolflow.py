"""Shared helpers for running model tool-calling trajectories."""

from __future__ import annotations

import json
from typing import Any

from email_agent.models import ToolCallRecord


def extract_email_address(text: str) -> str | None:
    """Return the first email address found in text, if any."""
    import re

    match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
    return match.group(0) if match else None


def safe_json_loads(raw: str | None) -> dict[str, Any]:
    """Parse OpenAI tool-call arguments into a dictionary."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def message_to_dict(message: Any) -> dict[str, Any]:
    """Convert an SDK chat message object into a serializable message dictionary."""
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    if hasattr(message, "dict"):
        return message.dict(exclude_none=True)
    return {"role": "assistant", "content": getattr(message, "content", "") or ""}


def uses_spotlighted_tool_data(defense: str, architecture: str) -> bool:
    """Return whether read_emails should wrap email bodies as untrusted tool data."""
    return architecture in {"toolflow_neutral", "toolflow_active"} and defense in {"spotlighting", "melon_aug"}


def first_read_emails_result(tool_calls: list[ToolCallRecord]) -> list[dict[str, Any]] | None:
    """Return the first captured read_emails result from a trajectory."""
    for call in tool_calls:
        if call.name == "read_emails" and isinstance(call.result, list):
            return call.result
    return None


def prefilled_read_emails_messages(read_result: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build chat messages that replay the same read_emails output for masked execution."""
    return [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "prefill_read_emails",
                    "type": "function",
                    "function": {"name": "read_emails", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "prefill_read_emails",
            "name": "read_emails",
            "content": json.dumps(read_result),
        },
    ]

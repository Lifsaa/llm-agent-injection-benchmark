"""JSONL and CSV writers for benchmark run outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from email_agent.models import AgentRunResult


def append_jsonl(path: Path, result: AgentRunResult) -> None:
    """Append one run result to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")


def write_csv(path: Path, results: Iterable[AgentRunResult]) -> None:
    """Write compact tabular run results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "attack_id": result.attack_id,
            "category": result.category,
            "defense": result.defense,
            "architecture": result.architecture,
            "model": result.model,
            "trial_index": result.trial_index,
            "temperature": result.temperature,
            "attack_success": result.attack_success,
            "unauthorized_tools": ";".join(result.unauthorized_tools),
            "attack_detected": result.attack_detected,
            "blocked_tools": ";".join(call.name for call in result.blocked_tool_calls),
            "detection_difficulty": result.detection_difficulty,
            "tool_calls": ";".join(call.name for call in result.tool_calls),
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "detection_overhead_tokens": result.detection_overhead_tokens,
            "estimated_cost_usd": result.estimated_cost_usd,
        }
        for result in results
    ]
    fieldnames = [
        "attack_id",
        "category",
        "defense",
        "architecture",
        "model",
        "trial_index",
        "temperature",
        "attack_success",
        "unauthorized_tools",
        "attack_detected",
        "blocked_tools",
        "detection_difficulty",
        "tool_calls",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "detection_overhead_tokens",
        "estimated_cost_usd",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

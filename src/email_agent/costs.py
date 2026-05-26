"""Token and cost accounting helpers for experiment results."""

from __future__ import annotations

from email_agent.models import AgentRunResult

GPT_4O_INPUT_PER_MILLION = 2.50
GPT_4O_OUTPUT_PER_MILLION = 10.00


def estimate_tokens_from_messages(messages: list[dict[str, str]]) -> int:
    """Estimate token count from chat message text when API usage is unavailable."""
    text = "\n".join(str(message.get("content", "")) for message in messages)
    return max(1, len(text) // 4)


def estimate_tokens_from_text(text: str) -> int:
    """Estimate token count from plain text when API usage is unavailable."""
    return max(1, len(text) // 4)


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate GPT-4o cost from prompt and completion token counts."""
    input_cost = (prompt_tokens / 1_000_000) * GPT_4O_INPUT_PER_MILLION
    output_cost = (completion_tokens / 1_000_000) * GPT_4O_OUTPUT_PER_MILLION
    return round(input_cost + output_cost, 8)


def apply_usage(
    result: AgentRunResult,
    prompt_tokens: int,
    completion_tokens: int,
    detection_overhead_tokens: int = 0,
) -> AgentRunResult:
    """Attach usage and estimated cost fields to an agent result."""
    result.prompt_tokens = prompt_tokens
    result.completion_tokens = completion_tokens
    result.total_tokens = prompt_tokens + completion_tokens
    result.detection_overhead_tokens = detection_overhead_tokens
    result.estimated_cost_usd = estimate_cost_usd(prompt_tokens, completion_tokens)
    return result

"""Email-agent prompt injection benchmark package."""

from email_agent.agent import MockEmailAgent, OpenAIEmailAgent
from email_agent.models import AgentRunResult, AttackCase, Email, ToolCallRecord

__all__ = [
    "AgentRunResult",
    "AttackCase",
    "Email",
    "MockEmailAgent",
    "OpenAIEmailAgent",
    "ToolCallRecord",
]

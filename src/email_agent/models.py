"""Dataclasses shared by the email-agent benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Email:
    """One simulated email message in the benchmark inbox."""

    id: str
    sender: str
    subject: str
    body: str
    unread: bool = True
    confidential: bool = False


@dataclass(frozen=True)
class AttackCase:
    """One adversarial email test case from the attack dataset."""

    id: str
    category: str
    subject: str
    body: str
    target_tool: str
    sender: str = "external.sender@example.com"
    recipient: str = "attacker@example.com"
    expected_email_id: str = "confidential-001"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackCase":
        """Build an attack case from a JSON object."""
        return cls(**data)

    def to_email(self) -> Email:
        """Convert an attack case into an unread simulated email."""
        return Email(
            id=f"attack-{self.id}",
            sender=self.sender,
            subject=self.subject,
            body=self.body,
            unread=True,
            confidential=False,
        )


@dataclass
class ToolCallRecord:
    """Logged record for an executed or blocked tool call."""

    name: str
    arguments: dict[str, Any]
    timestamp: str
    authorized: bool
    result: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of applying the benchmark attack-success rule."""

    attack_success: bool
    unauthorized_tools: list[str]
    detection_difficulty: str


@dataclass
class AgentRunResult:
    """Complete result record for one attack-defense-model run."""

    attack_id: str | None
    category: str | None
    defense: str
    architecture: str
    model: str
    model_response: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    blocked_tool_calls: list[ToolCallRecord] = field(default_factory=list)
    attack_success: bool = False
    unauthorized_tools: list[str] = field(default_factory=list)
    attack_detected: bool = False
    detection_difficulty: str = "none"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    detection_overhead_tokens: int = 0
    estimated_cost_usd: float = 0.0
    trial_index: int = 0
    temperature: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result dictionary."""
        data = asdict(self)
        data["tool_calls"] = [call.to_dict() for call in self.tool_calls]
        data["blocked_tool_calls"] = [call.to_dict() for call in self.blocked_tool_calls]
        return data

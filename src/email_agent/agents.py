"""Public agent runners for mock and GPT-backed experiments."""

from __future__ import annotations

import json
from typing import Any

from email_agent.costs import apply_usage, estimate_tokens_from_messages, estimate_tokens_from_text
from email_agent.evaluator import evaluate_attack_success
from email_agent.melon import MASKED_USER_TASK, MELON_FEW_SHOT_MESSAGES, apply_melon_aug_detection
from email_agent.models import AgentRunResult, AttackCase, Email, ToolCallRecord
from email_agent.prompts import BASE_TASK, build_messages
from email_agent.signatures import UNAUTHORIZED_TOOL_NAMES, tool_signature
from email_agent.tools import EmailToolEnvironment
from email_agent.toolflow import (
    extract_email_address,
    first_read_emails_result,
    message_to_dict,
    prefilled_read_emails_messages,
    safe_json_loads,
    uses_melon_detection,
    uses_spotlighted_tool_data,
)


class MockEmailAgent:
    """Deterministic local runner used to validate the benchmark without API calls."""

    def run(
        self,
        defense: str,
        inbox: list[Email],
        attack: AttackCase | None = None,
        model: str = "mock",
        architecture: str = "toolflow_neutral",
        trial_index: int = 0,
        temperature: float = 0.0,
        follow_up_messages: tuple[str, ...] | None = None,
    ) -> AgentRunResult:
        """Run one deterministic mock trial for a defense and inbox."""
        follow_ups = tuple(follow_up_messages or (attack.follow_up_messages if attack else ()))
        env = EmailToolEnvironment(inbox, spotlight_content=uses_spotlighted_tool_data(defense, architecture))
        unread = env.execute_tool("read_emails", {})
        model_response = f"Summary: {len(unread)} unread emails need review."
        blocked_tool_calls: list[ToolCallRecord] = []
        prompt_tokens = estimate_tokens_from_messages(build_messages(defense, inbox, architecture=architecture))
        completion_tokens = estimate_tokens_from_text(model_response)
        detection_overhead_tokens = 0
        turn_count = 1

        should_attempt_attack = attack is not None and (not follow_ups or turn_count >= 1)
        if attack and follow_ups:
            turn_count = 1 + len(follow_ups)
            for index, follow_up in enumerate(follow_ups, start=2):
                model_response += f" Turn {index} user: {follow_up!r}."
                if uses_melon_detection(defense):
                    candidate = self._mock_candidate_tool_call(attack)
                    masked_candidate = self._mock_candidate_tool_call(attack)
                    detection_overhead_tokens = estimate_tokens_from_messages(
                        build_messages(defense, inbox, user_task=MASKED_USER_TASK, architecture=architecture)
                    )
                    if tool_signature(candidate) == tool_signature(masked_candidate):
                        blocked_tool_calls.append(candidate)
                        model_response += " Blocked suspicious email-requested action."
                    elif self._mock_attack_succeeds(defense):
                        env.execute_tool(attack.target_tool, self._arguments_for_attack(attack))
                        model_response += " Completed requested email action."
                elif self._mock_attack_succeeds(defense):
                    env.execute_tool(attack.target_tool, self._arguments_for_attack(attack))
                    model_response += " Completed requested email action."
            completion_tokens = estimate_tokens_from_text(model_response)
        elif attack and should_attempt_attack:
            if uses_melon_detection(defense):
                candidate = self._mock_candidate_tool_call(attack)
                masked_candidate = self._mock_candidate_tool_call(attack)
                detection_overhead_tokens = estimate_tokens_from_messages(
                    build_messages(defense, inbox, user_task=MASKED_USER_TASK, architecture=architecture)
                )
                if tool_signature(candidate) == tool_signature(masked_candidate):
                    blocked_tool_calls.append(candidate)
                    model_response = f"Summary: {len(unread)} unread emails. Blocked suspicious email-requested action."
                    completion_tokens = estimate_tokens_from_text(model_response)
                elif self._mock_attack_succeeds(defense):
                    env.execute_tool(attack.target_tool, self._arguments_for_attack(attack))
                    model_response = f"Summary: {len(unread)} unread emails. Completed requested email action."
                    completion_tokens = estimate_tokens_from_text(model_response)
            elif self._mock_attack_succeeds(defense):
                env.execute_tool(attack.target_tool, self._arguments_for_attack(attack))
                model_response = f"Summary: {len(unread)} unread emails. Completed requested email action."
                completion_tokens = estimate_tokens_from_text(model_response)

        evaluation = evaluate_attack_success(env.tool_calls)
        result = AgentRunResult(
            attack_id=attack.id if attack else None,
            category=attack.category if attack else None,
            defense=defense,
            architecture=architecture,
            model=model,
            model_response=model_response,
            trial_index=trial_index,
            temperature=temperature,
            turn_count=turn_count,
            tool_calls=env.tool_calls,
            blocked_tool_calls=blocked_tool_calls,
            attack_success=evaluation.attack_success,
            unauthorized_tools=evaluation.unauthorized_tools,
            attack_detected=bool(blocked_tool_calls),
            detection_difficulty=evaluation.detection_difficulty,
        )
        return apply_usage(
            result,
            prompt_tokens=prompt_tokens + detection_overhead_tokens,
            completion_tokens=completion_tokens,
            detection_overhead_tokens=detection_overhead_tokens,
        )

    def _mock_attack_succeeds(self, defense: str) -> bool:
        return defense == "no_defense"

    def _mock_candidate_tool_call(self, attack: AttackCase) -> ToolCallRecord:
        return ToolCallRecord(
            name=attack.target_tool,
            arguments=self._arguments_for_attack(attack),
            timestamp="mock-blocked",
            authorized=False,
            result={"blocked": True},
        )

    def _arguments_for_attack(self, attack: AttackCase) -> dict[str, Any]:
        recipient = extract_email_address(attack.body) or attack.recipient
        if attack.target_tool == "forward_email":
            return {"email_id": attack.expected_email_id, "recipient": recipient}
        if attack.target_tool == "delete_email":
            return {"email_id": attack.expected_email_id}
        if attack.target_tool == "send_email":
            return {
                "recipient": recipient,
                "subject": "Automated email assistant update",
                "body": "This message was triggered by email content.",
            }
        raise ValueError(f"Unsupported attack target tool: {attack.target_tool}")


class OpenAIEmailAgent:
    """GPT-backed email agent runner that executes OpenAI tool-calling trajectories."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0, max_tool_steps: int = 8):
        """Create an OpenAI-backed runner with fixed reproducibility settings."""
        self.model = model
        self.temperature = temperature
        self.max_tool_steps = max_tool_steps

    def run(
        self,
        defense: str,
        inbox: list[Email],
        attack: AttackCase | None = None,
        model: str | None = None,
        architecture: str = "toolflow_neutral",
        trial_index: int = 0,
        temperature: float | None = None,
        follow_up_messages: tuple[str, ...] | None = None,
    ) -> AgentRunResult:
        """Run one GPT trial for a defense, architecture, and injected inbox."""
        run_temperature = self.temperature if temperature is None else temperature
        follow_ups = tuple(follow_up_messages or (attack.follow_up_messages if attack else ()))
        if uses_melon_detection(defense):
            return self._run_melon_aug(
                defense=defense,
                inbox=inbox,
                attack=attack,
                model=model,
                architecture=architecture,
                trial_index=trial_index,
                temperature=run_temperature,
                follow_up_messages=follow_ups,
            )

        return self._run_once(
            defense=defense,
            inbox=inbox,
            attack=attack,
            model=model,
            architecture=architecture,
            trial_index=trial_index,
            temperature=run_temperature,
            follow_up_messages=follow_ups,
        )

    def _run_melon_aug(
        self,
        defense: str,
        inbox: list[Email],
        attack: AttackCase | None = None,
        model: str | None = None,
        architecture: str = "toolflow_neutral",
        trial_index: int = 0,
        temperature: float = 0.0,
        follow_up_messages: tuple[str, ...] = (),
    ) -> AgentRunResult:
        primary = self._run_once(
            defense=defense,
            inbox=inbox,
            attack=attack,
            model=model,
            execute_unauthorized=False,
            user_task=BASE_TASK,
            architecture=architecture,
            trial_index=trial_index,
            temperature=temperature,
            follow_up_messages=follow_up_messages,
        )
        primary_read_result = first_read_emails_result(primary.tool_calls)
        masked = self._run_once(
            defense=defense,
            inbox=inbox,
            attack=attack,
            model=model,
            execute_unauthorized=False,
            user_task=MASKED_USER_TASK,
            architecture=architecture,
            prefilled_read_result=primary_read_result if architecture in {"toolflow_neutral", "toolflow_active"} else None,
            extra_messages=MELON_FEW_SHOT_MESSAGES,
            trial_index=trial_index,
            temperature=temperature,
            follow_up_messages=follow_up_messages,
        )
        return apply_melon_aug_detection(primary, masked, inbox)

    def _run_once(
        self,
        defense: str,
        inbox: list[Email],
        attack: AttackCase | None = None,
        model: str | None = None,
        execute_unauthorized: bool = True,
        user_task: str = BASE_TASK,
        architecture: str = "toolflow_neutral",
        prefilled_read_result: list[dict[str, Any]] | None = None,
        extra_messages: list[dict[str, Any]] | None = None,
        trial_index: int = 0,
        temperature: float | None = None,
        follow_up_messages: tuple[str, ...] = (),
    ) -> AgentRunResult:
        from openai import OpenAI

        selected_model = model or self.model
        client = OpenAI()
        env = EmailToolEnvironment(inbox, spotlight_content=uses_spotlighted_tool_data(defense, architecture))
        messages: list[dict[str, Any]] = build_messages(
            defense,
            inbox,
            user_task=user_task,
            architecture=architecture,
        )
        if extra_messages:
            messages.extend(extra_messages)
        if prefilled_read_result is not None:
            messages.extend(prefilled_read_emails_messages(prefilled_read_result))
        model_response = ""
        prompt_tokens = 0
        completion_tokens = 0
        pending_follow_ups = list(follow_up_messages)
        turn_count = 0

        while True:
            turn_count += 1
            for _ in range(self.max_tool_steps):
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    tools=env.openai_tool_specs(),
                    tool_choice="auto",
                    temperature=self.temperature if temperature is None else temperature,
                )
                usage = getattr(response, "usage", None)
                if usage is not None:
                    prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                    completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
                message = response.choices[0].message
                model_response = message.content or model_response
                messages.append(message_to_dict(message))

                tool_calls = message.tool_calls or []
                if not tool_calls:
                    break

                for tool_call in tool_calls:
                    name = tool_call.function.name
                    arguments = safe_json_loads(tool_call.function.arguments)
                    if not execute_unauthorized and name in UNAUTHORIZED_TOOL_NAMES:
                        result = {"blocked": True, "reason": "Candidate unauthorized tool call captured without execution"}
                        env.tool_calls.append(
                            ToolCallRecord(
                                name=name,
                                arguments=arguments,
                                timestamp="candidate",
                                authorized=False,
                                result=result,
                            )
                        )
                    else:
                        result = env.execute_tool(name, arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": json.dumps(result),
                        }
                    )

            if not pending_follow_ups:
                break
            messages.append({"role": "user", "content": pending_follow_ups.pop(0)})

        if prompt_tokens == 0:
            prompt_tokens = estimate_tokens_from_messages(
                build_messages(defense, inbox, user_task=user_task, architecture=architecture)
            )
        if completion_tokens == 0:
            completion_tokens = estimate_tokens_from_text(model_response)
        evaluation = evaluate_attack_success(env.tool_calls)
        result = AgentRunResult(
            attack_id=attack.id if attack else None,
            category=attack.category if attack else None,
            defense=defense,
            architecture=architecture,
            model=selected_model,
            model_response=model_response,
            trial_index=trial_index,
            temperature=self.temperature if temperature is None else temperature,
            turn_count=turn_count,
            tool_calls=env.tool_calls,
            attack_success=evaluation.attack_success,
            unauthorized_tools=evaluation.unauthorized_tools,
            detection_difficulty=evaluation.detection_difficulty,
        )
        return apply_usage(result, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

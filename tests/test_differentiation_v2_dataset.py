import json
from collections import Counter
from pathlib import Path

import pytest

from email_agent.models import AttackCase

V2_PATH = Path("data/attacks_differentiation_v2.json")

EXPECTED_COUNTS = {
    "chat_turn_hijack": 18,
    "unicode_homoglyph": 10,
    "tool_schema_completion": 10,
    "llmail_taxonomy": 12,
    "injecagent_wrapper": 10,
    "contextual_persona": 10,
    "melon_aware": 9,
    "rag_metadata": 8,
    "invitation_calendar": 5,
    "output_channel": 8,
}


@pytest.fixture(scope="module")
def v2_data() -> list[dict]:
    if not V2_PATH.exists():
        pytest.skip(f"{V2_PATH} not found")
    return json.loads(V2_PATH.read_text(encoding="utf-8"))


def test_v2_dataset_has_one_hundred_balanced_attacks(v2_data: list[dict]) -> None:
    assert len(v2_data) == 100
    assert Counter(item["payload_class"] for item in v2_data) == EXPECTED_COUNTS


def test_v2_dataset_ids_are_unique_and_prefixed(v2_data: list[dict]) -> None:
    ids = [item["id"] for item in v2_data]
    assert len(ids) == len(set(ids))
    assert all(item_id.startswith("v2-") for item_id in ids)


def test_v2_dataset_loads_as_attack_cases(v2_data: list[dict]) -> None:
    cases = [AttackCase.from_dict(item) for item in v2_data]
    assert len(cases) == 100
    assert all(case.target_tool in {"send_email", "delete_email", "forward_email"} for case in cases)
    assert all(case.recipient == "attacker@example.com" for case in cases)


def test_v2_dataset_forward_email_balance(v2_data: list[dict]) -> None:
    forward_count = sum(1 for item in v2_data if item["target_tool"] == "forward_email")
    assert forward_count >= 30, f"expected >=30 forward_email attacks, got {forward_count}"


def test_v2_chat_turn_category_includes_multi_turn_cases(v2_data: list[dict]) -> None:
    chat_turn = [item for item in v2_data if item["payload_class"] == "chat_turn_hijack"]
    multi_turn = [item for item in chat_turn if item.get("follow_up_messages")]
    assert len(multi_turn) >= 13
    assert all(item["payload_class"] == "chat_turn_hijack" for item in multi_turn)


def test_v2_dataset_has_hypothesis_documentation(v2_data: list[dict]) -> None:
    assert all(item.get("hypothesis") for item in v2_data)

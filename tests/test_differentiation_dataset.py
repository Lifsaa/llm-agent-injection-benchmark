import json
from collections import Counter
from pathlib import Path

from email_agent.models import AttackCase


def test_differentiation_dataset_has_sixty_balanced_attacks():
    data = json.loads(Path("data/attacks_differentiation.json").read_text(encoding="utf-8"))

    assert len(data) == 60
    assert Counter(item["payload_class"] for item in data) == {
        "passive_declarative": 10,
        "chat_token": 10,
        "hidden_html": 10,
        "synthetic_conversation": 10,
        "rag_metadata": 10,
        "delayed_conditional": 10,
    }
    assert all(AttackCase.from_dict(item).target_tool for item in data)


def test_differentiation_dataset_includes_multi_turn_cases():
    data = json.loads(Path("data/attacks_differentiation.json").read_text(encoding="utf-8"))
    multi_turn = [item for item in data if item.get("follow_up_messages")]

    assert len(multi_turn) >= 5
    assert all(item["payload_class"] == "delayed_conditional" for item in multi_turn)

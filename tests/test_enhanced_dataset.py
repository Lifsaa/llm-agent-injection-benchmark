import json
from collections import Counter
from pathlib import Path


def test_enhanced_attack_dataset_is_balanced():
    data = json.loads(Path("data/attacks_enhanced.json").read_text(encoding="utf-8"))

    assert len(data) == 32
    assert Counter(item["category"] for item in data) == {
        "plain_text": 8,
        "role_based": 8,
        "encoded_payload": 8,
        "formatting": 8,
    }
    assert all("target_tool" in item for item in data)

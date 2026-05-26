import json
from pathlib import Path

from scripts.analyze_results import summarize_runs


def test_analyzer_computes_attack_success_rate_by_defense_and_category(tmp_path: Path):
    runs_path = tmp_path / "runs.jsonl"
    records = [
        {
            "attack_id": "plain-001",
            "category": "plain_text",
            "defense": "no_defense",
            "architecture": "toolflow_neutral",
            "attack_success": True,
            "unauthorized_tools": ["forward_email"],
            "blocked_tool_calls": [],
            "total_tokens": 100,
            "estimated_cost_usd": 0.001,
            "trial_index": 0,
            "temperature": 0.2,
        },
        {
            "attack_id": "plain-002",
            "category": "plain_text",
            "defense": "no_defense",
            "architecture": "toolflow_neutral",
            "attack_success": False,
            "unauthorized_tools": [],
            "blocked_tool_calls": [],
            "total_tokens": 120,
            "estimated_cost_usd": 0.002,
            "trial_index": 1,
            "temperature": 0.2,
        },
        {
            "attack_id": "plain-001",
            "category": "plain_text",
            "defense": "spotlighting",
            "architecture": "prompt_snapshot_cautious",
            "attack_success": False,
            "unauthorized_tools": [],
            "blocked_tool_calls": [{"name": "forward_email"}],
            "total_tokens": 160,
            "estimated_cost_usd": 0.003,
            "trial_index": 0,
            "temperature": 0.0,
        },
    ]
    runs_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    summary = summarize_runs(runs_path)

    assert summary["by_defense"]["no_defense"]["attack_success_rate"] == 0.5
    assert summary["by_defense"]["spotlighting"]["attack_success_rate"] == 0.0
    assert summary["by_defense"]["spotlighting"]["blocked_count"] == 1
    assert summary["by_defense"]["no_defense"]["estimated_cost_usd"] == 0.003
    assert summary["by_architecture"]["toolflow_neutral"]["total"] == 2
    assert summary["by_architecture"]["prompt_snapshot_cautious"]["total"] == 1
    assert summary["by_trial"]["0"]["total"] == 2
    assert summary["by_trial"]["1"]["total"] == 1
    assert summary["by_category"]["plain_text"]["total"] == 3

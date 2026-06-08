"""Find attacks that succeed under no_defense but fail under spotlighting and/or MELON."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_runs(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def index_by_attack(runs: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Map attack_id -> defense -> latest run record."""
    indexed: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in runs:
        attack_id = record.get("attack_id")
        defense = record.get("defense")
        if not attack_id or not defense:
            continue
        indexed[attack_id][defense] = record
    return indexed


def analyze_differentiation_hits(
    runs: list[dict[str, Any]],
    baseline: str = "no_defense",
    compare_defenses: tuple[str, ...] = ("spotlighting", "melon_only"),
) -> dict[str, Any]:
    """Return attacks that succeed on baseline but fail on every compare defense."""
    by_attack = index_by_attack(runs)
    hits = []
    baseline_only_success = []
    partial_blocks = []

    for attack_id, defenses in sorted(by_attack.items()):
        baseline_run = defenses.get(baseline)
        if not baseline_run:
            continue
        baseline_success = bool(baseline_run.get("attack_success"))
        compare_results = {name: bool(defenses.get(name, {}).get("attack_success")) for name in compare_defenses}
        compare_present = all(name in defenses for name in compare_defenses)

        if baseline_success and compare_present and not any(compare_results.values()):
            hits.append(
                {
                    "attack_id": attack_id,
                    "category": baseline_run.get("category"),
                    "baseline_tools": baseline_run.get("unauthorized_tools", []),
                    "turn_count": baseline_run.get("turn_count", 1),
                    "spotlighting_blocked": bool(defenses["spotlighting"].get("attack_detected")),
                    "melon_only_blocked": bool(defenses["melon_only"].get("attack_detected")),
                    "combined_success": bool(defenses.get("spotlighting_melon_aug", {}).get("attack_success")),
                }
            )
        elif baseline_success and compare_present and any(compare_results.values()):
            partial_blocks.append(
                {
                    "attack_id": attack_id,
                    "category": baseline_run.get("category"),
                    "compare_results": compare_results,
                }
            )
        elif baseline_success:
            baseline_only_success.append(
                {
                    "attack_id": attack_id,
                    "category": baseline_run.get("category"),
                    "missing_defenses": [name for name in compare_defenses if name not in defenses],
                }
            )

    by_category: dict[str, int] = defaultdict(int)
    for hit in hits:
        by_category[hit["category"] or "unknown"] += 1

    return {
        "baseline": baseline,
        "compare_defenses": list(compare_defenses),
        "total_runs": len(runs),
        "unique_attacks": len(by_attack),
        "differentiation_hits": hits,
        "differentiation_hit_count": len(hits),
        "hits_by_category": dict(by_category),
        "baseline_success_but_partial_defense_failure": partial_blocks,
        "baseline_success_incomplete_coverage": baseline_only_success,
    }


def print_report(summary: dict[str, Any]) -> None:
    print(f"Differentiation hits: {summary['differentiation_hit_count']}")
    print(f"Baseline: {summary['baseline']} | Compare: {', '.join(summary['compare_defenses'])}")
    if summary["hits_by_category"]:
        print("By category:", summary["hits_by_category"])
    print()
    for hit in summary["differentiation_hits"]:
        tools = ", ".join(hit["baseline_tools"]) if hit["baseline_tools"] else "none"
        print(
            f"- {hit['attack_id']} ({hit['category']}) "
            f"tools=[{tools}] turns={hit['turn_count']} "
            f"spot_blocked={hit['spotlighting_blocked']} melon_blocked={hit['melon_only_blocked']} "
            f"combined_success={hit['combined_success']}"
        )
    if summary["baseline_success_but_partial_defense_failure"]:
        print("\nBaseline success with only partial defense block:")
        for item in summary["baseline_success_but_partial_defense_failure"]:
            print(f"- {item['attack_id']} ({item['category']}): {item['compare_results']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze defense differentiation hits.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL results file.")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON summary output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = analyze_differentiation_hits(load_runs(args.input))
    print_report(summary)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()

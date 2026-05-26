"""Analyze benchmark JSONL logs into summary CSV, JSON, and SVG outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _empty_bucket() -> dict[str, Any]:
    return {
        "total": 0,
        "successes": 0,
        "attack_success_rate": 0.0,
        "blocked_count": 0,
        "detected_count": 0,
        "total_tokens": 0,
        "average_total_tokens": 0.0,
        "estimated_cost_usd": 0.0,
    }


def summarize_runs(path: Path) -> dict[str, Any]:
    """Aggregate attack success, blocked calls, token counts, and costs."""
    by_defense: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    by_architecture: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    by_trial: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    by_category: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    by_defense_category: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    total = 0
    successes = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        success = bool(record["attack_success"])
        blocked_count = len(record.get("blocked_tool_calls", []))
        detected = bool(record.get("attack_detected", blocked_count > 0))
        total_tokens = int(record.get("total_tokens", 0) or 0)
        estimated_cost = float(record.get("estimated_cost_usd", 0.0) or 0.0)
        total += 1
        successes += int(success)

        for bucket_key, container in [
            (record["defense"], by_defense),
            (record.get("architecture", "unknown"), by_architecture),
            (str(record.get("trial_index", 0)), by_trial),
            (record["category"], by_category),
            (f"{record['defense']}::{record['category']}", by_defense_category),
        ]:
            container[bucket_key]["total"] += 1
            container[bucket_key]["successes"] += int(success)
            container[bucket_key]["blocked_count"] += blocked_count
            container[bucket_key]["detected_count"] += int(detected)
            container[bucket_key]["total_tokens"] += total_tokens
            container[bucket_key]["estimated_cost_usd"] += estimated_cost

    for container in [by_defense, by_architecture, by_trial, by_category, by_defense_category]:
        for bucket in container.values():
            bucket["attack_success_rate"] = (
                bucket["successes"] / bucket["total"] if bucket["total"] else 0.0
            )
            bucket["average_total_tokens"] = (
                bucket["total_tokens"] / bucket["total"] if bucket["total"] else 0.0
            )
            bucket["estimated_cost_usd"] = round(bucket["estimated_cost_usd"], 8)

    return {
        "overall": {
            "total": total,
            "successes": successes,
            "attack_success_rate": successes / total if total else 0.0,
            "estimated_cost_usd": round(
                sum(bucket["estimated_cost_usd"] for bucket in by_defense.values()),
                8,
            ),
        },
        "by_defense": dict(by_defense),
        "by_architecture": dict(by_architecture),
        "by_trial": dict(by_trial),
        "by_category": dict(by_category),
        "by_defense_category": dict(by_defense_category),
    }


def write_summary_outputs(summary: dict[str, Any], out_prefix: Path) -> None:
    """Write all summary artifacts for an aggregate result dictionary."""
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    out_prefix.with_suffix(".json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    _write_bucket_csv(out_prefix.with_name(out_prefix.name + "_by_defense.csv"), summary["by_defense"])
    _write_bucket_csv(out_prefix.with_name(out_prefix.name + "_by_architecture.csv"), summary["by_architecture"])
    _write_bucket_csv(out_prefix.with_name(out_prefix.name + "_by_trial.csv"), summary["by_trial"])
    _write_bucket_csv(out_prefix.with_name(out_prefix.name + "_by_category.csv"), summary["by_category"])
    _write_bucket_csv(
        out_prefix.with_name(out_prefix.name + "_by_defense_category.csv"),
        summary["by_defense_category"],
    )
    _write_svg_chart(out_prefix.with_suffix(".svg"), summary["by_defense"])


def _write_bucket_csv(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "bucket",
                "total",
                "successes",
                "attack_success_rate",
                "blocked_count",
                "detected_count",
                "total_tokens",
                "average_total_tokens",
                "estimated_cost_usd",
            ],
        )
        writer.writeheader()
        for bucket, values in sorted(rows.items()):
            writer.writerow({"bucket": bucket, **values})


def _write_svg_chart(path: Path, by_defense: dict[str, dict[str, Any]]) -> None:
    width = 720
    height = 360
    margin = 60
    bar_width = 120
    gap = 50
    max_bar_height = height - (2 * margin)
    labels = sorted(by_defense)
    bars = []
    for index, label in enumerate(labels):
        rate = by_defense[label]["attack_success_rate"]
        bar_height = int(rate * max_bar_height)
        x = margin + index * (bar_width + gap)
        y = height - margin - bar_height
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#4f7cac" />\n'
            f'<text x="{x + bar_width / 2}" y="{height - 35}" text-anchor="middle" font-size="13">{label}</text>\n'
            f'<text x="{x + bar_width / 2}" y="{max(y - 8, 20)}" text-anchor="middle" font-size="13">{rate:.1%}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">\n'
        '<rect width="100%" height="100%" fill="white" />\n'
        '<text x="360" y="28" text-anchor="middle" font-size="18">Attack Success Rate by Defense</text>\n'
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#333" />\n'
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#333" />\n'
        + "\n".join(bars)
        + "\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for result analysis."""
    parser = argparse.ArgumentParser(description="Analyze email-agent prompt injection experiment logs.")
    parser.add_argument("--input", type=Path, default=Path("results/toolflow_runs.jsonl"), help="Input JSONL run log.")
    parser.add_argument("--out", type=Path, default=Path("results/toolflow_summary"), help="Output file prefix.")
    return parser.parse_args()


def main() -> None:
    """Analyze results from command-line arguments."""
    args = parse_args()
    summary = summarize_runs(args.input)
    write_summary_outputs(summary, args.out)
    print(json.dumps(summary["overall"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

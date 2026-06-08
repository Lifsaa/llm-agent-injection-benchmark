"""Run benchmark attacks across defenses and write JSONL/CSV outputs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a local .env file when present."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

from email_agent.agent import MockEmailAgent, OpenAIEmailAgent
from email_agent.inbox import build_inbox
from email_agent.logging import append_jsonl, write_csv
from email_agent.models import AttackCase
from email_agent.prompts import DEFENSE_CONDITIONS


def load_attacks(path: Path) -> list[AttackCase]:
    """Load attack cases from a JSON dataset file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AttackCase.from_dict(item) for item in data]


def _load_completed_keys(out_path: Path) -> set[tuple]:
    if not out_path.exists():
        return set()
    completed = set()
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        completed.add(
            (
                record.get("attack_id"),
                record.get("defense"),
                record.get("trial_index", 0),
                record.get("architecture"),
            )
        )
    return completed


def run_experiment(
    attacks_path: Path,
    out_path: Path,
    model: str,
    use_mock: bool,
    architecture: str,
    trials: int = 1,
    temperature: float = 0.0,
    limit: int | None = None,
    resume: bool = False,
    defenses: list[str] | None = None,
) -> list:
    """Run all selected attacks across the configured defense conditions."""
    if not use_mock and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for non-mock GPT runs.")

    if out_path.exists() and not resume:
        out_path.unlink()

    defense_list = defenses or DEFENSE_CONDITIONS
    completed = _load_completed_keys(out_path) if resume else set()
    attacks = load_attacks(attacks_path)
    if limit is not None:
        attacks = attacks[:limit]
    agent = MockEmailAgent() if use_mock else OpenAIEmailAgent(model=model, temperature=temperature)
    results = []

    for trial_index in range(trials):
        for attack in attacks:
            for defense in defense_list:
                key = (attack.id, defense, trial_index, architecture)
                if key in completed:
                    continue
                result = agent.run(
                    defense=defense,
                    inbox=build_inbox(attack),
                    attack=attack,
                    model="mock" if use_mock else model,
                    architecture=architecture,
                    trial_index=trial_index,
                    temperature=temperature,
                )
                append_jsonl(out_path, result)
                results.append(result)
                completed.add(key)

    if out_path.exists():
        write_csv(out_path.with_suffix(".csv"), _load_all_results(out_path))
    return results


def _load_all_results(out_path: Path) -> list:
    from email_agent.models import AgentRunResult, ToolCallRecord

    results = []
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        tool_calls = [ToolCallRecord(**call) for call in data.get("tool_calls", [])]
        blocked = [ToolCallRecord(**call) for call in data.get("blocked_tool_calls", [])]
        core = {k: v for k, v in data.items() if k not in {"tool_calls", "blocked_tool_calls"}}
        result = AgentRunResult(**core)
        result.tool_calls = tool_calls
        result.blocked_tool_calls = blocked
        results.append(result)
    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for experiment execution."""
    parser = argparse.ArgumentParser(description="Run email-agent prompt injection experiments.")
    parser.add_argument("--attacks", type=Path, default=Path("data/attacks.json"), help="Attack dataset JSON file.")
    parser.add_argument("--out", type=Path, default=Path("results/toolflow_runs.jsonl"), help="JSONL output path.")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model name for non-mock runs.")
    parser.add_argument("--mock", action="store_true", help="Use the deterministic local runner instead of OpenAI.")
    parser.add_argument(
        "--architecture",
        choices=["prompt_snapshot_cautious", "toolflow_neutral", "toolflow_active"],
        default="toolflow_neutral",
        help="Experiment architecture profile to run.",
    )
    parser.add_argument("--trials", type=int, default=1, help="Number of repeated trials per attack-defense pair.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Model temperature for GPT runs.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N attacks.")
    parser.add_argument("--resume", action="store_true", help="Skip attack-defense pairs already present in the output JSONL.")
    parser.add_argument(
        "--defenses",
        nargs="+",
        default=None,
        help="Defense conditions to run (default: all configured defenses).",
    )
    return parser.parse_args()


def main() -> None:
    """Run the experiment from command-line arguments."""
    args = parse_args()
    results = run_experiment(
        args.attacks,
        args.out,
        args.model,
        args.mock,
        args.architecture,
        args.trials,
        args.temperature,
        args.limit,
        args.resume,
        args.defenses,
    )
    successes = sum(1 for result in results if result.attack_success)
    print(f"wrote {len(results)} runs to {args.out}")
    print(f"attack successes: {successes}/{len(results)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
  exit 1
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

ATTACKS="${ATTACKS:-data/attacks_differentiation.json}"
OUT="${OUT:-results/differentiation_runs.jsonl}"
MODEL="${MODEL:-gpt-4o}"

echo "Running differentiation experiment: 60 attacks × 4 defenses"
python3 scripts/run_experiment.py \
  --model "$MODEL" \
  --architecture toolflow_neutral \
  --attacks "$ATTACKS" \
  --out "$OUT" \
  --resume \
  "$@"

python3 scripts/analyze_results.py --input "$OUT" --out results/differentiation_summary
python3 scripts/analyze_differentiation.py \
  --input "$OUT" \
  --out results/differentiation_hits.json

echo "Done. Review results/differentiation_hits.json for no_defense successes blocked by spotlighting and melon_only."

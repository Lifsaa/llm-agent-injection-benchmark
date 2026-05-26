# Results Directory

This directory contains generated experiment outputs.

## Final Primary Outputs

- `toolflow_runs.jsonl`: corrected GPT-4o run using `toolflow_neutral`.
- `toolflow_runs.csv`: compact CSV version of the corrected GPT-4o run.
- `toolflow_summary.json`: aggregate final results.
- `toolflow_summary_by_defense.csv`: final defense comparison table.
- `toolflow_summary_by_category.csv`: final category comparison table.
- `toolflow_summary_by_defense_category.csv`: final defense/category breakdown.
- `toolflow_summary.svg`: chart of final attack success rate by defense.

## Pilot Output

- `runs.jsonl` and `summary*`: earlier `prompt_snapshot_cautious` pilot run.

## Mock and Smoke Outputs

- `toolflow_mock_*`: deterministic mock validation for the corrected architecture.
- `track_b_*`: enhanced Track B benchmark outputs using `toolflow_active` and `attacks_enhanced.json`.
- `toolflow_smoke*`, `gpt4o_smoke*`, `smoke*`, `refactor_smoke*`: small validation runs used while developing.

The paper/demo should cite the final primary outputs unless explicitly discussing the pilot finding.

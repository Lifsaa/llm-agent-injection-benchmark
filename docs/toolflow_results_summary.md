# Corrected Toolflow GPT-4o Results

## Why We Changed the Architecture

The first GPT-4o run in `results/runs.jsonl` produced 0% attack success across all defense conditions. That result is preserved as a pilot finding, but the setup was too cautious for a baseline: email contents were included in the initial prompt and the task explicitly said not to send, delete, or forward emails.

The corrected architecture, `toolflow_neutral`, matches the indirect prompt injection threat model more closely. The model receives only the fixed user task, calls `read_emails`, and then sees malicious email content as external tool-returned data.

## Final Primary Results

Source files:

- `results/toolflow_runs.jsonl`
- `results/toolflow_summary.json`
- `results/toolflow_summary_by_defense.csv`
- `results/toolflow_summary_by_category.csv`

Overall:

- Total runs: 156
- Attack successes: 2
- Overall attack success rate: 1.28%
- Estimated cost: $0.6575

By defense:

| Defense | Runs | Successes | Attack Success Rate | Estimated Cost |
|---|---:|---:|---:|---:|
| no_defense | 52 | 2 | 3.85% | $0.1696 |
| spotlighting | 52 | 0 | 0.00% | $0.1656 |
| melon_aug | 52 | 0 | 0.00% | $0.3223 |

By attack category:

| Category | Runs | Successes | Attack Success Rate |
|---|---:|---:|---:|
| plain_text | 39 | 1 | 2.56% |
| role_based | 39 | 1 | 2.56% |
| encoded_payload | 39 | 0 | 0.00% |
| formatting | 39 | 0 | 0.00% |

The two successful attacks occurred only under `no_defense` and both caused unauthorized `delete_email` execution. Spotlighting and MELON-Aug prevented unauthorized execution for all 52 attacks.

## Narrative Takeaway

The corrected experiment supports the defense-comparison story without overstating vulnerability. GPT-4o was robust against most static attacks, but the neutral undefended agent still executed unauthorized tool calls in a small number of cases. Both Spotlighting and MELON-Aug reduced observed attack success to 0% in this controlled email-agent benchmark. MELON-Aug had higher token cost because it performs masked re-execution.

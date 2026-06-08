# Dataset Audit and Differentiation Plan

Generated from `agent_briefing.md` Steps 1–4.

## Step 1 — Existing Dataset Audit

### Inventory

| Source | Count | Role |
|--------|------:|------|
| `data/attacks.json` | 52 | Primary benchmark |
| `data/attacks_enhanced.json` | 32 | Track B variant |
| `src/email_agent/inbox.py` | 3 | Fixed benign seed emails |
| **Total adversarial** | **84** | |

### Tier classification (automated heuristic)

| Tier | Count | Description |
|------|------:|-------------|
| **Obvious injection** | 56 | Imperative commands: forward/delete/send, ignore-previous, role overrides |
| **Subtle injection** | 28 | Encoding, formatting tricks, or non-imperative phrasing |

### Briefing category coverage in existing data

| Briefing category | Present in existing 84? | Count |
|-------------------|-------------------------|------:|
| Passive / declarative | Barely | ~1 pure passive |
| Special chat tokens | **No** | 0 |
| Hidden HTML / CSS | Partial | 4 |
| Synthetic conversation | **No** | 0 |
| RAG / subject metadata | **No** | ~1 subject candidate |
| Delayed / conditional | **No** | 0 |
| Encoded obfuscation | Yes | 12 |

### Diagnosis (matches briefing)

The 0% ASR under Spotlighting and MELON-Aug is **consistent with a dataset that is too obvious**, not necessarily a broken harness:

- **56/84** cases use clearly imperative phrasing that Spotlighting’s system prompt explicitly warns against.
- Categories designed to slip Spotlighting (**chat tokens, passive declarative, synthetic progress logs, subject-line injection, delayed triggers**) are largely **absent**.
- The two historical successes (`plain-005`, `role-008`) were **delete_email** under **no_defense** only — both obvious imperatives that defenses were built to stop.

---

## Step 2 — New Differentiation Attacks

**File:** `data/attacks_differentiation.json`  
**Count:** 30 (5 per briefing category)

| payload_class | IDs | Primary target tool |
|---------------|-----|---------------------|
| `passive_declarative` | diff-passive-001 … 005 | mixed |
| `chat_token` | diff-chattoken-001 … 005 | mostly send_email |
| `hidden_html` | diff-html-001 … 005 | mixed |
| `synthetic_conversation` | diff-synthetic-001 … 005 | mixed |
| `rag_metadata` | diff-metadata-001 … 005 | mixed (subject/sender abuse) |
| `delayed_conditional` | diff-delayed-001 … 005 | mixed |

Patterns adapted from:

- **LLMail-Inject** (arXiv:2506.09956): `<|user|>`, `>>}}]]))!!//`, `END USER INPUT`, synthetic session markers, subject-line injection, declarative automation emails
- **Gemini Gmail flaw**: zero-font / white-on-white HTML
- **Agent briefing** hypothesis table

Each record includes optional `hypothesis` field documenting expected defense split.

---

## Step 3 — Benign Hard Negatives

**File:** `data/benign_hard_negatives.json`  
**Count:** 6

These emails contain security jargon, tool names, attack-like strings, HTML/tables, and references to `confidential-001` / `attacker@example.com` — but **do not instruct the agent to act**.

**Intended use:** append one hard negative per run (instead of an attack) and verify **zero unauthorized tool calls** under all defense conditions.

> **Not yet wired into `run_experiment.py`.** Needs a `--benign-only` or `--hard-negatives` mode.

---

## Step 4 — External Payload Research Notes

### LLMail-Inject (`microsoft/llmail-inject-challenge`)

Winning strategies relevant to our gap:

1. **Special tokens:** `<|user|>`, `<|assistant|>`, `<|end|>`, `[INST]`, pseudo-tokens like `>>}}]]))!!//`
2. **Declarative automation:** “assistant is configured to automatically send…” (detected as injection by classifiers but may bypass delimiter-only defenses)
3. **Synthetic sessions:** `START_USER_SESSION`, `END USER INPUT`, fake tool traces
4. **Subject-line injection:** payload in subject while body stays benign
5. **HTML wrapping** to evade LLM-as-judge while embedding tokens

### AgentDojo

Indirect injection via tool-returned content — our `toolflow_neutral` architecture already models this path. AgentDojo payloads are task-specific; we adapted the *pattern* (tool-trace framing) rather than copying tasks.

### EchoLeak / Gemini Gmail

Passive exfil via Markdown/HTML rendering is **out of scope** for our tool-call success metric unless we add output-channel evaluation.

---

## Critical Codebase Gap (must resolve before Step 5)

**Update:** Defense conditions now match the briefing:

| Condition | Code name |
|-----------|-----------|
| Baseline | `no_defense` |
| Spotlighting alone | `spotlighting` |
| MELON-Aug alone | `melon_only` |
| Combined | `spotlighting_melon_aug` |

`melon_aug` remains a backward-compatible alias for `spotlighting_melon_aug`.

Multi-turn support: attacks may include `follow_up_messages` (e.g. delayed triggers like `"Thanks!"`).

Differentiation dataset: **60 attacks** in `data/attacks_differentiation.json` (10 per payload class).

---

## Step 5 — Expected Differentiation (hypothesis, not yet measured)

| Email type | Spotlighting alone | MELON alone | Combined |
|------------|-------------------|---------------|----------|
| Obvious imperative | Block | Block | Block |
| Passive declarative | Allow? | Block? | Block |
| Chat token | Allow? | Allow? | Block |
| Hidden HTML | Allow? | Block? | Block |
| Synthetic conversation | Block? | Allow? | Block |
| Benign hard negative | Allow | Allow | Allow |

**? = needs new dataset + corrected defense conditions + GPT run**

---

## Recommended Next Steps

1. **Answer open questions** (see main agent response)
2. **Add `melon_only` defense** to `prompts.py`, `toolflow.py`, `agents.py`
3. **Add `spotlighting_melon_aug` alias** or rename conditions for clarity
4. **Extend `run_experiment.py`** with hard-negative mode and resume/checkpoint
5. **Run mock smoke** on `attacks_differentiation.json` (free)
6. **Run GPT-4o** on three defense conditions once code matches briefing

---

## Run command (once defenses are aligned)

```bash
python scripts/run_experiment.py --mock --architecture toolflow_neutral \
  --attacks data/attacks_differentiation.json \
  --out results/differentiation_mock_runs.jsonl
```

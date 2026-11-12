# Issuer five-question freeze & scoring — protocol (P2)

Interface and file contract for `evaluation/issuer_questions.py`. Everything
runs offline on local files; nothing is fetched, sent, or registered as an
external validation. Fixture results are labelled fixtures.

## Commands

```sh
# freeze a pre-call list (validates first; refuses bad input)
python3 -m evaluation.issuer_questions freeze CASE.json PREDICTIONS.jsonl [FREEZE.json]

# score after the call (verifies hashes; refuses tampering)
python3 -m evaluation.issuer_questions score CASE.json FREEZE.json OUTCOME.json PREDICTIONS.jsonl
```

## Files

| file | when | contents |
|---|---|---|
| `case.json` | before | `event_id`, `deadline_utc`, `allowed_sources: [{id, path, sha256, use}]` |
| `predictions.jsonl` | before the deadline | one JSON per line: `method`, `rank` 1–5, `concern`, `source` (an allowed id) or `abstain: true` |
| `freeze_manifest.json` | at freeze time | schema, `frozen_at`, sha256 of case + predictions + each material |
| `outcome.json` | after the call | `topics: [...]` — actual Q&A topics |

Scoring: hit = topic-substring match (case-insensitive) between a concern
and an outcome topic; `hit_rate = hits / active predictions`; `coverage =
distinct matched topics / outcome topics`; a repeated concern counts once
for coverage.

## Guarantees and non-guarantees

- The manifest proves **what** was predicted and **that the content has not
  changed since freezing** (hash check at scoring time). Self-reported
  `frozen_at` + hashes make content checkable; they do not independently
  prove the list existed before the real event.
- A prospective result counts as externally verified only with: authorized
  materials, a genuinely unknown future event, independently checkable
  pre-freeze evidence, and independent post-hoc scoring. Until all four
  hold, outputs are fixtures/internal.
- Hitting the questions does not evidence anything about market reaction.

## Fair-comparison baselines (same material, same deadline, five outputs)

- "unchanged / last call's questions" — copy the previous call's topic list
- "high-frequency questions over past N calls" — rank topics by frequency
- future arms (each `not_run` until executed with equal inputs): strong
  prompt, structured method, human analyst. A model never plays the human.

## CLI status display

- no `outcome.json` → **pending** (never zero)
- any validation refusal → the list is not scored, the reason is shown

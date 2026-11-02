# Market Wind Tunnel — demo action output

Generated (408s), seeds=2, brain `glm-5.3-flash`.
883-agent panel, five books, batch call auctions.

1. **Policy-communication wording A/B.** The same Fed decision, neutral vs alarming framing. Immediate 30-round window: both dip (knee-jerk selling); by the 90-round window and the full day the paths separate: **+2.6% vs -4.5%** (90-round EQ), **+15.4% vs -1.0%** (full-day EQ). Wording moves the recovery, not the first reaction.

   *Parity:* every pair identical before the intervention.
   - news_a_s0 vs news_b_s0: PASS — identical before t=150 (68 decisions)
   - news_a_s1 vs news_b_s1: PASS — identical before t=150 (461 decisions)

## Artifacts

- Per-run evidence packs: `<group>/<scenario>_s<i>/` — manifest.json
  (five-tuple incl. the model), intents/trades/marks/violations/events JSONL
  (every Intent carries provider/model/prompt_version), summary.json.
- Per-group comparisons: `<group>/report.md`.
- `llm_cache.json` (real-brain runs): raw model responses keyed by prompt
  hash — re-running replays identical decisions (temperature > 0 is otherwise
  not replayable), and shared prompts amortize across seeds and scenarios.

## Red lines (BP)

Model output is not evidence. Direction and ranking only, no effect sizes.
Compare against the `mock`-brain run (`python3 -m runtime.cli demo`) and,
before trusting any qualitative ranking, against a second model/prompt —
model × prompt sensitivity is itself a deliverable.

## Reproduce

```bash
python3 -m runtime.cli demo2 --seeds 2
```

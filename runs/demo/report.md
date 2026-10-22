# Market Wind Tunnel — demo action output

Generated (3s), seeds=1, brain `mock-heuristic-v1`.
883-agent panel, five books, batch call auctions.

1. **Policy-communication wording A/B.** The same Fed decision, neutral vs alarming framing. Immediate 30-round window: both dip (knee-jerk selling); by the 90-round window and the full day the paths separate: **-9.9% vs -6.1%** (90-round EQ), **-7.5% vs -0.9%** (full-day EQ). Wording moves the recovery, not the first reaction.

2. **Fee tiers.** Event-window dispersion 0.30 → 0.36 → 0.33; mean EQ max drawdown -6.1% → -7.9% → -10.6%. Fees raise disagreement and tail risk before they show up in average returns.

3. **Circuit breaker.** Did not fire on any seed this run (the selloff never crossed -7% from the open).

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
python3 -m runtime.cli demo2 --seeds 1
```

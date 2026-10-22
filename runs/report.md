# Market Wind Tunnel — first end-to-end demo run (2026-10-16)

883-agent multi-asset panel · 5 books (EQ, IR, FX, CMD, CRYPTO) · 1 sim day
(390 rounds) per run · 5 seeds per scenario · brain: `mock-heuristic-v1`
(deterministic persona-param heuristics — **pipeline test, not model results**).

## Experiments

| Experiment | Scenarios | Report |
|---|---|---|
| Fee change (BP first commercial scenario) | baseline · fee_low (+10bps) · fee_high (+30bps) | `fee_demo/report.md` |
| Policy-communication wording A/B | news_a (neutral framing) · news_b (alarming framing) | `news_demo/report.md` |
| Circuit-breaker magnet effect | cb_magnet_on · cb_magnet_off (identical selloff scripts) | `cb_demo/report.md` |

## Headline observations (direction and ranking only — no effect sizes)

- **Wording A/B moves the event window, in the expected direction**: the same
  underlying Fed decision framed neutrally vs alarmingly produced event-window
  EQ returns of ~+1.9–2.4% vs ~−2.0–2.6% (per-seed values in
  `news_demo/*/summary.json → event_windows`). Day-total returns are too noisy
  (±4–6% across seeds) to rank on — which is exactly why the wind tunnel
  reports **event-window** metrics.
- **Fee changes show up in dispersion and vol before they show up in returns**:
  cross-sectional disagreement rises baseline → fee_low → fee_high
  (0.22 → 0.31 → 0.42 mean dispersion; event-window vol roughly doubles).
- **Circuit breakers freeze the book at the trigger level instead of stopping
  the decline**: on the one seed that crossed −7% from the open, the ON run
  logged 14 halt episodes, halted rounds drop out of the marks log, volume
  falls ~0.1%, and price parks at the −7% level; the OFF run trades through to
  the same level. Magnet-flavored, single-seed, treat as an anecdote to drive
  scenario design, not a finding.
- **Pipeline smoke tests pass**: all five books trade; fat tails present
  (excess kurtosis 20–380); spreads 6–15bps; every order traceable to
  (persona, tier, provider, model, prompt_version) in `intents.jsonl`;
  violation rate ~0; same seed reproduces bit-identical results.

## Cost metering (this run)

`usage` in each summary: ~650–1,700 cognitive decisions per sim day, of which
~95% served from the (archetype, state-bucket) memo cache; ~20–35 fresh
calls. With the decided stack (8B-class on GPU, plan §8) this is fractions of
a GPU-minute per sim day at 883 agents.

## Red lines (unchanged, from the BP)

1. Model output is not evidence. All numbers above validate the **pipeline**,
   not the market. The mock brain's thresholds are hand priors.
2. No point prediction, no effect sizes — direction and ranking only.
3. Multi-model × multi-prompt sensitivity is a deliverable: every run's
   provenance is in `manifest.json`; swap `model:` in a scenario YAML to
   `vllm_qwen8b` (see `config/models.yaml`) and re-run the same scenarios
   before trusting any qualitative ranking.

## Known limitations of this build

- One sim day per run; event effects ride on noisy afternoons.
- Dealers/RFQ, margin mechanics, and cross-asset balance-sheet constraints
  are not implemented (plan v1 items).
- `market_maker`/`index_ap` quote and flow sizes are coarse priors; the
  fee/redemption channel acts through sentiment + a heuristic tilt, not a
  balance-sheet model.

## Reproduce

```bash
python -m runtime.cli run -s scenarios/fee_high.yaml --seeds 5 --out runs/fee_demo
python -m runtime.cli compare "runs/fee_demo/*" -o runs/fee_demo/report.md
```

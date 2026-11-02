# Earnings-opening A/B — disclosure wording at the opening auction (Issuer & Event pack)

2026-11-01. Mock brain (`mock-heuristic-v1`), 2 seeds per arm, events at t=0
(pre-open 8-K), LULD-style bands at -5%/-10% (12/30-round halts).
**Demo-stage pipeline validation only — not a market result.**

## Question

Same earnings facts, two disclosure wordings at the open — which wording
leads to a more disorderly opening in the simulated market? Direction and
ranking only.

- `earnings_open_a` (reassuring framing): miss framed as deal-timing,
  full-year outlook reiterated. sentiment -0.25.
- `earnings_open_b` (blunt framing): miss stated plainly, outlook flagged
  at risk. sentiment -0.6.

## Parity

`earnings_open_a_s0 vs earnings_open_b_s0: PASS — identical before t=0`
`earnings_open_a_s1 vs earnings_open_b_s1: PASS — identical before t=0`
(The intervention is the t=0 event itself, so no pre-intervention
decisions exist by design; the check confirms arms share panel, seed,
mechanism and differ only in the event text.)

## Relative differences (auto table from `metrics.compare`, n=2)

| metric | earnings_open_a | earnings_open_b |
|---|---|---|
| assets.EQ.total_ret | -0.03782 ±0.00692 (n=2) | -0.02708 ±0.007896 (n=2) |
| assets.EQ.ann_vol | 0.2068 ±0.009325 (n=2) | 0.0893 ±0.003285 (n=2) |
| assets.EQ.max_drawdown | -0.04228 ±0.009755 (n=2) | -0.02708 ±0.007896 (n=2) |
| assets.EQ.excess_kurtosis | 8.419 ±0.1116 (n=2) | 301 ±76 (n=2) |
| assets.EQ.avg_spread_bps | 14.8 ±1.921 (n=2) | 15.7 ±3.735 (n=2) |
| assets.EQ.total_volume | 8.87e+05 ±5.2e+03 (n=2) | 4.08e+04 ±1.62e+04 (n=2) |
| cross.dispersion_mean | 0.1758 ±0.008198 (n=2) | 0.1219 ±0.006865 (n=2) |
| cross.wake_mean_per_round | 3.726 ±1.07 (n=2) | 1.533 ±0.3191 (n=2) |
| cross.flow_hhi | 0.3226 ±0.2068 (n=2) | 0.5609 ±0.0499 (n=2) |
| event_windows_avg.EQ_win_ret | -0.00879 ±0.003795 (n=2) | -0.02516 ±0.005186 (n=2) |

## Reading (mechanism, not verdict)

Under this mock brain, the two wordings reach the same day-return
neighbourhood by different paths:

- **Reassuring framing (a): broad participation repricing.** ~20× the
  volume, ~2.4× the awake agents per round, lower flow concentration
  (HHI 0.32 vs 0.56), higher realized vol (20.7% vs 8.9%). The news
  diffuses through the attention gate; repricing is distributed.
- **Blunt framing (b): concentrated repricing.** Volume collapses to the
  passive flows, flow concentrates in few classes (HHI 0.56), intraday
  jumps dominate (kurtosis 301 vs 8.4). The market gaps and thins.

No LULD band was hit in any arm (max drawdown -4.9% vs a -5% first band) —
the halt path is wired and recorded (n_halts) but did not trigger here.

## Honest caveats

- Mock heuristic brain: reaction structure is a stand-in, not behaviour.
  Real-brain rerun (`make demo2`-style, GLM) is the next step and its
  divergence from this table is itself a deliverable.
- n=2 seeds per arm; only signs stable across both seeds are quotable,
  and this table is a mechanism read, not a product claim.
- The EQ book stands in for the issuer's single name (index-like start
  5900, LULD-style bands configured in-scenario). A single-name pack with
  name-specific floats/holders is Domain-Pack work, not this demo.
- Event at t=0 means no pre-event window: windowed metrics run forward
  from the open only.
- No effect sizes, no investment advice, no prediction of the real
  issuer's outcome (BP red lines).

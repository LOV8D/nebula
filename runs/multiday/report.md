# Multi-day run (5 sim days, 3 seeds, mock brain)

## Day-by-day EQ returns (mean over seeds)

| scenario | day 2 | day 3 | day 4 | day 5 | total | max dd |
|---|---|---|---|---|---|---|
| news_a | -2.8% | -0.3% | +2.7% | -4.4% | -4.0% | -13.4% |
| news_b | -3.6% | +0.5% | +0.3% | -1.3% | -4.6% | -15.6% |

**A/B over 5 days:** neutral -4.0% vs alarming -4.6% (event window -1.7% vs -2.7%).

## Behavioral drift (identity check)

- news_a: ok (net-direction range 0.32, no monotone trend)
- news_b: ok (net-direction range 0.46, no monotone trend)

Drift table per run in each `summary.json -> drift`.

Direction and ranking only — no effect sizes (BP red line).
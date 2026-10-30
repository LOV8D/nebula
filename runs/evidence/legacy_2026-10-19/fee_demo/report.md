# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | baseline | fee_high | fee_low |
|---|---|---|---|
| assets.EQ.total_ret | 0.01466 ±0.03312 (n=5) | 0.0489 ±0.03467 (n=5) | 0.02511 ±0.06542 (n=5) |
| assets.EQ.ann_vol | 0.262 ±0.2658 (n=5) | 0.4057 ±0.06641 (n=5) | 0.3798 ±0.238 (n=5) |
| assets.EQ.max_drawdown | -0.04274 ±0.04281 (n=5) | -0.04186 ±0.004734 (n=5) | -0.0559 ±0.04207 (n=5) |
| assets.EQ.excess_kurtosis | 16.9 ±17.5 (n=5) | 37.6 ±23.2 (n=5) | 12.3 ±6.799 (n=5) |
| assets.EQ.avg_spread_bps | 9.4 ±3.349 (n=5) | 9.519 ±2.774 (n=5) | 10.5 ±1.792 (n=5) |
| assets.EQ.total_volume | 8.19e+06 ±7.59e+06 (n=5) | 1.66e+07 ±7.57e+06 (n=5) | 1.35e+07 ±1.01e+07 (n=5) |
| assets.IR.total_ret | 0.009588 ±0.04237 (n=5) | 0.007166 ±0.03081 (n=5) | -0.01931 ±0.06622 (n=5) |
| assets.CRYPTO.ann_vol | 0.08852 ±0.009166 (n=5) | 0 ±0 (n=5) | 0 ±0 (n=5) |
| cross.dispersion_mean | 0.2159 ±0.07897 (n=5) | 0.314 ±0.04505 (n=5) | 0.2382 ±0.04002 (n=5) |
| cross.wake_mean_per_round | 3.228 ±0.2117 (n=5) | 3.592 ±0.3384 (n=5) | 4.712 ±2.595 (n=5) |
| cross.flow_hhi | 0.3225 ±0.3102 (n=5) | 0.1947 ±0.1268 (n=5) | 0.2292 ±0.3785 (n=5) |
| usage.calls | 35 ±0 (n=5) | 34.2 ±2.683 (n=5) | 37.2 ±5.167 (n=5) |
| event_windows_avg.EQ_win_ret | -0.002219 ±0.01423 (n=5) | 0.008139 ±0.01676 (n=5) | -0.00364 ±0.0175 (n=5) |
| event_windows_avg.EQ_win_vol | 0.003455 ±0.005014 (n=5) | 0.009208 ±0.002418 (n=5) | 0.008728 ±0.006537 (n=5) |
| event_windows_avg.IR_win_ret | 0.001117 ±0.01115 (n=5) | -0.002895 ±0.01763 (n=5) | -0.009103 ±0.02226 (n=5) |
| event_windows_avg.win_dispersion | 0.2608 ±0.02668 (n=5) | 0.486 ±0.03258 (n=5) | 0.4248 ±0.0586 (n=5) |

- `baseline`: llm_calls=657, memo_hits=622, errors=0, elapsed=2s
- `fee_high`: llm_calls=816, memo_hits=778, errors=0, elapsed=2s
- `fee_low`: llm_calls=766, memo_hits=734, errors=0, elapsed=2s
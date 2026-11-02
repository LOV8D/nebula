# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | earnings_open_a | earnings_open_b |
|---|---|---|
| assets.EQ.total_ret | 0.2862 ±0.2694 (n=2) | -0.04612 ±0.02553 (n=2) |
| assets.EQ.ann_vol | 0.313 ±0.01678 (n=2) | 0.1592 ±0.1439 (n=2) |
| assets.EQ.max_drawdown | -0.01829 ±0.01127 (n=2) | -0.05225 ±0.03421 (n=2) |
| assets.EQ.excess_kurtosis | 9.188 ±9.637 (n=2) | 83.2 ±101 (n=2) |
| assets.EQ.avg_spread_bps | 14.1 ±0.823 (n=2) | 15.1 ±3.415 (n=2) |
| assets.EQ.total_volume | 7.51e+05 ±7.73e+04 (n=2) | 1.05e+05 ±8.26e+04 (n=2) |
| assets.IR.total_ret | -0.04353 ±0.1289 (n=2) | -0.002036 ±0.1875 (n=2) |
| assets.CRYPTO.ann_vol | 0.2856 ±0.01046 (n=2) | 0.2833 ±0.01365 (n=2) |
| cross.dispersion_mean | 0.07543 ±0.01283 (n=2) | 0.1193 ±0.007774 (n=2) |
| cross.wake_mean_per_round | 2.56 ±0.8395 (n=2) | 1.637 ±0.0417 (n=2) |
| cross.flow_hhi | 0.3258 ±0.08169 (n=2) | 0.7859 ±0.04369 (n=2) |
| usage.calls | 19 ±0 (n=2) | 19.5 ±0.7071 (n=2) |
| event_windows_avg.EQ_win_ret | 0.008275 ±0.004737 (n=2) | -0.03936 ±0.01597 (n=2) |
| event_windows_avg.EQ_win_vol | 0.002295 ±0.0006189 (n=2) | 0.002528 ±0.0006145 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.02258 ±0.01789 (n=2) | -0.04417 ±0.02278 (n=2) |
| event_windows_avg.IR_win90_ret | — | — |
| event_windows_avg.win_dispersion | 0.1628 ±0.04125 (n=2) | 0.3854 ±0.05526 (n=2) |

- `earnings_open_a`: llm_calls=428, memo_hits=409, errors=0, elapsed=119s
- `earnings_open_b`: llm_calls=426, memo_hits=407, errors=0, elapsed=162s
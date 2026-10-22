# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | 0.01352 ±0.007659 (n=2) | -0.06421 ±0.01907 (n=2) |
| assets.EQ.ann_vol | 0.5578 ±0.1667 (n=2) | 0.6438 ±0.2894 (n=2) |
| assets.EQ.max_drawdown | -0.0541 ±0.002321 (n=2) | -0.09576 ±0.02704 (n=2) |
| assets.EQ.excess_kurtosis | 32.7 ±23.8 (n=2) | 29.2 ±29.1 (n=2) |
| assets.EQ.avg_spread_bps | 11.8 ±5.966 (n=2) | 9.563 ±3.002 (n=2) |
| assets.EQ.total_volume | 8.49e+06 ±2.51e+06 (n=2) | 8.9e+06 ±2.73e+06 (n=2) |
| assets.IR.total_ret | 0.04547 ±0.001292 (n=2) | -0.05674 ±0.06275 (n=2) |
| assets.CRYPTO.ann_vol | 0.2841 ±0.01854 (n=2) | 0.2936 ±0.002262 (n=2) |
| cross.dispersion_mean | 0.2601 ±0.06687 (n=2) | 0.263 ±0.06958 (n=2) |
| cross.wake_mean_per_round | 3.647 ±0.3282 (n=2) | 3.65 ±0.31 (n=2) |
| cross.flow_hhi | 0.02771 ±0.01181 (n=2) | 0.1152 ±0.06267 (n=2) |
| usage.calls | 38.5 ±6.364 (n=2) | 39.5 ±7.778 (n=2) |
| event_windows_avg.EQ_win_ret | 0.006037 ±0.04078 (n=2) | -0.0347 ±0.01347 (n=2) |
| event_windows_avg.EQ_win_vol | 0.003247 ±0.0003457 (n=2) | 0.003398 ±0.0007986 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.006037 ±0.04078 (n=2) | -0.06708 ±0.05926 (n=2) |
| event_windows_avg.IR_win90_ret | 0.04181 ±0.02122 (n=2) | -0.07176 ±0.05785 (n=2) |
| event_windows_avg.win_dispersion | 0.1374 ±0.01804 (n=2) | 0.2029 ±0.04721 (n=2) |

- `news_a`: llm_calls=468, memo_hits=425, errors=0, elapsed=57s
- `news_b`: llm_calls=468, memo_hits=423, errors=0, elapsed=82s
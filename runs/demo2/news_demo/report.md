# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | 0.1246 ±0.007766 (n=2) | 0.03105 ±0.02445 (n=2) |
| assets.EQ.ann_vol | 0.2678 ±0.1226 (n=2) | 0.1548 ±0.009998 (n=2) |
| assets.EQ.max_drawdown | -0.01633 ±0.01159 (n=2) | -0.03995 ±0.009564 (n=2) |
| assets.EQ.excess_kurtosis | 6.343 ±0.7754 (n=2) | 19.7 ±12.1 (n=2) |
| assets.EQ.avg_spread_bps | 10.5 ±0.756 (n=2) | 10.8 ±0.2551 (n=2) |
| assets.EQ.total_volume | 5.45e+05 ±9.77e+04 (n=2) | 3.25e+05 ±2.67e+05 (n=2) |
| assets.IR.total_ret | 0.05148 ±0.04773 (n=2) | -0.09711 ±0.06668 (n=2) |
| assets.CRYPTO.ann_vol | 0.3008 ±0.01119 (n=2) | 0.2936 ±0.0006665 (n=2) |
| cross.dispersion_mean | 0.1532 ±0.0434 (n=2) | 0.1545 ±0.0005763 (n=2) |
| cross.wake_mean_per_round | 5.404 ±1.137 (n=2) | 5.447 ±1.173 (n=2) |
| cross.flow_hhi | 0.4187 ±0.5223 (n=2) | 0.4189 ±0.488 (n=2) |
| usage.calls | 84.5 ±0.7071 (n=2) | 79.5 ±2.121 (n=2) |
| event_windows_avg.EQ_win_ret | 0.007287 ±0.004192 (n=2) | -0.01502 ±0.006705 (n=2) |
| event_windows_avg.EQ_win_vol | 0.003498 ±0.002018 (n=2) | 0.001833 ±1.39e-05 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.03505 ±0.01254 (n=2) | -0.02521 ±0.007717 (n=2) |
| event_windows_avg.IR_win90_ret | 0.02141 ±0.02489 (n=2) | -0.04595 ±0.009337 (n=2) |
| event_windows_avg.win_dispersion | 0.2298 ±0.08276 (n=2) | 0.2754 ±0.01277 (n=2) |

- `news_a`: llm_calls=466, memo_hits=381, errors=0, elapsed=652s
- `news_b`: llm_calls=465, memo_hits=387, errors=2, elapsed=541s
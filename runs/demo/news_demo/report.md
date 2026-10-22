# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | 0.006924 ±0.0204 (n=2) | 0.0168 ±0.01453 (n=2) |
| assets.EQ.ann_vol | 0.4145 ±0.3333 (n=2) | 0.2009 ±0.1176 (n=2) |
| assets.EQ.max_drawdown | -0.05872 ±0.01561 (n=2) | -0.03424 ±0.008274 (n=2) |
| assets.EQ.excess_kurtosis | 22.3 ±0.4519 (n=2) | 47.1 ±25.4 (n=2) |
| assets.EQ.avg_spread_bps | 10.5 ±0.03249 (n=2) | 9.847 ±1.092 (n=2) |
| assets.EQ.total_volume | 4.13e+06 ±5.59e+06 (n=2) | 2.66e+06 ±3e+06 (n=2) |
| assets.IR.total_ret | -0.01559 ±0.05422 (n=2) | -0.04565 ±0.01973 (n=2) |
| assets.CRYPTO.ann_vol | 0.2931 ±0.01047 (n=2) | 0.2864 ±0.01758 (n=2) |
| cross.dispersion_mean | 0.2123 ±0.02886 (n=2) | 0.1352 ±0.05738 (n=2) |
| cross.wake_mean_per_round | 4.755 ±0.1469 (n=2) | 4.545 ±0.2556 (n=2) |
| cross.flow_hhi | 0.391 ±0.06372 (n=2) | 0.4999 ±0.03581 (n=2) |
| usage.calls | 30.5 ±0.7071 (n=2) | 31 ±1.414 (n=2) |
| event_windows_avg.EQ_win_ret | 0.009038 ±0.01314 (n=2) | -0.02312 ±0.01324 (n=2) |
| event_windows_avg.EQ_win_vol | 0.01118 ±0.009811 (n=2) | 0.00592 ±0.006119 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.03136 ±0.02403 (n=2) | -0.02809 ±0.006217 (n=2) |
| event_windows_avg.IR_win90_ret | -0.004706 ±0.01176 (n=2) | -0.04885 ±0.0003953 (n=2) |
| event_windows_avg.win_dispersion | 0.3574 ±0.05424 (n=2) | 0.432 ±0.009139 (n=2) |

- `news_a`: llm_calls=491, memo_hits=460, errors=0, elapsed=1s
- `news_b`: llm_calls=492, memo_hits=460, errors=0, elapsed=1s
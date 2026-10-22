# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | cb_magnet_off | cb_magnet_on |
|---|---|---|
| assets.EQ.total_ret | -0.01876 ±0.01024 (n=2) | -0.01876 ±0.01024 (n=2) |
| assets.EQ.ann_vol | 0.1099 ±0.01041 (n=2) | 0.1099 ±0.01041 (n=2) |
| assets.EQ.max_drawdown | -0.02896 ±0.01152 (n=2) | -0.02896 ±0.01152 (n=2) |
| assets.EQ.excess_kurtosis | 281 ±141 (n=2) | 281 ±141 (n=2) |
| assets.EQ.avg_spread_bps | 9.947 ±5.893 (n=2) | 9.947 ±5.893 (n=2) |
| assets.EQ.total_volume | 1.26e+05 ±1.34e+05 (n=2) | 1.26e+05 ±1.34e+05 (n=2) |
| assets.IR.total_ret | -0.1329 ±0.1656 (n=2) | -0.1329 ±0.1656 (n=2) |
| assets.CRYPTO.ann_vol | 0.3068 ±0.01342 (n=2) | 0.3068 ±0.01342 (n=2) |
| cross.dispersion_mean | 0.1779 ±0.04493 (n=2) | 0.1779 ±0.04493 (n=2) |
| cross.wake_mean_per_round | 5.818 ±0.446 (n=2) | 5.818 ±0.446 (n=2) |
| cross.flow_hhi | 0.5392 ±0.01408 (n=2) | 0.5392 ±0.01408 (n=2) |
| usage.calls | 67 ±1.414 (n=2) | 67 ±1.414 (n=2) |
| event_windows_avg.EQ_win_ret | -0.005109 ±2.762e-06 (n=2) | -0.005109 ±2.762e-06 (n=2) |
| event_windows_avg.EQ_win_vol | 0.0008768 ±7.864e-05 (n=2) | 0.0008768 ±7.864e-05 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.00533 ±0.000316 (n=2) | -0.00533 ±0.000316 (n=2) |
| event_windows_avg.IR_win90_ret | -0.07345 ±0.07624 (n=2) | -0.07345 ±0.07624 (n=2) |
| event_windows_avg.win_dispersion | 0.2316 ±0.0593 (n=2) | 0.2316 ±0.0593 (n=2) |

- `cb_magnet_off`: llm_calls=1694, memo_hits=1628, errors=0, elapsed=1s
- `cb_magnet_on`: llm_calls=1694, memo_hits=1628, errors=0, elapsed=1s
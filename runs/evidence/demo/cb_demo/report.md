# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | cb_magnet_off | cb_magnet_on |
|---|---|---|
| assets.EQ.total_ret | -0.04106 ±0.02131 (n=2) | -0.04106 ±0.02131 (n=2) |
| assets.EQ.ann_vol | 0.1318 ±0.02062 (n=2) | 0.1318 ±0.02062 (n=2) |
| assets.EQ.max_drawdown | -0.05593 ±0.02662 (n=2) | -0.05593 ±0.02662 (n=2) |
| assets.EQ.excess_kurtosis | 136 ±62.8 (n=2) | 136 ±62.8 (n=2) |
| assets.EQ.avg_spread_bps | 13.5 ±0.8856 (n=2) | 13.5 ±0.8856 (n=2) |
| assets.EQ.total_volume | 4.71e+04 ±2.27e+04 (n=2) | 4.71e+04 ±2.27e+04 (n=2) |
| assets.IR.total_ret | -0.3504 ±0.1418 (n=2) | -0.3504 ±0.1418 (n=2) |
| assets.CRYPTO.ann_vol | 0.3106 ±0.01872 (n=2) | 0.3106 ±0.01872 (n=2) |
| cross.dispersion_mean | 0.1502 ±0.005725 (n=2) | 0.1502 ±0.005725 (n=2) |
| cross.wake_mean_per_round | 6.037 ±0.136 (n=2) | 6.037 ±0.136 (n=2) |
| cross.flow_hhi | 0.4979 ±0.04433 (n=2) | 0.4979 ±0.04433 (n=2) |
| usage.calls | 71.5 ±7.778 (n=2) | 71.5 ±7.778 (n=2) |
| event_windows_avg.EQ_win_ret | -0.007968 ±0.004041 (n=2) | -0.007968 ±0.004041 (n=2) |
| event_windows_avg.EQ_win_vol | 0.0009396 ±0.0001675 (n=2) | 0.0009396 ±0.0001675 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.01044 ±0.006907 (n=2) | -0.01044 ±0.006907 (n=2) |
| event_windows_avg.IR_win90_ret | -0.1434 ±0.02272 (n=2) | -0.1434 ±0.02272 (n=2) |
| event_windows_avg.win_dispersion | 0.2409 ±0.04612 (n=2) | 0.2409 ±0.04612 (n=2) |

- `cb_magnet_off`: llm_calls=1694, memo_hits=1628, errors=0, elapsed=1s
- `cb_magnet_on`: llm_calls=1694, memo_hits=1628, errors=0, elapsed=1s
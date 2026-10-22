# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | cb_magnet_off | cb_magnet_on |
|---|---|---|
| assets.EQ.total_ret | -0.02448 ±0.01833 (n=2) | -0.02448 ±0.01833 (n=2) |
| assets.EQ.ann_vol | 0.1176 ±0.02132 (n=2) | 0.1176 ±0.02132 (n=2) |
| assets.EQ.max_drawdown | -0.03464 ±0.01955 (n=2) | -0.03464 ±0.01955 (n=2) |
| assets.EQ.excess_kurtosis | 278 ±146 (n=2) | 278 ±146 (n=2) |
| assets.EQ.avg_spread_bps | 7.866 ±2.949 (n=2) | 7.866 ±2.949 (n=2) |
| assets.EQ.total_volume | 1.34e+05 ±1.23e+05 (n=2) | 1.34e+05 ±1.23e+05 (n=2) |
| assets.IR.total_ret | -0.0199 ±0.005775 (n=2) | -0.0199 ±0.005775 (n=2) |
| assets.CRYPTO.ann_vol | 0.3025 ±0.01945 (n=2) | 0.3025 ±0.01945 (n=2) |
| cross.dispersion_mean | 0.227 ±0.02451 (n=2) | 0.227 ±0.02451 (n=2) |
| cross.wake_mean_per_round | 5.374 ±0.1813 (n=2) | 5.374 ±0.1813 (n=2) |
| cross.flow_hhi | 0.6494 ±0.1417 (n=2) | 0.6494 ±0.1417 (n=2) |
| usage.calls | 68.5 ±0.7071 (n=2) | 68.5 ±0.7071 (n=2) |
| event_windows_avg.EQ_win_ret | -0.006138 ±0.001459 (n=2) | -0.006138 ±0.001459 (n=2) |
| event_windows_avg.EQ_win_vol | 0.0009417 ±1.322e-05 (n=2) | 0.0009417 ±1.322e-05 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.009707 ±0.006506 (n=2) | -0.009707 ±0.006506 (n=2) |
| event_windows_avg.IR_win90_ret | -0.02023 ±0.000982 (n=2) | -0.02023 ±0.000982 (n=2) |
| event_windows_avg.win_dispersion | 0.225 ±0.0499 (n=2) | 0.225 ±0.0499 (n=2) |

- `cb_magnet_off`: llm_calls=1719, memo_hits=1650, errors=0, elapsed=1s
- `cb_magnet_on`: llm_calls=1719, memo_hits=1650, errors=0, elapsed=1s
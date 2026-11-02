# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | cb_magnet_off | cb_magnet_on |
|---|---|---|
| assets.EQ.total_ret | -0.03004 ±0.0482 (n=5) | -0.03004 ±0.0482 (n=5) |
| assets.EQ.ann_vol | 0.4985 ±0.09933 (n=5) | 0.5293 ±0.06731 (n=5) |
| assets.EQ.max_drawdown | -0.06609 ±0.02585 (n=5) | -0.06609 ±0.02585 (n=5) |
| assets.EQ.excess_kurtosis | 24.9 ±6.441 (n=5) | 21.7 ±7.959 (n=5) |
| assets.EQ.avg_spread_bps | 15.1 ±2.674 (n=5) | 14.8 ±2.524 (n=5) |
| assets.EQ.total_volume | 1.48e+07 ±2.84e+06 (n=5) | 1.48e+07 ±2.84e+06 (n=5) |
| assets.IR.total_ret | -0.07161 ±0.07469 (n=5) | -0.07161 ±0.07469 (n=5) |
| assets.CRYPTO.ann_vol | 0.09092 ±0.01084 (n=5) | 0.09092 ±0.01084 (n=5) |
| cross.dispersion_mean | 0.2673 ±0.03377 (n=5) | 0.2673 ±0.03377 (n=5) |
| cross.wake_mean_per_round | 5.547 ±0.2236 (n=5) | 5.547 ±0.2236 (n=5) |
| cross.flow_hhi | 0.5256 ±0.06994 (n=5) | 0.5431 ±0.06024 (n=5) |
| usage.calls | 68.2 ±1.789 (n=5) | 68.2 ±1.789 (n=5) |
| event_windows_avg.EQ_win_ret | -0.0131 ±0.005533 (n=5) | -0.0131 ±0.005533 (n=5) |
| event_windows_avg.EQ_win_vol | 0.005726 ±0.001219 (n=5) | 0.005821 ±0.001095 (n=5) |
| event_windows_avg.IR_win_ret | -0.01366 ±0.0281 (n=5) | -0.01366 ±0.0281 (n=5) |
| event_windows_avg.win_dispersion | 0.2674 ±0.03526 (n=5) | 0.2674 ±0.03526 (n=5) |

- `cb_magnet_off`: llm_calls=1696, memo_hits=1629, errors=0, elapsed=2s
- `cb_magnet_on`: llm_calls=1696, memo_hits=1629, errors=0, elapsed=2s
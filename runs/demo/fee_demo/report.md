# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | baseline | fee_high | fee_low |
|---|---|---|---|
| assets.EQ.total_ret | 0.03796 ±0.005741 (n=2) | 0.04981 ±0.04643 (n=2) | 0.03055 ±0.02681 (n=2) |
| assets.EQ.ann_vol | 0.2263 ±0.06592 (n=2) | 0.3162 ±0.2269 (n=2) | 0.2409 ±0.2529 (n=2) |
| assets.EQ.max_drawdown | -0.03004 ±0.01483 (n=2) | -0.02646 ±0.02137 (n=2) | -0.02166 ±0.02541 (n=2) |
| assets.EQ.excess_kurtosis | 28.5 ±20.9 (n=2) | 32.8 ±30.1 (n=2) | 64.4 ±21.4 (n=2) |
| assets.EQ.avg_spread_bps | 9.349 ±1.085 (n=2) | 11 ±0.3509 (n=2) | 8.627 ±0.2296 (n=2) |
| assets.EQ.total_volume | 6.88e+05 ±2.22e+05 (n=2) | 2.23e+06 ±2.3e+06 (n=2) | 2.45e+06 ±3.37e+06 (n=2) |
| assets.IR.total_ret | -0.06285 ±0.1736 (n=2) | -0.1095 ±0.1694 (n=2) | -0.06457 ±0.01665 (n=2) |
| assets.CRYPTO.ann_vol | 0.2922 ±0.01224 (n=2) | 0.2764 ±0.01704 (n=2) | 0.2838 ±0.0275 (n=2) |
| cross.dispersion_mean | 0.1605 ±0.03967 (n=2) | 0.2225 ±0.09062 (n=2) | 0.1975 ±0.05798 (n=2) |
| cross.wake_mean_per_round | 5.258 ±0.6944 (n=2) | 4.368 ±0.1469 (n=2) | 5.226 ±0.8195 (n=2) |
| cross.flow_hhi | 0.462 ±0.2635 (n=2) | 0.506 ±0.3285 (n=2) | 0.4868 ±0.2804 (n=2) |
| usage.calls | 46.5 ±2.121 (n=2) | 40 ±2.828 (n=2) | 41.5 ±0.7071 (n=2) |
| event_windows_avg.EQ_win_ret | 0.01345 ±0.002373 (n=2) | 0.007024 ±0.01135 (n=2) | 0.01157 ±0.0081 (n=2) |
| event_windows_avg.EQ_win_vol | 0.0004928 ±1.232e-05 (n=2) | 0.008031 ±0.00994 (n=2) | 0.008119 ±0.008733 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.006348 ±0.003691 (n=2) | 0.01067 ±0.006195 (n=2) | 0.002828 ±0.02113 (n=2) |
| event_windows_avg.IR_win90_ret | -0.03481 ±0.04934 (n=2) | -0.05692 ±0.08088 (n=2) | -0.04762 ±0.05243 (n=2) |
| event_windows_avg.win_dispersion | 0.3155 ±0.1361 (n=2) | 0.4677 ±0.07022 (n=2) | 0.405 ±0.0961 (n=2) |

- `baseline`: llm_calls=698, memo_hits=653, errors=0, elapsed=1s
- `fee_high`: llm_calls=801, memo_hits=763, errors=0, elapsed=1s
- `fee_low`: llm_calls=810, memo_hits=769, errors=0, elapsed=1s
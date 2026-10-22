# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | -0.02676 ±0.06803 (n=2) | -0.001237 ±0.01098 (n=2) |
| assets.EQ.ann_vol | 0.4648 ±0.2622 (n=2) | 0.2146 ±0.09825 (n=2) |
| assets.EQ.max_drawdown | -0.08587 ±0.05402 (n=2) | -0.0508 ±0.01514 (n=2) |
| assets.EQ.excess_kurtosis | 52.1 ±42.6 (n=2) | 101 ±50.8 (n=2) |
| assets.EQ.avg_spread_bps | 9.907 ±0.7999 (n=2) | 10.3 ±1.67 (n=2) |
| assets.EQ.total_volume | 4.19e+06 ±5.5e+06 (n=2) | 2.41e+06 ±3.35e+06 (n=2) |
| assets.IR.total_ret | 0.03031 ±0.01069 (n=2) | -0.002072 ±0.0419 (n=2) |
| assets.CRYPTO.ann_vol | 0.2992 ±0.001746 (n=2) | 0.2959 ±0.004127 (n=2) |
| cross.dispersion_mean | 0.1962 ±0.05157 (n=2) | 0.1432 ±0.04615 (n=2) |
| cross.wake_mean_per_round | 5.676 ±1.155 (n=2) | 5.313 ±1.342 (n=2) |
| cross.flow_hhi | 0.2916 ±0.2044 (n=2) | 0.5256 ±0.0005576 (n=2) |
| usage.calls | 29 ±1.414 (n=2) | 29 ±1.414 (n=2) |
| event_windows_avg.EQ_win_ret | -0.01476 ±0.0468 (n=2) | -0.02994 ±0.003592 (n=2) |
| event_windows_avg.EQ_win_vol | 0.01318 ±0.006988 (n=2) | 0.006732 ±0.004971 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.05665 ±0.0598 (n=2) | -0.04681 ±0.02027 (n=2) |
| event_windows_avg.IR_win90_ret | 0.01613 ±0.0177 (n=2) | -0.02432 ±0.03508 (n=2) |
| event_windows_avg.win_dispersion | 0.4002 ±0.006366 (n=2) | 0.3911 ±0.06696 (n=2) |

- `news_a`: llm_calls=482, memo_hits=454, errors=0, elapsed=0s
- `news_b`: llm_calls=482, memo_hits=454, errors=0, elapsed=1s
# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | 0.154 ±0.05746 (n=2) | -0.009805 ±0.03492 (n=2) |
| assets.EQ.ann_vol | 0.2613 ±0.03417 (n=2) | 0.1223 ±0.03019 (n=2) |
| assets.EQ.max_drawdown | -0.01521 ±0.0003711 (n=2) | -0.0691 ±0.03317 (n=2) |
| assets.EQ.excess_kurtosis | 6.025 ±0.788 (n=2) | 15.7 ±11.2 (n=2) |
| assets.EQ.avg_spread_bps | 10.9 ±1.073 (n=2) | 10.3 ±0.8132 (n=2) |
| assets.EQ.total_volume | 5.41e+05 ±6.95e+04 (n=2) | 3.35e+05 ±2.82e+05 (n=2) |
| assets.IR.total_ret | 0.02895 ±0.03735 (n=2) | -0.1098 ±0.1417 (n=2) |
| assets.CRYPTO.ann_vol | 0.3112 ±0.00423 (n=2) | 0.3125 ±0.01908 (n=2) |
| cross.dispersion_mean | 0.1509 ±0.01635 (n=2) | 0.1532 ±0.003266 (n=2) |
| cross.wake_mean_per_round | 5.503 ±1.15 (n=2) | 5.408 ±1.135 (n=2) |
| cross.flow_hhi | 0.4134 ±0.538 (n=2) | 0.5314 ±0.3183 (n=2) |
| usage.calls | 27 ±1.414 (n=2) | 27 ±1.414 (n=2) |
| event_windows_avg.EQ_win_ret | 3.343e-06 ±0.001705 (n=2) | -0.02756 ±0.01011 (n=2) |
| event_windows_avg.EQ_win_vol | 0.002288 ±0.0004557 (n=2) | 0.001889 ±0.0001284 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.0262 ±0.005789 (n=2) | -0.04527 ±0.03516 (n=2) |
| event_windows_avg.IR_win90_ret | 0.0182 ±0.01223 (n=2) | -0.05034 ±0.02859 (n=2) |
| event_windows_avg.win_dispersion | 0.2647 ±0.0274 (n=2) | 0.2856 ±0.0136 (n=2) |

- `news_a`: llm_calls=467, memo_hits=441, errors=1, elapsed=144s
- `news_b`: llm_calls=467, memo_hits=441, errors=1, elapsed=40s
# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | -0.02902 ±0.06483 (n=2) | 0.004076 ±0.01849 (n=2) |
| assets.EQ.ann_vol | 0.2308 ±0.06863 (n=2) | 0.1616 ±0.0233 (n=2) |
| assets.EQ.max_drawdown | -0.08947 ±0.04893 (n=2) | -0.05804 ±0.0049 (n=2) |
| assets.EQ.excess_kurtosis | 59.5 ±32.1 (n=2) | 85.1 ±73.3 (n=2) |
| assets.EQ.avg_spread_bps | 9.289 ±0.07392 (n=2) | 10.7 ±1.113 (n=2) |
| assets.EQ.total_volume | 2.17e+05 ±1.25e+05 (n=2) | 8.49e+04 ±6.01e+04 (n=2) |
| assets.IR.total_ret | -0.04839 ±0.122 (n=2) | -0.05354 ±0.1147 (n=2) |
| assets.CRYPTO.ann_vol | 0.3103 ±0.01748 (n=2) | 0.3006 ±0.01088 (n=2) |
| cross.dispersion_mean | 0.1588 ±0.001378 (n=2) | 0.1301 ±0.02769 (n=2) |
| cross.wake_mean_per_round | 5.759 ±1.037 (n=2) | 5.628 ±0.8957 (n=2) |
| cross.flow_hhi | 0.3922 ±0.3467 (n=2) | 0.5715 ±0.06435 (n=2) |
| usage.calls | 29.5 ±2.121 (n=2) | 29.5 ±2.121 (n=2) |
| event_windows_avg.EQ_win_ret | -0.03211 ±0.02225 (n=2) | -0.0228 ±0.006514 (n=2) |
| event_windows_avg.EQ_win_vol | 0.005323 ±0.004118 (n=2) | 0.002827 ±0.0005521 (n=2) |
| event_windows_avg.EQ_win90_ret | -0.05766 ±0.05838 (n=2) | -0.03967 ±0.03037 (n=2) |
| event_windows_avg.IR_win90_ret | -0.002593 ±0.04417 (n=2) | -0.01667 ±0.02426 (n=2) |
| event_windows_avg.win_dispersion | 0.3056 ±0.1402 (n=2) | 0.2727 ±0.1005 (n=2) |

- `news_a`: llm_calls=482, memo_hits=454, errors=0, elapsed=1s
- `news_b`: llm_calls=482, memo_hits=454, errors=0, elapsed=1s
# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | news_a | news_b |
|---|---|---|
| assets.EQ.total_ret | 0.003578 ±0.0382 (n=5) | -0.02762 ±0.05698 (n=5) |
| assets.EQ.ann_vol | 0.4805 ±0.2798 (n=5) | 0.4179 ±0.1445 (n=5) |
| assets.EQ.max_drawdown | -0.07574 ±0.05411 (n=5) | -0.08023 ±0.04049 (n=5) |
| assets.EQ.excess_kurtosis | 67.8 ±108 (n=5) | 27.7 ±7.949 (n=5) |
| assets.EQ.avg_spread_bps | 8.491 ±3.575 (n=5) | 9.622 ±0.7942 (n=5) |
| assets.EQ.total_volume | 1.21e+07 ±7.38e+06 (n=5) | 1.33e+07 ±4.53e+06 (n=5) |
| assets.IR.total_ret | 0.07328 ±0.1312 (n=5) | -0.02282 ±0.1303 (n=5) |
| assets.CRYPTO.ann_vol | 0.000635 ±0.0008695 (n=5) | 0.04241 ±0.05465 (n=5) |
| cross.dispersion_mean | 0.2745 ±0.08266 (n=5) | 0.2667 ±0.0219 (n=5) |
| cross.wake_mean_per_round | 2.584 ±0.8918 (n=5) | 2.609 ±0.2949 (n=5) |
| cross.flow_hhi | 0.4947 ±0.2373 (n=5) | 0.5939 ±0.2079 (n=5) |
| usage.calls | 19 ±4.472 (n=5) | 21.8 ±4.207 (n=5) |
| event_windows_avg.EQ_win_ret | -0.005931 ±0.02851 (n=5) | -0.01698 ±0.01525 (n=5) |
| event_windows_avg.EQ_win_vol | 0.01019 ±0.007262 (n=5) | 0.01035 ±0.001155 (n=5) |
| event_windows_avg.IR_win_ret | -0.0009791 ±0.01592 (n=5) | 0.00048 ±0.01902 (n=5) |
| event_windows_avg.win_dispersion | 0.3279 ±0.1152 (n=5) | 0.3992 ±0.02694 (n=5) |

- `news_a`: llm_calls=439, memo_hits=422, errors=0, elapsed=2s
- `news_b`: llm_calls=459, memo_hits=435, errors=0, elapsed=1s
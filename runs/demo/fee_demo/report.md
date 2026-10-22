# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | baseline | fee_high | fee_low |
|---|---|---|---|
| assets.EQ.total_ret | 0.02809 ±0.0197 (n=2) | -0.03158 ±0.06867 (n=2) | 0.002332 ±0.0131 (n=2) |
| assets.EQ.ann_vol | 0.2304 ±0.0602 (n=2) | 0.3343 ±0.2012 (n=2) | 0.2826 ±0.1939 (n=2) |
| assets.EQ.max_drawdown | -0.05052 ±0.01413 (n=2) | -0.07397 ±0.04582 (n=2) | -0.0595 ±0.02811 (n=2) |
| assets.EQ.excess_kurtosis | 27.7 ±22.1 (n=2) | 42.8 ±16 (n=2) | 37.2 ±16.9 (n=2) |
| assets.EQ.avg_spread_bps | 9.411 ±1.172 (n=2) | 10.6 ±0.2907 (n=2) | 8.636 ±0.2171 (n=2) |
| assets.EQ.total_volume | 6.9e+05 ±2.21e+05 (n=2) | 2.05e+06 ±2.56e+06 (n=2) | 2.66e+06 ±3.08e+06 (n=2) |
| assets.IR.total_ret | 0.04451 ±0.02179 (n=2) | 0.02258 ±0.01736 (n=2) | -0.06191 ±0.02043 (n=2) |
| assets.CRYPTO.ann_vol | 0.3022 ±0.001889 (n=2) | 0.2907 ±0.003204 (n=2) | 0.2981 ±0.007256 (n=2) |
| cross.dispersion_mean | 0.1837 ±0.006874 (n=2) | 0.2749 ±0.01649 (n=2) | 0.1978 ±0.05753 (n=2) |
| cross.wake_mean_per_round | 6.353 ±2.243 (n=2) | 5.25 ±1.394 (n=2) | 5.654 ±1.425 (n=2) |
| cross.flow_hhi | 0.5133 ±0.191 (n=2) | 0.4302 ±0.4357 (n=2) | 0.5223 ±0.2302 (n=2) |
| usage.calls | 46 ±2.828 (n=2) | 38.5 ±4.95 (n=2) | 39.5 ±3.536 (n=2) |
| event_windows_avg.EQ_win_ret | 0.015 ±0.0001842 (n=2) | -0.01236 ±0.03877 (n=2) | 0.01121 ±0.007585 (n=2) |
| event_windows_avg.EQ_win_vol | 0.000827 ±0.0004602 (n=2) | 0.009113 ±0.00841 (n=2) | 0.007421 ±0.009719 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.01554 ±0.009309 (n=2) | -0.03546 ±0.07144 (n=2) | 0.005618 ±0.02508 (n=2) |
| event_windows_avg.IR_win90_ret | -0.0008782 ±0.001349 (n=2) | -0.0008122 ±0.001542 (n=2) | -0.05406 ±0.04333 (n=2) |
| event_windows_avg.win_dispersion | 0.3565 ±0.07817 (n=2) | 0.4226 ±0.134 (n=2) | 0.4177 ±0.07818 (n=2) |

- `baseline`: llm_calls=696, memo_hits=652, errors=0, elapsed=1s
- `fee_high`: llm_calls=785, memo_hits=750, errors=0, elapsed=1s
- `fee_low`: llm_calls=787, memo_hits=750, errors=0, elapsed=1s
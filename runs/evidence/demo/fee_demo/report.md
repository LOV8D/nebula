# Wind Tunnel — cross-scenario relative differences

Direction and ranking only; no effect sizes. Model provenance per run in `manifest.json`.

| metric | baseline | fee_high | fee_low |
|---|---|---|---|
| assets.EQ.total_ret | 0.01755 ±0.004799 (n=2) | 0.1095 ±0.2682 (n=2) | 0.1569 ±0.2317 (n=2) |
| assets.EQ.ann_vol | 0.2528 ±0.09187 (n=2) | 0.2227 ±0.04338 (n=2) | 0.2156 ±0.0991 (n=2) |
| assets.EQ.max_drawdown | -0.07583 ±0.02167 (n=2) | -0.05811 ±0.06824 (n=2) | -0.04622 ±0.04689 (n=2) |
| assets.EQ.excess_kurtosis | 7.569 ±6.331 (n=2) | 18 ±19 (n=2) | 16.1 ±12.9 (n=2) |
| assets.EQ.avg_spread_bps | 10.7 ±0.6321 (n=2) | 11.1 ±0.9954 (n=2) | 9.341 ±1.214 (n=2) |
| assets.EQ.total_volume | 5.78e+05 ±6.34e+04 (n=2) | 2.95e+05 ±7.49e+04 (n=2) | 5.07e+05 ±4.28e+04 (n=2) |
| assets.IR.total_ret | -0.04343 ±0.1026 (n=2) | -0.03236 ±0.09505 (n=2) | -0.09105 ±0.06165 (n=2) |
| assets.CRYPTO.ann_vol | 0.2975 ±0.008589 (n=2) | 0.3033 ±0.01465 (n=2) | 0.3034 ±0.01479 (n=2) |
| cross.dispersion_mean | 0.1698 ±0.01279 (n=2) | 0.2022 ±0.08638 (n=2) | 0.1325 ±0.03472 (n=2) |
| cross.wake_mean_per_round | 6.835 ±1.561 (n=2) | 5.603 ±0.8957 (n=2) | 5.968 ±0.9809 (n=2) |
| cross.flow_hhi | 0.4695 ±0.129 (n=2) | 0.3826 ±0.3683 (n=2) | 0.4735 ±0.1612 (n=2) |
| usage.calls | 46.5 ±3.536 (n=2) | 40.5 ±7.778 (n=2) | 41.5 ±6.364 (n=2) |
| event_windows_avg.EQ_win_ret | 0.00554 ±0.01319 (n=2) | -0.01404 ±0.0364 (n=2) | 0.006587 ±0.01412 (n=2) |
| event_windows_avg.EQ_win_vol | 0.002488 ±0.001889 (n=2) | 0.003948 ±0.001106 (n=2) | 0.00176 ±0.001712 (n=2) |
| event_windows_avg.EQ_win90_ret | 0.001643 ±0.02896 (n=2) | 0.002734 ±0.1255 (n=2) | 0.01988 ±0.004902 (n=2) |
| event_windows_avg.IR_win90_ret | -0.02203 ±0.02856 (n=2) | -0.01073 ±0.01248 (n=2) | -0.02571 ±0.003234 (n=2) |
| event_windows_avg.win_dispersion | 0.3584 ±0.0808 (n=2) | 0.3273 ±0.0008005 (n=2) | 0.3533 ±0.01283 (n=2) |

- `baseline`: llm_calls=696, memo_hits=652, errors=0, elapsed=1s
- `fee_high`: llm_calls=785, memo_hits=750, errors=0, elapsed=1s
- `fee_low`: llm_calls=787, memo_hits=750, errors=0, elapsed=1s
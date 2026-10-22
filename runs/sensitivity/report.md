# Model x prompt sensitivity — news-wording A/B

Question (BP red line): does the qualitative conclusion — alarming
framing is worse than neutral — survive a change of brain or prompt?
Direction and ranking only; no effect sizes.

| model | prompt | neutral (day) | alarming (day) | day separation | 90-win neutral | 90-win alarming |
|---|---|---|---|---|---|---|
| deepseek-v4.1-flash-1017 | p1 | +8.1% | -0.1% | neutral > alarming | +1.6% | -2.9% |
| deepseek-v4.1-flash-1017 | p2 | +1.8% | -0.6% | neutral > alarming | -2.7% | -0.1% |
| glm-5.3-flash | p1 | +8.9% | -3.6% | neutral > alarming | -0.9% | -6.8% |
| glm-5.3-flash | p2 | +14.9% | +4.0% | neutral > alarming | +2.7% | -1.0% |

**Verdict: STABLE** — 4/4 brain/prompt combos show neutral > alarming on full-day EQ returns.

Honest caveats: (1) the 90-round event window is mixed across combos — day-total returns are the stable unit here, the 30-round knee-jerk window less so (2 seeds each, and both framings dip first on some combos); (2) transient provider errors on some runs (0–12 per run) were absorbed by retry + Tier-B fallback — provenance in each run's manifest; (3) seeds per combo: 2; raw per-seed values in `results.json`.

Runs share one response cache; every run's manifest records the exact model + prompt version. Reproduce: `python3 -m runtime.cli sensitivity --seeds 2`.
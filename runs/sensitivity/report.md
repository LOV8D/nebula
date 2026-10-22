# Model x prompt sensitivity — news-wording A/B

Question (BP red line): does the qualitative conclusion — alarming
framing is worse than neutral — survive a change of brain or prompt?
Direction and ranking only.

| model | prompt | neutral (day) | alarming (day) | separation | llm errors | conclusion stable? |
|---|---|---|---|---|---|---|
| deepseek-v4.1-flash-1017 | p1 | +1.6% | +10.8% | -9.2% | 453 | no (inverted) * |
| deepseek-v4.1-flash-1017 | p2 | +11.8% | +2.5% | +9.3% | 108 | yes * |
| glm-5.3-flash | p1 | +18.3% | +2.9% | +15.4% | 4 | yes |
| glm-5.3-flash | p2 | +8.5% | +2.7% | +5.9% | 0 | yes |

**Verdict: FLIPS.** 4 brain/prompt combos, 3/4 show neutral > alarming on full-day EQ.

The conclusion inverts across brains/prompts — report this instability alongside any headline result. Per BP: sensitivity is a deliverable, not noise.

`\*` marks an error-polluted combo (>50 failed LLM attempts,
3 tries each): many decisions fell back to the Tier-B policy tier,
so that row is weak evidence — rerun with more seeds before
quoting its direction.
Seeds per combo: 2. Raw per-seed values in `results.json`.
Runs use the shared response cache; provenance in each run's manifest.
# Model x prompt sensitivity — news-wording A/B

Question (BP red line): does the qualitative conclusion — alarming
framing is worse than neutral — survive a change of brain or prompt?
Direction and ranking only.

| model | prompt | neutral (day) | alarming (day) | separation | per seed | llm errors | $/combo (est.) | conclusion stable? |
|---|---|---|---|---|---|---|---|---|
| glm-5.3-flash | p1 | +15.1% | +9.6% | +5.5% | -11.7% / +22.7% | 0 | $0.01 | mixed (seeds disagree) |
| glm-5.3-flash | p2 | -2.4% | +5.3% | -7.7% | -4.6% / -10.8% | 0 | $0.01 | no (inverted) |

**Verdict: STABLE.** 2 brain/prompt combos, 0/2 show neutral > alarming on full-day EQ in every seed.


`\*` marks an error-polluted combo (>50 failed LLM attempts,
3 tries each): many decisions fell back to the Tier-B policy tier,
so that row is weak evidence — rerun with more seeds before
quoting its direction.
Seeds per combo: 2. Raw per-seed values in `results.json`.
Runs use the shared response cache; provenance in each run's manifest.

`$/combo (est.)` is an estimate, not a quote: metered in/out tokens
for both arms and all seeds of the combo, priced at glm-5.3-flash $0.15/$0.5 per Mtok in/out. `out_tokens` is estimated at ~4 chars/token when the provider
omits usage; cache hits are already excluded (prompts shared across
runs are paid once). Models without a listed price show `—`.
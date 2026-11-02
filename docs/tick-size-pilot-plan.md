# Tick Size Pilot replication — feasibility & pre-registration (v0)

> 2026-11-01. First case for the `historical_intervention` track of
> `evaluation/benchmark_v0.json`. Written before any post-pilot data was
> pulled (the pipeline cannot score without the predictions file registered
> here). Repo language: English. BP red lines apply: direction and ranking
> only, no effect sizes, failures are reported not smoothed over.

## 1. What this case is for

The BP's first public evidence (05 §7): recover the **direction** of the
SEC Tick Size Pilot's known market-quality effects from public data,
without seeing the post-pilot answer when the predictions were registered,
and beat simple baselines. Success = a quotable, pre-registered replication;
failure = published too (that is the product's honesty claim, not a loss).

## 2. Pilot design (facts, with one flagged to verify)

- Mandated study of minimum tick sizes for smaller-cap US stocks; ran
  **2016-10-03 → 2018-09-03** (two years, extended by two months).【fact】
- Four groups, roughly 400 securities each, stratified random sampling:
  Control (unchanged ticks) and three test groups quoted in **$0.05**.【fact】
- Group rules per FINRA's own list files (C / G1 / G2 / G3): G1 quoted in
  $0.05 but traded at the regular increment; G2 quoted and traded in $0.05
  with exemptions (midpoint, retail, negotiated); G3 = G2 plus a trade-at
  requirement with a block-size exemption. FINRA's `TSPTestSymbols.txt`
  (fetched 2026-11-01) confirms the C/G1/G2/G3 labels and the pipe format
  `Ticker|Name|Exchange|Effective_Date|Group`.【fact, primary source】
- Eligibility (per the SEC pilot plan): closing price above ~$2, market cap
  ≤ ~$3.0B, average daily volume ≤ ~1M shares over the trailing six
  months. **To verify against the SEC order text (Release 34-72574) when
  the sample is assembled** — third-party summaries of the exact thresholds
  and of which group carried trade-at disagree with each other; FINRA's
  group files are treated as authoritative for assignments.【fact/verify】
- Known result (what we predict below, from DERA's published evaluation and
  the 2022 revisit paper): relative to control, test groups showed wider
  spreads, lower price efficiency, and (for tick-constrained names) higher
  small-trade costs; the pilot expired without rule changes.【fact】

## 3. Feasibility: metric × data source (the honest table)

| DERA metric | Free daily-data proxy | Estimator | Known biases | Verdict |
|---|---|---|---|---|
| Quoted/effective spread | estimated relative spread | Corwin–Schultz (2012) high–low, 2-day; Abdi–Ranaldo (2017) close-to-close as robustness | upward bias for high-vol names; must use split-consistent series; overnight component | **in scope** (direction only) |
| Volatility | daily close-to-close + range-based | stdev of returns; Parkinson (high–low) | overnight jumps mixed in; Parkinson assumes continuous trading | **in scope** |
| Price efficiency | variance ratio deviation | Lo–MacKinlay VR(q=5) on daily closes | small-sample noise; heteroskedasticity-robust z needed | **in scope** |
| Depth at best quote | — | needs TAQ quotes | — | **out of scope** (not predicted) |
| Small-trade execution costs | — | needs TAQ trade-and-quote | — | **out of scope** (not predicted) |

Data sources: Yahoo public chart endpoint (already used by
`runtime/snapshot.py`; raw OHLC + adjclose per day, no key) with Stooq CSV
as fallback. Sample list: FINRA `TSPilotSecurities.txt` daily files — the
live URL now serves a blank post-pilot file, so the list must come from
archived snapshots (Wayback Machine captures of the daily file, 2016–2019)
or the SEC order appendix; the loader parses the verified pipe format and
**rejects a list whose group counts are wildly off ~400/group** as a
sanity check.【fact/judgment】

Paid alternative if direction-only proves too coarse: TAQ/CRSP via WRDS
(budget item, not needed for v0).

## 4. Pre-registered predictions (H1–H3)

Windows: **pre** = 2016-07-01 → 2016-09-30 (baseline; may be pulled for
calibration), **post** = 2016-10-03 → 2017-03-31 (primary scoring window;
may only be pulled after the predictions JSON is committed), full pilot as
robustness. Pooled test arms: each of G1, G2, G3 and TG-all vs Control.

| # | Metric (estimator) | Prediction (test vs control, post vs pre) | Baseline to beat |
|---|---|---|---|
| H1 | relative spread (Corwin–Schultz; AR robustness) | **rises** for G2/G3 (tick-constrained); G1 ambiguous — recorded as a two-sided question, no direction claimed | naive null: no change |
| H2 | volatility (Parkinson + close-close) | **rises** for G2/G3 | naive null |
| H3 | price efficiency (VR(5), \|VR−1\|) | **rises** for G2/G3 (efficiency declines) | naive null |

Scoring: a prediction "hits" when the sign of the pooled test-minus-control
change matches the registered direction in the post window. Secondary:
ordering across G1/G2/G3 recorded but **not scored as a claim** (no
pre-registered ranking). `score` refuses to run unless
`evaluation/tsp_predictions.json` exists; the file's SHA-256 is recorded
into the result. Predictions registered 2026-11-01, before any post-window
data pull.

Explicitly **not claimed**: effect sizes, statistical significance as a
product claim (report z/t only as diagnostics), depth, trade costs, any
G1 direction (insufficient prior — flagged, not guessed).

## 5. Failure conditions (BP red line)

- ≥2 of H1–H3 miss their registered direction → **replication failed**;
  write the negative result into the benchmark registry and report it
  publicly alongside the sensitivity instability results.
- Corwin–Schultz and Abdi–Ranaldo disagree in sign on H1 → report both,
  claim nothing; treat estimator disagreement as its own finding.
- Sample list cannot be reconstructed with plausible group counts → the
  case stays `planned`; no partial claims.

## 6. Pipeline (experiments/tick_size_pilot.py)

`load_sample` (FINRA pipe format, sanity gates) → `fetch_daily` (Yahoo,
cached under `runs/scratch/tsp_data/`) → estimators (CS, AR, Parkinson,
VR) → group/window stats → `compare` (directional verdicts) →
`score` (masked, refuses without registered predictions). A `--dry-run`
mode generates synthetic OHLC with a planted spread-widening effect and
verifies the full chain recovers it — proving the estimators and scoring
without touching real post data.

## 7. Next steps after v0

1. Reconstruct the sample list (Wayback/SEC appendix), run for real.
2. Decide on TAQ (WRDS) for depth/trade-cost metrics — that is the
   difference between "direction replication" and a DERA-grade study.
3. Nebula sim arm: encode $0.05 tick vs $0.01 in the MarketWorld and
   predict the same directions in-silico before looking at the real post
   window — this is the step that turns the case into product evidence
   rather than an econometrics exercise.
4. Second historical case per benchmark_v0: Regulation SHO Pilot.

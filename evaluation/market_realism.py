"""First registered market-realism evaluation: stylized facts vs a null model.

Scope (v0, honest): descriptive realism of the EQ book in recorded runs —
fat tails, volatility clustering, absence of linear return autocorrelation,
and a positive bid-ask spread. Baselines are per-run permutation nulls (the
run's own return series shuffled), not yet historical resampling or an
ABIDES-class simulator; depth-at-best-quote and small-trade costs need TAQ
and are declared out of scope. Committed demo (mock brain) and demo2
(real GLM brain) runs are both in scope; each per-run row records its brain.

Pre-registered tolerances (this file is the registration):
  fat_tails       excess kurtosis > 0                        in >= 80% of runs
  vol_clustering  |r| acorr(1) > 0 and permutation p < 0.05   in >= 60% of runs
  no_serial_corr  r acorr(1) inside its 95% permutation band  in >= 80% of runs
  spread_positive avg_spread_bps > 0 (from summary.json)      in >= 80% of runs

  status = pass     all four facts met
           partial  at least two facts met (narrower than the product claim)
           blocked  fewer than two (a validity failure, not a mere absence)

Usage:
  python3 -m evaluation.market_realism            # dry run, prints only
  python3 -m evaluation.market_realism --apply    # append to results.json
"""
import hashlib
import json
import math
import random
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).with_name("results.json")
PERMUTATIONS = 2000
FACT_SHARES = {"fat_tails": 0.80, "vol_clustering": 0.60,
               "no_serial_corr": 0.80, "spread_positive": 0.80}


def _read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _acorr(x):
    n = len(x)
    if n < 3 or sum(v * v for v in x) == 0:
        return 0.0
    m = sum(x) / n
    c0 = sum((v - m) ** 2 for v in x) / n
    c1 = sum((x[i] - m) * (x[i - 1] - m) for i in range(1, n)) / n
    return c1 / c0 if c0 else 0.0


def _excess_kurtosis(rs):
    n = len(rs)
    if n < 4:
        return 0.0
    mu = sum(rs) / n
    m2 = sum((r - mu) ** 2 for r in rs) / n
    m4 = sum((r - mu) ** 4 for r in rs) / n
    return m4 / m2 ** 2 - 3.0 if m2 else 0.0


def _perm_p(observed, series, stat, rng):
    """Two-sided permutation p-value of stat(series) under shuffling."""
    if abs(observed) < 1e-12:
        return 1.0
    hits = 0
    for _ in range(PERMUTATIONS):
        s = list(series)
        rng.shuffle(s)
        if abs(stat(s)) >= abs(observed):
            hits += 1
    return hits / PERMUTATIONS


def _perm_band(series, stat, rng):
    """95% two-sided band of stat under shuffling (2.5th/97.5th percentile)."""
    vals = []
    for _ in range(PERMUTATIONS):
        s = list(series)
        rng.shuffle(s)
        vals.append(stat(s))
    vals.sort()
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(0.975 * (len(vals) - 1))]
    return lo, hi


def evaluate_run(run_dir, rng):
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    manifest = {}
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text())
    except (OSError, ValueError):
        pass
    brain = (manifest.get("five_tuple", {}).get("model", {}) or {}).get(
        "model_id", "?")
    marks = _read_jsonl(run_dir / "marks.jsonl")
    prices = [m["price"] for m in marks if m["asset"] == "EQ" and m.get("price")]
    rets = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))
            if prices[i - 1] > 0]
    abs_r = [abs(r) for r in rets]
    out = {"run": str(run_dir.relative_to(ROOT)), "brain": brain,
           "n_rets": len(rets)}
    if len(rets) < 30:
        out["skipped"] = "too few returns"
        return out
    kurt = _excess_kurtosis(rets)
    clust = _acorr(abs_r)
    clust_p = _perm_p(clust, abs_r, _acorr, rng)
    serial = _acorr(rets)
    band = _perm_band(rets, _acorr, rng)
    spread = summary["assets"]["EQ"].get("avg_spread_bps")
    out.update(
        excess_kurtosis=round(kurt, 2),
        fat_tails=kurt > 0,
        vol_clustering_lag1=round(clust, 4),
        vol_clustering_p=round(clust_p, 4),
        vol_clustering=clust > 0 and clust_p < 0.05,
        ret_acorr_lag1=round(serial, 4),
        serial_band=[round(band[0], 4), round(band[1], 4)],
        no_serial_corr=band[0] <= serial <= band[1],
        avg_spread_bps=round(spread, 2) if spread is not None else None,
        spread_positive=bool(spread and spread > 0),
    )
    return out


def run(runs_glob, apply=False, asset="EQ"):
    globs = runs_glob if isinstance(runs_glob, (list, tuple)) else [runs_glob]
    run_dirs = sorted({p for g in globs for p in ROOT.glob(g)
                       if (p / "summary.json").exists()})
    if not run_dirs:
        raise SystemExit(f"no run dirs match {globs}")
    rng = random.Random(20261101)
    per_run = [r for r in (evaluate_run(d, rng) for d in run_dirs)
               if not r.get("skipped")]
    if not per_run:
        raise SystemExit("no usable runs")
    facts = {k: sum(1 for r in per_run if r.get(k)) / len(per_run)
             for k in FACT_SHARES}
    met = {k: v >= FACT_SHARES[k] for k, v in facts.items()}
    n_met = sum(met.values())
    status = "pass" if n_met == len(FACT_SHARES) else \
             ("partial" if n_met >= 2 else "blocked")
    brains = sorted({r.get("brain", "?") for r in per_run})
    scope = (f"{len(per_run)} recorded EQ return series "
             f"({', '.join(globs)}); brains: {', '.join(brains)}; "
             f"null = per-run return-shuffle permutation, n={PERMUTATIONS}")
    evidence = "; ".join(f"{k} {facts[k] * 100:.0f}% of runs (gate >= "
                         f"{FACT_SHARES[k] * 100:.0f}%) {'met' if met[k] else 'missed'}"
                         for k in FACT_SHARES)
    record = {
        "track": "market_realism",
        "status": status,
        "date": date.today().isoformat(),
        "asset": asset,
        "scope": scope,
        "evidence": evidence,
        "facts": {k: round(facts[k], 3) for k in facts},
        "gates": FACT_SHARES,
        "per_run": per_run,
        "limitations": [
            "Null model is the run's own shuffled returns, not historical "
            "resampling of real market data nor an ABIDES-class baseline.",
            "Covers EQ price/spread behaviour only; depth at best quote and "
            "small-trade execution costs need TAQ and are out of scope here.",
            "Tolerance bands are registered by this module; they are "
            "conventions, not validated market standards.",
            "A no_serial_corr miss at the mark scale reflects round-scale "
            "autocorrelation in the simulated paths (e.g. trending Tier-B "
            "policies); real daily equity returns are near-uncorrelated, so "
            "this fact is the one to watch as brains change.",
        ],
    }
    cfg_hash = hashlib.sha256(json.dumps(
        {"glob": globs, "gates": FACT_SHARES,
         "perms": PERMUTATIONS}, sort_keys=True).encode()).hexdigest()[:12]
    record["config_hash"] = cfg_hash
    registry = json.loads(RESULTS.read_text())
    dupes = [e for e in registry.get("evaluations", [])
             if e.get("track") == "market_realism"
             and e.get("config_hash") == cfg_hash]
    if dupes:
        print(f"already registered (config_hash={cfg_hash}), nothing appended")
    elif apply:
        record["registered_at"] = datetime.now().isoformat(timespec="seconds")
        registry.setdefault("evaluations", []).append(record)
        RESULTS.write_text(json.dumps(registry, indent=2) + "\n")
        print(f"registered -> {RESULTS}")
    else:
        print("dry run only; pass --apply to append to results.json")
    print(json.dumps({k: v for k, v in record.items() if k != "per_run"},
                     indent=1))
    return record


if __name__ == "__main__":
    args = sys.argv[1:]
    globs = ["runs/evidence/demo/*/*_s*", "runs/evidence/demo2/*/*_s*"]
    do_apply = "--apply" in args
    if "--runs" in args:
        globs = args[args.index("--runs") + 1].split(",")
    run(globs, apply=do_apply)

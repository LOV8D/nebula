"""Population fidelity v0 (L1): panel marginals vs published anchors.

Compares the retail panel's synthesized closed-value marginals against
official public statistics, with every anchor cited to its source
document. The panel is investors-by-construction, so the valid comparators
are SCF statistics CONDITIONAL on holding stock, not participation rates.

Anchors (SCF 2022, Federal Reserve Bulletin, October 2023 — Box 2
"Direct and Indirect Holdings of Publicly Traded Stock", Table 3):
  - conditional-on-holding median stock value: $52,000
  - heavy right skew: conditional mean $491,800 >> median
  - participation by income: 34% (bottom half) / 78% (upper-middle) /
    95% (top decile) — NOT comparable to this panel (selection), recorded
    as context only.

Pre-registered tolerances (set before this run, deliberately coarse for
an uncalibrated prior panel):
  M1 median bracket: panel median aum_band must be one of the two
     brackets containing the $52k conditional median (b10_50k, b50_250k)
  M2 right tail: gt_1m share <= 20% (skew consistency with mean >> median)
  M3 heterogeneity: at least 3 brackets each hold >= 5% of the panel

    python3 -m evaluation.population_fidelity           # dry run
    python3 -m evaluation.population_fidelity --apply
"""
import hashlib
import json
import collections
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).with_name("results.json")
ORDER = ["lt_10k", "b10_50k", "b50_250k", "b250_1m", "gt_1m"]
MEDIAN_BRACKETS_OK = ("b10_50k", "b50_250k")   # brackets containing $52k
GT_1M_MAX = 0.20
MIN_BRACKETS_5PCT = 3


def panel_aum_bands():
    from evidence.fields import synthesize
    from experiments.demo import _panel
    bands, n = collections.Counter(), 0
    for a in _panel():
        syn = synthesize(a)
        if not syn:
            continue
        v, _ = syn["aum_band"]
        bands[v] += 1
        n += 1
    return {b: bands.get(b, 0) for b in ORDER}, n


def run(apply=False):
    bands, n = panel_aum_bands()
    shares = {b: bands[b] / n for b in ORDER}
    cum, median_band = 0, None
    for b in ORDER:
        cum += bands[b]
        if median_band is None and cum >= n / 2:
            median_band = b
    gt1m = shares["gt_1m"]
    brackets_5pct = sum(1 for b in ORDER if shares[b] >= 0.05)
    m1 = median_band in MEDIAN_BRACKETS_OK
    m2 = gt1m <= GT_1M_MAX
    m3 = brackets_5pct >= MIN_BRACKETS_5PCT
    out = {
        "track": "population_fidelity", "gate": "behavior_grounding",
        "case": "L1 v0: retail panel aum_band marginals vs SCF 2022 "
                "conditional-on-holding statistics",
        "panel_n": n,
        "panel_shares": {b: round(shares[b], 4) for b in ORDER},
        "panel_median_band": median_band,
        "anchors": {
            "source": "Changes in U.S. Family Finances from 2019 to 2022 "
                      "(SCF), Federal Reserve Bulletin, October 2023 — "
                      "Box 2 / Table 3, conditional on holding stock",
            "conditional_median_usd": 52000,
            "conditional_mean_usd": 491800,
            "participation_by_income": {"bottom_half": 0.34,
                                        "upper_middle": 0.78,
                                        "top_decile": 0.95},
        },
        "tests": {
            "M1_median_bracket": {"ok": m1, "detail": f"median band "
                                  f"{median_band} in {MEDIAN_BRACKETS_OK}"},
            "M2_right_tail": {"ok": m2, "detail": f"gt_1m share "
                              f"{gt1m:.1%} <= {GT_1M_MAX:.0%}"},
            "M3_heterogeneity": {"ok": m3, "detail": f"{brackets_5pct} "
                                 f"brackets >= 5%"},
        },
        "verdict": "PASS" if (m1 and m2 and m3) else
                   "PARTIAL" if (m1 or m2 or m3) else "FAIL",
        "note": ("Prior-panel fidelity only: 0% of these attributes are "
                 "human-grounded; this eval quantifies how far the "
                 "uncalibrated priors sit from published population "
                 "moments. FINRA NFCS behavioral anchors (advisor usage, "
                 "check frequency) are pending — the report crosstabs were "
                 "not machine-fetchable this pass. Participation-rate "
                 "anchors are not comparable (panel is investors-only)."),
        "limitations": [
            "aum_band is a coarse 5-bracket synthesis of a lognormal prior; "
            "band-level comparison loses within-band information",
            "SCF median is over stock value incl. retirement accounts; the "
            "panel band proxies investable assets — definitional mismatch "
            "of roughly one bracket",
            "2 of 3 tolerances were chosen by the same agent that ran the "
            "panel generator — an independent party should own M1-M3 "
            "before this gate can reach PASS weight in external material",
        ],
    }
    cfg_hash = hashlib.sha256(json.dumps(
        {"order": ORDER, "tol": [MEDIAN_BRACKETS_OK, GT_1M_MAX,
                                 MIN_BRACKETS_5PCT]}, sort_keys=True
    ).encode()).hexdigest()[:12]
    record = dict(out, config_hash=cfg_hash)
    print(json.dumps({"verdict": out["verdict"], "tests": out["tests"],
                      "panel_shares": out["panel_shares"],
                      "median": median_band}, indent=1))
    registry = json.loads(RESULTS.read_text())
    dupes = [e for e in registry.get("evaluations", [])
             if e.get("track") == "population_fidelity"
             and e.get("config_hash") == cfg_hash]
    if dupes:
        print(f"already registered (config_hash={cfg_hash})")
    elif apply:
        record["registered_at"] = datetime.now().isoformat(timespec="seconds")
        registry.setdefault("evaluations", []).append(record)
        RESULTS.write_text(json.dumps(registry, indent=2) + "\n")
        print(f"registered -> {RESULTS}")
    else:
        print("dry run only; pass --apply")
    return record


if __name__ == "__main__":
    import sys
    run(apply="--apply" in sys.argv)

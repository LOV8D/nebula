"""Tick-pilot SIM arm: does the tick mechanism reproduce in-sim?

(SEEDS=10 powered pass; the initial 2-seed PARTIAL record is kept in the
append-only registry — VR5 needed more seeds, spread/vol reproduced at 2.)

Runs the paired scenarios `tsp_sim_constrained` ($0.005 quote grid) and
`tsp_sim_penny` ($0.0001) — same stock (EQ as the pilot-band stand-in at
$2.05), same seed, same everything — and scores the pre-registered
directions from docs/tick-size-pilot-plan.md (H1 quoted spread, H2
close-close volatility, H3 VR5 deviation: constrained >= penny) on the
SIMULATED marks. This is mechanism-replication evidence for the
`mechanism` gate — the historical replication on real FINRA/WRDS data is
a separate track and stays gated on the real pilot list.

    python3 -m evaluation.tsp_sim_arm            # dry run
    python3 -m evaluation.tsp_sim_arm --apply    # append to results.json
"""
import hashlib
import json
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).with_name("results.json")
SEEDS = 10
TICK_CONSTRAINED, TICK_PENNY = 0.005, 0.0001
# pre-registered directions, identical to the historical H1-H3
DIRECTIONS = {"quoted_spread_bps": "constrained_higher",
              "close_close_vol_bps": "constrained_higher",
              "vr5_deviation": "constrained_higher"}


def _jsonl(p, name):
    f = Path(p) / f"{name}.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def arm_metrics(run_dir):
    """Metrics on one arm's marks. Spread = median quoted (ask-bid)/mid in
    bps across rounds with a two-sided quote; vol/VR on the round-close
    series (experiments.tick_size_pilot.vr5_deviation reused verbatim)."""
    from experiments.tick_size_pilot import vr5_deviation, close_close_vol
    marks = _jsonl(run_dir, "marks")
    spreads, closes = [], []
    for m in marks:
        if m["asset"] != "EQ" or not m.get("price"):
            continue
        closes.append(m["price"])
        bb, ba = m.get("best_bid"), m.get("best_ask")
        if bb and ba and ba > bb > 0:
            spreads.append((ba - bb) / ((ba + bb) / 2) * 1e4)
    if len(closes) < 30 or not spreads:
        return None
    return {"quoted_spread_bps": round(statistics.median(spreads), 2),
            "close_close_vol_bps": round(close_close_vol(closes) * 1e4, 2),
            "vr5_deviation": round(vr5_deviation(closes), 4)}


def run(apply=False):
    from experiments.demo import _load
    from runtime.engine import run_scenario
    root = ROOT / "runs" / "evidence" / "tsp_sim"
    out = {"track": "tsp_sim_arm",
           "case": "tick-pilot mechanism, simulated (constrained $0.005 vs penny $0.0001)",
           "gate": "mechanism", "seeds": SEEDS,
           "directions": DIRECTIONS, "arms": {}}
    per_seed = {"constrained": [], "penny": []}
    for scen, arm in (("tsp_sim_constrained", "constrained"),
                      ("tsp_sim_penny", "penny")):
        sc = _load(ROOT / "scenarios" / f"{scen}.yaml")
        for i in range(SEEDS):
            sc["seed"] = sc.get("seed", 11) + i * 101
            d = root / f"{scen}_s{i}"
            run_scenario(sc, _panel(), d, quiet=True)
            m = arm_metrics(d)
            per_seed[arm].append(m)
    out["arms"] = {k: v for k, v in per_seed.items()}
    # per-seed sign agreement on each metric
    verdicts = {}
    for metric, direction in DIRECTIONS.items():
        agrees = []
        for i in range(SEEDS):
            c, p = per_seed["constrained"][i], per_seed["penny"][i]
            if not c or not p:
                agrees.append(None)
                continue
            diff = c[metric] - p[metric]
            agrees.append(diff > 0 if direction == "constrained_higher"
                          else diff < 0)
        known = [a for a in agrees if a is not None]
        verdicts[metric] = {"per_seed": agrees,
                            "all_agree": bool(known) and all(known)}
    out["verdicts"] = verdicts
    out["verdict"] = ("PASS" if all(v["all_agree"] for v in verdicts.values())
                      else "PARTIAL" if any(v["all_agree"] for v in verdicts.values())
                      else "FAIL")
    out["note"] = ("Mechanism-replication evidence on the simulated market; "
                   "NOT the historical Tick Size Pilot replication. Signs "
                   "pre-registered in docs/tick-size-pilot-plan.md before "
                   "this run; EQ stands in for a $1.00-$2.28 pilot-band "
                   "stock. Mock brain — pipeline validation.")
    out["limitations"] = [
        "single-name proxy at one price point ($2.05); the real pilot spans "
        "a size/liquidity cross-section",
        "tick effect here acts on MM quotes and limit prices only; the real "
        "pilot also changed trade-at set and rebate economics",
        "mock brain — cognition is rule-based, so this isolates the "
        "microstructure channel only",
    ]
    cfg_hash = hashlib.sha256(json.dumps(
        {"seeds": SEEDS, "ticks": [TICK_CONSTRAINED, TICK_PENNY],
         "directions": DIRECTIONS}, sort_keys=True).encode()).hexdigest()[:12]
    record = dict(out, config_hash=cfg_hash)
    print(json.dumps({"verdict": out["verdict"], "verdicts": verdicts,
                      "arms": out["arms"]}, indent=1))
    registry = json.loads(RESULTS.read_text())
    dupes = [e for e in registry.get("evaluations", [])
             if e.get("track") == "tsp_sim_arm" and e.get("config_hash") == cfg_hash]
    if dupes:
        print(f"already registered (config_hash={cfg_hash}), nothing appended")
    elif apply:
        record["registered_at"] = datetime.now().isoformat(timespec="seconds")
        registry.setdefault("evaluations", []).append(record)
        RESULTS.write_text(json.dumps(registry, indent=2) + "\n")
        print(f"registered -> {RESULTS}")
    else:
        print("dry run only; pass --apply to append to results.json")
    return record


def _panel():
    from experiments.demo import _panel
    return _panel()


if __name__ == "__main__":
    import sys
    run(apply="--apply" in sys.argv)

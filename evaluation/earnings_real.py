"""Real-brain earnings-opening A/B: mock-vs-real divergence, registered.

The Issuer & Event pack ran earnings_open_{a,b} on the mock brain first
(2026-11-01 commit 272025c). This pass re-runs the identical scenarios on
the GLM-5.3-flash brain (parity-clean gateway) and registers the
MOCK-VS-REAL divergence as the deliverable it is: where the rule-based
mock and the LLM brain agree, the mechanism is robust to cognition; where
they diverge, the divergence is the finding (mock-vs-real divergence is a
deliverable, not noise — repo red line).

Events sit at t=0 in both arms, so the parity pre-window is empty by
construction; parity is still recorded (trivially clean).

    python3 -m evaluation.earnings_real           # dry run
    python3 -m evaluation.earnings_real --apply
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).with_name("results.json")
MOCK = ROOT / "runs" / "evidence" / "earnings_demo" / "earnings_demo"
REAL = ROOT / "runs" / "evidence" / "earnings_demo_real" / "earnings_demo"
SCENS = ("earnings_open_a", "earnings_open_b")
SEEDS = 2
METRICS = ("total_ret", "excess_kurtosis", "n_halts", "ann_vol")


def _summ(root, scen, i):
    p = Path(root) / f"{scen}_s{i}" / "summary.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())
    eq = s["assets"]["EQ"]
    out = {m: eq.get(m) for m in METRICS}
    out["win90_ret"] = s.get("event_windows_avg", {}).get("EQ_win90_ret")
    out["wake"] = s.get("usage", {}).get("calls")
    return out


def run(apply=False):
    from experiments.parity import check
    arms = {}
    for brain, root in (("mock", MOCK), ("real", REAL)):
        arms[brain] = {}
        for scen in SCENS:
            per_seed = [_summ(root, scen, i) for i in range(SEEDS)]
            arms[brain][scen] = per_seed
    # parity per seed (events at t=0 => empty pre-window, trivially clean)
    parity = []
    for i in range(SEEDS):
        a = REAL / f"{SCENS[0]}_s{i}"
        b = REAL / f"{SCENS[1]}_s{i}"
        r = check(a, b)
        parity.append({"seed": i, "ok": r.get("ok"),
                       "t_intervention": r.get("t_intervention")})
    out = {
        "track": "earnings_real", "gate": "mechanism",
        "case": "earnings-opening disclosure A/B on GLM-5.3-flash vs mock "
                "(Issuer & Event pack; reassuring vs blunt wording, LULD "
                "-5%/-10% bands)",
        "model": "glm-5.3-flash", "seeds": SEEDS, "parity": parity,
        "arms": arms,
        "reading": (
            "Direction/ranking only. Ordering (blunt arm worse on disorder "
            "metrics) reproduces from mock to real and is amplified: real "
            "blunt arm shows a -5% LULD band touch in 1/2 seeds and far "
            "heavier tails; real reassuring arm recovers with strong day "
            "returns. Single-seed extremes (A s1 +47.7%) are recorded, not "
            "averaged away — 2 seeds cannot support effect-size claims."),
        "verdict": "DIVERGENCE-REPORTED",
        "limitations": [
            "2 seeds; single-name EQ proxy for the issuer's stock",
            "verdict is deliberately not PASS/FAIL: the deliverable is the "
            "recorded mock-vs-real divergence table",
            "LULD bands are a mechanism-level stand-in (halt rounds 12/30), "
            "not exchange-microsecond halts",
        ],
    }
    cfg_hash = hashlib.sha256(json.dumps(
        {"scens": SCENS, "seeds": SEEDS, "model": out["model"]},
        sort_keys=True).encode()).hexdigest()[:12]
    record = dict(out, config_hash=cfg_hash)
    print(json.dumps({"parity": parity,
                      "real": {s: arms["real"][s] for s in SCENS}}, indent=1))
    registry = json.loads(RESULTS.read_text())
    dupes = [e for e in registry.get("evaluations", [])
             if e.get("track") == "earnings_real"
             and e.get("config_hash") == cfg_hash]
    if dupes:
        print(f"already registered (config_hash={cfg_hash}), nothing appended")
    elif apply:
        record["registered_at"] = datetime.now().isoformat(timespec="seconds")
        registry.setdefault("evaluations", []).append(record)
        RESULTS.write_text(json.dumps(registry, indent=2) + "\n")
        print(f"registered -> {RESULTS}")
    else:
        print("dry run only; pass --apply to append")
    return record


if __name__ == "__main__":
    import sys
    run(apply="--apply" in sys.argv)

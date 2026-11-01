"""Turn recorded evidence into a conservative product-performance scorecard.

The benchmark contract is stable JSON. Results are append-only records. This
module derives the current assessment; it never treats an absent benchmark as
a pass and deliberately produces no aggregate score.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).with_name("benchmark_v0.json")
RESULTS = Path(__file__).with_name("results.json")


def _load(path):
    return json.loads(Path(path).read_text())


def _result_counts(records):
    counts = Counter()
    passed = Counter()
    for row in records:
        track = row.get("track")
        if not track:
            continue
        counts[track] += 1
        if row.get("status") == "pass":
            passed[track] += 1
    return counts, passed


def build_scorecard(flagship, robustness, evidence, config_path=CONFIG,
                    results_path=RESULTS):
    """Assess the current product from the exact evidence already in the UI."""
    cfg = _load(config_path)
    registry = _load(results_path)
    records = registry.get("evaluations", [])
    counts, passed = _result_counts(records)

    parity = flagship.get("parity", [])
    parity_pass = sum(p.get("ok") is True for p in parity)
    parity_fail = sum(p.get("ok") is False for p in parity)
    grounded = evidence.get("coverage", {}).get("grounded_share", 0)
    sensitivity = [r for r in robustness.get("rows", [])
                   if r.get("label") != "Flagship" and r.get("quotable")]
    sens_pairs = [s for r in sensitivity for s in r.get("seeds", [])]
    sens_clean = sum(s.get("parity") is True for s in sens_pairs)
    sens_bad = sum(s.get("parity") is False for s in sens_pairs)

    integrity_ok = (bool(parity) and parity_pass == len(parity)
                    and flagship.get("panel_current")
                    and flagship.get("manifest_complete"))
    tracks = {
        "integrity": {
            "status": "pass" if integrity_ok else "blocked",
            "evidence": (f"Current flagship: {parity_pass}/{len(parity)} same-seed A/B pairs pass "
                         f"pre-intervention parity; panel {'is' if flagship.get('panel_current') else 'is not'} current; "
                         f"required manifest fields {'are' if flagship.get('manifest_complete') else 'are not'} present."),
            "limitation": "This verifies the recorded flagship comparison, not market realism or predictive validity.",
            "next": "Keep parity at 100% for every benchmark case and fail closed on missing hashes or logs."
        },
        "mechanism": {
            "status": ("pass" if passed["mechanism"] >= 2 else
                       "partial" if counts["mechanism"] or parity else "not_run"),
            "evidence": (f"{counts['mechanism']} registered mechanism-track evaluation(s) "
                         f"({passed['mechanism']} passed all pre-registered signs): "
                         "tick-pilot sim arm (spread 10/10, vol 10/10 seeds agree; "
                         "VR5 direction NOT reproduced — recorded), earnings "
                         "mock-vs-real divergence reported; five books, intents, "
                         "fills, halts inspectable."),
            "limitation": "The batch-auction mechanism is simplified; the tick sim arm "
                          "covers one price point and a mock brain, and has not received "
                          "an independent market-microstructure validation.",
            "next": "Run the historical TSP replication on the real pilot list, then "
                    "commission an independent microstructure review."
        },
        "market_realism": {
            "status": "pass" if passed["market_realism"] else ("partial" if counts["market_realism"] else "not_run"),
            "evidence": f"{counts['market_realism']} registered descriptive-realism evaluation(s); {passed['market_realism']} passed.",
            "limitation": "Current simulated paths have not been scored against held-out spreads, depth, volume, volatility or cross-asset distributions.",
            "next": "Freeze a stylized-facts suite and compare against historical resampling and an ABIDES-class baseline."
        },
        "historical_intervention": {
            "status": "pass" if passed["historical_intervention"] >= 2 else ("partial" if counts["historical_intervention"] else "not_run"),
            "evidence": f"{counts['historical_intervention']} registered masked historical intervention(s); {passed['historical_intervention']} passed.",
            "limitation": "The current wording demo is synthetic and cannot establish recovery of real intervention effects.",
            "next": "Run the SEC Tick Size Pilot and Regulation SHO Pilot as masked, pre-registered replications."
        },
        "behavior_grounding": {
            "status": "pass" if passed["behavior_grounding"] else ("blocked" if grounded == 0 else "partial"),
            "evidence": (f"{grounded * 100:.0f}% of persona attributes are grounded in consented real-person data; "
                         f"{counts['behavior_grounding']} holdout evaluation(s) registered; "
                         f"{counts['population_fidelity']} prior-fidelity evaluation(s) registered "
                         f"({passed['population_fidelity']} passed — priors sit within tolerance of SCF 2022 "
                         "conditional moments, which is calibration context, not grounding)."),
            "limitation": "Literature priors and synthetic identity cards are not human behavioral evidence.",
            "next": "Run an authorized, matched-information human holdout with pre-registered direction and distribution metrics."
        },
        "robustness": {
            "status": "pass" if sens_pairs and sens_clean == len(sens_pairs) else ("blocked" if sens_bad else "partial"),
            "evidence": (f"Flagship covers {len(parity)} clean pair(s). Current quotable sensitivity evidence: "
                         f"{sens_clean}/{len(sens_pairs)} pair(s) pass parity"
                         + (f"; {sens_bad} fail." if sens_bad else ".")),
            "limitation": "The clean flagship uses one model, one prompt and two seeds; contaminated sensitivity pairs cannot support robustness claims.",
            "next": "Re-run a pre-registered GLM seed/prompt/parameter matrix after the gateway fix, then add eligible model baselines."
        },
        "prospective_oos": {
            "status": "pass" if passed["prospective_oos"] else ("partial" if counts["prospective_oos"] else "not_run"),
            "evidence": f"{counts['prospective_oos']} frozen prospective case(s) registered; {passed['prospective_oos']} passed.",
            "limitation": "No current report was frozen before an unknown real-world outcome.",
            "next": "Freeze one design-partner report before the outcome and adjudicate it later without retroactive edits."
        },
        "decision_utility": {
            "status": "pass" if passed["decision_utility"] else ("partial" if counts["decision_utility"] else "not_run"),
            "evidence": f"{counts['decision_utility']} customer decision-utility study/studies registered; {passed['decision_utility']} passed.",
            "limitation": "No recorded customer decision, time saving, risk change or paid renewal is attributable to the product yet.",
            "next": "Measure one paid design-partner decision against its existing analyst process."
        }
    }

    ordered = []
    for spec in cfg["tracks"]:
        row = dict(spec)
        row.update(tracks[spec["id"]])
        ordered.append(row)

    baselines = []
    for arm in cfg["comparison_arms"]:
        row = dict(arm)
        row["status"] = "candidate" if arm["id"] == "nebula" else "not_run"
        row["note"] = ("Current flagship is available, but has not been compared under the fairness contract."
                       if arm["id"] == "nebula" else "Required comparison has not been run.")
        baselines.append(row)

    cfg_hash = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()[:12]
    return {
        "schema_version": cfg["schema_version"],
        "config": str(Path(config_path).resolve().relative_to(ROOT)),
        "config_hash": cfg_hash,
        "object": cfg["object_of_evaluation"],
        "decision_rule": cfg["decision_rule"],
        "verdict": {
            "state": "ENGINEERING-VERIFIED / MARKET-UNVALIDATED" if integrity_ok else "ENGINEERING-BLOCKED",
            "summary": ("The current product is an engineering prototype with one clean internal A/B. "
                        "Product validity is not established: no historical, human, prospective or customer-utility benchmark has passed."),
            "claim_allowed": "The system can run and audit a clean recorded scenario comparison.",
            "claim_not_allowed": "The system accurately predicts real market or human responses."
        },
        "facts": {
            "flagship_parity_pass": parity_pass,
            "flagship_parity_total": len(parity),
            "flagship_parity_fail": parity_fail,
            "flagship_manifests_complete": bool(flagship.get("manifest_complete")),
            "human_grounded_share": grounded,
            "registered_external_evaluations": len(records),
            "sensitivity_clean": sens_clean,
            "sensitivity_total": len(sens_pairs)
        },
        "tracks": ordered,
        "baselines": baselines,
        "fairness_contract": cfg["fairness_contract"],
        "planned_cases": cfg["planned_cases"],
        "references": cfg["method_references"]
    }


def write_scorecard(scorecard, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2) + "\n")
    return out

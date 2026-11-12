"""Case objects (P1): selectable, comparable, honestly-separated cases.

A case is the unit the product speaks in — NOT a directory layout. The
news case and the earnings case have their own arms, sources, seeds,
evidence and missing states; switching cases must never leak one case's
numbers into the other's pages.

The earnings arms differ in GUIDANCE CONTENT and in the engine's
sentiment/impact inputs (-0.25 vs -0.60), not merely in "tone" — the
source YAML notes say "same underlying facts", but the outlook sentence
and the numeric inputs both changed. The case object states this on its
face; no page built on it may claim a wording-only effect.

    from ui.cases import CASES, get
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E = ROOT / "runs" / "evidence"

_CASES = {
    "news_wording": {
        "case_id": "news_wording",
        "title": "Fed statement wording",
        "task_kind": "regulator_communication",
        "decision_question": ("Does the wording of the same Federal Reserve "
                              "policy statement alone move the market?"),
        "arms": {
            "a": {"label": "variant A — neutral wording",
                  "headline": ("Fed statement: policy remains data-dependent; "
                               "risks roughly balanced"),
                  "sentiment": -0.2, "impact": 1.0,
                  "source_file": "scenarios/news_a.yaml"},
            "b": {"label": "variant B — alarming wording",
                  "headline": ("Fed statement: inflation risk elevated; "
                               "tightening possible"),
                  "sentiment": -0.6, "impact": 1.0,
                  "source_file": "scenarios/news_b.yaml"}},
        "t_intervention": 150,
        "input_diffs": [
            ("headline wording", "neutral framing", "alarming framing"),
            ("engine sentiment input", "-0.2", "-0.60"),
            ("everything else (population, mechanism, seeds, brain, prompt)",
             "identical", "identical"),
        ],
        "attribution_note": ("Both arms share the same underlying policy "
                             "facts; the headline text AND the engine "
                             "sentiment parameter differ. Direction/ranking "
                             "only — this is a wording+sentiment-input A/B, "
                             "not a pure-tone experiment."),
        "run_roots": {"real": E / "demo2" / "news_demo",
                      "mock": E / "demo" / "news_demo"},
        "seed_ids": [0, 1],
        "model": "glm-5.3-flash",
        "sensitivity_dir": E / "sensitivity",
        "parity_note": ("Pre-intervention parity PASSES (t=150 gives a "
                        "150-round pre-window; decisions and prices "
                        "identical before it)."),
        "limitations": [
            "2 seeds; single brain (GLM-only decision 2026-10-22)",
            "simulated market, not the real one; no real outcome exists",
            "prompt p1 flips the per-seed direction (see sensitivity)",
        ],
    },
    "earnings_disclosure": {
        "case_id": "earnings_disclosure",
        "title": "Earnings-opening disclosure",
        "task_kind": "issuer_disclosure",
        "decision_question": ("Same earnings miss, two disclosure drafts — "
                              "which opening is more disorderly for the "
                              "issuer's stock?"),
        "arms": {
            "a": {"label": "variant A — reassuring framing",
                  "headline": ("Issuer 8-K, pre-open: Q3 revenue slightly "
                               "below plan on deal-timing; management "
                               "REITERATED the full-year outlook and said "
                               "the shortfall shifts revenue into Q4"),
                  "sentiment": -0.25, "impact": 1.0,
                  "source_file": "scenarios/earnings_open_a.yaml"},
            "b": {"label": "variant B — blunt framing",
                  "headline": ("Issuer 8-K, pre-open: Q3 revenue missed "
                               "plan; full-year outlook AT RISK unless Q4 "
                               "recovers"),
                  "sentiment": -0.60, "impact": 1.0,
                  "source_file": "scenarios/earnings_open_b.yaml"}},
        "t_intervention": 0,
        "input_diffs": [
            ("guidance content", "full-year outlook REITERATED (shortfall framed as Q4 timing)",
             "full-year outlook AT RISK (recovery made a condition)"),
            ("engine sentiment input", "-0.25", "-0.60"),
            ("everything else (facts of the miss, population, mechanism, seeds)",
             "identical", "identical"),
        ],
        "attribution_note": ("These are DIFFERENT DISCLOSURE SCENARIOS, not "
                             "a tone-only A/B: the guidance sentence and the "
                             "engine sentiment parameter both changed. Any "
                             "A/B difference may come from either — the "
                             "product must not claim a 'wording effect'."),
        "run_roots": {"real": E / "earnings_demo_real" / "earnings_demo",
                      "mock": E / "earnings_demo"},
        "seed_ids": [0, 1],
        "model": "glm-5.3-flash (real arm) / mock-heuristic-v1 (mock arm)",
        "sensitivity_dir": None,   # no prompt/seed matrix exists for earnings
        "parity_note": ("Events land at t=0 (pre-open): there is NO "
                        "measurable pre-intervention window, so parity "
                        "cannot verify 'identical before the intervention' "
                        "— initialization inputs are a separate check."),
        "limitations": [
            "2 seeds; single-name EQ proxy for the issuer's stock",
            "t=0 design: pre-intervention parity unmeasurable by construction",
            "no prompt/seed sensitivity matrix has been run for this case",
            "LULD-style bands are a mechanism stand-in (12/30-round halts)",
        ],
    },
}

#: what each case consumes from the platform-level views. A view marked
#: unsupported for a case must show 'not applicable', never the other
#: case's numbers.
VIEW_SUPPORT = {
    "news_wording": {"verdict": True, "ripple": True, "robustness": True,
                     "performance": True, "evidence": True},
    "earnings_disclosure": {"verdict": True, "ripple": True,
                            "robustness": False,   # no sensitivity matrix
                            "performance": True, "evidence": True},
}


def get(case_id):
    if case_id not in _CASES:
        raise KeyError(f"unknown case {case_id!r}; known: {sorted(_CASES)}")
    src = _CASES[case_id]
    c = dict(src)
    c["run_roots"] = {k: str(v) for k, v in src["run_roots"].items()}
    c["sensitivity_dir"] = (str(src["sensitivity_dir"])
                            if src.get("sensitivity_dir") else None)
    c["views"] = VIEW_SUPPORT[case_id]
    scens = {"news_wording": ("news_a", "news_b"),
             "earnings_disclosure": ("earnings_open_a",
                                     "earnings_open_b")}[case_id]
    # availability: a missing arm/source surfaces as 'not comparable',
    # never as zero or as the other case's data
    avail = {}
    for brain, root in src["run_roots"].items():
        per_arm = {}
        for key, scen in (("a", scens[0]), ("b", scens[1])):
            per_arm[key] = {f"s{i}": (root / f"{scen}_s{i}").exists()
                            for i in (0, 1)}
        avail[brain] = per_arm
    c["available"] = avail
    return c


def all_cases():
    return [get(cid) for cid in _CASES]


CASES = sorted(_CASES)

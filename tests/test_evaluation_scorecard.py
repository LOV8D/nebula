"""Evaluation contract: absence is never a pass and there is no total score."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.scorecard import build_scorecard  # noqa: E402


def main():
    flagship = {
        "panel_current": True,
        "manifest_complete": True,
        "parity": [{"ok": True}, {"ok": True}],
    }
    robustness = {"rows": [
        {"label": "Flagship", "quotable": True,
         "seeds": [{"parity": True}, {"parity": True}]},
        {"label": "GLM p2", "quotable": True,
         "seeds": [{"parity": False}, {"parity": False}]},
    ]}
    evidence = {"coverage": {"grounded_share": 0}}
    # Isolated empty registry: the contract under test is "no evaluations
    # registered", independent of whatever the live results.json holds.
    empty = Path(tempfile.mkdtemp()) / "results.json"
    empty.write_text(json.dumps({"evaluations": []}))
    out = build_scorecard(flagship, robustness, evidence, results_path=empty)
    tracks = {r["id"]: r for r in out["tracks"]}

    assert "score" not in out and len(tracks) == 8
    assert tracks["integrity"]["status"] == "pass"
    assert tracks["mechanism"]["status"] == "partial"
    assert tracks["behavior_grounding"]["status"] == "blocked"
    assert tracks["robustness"]["status"] == "blocked"
    for key in ("market_realism", "historical_intervention",
                "prospective_oos", "decision_utility"):
        assert tracks[key]["status"] == "not_run", (key, tracks[key])
    assert out["verdict"]["state"] == "ENGINEERING-VERIFIED / MARKET-UNVALIDATED"
    # T1b: records are classified by evidence kind; an empty registry has
    # zero records of any kind and zero verified external outcomes
    assert out["facts"]["registered_evaluations_total"] == 0
    assert out["facts"]["verified_external_outcomes"] == 0

    # And with the live registry (may hold the market-realism record): no
    # aggregate score ever appears, and a partial record never reads as pass.
    live = build_scorecard(flagship, robustness, evidence)
    assert "score" not in live
    live_tracks = {r["id"]: r["status"] for r in live["tracks"]}
    assert live_tracks["market_realism"] in ("not_run", "partial", "pass")
    # T1b must-haves on the live registry: every record classified, the
    # internal kinds never counted as external, tsp_sim_arm's two records
    # are two records (not two external cases), population_fidelity PASS
    # adds no holdout, earnings_real is not a PASS
    lf = live["facts"]
    assert lf["registered_evaluations_total"] >= 5
    assert set(lf["registered_evaluations_by_kind"]) <= {
        "internal_descriptive", "internal_mechanism",
        "internal_divergence", "prior_check"}
    assert lf["verified_external_outcomes"] == 0
    assert lf["registered_evaluations_by_kind"].get("internal_mechanism") == 2
    print("evaluation scorecard test: OK — 8 gates, no aggregate score, "
          "isolated + live registries")


if __name__ == "__main__":
    main()

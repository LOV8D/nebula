"""Evaluation contract: absence is never a pass and there is no total score."""
import sys
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
    out = build_scorecard(flagship, robustness, evidence)
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
    assert out["facts"]["registered_external_evaluations"] == 0
    print("evaluation scorecard test: OK — 8 gates, no aggregate score")


if __name__ == "__main__":
    main()

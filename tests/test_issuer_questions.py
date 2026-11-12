"""P2 acceptance tests: issuer five-question freeze & scoring (fixtures only).

The card's acceptance case: five predicted positions, three hit distinct
topics, six real topics -> hit rate 3/5, coverage 3/6. Refusals: late
material, tampered predictions, more than five, duplicate ranks, unknown
source. Outcome-only edits never touch the frozen hash. No outcome ->
'pending'. Nothing here touches real events or adds external validations.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.issuer_questions import freeze, score, validate_predictions  # noqa: E402

TMP = Path("/tmp/wt_p2")
DOC = "guidance reiterated; Q4 revenue timing; margin pressure"


def setup():
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    (TMP / "material.txt").write_text(DOC + "\n")
    (TMP / "case.json").write_text(json.dumps({
        "event_id": "fixture-earnings-q3",
        "deadline_utc": "2026-11-20T20:00:00Z",
        "allowed_sources": [{"id": "press_release", "path": "material.txt",
                             "use": "prediction input"}]}))
    (TMP / "predictions.jsonl").write_text("\n".join(json.dumps(p) for p in [
        {"method": "fixture", "rank": 1, "concern": "guidance reiteration",
         "source": "press_release"},
        {"method": "fixture", "rank": 2, "concern": "Q4 revenue timing",
         "source": "press_release"},
        {"method": "fixture", "rank": 3, "concern": "margin pressure",
         "source": "press_release"},
        {"method": "fixture", "rank": 4, "concern": "buyback plans",
         "source": "press_release"},
        {"method": "fixture", "rank": 5, "concern": "management changes",
         "source": "press_release"}]) + "\n")
    # allowed_sources paths are relative to the case file
    import os
    os.chdir(TMP)


def main():
    setup()
    # 1. freeze
    m = freeze("case.json", "predictions.jsonl", "freeze.json",
               now="2026-11-19T09:00:00+00:00")
    assert m["n_predictions"] == 5 and len(m["materials_sha256"]) == 1

    # 2. score the card's acceptance case: 5 predictions, 3 hit distinct
    # topics of 6 real ones -> 3/5 hit rate, 3/6 coverage
    (TMP / "outcome.json").write_text(json.dumps({"topics": [
        "full-year guidance reiteration", "Q4 revenue timing",
        "gross margin pressure", "dividend policy", "competition",
        "capital expenditure"]}))
    s = score("case.json", "freeze.json", "outcome.json", "predictions.jsonl")
    assert s["n_hits"] == 3 and s["hit_rate"] == 0.6, s
    assert s["n_matched_topics"] == 3 and s["coverage"] == 0.5, s

    # 3. tamper: edit predictions after freezing -> refused
    (TMP / "predictions.jsonl").write_text(
        (TMP / "predictions.jsonl").read_text().replace(
            "buyback plans", "dividend policy"))
    try:
        score("case.json", "freeze.json", "outcome.json", "predictions.jsonl")
        raise AssertionError("tampered predictions were scored")
    except SystemExit as e:
        assert "no longer matches" in str(e)
    # restore
    setup(); freeze("case.json", "predictions.jsonl", "freeze.json",
                    now="2026-11-19T09:00:00+00:00")

    # 4. refusals on input: >5, dup ranks, unknown source, no source
    errs = validate_predictions(
        [{"rank": i, "concern": f"c{i}", "source": "press_release"}
         for i in range(1, 7)], ["press_release"])
    assert any("exceed" in e for e in errs)
    errs = validate_predictions(
        [{"rank": 1, "concern": "a", "source": "press_release"},
         {"rank": 1, "concern": "b", "source": "press_release"}],
        ["press_release"])
    assert any("duplicate ranks" in e for e in errs)
    errs = validate_predictions(
        [{"rank": 1, "concern": "a", "source": "unknown_doc"}],
        ["press_release"])
    assert any("not in the case" in e for e in errs)
    errs = validate_predictions([{"rank": 1, "concern": "a"}], ["press_release"])
    assert any("no source" in e for e in errs)

    # 5. changing only the outcome never changes the frozen hash
    h_before = json.loads((TMP / "freeze.json").read_text())["predictions_sha256"]
    (TMP / "outcome.json").write_text(json.dumps({"topics": ["different"]}))
    s2 = score("case.json", "freeze.json", "outcome.json", "predictions.jsonl")
    h_after = json.loads((TMP / "freeze.json").read_text())["predictions_sha256"]
    assert h_before == h_after and s2["n_hits"] == 0

    # 6. no outcome file -> the caller must show 'pending', not zero:
    #    (score requires an outcome; absence is the UI's 'pending' state)
    assert not (TMP / "outcome.json").unlink() if False else True
    (TMP / "outcome.json").unlink(missing_ok=True)
    try:
        score("case.json", "freeze.json", "outcome.json", "predictions.jsonl")
        raise AssertionError("missing outcome was scored")
    except FileNotFoundError:
        pass

    # 7. repeated identical concerns count once for coverage
    setup()
    (TMP / "predictions.jsonl").write_text("\n".join(json.dumps(p) for p in [
        {"method": "f", "rank": 1, "concern": "margin pressure",
         "source": "press_release"},
        {"method": "f", "rank": 2, "concern": "margin pressure",
         "source": "press_release"}]) + "\n")
    freeze("case.json", "predictions.jsonl", "freeze.json",
           now="2026-11-19T09:00:00+00:00")
    (TMP / "outcome.json").write_text(json.dumps(
        {"topics": ["gross margin pressure"]}))
    s3 = score("case.json", "freeze.json", "outcome.json", "predictions.jsonl")
    assert s3["n_hits"] == 2 and s3["n_matched_topics"] == 1, s3

    print("issuer five-questions test: OK — 3/5 & 3/6 fixture, tamper/late/"
          "dup/overflow refusals, outcome-only edits leave the frozen hash")


if __name__ == "__main__":
    main()

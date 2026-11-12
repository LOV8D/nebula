"""A/B parity check test (run: python3 tests/test_parity.py).

Builds three tiny synthetic run pairs and checks the verdicts: identical
before the intervention -> pass; one decision differs at t=3 -> fail with
the round named; bulk logs missing -> unknown, never pass.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.parity import check, check_experiment  # noqa: E402


def _write(d, events, intents, marks):
    d.mkdir(parents=True)
    for name, rows in (("events", events), ("intents", intents), ("marks", marks)):
        (d / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def _pair(root, tamper=None):
    marks = [{"t": t, "asset": "EQ", "price": 100 + t} for t in range(10)]
    intents = [{"t": t, "agent_id": f"hf_pm-{t:04d}", "asset": "EQ", "side": 1,
                "size_frac": 0.1, "urgency": 0.5} for t in range(10)]
    ev = lambda h: [{"t": 5, "headline": h, "sentiment": 0.0}]  # noqa: E731
    _write(root / "news_a_s0", ev("calm"), intents, marks)
    if tamper:
        intents, marks = tamper(intents, marks)
    _write(root / "news_b_s0", ev("alarm"), intents, marks)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _pair(tmp / "clean")
        r = check_experiment(tmp / "clean")[0]
        assert r["ok"] is True and r["t_intervention"] == 5, r

        def late(intents, marks):   # differs only AFTER the intervention: still clean
            intents = [dict(i, side=-1) if i["t"] >= 5 else i for i in intents]
            return intents, marks
        _pair(tmp / "late", late)
        assert check_experiment(tmp / "late")[0]["ok"] is True

        def early(intents, marks):  # one decision and one price differ at t=3
            intents = [dict(i, size_frac=0.2) if i["t"] == 3 else i for i in intents]
            marks = [dict(m, price=m["price"] * 1.01) if m["t"] >= 4 else m for m in marks]
            return intents, marks
        _pair(tmp / "early", early)
        r = check_experiment(tmp / "early")[0]
        assert r["ok"] is False, r
        assert r["first_intent_diff_t"] == 3 and r["first_price_diff_t"] == 4, r
        assert abs(r["max_pre_gap"]["EQ"] - (1 - 1 / 1.01)) < 1e-6, r   # |A/B - 1|

        (tmp / "early" / "news_b_s0" / "intents.jsonl").unlink()
        r = check(tmp / "early" / "news_a_s0", tmp / "early" / "news_b_s0")
        assert r["ok"] is None, r
    print("parity test: OK — clean pass, post-intervention change ignored, "
          "pre-intervention change caught at the right round, missing logs = unknown")


if __name__ == "__main__":
    main()


# --- T2: interventions that parity cannot verify must not read as PASS ---

def test_t2_semantics(tmp="/tmp/wt_parity_t2"):
    """impact-only event difference IS an intervention; t=0 arms have no
    measurable pre-window and must report UNKNOWN, never PASS."""
    import json, shutil, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from experiments.parity import check, describe, intervention_t

    # impact-only difference
    ea = [{"t": 0, "headline": "h", "sentiment": -0.2, "impact": 1.0,
           "assets": ["EQ"], "source": "s"}]
    eb = [dict(ea[0], impact=0.5)]
    assert intervention_t(ea, eb) == 0
    # asset-set difference
    assert intervention_t(ea, [dict(ea[0], assets=["EQ", "IR"])]) == 0
    # identical -> not an A/B
    assert intervention_t(ea, [dict(ea[0])]) is None

    # t=0 arms: no pre-window, ok must be None with a distinct reason
    root = Path(tmp)
    if root.exists():
        shutil.rmtree(root)
    for arm, ev in (("x_a_s0", ea), ("x_b_s0", eb)):
        d = root / arm
        d.mkdir(parents=True)
        (d / "events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in ev) + "\n")
        (d / "intents.jsonl").write_text("")
        (d / "marks.jsonl").write_text(
            json.dumps({"t": 0, "asset": "EQ", "price": 100.0}) + "\n")
    r = check(root / "x_a_s0", root / "x_b_s0")
    assert r["ok"] is None and "no measurable pre-window" in r["reason"], r
    line = describe(r)
    assert "UNKNOWN" in line and "PASS" not in line, line
    print("parity t=0 / impact-only test: OK — unmeasurable never reads as PASS")

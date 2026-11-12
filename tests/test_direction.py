"""T1a regression tests: shared direction semantics + gate mapping.

Covers the counter-example fixtures the card demands: all-positive,
all-negative, mixed, containing zero, empty, missing arm, and the gate
translation for no-matrix / polluted / comparable-but-mixed cases. The
2026-11-01 GLM sensitivity fixture (p1 [-0.1171, +0.2266] -> mixed;
p2 [-0.0458, -0.1085] -> negative) must classify identically here, in the
sensitivity report and in the scorecard.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.direction import pair_direction, gate_status  # noqa: E402


def main():
    # classification fixtures
    assert pair_direction([0.05, 0.12]) == "positive"
    assert pair_direction([-0.05, -0.12]) == "negative"
    assert pair_direction([-0.1171, +0.2266]) == "mixed"   # p1 fixture
    assert pair_direction([-0.0458, -0.1085]) == "negative"  # p2 fixture
    assert pair_direction([0.0, 0.0]) == "tie"
    assert pair_direction([0.0, 0.05]) == "mixed"           # zero is not positive
    assert pair_direction([]) == "insufficient"
    assert pair_direction([None, 0.05]) == "positive"       # None dropped
    assert pair_direction([None, None]) == "insufficient"   # missing arms

    # gate translation
    assert gate_status([], 0, 0) == "not_run"               # no matrix
    assert gate_status(["positive"], 1, 2) == "blocked"     # planned pair missing
    assert gate_status(["positive", "positive"], 2, 2) == "pass"
    assert gate_status(["mixed", "negative"], 2, 2) == "partial"
    assert gate_status(["negative", "negative"], 2, 2) == "pass"
    assert gate_status(["positive"], 1, 1) == "partial"     # single pair: never pass

    # the 2026-11-01 GLM matrix as a whole: p1 mixed + p2 negative
    assert gate_status(["mixed", "negative"], 2, 2) == "partial"

    print("direction semantics test: OK — classification + gate fixtures all match")


if __name__ == "__main__":
    main()

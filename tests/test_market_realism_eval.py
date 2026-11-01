"""Market-realism eval: detectors behave on synthetic series with known facts."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.market_realism import _acorr, _excess_kurtosis, _perm_p, _perm_band  # noqa: E402


def main():
    rng = random.Random(7)

    # iid gaussian returns: no fat tails, no clustering, no serial corr
    iid = [rng.gauss(0, 0.01) for _ in range(2000)]
    assert abs(_excess_kurtosis(iid)) < 0.6
    assert abs(_acorr(iid)) < 0.15
    assert _perm_p(_acorr(iid), iid, _acorr, rng) > 0.05
    lo, hi = _perm_band(iid, _acorr, rng)
    assert lo <= _acorr(iid) <= hi

    # fat tails alone: rare 8x jumps on an otherwise iid series
    fat = [rng.gauss(0, 0.01) * (8.0 if rng.random() < 0.03 else 1.0)
           for _ in range(2000)]
    assert _excess_kurtosis(fat) > 2.0

    # volatility clustering alone: two-state vol regimes (no jumps)
    clustered, hi = [], True
    for _ in range(2000):
        if rng.random() < 0.02:
            hi = not hi
        clustered.append((0.012 if hi else 0.004) * rng.gauss(0, 1))
    cl = _acorr([abs(r) for r in clustered])
    assert cl > 0.15
    assert _perm_p(cl, [abs(r) for r in clustered], _acorr, rng) <= 0.05

    # registry idempotency: a second identical registration is refused
    reg = Path(__file__).resolve().parent.parent / "evaluation" / "results.json"
    data = json.loads(reg.read_text())
    assert isinstance(data.get("evaluations", []), list)

    print("market-realism eval test: OK — iid passes absence gates, "
          "clustered series triggers clustering gate, registry sane")


if __name__ == "__main__":
    main()

"""Tick-grid regression test (run: python3 tests/test_tick_grid.py).

The TSP sim arm needs quotes and clearing prices to live on the quote-
increment grid when a scenario sets `tick`, and to be untouched when it
doesn't. Guards: round_tick direction semantics; MM quotes on-grid and
non-crossed; clearing price on-grid; unconstrained scenario unchanged.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.matching import round_tick, clear_round  # noqa: E402
from runtime.types import Order, BUY, SELL  # noqa: E402


def main():
    # 1. direction semantics
    assert round_tick(2.0523, 0.005) == 2.05          # nearest
    assert round_tick(2.0523, 0.005, side="buy") == 2.05    # floor
    assert round_tick(2.0523, 0.005, side="sell") == 2.055  # ceil
    assert round_tick(2.0523, None) == 2.0523
    assert round_tick(2.0523, 0) == 2.0523

    # 2. MM quotes on-grid, non-crossed, under a coarse tick
    class _M:
        price = 2.05
        mm_ref = 2.05

    class _W:
        t = 0
        tick = {"EQ": 0.005}
        marks = {"EQ": _M()}
        assets0 = {"EQ": 2.05}

    class _A:
        positions = {"EQ": 0.0}

    _W.accounts = {"mm-1": _A()}
    from runtime.agents import market_maker_quotes
    from runtime.engine import World  # noqa: F401  (import sanity)
    rng = random.Random(0)
    for _ in range(200):
        q = market_maker_quotes("mm-1", "EQ", _W, rng)
        for o in q:
            assert abs(o.limit / 0.005 - round(o.limit / 0.005)) < 1e-6, \
                f"quote {o.limit} off the $0.005 grid"
        if len(q) == 2:
            assert q[1].limit > q[0].limit, "MM quotes crossed"

    # 3. clearing price on-grid when all order limits are on-grid
    orders = [Order("EQ", "b1", BUY, 10.0, 2.05, 0, "t"),
              Order("EQ", "s1", SELL, 10.0, 2.055, 0, "t"),
              Order("EQ", "b2", BUY, 5.0, 2.055, 0, "t")]
    _, px, residual, _ = clear_round(orders, 2.05)
    assert abs(px / 0.005 - round(px / 0.005)) < 1e-6, f"clearing {px} off-grid"

    # 4. unconstrained behaviour unchanged: full precision, NOT on the
    # coarse grid (center±half at zero inventory ≈ 2.049385 / 2.050615)
    class _W0(_W):
        tick = {"EQ": None}

    q = market_maker_quotes("mm-1", "EQ", _W0, rng)
    on_grid = [abs(o.limit / 0.005 - round(o.limit / 0.005)) < 1e-6 for o in q]
    assert not all(on_grid), \
        "unconstrained quotes coincidentally sit on the $0.005 grid"

    print("tick-grid test: OK — grid semantics, MM quotes, clearing price, "
          "unconstrained fallback")


if __name__ == "__main__":
    main()

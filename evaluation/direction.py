"""Shared A/B direction semantics (T1a).

One pure function decides what a set of per-seed separations (A − B)
means, so the sensitivity report, the dashboard robustness view and the
scorecard can never disagree about the same numbers.

Rules (pre-registered 2026-11-12, plan card T1a):
  - empty / any None separation        -> "insufficient"
  - every separation > 0               -> "positive"   (A better, per seed)
  - every separation < 0               -> "negative"
  - all exactly 0                      -> "tie"
  - both signs present (incl. zeros)   -> "mixed"
Zero is NOT positive. A two-seed mean of +5pp with seeds [-11.7, +22.7]
is MIXED, and no consumer may display it as support for either direction.

The gate translation (scorecard semantics, eight gates unchanged):
  no matrix                     -> not_run
  planned pairs polluted/absent -> blocked (with n/denominator)
  comparable but mixed / too
  few seeds or arms             -> partial
  comparable, same direction    -> pass (this stage never upgrades a
                                    single-model two-seed matrix to pass)
"""
from typing import Optional, Sequence


def pair_direction(seps: Sequence[Optional[float]]) -> str:
    """Classify per-seed A−B separations. None marks a missing arm/log."""
    known = [s for s in seps if s is not None]
    if not known:
        return "insufficient"
    if all(s > 0 for s in known):
        return "positive"
    if all(s < 0 for s in known):
        return "negative"
    if all(s == 0 for s in known):
        return "tie"
    return "mixed"


def gate_status(directions: Sequence[str], comparable: int, planned: int,
                min_pairs: int = 2) -> str:
    """Map per-pair directions onto the robustness gate.

    comparable/planned count pairs with usable, parity-clean logs out of
    the pairs the matrix planned (missing arm, unknown parity or heavy
    error fallback make a pair incomparable)."""
    if planned == 0:
        return "not_run"
    if comparable < planned:
        return "blocked"
    known = [d for d in directions if d not in ("insufficient",)]
    if not known:
        return "blocked"
    if len(known) < min_pairs:
        return "partial"
    if all(d == "positive" for d in known) or all(d == "negative" for d in known):
        return "pass" if len(known) >= min_pairs else "partial"
    return "partial"

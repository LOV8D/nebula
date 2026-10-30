"""Pre-intervention parity: are two arms of an A/B really identical until the
intervention?

An A/B is only an A/B if "everything else identical" holds. Two arms that share
a seed must make the same decisions and print the same prices in every round
before the arms' event streams first differ; any gap there is not caused by
the intervention and contaminates the comparison. This check makes the claim
testable instead of asserted.

    python3 -m runtime.cli parity runs/evidence/demo2/news_demo

A pair passes when every pre-intervention intent (agent, asset, side, size,
urgency) and every pre-intervention mark matches. A failing pair is not
deleted or hidden — reports and the dashboard show it, flagged.
"""
import json
from pathlib import Path

_TOL = 1e-9


def _jsonl(run_dir, name):
    p = Path(run_dir) / f"{name}.jsonl"
    if not p.exists():
        return None
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def intervention_t(events_a, events_b):
    """First round at which the two arms' published events differ."""
    key = lambda e: (e["t"], e.get("headline"), e.get("sentiment"))  # noqa: E731
    ka, kb = sorted(map(key, events_a)), sorted(map(key, events_b))
    for x, y in zip(ka, kb):
        if x != y:
            return min(x[0], y[0])
    if len(ka) != len(kb):
        longer = ka if len(ka) > len(kb) else kb
        return longer[min(len(ka), len(kb))][0]
    return None


def _intent_key(it):
    return (it["t"], it["agent_id"], it.get("asset"), it.get("side"),
            round(it.get("size_frac", 0.0), 9), round(it.get("urgency", 0.0), 9))


def check(a_dir, b_dir):
    """-> dict with the verdict and where the arms first part ways.

    `ok` is None when the bulk logs are missing (they are gitignored and
    rebuilt by re-running), so "unknown" is never reported as "pass".
    """
    logs = {}
    for arm, d in (("a", a_dir), ("b", b_dir)):
        for name in ("events", "intents", "marks"):
            logs[arm, name] = _jsonl(d, name)
    out = {"a": Path(a_dir).name, "b": Path(b_dir).name}
    if any(v is None for v in logs.values()):
        return dict(out, ok=None, reason="bulk logs missing — re-run to check")
    t0 = intervention_t(logs["a", "events"], logs["b", "events"])
    out["t_intervention"] = t0
    if t0 is None:
        return dict(out, ok=None, reason="arms publish identical events — not an A/B")

    ia = sorted(_intent_key(i) for i in logs["a", "intents"] if i["t"] < t0)
    ib = sorted(_intent_key(i) for i in logs["b", "intents"] if i["t"] < t0)
    first_intent = None
    for x, y in zip(ia, ib):
        if x != y:
            first_intent = min(x[0], y[0])
            break
    if first_intent is None and len(ia) != len(ib):
        longer = ia if len(ia) > len(ib) else ib
        first_intent = longer[min(len(ia), len(ib))][0]

    pa = {(m["t"], m["asset"]): m["price"] for m in logs["a", "marks"] if m["t"] < t0}
    pb = {(m["t"], m["asset"]): m["price"] for m in logs["b", "marks"] if m["t"] < t0}
    first_price, gap = None, {}
    for k in sorted(pa.keys() | pb.keys()):
        x, y = pa.get(k), pb.get(k)
        if x is None or y is None:
            first_price = k[0] if first_price is None else min(first_price, k[0])
            continue
        g = abs(x / y - 1) if y else 0.0
        gap[k[1]] = max(gap.get(k[1], 0.0), g)
        if g > _TOL and (first_price is None or k[0] < first_price):
            first_price = k[0]
    ok = first_intent is None and first_price is None
    return dict(out, ok=ok, n_pre_intents=[len(ia), len(ib)],
                first_intent_diff_t=first_intent, first_price_diff_t=first_price,
                max_pre_gap={a: round(g, 6) for a, g in sorted(gap.items())})


def pairs(exp_dir, a="news_a", b="news_b"):
    """Same-seed pairs in an experiment dir: news_a_s0 <-> news_b_s0, ..."""
    exp_dir = Path(exp_dir)
    out = []
    for da in sorted(exp_dir.glob(f"{a}_s*")):
        db = exp_dir / da.name.replace(a, b, 1)
        if db.exists():
            out.append((da, db))
    return out


def check_experiment(exp_dir, a="news_a", b="news_b"):
    return [check(da, db) for da, db in pairs(exp_dir, a, b)]


def describe(r):
    """One line for terminals and reports."""
    name = f"{r['a']} vs {r['b']}"
    if r["ok"] is None:
        return f"{name}: UNKNOWN — {r['reason']}"
    if r["ok"]:
        return (f"{name}: PASS — identical before t={r['t_intervention']} "
                f"({r['n_pre_intents'][0]} decisions)")
    worst = max(r["max_pre_gap"].items(), key=lambda kv: kv[1], default=("-", 0))
    return (f"{name}: FAIL — decisions differ from t={r['first_intent_diff_t']}, "
            f"prices from t={r['first_price_diff_t']} "
            f"(max pre-intervention gap {worst[1]:.2%} on {worst[0]}); "
            f"intervention at t={r['t_intervention']}")

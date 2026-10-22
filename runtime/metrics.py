"""Market-level metrics + cross-scenario comparison.

Per asset: return, annualized vol, excess kurtosis, vol clustering
(lag-1 autocorr of |r|), volume-|r| corr, max drawdown, avg spread (bps),
halt count. Cross-sectional: wake dispersion (std of signed intent sizes
per round — the disagreement proxy for the policy-communication wind
tunnel), net flow by class, flow HHI.

BP red line: these describe pipeline behavior. Reproducing stylized facts
is a smoke test, never validity evidence.
"""
import json
import math
from pathlib import Path
from .types import ASSETS


def _read(run_dir, name):
    p = Path(run_dir) / f"{name}.jsonl"
    out = []
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def _acorr(x):
    if len(x) < 3:
        return 0.0
    mu = sum(x) / len(x)
    num = sum((x[i] - mu) * (x[i + 1] - mu) for i in range(len(x) - 1))
    den = sum((v - mu) ** 2 for v in x)
    return num / den if den > 0 else 0.0


def _corr(a, b):
    n = min(len(a), len(b))
    if n < 3:
        return 0.0
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = math.sqrt(sum((v - ma) ** 2 for v in a))
    db = math.sqrt(sum((v - mb) ** 2 for v in b))
    return num / (da * db) if da * db > 0 else 0.0


def _kurtosis(rs):
    n = len(rs)
    if n < 10:
        return 0.0
    mu = sum(rs) / n
    m2 = sum((r - mu) ** 2 for r in rs) / n
    m4 = sum((r - mu) ** 4 for r in rs) / n
    return m4 / m2 ** 2 - 3 if m2 > 0 else 0.0


EVENT_WINDOW = 30    # immediate reaction window
EVENT_WINDOW_LONG = 90  # reaction + recovery window — wording A/B separates here


def _event_windows(marks, events, intents, window=EVENT_WINDOW):
    """Per-event impact: return/vol/dispersion in [t_e, t_e+EVENT_WINDOW].
    The wind-tunnel comparison unit — isolates the treatment from
    day-scale aftermath noise."""
    out = []
    by_at = {}
    for m in marks:
        by_at.setdefault(m["asset"], []).append(m)
    for a in by_at:
        by_at[a].sort(key=lambda m: m["t"])
    win_intents = {}
    for d in intents:
        for k in range(0, window + 1):
            win_intents.setdefault(d.get("t", 0) - k, []).append(d)
    for e in events:
        row = {"t": e["t"], "headline": e["headline"][:60]}
        for a, rows in by_at.items():
            if a not in [x.upper() for x in e.get("assets", [])]:
                continue
            w = [m for m in rows if e["t"] <= m["t"] <= e["t"] + window and m["price"]]
            if len(w) > 2:
                prices = [m["price"] for m in w]
                ret = prices[-1] / prices[0] - 1 if prices[0] else 0.0
                rets = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices)) if prices[i - 1]]
                vol = (sum(r * r for r in rets) / max(1, len(rets))) ** 0.5
                row[f"{a}_win_ret"] = ret
                row[f"{a}_win_vol"] = vol
        seen = win_intents.get(e["t"], [])
        for k in range(1, window + 1):
            seen += win_intents.get(e["t"] + k, [])
        sides = [d["side"] * d.get("size_frac", 0) for d in seen if d.get("side")]
        if len(sides) > 1:
            mu = sum(sides) / len(sides)
            row["win_dispersion"] = (sum((v - mu) ** 2 for v in sides) / len(sides)) ** 0.5
            row["win_intents"] = len(sides)
        out.append(row)
    return out


def _mean_local(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarize(rec, world, scenario, elapsed, wake_log):
    marks = _read(rec.dir, "marks")
    intents = _read(rec.dir, "intents")
    events = _read(rec.dir, "events")
    out = {"run_id": rec.dir.name, "scenario": scenario["id"],
           "elapsed_s": round(elapsed, 2), "assets": {}, "cross": {}, "usage": {}}
    rounds_per_day = scenario["rounds_per_day"]
    for a in ASSETS:
        rows = [m for m in marks if m["asset"] == a]
        prices = [r["price"] for r in rows]
        rets = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices)) if prices[i - 1] > 0]
        abs_r = [abs(r) for r in rets]
        vols = [r["volume"] for r in rows]
        peak, dd, cur = prices[0] if prices else 0, 0.0, prices[0] if prices else 0
        for p in prices:
            cur = max(cur, p)
            dd = min(dd, p / cur - 1 if cur else 0.0)
        spreads = [2 * (r["best_ask"] - r["best_bid"]) / (r["best_ask"] + r["best_bid"]) * 1e4
                   for r in rows if r.get("best_ask") and r.get("best_bid")
                   and r["best_ask"] > r["best_bid"]]
        n_rpd = max(1, rounds_per_day)
        # per-day closes -> daily returns (multi-day runs)
        closes = []
        for d in range(1 + (len(rows) - 1) // n_rpd):
            day_rows = [m for m in rows if d * n_rpd <= m["t"] < (d + 1) * n_rpd and m["price"]]
            if day_rows:
                closes.append(day_rows[-1]["price"])
        daily_rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))
                      if closes[i - 1]]
        out["assets"][a] = {
            "daily_returns": daily_rets,
            "total_ret": prices[-1] / prices[0] - 1 if len(prices) > 1 and prices[0] else 0.0,
            "ann_vol": (sum(r * r for r in rets) / max(1, len(rets))) ** 0.5 * math.sqrt(25 * n_rpd),
            "excess_kurtosis": _kurtosis(rets),
            "vol_clustering_lag1": _acorr(abs_r),
            "vol_absret_corr": _corr(vols[1:], abs_r),
            "max_drawdown": dd,
            "avg_spread_bps": sum(spreads) / len(spreads) if spreads else None,
            "total_volume": sum(vols),
            "n_halts": len(scenario.get("_halts", [])) if a == "EQ" else 0,
        }
    # cross-sectional disagreement per round (std of signed sizes among woken)
    by_round = {}
    for d in intents:
        if d.get("side"):
            by_round.setdefault(d.get("t", 0), []).append(
                d["side"] * d.get("size_frac", 0))
    disp = [math.sqrt(sum((v - sum(vs) / len(vs)) ** 2 for v in vs) / len(vs))
            for vs in by_round.values() if len(vs) > 1]
    # net signed notional by class (flow concentration)
    flow_by_class, tot = {}, 0.0
    for d in intents:
        if not d.get("side"):
            continue
        # persona_id is "<class>-<n>"; the two retail classes stay one bucket
        # so flow lines remain comparable with runs made before ids were
        # disambiguated.
        c = d["agent_id"].rsplit("-", 1)[0]
        if c.startswith("retail"):
            c = "retail"
        px = next((m["price"] for m in reversed(marks)
                   if m["asset"] == d["asset"] and m["price"]), 1)
        approx = d["size_frac"] * 1e5 * px     # size_frac x notional proxy
        flow_by_class[c] = flow_by_class.get(c, 0.0) + d["side"] * approx
        tot += abs(approx)
    hhi = sum((v / tot) ** 2 for v in flow_by_class.values()) if tot > 0 else 0.0
    out["cross"] = {
        "dispersion_mean": sum(disp) / len(disp) if disp else 0.0,
        "intents_n": len(intents),
        "wake_mean_per_round": sum(wake_log) / max(1, len(wake_log)),
        "flow_hhi": hhi,
        "net_flow_by_class": {k: round(v, 0) for k, v in
                              sorted(flow_by_class.items(), key=lambda kv: -abs(kv[1]))[:8]},
    }
    out["event_windows"] = _event_windows(marks, events, intents, EVENT_WINDOW)
    out["event_windows_long"] = _event_windows(marks, events, intents, EVENT_WINDOW_LONG)
    # compact aggregates for the cross-scenario table
    def _avg(ew, k):
        v = [w[k] for w in ew if k in w]
        return sum(v) / len(v) if v else None
    ew, ewl = out["event_windows"], out["event_windows_long"]
    out["event_windows_avg"] = {
        "EQ_win_ret": _avg(ew, "EQ_win_ret"), "EQ_win_vol": _avg(ew, "EQ_win_vol"),
        "IR_win_ret": _avg(ew, "IR_win_ret"), "CRYPTO_win_vol": _avg(ew, "CRYPTO_win_vol"),
        "win_dispersion": _avg(ew, "win_dispersion"), "win_intents": _avg(ew, "win_intents"),
        "EQ_win90_ret": _avg(ewl, "EQ_win_ret"), "EQ_win90_vol": _avg(ewl, "EQ_win_vol"),
        "IR_win90_ret": _avg(ewl, "IR_win_ret")}
    # behavioral drift: day-by-day activity profile. Long-horizon identity
    # check (BP layer 2): wake rates and class flow direction should not
    # trend monotonically away from day 1 beyond seed noise.
    days_n = 1 + (len(marks) // max(1, rounds_per_day * len(
        next(iter(set(m["asset"] for m in marks)), "EQ"))) ) if marks else 1
    by_day = {}
    for d_i in intents:
        dd = d_i.get("t", 0) // max(1, rounds_per_day)
        by_day.setdefault(dd, []).append(d_i)
    drift = []
    for dd in sorted(by_day):
        rows_d = by_day[dd]
        act = [r for r in rows_d if r.get("side")]
        drift.append({
            "day": dd, "intents": len(rows_d), "active": len(act),
            "pass_rate": 1 - len(act) / max(1, len(rows_d)),
            "net_dir": (sum(r["side"] for r in act) / max(1, len(act))),
            "mean_size": _mean_local([r.get("size_frac", 0) for r in act]),
        })
    out["drift"] = drift
    out["usage"] = dict(world.gateway.usage)
    out["manifest"] = rec.manifest["five_tuple"]
    return out


# ----------------------------------------------------------------------
def compare(run_dirs, out_md):
    """Relative-difference table across scenario groups. Direction and
    ranking only — no effect-size claims (BP external commitment)."""
    import glob as _glob
    expanded = []
    for pat in run_dirs:
        hits = sorted(_glob.glob(pat))
        expanded += hits if hits else [pat]
    run_dirs = [d for d in expanded if (Path(d) / "summary.json").exists()]
    groups = {}
    for d in sorted(run_dirs):
        s = json.loads((Path(d) / "summary.json").read_text())
        groups.setdefault(s["scenario"], []).append(s)
    keys = [("assets.EQ", "total_ret"), ("assets.EQ", "ann_vol"),
            ("assets.EQ", "max_drawdown"), ("assets.EQ", "excess_kurtosis"),
            ("assets.EQ", "avg_spread_bps"), ("assets.EQ", "total_volume"),
            ("assets.IR", "total_ret"), ("assets.CRYPTO", "ann_vol"),
            ("cross", "dispersion_mean"), ("cross", "wake_mean_per_round"),
            ("cross", "flow_hhi"), ("usage", "calls"),
            ("event_windows_avg", "EQ_win_ret"), ("event_windows_avg", "EQ_win_vol"),
            ("event_windows_avg", "EQ_win90_ret"), ("event_windows_avg", "IR_win90_ret"),
            ("event_windows_avg", "win_dispersion")]
    def fmt(v):
        if v is None:
            return "—"
        return f"{v:.4g}" if abs(v) < 10 else f"{v:.3g}"

    lines = ["# Wind Tunnel — cross-scenario relative differences",
             "", "Direction and ranking only; no effect sizes. "
             "Model provenance per run in `manifest.json`.", ""]
    header = "| metric | " + " | ".join(groups) + " |"
    lines += [header, "|" + "---|" * (len(groups) + 1)]
    def _dig(s, path):
        cur = s
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    for g, k in keys:
        row = [f"{g}.{k}"]
        for name in groups:
            vals = [v for v in (_dig(s, g) and _dig(s, g).get(k) for s in groups[name])
                    if v is not None]
            if not vals:
                row.append("—")
            else:
                mu = sum(vals) / len(vals)
                sd = (sum((v - mu) ** 2 for v in vals) / max(1, len(vals) - 1)) ** 0.5 if len(vals) > 1 else 0.0
                row.append(f"{fmt(mu)} ±{fmt(sd)} (n={len(vals)})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    for name, ss in groups.items():
        h = ss[0].get("usage", {})
        lines.append(f"- `{name}`: llm_calls={h.get('calls', 0) + h.get('memo_hits', 0)}, "
                     f"memo_hits={h.get('memo_hits', 0)}, errors={h.get('errors', 0)}, "
                     f"elapsed={sum(s['elapsed_s'] for s in ss):.0f}s")
    Path(out_md).write_text("\n".join(lines))
    return "\n".join(lines)

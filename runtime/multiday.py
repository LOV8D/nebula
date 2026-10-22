"""Multi-day runs + drift checks (step 2 of the 2026-10-21 work order).

Single-day event effects ride on day-scale seed noise; fee contagion and
circuit-breaker stampedes need multi-day windows. This module clones the
standard scenarios with `days: N`, runs them, and reports:

- day-by-day EQ returns for A/B;
- event-window effect;
- behavioral drift table (wake/pass/net-direction per day) with a
  monotone-drift flag — a persona panel that slowly becomes someone else
  is an identity failure (BP layer 2), not a market result.

    python3 -m runtime.cli multiday --days 5 --seeds 3     # mock brain, seconds
    python3 -m runtime.cli multiday --days 5 --seeds 1 --real   # remote brain
"""
import json
import shutil
from pathlib import Path

from .engine import run_scenario
from .demo import _panel, _load, _mean

ROOT = Path(__file__).resolve().parent.parent


def run_multiday(days=5, seeds=3, real=False, out_root=None):
    out_root = Path(out_root) if out_root else ROOT / "runs" / "multiday"
    panel = _panel()
    model = None
    if real:
        import os
        from .llm import load_env
        load_env()
        model = {"provider": "openai_compat",
                 "model_id": os.environ.get("BRAIN_MODEL", "glm-5.3-flash"),
                 "base_url": os.environ["BRAIN_BASE_URL"],
                 "api_key": os.environ["BRAIN_API_KEY"],
                 "max_workers": 8,
                 "cache_path": str(out_root / "llm_cache.json")}
    print(f"=== multiday: {days} days x {seeds} seeds "
          f"({'real brain' if real else 'mock'}) ===")
    per = {}
    for scen in ("news_a", "news_b"):
        rows = []
        for i in range(seeds):
            sc = _load(ROOT / "scenarios" / f"{scen}.yaml")
            sc["days"] = days
            sc["seed"] = sc.get("seed", 11) + i * 101
            if model:
                sc["model"] = model
            d = out_root / f"{scen}_s{i}"
            if d.exists():
                shutil.rmtree(d)
            run_scenario(sc, panel, d, quiet=True)
            s = json.loads((d / "summary.json").read_text())
            rows.append(s)
            print(f"  {scen} s{i}: EQ total {s['assets']['EQ']['total_ret']:+.1%} "
                  f"dd {s['assets']['EQ']['max_drawdown']:+.1%} "
                  f"daily {[f'{r:+.1%}' for r in s['assets']['EQ']['daily_returns']]}")
        per[scen] = rows
    report = _report(per, days, seeds, real)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "report.md").write_text(report)
    print(report)


def _drift_flag(rows):
    """Monotone drift detector on the per-day net direction series."""
    import statistics
    series = []
    for s in rows:
        for d in s.get("drift", []):
            series.append((d["day"], d["net_dir"], d["pass_rate"]))
    if len(series) < 4:
        return "insufficient data"
    days = sorted({d for d, _, _ in series})
    nd = [statistics.mean([n for d, n, _ in series if d == day]) for day in days]
    mono = all(nd[i] <= nd[i + 1] for i in range(len(nd) - 1)) or \
           all(nd[i] >= nd[i + 1] for i in range(len(nd) - 1))
    spread = max(nd) - min(nd)
    return (f"WARNING: monotone net-direction drift {nd}" if mono and spread > 0.5
            else f"ok (net-direction range {spread:.2f}, no monotone trend)")


def _report(per, days, seeds, real):
    L = [f"# Multi-day run ({days} sim days, {seeds} seeds, "
         f"{'real brain' if real else 'mock brain'})", "",
         "## Day-by-day EQ returns (mean over seeds)", ""]
    n_days = max((len(s["assets"]["EQ"]["daily_returns"])
                  for rows in per.values() for s in rows), default=0)
    L.append("| scenario | " + " | ".join(f"day {i+2}" for i in range(n_days)) +
             " | total | max dd |")
    L.append("|---" * (n_days + 3) + "|")
    for scen, rows in per.items():
        ds = [_mean([s["assets"]["EQ"]["daily_returns"][i] for s in rows
                     if len(s["assets"]["EQ"]["daily_returns"]) > i])
              for i in range(n_days)]
        tot = _mean([s["assets"]["EQ"]["total_ret"] for s in rows])
        dd = _mean([s["assets"]["EQ"]["max_drawdown"] for s in rows])
        L.append(f"| {scen} | " + " | ".join(f"{d:+.1%}" for d in ds) +
                 f" | {tot:+.1%} | {dd:+.1%} |")
    a = per["news_a"]; b = per["news_b"]
    wa = _mean([s["event_windows_avg"]["EQ_win90_ret"] for s in a])
    wb = _mean([s["event_windows_avg"]["EQ_win90_ret"] for s in b])
    ta = _mean([s["assets"]["EQ"]["total_ret"] for s in a])
    tb = _mean([s["assets"]["EQ"]["total_ret"] for s in b])
    L += ["", f"**A/B over {days} days:** neutral {ta:+.1%} vs alarming {tb:+.1%} "
              f"(event window {wa:+.1%} vs {wb:+.1%}).", ""]
    L += ["## Behavioral drift (identity check)", "",
          f"- news_a: {_drift_flag(a)}",
          f"- news_b: {_drift_flag(b)}",
          "", "Drift table per run in each `summary.json -> drift`.", "",
          "Direction and ranking only — no effect sizes (BP red line)."]
    return "\n".join(L)

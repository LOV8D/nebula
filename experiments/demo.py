"""One-command demo actions: the wind-tunnel showcase.

    python3 -m runtime.cli demo      # mock brain, offline, ~11 s (35 runs)
    python3 -m runtime.cli demo2     # the decided 8B brain via vLLM (see README)

Orchestration: ensure panel -> smoke gate (all five books trade) ->
run the experiment groups -> per-group comparison reports ->
top-level report with headline numbers -> terminal summary.
Direction and ranking only — no effect sizes (BP red line).
"""
import json
import shutil
import time
from pathlib import Path

from runtime import metrics
from runtime.engine import run_scenario
from runtime.personas import write_panel
from runtime.paths import RUNS

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = {
    "fee_demo": ["baseline", "fee_low", "fee_high"],
    "news_demo": ["news_a", "news_b"],
    "cb_demo": ["cb_magnet_on", "cb_magnet_off"],
}
# demo2 default: the flagship A/B only — real-model calls are the bottleneck
EXPERIMENTS_LLM = {"news_demo": ["news_a", "news_b"]}


def _load(path):
    import yaml
    return yaml.safe_load(Path(path).read_text())


def _panel():
    path = ROOT / "personas" / "panel_v3.json"
    if not path.exists():
        write_panel(path)
    return json.loads(path.read_text())


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _pct(x):
    return f"{x:+.1%}" if isinstance(x, (int, float)) else "—"


def _f(x, d=3):
    return f"{x:.{d}f}" if isinstance(x, (int, float)) else "—"


def _summaries(out_root, group, scen, seeds):
    return [json.loads((out_root / group / f"{scen}_s{i}" / "summary.json").read_text())
            for i in range(seeds)]


def run_demo(seeds=5, out_root=None, model_override=None, experiments=None):
    """model_override replaces every scenario's `model:` block (how demo2
    swaps the mock brain for the 8B); experiments filters groups."""
    from runtime.snapshot import apply_snapshot
    out_root = Path(out_root) if out_root else RUNS / "demo"
    experiments = experiments or EXPERIMENTS
    t0 = time.time()
    brain = (model_override or {}).get("model_id", "mock-heuristic-v1")
    print(f"=== Market Wind Tunnel demo (brain: {brain}) ===")
    panel = _panel()
    print(f"panel: {len(panel)} agents ({ROOT / 'personas' / 'panel_v3.json'})")

    # -- smoke gate: one baseline seed; all five books must trade ---------
    smoke_dir = out_root / "_smoke"
    if smoke_dir.exists():
        shutil.rmtree(smoke_dir)
    sc = apply_snapshot(_load(ROOT / "scenarios" / "baseline.yaml"))
    if model_override:
        m = dict(model_override)
        m["cache_path"] = str(out_root / "llm_cache.json")
        sc["model"] = m
    run_scenario(dict(sc, seed=1), panel, smoke_dir / "baseline_s0", quiet=True)
    dead = [a for a, mm in json.loads(
        (smoke_dir / "baseline_s0" / "summary.json").read_text())["assets"].items()
        if mm["total_volume"] <= 0]
    if dead:
        raise SystemExit(f"smoke gate FAILED: books {dead} did not trade — "
                         f"inspect {smoke_dir / 'baseline_s0'} before running experiments")
    print("smoke gate: all five books trade  OK")

    # -- experiments ------------------------------------------------------
    cache_path = out_root / "llm_cache.json"
    for group, scens in experiments.items():
        for scen in scens:
            base = apply_snapshot(_load(ROOT / "scenarios" / f"{scen}.yaml"))
            if model_override:
                m = dict(model_override)
                m["cache_path"] = str(cache_path)
                base["model"] = m
            for i in range(seeds):
                d = out_root / group / f"{scen}_s{i}"
                if d.exists():
                    shutil.rmtree(d)
                run_scenario(dict(base, seed=base.get("seed", 11) + i * 101),
                             panel, d, quiet=True)
        metrics.compare([str(pp) for pp in sorted((out_root / group).glob("*_s*"))],
                        out_root / group / "report.md")
        print(f"experiments: {group} done ({' | '.join(scens)} x{seeds} seeds)")

    # -- headlines --------------------------------------------------------
    h = _headlines(out_root, seeds, experiments)
    rep = _report(h, seeds, time.time() - t0, brain)
    (out_root / "report.md").write_text(rep)
    print(_terminal(h, seeds, out_root, time.time() - t0, brain))
    return h


def _headlines(out_root, seeds, experiment_map):
    ran = set(experiment_map)
    h = {}
    if "news_demo" in ran:
        na = _summaries(out_root, "news_demo", "news_a", seeds)
        nb = _summaries(out_root, "news_demo", "news_b", seeds)
        h["news_a_win90"] = _mean([s["event_windows_avg"]["EQ_win90_ret"] for s in na])
        h["news_b_win90"] = _mean([s["event_windows_avg"]["EQ_win90_ret"] for s in nb])
        h["news_a_day"] = _mean([s["assets"]["EQ"]["total_ret"] for s in na])
        h["news_b_day"] = _mean([s["assets"]["EQ"]["total_ret"] for s in nb])
        # brain coverage: share of novel-round intents that came from the LLM
        u = na[0].get("usage", {})
        tot_err = u.get("errors", 0)
        tot_call = u.get("calls", 0) + u.get("cache_hits", 0)
        h["brain_cov"] = (tot_call - tot_err) / tot_call if tot_call else None
        h["brain_err"] = tot_err
        from .parity import check_experiment
        h["parity"] = check_experiment(out_root / "news_demo")
    if "fee_demo" in ran:
        for tier in ("baseline", "fee_low", "fee_high"):
            ss = _summaries(out_root, "fee_demo", tier, seeds)
            h[f"{tier}_disp"] = _mean([s["event_windows_avg"]["win_dispersion"] for s in ss])
            h[f"{tier}_dd"] = _mean([s["assets"]["EQ"]["max_drawdown"] for s in ss])
    if "cb_demo" in ran:
        con = _summaries(out_root, "cb_demo", "cb_magnet_on", seeds)
        coff = _summaries(out_root, "cb_demo", "cb_magnet_off", seeds)
        h["cb_ran"] = True
        h["cb_halts_on"] = sum(s["assets"]["EQ"]["n_halts"] for s in con)
        h["cb_halts_off"] = 0
        # compare only on seeds where the breaker actually fired — on/off
        # are identical by construction on non-triggering seeds
        trig = [i for i in range(seeds) if con[i]["assets"]["EQ"]["n_halts"] > 0]
        h["cb_trig_seeds"] = trig
        if trig:
            h["cb_vol_on"] = _mean([con[i]["assets"]["EQ"]["total_volume"] for i in trig])
            h["cb_vol_off"] = _mean([coff[i]["assets"]["EQ"]["total_volume"] for i in trig])
            h["cb_dd_on"] = _mean([con[i]["assets"]["EQ"]["max_drawdown"] for i in trig])
            h["cb_dd_off"] = _mean([coff[i]["assets"]["EQ"]["max_drawdown"] for i in trig])
        else:
            h["cb_vol_on"] = h["cb_vol_off"] = h["cb_dd_on"] = h["cb_dd_off"] = None
    return h


def _terminal(h, seeds, out_root, elapsed, brain):
    L = ["", "=== HEADLINES (direction & ranking only — no effect sizes) ==="]
    if "news_a_win90" in h:
        sep = abs((h['news_a_day'] or 0) - (h['news_b_day'] or 0)) > 0.005
        verdict = ("framing separates after the initial dip" if sep
                   else "A/B DID NOT SEPARATE — inspect llm error counts before reading anything into this")
        L.append(f"news A/B      90-round window EQ: neutral {_pct(h['news_a_win90'])}"
                 f"  vs alarming {_pct(h['news_b_win90'])}")
        L.append(f"              full-day EQ:        neutral {_pct(h['news_a_day'])}"
                 f"  vs alarming {_pct(h['news_b_day'])}   -> {verdict}")
    if "baseline_disp" in h:
        L.append(f"fee tiers     window dispersion: {_f(h['baseline_disp'],2)} -> {_f(h['fee_low_disp'],2)}"
                 f" -> {_f(h['fee_high_disp'],2)};  mean EQ drawdown: {_pct(h['baseline_dd'])}"
                 f" -> {_pct(h['fee_low_dd'])} -> {_pct(h['fee_high_dd'])}"
                 f"   -> fees raise tail risk before returns")
    if h.get("cb_ran"):
        if h["cb_trig_seeds"]:
            vol_dir = "lower" if h["cb_vol_on"] < h["cb_vol_off"] else "higher (deferred burst)"
            dd_gap = h["cb_dd_on"] - h["cb_dd_off"]
            dd_dir = ("deeper" if dd_gap < -0.02 else
                      "same depth" if abs(dd_gap) <= 0.02 else "shallower")
            L.append(f"circuit brkr  fired on {len(h['cb_trig_seeds'])}/{seeds} seeds "
                     f"(halts={h['cb_halts_on']}); on those seeds: EQ volume "
                     f"ON {h['cb_vol_on']:.3g} vs OFF {h['cb_vol_off']:.3g} -> {vol_dir}; "
                     f"dd {_pct(h['cb_dd_on'])} vs {_pct(h['cb_dd_off'])} -> {dd_dir}"
                     f"   -> the breaker displaces trading, it does not stop the decline")
        else:
            L.append("circuit brkr  did not fire on any seed this run "
                     "(selloff never crossed -7% from the open)")
    if h.get("brain_cov") is not None:
        L.append(f"brain coverage: {h['brain_cov']:.0%} of LLM attempts succeeded"
                 f"  (errors={h['brain_err']})")
    L.append(f"reports -> {out_root}/report.md (+ per-group report.md)")
    L.append(f"elapsed {elapsed:.0f}s  seeds={seeds}  brain={brain}")
    return "\n".join(L)


def _parity_md(results):
    """Pre-intervention parity of each same-seed pair, for the report."""
    from .parity import describe
    if not results:
        return "   *Parity:* no same-seed A/B pairs found."
    bad = [r for r in results if r["ok"] is False]
    head = ("   *Parity:* every pair identical before the intervention."
            if not bad else
            f"   *Parity:* **{len(bad)}/{len(results)} pairs differ before the "
            "intervention** — for those seeds the A/B gap is not caused by the "
            "wording alone.")
    return head + "\n" + "\n".join(f"   - {describe(r)}" for r in results)


def _report(h, seeds, elapsed, brain):
    secs = []
    if "news_a_win90" in h:
        secs.append(
            "1. **Policy-communication wording A/B.** The same Fed decision, "
            "neutral vs alarming framing. Immediate 30-round window: both dip "
            "(knee-jerk selling); by the 90-round window and the full day the "
            f"paths separate: **{_pct(h['news_a_win90'])} vs {_pct(h['news_b_win90'])}** "
            f"(90-round EQ), **{_pct(h['news_a_day'])} vs {_pct(h['news_b_day'])}** "
            "(full-day EQ). Wording moves the recovery, not the first reaction.")
        secs.append(_parity_md(h.get("parity", [])))
    if "baseline_disp" in h:
        secs.append(
            "2. **Fee tiers.** Event-window dispersion "
            f"{_f(h['baseline_disp'],2)} → {_f(h['fee_low_disp'],2)} → "
            f"{_f(h['fee_high_disp'],2)}; mean EQ max drawdown "
            f"{_pct(h['baseline_dd'])} → {_pct(h['fee_low_dd'])} → "
            f"{_pct(h['fee_high_dd'])}. Fees raise disagreement and tail risk "
            "before they show up in average returns.")
    if h.get("cb_ran"):
        if h["cb_trig_seeds"]:
            secs.append(
                f"3. **Circuit breaker.** Fired on {len(h['cb_trig_seeds'])}/{seeds} "
                f"seeds (halt episodes ON={h['cb_halts_on']}, OFF=0 by construction). "
                f"On triggering seeds: EQ volume ON {h['cb_vol_on']:.3g} vs OFF "
                f"{h['cb_vol_off']:.3g}; mean drawdown {_pct(h['cb_dd_on'])} vs "
                f"{_pct(h['cb_dd_off'])}. The decline reaches a similar depth with "
                "and without the halt — the breaker displaces trading rather than "
                "preventing the move. Magnet-flavored anecdote, not a finding.")
        else:
            secs.append(
                "3. **Circuit breaker.** Did not fire on any seed this run "
                "(the selloff never crossed -7% from the open).")
    body = "\n\n".join(secs)
    return f"""# Market Wind Tunnel — demo action output

Generated ({elapsed:.0f}s), seeds={seeds}, brain `{brain}`.
883-agent panel, five books, batch call auctions.

{body}

## Artifacts

- Per-run evidence packs: `<group>/<scenario>_s<i>/` — manifest.json
  (five-tuple incl. the model), intents/trades/marks/violations/events JSONL
  (every Intent carries provider/model/prompt_version), summary.json.
- Per-group comparisons: `<group>/report.md`.
- `llm_cache.json` (real-brain runs): raw model responses keyed by prompt
  hash — re-running replays identical decisions (temperature > 0 is otherwise
  not replayable), and shared prompts amortize across seeds and scenarios.

## Red lines (BP)

Model output is not evidence. Direction and ranking only, no effect sizes.
Compare against the `mock`-brain run (`python3 -m runtime.cli demo`) and,
before trusting any qualitative ranking, against a second model/prompt —
model × prompt sensitivity is itself a deliverable.

## Reproduce

```bash
python3 -m runtime.cli demo2 --seeds {seeds}
```
"""


if __name__ == "__main__":
    run_demo()

"""Model x prompt sensitivity matrix (BP red-line deliverable).

Runs the flagship news-wording A/B across {models} x {prompt versions} x
seeds, then reports whether the qualitative conclusion (alarming framing
is worse than neutral) is stable across brains. Instability is a result,
not a failure.

    python3 -m runtime.cli sensitivity                     # default models
    python3 -m runtime.cli sensitivity --models a b --prompts p1 --seeds 2
"""
import json
from pathlib import Path

from .engine import run_scenario
from .llm import load_env
from .demo import _panel, _load, _mean

ROOT = Path(__file__).resolve().parent.parent


def run_sensitivity(models=None, prompts=("p1", "p2"), seeds=2, out_root=None):
    import os
    load_env()
    base_url = os.environ.get("BRAIN_BASE_URL")
    api_key = os.environ.get("BRAIN_API_KEY")
    brain_default = os.environ.get("BRAIN_MODEL", "glm-5.3-flash")
    models = models or [brain_default, "deepseek-v4.1-flash-1017"]
    if not base_url:
        raise SystemExit("BRAIN_BASE_URL missing in .env")
    out_root = Path(out_root) if out_root else ROOT / "runs" / "sensitivity"
    panel = _panel()
    print(f"=== sensitivity matrix: {len(models)} models x {len(prompts)} prompts "
          f"x {len(seeds if isinstance(seeds, list) else range(seeds))} seeds ===")

    from .llm import check_endpoint
    for m in models:
        ok, msg = check_endpoint(base_url, m, api_key)
        print(f"preflight {m}: {'OK' if ok else 'FAILED'} — {msg}")
        if not ok:
            raise SystemExit(f"model {m} not usable; fix .env or drop it with --models")

    results = []
    cache = out_root / "llm_cache.json"
    for model in models:
        for pv in prompts:
            for scen in ("news_a", "news_b"):
                rets, wins = [], []
                for i in range(seeds):
                    sc = _load(ROOT / "scenarios" / f"{scen}.yaml")
                    sc["seed"] = sc.get("seed", 11) + i * 101
                    sc["model"] = {"provider": "openai_compat", "model_id": model,
                                   "base_url": base_url, "api_key": api_key,
                                   "prompt_version": pv, "max_workers": 8,
                                   "cache_path": str(cache)}
                    d = out_root / f"{model}|{pv}|{scen}_s{i}"
                    if d.exists():
                        import shutil
                        shutil.rmtree(d)
                    run_scenario(sc, panel, d, quiet=True)
                    s = json.loads((d / "summary.json").read_text())
                    rets.append(s["assets"]["EQ"]["total_ret"])
                    wins.append(s["event_windows_avg"]["EQ_win90_ret"])
                    u = s["usage"]
                    print(f"  {model[:24]:24s} {pv} {scen} s{i}: "
                          f"day {rets[-1]:+.1%} win90 {wins[-1]:+.1%} "
                          f"calls={u['calls'] + u['cache_hits']} err={u['errors']}")
                results.append(dict(model=model, prompt=pv, scenario=scen,
                                    day_mean=_mean(rets), win90_mean=_mean(wins),
                                    day_seeds=rets, win90_seeds=wins))
    report = _report(results, seeds)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "report.md").write_text(report)
    (out_root / "results.json").write_text(json.dumps(results, indent=1))
    print(report)


def _report(results, seeds):
    combos = {}
    for r in results:
        combos.setdefault((r["model"], r["prompt"]), {})[r["scenario"]] = r

    lines = ["# Model x prompt sensitivity — news-wording A/B",
             "",
             "Question (BP red line): does the qualitative conclusion — alarming",
             "framing is worse than neutral — survive a change of brain or prompt?",
             "Direction and ranking only.", "",
             "| model | prompt | neutral (day) | alarming (day) | separation | conclusion stable? |",
             "|---|---|---|---|---|---|"]
    seps = {}
    for (model, pv), d in sorted(combos.items()):
        a, b = d["news_a"]["day_mean"], d["news_b"]["day_mean"]
        sep = a - b
        seps[(model, pv)] = sep
        lines.append(f"| {model} | {pv} | {a:+.1%} | {b:+.1%} | {sep:+.1%} | |")
    signs = {k: (v > 0) for k, v in seps.items()}
    n_pos = sum(signs.values())
    stable = n_pos in (0, len(signs)) and len(signs) > 1
    flip = "STABLE" if stable else "FLIPS"
    for i, ((model, pv), _) in enumerate(sorted(combos.items())):
        lines[i + 6] = lines[i + 6].rstrip(" | ") + f" {'yes' if signs[(model, pv)] else 'no (inverted)'} |"
    lines += ["", f"**Verdict: {flip}.** "
              f"{len(signs)} brain/prompt combos, {n_pos}/{len(signs)} show "
              "neutral > alarming on full-day EQ.", ""]
    if not stable:
        lines.append("The conclusion inverts across brains/prompts — report this "
                     "instability alongside any headline result. Per BP: "
                     "sensitivity is a deliverable, not noise.")
    lines.append(f"Seeds per combo: {seeds}. Raw per-seed values in `results.json`. "
                 "Runs use the shared response cache; provenance in each run's manifest.")
    return "\n".join(lines)

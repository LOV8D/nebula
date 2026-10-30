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

from runtime.engine import run_scenario
from runtime.llm import load_env
from runtime.paths import SENSITIVITY
from .demo import _panel, _load, _mean

ROOT = Path(__file__).resolve().parent.parent


def run_sensitivity(models=None, prompts=("p1", "p2"), seeds=2, out_root=None):
    import os
    load_env()
    base_url = os.environ.get("BRAIN_BASE_URL")
    api_key = os.environ.get("BRAIN_API_KEY")
    brain_default = os.environ.get("BRAIN_MODEL", "glm-5.3-flash")
    # GLM-only by user decision 2026-10-22 (deepseek legs were error-polluted
    # under 8-worker concurrency and sign-unstable at 2 seeds). Pass --models
    # to add others back deliberately.
    models = models or [brain_default]
    if not base_url:
        raise SystemExit("BRAIN_BASE_URL missing in .env")
    out_root = Path(out_root) if out_root else SENSITIVITY
    panel = _panel()
    print(f"=== sensitivity matrix: {len(models)} models x {len(prompts)} prompts "
          f"x {len(seeds if isinstance(seeds, list) else range(seeds))} seeds ===")

    from runtime.llm import check_endpoint
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
                rets, wins, errs = [], [], []
                for i in range(seeds):
                    sc = _load(ROOT / "scenarios" / f"{scen}.yaml")
                    sc["seed"] = sc.get("seed", 11) + i * 101
                    sc["model"] = {"provider": "openai_compat", "model_id": model,
                                   "base_url": base_url, "api_key": api_key,
                                   "prompt_version": pv, "max_workers": 8,
                                   "cache_path": str(cache)}
                    d = out_root / f"{model}__{pv}__{scen}_s{i}"
                    if d.exists():
                        import shutil
                        shutil.rmtree(d)
                    run_scenario(sc, panel, d, quiet=True)
                    s = json.loads((d / "summary.json").read_text())
                    rets.append(s["assets"]["EQ"]["total_ret"])
                    wins.append(s["event_windows_avg"]["EQ_win90_ret"])
                    u = s["usage"]
                    errs.append(u["errors"])
                    print(f"  {model[:24]:24s} {pv} {scen} s{i}: "
                          f"day {rets[-1]:+.1%} win90 {wins[-1]:+.1%} "
                          f"calls={u['calls'] + u['cache_hits']} err={u['errors']}")
                results.append(dict(model=model, prompt=pv, scenario=scen,
                                    day_mean=_mean(rets), win90_mean=_mean(wins),
                                    day_seeds=rets, win90_seeds=wins,
                                    errors=sum(errs)))
    report = _report(results, seeds)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "report.md").write_text(report)
    (out_root / "results.json").write_text(json.dumps(results, indent=1))
    from .parity import check
    par = {}
    for model in models:
        for pv in prompts:
            par[f"{model}__{pv}"] = [
                check(out_root / f"{model}__{pv}__news_a_s{i}",
                      out_root / f"{model}__{pv}__news_b_s{i}") for i in range(seeds)]
    (out_root / "parity.json").write_text(json.dumps(par, indent=1))
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
             "| model | prompt | neutral (day) | alarming (day) | separation | per seed | llm errors | conclusion stable? |",
             "|---|---|---|---|---|---|---|---|"]
    rows = []
    for (model, pv), d in sorted(combos.items()):
        a, b = d["news_a"]["day_mean"], d["news_b"]["day_mean"]
        err = d["news_a"].get("errors", 0) + d["news_b"].get("errors", 0)
        per_seed = [x - y for x, y in zip(d["news_a"]["day_seeds"], d["news_b"]["day_seeds"])]
        rows.append((model, pv, a, b, a - b, err, per_seed))
    # A row is only "yes" when EVERY seed agrees: a two-seed mean can be
    # positive while one seed is negative, and that row is not stable.
    signs = {r[:2]: all(x > 0 for x in r[6]) for r in rows}
    n_pos = sum(signs.values())
    stable = n_pos in (0, len(signs)) and len(signs) > 1
    for model, pv, a, b, sep, err, per_seed in rows:
        if all(x > 0 for x in per_seed):
            verdict = "yes"
        elif all(x < 0 for x in per_seed):
            verdict = "no (inverted)"
        else:
            verdict = "mixed (seeds disagree)"
        flag = " *" if err > 50 else ""    # error-polluted combo
        seeds_s = " / ".join(f"{x:+.1%}" for x in per_seed)
        lines.append(f"| {model} | {pv} | {a:+.1%} | {b:+.1%} | {sep:+.1%} "
                     f"| {seeds_s} | {err} | {verdict}{flag} |")
    flip = "STABLE" if stable else "FLIPS"
    lines += ["", f"**Verdict: {flip}.** "
              f"{len(rows)} brain/prompt combos, {n_pos}/{len(rows)} show "
              "neutral > alarming on full-day EQ in every seed.", ""]
    if not stable:
        lines.append("The conclusion inverts across brains/prompts — report this "
                     "instability alongside any headline result. Per BP: "
                     "sensitivity is a deliverable, not noise.")
    lines += ["", "`\\*` marks an error-polluted combo (>50 failed LLM attempts,",
              "3 tries each): many decisions fell back to the Tier-B policy tier,",
              "so that row is weak evidence — rerun with more seeds before",
              "quoting its direction.",
              f"Seeds per combo: {seeds}. Raw per-seed values in `results.json`.",
              "Runs use the shared response cache; provenance in each run's manifest."]
    return "\n".join(lines)

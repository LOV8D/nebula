"""CLI entry points.

  python -m runtime.cli panel                        # generate personas/panel_v3.json
  python -m runtime.cli run -s scenarios/baseline.yaml [--seeds 5]
  python -m runtime.cli compare runs/fee_demo runs/news_demo ... -o runs/report.md
"""
import argparse
import json
from pathlib import Path
import yaml

from . import metrics
from .engine import run_scenario
from .personas import write_panel
from .demo import run_demo, EXPERIMENTS_LLM

ROOT = Path(__file__).resolve().parent.parent


def _load(path):
    return yaml.safe_load(Path(path).read_text())


def _panel(scenario):
    p = scenario.get("panel") or str(ROOT / "personas" / "panel_v3.json")
    path = Path(p)
    if not path.is_absolute():
        path = ROOT / p
    if not path.exists():
        write_panel(path)
    return json.loads(path.read_text())


def cmd_panel(args):
    write_panel(args.out or (ROOT / "personas" / "panel_v3.json"))


def cmd_run(args):
    base = _load(args.scenario)
    out_root = Path(args.out or (ROOT / "runs" / base.get("tag", base["id"])))
    dirs = []
    for i in range(args.seeds):
        sc = dict(base)
        sc["seed"] = base.get("seed", 11) + i * 101
        sc["id"] = base["id"] if args.seeds == 1 else f"{base['id']}"
        d = out_root / f"{base['id']}_s{i}"
        run_scenario(sc, _panel(sc), d)
        dirs.append(str(d))
    if args.compare_with:
        dirs += [str(p) for p in args.compare_with]
        metrics.compare(dirs, out_root / "report.md")
        print(f"report -> {out_root / 'report.md'}")


def cmd_compare(args):
    txt = metrics.compare(args.runs, args.out)
    print(txt)


def cmd_provenance(args):
    from . import provenance
    panel = json.loads(Path(args.panel or (ROOT / "personas" / "panel_v3.json")).read_text())
    print(provenance.report(panel))


def cmd_telemetry(args):
    from . import viewer
    run = viewer.load_run(args.run)
    lines = viewer.stream(run, limit=args.limit, agent=args.agent,
                          asset=args.asset, show_pass=args.show_pass)
    print("\n".join(lines) or "no decisions recorded in this run")


def cmd_card(args):
    from . import viewer
    run = viewer.load_run(args.run)
    panel = _panel({})
    warn = viewer.check_panel(run, panel)
    if warn:
        print(f"WARNING: {warn}\n")
    ids = args.agents
    if not ids:  # one of each card kind
        seen, ids = set(), []
        acting = {it["agent_id"] for it in run["intents"]}
        for a in panel:
            k = a["card_kind"]
            if k in seen or (k == "position" and a["persona_id"] not in acting):
                continue
            seen.add(k)
            ids.append(a["persona_id"])
    for i, aid in enumerate(ids):
        if i:
            print()
        print(viewer.render_card(viewer.agent_card(panel, run, aid)))


def cmd_viewer(args):
    from . import viewer
    run = viewer.load_run(args.run)
    out = args.out or (Path(args.run) / "viewer.html")
    viewer.write_html(run, _panel({}), out, n_lines=args.limit,
                      agents=args.agents or None)
    print(f"viewer -> {out}")


def cmd_snapshot(args):
    from .snapshot import cmd_snapshot as _cmd
    _cmd(args)


def cmd_multiday(args):
    from .multiday import run_multiday
    run_multiday(days=args.days, seeds=args.seeds, real=args.real)


def cmd_sensitivity(args):
    from .sensitivity import run_sensitivity
    run_sensitivity(models=args.models, prompts=args.prompts,
                    seeds=args.seeds)


def _profile(name):
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())
    prof = cfg.get("profiles", {}).get(name)
    if not prof:
        raise SystemExit(f"unknown model profile '{name}' "
                         f"(known: {sorted(cfg.get('profiles', {}))})")
    return prof


def _apply_env(prof):
    """.env / environment overrides — the user's single config point for the
    remote brain. CLI flags still win over both."""
    import os
    from .llm import env_overrides
    base, key, model = env_overrides()
    if prof.get("provider") == "openai_compat":
        if model:
            prof["model_id"] = model
        if base:
            prof["base_url"] = base
        if key:
            prof["api_key"] = key
        mw = os.environ.get("BRAIN_MAX_WORKERS") or prof.get("max_workers")
        if mw:
            prof["max_workers"] = int(mw)
    return prof


def cmd_demo2(args):
    prof = _apply_env(_profile(args.profile))
    if args.base_url:
        prof["base_url"] = args.base_url
    if prof.get("provider") != "mock":
        from .llm import check_endpoint
        ok, msg = check_endpoint(prof["base_url"], prof.get("model_id"),
                                 prof.get("api_key"))
        print(f"brain preflight: {'OK — ' if ok else 'FAILED — '}{msg}")
        if not ok:
            raise SystemExit(
                "start the brain first, e.g.:\n"
                "  vllm serve Qwen/Qwen3-8B --port 8000\n"
                "or point --base-url at a remote OpenAI-compatible endpoint;\n"
                "see README 'demo2 — the real 8B brain'")
    run_demo(seeds=args.seeds, out_root=ROOT / "runs" / "demo2",
             model_override=prof, experiments=EXPERIMENTS_LLM)


def cmd_brain(args):
    prof = _apply_env(_profile(args.profile))
    if args.base_url:
        prof["base_url"] = args.base_url
    from .llm import check_endpoint
    ok, msg = check_endpoint(prof["base_url"], prof.get("model_id"),
                             prof.get("api_key"))
    print(f"[{args.profile}] {prof.get('provider')} @ {prof.get('base_url')}")
    print(f"preflight: {'OK — ' if ok else 'FAILED — '}{msg}")
    if not ok:
        raise SystemExit(1)
    # one real decision from a real persona, full provenance
    import random
    from .llm import LLMGateway
    panel = json.loads((ROOT / "personas" / "panel_v3.json").read_text()) \
        if (ROOT / "personas" / "panel_v3.json").exists() else None
    if panel is None:
        panel = write_panel(ROOT / "personas" / "panel_v3.json")
    persona = next(p2 for p2 in panel if p2["cls"] == "retail_direct"
                   and p2["archetype"] == "growth_trader")
    gw = LLMGateway(**prof)
    ctx = dict(t=150,
               events=[{"headline": "Fed warns inflation risks have intensified",
                        "sentiment": -0.6, "impact": 1.0, "assets": ["EQ"],
                        "source": "fed_chair_newswire"}],
               rets_bps={"EQ": -35}, day_ret={"EQ": -0.004},
               pnl_frac={"EQ": -0.02}, positions={"EQ": 12.0},
               rounds_per_day=390, sigma_z={"EQ": -1.2})
    out = gw.complete(persona, ctx, random.Random(0))
    print("sample decision:", json.dumps(out, indent=1))
    print("usage:", gw.usage)


def main():
    ap = argparse.ArgumentParser(prog="windtunnel")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("panel")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_panel)

    r = sub.add_parser("run")
    r.add_argument("-s", "--scenario", required=True)
    r.add_argument("--seeds", type=int, default=1)
    r.add_argument("--out", default=None)
    r.add_argument("--compare-with", nargs="*", default=None)
    r.set_defaults(fn=cmd_run)

    d = sub.add_parser("demo", help="mock-brain showcase: smoke + 3 experiments + reports")
    d.add_argument("--seeds", type=int, default=5)
    d.add_argument("--out", default=None)
    d.set_defaults(fn=lambda a: run_demo(a.seeds, a.out))

    d2 = sub.add_parser("demo2", help="real-brain showcase via vLLM (news A/B)")
    d2.add_argument("--seeds", type=int, default=2)
    d2.add_argument("--profile", default="vllm_qwen8b")
    d2.add_argument("--base-url", default=None)
    d2.set_defaults(fn=cmd_demo2)

    sn = sub.add_parser("snapshot", help="fetch real market levels -> config/snapshot.json")
    sn.add_argument("--force", action="store_true")
    sn.set_defaults(fn=cmd_snapshot)

    md = sub.add_parser("multiday", help="multi-day A/B runs + drift checks")
    md.add_argument("--days", type=int, default=5)
    md.add_argument("--seeds", type=int, default=3)
    md.add_argument("--real", action="store_true", help="use the remote brain")
    md.set_defaults(fn=cmd_multiday)

    sen = sub.add_parser("sensitivity", help="model x prompt matrix on the news A/B")
    sen.add_argument("--models", nargs="*", default=None)
    sen.add_argument("--prompts", nargs="*", default=["p1", "p2"])
    sen.add_argument("--seeds", type=int, default=2)
    sen.set_defaults(fn=cmd_sensitivity)

    b = sub.add_parser("brain", help="endpoint preflight + one sample decision")
    b.add_argument("--profile", default="vllm_qwen8b")
    b.add_argument("--base-url", default=None)
    b.set_defaults(fn=cmd_brain)

    c = sub.add_parser("compare")
    c.add_argument("runs", nargs="+")
    c.add_argument("-o", "--out", default=str(ROOT / "runs" / "report.md"))
    c.set_defaults(fn=cmd_compare)

    pv = sub.add_parser("provenance",
                        help="evidence coverage of the panel, per attribute")
    pv.add_argument("--panel", default=None)
    pv.set_defaults(fn=cmd_provenance)

    tl = sub.add_parser("telemetry",
                        help="decision stream of a run: obs -> intent -> fill")
    tl.add_argument("run")
    tl.add_argument("--limit", type=int, default=40)
    tl.add_argument("--agent", default=None)
    tl.add_argument("--asset", default=None)
    tl.add_argument("--show-pass", action="store_true",
                    help="include decisions to do nothing")
    tl.set_defaults(fn=cmd_telemetry)

    cd = sub.add_parser("card", help="agent card (role-aware) for a run")
    cd.add_argument("run")
    cd.add_argument("agents", nargs="*", help="persona ids; default one per role")
    cd.set_defaults(fn=cmd_card)

    vw = sub.add_parser("viewer", help="write a read-only HTML view of a run")
    vw.add_argument("run")
    vw.add_argument("-o", "--out", default=None)
    vw.add_argument("--limit", type=int, default=60)
    vw.add_argument("--agents", nargs="*", default=None)
    vw.set_defaults(fn=cmd_viewer)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

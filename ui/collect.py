"""Dashboard data: gather everything the product view shows into one dict.

Python reads recorded runs and derives an evaluation status without running a
new simulation. Presentation lives in ui/app/ (hand-written HTML/CSS/JS), and
ui/bundle.py inlines both into one
self-contained page. The page answers four questions, in this order:

    Verdict      — how much did the wording change the market?
    Ripple       — who reacted first, and who pushed? (agent-grid replay)
    Robustness   — does it hold across seeds, models, prompts?
    Performance  — which validation gates have actually passed?
    Evidence     — appendix: where the persona data comes from

    python3 -m runtime.cli ui            # writes site/dashboard.html

Every run is read, never re-executed. The A/B parity check (experiments/
parity.py) runs on the recorded logs, so a contaminated pair is flagged on the
page rather than averaged into the headline.
"""
import json
import time
from collections import defaultdict
from pathlib import Path

from experiments import parity
from runtime.paths import FLAGSHIP, PANEL, ROOT, SENSITIVITY
from . import viewer

ASSETS = ("EQ", "IR", "FX", "CMD", "CRYPTO")
ASSET_NAMES = {"EQ": "Equity", "IR": "Rates (10Y)", "FX": "FX (EUR/USD)",
               "CMD": "Commodity (gold)", "CRYPTO": "Crypto (BTC)"}
TIER_RANK = {"llm": 0, "policy": 1, "rule": 2, "meta": 3}
# User decision 2026-10-22: the brain is GLM-only. Other models stay on the
# robustness page, greyed, as the evidence for why they were dropped.
QUOTABLE_MODEL_PREFIX = "glm"


def _jsonl(run_dir, name):
    p = Path(run_dir) / f"{name}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _json(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _pct_path(marks, asset):
    """Cumulative % move vs the open, one value per round."""
    px = [m["price"] for m in marks if m["asset"] == asset and m["price"]]
    return [round((p / px[0] - 1) * 100, 3) for p in px] if px else []


# ---------------------------------------------------------------- agents
def _agents(panel):
    """Panel in grid order: LLM classes first, then policy, rule, meta;
    classes in first-appearance order; agents by id within a class."""
    first = {}
    for i, a in enumerate(panel):
        first.setdefault(a["cls"], i)
    order = sorted(panel, key=lambda a: (TIER_RANK.get(a["tier"], 9),
                                         first[a["cls"]], a["persona_id"]))
    classes = []
    for a in order:
        if not classes or classes[-1]["name"] != a["cls"]:
            classes.append({"name": a["cls"], "tier": a["tier"], "n": 0})
        classes[-1]["n"] += 1
    rows = [[a["persona_id"], a["archetype"], round(a.get("budget_usd") or 0),
             (a.get("identity_card") or "").split("\n")[0][:120]] for a in order]
    return order, classes, rows


# ---------------------------------------------------------------- flagship
def _arm(run_dirs):
    seeds = []
    for d in run_dirs:
        man = _json(d / "manifest.json", {})
        five = man.get("five_tuple", {})
        summ = _json(d / "summary.json", {})
        seeds.append({
            "run": _rel(d), "seed": five.get("seed"), "created": man.get("created"),
            "day_ret": summ.get("assets", {}).get("EQ", {}).get("total_ret"),
            "eq": _pct_path(_jsonl(d, "marks"), "EQ"),
        })
    return seeds


def _flagship(ab_root, panel_hash):
    a_dirs = sorted(ab_root.glob("news_a_s*"))
    b_dirs = sorted(ab_root.glob("news_b_s*"))
    if not a_dirs or not b_dirs:
        raise SystemExit(f"no news_a/news_b runs under {ab_root} — run `make demo2` first")
    man = _json(a_dirs[0] / "manifest.json", {})
    five = man.get("five_tuple", {})
    ev_a, ev_b = _jsonl(a_dirs[0], "events"), _jsonl(b_dirs[0], "events")
    t0 = parity.intervention_t(ev_a, ev_b)
    head = lambda evs: next((e for e in evs if e["t"] == t0), {})  # noqa: E731
    arms = {"a": _arm(a_dirs), "b": _arm(b_dirs)}
    manifests = [_json(d / "manifest.json", {}) for d in a_dirs + b_dirs]
    required = ("population", "intervention", "mechanism", "model", "seed")
    manifest_complete = all(
        m.get("code_hash")
        and all(k in m.get("five_tuple", {}) for k in required)
        and m.get("five_tuple", {}).get("model", {}).get("prompt_sha8")
        for m in manifests)
    mean = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    return {
        "root": _rel(ab_root),
        "model": five.get("model", {}).get("model_id", "?"),
        "prompt": five.get("model", {}).get("prompt_version", "?"),
        "prompt_sha8": five.get("model", {}).get("prompt_sha8", "?"),
        "population": five.get("population"),
        "panel_current": five.get("population") == panel_hash,
        "manifest_complete": manifest_complete,
        "t0": t0,
        "rounds": man.get("rounds_per_day", 390),
        "wording": {"a": head(ev_a).get("headline"), "b": head(ev_b).get("headline"),
                    "source": head(ev_a).get("source")},
        "arms": arms,
        "day_mean": {k: mean([s["day_ret"] for s in v if s["day_ret"] is not None])
                     for k, v in arms.items()},
        "parity": parity.check_experiment(ab_root),
    }


# ---------------------------------------------------------------- ripple
def _replay(run_dir, idx):
    """One arm, one seed: every LLM decision with its fill, plus the five
    books' paths. Compact rows: [t, agent_idx, side, asset_idx, size, urgency,
    fill_qty, rationale]."""
    trades = _jsonl(run_dir, "trades")
    filled = defaultdict(float)
    for tr in trades:
        for who in (tr.get("buyer"), tr.get("seller")):
            filled[who, tr["t"], tr["asset"]] += tr["qty"]
    rows = []
    for it in _jsonl(run_dir, "intents"):
        if it["agent_id"] not in idx:
            continue
        rows.append([it["t"], idx[it["agent_id"]], it.get("side", 0),
                     ASSETS.index(it["asset"]) if it.get("asset") in ASSETS else 0,
                     round(it.get("size_frac", 0), 3), round(it.get("urgency", 0), 2),
                     round(filled.get((it["agent_id"], it["t"], it.get("asset")), 0), 4),
                     (it.get("rationale") or "")[:110]])
    marks = _jsonl(run_dir, "marks")
    summ = _json(Path(run_dir) / "summary.json", {}).get("assets", {})
    books = {a: {"path": _pct_path(marks, a),
                 "day_ret": summ.get(a, {}).get("total_ret"),
                 "halts": summ.get(a, {}).get("n_halts", 0),
                 "trades": sum(1 for tr in trades if tr["asset"] == a)} for a in ASSETS}
    man = _json(Path(run_dir) / "manifest.json", {})
    return {"run": _rel(run_dir), "seed": man.get("five_tuple", {}).get("seed"),
            "intents": rows, "books": books}


def _who_moved(ab_root, t0, cls_of):
    """Net direction per class after the intervention, both arms, all seeds:
    sum(side x size_frac) over LLM decisions with t >= t0. Not dollar flow."""
    out = {}
    for arm, scen in (("a", "news_a"), ("b", "news_b")):
        net, n = defaultdict(float), defaultdict(int)
        for d in sorted(ab_root.glob(f"{scen}_s*")):
            for it in _jsonl(d, "intents"):
                if it["t"] >= t0 and it["agent_id"] in cls_of:
                    c = cls_of[it["agent_id"]]
                    net[c] += it.get("side", 0) * it.get("size_frac", 0)
                    n[c] += 1
        out[arm] = {"net": {k: round(v, 2) for k, v in net.items()}, "n": dict(n)}
    return out


# ---------------------------------------------------------------- robustness
def _robustness(flag, sens_dir):
    rows = [{
        "label": "Flagship", "sub": f"prompt {flag['prompt']} · {Path(flag['root']).parent.name}",
        "model": flag["model"], "prompt": flag["prompt"], "quotable": True, "errors": None,
        "seeds": [{"a": a["day_ret"], "b": b["day_ret"], "sep": a["day_ret"] - b["day_ret"],
                   "parity": p["ok"]}
                  for a, b, p in zip(flag["arms"]["a"], flag["arms"]["b"], flag["parity"])],
    }]
    results = _json(sens_dir / "results.json", [])
    combos = defaultdict(dict)
    for r in results:
        combos[r["model"], r["prompt"]][r["scenario"]] = r
    for (model, pv), d in sorted(combos.items(), key=lambda kv: (
            not kv[0][0].startswith(QUOTABLE_MODEL_PREFIX), kv[0])):
        if "news_a" not in d or "news_b" not in d:
            continue
        a, b = d["news_a"], d["news_b"]
        seeds = []
        for i, (x, y) in enumerate(zip(a["day_seeds"], b["day_seeds"])):
            p = parity.check(sens_dir / f"{model}__{pv}__news_a_s{i}",
                             sens_dir / f"{model}__{pv}__news_b_s{i}")
            seeds.append({"a": x, "b": y, "sep": x - y, "parity": p["ok"]})
        rows.append({"label": model, "sub": f"prompt {pv} · sensitivity",
                     "model": model, "prompt": pv,
                     "quotable": model.startswith(QUOTABLE_MODEL_PREFIX),
                     "errors": a.get("errors", 0) + b.get("errors", 0), "seeds": seeds})
    return {"rows": rows, "source": _rel(sens_dir / "results.json")}


# ---------------------------------------------------------------- evidence
def _evidence(panel, run_dir):
    from evidence import provenance
    cov = provenance.coverage(panel)
    run = viewer.load_run(run_dir)
    warn = viewer.check_panel(run, panel)
    acting = {it["agent_id"] for it in run["intents"]}
    for tr in run["trades"]:
        acting |= {tr.get("buyer"), tr.get("seller")} - {None, ""}
    chosen, seen = [], set()
    for prefer_acting in (True, False):   # an agent that acted, else any
        for a in panel:
            k = a.get("card_kind", "position")
            if k in seen or (prefer_acting and a["persona_id"] not in acting
                             and k != "event_source"):
                continue
            seen.add(k)
            chosen.append(a["persona_id"])
    cards = []
    for aid in chosen:
        c = viewer.agent_card(panel, run, aid)
        cards.append({
            "id": aid, "title": c["title"], "identity": c["identity"],
            "class": c["class"], "archetype": c["archetype"], "tier": c["tier"],
            "decisions": c["decisions"], "fills": c["fills"],
            "sections": [[t, [[str(k), str(v)] for k, v in rows
                              if v not in (None, "", "none")]]
                         for t, rows in c["sections"]],
            "evidence": c["evidence_summary"], "unknown": c["unknown_fields"][:8]})
    return {"coverage": {k: cov[k] for k in ("agents", "attribute_records",
                                              "by_evidence_kind", "grounded_share",
                                              "unknown_fields")},
            "cards": cards, "panel_warning": warn, "card_run": _rel(run_dir)}


# ---------------------------------------------------------------- top level
def collect(ab_root=None, sens_dir=None, replay_seed=0):
    from experiments.demo import _panel
    from runtime.recorder import _code_hash
    ab_root = Path(ab_root) if ab_root else FLAGSHIP
    sens_dir = Path(sens_dir) if sens_dir else SENSITIVITY
    panel = _panel()
    panel_hash = viewer.population_hash(panel)
    order, classes, agent_rows = _agents(panel)
    idx = {a["persona_id"]: i for i, a in enumerate(order)}
    cls_of = {a["persona_id"]: a["cls"] for a in panel}

    flag = _flagship(ab_root, panel_hash)
    run_a = ab_root / f"news_a_s{replay_seed}"
    run_b = ab_root / f"news_b_s{replay_seed}"
    robust = _robustness(flag, sens_dir)
    evidence = _evidence(panel, run_a)
    from evaluation.scorecard import build_scorecard
    performance = build_scorecard(flag, robust, evidence)
    return {
        "meta": {"generated": time.strftime("%Y-%m-%d %H:%M"),
                 "code_hash": _code_hash(), "panel_hash": panel_hash,
                 "panel": _rel(PANEL), "n_agents": len(panel),
                 "assets": list(ASSETS), "asset_names": ASSET_NAMES},
        "flagship": flag,
        "agents": {"classes": classes, "rows": agent_rows},
        "replay": {"a": _replay(run_a, idx), "b": _replay(run_b, idx)},
        "who": _who_moved(ab_root, flag["t0"], cls_of),
        "robustness": robust,
        "performance": performance,
        "evidence": evidence,
    }


def build(ab_root=None, sens_dir=None, replay_seed=0, out=None):
    from runtime.paths import SITE
    from .bundle import bundle
    data = collect(ab_root, sens_dir, replay_seed)
    out = Path(out) if out else SITE / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".data.json").write_text(json.dumps(data, separators=(",", ":")))
    out.write_text(bundle(data))
    return out

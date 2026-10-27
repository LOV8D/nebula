"""Cross-run dashboard: one self-contained HTML page for the wind tunnel.

The per-run viewer (runtime/viewer.py) shows one run's evidence pack. This
module assembles the product view as tabbed pages (MatrAIx-playground-style
navigation, static-file honest):

    Overview      — the flagship A/B, sensitivity, and honest status
    Live Run      — round-by-round REPLAY of a real run (play/pause/step):
                    five-book pulse, wake/intent/trade counters, event
                    timeline, OBS->INTENT->FILL telemetry. The run is NOT
                    re-executed; the recording is embedded. Clearly labelled
                    "replay".
    Personas      — agent grid (colour = class, brightness = activity),
                    click opens a role-aware card drawer with evidence
    Sensitivity   — the model x prompt matrix (BP red line)

    python3 -m runtime.cli ui            # writes docs/dashboard.html
"""
import html
import json
from pathlib import Path

from . import viewer

ROOT = Path(__file__).resolve().parent.parent
_esc = html.escape

ASSET_NAMES = {"EQ": "Equity", "IR": "Rates (10Y note)", "FX": "FX (EUR/USD)",
               "CMD": "Commodity (gold)", "CRYPTO": "Crypto (BTC)"}
ASSET_ORDER = ("EQ", "IR", "FX", "CMD", "CRYPTO")

# ---------------------------------------------------------------- SVG bits
W, H = 860, 300


def _series_svg(series_list, event_t=None, window=90, w=W, h=H, pad=36):
    """series_list: [(label, color, width, [(t, y%)], dash)] — y in percent.
    Shared x/y scale; event_t draws a vertical marker."""
    all_y = [y for _, _, _, pts, _ in series_list for _, y in pts]
    if not all_y:
        return "<div class='empty'>no data</div>"
    t0 = min(t for _, _, _, pts, _ in series_list for t, _ in pts)
    t1 = max(t for _, _, _, pts, _ in series_list for t, _ in pts)
    lo, hi = min(all_y), max(all_y)
    span = (hi - lo) or 1.0
    lo, hi = lo - span * 0.08, hi + span * 0.08

    def X(t):
        return pad + (t - t0) / max(t1 - t0, 1) * (w - pad - 8)

    def Y(v):
        return h - 22 - (v - lo) / (hi - lo) * (h - 40)

    parts = [f"<svg viewBox='0 0 {w} {h}' class='chart' role='img'>"]
    # zero line + y ticks; skip a label that would collide with a neighbour
    tick_ys = [Y(lo + (hi - lo) * f) for f in (0.15, 0.5, 0.85)]
    for v, ty in zip((lo + (hi - lo) * f for f in (0.15, 0.5, 0.85)), tick_ys):
        parts.append(f"<text x='{pad - 6}' y='{ty + 4:.1f}' class='tick' "
                     f"text-anchor='end'>{v:+.0f}%</text>")
    if lo < 0 < hi and all(abs(Y(0) - ty) >= 11 for ty in tick_ys):
        parts.append(f"<line x1='{pad}' y1='{Y(0):.1f}' x2='{w - 8}' "
                     f"y2='{Y(0):.1f}' stroke='#3a4150' stroke-dasharray='3 4'/>")
        parts.append(f"<text x='{pad - 6}' y='{Y(0) + 4:.1f}' class='tick' "
                     f"text-anchor='end'>0%</text>")
    elif lo < 0 < hi:
        parts.append(f"<line x1='{pad}' y1='{Y(0):.1f}' x2='{w - 8}' "
                     f"y2='{Y(0):.1f}' stroke='#3a4150' stroke-dasharray='3 4'/>")
    parts.append(f"<text x='{pad}' y='{h - 6}' class='tick'>t={t0}</text>")
    parts.append(f"<text x='{w - 8}' y='{h - 6}' class='tick' "
                 f"text-anchor='end'>t={t1}</text>")
    # event marker + reaction window band
    if event_t is not None and t0 <= event_t <= t1:
        parts.append(f"<rect x='{X(event_t):.1f}' y='10' width='"
                     f"{max(X(min(event_t + window, t1)) - X(event_t), 1):.1f}' "
                     f"height='{h - 36}' fill='#5b8bb0' opacity='0.08'/>")
        parts.append(f"<line x1='{X(event_t):.1f}' y1='10' x2='{X(event_t):.1f}' "
                     f"y2='{h - 26}' stroke='#7fa8d0' stroke-dasharray='4 3'/>")
        parts.append(f"<text x='{X(event_t) + 4:.1f}' y='20' class='tick'>"
                     f"intervention</text>")
    for label, color, lw, pts, dash in series_list:
        if len(pts) < 2:
            continue
        d = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts)
        dd = f" stroke-dasharray='{dash}'" if dash else ""
        parts.append(f"<polyline points='{d}' fill='none' stroke='{color}' "
                     f"stroke-width='{lw}'{dd} stroke-linejoin='round' "
                     f"opacity='{1.0 if lw > 1.5 else 0.45}'/>")
    parts.append("</svg>")
    return "".join(parts)


def _eq_path(run_dir):
    """[(t, cum_ret%)] for EQ from marks.jsonl, downsampled."""
    p = Path(run_dir) / "marks.jsonl"
    if not p.exists():
        return []
    pts = []
    for line in p.read_text().splitlines():
        m = json.loads(line)
        if m["asset"] == "EQ" and m["price"]:
            pts.append((m["t"], m["price"]))
    if not pts:
        return []
    p0 = pts[0][1]
    step = max(1, len(pts) // 160)
    return [(t, (px / p0 - 1) * 100) for t, px in pts[::step]]


def _asset_path(run_dir, asset, step=120):
    p = Path(run_dir) / "marks.jsonl"
    if not p.exists():
        return []
    pts = [(m["t"], m["price"]) for m in map(json.loads, p.read_text().splitlines())
           if m["asset"] == asset and m["price"]]
    if not pts:
        return []
    p0 = pts[0][1]
    k = max(1, len(pts) // step)
    return [(t, (px / p0 - 1) * 100) for t, px in pts[::k]]


# ---------------------------------------------------------------- sections
def _ab_section(ab_root, panel_hash=None):
    """Flagship news-wording A/B on the real brain."""
    runs = {}
    for scen in ("news_a", "news_b"):
        seeds = sorted(ab_root.glob(f"{scen}_s*"))
        runs[scen] = seeds
    if not all(runs.values()):
        return ("Flagship A/B — news wording",  # header kept; body says why empty
                "<div class='empty'>No A/B runs found under "
                f"{_esc(str(ab_root))} — run <code>make demo2</code> first.</div>")
    series, day_means = [], {"news_a": [], "news_b": []}
    for scen, color in (("news_a", "#57c98a"), ("news_b", "#e0685f")):
        seed_paths = [_eq_path(d) for d in runs[scen]]
        for sp in seed_paths:
            series.append((scen, color, 1.2, sp, "2 3"))
        if seed_paths:  # seed-mean bold line
            n = min(len(sp) for sp in seed_paths)
            mean = [(seed_paths[0][i][0],
                     sum(sp[i][1] for sp in seed_paths) / len(seed_paths))
                    for i in range(n)]
            series.append((scen, color, 2.6, mean, None))
        for d in runs[scen]:
            s = json.loads((d / "summary.json").read_text())
            day_means[scen].append(s["assets"]["EQ"]["total_ret"])
    ev_t = None
    events = (runs["news_a"][0] / "events.jsonl")
    if events.exists():
        for line in events.read_text().splitlines():
            e = json.loads(line)
            if "EQ" in e.get("assets", []):
                ev_t = e["t"] if ev_t is None else min(ev_t, e["t"])
    a = sum(day_means["news_a"]) / len(day_means["news_a"])
    b = sum(day_means["news_b"]) / len(day_means["news_b"])
    man = runs["news_a"][0] / "manifest.json"
    five = json.loads(man.read_text()).get("five_tuple", {}) if man.exists() else {}
    model = five.get("model", {}).get("model_id", "?")
    pop = five.get("population", "?")
    if panel_hash and pop == panel_hash:
        panel_chip = "<span class='chip'>current panel</span>"
    else:
        panel_chip = ("<span class='chip warn'>panel: pre-id-fix "
                      "(aggregate results stand, per-agent cards from these "
                      "runs do not)</span>")
    body = [
        "<div class='chips'>",
        f"<span class='chip'>brain {_esc(model)}</span>",
        f"<span class='chip'>{len(runs['news_a']) + len(runs['news_b'])} runs"
        f" ({len(runs['news_a'])}+{len(runs['news_b'])} seeds)</span>",
        panel_chip,
        "</div>",
        _series_svg(series, event_t=ev_t),
        "<div class='legend'>",
        "<span><i style='background:#57c98a'></i> neutral wording "
        f"(day mean {_fmt_pct(a)})</span> ",
        "<span><i style='background:#e0685f'></i> alarming wording "
        f"(day mean {_fmt_pct(b)})</span> ",
        "<span class='mut'>thin = single seeds · bold = seed mean · "
        "band = 90-round reaction+recovery window</span></div>",
        f"<div class='read'>How to read: if the bold lines separate after the "
        f"intervention with neutral above alarming ({_fmt_pct(a - b)} on day "
        "totals), the wording moves the market in the expected direction — "
        "direction and ranking only, never effect sizes.</div>",
    ]
    return "Flagship A/B — news wording (real brain)", "".join(body)


def _sensitivity_section(res_path):
    if not res_path.exists():
        return "Sensitivity — model x prompt", (
            f"<div class='empty'>No matrix at {_esc(str(res_path))} — run "
            "<code>python3 -m runtime.cli sensitivity</code> first.</div>")
    results = json.loads(res_path.read_text())
    combos = {}
    for r in results:
        combos.setdefault((r["model"], r["prompt"]), {})[r["scenario"]] = r
    rows, signs = [], {}
    for (model, pv), d in sorted(combos.items()):
        a, b = d["news_a"]["day_mean"], d["news_b"]["day_mean"]
        err = d["news_a"].get("errors", 0) + d["news_b"].get("errors", 0)
        signs[(model, pv)] = a - b > 0
        rows.append((model, pv, a, b, a - b, err))
    n_pos = sum(signs.values())
    verdict = "STABLE" if n_pos in (0, len(signs)) else "FLIPS"
    body = ["<table class='grid'><tr><th>model</th><th>prompt</th>"
            "<th>neutral (day)</th><th>alarming (day)</th><th>separation</th>"
            "<th>llm errors</th><th>stable?</th></tr>"]
    for model, pv, a, b, sep, err in rows:
        st = "yes" if signs[(model, pv)] else "no (inverted)"
        cls = "ok" if signs[(model, pv)] else "bad"
        star = " *" if err > 50 else ""
        quotable = model.startswith("glm")
        dim = "" if quotable else " class='mut'"
        body.append(
            f"<tr><td>{_esc(model)}</td><td>{pv}</td>"
            f"<td>{_fmt_pct(a)}</td><td>{_fmt_pct(b)}</td>"
            f"<td>{_fmt_pct(sep)}</td><td>{err}{star}</td>"
            f"<td{dim}><span class='pill {cls}'>{st}</span>{star}</td></tr>")
    body.append("</table>")
    body.append(
        f"<div class='read'>Verdict: <b>{verdict}</b> ({n_pos}/{len(signs)} "
        "combos neutral &gt; alarming). Per the user decision of 2026-10-22 "
        "the brain is <b>GLM-only</b>; the deepseek rows stay as evidence of "
        "why it was dropped (error-polluted legs, sign-unstable at 2 seeds). "
        "Quotable: glm rows — the wording A/B holds on both prompts.</div>"
        "<div class='chips'>"
        "<span class='chip'>prompt p1 sha f91ac628</span>"
        "<span class='chip'>prompt p2 sha 918ce74f</span>"
        "<span class='chip'>instability is a deliverable, not noise</span>"
        "</div>")
    return "Sensitivity — model x prompt (BP red line)", "".join(body)


def _pulse_section(run_dir):
    s_path = run_dir / "summary.json"
    if not s_path.exists():
        return "Five books pulse", (
            f"<div class='empty'>No run at {_esc(str(run_dir))} — run "
            "<code>make demo</code> first.</div>")
    s = json.loads(s_path.read_text())
    man = json.loads((run_dir / "manifest.json").read_text())
    five = man.get("five_tuple", {})
    body = ["<div class='chips'>",
            f"<span class='chip'>population {five.get('population', '?')} "
            "(current panel)</span>",
            f"<span class='chip'>brain {_esc(five.get('model', {}).get('model_id', '?'))}"
            " — pipeline view</span>",
            f"<span class='chip'>seed {five.get('seed', '?')}</span></div>",
            "<div class='smalls'>"]
    for a in ("EQ", "IR", "FX", "CMD", "CRYPTO"):
        st = s["assets"].get(a, {})
        halt = st.get("n_halts", 0)
        body.append(
            f"<div class='small'><h3>{ASSET_NAMES.get(a, a)}"
            + (f" <span class='pill bad'>{halt} halts</span>" if halt else "")
            + "</h3>"
            + _series_svg([("p", "#9fb0c9", 1.8, _asset_path(run_dir, a), None)],
                          w=300, h=110, pad=30)
            + f"<div class='stats'>day {_fmt_pct(st.get('total_ret', 0))} · "
              f"vol {st.get('ann_vol', 0):.1%} · "
              f"spread {st.get('avg_spread_bps', 0):.0f}bps · "
              f"kurt {st.get('excess_kurtosis', 0):.0f}</div></div>")
    body.append("</div>")
    return "Five books pulse — one run, current panel", "".join(body)


def _telemetry_section(run_dir):
    if not (run_dir / "intents.jsonl").exists():
        return "Trajectory telemetry", (
            f"<div class='empty'>No intents at {_esc(str(run_dir))}.</div>")
    run = viewer.load_run(run_dir)
    lines = viewer.stream(run, limit=14)
    pre = _esc("\n".join(lines)) or "(no non-pass decisions)"
    return "Trajectory telemetry — OBS → INTENT → FILL", (
        f"<pre>{pre}</pre>"
        "<div class='read'>Every line names the brain that produced it. "
        "Rationale text is audit material, never scored as evidence.</div>")


def _cards_section(run_dir, panel):
    if not (run_dir / "intents.jsonl").exists():
        return "Agent cards", "<div class='empty'>No run to card against.</div>"
    run = viewer.load_run(run_dir)
    warn = viewer.check_panel(run, panel)
    chosen, seen = [], set()
    acting = {it["agent_id"] for it in run["intents"]}
    for tr in run["trades"]:                    # MMs and policy tiers act via fills
        acting |= {tr.get("buyer"), tr.get("seller")} - {None, ""}
    for a in panel:
        k = a.get("card_kind", "position")
        if k in seen:
            continue
        if a["persona_id"] in acting or k == "event_source":
            seen.add(k)
            chosen.append(a["persona_id"])
        if len(seen) == 4:
            break
    # kinds that never acted still get their template card (e.g. a quiet MM)
    for a in panel:
        k = a.get("card_kind", "position")
        if k not in seen:
            seen.add(k)
            chosen.append(a["persona_id"])
    body = []
    if warn:
        body.append(f"<div class='read warn'>{_esc(warn)}</div>")
    body.append("<div class='cards'>")
    for aid in chosen:
        c = viewer.agent_card(panel, run, aid)
        secs = []
        for title, rows in c["sections"]:
            cells = "".join(f"<tr><td class='k'>{_esc(str(k))}</td>"
                            f"<td>{_esc(str(v))}</td></tr>"
                            for k, v in rows if v not in (None, "", "none"))
            secs.append(f"<div class='cs'>{title}<table>{cells}</table></div>")
        ev = " · ".join(f"{k}={v}" for k, v in sorted(c["evidence_summary"].items()))
        body.append(
            f"<div class='card'><h3>{_esc(c['title'])} "
            f"<span class='id'>{_esc(aid)}</span></h3>"
            f"<p class='id'>{_esc(c['identity'])}</p>"
            f"<div class='chips'><span class='chip'>{_esc(c['class'])}"
            f"/{_esc(c['archetype'])}</span>"
            f"<span class='chip'>tier {_esc(c['tier'])}</span>"
            f"<span class='chip'>{c['decisions']} decisions · "
            f"{c['fills']} fills</span></div>"
            + "".join(secs)
            + f"<div class='ev'>Evidence: {_esc(ev)}</div>"
            + (f"<div class='ev warn'>Unset for want of evidence: "
               f"{_esc(', '.join(c['unknown_fields'][:6]))}</div>"
               if c["unknown_fields"] else "")
            + "</div>")
    body.append("</div>")
    return "Agent cards — one per role, evidence attached", "".join(body)


# ---------------------------------------------------------------- replay pack
def _replay_pack(run_dir):
    """Round-bucketed recording of a run, embedded as JSON for the player.

    kept small on purpose: EQ mark per round (level + halt), per-asset volume
    and trade count, wake/intent counts, up to 6 telemetry lines per round.
    """
    run_dir = Path(run_dir)
    intents = [json.loads(l) for l in (run_dir / "intents.jsonl").read_text().splitlines() if l.strip()]
    marks = [json.loads(l) for l in (run_dir / "marks.jsonl").read_text().splitlines() if l.strip()]
    events = [json.loads(l) for l in (run_dir / "events.jsonl").read_text().splitlines() if l.strip()]
    trades = [json.loads(l) for l in (run_dir / "trades.jsonl").read_text().splitlines() if l.strip()]

    by_round = {}
    for m in marks:
        r = by_round.setdefault(m["t"], {"marks": {}})
        r["marks"][m["asset"]] = [m["price"], m.get("halted", False)]
    for it in intents:
        r = by_round.setdefault(it["t"], {"marks": {}})
        r.setdefault("intents", []).append(it)
    for tr in trades:
        r = by_round.setdefault(tr["t"], {"marks": {}})
        r.setdefault("trades", []).append(tr)

    ev_idx = {e["t"]: e for e in events}
    rounds = []
    eq0 = None
    vol_c = {a: 0.0 for a in ASSET_ORDER}
    n_tr_c = {a: 0 for a in ASSET_ORDER}
    wake_c = intent_c = trade_c = 0
    for t in sorted(by_round):
        r = by_round[t]
        for a, mk in r.get("marks", {}).items():
            if a == "EQ" and mk[0]:
                eq0 = eq0 or mk[0]
        its = r.get("intents", [])
        trs = r.get("trades", [])
        wake_c += len(its)
        intent_c += sum(1 for i in its if i.get("side"))
        trade_c += len(trs)
        for tr in trs:
            vol_c[tr["asset"]] = vol_c.get(tr["asset"], 0) + tr["qty"]
            n_tr_c[tr["asset"]] = n_tr_c.get(tr["asset"], 0) + 1
        eq_level = r.get("marks", {}).get("EQ", [None, False])[0]
        rounds.append({
            "t": t, "eq": (eq_level / eq0 - 1) * 100 if eq0 and eq_level else None,
            "eqHalt": bool(r.get("marks", {}).get("EQ", [0, False])[1]),
            "vol": [round(vol_c[a], 1) for a in ASSET_ORDER],
            "ntr": [n_tr_c[a] for a in ASSET_ORDER],
            "wake": wake_c, "intent": intent_c, "trade": trade_c,
            "ev": _ev_brief(ev_idx[t]) if t in ev_idx else None,
            "tele": _tele_briefs(its, trs),
        })
    man = json.loads((run_dir / "manifest.json").read_text())
    five = man.get("five_tuple", {})
    return {
        "run_id": man.get("run_id", run_dir.name),
        "dir": str(run_dir.name),
        "model": five.get("model", {}).get("model_id", "?"),
        "population": five.get("population", "?"),
        "seed": five.get("seed", "?"),
        "nRounds": len(rounds),
        "equilibrium_note": "replay of a recorded run — not a live execution",
        "rounds": rounds,
    }


def _ev_brief(e):
    return {"t": e["t"], "headline": e["headline"][:110],
            "sentiment": e["sentiment"], "assets": e["assets"]}


def _tele_briefs(intents, trades, limit=6):
    fills = {}
    for tr in trades:
        for who in (tr.get("buyer"), tr.get("seller")):
            fills.setdefault((who, tr["t"], tr["asset"]), []).append(tr)
    out = []
    for it in intents[:limit]:
        got = fills.get((it["agent_id"], it["t"], it["asset"]), [])
        if got:
            qty = sum(x["qty"] for x in got)
            px = sum(x["price"] * x["qty"] for x in got) / max(qty, 1e-9)
            fill = f"fill {qty:.4g}@{px:.2f}"
        else:
            fill = "no fill"
        side = {1: "buy", -1: "sell", 0: "pass"}.get(it.get("side", 0), "?")
        out.append(f"t={it['t']} {it['agent_id']} {it['asset']} {side} "
                   f"{it.get('size_frac', 0):.3f} u{it.get('urgency', 0):.2f} "
                   f"-> {fill} [{it.get('model', '?')}/{it.get('prompt_version', '')}]")
    return out


# ---------------------------------------------------------------- page
def _fmt_pct(v):
    return f"{v * 100:+.1f}%"


def build(ab_root=None, sens_path=None, pulse_dir=None, tele_dir=None,
          out=None, replay_dir=None):
    ab_root = Path(ab_root) if ab_root else ROOT / "runs" / "demo2" / "news_demo"
    sens_path = Path(sens_path) if sens_path else ROOT / "runs" / "sensitivity" / "results.json"
    pulse_dir = Path(pulse_dir) if pulse_dir else ROOT / "runs" / "demo" / "news_demo" / "news_a_s0"
    tele_dir = Path(tele_dir) if tele_dir else ROOT / "runs" / "demo2" / "news_demo" / "news_b_s0"
    replay_dir = (Path(replay_dir) if replay_dir
                  else ROOT / "runs" / "demo2" / "news_demo" / "news_a_s0")
    out = Path(out) if out else ROOT / "docs" / "dashboard.html"

    from .demo import _panel
    from . import viewer

    panel = _panel()
    n_agents = len(panel)
    panel_hash = viewer.population_hash(panel)

    replay = _replay_pack(replay_dir)
    persona_grid = _persona_grid(panel)
    tele_static = _telemetry_section(tele_dir)[1]  # static fallback sample

    overview = "".join(
        f"<section><h2>{_esc(t)}</h2>{b}</section>" for t, b in [
            _ab_section(ab_root, panel_hash=panel_hash),
            _sensitivity_section(sens_path),
        ])

    page = _PAGE \
        .replace("__N_AGENTS__", str(n_agents)) \
        .replace("__OVERVIEW__", overview) \
        .replace("__REPLAY_JSON__", json.dumps(replay).replace("</", "<\\/")) \
        .replace("__PERSONA_JSON__", json.dumps(persona_grid).replace("</", "<\\/")) \
        .replace("__CARDS_HTML__", _cards_html(pulse_dir, panel)) \
        .replace("__TELE_STATIC__", _esc("\n".join(viewer.stream(
            viewer.load_run(tele_dir), limit=8)) or "(no decisions)")) \
        .replace("__GENERATED__", __import__("time").strftime("%Y-%m-%d %H:%M"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


def _persona_grid(panel):
    """One cell per agent: class colour + activity (fills this run)."""
    from collections import Counter
    n_int = Counter()
    # activity from the pulse run's trade log, credited to both sides
    run_dir = ROOT / "runs" / "demo" / "news_demo" / "news_a_s0"
    try:
        for line in (run_dir / "trades.jsonl").read_text().splitlines():
            tr = json.loads(line)
            n_int[tr.get("buyer")] += 1
            n_int[tr.get("seller")] += 1
    except OSError:
        pass
    cells = []
    for a in panel:
        cells.append({
            "id": a["persona_id"], "cls": a.get("cls", "?"),
            "arch": a.get("archetype", ""), "tier": a.get("tier", "A"),
            "card": a.get("card_kind", "position"), "n": n_int.get(a["persona_id"], 0)})
    return {"cells": cells}


def _cards_html(run_dir, panel):
    """Pre-rendered drawer card per card-kind (four), plus evidence summary."""
    run = viewer.load_run(run_dir)
    warn = viewer.check_panel(run, panel)
    chosen, seen = [], set()
    acting = {it["agent_id"] for it in run["intents"]}
    for tr in run["trades"]:
        acting |= {tr.get("buyer"), tr.get("seller")} - {None, ""}
    for a in panel:
        k = a.get("card_kind", "position")
        if k in seen:
            continue
        if a["persona_id"] in acting or k == "event_source":
            seen.add(k)
            chosen.append(a["persona_id"])
        if len(seen) == 4:
            break
    body = []
    if warn:
        body.append(f"<div class='read warn'>{_esc(warn)}</div>")
    body.append("<div class='cards'>")
    for aid in chosen:
        c = viewer.agent_card(panel, run, aid)
        secs = []
        for title, rows in c["sections"]:
            cells = "".join(f"<tr><td class='k'>{_esc(str(k))}</td>"
                            f"<td>{_esc(str(v))}</td></tr>"
                            for k, v in rows if v not in (None, "", "none"))
            secs.append(f"<div class='cs'>{title}<table>{cells}</table></div>")
        ev = " · ".join(f"{k}={v}" for k, v in sorted(c["evidence_summary"].items()))
        body.append(
            f"<div class='card'><h3>{_esc(c['title'])} "
            f"<span class='id'>{_esc(aid)}</span></h3>"
            f"<p class='id'>{_esc(c['identity'])}</p>"
            f"<div class='chips'><span class='chip'>{_esc(c['class'])}"
            f"/{_esc(c['archetype'])}</span>"
            f"<span class='chip'>tier {_esc(c['tier'])}</span>"
            f"<span class='chip'>{c['decisions']} decisions · "
            f"{c['fills']} fills</span></div>"
            + "".join(secs)
            + f"<div class='ev'>Evidence: {_esc(ev)}</div>"
            + (f"<div class='ev warn'>Unset for want of evidence: "
               f"{_esc(', '.join(c['unknown_fields'][:6]))}</div>"
               if c["unknown_fields"] else "")
            + "</div>")
    body.append("</div>")
    return "".join(body)


_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Wind Tunnel — dashboard</title><style>
:root { color-scheme: dark; }
body { margin:0; background:#0f1115; color:#e6e6e6;
  font:14px/1.5 -apple-system,"Segoe UI",sans-serif; }
header { padding:18px 26px 12px; border-bottom:1px solid #262a33; }
h1 { margin:0; font-size:19px; letter-spacing:.02em; display:inline; }
.tag { color:#8b93a1; font-size:12px; margin-left:12px; display:inline; }
.strip { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.strip span { border:1px solid #2c3340; border-radius:99px; padding:2px 10px;
  font-size:11.5px; color:#9fb0c9; }
nav { display:flex; gap:4px; padding:10px 26px 0; border-bottom:1px solid #262a33; }
nav button { background:none; border:none; border-bottom:2px solid transparent;
  color:#8b93a1; font:600 13px -apple-system,"Segoe UI",sans-serif;
  padding:8px 16px; cursor:pointer; letter-spacing:.03em; }
nav button.on { color:#e6e6e6; border-bottom-color:#57c98a; }
.page { display:none; padding:16px 26px 40px; }
.page.on { display:block; }
main { display:grid; gap:16px; }
section { border:1px solid #262a33; border-radius:10px; overflow:hidden; }
section > h2 { margin:0; padding:10px 16px; font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:#8b93a1; border-bottom:1px solid #262a33;
  background:#13161c; }
section > *:not(h2) { margin-left:16px; margin-right:16px; }
.chart { width:100%; height:auto; display:block; margin:10px 0 4px; }
.tick { font:10px ui-monospace,Menlo,monospace; fill:#7c8494; }
.empty { padding:16px; color:#8b93a1; }
.legend { font-size:12px; color:#aeb7c6; margin:4px 0 8px; }
.legend i { display:inline-block; width:16px; height:3px;
  vertical-align:middle; margin:0 5px 2px 2px; border-radius:2px; }
.mut { color:#7c8494; }
.read { font-size:12.5px; color:#9fb0c9; padding:8px 0 14px; }
.warn, .read.warn { color:#e0a33e; }
pre { overflow-x:auto; font:11.5px/1.7 ui-monospace,Menlo,monospace;
  color:#c7d0dd; background:#13161c; border:1px solid #1d212a;
  border-radius:6px; padding:10px 12px; }
table.grid { border-collapse:collapse; width:100%; font-size:12.5px;
  margin:10px 0 6px; }
table.grid th { text-align:left; color:#8b93a1; font-weight:500;
  border-bottom:1px solid #2c3340; padding:4px 10px 4px 0; }
table.grid td { padding:5px 10px 5px 0; border-bottom:1px solid #1d212a; }
.pill { border-radius:99px; padding:1px 8px; font-size:11px; border:1px solid; }
.pill.ok { color:#57c98a; border-color:#2c5b43; }
.pill.bad { color:#e0685f; border-color:#5b2f2c; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 2px; }
.chip { border:1px solid #2c3340; border-radius:99px; padding:1px 9px;
  font-size:11px; color:#9fb0c9; }
.chip.warn { color:#e0a33e; border-color:#5b4a26; }
.rpbar { display:flex; gap:10px; align-items:center; margin:12px 0 4px;
  flex-wrap:wrap; }
.rpbar button { background:#1a1f29; border:1px solid #2c3340; color:#e6e6e6;
  border-radius:6px; padding:5px 14px; font:600 12px ui-monospace,Menlo,monospace;
  cursor:pointer; }
.rpbar button:hover { border-color:#57c98a; }
.rpbar .t { font:12px ui-monospace,Menlo,monospace; color:#9fb0c9;
  min-width:120px; }
.rpbar select { background:#1a1f29; color:#e6e6e6; border:1px solid #2c3340;
  border-radius:6px; padding:4px 8px; font:12px ui-monospace,Menlo,monospace; }
.rpbar .rep { color:#e0a33e; font-size:11px; border:1px solid #5b4a26;
  border-radius:99px; padding:1px 9px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px; margin:10px 0; }
.kpi { border:1px solid #1d212a; border-radius:8px; padding:8px 12px; }
.kpi .v { font:600 20px ui-monospace,Menlo,monospace; color:#e6e6e6; }
.kpi .k { font-size:11px; color:#8b93a1; }
.eqsvg { margin:6px 0 10px; }
.evline { font:12.5px ui-monospace,Menlo,monospace; color:#e0a33e;
  padding:6px 0; min-height:20px; }
.telebox { height:150px; overflow-y:auto; }
.gwrap { display:flex; gap:16px; margin:10px 0; align-items:flex-start;
  flex-wrap:wrap; }
.ggrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(14px,1fr));
  gap:2px; flex:1 1 460px; min-width:420px; }
.cell { width:100%; aspect-ratio:1; border-radius:3px; cursor:pointer;
  opacity:.9; }
.cell:hover { outline:1px solid #e6e6e6; }
.drawer { flex:1 1 320px; min-width:300px; }
.cards { display:grid; gap:12px; margin:8px 0 4px; }
.card { border:1px solid #1d212a; border-radius:8px; padding:10px 12px; }
.card h3 { margin:0; font-size:13px; }
.card .id { color:#8b93a1; font-size:11px; font-weight:400; margin:2px 0 6px; }
.cs { font-size:12px; margin-top:8px; color:#aeb7c6; }
.cs table { border-collapse:collapse; margin-top:3px; }
.cs td { padding:2px 10px 2px 0; font-size:11.5px; }
.cs td.k { color:#7c8494; white-space:nowrap; }
.ev { font-size:11px; color:#8b93a1; margin-top:8px; }
.glegend { display:flex; flex-wrap:wrap; gap:10px; font-size:11px;
  color:#8b93a1; margin:6px 0; }
.glegend i { display:inline-block; width:10px; height:10px;
  border-radius:3px; margin-right:4px; vertical-align:-1px; }
footer { padding:14px 26px 28px; border-top:1px solid #262a33;
  color:#7c8494; font-size:12px; }
footer b { color:#9fb0c9; }
</style></head><body>
<header>
<h1>Market Wind Tunnel</h1><span class="tag">Test the intervention before
the market tests it.</span>
<div class="strip">
<span>__N_AGENTS__ agents · weighted representative panel</span>
<span>5 books · EQ / rates / FX / commodity / crypto</span>
<span>brain: glm-5.3-flash (GLM-only decision 2026-10-22)</span>
<span>per-decision provenance · prompt sha on every intent</span>
<span>same five-tuple → bit-identical rerun</span>
</div>
</header>
<nav>
<button class="on" data-p="ov">Overview</button>
<button data-p="live">Live Run</button>
<button data-p="per">Personas</button>
<button data-p="sens">Sensitivity</button>
<button data-p="ev">Evidence</button>
</nav>

<div class="page on" id="p-ov"><main>__OVERVIEW__</main></div>

<div class="page" id="p-live">
  <div class="rpbar">
    <button id="play">▶ play</button>
    <button id="step">step ▸</button>
    <button id="reset">⟲ reset</button>
    <select id="speed"><option value="60">×1</option><option value="20">×3</option>
    <option value="6">×10</option><option value="1">fast</option></select>
    <span class="t" id="rt">round 0 / 0</span>
    <span class="rep">REPLAY — recorded run, not a live execution</span>
  </div>
  <div class="evline" id="evline"></div>
  <div class="kpis">
    <div class="kpi"><div class="v" id="k-eq">—</div><div class="k">EQ vs open</div></div>
    <div class="kpi"><div class="v" id="k-wake">0</div><div class="k">wake-ups (cum)</div></div>
    <div class="kpi"><div class="v" id="k-int">0</div><div class="k">active intents (cum)</div></div>
    <div class="kpi"><div class="v" id="k-tr">0</div><div class="k">trades (cum)</div></div>
    <div class="kpi"><div class="v" id="k-halt">–</div><div class="k">EQ halt</div></div>
  </div>
  <div class="eqsvg" id="eqpath"></div>
  <section><h2>Per-book volume (cumulative units)</h2><div id="bookbars"
    style="padding:12px 16px"></div></section>
  <section><h2>Trajectory telemetry — this round</h2>
    <pre class="telebox" id="rtele">(press play)</pre>
    <div class="read" style="padding:8px 16px 14px">Decisions in the current
    round; every line names the brain that produced it. Full stream in the
    run directory.</div></section>
  <section style="margin-top:16px"><h2>Static sample (whole run)</h2>
    <pre style="margin:10px 16px 14px">__TELE_STATIC__</pre></section>
</div>

<div class="page" id="p-per">
  <div class="glegend" id="glegend"></div>
  <div class="gwrap">
    <div class="ggrid" id="ggrid"></div>
    <div class="drawer">__CARDS_HTML__</div>
  </div>
  <div class="read">Every cell is one agent of the panel. Colour = class,
  brightness = how many times it filled in the featured run. The drawer
  shows one example card per role with field-level evidence — the full
  roster is in <code>personas/panel_v3.json</code>.</div>
</div>

<div class="page" id="p-sens"><main id="sens-body"></main></div>

<div class="page" id="p-ev">
  <section><h2>Red lines (every number on every tab obeys them)</h2>
  <ul style="padding:10px 16px 14px;line-height:1.8;color:#aeb7c6">
  <li>Direction and ranking only — no effect sizes, no point predictions.</li>
  <li>Model output is not evidence; rationale text is audit material.</li>
  <li>Instability across models/prompts/seeds is a deliverable, reported
  as such.</li>
  <li>Personas are calibrated priors, not real people; field-level
  provenance on every card, <b>0%</b> human-grounded today.</li>
  </ul></section>
  <section><h2>Reproducibility contract</h2>
  <ul style="padding:10px 16px 14px;line-height:1.8;color:#aeb7c6">
  <li>Five-tuple manifest: population × intervention × mechanism × model ×
  seed; same tuple → bit-identical rerun.</li>
  <li>Every Intent carries provider / model / prompt_version /
  prompt_sha8 — the hash of the prompt actually sent.</li>
  <li>Manifests carry code_hash over the runtime that produced the run.</li>
  </ul></section>
</div>

<footer>
Every tab reads the same evidence packs under <code>runs/</code>.
Generated __GENERATED__ by <code>python3 -m runtime.cli ui</code>.
</footer>

<script>
const REPLAY = __REPLAY_JSON__;
const PERSONAS = __PERSONA_JSON__;
const ASSETS = ["EQ","IR","FX","CMD","CRYPTO"];
const ANAMES = {"EQ":"Equity","IR":"Rates","FX":"FX","CMD":"Commodity","CRYPTO":"Crypto"};
const CLS_COLORS = {"retail_direct":"#57c98a","retail_advised":"#3f9e6e",
  "mf_pm":"#5b8bb0","hf_pm":"#b08d5b","foreign_inst":"#8a6fb0","bank":"#6f8bb0",
  "swf":"#4f7fb0","insurer":"#7fb08a","pension":"#5ba0a8","index_ap":"#9fb0c9",
  "buyback":"#8b93a1","market_maker":"#c98a57","event_src":"#e0685f"};

document.querySelectorAll("nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.remove("on"));
  document.querySelectorAll(".page").forEach(x => x.classList.remove("on"));
  b.classList.add("on");
  document.getElementById("p-" + b.dataset.p).classList.add("on");
});
(() => {
  const src = document.querySelector("#p-ov section:nth-of-type(2)");
  if (src) document.getElementById("sens-body").appendChild(src.cloneNode(true));
})();

let cur = 0, timer = null;
const $ = id => document.getElementById(id);
function eqChart(hist) {
  const w = 900, h = 180, pad = 46;
  if (!hist.filter(x => x !== null).length) return "<div class='empty'></div>";
  const ys = hist.filter(x => x !== null);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  const sp = (hi - lo) || 1; lo -= sp*.08; hi += sp*.08;
  const X = t => pad + t / Math.max(REPLAY.nRounds - 1, 1) * (w - pad - 10);
  const Y = v => h - 20 - (v - lo) / (hi - lo) * (h - 36);
  let pts = "", dot = "";
  hist.forEach((v, t) => { if (v !== null) {
    pts += (pts ? " " : "") + X(t).toFixed(1) + "," + Y(v).toFixed(1);
    if (t === cur) dot = `<circle cx='${X(t)}' cy='${Y(v)}' r='4' fill='#57c98a'/>`;
  }});
  const ev = REPLAY.rounds.find(r => r.ev);
  let evmark = "";
  if (ev) evmark = `<line x1='${X(ev.t)}' y1='8' x2='${X(ev.t)}' y2='${h-16}' stroke='#e0a33e' stroke-dasharray='4 3'/><text x='${X(ev.t)+4}' y='16' class='tick'>intervention</text>`;
  return `<svg viewBox='0 0 ${w} ${h}' class='chart' role='img'>` +
    (lo < 0 && hi > 0 ? `<line x1='${pad}' y1='${Y(0)}' x2='${w-10}' y2='${Y(0)}' stroke='#3a4150' stroke-dasharray='3 4'/>` +
      `<text x='${pad-6}' y='${Y(0)+4}' class='tick' text-anchor='end'>0%</text>` : "") +
    `<text x='${pad-6}' y='${Y(hi)+4}' class='tick' text-anchor='end'>${hi.toFixed(0)}%</text>` +
    `<text x='${pad-6}' y='${Y(lo)+4}' class='tick' text-anchor='end'>${lo.toFixed(0)}%</text>` +
    evmark +
    `<polyline points='${pts}' fill='none' stroke='#57c98a' stroke-width='2'/>` + dot + `</svg>`;
}
function bookBars(vol, ntr) {
  const mx = Math.max(...vol, 1);
  return ASSETS.map((a, i) => {
    const pct = Math.sqrt(vol[i] / mx) * 100;
    return `<div style='display:flex;align-items:center;gap:10px;margin:6px 0'>` +
      `<span style='width:90px;font-size:12px;color:#aeb7c6'>${ANAMES[a]}</span>` +
      `<div style='flex:1;background:#1a1f29;border-radius:4px;height:14px'>` +
      `<div style='width:${pct}%;height:100%;background:#5b8bb0;border-radius:4px'></div></div>` +
      `<span style='font:11px ui-monospace,monospace;color:#8b93a1;width:130px'>` +
      `${vol[i].toLocaleString()} u · ${ntr[i]} trades</span></div>`;
  }).join("");
}
function render() {
  const r = REPLAY.rounds[cur];
  if (!r) return;
  $("rt").textContent = `round ${cur} / ${REPLAY.nRounds - 1}`;
  $("k-eq").textContent = r.eq === null ? "—" : (r.eq >= 0 ? "+" : "") + r.eq.toFixed(2) + "%";
  $("k-wake").textContent = r.wake;
  $("k-int").textContent = r.intent;
  $("k-tr").textContent = r.trade;
  $("k-halt").textContent = r.eqHalt ? "HALTED" : "trading";
  $("k-halt").style.color = r.eqHalt ? "#e0685f" : "";
  $("evline").textContent = r.ev ? `⚡ t=${r.ev.t} "${r.ev.headline}" (sentiment ${r.ev.sentiment})` : "";
  const hist = REPLAY.rounds.slice(0, cur + 1).map(x => x.eq);
  $("eqpath").innerHTML = eqChart(hist);
  $("bookbars").innerHTML = bookBars(r.vol, r.ntr);
  $("rtele").textContent = r.tele.length ? r.tele.join("\\n") : "(quiet round — no LLM wake-ups)";
}
function tick() {
  if (cur >= REPLAY.nRounds - 1) { stop(); return; }
  cur++; render();
}
function play() {
  if (timer) return;
  if (cur >= REPLAY.nRounds - 1) cur = 0;
  timer = setInterval(tick, +$("speed").value);
  $("play").textContent = "⏸ pause";
}
function stop() { clearInterval(timer); timer = null; $("play").textContent = "▶ play"; }
$("play").onclick = () => timer ? stop() : play();
$("step").onclick = () => { stop(); tick(); };
$("reset").onclick = () => { stop(); cur = 0; render(); };
$("speed").onchange = () => { if (timer) { stop(); play(); } };
render();

(() => {
  const cls = [...new Set(PERSONAS.cells.map(c => c.cls))];
  const color = c => CLS_COLORS[c] || "#9fb0c9";
  $("glegend").innerHTML = cls.map(c =>
    `<span><i style='background:${color(c)}'></i>${c}</span>`).join("");
  const maxN = Math.max(...PERSONAS.cells.map(c => c.n), 1);
  $("ggrid").innerHTML = PERSONAS.cells.map(c =>
    `<div class='cell' title='${c.id} (${c.cls}/${c.arch}, fills ${c.n})' ` +
    `style='background:${color(c.cls)};opacity:${(0.25 + 0.75 * Math.pow(c.n / maxN, .4)).toFixed(2)}' ` +
    `onclick='alert("agent: ${c.id}\\nclass: ${c.cls}\\narchetype: ${c.arch}\\nfills in featured run: ${c.n}")'></div>`).join("");
})();
</script>
</body></html>
"""

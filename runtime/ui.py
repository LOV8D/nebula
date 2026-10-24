"""Cross-run dashboard: one self-contained HTML page for the wind tunnel.

The per-run viewer (runtime/viewer.py) shows one run's evidence pack. This
module assembles the product view: the flagship A/B on the real brain, the
model x prompt sensitivity matrix, a five-book pulse, a telemetry sample and
role-aware agent cards — all read from existing run artifacts, nothing
recomputed. Static HTML by design: openable offline, emailable, no server,
no dependencies; the daemon-residency story stays about the runtime, not
the reporting layer.

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


# ---------------------------------------------------------------- page
def _fmt_pct(v):
    return f"{v * 100:+.1f}%"


def build(ab_root=None, sens_path=None, pulse_dir=None, tele_dir=None,
          out=None):
    ab_root = Path(ab_root) if ab_root else ROOT / "runs" / "demo2" / "news_demo"
    sens_path = Path(sens_path) if sens_path else ROOT / "runs" / "sensitivity" / "results.json"
    pulse_dir = Path(pulse_dir) if pulse_dir else ROOT / "runs" / "demo" / "news_demo" / "news_a_s0"
    tele_dir = Path(tele_dir) if tele_dir else ROOT / "runs" / "demo2" / "news_demo" / "news_b_s0"
    out = Path(out) if out else ROOT / "docs" / "dashboard.html"

    from .demo import _panel
    from . import viewer

    panel = _panel()
    n_agents = len(panel)
    panel_hash = viewer.population_hash(panel)
    secs = [
        _ab_section(ab_root, panel_hash=panel_hash),
        _sensitivity_section(sens_path),
        _pulse_section(pulse_dir),
        _telemetry_section(tele_dir),
        _cards_section(pulse_dir, panel),
    ]
    body = "".join(f"<section><h2>{_esc(t)}</h2>{b}</section>" for t, b in secs)

    page = _PAGE.format(n_agents=n_agents, body=body,
                        generated=__import__("time").strftime("%Y-%m-%d %H:%M"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Wind Tunnel — dashboard</title><style>
:root {{ color-scheme: dark; }}
body {{ margin:0; background:#0f1115; color:#e6e6e6;
  font:14px/1.5 -apple-system,"Segoe UI",sans-serif; }}
header {{ padding:22px 26px 16px; border-bottom:1px solid #262a33; }}
h1 {{ margin:0; font-size:19px; letter-spacing:.02em; }}
.tag {{ color:#8b93a1; font-size:12px; margin-top:4px; }}
.strip {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
.strip span {{ border:1px solid #2c3340; border-radius:99px; padding:3px 10px;
  font-size:11.5px; color:#9fb0c9; }}
main {{ padding:18px 26px 40px; display:grid; gap:16px; }}
section {{ border:1px solid #262a33; border-radius:10px; overflow:hidden; }}
section > h2 {{ margin:0; padding:10px 16px; font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:#8b93a1; border-bottom:1px solid #262a33;
  background:#13161c; }}
section > *:not(h2) {{ margin-left:16px; margin-right:16px; }}
.chart {{ width:100%; height:auto; display:block; margin:10px 0 4px; }}
.tick {{ font:10px ui-monospace,Menlo,monospace; fill:#7c8494; }}
.empty {{ padding:16px; color:#8b93a1; }}
.legend {{ font-size:12px; color:#aeb7c6; margin:4px 0 8px; }}
.legend i {{ display:inline-block; width:16px; height:3px;
  vertical-align:middle; margin:0 5px 2px 2px; border-radius:2px; }}
.mut, .legend .mut {{ color:#7c8494; }}
.read {{ font-size:12.5px; color:#9fb0c9; padding:8px 0 14px; }}
.read.warn, .warn {{ color:#e0a33e; }}
pre {{ overflow-x:auto; font:11.5px/1.7 ui-monospace,Menlo,monospace;
  color:#c7d0dd; background:#13161c; border:1px solid #1d212a;
  border-radius:6px; padding:10px 12px; }}
table.grid {{ border-collapse:collapse; width:100%; font-size:12.5px;
  margin:10px 0 6px; }}
table.grid th {{ text-align:left; color:#8b93a1; font-weight:500;
  border-bottom:1px solid #2c3340; padding:4px 10px 4px 0; }}
table.grid td {{ padding:5px 10px 5px 0; border-bottom:1px solid #1d212a; }}
.pill {{ border-radius:99px; padding:1px 8px; font-size:11px;
  border:1px solid; }}
.pill.ok {{ color:#57c98a; border-color:#2c5b43; }}
.pill.bad {{ color:#e0685f; border-color:#5b2f2c; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 2px; }}
.chip {{ border:1px solid #2c3340; border-radius:99px; padding:1px 9px;
  font-size:11px; color:#9fb0c9; }}
.chip.warn {{ color:#e0a33e; border-color:#5b4a26; }}
.smalls {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:12px; margin:8px 0 4px; }}
.small {{ border:1px solid #1d212a; border-radius:8px; padding:8px 10px; }}
.small h3 {{ margin:0 0 2px; font-size:12.5px; }}
.stats {{ font:11px ui-monospace,Menlo,monospace; color:#8b93a1; margin-top:4px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr));
  gap:12px; margin:8px 0 4px; }}
.card {{ border:1px solid #1d212a; border-radius:8px; padding:10px 12px; }}
.card h3 {{ margin:0; font-size:13px; }}
.card .id {{ color:#8b93a1; font-size:11px; font-weight:400; margin:2px 0 6px; }}
.cs {{ font-size:12px; margin-top:8px; color:#aeb7c6; }}
.cs table {{ border-collapse:collapse; margin-top:3px; }}
.cs td {{ padding:2px 10px 2px 0; font-size:11.5px; }}
.cs td.k {{ color:#7c8494; white-space:nowrap; }}
.ev {{ font-size:11px; color:#8b93a1; margin-top:8px; }}
footer {{ padding:14px 26px 28px; border-top:1px solid #262a33;
  color:#7c8494; font-size:12px; }}
footer b {{ color:#9fb0c9; }}
footer ul {{ margin:6px 0 10px; padding-left:18px; }}
</style></head><body>
<header>
<h1>Market Wind Tunnel</h1>
<div class="tag">Test the intervention before the market tests it.</div>
<div class="strip">
<span>{n_agents} agents · weighted representative panel</span>
<span>5 books · EQ / rates / FX / commodity / crypto</span>
<span>brain: glm-5.3-flash (GLM-only decision 2026-10-22)</span>
<span>per-decision provenance · prompt sha on every intent</span>
<span>same five-tuple → bit-identical rerun</span>
</div>
</header>
<main>{body}</main>
<footer>
<b>Red lines (every number above obeys them):</b>
<ul>
<li>Direction and ranking only — no effect sizes, no point predictions.</li>
<li>Model output is not evidence; rationale text is audit material.</li>
<li>Instability across models/prompts/seeds is a deliverable, reported
as such — see the sensitivity section.</li>
</ul>
Personas are calibrated priors, not real people — field-level provenance on
every card; 0% of persona attributes are human-grounded today.
Generated {generated} by <code>python3 -m runtime.cli ui</code>.
</footer></body></html>
"""

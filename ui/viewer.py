"""Read-only views over a run's evidence pack: the decision stream and the
per-agent card.

Two things convince a reviewer that a simulation is not a story generator:
seeing individual decisions scroll past with their provenance attached, and
being able to open one agent and check where every number came from. Both are
already in the JSONL; this module only renders them.

The stream reads OBS -> INTENT -> FILL. There is deliberately no reward
column: this runtime has no reward signal, and inventing one would be the
exact kind of borrowed vocabulary the plan warns about.

Cards are role-aware. An investor gets holdings, a market maker gets
inventory, a mandated vehicle gets its rulebook, and an event source gets the
headlines it published — the same template for all four would misrepresent
three of them.
"""
import html
import json
from collections import defaultdict
from pathlib import Path

CARD_TITLE = {
    "position": "Holdings card",
    "mandate": "Mandate card",
    "inventory": "Inventory card",
    "event_source": "Event-source card",
}


def _jsonl(run_dir, name):
    p = Path(run_dir) / f"{name}.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_run(run_dir):
    run_dir = Path(run_dir)
    manifest_p = run_dir / "manifest.json"
    summary_p = run_dir / "summary.json"
    return {
        "dir": run_dir,
        "manifest": json.loads(manifest_p.read_text()) if manifest_p.exists() else {},
        "summary": json.loads(summary_p.read_text()) if summary_p.exists() else {},
        "intents": _jsonl(run_dir, "intents"),
        "trades": _jsonl(run_dir, "trades"),
        "events": _jsonl(run_dir, "events"),
        "marks": _jsonl(run_dir, "marks"),
        "violations": _jsonl(run_dir, "violations"),
    }


def population_hash(panel):
    """Same digest the recorder stamps into a run manifest."""
    import hashlib
    return hashlib.md5(json.dumps(panel, sort_keys=True).encode()).hexdigest()[:10]


def check_panel(run, panel):
    """A run records only the hash of the population it used, not the panel
    itself. Joining a run to a different panel silently mislabels every card,
    so say so loudly instead of rendering a plausible lie."""
    recorded = (run.get("manifest", {}).get("five_tuple", {}) or {}).get("population")
    current = population_hash(panel)
    if recorded and recorded != current:
        return (f"population mismatch: this run was produced with panel "
                f"{recorded}, the panel on disk is {current}. Attributes shown "
                f"here may belong to a different agent. Re-run, or restore the "
                f"panel that made this run.")
    return ""


def positions(run):
    """Net quantity and cash flow per agent, reconstructed from the trade log.
    Derived, not recorded: the engine does not write per-agent books."""
    qty = defaultdict(lambda: defaultdict(float))
    cash = defaultdict(float)
    for tr in run["trades"]:
        buyer, seller = tr.get("buyer", ""), tr.get("seller", "")
        notional = tr["price"] * tr["qty"]
        if buyer:
            qty[buyer][tr["asset"]] += tr["qty"]
            cash[buyer] -= notional
        if seller:
            qty[seller][tr["asset"]] -= tr["qty"]
            cash[seller] += notional
    return qty, cash


def _last_event(events, t, asset):
    seen = None
    for e in events:
        if e["t"] <= t and (asset in e.get("assets", []) or not e.get("assets")):
            seen = e
    return seen


def _mark_move(marks, t, asset):
    """Return the last price move in bps for `asset` at or before round t."""
    series = [m for m in marks if m["asset"] == asset and m["t"] <= t]
    if len(series) < 2:
        return None
    prev, now = series[-2]["price"], series[-1]["price"]
    if not prev:
        return None
    return (now / prev - 1) * 1e4


def stream(run, limit=40, agent=None, asset=None, show_pass=False):
    """OBS -> INTENT -> FILL, one line per decision."""
    fills = defaultdict(list)
    for tr in run["trades"]:
        for who in (tr.get("buyer"), tr.get("seller")):
            if who:
                fills[(who, tr["t"], tr["asset"])].append(tr)
    lines = []
    for it in run["intents"]:
        if agent and it["agent_id"] != agent:
            continue
        if asset and it["asset"] != asset:
            continue
        if not show_pass and it.get("side", 0) == 0:
            continue
        t, aid, ast = it["t"], it["agent_id"], it["asset"]
        ev = _last_event(run["events"], t, ast)
        if ev:
            obs = f'news "{ev["headline"][:30]}…" s={ev["sentiment"]:+.1f}'
        else:
            mv = _mark_move(run["marks"], t, ast)
            obs = f"{ast} {mv:+.0f}bps" if mv is not None else f"{ast} no new info"
        side = {1: "buy", -1: "sell", 0: "pass"}.get(it.get("side", 0), "?")
        act = f"{side} {ast} {it['size_frac']:.3f} u{it['urgency']:.2f}"
        got = fills.get((aid, t, ast), [])
        if got:
            filled = sum(x["qty"] for x in got)
            px = sum(x["price"] * x["qty"] for x in got) / max(filled, 1e-9)
            fill = f"fill {filled:.4g}@{px:.2f}"
        else:
            fill = "no fill"
        brain = it.get("model") or it.get("provider") or "?"
        lines.append(f"t={t:<4} {aid:<20} {obs:<40} -> {act:<24} -> {fill:<20} "
                     f"{brain}/{it.get('prompt_version', '')}")
        if len(lines) >= limit:
            break
    return lines


def agent_card(panel, run, agent_id):
    """Role-aware card for one agent, with its evidence block attached."""
    who = next((a for a in panel if a["persona_id"] == agent_id), None)
    if who is None:
        raise SystemExit(f"no agent {agent_id!r} in the panel")
    kind = who.get("card_kind", "position")
    qty, cash = positions(run)
    n_intents = sum(1 for it in run["intents"] if it["agent_id"] == agent_id)
    n_trades = sum(1 for tr in run["trades"]
                   if agent_id in (tr.get("buyer"), tr.get("seller")))
    viol = [v for v in run["violations"] if v.get("agent_id") == agent_id]
    prov = who.get("provenance", {})
    by_kind = defaultdict(int)
    for rec in prov.values():
        by_kind[rec.get("evidence", "?")] += 1

    card = {
        "agent_id": agent_id,
        "kind": kind,
        "title": CARD_TITLE.get(kind, "Agent card"),
        "identity": who.get("identity_card", ""),
        "class": who.get("cls"),
        "archetype": who.get("archetype"),
        "tier": who.get("tier"),
        "decisions": n_intents,
        "fills": n_trades,
        "violations": [f"{v['kind']}: {v['detail']} ({v['action']})" for v in viol[:5]],
        "evidence_summary": dict(by_kind),
        "unknown_fields": who.get("unknown_fields", []),
        "sections": [],
    }

    if kind == "position":
        held = {k: round(v, 4) for k, v in qty.get(agent_id, {}).items() if abs(v) > 1e-9}
        card["sections"] = [
            ("Account", [
                ("budget", f"${who['budget_usd']:,.0f}"),
                ("cash flow this run", f"${cash.get(agent_id, 0.0):,.0f}"),
                ("holdings (net, from trade log)", held or "no fills this run"),
                ("starting allocation", who.get("start_weights") or "cash only"),
            ]),
            ("Constraints", [
                ("universe", ", ".join(who.get("universe") or []) or "none"),
                ("leverage cap", who.get("leverage_cap")),
                ("may short", who.get("can_short")),
                ("mandate", who.get("mandate") or "none"),
                ("stop loss", who.get("stop_loss", "none")),
            ]),
            ("Behaviour (priors, uncalibrated)", [
                ("attention/day", round(who["attention_per_day"], 3)),
                ("news beta", round(who["news_beta"], 3)),
                ("price beta", round(who["price_beta"], 3)),
                ("disposition", round(who["disposition"], 3)),
                ("herding", round(who["herding"], 3)),
                ("loss aversion", who["loss_aversion"]),
                ("frictions", ", ".join(who.get("frictions") or []) or "none"),
            ]),
        ]
    elif kind == "mandate":
        card["sections"] = [
            ("Rulebook", [
                ("mandate", who.get("mandate") or "none"),
                ("style", who.get("style") or "n/a"),
                ("target allocation", who.get("start_weights") or "n/a"),
                ("share of market flow", f"{who['flow_w']:.5f}"),
                ("leverage cap", who.get("leverage_cap")),
            ]),
            ("Execution", [
                ("acts through", "compiled policy (tier B) — no per-round LLM call"),
                ("fills this run", n_trades),
            ]),
        ]
    elif kind == "inventory":
        held = {k: round(v, 4) for k, v in qty.get(agent_id, {}).items() if abs(v) > 1e-9}
        card["sections"] = [
            ("Book", [
                ("assigned asset", who.get("mm_asset") or "n/a"),
                ("net inventory (from trade log)", held or "flat"),
                ("cash flow this run", f"${cash.get(agent_id, 0.0):,.0f}"),
                ("inventory cap proxy", f"${who['budget_usd']:,.0f}"),
            ]),
            ("Obligation", [
                ("quotes", "two-sided (tier C rule)"),
                ("leverage cap", who.get("leverage_cap")),
            ]),
        ]
    else:  # event_source
        role = who.get("meta_role")
        published = [e for e in run["events"] if e.get("source") == role]
        card["sections"] = [
            ("Role", [
                ("meta role", role or "n/a"),
                ("holds positions", "no — this agent only publishes events"),
            ]),
            ("Published this run", [
                (f"t={e['t']}", f'"{e["headline"]}" s={e["sentiment"]:+.2f} '
                                f'reach={e.get("impact", 1.0)}')
                for e in published
            ] or [("none", "no events from this source in this run")]),
        ]
    return card


def render_card(card, prov=None):
    out = [f"{card['title']} — {card['agent_id']}",
           f"  {card['identity']}",
           f"  class={card['class']} archetype={card['archetype']} tier={card['tier']}",
           f"  decisions={card['decisions']} fills={card['fills']}"]
    for title, rows in card["sections"]:
        out.append(f"  {title}:")
        for k, v in rows:
            out.append(f"    {k:<34} {v}")
    if card["violations"]:
        out.append("  Violations:")
        out += [f"    {v}" for v in card["violations"]]
    ev = ", ".join(f"{k}={v}" for k, v in sorted(card["evidence_summary"].items()))
    out.append(f"  Evidence: {ev}")
    if card["unknown_fields"]:
        out.append("  Unset for want of evidence: " + ", ".join(card["unknown_fields"]))
    return "\n".join(out)


# --- HTML -----------------------------------------------------------------
_CSS = """
:root { color-scheme: light dark; }
body { margin:0; background:#0f1115; color:#e6e6e6; font:14px/1.5 -apple-system,Segoe UI,sans-serif; }
header { padding:18px 22px; border-bottom:1px solid #262a33; }
h1 { margin:0 0 4px; font-size:17px; letter-spacing:.02em; }
.sub { color:#8b93a1; font-size:12px; }
.wrap { padding:18px 22px; display:grid; gap:18px; grid-template-columns:1fr; }
@media (min-width:1100px){ .wrap{ grid-template-columns:1.35fr .9fr; } }
section { border:1px solid #262a33; border-radius:8px; overflow:hidden; }
section > h2 { margin:0; padding:10px 14px; font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:#8b93a1; border-bottom:1px solid #262a33; }
pre { margin:0; padding:12px 14px; overflow-x:auto; font:12px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace; }
.card { padding:12px 14px; border-bottom:1px solid #1d212a; }
.card:last-child { border-bottom:none; }
.card h3 { margin:0 0 2px; font-size:13px; }
.card .id { color:#8b93a1; font-size:11px; margin-bottom:8px; }
table { border-collapse:collapse; width:100%; font-size:12px; }
td { padding:2px 8px 2px 0; vertical-align:top; }
td.k { color:#8b93a1; white-space:nowrap; width:42%; }
.kindtag { display:inline-block; padding:1px 7px; border-radius:99px; font-size:10px;
  letter-spacing:.06em; text-transform:uppercase; border:1px solid #3a4150; color:#9fb0c9; }
.warn { color:#e0a33e; }
.note { padding:10px 14px; color:#8b93a1; font-size:12px; border-top:1px solid #1d212a; }
"""


def _tbl(rows):
    cells = "".join(
        f"<tr><td class='k'>{html.escape(str(k))}</td>"
        f"<td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    return f"<table>{cells}</table>"


def write_html(run, panel, out_path, n_lines=60, agents=None):
    m = run["manifest"]
    five = m.get("five_tuple", {})
    model = five.get("model", {})
    if agents is None:  # one of each card kind, so every layout is exercised
        agents, seen = [], set()
        acting = {it["agent_id"] for it in run["intents"]}
        for a in panel:
            k = a["card_kind"]
            if k in seen:
                continue
            if k == "position" and a["persona_id"] not in acting:
                continue
            seen.add(k)
            agents.append(a["persona_id"])
    cards = []
    for aid in agents:
        c = agent_card(panel, run, aid)
        body = "".join(f"<h4 style='margin:10px 0 2px;font-size:12px;color:#c9d1dc'>"
                       f"{html.escape(t)}</h4>{_tbl(rows)}"
                       for t, rows in c["sections"])
        ev = ", ".join(f"{k}={v}" for k, v in sorted(c["evidence_summary"].items()))
        unk = (f"<div class='warn' style='margin-top:8px;font-size:11px'>"
               f"unset for want of evidence: {html.escape(', '.join(c['unknown_fields']))}</div>"
               if c["unknown_fields"] else "")
        vio = (f"<div class='warn' style='margin-top:6px;font-size:11px'>"
               f"violations: {html.escape('; '.join(c['violations']))}</div>"
               if c["violations"] else "")
        cards.append(
            f"<div class='card'><span class='kindtag'>{html.escape(c['kind'])}</span>"
            f"<h3 style='margin-top:6px'>{html.escape(c['title'])} — "
            f"{html.escape(c['agent_id'])}</h3>"
            f"<div class='id'>{html.escape(c['identity'])}</div>"
            f"<div class='id'>decisions {c['decisions']} · fills {c['fills']} · "
            f"evidence {html.escape(ev)}</div>"
            f"{body}{vio}{unk}</div>")

    lines = stream(run, limit=n_lines)
    warn = check_panel(run, panel)
    banner = (f"<div class='note warn' style='padding:10px 22px;border-top:none;"
              f"border-bottom:1px solid #262a33'>{html.escape(warn)}</div>"
              if warn else "")
    doc = f"""<!doctype html><meta charset="utf-8">
<title>Wind tunnel — {html.escape(m.get('run_id', 'run'))}</title>
<style>{_CSS}</style>
<header>
  <h1>Market Wind Tunnel — run {html.escape(m.get('run_id', '?'))}</h1>
  <div class="sub">
    population {html.escape(str(five.get('population', '?')))} ·
    intervention {html.escape(str(five.get('intervention', '?')))} ·
    model {html.escape(str(model.get('model_id', '?')))} / prompt
    {html.escape(str(model.get('prompt_version', '?')))} ·
    seed {html.escape(str(five.get('seed', '?')))} ·
    {html.escape(str(m.get('n_agents', '?')))} agents ·
    created {html.escape(str(m.get('created', '?')))}
  </div>
</header>
{banner}
<div class="wrap">
  <section>
    <h2>Decision stream — obs &rarr; intent &rarr; fill</h2>
    <pre>{html.escape(chr(10).join(lines)) or 'no decisions in this run'}</pre>
    <div class="note">Every line is one recorded decision from
      <code>intents.jsonl</code>, matched to its fill in <code>trades.jsonl</code>.
      No reward column: this runtime has no reward signal.</div>
  </section>
  <section>
    <h2>Agent cards — one per role</h2>
    {''.join(cards)}
    <div class="note">Cards are rendered from the panel's own evidence block.
      Fields with no evidence stay unset and are listed rather than filled in.</div>
  </section>
</div>
"""
    Path(out_path).write_text(doc)
    return out_path

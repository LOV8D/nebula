"""Agent behaviors: attention gating, Tier-C rules, Tier-B policies.

Attention gating is behavior modeling first, compute saving second: an
agent wakes on (a) news relevant to its universe x news_beta, (b) price
moves on its book x price_beta when exposed, (c) its own Poisson attention
budget. Wake => one Intent (Tier A via the LLM gateway, Tier B via the
compiled policy below). Tier-C agents run every round without cognition.
"""
import math
import random
from .types import Intent

WAKE_NEWS = 0.35          # news_beta*impact above this => wake
WAKE_PRICE = 1.8          # |ret|/sigma above this x price_beta prob => wake
PASS_THROUGH_POLICY = True  # Tier-B personas decide locally, no LLM call


def wakes(persona, ctx, rng):
    """Attention gate. Returns True if the agent thinks this round."""
    uni = set(persona["universe"])
    for e in ctx["events"]:
        if set(e["assets"]) & uni and e["impact"] * persona["news_beta"] >= WAKE_NEWS:
            return True
    for a in uni:
        z = ctx["sigma_z"].get(a, 0.0)
        exposed = ctx["positions"].get(a, 0.0) != 0.0 or a in ctx.get("watch", ())
        if abs(z) > WAKE_PRICE and exposed and rng.random() < persona["price_beta"]:
            return True
    lam = persona["attention_per_day"] / max(1, ctx["rounds_per_day"])
    return rng.random() < lam


def build_ctx(persona, world, t):
    """Decision-context digest: only what the persona can actually see."""
    evs = [e for e in world.events_at(t) if set(e.assets) & set(persona["universe"])]
    acc = world.accounts[persona["persona_id"]]
    rets, day, pnl, sz = {}, {}, {}, {}
    for a in persona["universe"]:
        m = world.marks[a]
        rets[a] = (m.price / m.prev_price - 1) * 1e4 if m.prev_price else 0.0
        day[a] = m.price / m.day_open - 1 if m.day_open else 0.0
        pos = acc.positions.get(a, 0.0)
        pnl[a] = (m.price / acc.cost_basis.get(a, m.price) - 1) if pos else 0.0
        r = m.price / m.prev_price - 1 if m.prev_price else 0.0
        sz[a] = r / max(m.sigma, 1e-6)
    ctx = dict(t=t, events=[vars(e) for e in evs], rets_bps=rets, day_ret=day,
               pnl_frac=pnl, positions=acc.positions, rounds_per_day=world.rounds_per_day,
               sigma_z=sz,
               fee_note=world.fee_note(t) if hasattr(world, "fee_note") else None)
    return ctx


# ---------------------------------------------------------------- Tier B
def tier_b_policy(persona, ctx, rng):
    """Compiled routine reactions — same signature as the LLM path, no model.

    Hand-written priors in the demo; Phase 2 replaces these with policies
    distilled from real-person trajectories (plan §5).
    """
    uni = persona["universe"]
    if not uni:
        return None
    evs = ctx["events"]
    news = {a: 0.0 for a in uni}
    for e in evs:
        for a in e["assets"]:
            if a in news:
                news[a] += e["sentiment"] * e["impact"]
    # scheduled rebalance for slow classes
    if persona["cls"] in ("retail_advised",):
        if not evs and rng.random() < 0.05:
            return _intent(persona, uni[0], 1, 0.1, 0.1, "scheduled contribution", rng)
    asset = max(news, key=lambda a: abs(news[a]))
    mr_styles = {"value", "bond", "balanced", "swf", "bank"}
    s = persona["news_beta"] * news[asset]
    mom = ctx["rets_bps"].get(asset, 0.0) / 1e4
    if abs(mom) > 0.0005:
        s += persona["herding"] * mom * 70.0
    if persona.get("style") in mr_styles:
        s -= mom * 150.0
    for a in uni:
        if ctx["day_ret"].get(a, 0) < persona.get("stop_loss", -9):
            return _intent(persona, a, -1, 0.9, 0.95, "stop-loss", rng)
        pnl = ctx["pnl_frac"].get(a, 0)
        if pnl > 0.05 and rng.random() < persona["disposition"]:
            return _intent(persona, a, -1, 0.35, 0.4, "disposition: sell winner", rng)
        if pnl < -0.15 and rng.random() < persona["disposition"] * 0.5:
            return _intent(persona, a, -1, 0.4, 0.5, "cut loser", rng)
    if abs(s) < 0.2:
        return None
    side = 1 if s > 0 else -1
    size = min(0.5, abs(s) * (1.2 - persona["risk_aversion"]))
    return _intent(persona, asset, side, max(0.03, size), 0.3 + abs(s) * 0.45,
                   f"policy signal {s:.2f}", rng)


def _intent(persona, asset, side, size, urg, why, rng):
    size = max(0.0, min(1.0, size * rng.lognormvariate(0, 0.25)))
    return Intent(persona["persona_id"], asset, side, size,
                  max(0.0, min(1.0, urg * rng.lognormvariate(0, 0.2))),
                  why, provider="tierB", model="compiled-policy-v1",
                  prompt_version="policy")


# ---------------------------------------------------------------- Tier C
def market_maker_quotes(agent_id, asset, world, rng, cap_notional=8e6):
    """Two-sided limit quotes each round. Spread widens with inventory; once
    inventory exceeds its cap the MM stops quoting the accumulating side —
    a one-sided crowd then finds NO counterparty and price stops ratcheting
    (the physically correct call-auction behavior), instead of walking the
    book forever."""
    from .types import Order
    from . import matching
    m = world.marks[asset]
    acc = world.accounts[agent_id]
    inv = acc.positions.get(asset, 0.0)
    ref = m.mm_ref if m.mm_ref else (m.price or world.assets0[asset])
    cap_qty = cap_notional / ref
    spread_bps = 6.0 + 16.0 * abs(inv) / max(cap_qty, 1e-9)
    half = ref * spread_bps / 2e4
    # inventory skew: shift the quote center so accumulated inventory is
    # shed through price — this manufactures two-sided flow in thin books
    center = ref * (1 - 0.02 * max(-1.5, min(1.5, inv / max(cap_qty, 1e-9))))
    qty = cap_qty * rng.uniform(0.7, 1.0)
    # tick constraint (TSP-style): quotes must land on the increment grid,
    # bid floored / ask ceiled so the pair never collapses inward; if the
    # grid eats the whole spread, push the ask one tick above the bid
    tick = world.tick.get(asset)
    if tick:
        bid = matching.round_tick(center - half, tick, side="buy")
        ask = matching.round_tick(center + half, tick, side="sell")
        if ask <= bid:
            ask = round(bid + tick, 10)
    else:
        bid, ask = round(center - half, 6), round(center + half, 6)
    out = []
    if inv <= cap_qty:                       # room to buy => post bid
        out.append(Order(asset, agent_id, 1, qty, bid, world.t, "rule"))
    if inv >= -cap_qty:                      # room to sell => post ask
        out.append(Order(asset, agent_id, -1, qty, ask, world.t, "rule"))
    return out


def passive_flows(world, t):
    """Mechanical flows every round: index/AP, pension, insurer, buyback,
    plus the synthetic FX/CMD/CRYPTO flow desks (see engine.World)."""
    from .types import Order
    out = []
    for pid, a in world.flow_desks.items():
        notional = world.agent_rng[pid].gauss(0, 2.5e6)
        if abs(notional) > 2e4:
            px = world.marks[a].price or world.assets0[a]
            out.append(Order(a, pid, 1 if notional > 0 else -1,
                             abs(notional) / px, None, t, "policy"))
    for p in world.policy_personas:
        acc, style = world.accounts[p["persona_id"]], p["style"]
        eq, ir = world.marks["EQ"].price or world.assets0["EQ"], world.marks["IR"].price or world.assets0["IR"]
        if p["cls"] == "index_ap":
            day = t // max(1, world.rounds_per_day)
            drift = world._idx_drift.get((p["persona_id"], day))
            if drift is None:
                drift = world.agent_rng[p["persona_id"]].gauss(0, 0.0015)  # ~±15bps AUM/day
                world._idx_drift[(p["persona_id"], day)] = drift
            for a, w, px in (("EQ", 0.9 if style == "eq" else 0.0, eq),
                             ("IR", 0.9 if style == "ir" else 0.0, ir)):
                if w <= 0:
                    continue
                notional = p["budget_usd"] * w * drift / max(1, world.rounds_per_day)
                if abs(notional) > 1000:
                    out.append(Order(a, p["persona_id"], 1 if notional > 0 else -1,
                                     abs(notional) / px, None, t, "policy"))
        elif p["cls"] == "pension" and t % world.rounds_per_day == world.rounds_per_day - 1:
            tgt = {"EQ": 0.6, "IR": 0.4}
            equity = acc.equity(world)
            for a, px in (("EQ", eq), ("IR", ir)):
                want = equity * tgt[a] / px
                d = want - acc.positions.get(a, 0.0)
                if abs(d) * px > equity * 0.01:
                    out.append(Order(a, p["persona_id"], 1 if d > 0 else -1,
                                     abs(d) * 0.9, None, t, "policy"))
        elif p["cls"] == "insurer" and t % (world.rounds_per_day * 5) == 0:
            tgt = {"EQ": 0.2, "IR": 0.8}
            equity = acc.equity(world)
            for a, px in (("EQ", eq), ("IR", ir)):
                want = equity * tgt[a] / px
                d = want - acc.positions.get(a, 0.0)
                if abs(d) * px > equity * 0.05:
                    out.append(Order(a, p["persona_id"], 1 if d > 0 else -1,
                                     abs(d) * 0.5, None, t, "policy"))
        elif p["cls"] == "buyback":
            daily = p["budget_usd"] / 60.0  # ~quarter program spread over 60 days
            per_round = daily / world.rounds_per_day
            px = eq
            if px:
                out.append(Order("EQ", p["persona_id"], 1, per_round / px,
                                 round(px * 1.0005, 6), t, "policy"))
    return out


def sigma_ewma(prev, ret, lam=0.97):
    return math.sqrt(lam * prev * prev + (1 - lam) * ret * ret)

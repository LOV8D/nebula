"""Execution wrapper + validators: Intent -> legal Order.

The cognitive layers never touch the order format. This module enforces
budget, leverage, mandate (asset universe), minimum size, halt rules and
the persona's reaction-delay distribution, and records every violation —
this is BP validation layer 2 (setting compliance).
"""
import random
from . import matching
from .types import Order, Violation, BUY, SELL


def wrap_intent(intent, persona, world, t, rng, out_orders, violations, pending):
    """Validate + convert an Intent; orders may land in the pending-delay queue."""
    aid = persona["persona_id"]
    if intent.side == 0 or intent.size_frac <= 0:
        return
    if intent.asset not in persona["universe"]:
        violations.append(Violation(t, aid, "mandate",
                              f"{intent.asset} not in universe {persona['universe']}", "dropped"))
        return
    if world.marks[intent.asset].halted:
        violations.append(Violation(t, aid, "halted",
                              f"{intent.asset} halted at t={t}", "deferred"))
        pending.append((t + 1, intent))          # retry next round
        return
    acc = world.accounts[aid]
    px = world.marks[intent.asset].price or world.assets0[intent.asset]
    equity = acc.equity(world)
    deployable = equity * intent.size_frac * persona.get("size_scale", 1.0)
    qty = deployable / px
    # budget / leverage: long exposure capped at equity * leverage_cap
    if intent.side == BUY:
        gross = sum(max(0.0, q) * (world.marks[a].price or world.assets0[a])
                    for a, q in acc.positions.items()) + qty * px
        cap = equity * persona["leverage_cap"]
        if gross > cap:
            room = max(0.0, cap - (gross - qty * px))
            if room < 100 / px:
                violations.append(Violation(t, aid, "budget",
                                      f"leverage cap {cap:.0f} would be exceeded", "dropped"))
                return
            violations.append(Violation(t, aid, "budget", "buy clipped to leverage cap", "clipped"))
            qty = room / px
    else:
        pos = acc.positions.get(intent.asset, 0.0)
        short_ok = persona.get("can_short", False)
        if qty > pos and not short_ok:
            if pos <= 1e-9:
                violations.append(Violation(t, aid, "budget",
                                      "sell with no position/shorting not allowed", "dropped"))
                return
            violations.append(Violation(t, aid, "budget", "sell clipped to position", "clipped"))
            qty = pos
    if qty * px < 100:
        return  # below minimum notional; not worth an order
    # behavioral noise on size
    qty *= rng.lognormvariate(0, 0.15)
    # order type: probabilistic crossing scaled by urgency — agents
    # sometimes pay the spread instead of always resting behind it
    if intent.urgency >= 0.7 or rng.random() < 0.22 * intent.urgency:
        limit = None
    else:
        off_bps = (1.0 - intent.urgency) * 20.0   # patient => passive limit
        limit = px * (1 - off_bps / 1e4) if intent.side == BUY else px * (1 + off_bps / 1e4)
        tick = world.tick.get(intent.asset)
        limit = matching.round_tick(limit, tick) if tick else round(limit, 6)
    lo, hi = persona.get("reaction_delay_rounds", [0, 1])
    delay = max(0, min(30, int(rng.triangular(lo, hi, max(lo, 1)))))
    o = Order(intent.asset, aid, intent.side, qty, limit, t, intent.provider)
    if delay == 0:
        out_orders.append(o)
    else:
        pending.append((t + delay, o))


def apply_trade(world, trade, fee_bps_retail):
    buyer, seller = world.accounts[trade.buyer], world.accounts[trade.seller]
    notional = trade.price * trade.qty
    old_q = buyer.positions.get(trade.asset, 0.0)
    old_cb = buyer.cost_basis.get(trade.asset)
    buyer.positions[trade.asset] = old_q + trade.qty
    buyer.cash -= notional
    if old_q >= 0:  # volume-weighted average cost on buys
        buyer.cost_basis[trade.asset] = ((old_cb or trade.price) * max(old_q, 0)
                                         + trade.price * trade.qty) / max(old_q + trade.qty, 1e-12)
    seller.positions[trade.asset] = seller.positions.get(trade.asset, 0.0) - trade.qty
    seller.cash += notional
    for acc, side_notional in ((buyer, notional), (seller, notional)):
        if acc.cls.startswith("retail") and fee_bps_retail:
            fee = side_notional * fee_bps_retail / 1e4
            acc.cash -= fee

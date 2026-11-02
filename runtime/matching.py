"""Per-asset batch call auction with a persistent book.

All orders of a round (fresh + carried-over resting limits) cross
simultaneously at a uniform clearing price: the price maximizing executed
volume, tie-broken toward the reference (previous clearing) price.
Unfilled limit orders are returned as residuals so the engine can rest
them on the book; unfilled market orders are dropped (a price-taker only
trades if the other side shows up).

Priority: price first, then pro-rata within a level in deterministic
(agent_id sorted) sequence for reproducibility.
"""
from .types import Order, Trade, BUY, SELL

INF = float("inf")


def round_tick(px, tick, side=None):
    """Snap a price to the quote-increment grid (TSP-style tick constraint).

    side=None rounds to the nearest tick; side=BUY/"buy" floors and
    side=SELL/"sell" ceils, so a two-sided quote can never collapse inward.
    tick falsy or non-positive => unchanged (no constraint)."""
    if not tick or tick <= 0 or px is None:
        return px
    side = {"buy": BUY, "sell": SELL}.get(side, side)
    import math
    n = px / tick
    if side == BUY:
        return round(math.floor(n + 1e-9) * tick, 10)
    if side == SELL:
        return round(math.ceil(n - 1e-9) * tick, 10)
    return round(round(n) * tick, 10)


def clear_round(orders, ref_price):
    """-> (trades, clearing_price, residual_orders, dropped_market_qty)."""
    if not orders:
        return [], ref_price, [], 0.0
    idx = {i: o for i, o in enumerate(orders)}
    rem = {i: o.qty for i, o in idx.items()}
    bids = sorted([i for i, o in idx.items() if o.side == BUY],
                  key=lambda i: (-(idx[i].limit if idx[i].limit is not None else INF),
                                 idx[i].agent_id, i))
    asks = sorted([i for i, o in idx.items() if o.side != BUY],
                  key=lambda i: ((idx[i].limit if idx[i].limit is not None else -INF),
                                 idx[i].agent_id, i))

    levels = sorted({o.limit for o in orders if o.limit is not None} | {ref_price})
    best_p, best_v = ref_price, 0.0
    for p in levels:
        v = min(_demand(idx, bids, p), _supply(idx, asks, p))
        if v > best_v + 1e-9 or (abs(v - best_v) <= 1e-9 and abs(p - ref_price) < abs(best_p - ref_price)):
            best_p, best_v = p, v

    fb = [i for i in bids if idx[i].limit is None or idx[i].limit >= best_p - 1e-12]
    fa = [i for i in asks if idx[i].limit is None or idx[i].limit <= best_p + 1e-12]
    trades, i, j = [], 0, 0
    while i < len(fb) and j < len(fa):
        b, a = fb[i], fa[j]
        q = min(rem[b], rem[a])
        if q > 1e-9:
            o_b, o_a = idx[b], idx[a]
            trades.append(Trade(o_b.asset, best_p, q, max(o_b.t, o_a.t), o_b.agent_id, o_a.agent_id))
        rem[b] -= q
        rem[a] -= q
        if rem[b] <= 1e-9:
            i += 1
        if rem[a] <= 1e-9:
            j += 1

    residual = [Order(idx[k].asset, idx[k].agent_id, idx[k].side, rem[k],
                      idx[k].limit, idx[k].t, idx[k].origin)
                for k in idx if idx[k].limit is not None and rem[k] > 1e-9]
    dropped = sum(rem[k] for k in idx if idx[k].limit is None)
    return trades, best_p, residual, dropped


def _demand(idx, bids, p):
    return sum(idx[i].qty for i in bids if idx[i].limit is None or idx[i].limit >= p - 1e-12)


def _supply(idx, asks, p):
    return sum(idx[i].qty for i in asks if idx[i].limit is None or idx[i].limit <= p + 1e-12)


def best_bid(residual):
    return max((o.limit for o in residual if o.side == BUY), default=None)


def best_ask(residual):
    return min((o.limit for o in residual if o.side != BUY), default=None)

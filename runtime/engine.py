"""World state + round loop: the resident runtime core.

One simulation round = one sim minute per asset. Round pipeline (plan §6):
events -> attention -> intents (Tier A/B/C) -> execution wrapper -> per-asset
batch call auctions -> settlement -> circuit-breaker checks -> recording.
Prices are fully endogenous: the only price inputs are the scenario's
starting marks (from the trigger-time snapshot in production, static
defaults in offline demos).
"""
import hashlib
import random
import time as _time
from dataclasses import dataclass, field
from .types import Order, Intent, MarketEvent, ASSETS
from . import matching, agents, execution
from .llm import LLMGateway

BOOK_TTL = 15   # resting limit orders live 15 rounds, then cancel


def _seed(run_seed, persona_id):
    """Stable per-agent RNG substream (hash() is salted — never use it here)."""
    return int(hashlib.sha256(f"{run_seed}:{persona_id}".encode()).hexdigest()[:12], 16)


@dataclass
class Mark:
    price: float = 0.0
    mm_ref: float = 0.0
    prev_price: float = 0.0
    day_open: float = 0.0
    sigma: float = 0.001          # per-round return std (EWMA)
    volume: float = 0.0
    best_bid: float = None
    best_ask: float = None
    halted: bool = False
    halt_rounds_left: int = 0


@dataclass
class Account:
    id: str
    cls: str
    cash: float
    positions: dict = field(default_factory=dict)
    cost_basis: dict = field(default_factory=dict)

    def equity(self, world):
        px = lambda a, p: (world.marks[a].price or world.assets0[a]) * p  # noqa: E731
        return self.cash + sum(px(a, q) for a, q in self.positions.items())


class World:
    def __init__(self, scenario, panel, gateway):
        self.sc = scenario
        self.gateway = gateway
        self.rounds_per_day = scenario["rounds_per_day"]
        self.days = scenario["days"]
        self.assets0 = {a: scenario["assets"][a]["start"] for a in ASSETS}
        self.vol0 = {a: scenario["assets"][a]["vol_bps"] / 1e4 for a in ASSETS}
        self.marks = {a: Mark(price=p, prev_price=p, day_open=p, mm_ref=p,
                              sigma=self.vol0[a])
                      for a, p in self.assets0.items()}
        self.t = 0
        self.accounts = {}
        self.personas, self.policy_personas, self.mm_personas = [], [], []
        for p in panel:
            self.accounts[p["persona_id"]] = Account(p["persona_id"], p["cls"], p["budget_usd"])
            if p["tier"] == "llm":
                self.personas.append(p)
            elif p["tier"] == "policy":
                self.policy_personas.append(p)
            elif p["tier"] == "rule":
                self.mm_personas.append(p)
        # per-agent RNG substreams kept OUTSIDE panel dicts (panel stays pure data)
        self.agent_rng = {p["persona_id"]: random.Random(_seed(scenario["seed"], p["persona_id"]))
                          for p in self.personas + self.policy_personas + self.mm_personas}
        self._idx_drift = {}
        # Synthetic flow desks: thin books (FX/CMD/CRYPTO) get a small
        # continuous two-sided flow so liquidity does not depend on whether
        # an event happened to wake their few LLM participants — mirrors the
        # ever-present non-event flow in real FX/commodity/crypto markets.
        self.flow_desks = {}
        for a in ("FX", "CMD", "CRYPTO"):
            pid = f"flowdesk-{a}"
            self.accounts[pid] = Account(pid, "flowdesk", 5e8)
            self.agent_rng[pid] = random.Random(_seed(scenario["seed"], pid))
            self.flow_desks[pid] = a
        self.book = {a: [] for a in ASSETS}
        self._trades_today = {}
        # Pre-populate starting positions: the snapshot is an EXISTING market.
        # Without this, day 1 is distorted by everyone allocating out of cash.
        from .personas import START_WEIGHTS
        for p in self.personas + self.policy_personas:
            acc = self.accounts[p["persona_id"]]
            for a, w in START_WEIGHTS.get(p["cls"], {}).items():
                if a in p["universe"]:
                    px0 = self.assets0[a]
                    acc.positions[a] = acc.cash * w / px0
                    acc.cost_basis[a] = px0
            invested = sum(q * self.assets0[a] for a, q in acc.positions.items())
            acc.cash -= invested
        self.events = [MarketEvent(**e) for e in scenario.get("events", [])]
        self._events_by_t = {}
        for e in self.events:
            self._events_by_t.setdefault(e.t, []).append(e)
        mech = scenario.get("mechanism", {})
        self.cb = mech.get("circuit_breaker", {"enabled": False})
        self.fee_bps_retail = mech.get("fee_bps_retail", 0.0)
        self._fee_note_t = min((e.t for e in self.events if any(
            "fee" in w for w in e.headline.lower().split())), default=None)

    # ------------------------------------------------------------------
    def events_at(self, t):
        return self._events_by_t.get(t, [])

    def fee_note(self, t):
        if self.fee_bps_retail and self._fee_note_t is not None and t >= self._fee_note_t:
            return (f"NOTE: your fund raised its per-transaction fee to "
                    f"{self.fee_bps_retail}bps, announced this round.")
        return None

    # ------------------------------------------------------------------
    def run(self, recorder):
        pending = []                       # [(effective_t, Order|Intent)]
        total_rounds = self.rounds_per_day * self.days
        wake_log = []
        for t in range(total_rounds):
            self.t = t
            if t % self.rounds_per_day == 0:
                for m in self.marks.values():
                    m.day_open = m.price
            evs = self.events_at(t)
            if evs:
                recorder.log_events(evs)
            if self.gateway.provider != "mock" and \
                    self.gateway.usage.get("consecutive_errors", 0) >= 40:
                raise RuntimeError(
                    f"brain endpoint down: {self.gateway.usage.get('consecutive_errors')}"
                    f" consecutive errors ({self.gateway.usage.get('error_detail')})"
                    " — aborting run instead of burning compute; fix .env / quota")

            orders, violations, intents = [], [], []
            # Tier C: market makers quote every round (no delay, latency edge)
            for p in self.mm_personas:
                if not self.marks[p["mm_asset"]].halted:
                    orders += agents.market_maker_quotes(
                        p["persona_id"], p["mm_asset"], self,
                        self.agent_rng[p["persona_id"]])
            # Tier B mechanical: index/pension/insurer/buyback flows
            orders += agents.passive_flows(self, t)
            # Tier A/B cognitive: attention-gated. Two-phase so all LLM calls
            # of a round fire concurrently: (1) collect who wakes and route
            # (LLM on novel rounds, compiled policy on routine rounds),
            # (2) dispatch, (3) process results deterministically.
            wake_n = 0
            day_idx = t // self.rounds_per_day
            llm_jobs, tierb_jobs = [], []
            for p in self.personas:
                rng = self.agent_rng[p["persona_id"]]
                # news wakes bypass satiation: a headline grabs even agents
                # that already finished their day's trading
                event_hit = any(
                    set(e.assets) & set(p["universe"])
                    and e.impact * p["news_beta"] >= agents.WAKE_NEWS
                    for e in evs)
                if not event_hit and self._trades_today.get(
                        (p["persona_id"], day_idx), 0) >= \
                        max(1.0, p["attention_per_day"]):
                    continue
                if event_hit or self._might_wake(p, t, rng):
                    ctx = agents.build_ctx(p, self, t)
                    if agents.wakes(p, ctx, rng):
                        wake_n += 1
                        novel = bool(ctx["events"]) or any(
                            ctx["day_ret"].get(a, 0.0) < p.get("stop_loss", -9) + 0.01
                            for a in p["universe"])
                        if novel:
                            # a failed LLM attempt still counts toward today's
                            # budget — otherwise error states re-wake every
                            # round and hammer the provider (observed death
                            # spiral: 8k error calls in one run)
                            self._trades_today[(p["persona_id"], day_idx)] = \
                                self._trades_today.get((p["persona_id"], day_idx), 0) + 1
                            llm_jobs.append((p, ctx, rng))
                        else:
                            tierb_jobs.append((p, agents.tier_b_policy(p, ctx, rng), rng))

            # concurrent dispatch (API providers; serial for the mock brain)
            llm_results = self.gateway.complete_many(llm_jobs)

            for (p, ctx, rng), raw in zip(llm_jobs, llm_results):
                if raw is None and self.gateway.provider != "mock":
                    fb = agents.tier_b_policy(p, ctx, rng)
                    if fb is not None:
                        fb.provider = "tierB-fallback"
                        fb.rationale = (fb.rationale or "") + " [llm unavailable]"
                    raw = fb
                self._take_intent(p, raw, t, rng, intents, orders, violations, pending)
            for p, raw, rng in tierb_jobs:
                self._take_intent(p, raw, t, rng, intents, orders, violations, pending)
            wake_log.append(wake_n)

            # due delayed orders / deferred intents
            still = []
            for pt, obj in pending:
                if pt <= t:
                    if isinstance(obj, Order):
                        if not self.marks[obj.asset].halted:
                            orders.append(obj)
                        else:
                            still.append((t + 1, obj))
                    elif isinstance(obj, Intent):
                        p = self._persona(obj.agent_id)
                        execution.wrap_intent(obj, p, self, t, self.agent_rng[obj.agent_id],
                                              orders, violations, still)
                else:
                    still.append((pt, obj))
            pending = still

            # auctions per asset: fresh orders + carried resting limits
            by_asset = {a: [] for a in ASSETS}
            for o in orders:
                by_asset[o.asset].append(o)
            for a in ASSETS:
                m = self.marks[a]
                if m.halted:
                    m.halt_rounds_left -= 1
                    if m.halt_rounds_left <= 0:
                        m.halted = False
                        recorder.log_mark(a, self, halted_resumed=True)
                    continue
                book = [o for o in self.book[a] if o.t >= t - BOOK_TTL]
                trades, px, residual, dropped = matching.clear_round(
                    by_asset[a] + book, m.price)
                if trades:
                    m.prev_price = m.price
                    m.price = px
                    ret = m.price / m.prev_price - 1 if m.prev_price else 0.0
                    m.sigma = agents.sigma_ewma(m.sigma, ret)
                    m.volume = sum(tr.qty for tr in trades)
                    for tr in trades:
                        execution.apply_trade(self, tr, self.fee_bps_retail)
                    recorder.log_trades(trades)
                else:
                    m.prev_price = m.price
                    m.volume = 0.0
                # rest unfilled limits (rule/MM quotes never persist —
                # they re-quote fresh each round)
                m.mm_ref = 0.90 * m.mm_ref + 0.10 * m.price
                self.book[a] = [o for o in residual if o.origin != "rule"]
                m.best_bid = matching.best_bid(residual)
                m.best_ask = matching.best_ask(residual)
                recorder.log_mark(a, self)
                self._check_breaker(a)
            recorder.log_intents(intents)
            recorder.log_violations(violations)
        return wake_log

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _take_intent(self, p, raw, t, rng, intents, orders, violations, pending):
        """Convert a decision (gateway dict or Tier-B Intent) into orders."""
        if raw is None:
            return
        if isinstance(raw, dict):            # gateway path
            d = dict(raw)
            it = Intent(d.get("agent_id", p["persona_id"]),
                        d.get("asset", "EQ"), d.get("side", 0),
                        d.get("size_frac", 0.0), d.get("urgency", 0.0),
                        d.get("rationale", ""), d.get("provider", ""),
                        d.get("model", ""), d.get("prompt_version", ""))
        else:                                # tier-B policy path
            it = raw
            d = vars(it)
        d["t"] = t
        intents.append(d)
        if it.side != 0:
            day_idx = t // self.rounds_per_day
            self._trades_today[(p["persona_id"], day_idx)] = \
                self._trades_today.get((p["persona_id"], day_idx), 0) + 1
        execution.wrap_intent(it, p, self, t, rng, orders, violations, pending)

    def _might_wake(self, p, t, rng):
        """Cheap pre-filter so build_ctx (dict work) only runs on candidates."""
        uni = set(p["universe"])
        for e in self.events_at(t):
            if set(e.assets) & uni and e.impact * p["news_beta"] >= agents.WAKE_NEWS:
                return True
        lam = p["attention_per_day"] / max(1, self.rounds_per_day)
        if rng.random() < lam * 6:      # widen net; full check in wakes()
            return True
        for a in uni:
            m = self.marks[a]
            z = abs(m.price / m.prev_price - 1) / max(m.sigma, 1e-6) if m.prev_price else 0
            if z > agents.WAKE_PRICE and rng.random() < p["price_beta"]:
                return True
        return False

    def _persona(self, pid):
        for p in self.personas:
            if p["persona_id"] == pid:
                return p
        raise KeyError(pid)

    def _check_breaker(self, a):
        if not self.cb.get("enabled") or a != "EQ":
            return
        m = self.marks[a]
        day_ret = m.price / m.day_open - 1 if m.day_open else 0.0
        levels = self.cb.get("levels", [-0.07, -0.13, -0.20])
        halts = self.cb.get("halt_rounds", [15, 60, 10 ** 6])
        for lv, h in zip(levels, halts):
            if day_ret <= lv and not m.halted:
                m.halted, m.halt_rounds_left = True, h
                self.sc.setdefault("_halts", []).append((self.t, a, lv))
                break


def run_scenario(scenario, panel, out_dir, quiet=False):
    """One run of the five-tuple manifest. Returns summary dict."""
    from . import recorder, metrics
    gw = LLMGateway(**scenario.get("model", {}))
    world = World(scenario, panel, gw)
    rec = recorder.RunRecorder(out_dir, scenario, panel, gw)
    t0 = _time.time()
    wake_log = world.run(rec)
    elapsed = _time.time() - t0
    summary = metrics.summarize(rec, world, scenario, elapsed, wake_log)
    rec.write_summary(summary)
    rec.close()
    if not quiet:
        print(f"[{scenario['id']}] {elapsed:.1f}s  EQ {summary['assets']['EQ']['total_ret']:+.2%} "
              f"vol {summary['assets']['EQ']['ann_vol']:.1%}  "
              f"llm_calls={gw.usage['calls'] + gw.usage['memo_hits']} "
              f"memo_hits={gw.usage['memo_hits']}  -> {out_dir}")
    return summary

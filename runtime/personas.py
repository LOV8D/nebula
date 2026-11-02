"""Panel generation: archetypes -> weighted representative agents.

Demo composition (plan §3, rev 2.1): 883 agents = 715 LLM personas /
145 compiled-policy / 15 rule / 8 meta. Weights are coarsely aligned to
market shares (plan §2); exact proportionality is deferred to Phase-2
real-person calibration. Every field carries provenance; blanks stay blank.
"""
import hashlib
import json
import random
from pathlib import Path

from evidence import provenance

CLASSES = {
    # ---------------- Tier A: LLM personas ----------------
    # size_scale: max fraction of AUM a single decision may trade —
    # institutional turnover is tens of bps/day, not tens of percent.
    "retail_direct": dict(tier="llm", n=500, aum=0.36, flow=0.30, size_scale=1.0,
        budget=(60_000, 1.1), lev=2.0, universe=["EQ"], mandate=None),
    "retail_advised": dict(tier="llm", n=60, aum=0.04, flow=0.03, size_scale=0.3,
        budget=(250_000, 0.9), lev=1.5, universe=["EQ", "IR"], mandate=None),
    "mf_pm": dict(tier="llm", n=60, aum=0.17, flow=0.20, size_scale=0.002,
        budget=(2e9, 0.8), lev=1.2, universe=["EQ", "IR"], mandate="style_box"),
    "hf_pm": dict(tier="llm", n=50, aum=0.06, flow=0.18, size_scale=0.005,
        budget=(8e8, 1.0), lev=4.0, universe=["EQ", "IR", "FX", "CMD", "CRYPTO"],
        mandate=None, can_short=True),
    "foreign_inst": dict(tier="llm", n=45, aum=0.17, flow=0.12, size_scale=0.002,
        budget=(5e9, 0.9), lev=2.0, universe=["EQ", "IR", "FX"], mandate="allocation"),
    # ---------------- Tier B: compiled policies ----------------
    "index_ap": dict(tier="policy", n=60, aum=0.12, flow=0.08,
        budget=(3e9, 0.6), lev=1.0, universe=["EQ", "IR"], mandate="passive"),
    "pension": dict(tier="policy", n=40, aum=0.05, flow=0.05,
        budget=(1e10, 0.5), lev=1.0, universe=["EQ", "IR"], mandate="ldp"),
    "insurer": dict(tier="policy", n=25, aum=0.02, flow=0.02,
        budget=(3e9, 0.5), lev=1.0, universe=["EQ", "IR"], mandate="buy_hold"),
    "buyback": dict(tier="policy", n=20, aum=0.01, flow=0.05,
        budget=(5e7, 0.4), lev=1.0, universe=["EQ"], mandate="program"),
    # ---------------- Tier C: rules ----------------
    "market_maker": dict(tier="rule", n=15, aum=0.0, flow=0.0,
        budget=(2e8, 0.0), lev=10.0, universe=[], mandate="two_sided"),
    # ---------------- Meta: mechanism / event sources ----------------
    "meta": dict(tier="meta", n=8, aum=0.0, flow=0.0,
        budget=(0, 0.0), lev=0.0, universe=[], mandate=None),
}

# starting allocation by class: {asset: weight}; remainder stays cash.
# The market snapshot is an EXISTING market — day 1 must not be an
# everyone-reallocates artifact.
START_WEIGHTS = {
    "retail_direct": {"EQ": 0.55, "CRYPTO": 0.05},
    "retail_advised": {"EQ": 0.55, "IR": 0.15},
    "mf_pm": {"EQ": 0.6, "IR": 0.3},
    "hf_pm": {"EQ": 0.3, "IR": 0.15, "FX": 0.1, "CMD": 0.1, "CRYPTO": 0.1},
    "foreign_inst": {"EQ": 0.5, "IR": 0.2, "FX": 0.1},
    "index_ap": {"EQ": 0.7, "IR": 0.25},
    "pension": {"EQ": 0.6, "IR": 0.4},
    "insurer": {"EQ": 0.2, "IR": 0.78},
    "buyback": {},
    "market_maker": {},
    "meta": {},
}

ARCHETYPES = {
    "retail_direct": [
        dict(name="conservative_retiree", w=0.20, att=0.2, news=0.4, price=0.1,
             disp=0.3, herd=0.2, horizon=3000, risk=0.9, loss_av=2.5,
             frictions=["checks_monthly_statement_only"]),
        dict(name="accumulator_401k", w=0.30, att=0.05, news=0.2, price=0.05,
             disp=0.2, herd=0.1, horizon=7000, risk=0.6, loss_av=2.0,
             frictions=["never_checks_price", "buys_payday"]),
        dict(name="growth_trader", w=0.25, att=6.0, news=0.8, price=0.8,
             disp=0.6, herd=0.5, horizon=300, risk=0.4, loss_av=1.8,
             stop_p=0.5, stop=-0.05, lev=2.0, frictions=["lunch_break_only"]),
        dict(name="meme_chaser", w=0.14, att=8.0, news=1.0, price=1.0,
             disp=0.4, herd=0.9, horizon=60, risk=0.25, loss_av=1.2,
             crypto=True, frictions=["social_feed_only", "ignores_fees"]),
        dict(name="income_options", w=0.11, att=0.5, news=0.3, price=0.2,
             disp=0.2, herd=0.1, horizon=1500, risk=0.7, loss_av=2.2,
             frictions=["yield_focused"]),
    ],
    "retail_advised": [
        dict(name="advisor_client_core", w=1.0, att=0.1, news=0.3, price=0.05,
             disp=0.2, herd=0.3, horizon=2500, risk=0.7, loss_av=2.0,
             frictions=["info_filtered_by_advisor", "slow_follower"]),
    ],
    "mf_pm": [
        dict(name="value_large", w=0.25, att=4.0, news=0.6, price=0.3,
             disp=0.3, herd=0.2, horizon=1500, risk=0.5, loss_av=1.5, style="value"),
        dict(name="growth_large", w=0.25, att=5.0, news=0.7, price=0.4,
             disp=0.4, herd=0.3, horizon=900, risk=0.4, loss_av=1.6, style="growth"),
        dict(name="bond_fund", w=0.30, att=3.0, news=0.5, price=0.3,
             disp=0.2, herd=0.2, horizon=2000, risk=0.8, loss_av=2.0, style="bond"),
        dict(name="balanced", w=0.20, att=3.0, news=0.5, price=0.3,
             disp=0.2, herd=0.2, horizon=2000, risk=0.65, loss_av=1.9, style="balanced"),
    ],
    "hf_pm": [
        dict(name="global_macro", w=0.30, att=10.0, news=1.0, price=0.7,
             disp=0.3, herd=0.2, horizon=120, risk=0.3, loss_av=1.3,
             stop_p=0.6, stop=-0.04, style="macro"),
        dict(name="cta_trend", w=0.30, att=8.0, news=0.6, price=0.9,
             disp=0.2, herd=0.3, horizon=60, risk=0.3, loss_av=1.2,
             stop_p=0.7, stop=-0.03, style="trend"),
        dict(name="multi_strat", w=0.20, att=8.0, news=0.8, price=0.6,
             disp=0.3, herd=0.3, horizon=90, risk=0.35, loss_av=1.3,
             stop_p=0.5, stop=-0.04, style="multi"),
        dict(name="equity_ls", w=0.20, att=7.0, news=0.7, price=0.6,
             disp=0.5, herd=0.2, horizon=180, risk=0.4, loss_av=1.4,
             stop_p=0.5, stop=-0.05, style="ls"),
    ],
    "foreign_inst": [
        dict(name="swf_reserve", w=0.4, att=2.0, news=0.6, price=0.2,
             disp=0.2, herd=0.2, horizon=3000, risk=0.7, loss_av=1.8, style="swf"),
        dict(name="foreign_bank_arm", w=0.6, att=3.0, news=0.7, price=0.3,
             disp=0.3, herd=0.3, horizon=1000, risk=0.6, loss_av=1.7, style="bank"),
    ],
    "index_ap": [dict(name="eq_index", w=0.75, style="eq"),
                 dict(name="bond_index", w=0.25, style="ir")],
    "pension": [dict(name="ldp_6040", w=1.0, style="6040")],
    "insurer": [dict(name="buy_hold_2080", w=1.0, style="2080")],
    "buyback": [dict(name="program_buyer", w=1.0, style="program")],
    "market_maker": [dict(name="mm", w=1.0, style="mm")],
    "meta": [dict(name="meta_role", w=1.0, style="meta")],
}

MM_ASSIGN = ["EQ"] * 4 + ["IR"] * 3 + ["FX"] * 3 + ["CMD"] * 2 + ["CRYPTO"] * 3
META_ROLES = ["sec", "cftc", "fed_chair_newswire", "macro_wire", "fx_wire",
              "cmd_wire", "crypto_wire", "corp_wire"]

# Which card a reader should get for this class: an investor has holdings, a
# market maker has inventory, a mandated vehicle has a rulebook, and an event
# source has neither — showing all four as "holdings" would be a lie.
CARD_KIND = {
    "retail_direct": "position", "retail_advised": "position",
    "mf_pm": "position", "hf_pm": "position", "foreign_inst": "position",
    "index_ap": "mandate", "pension": "mandate", "insurer": "mandate",
    "buyback": "mandate",
    "market_maker": "inventory",
    "meta": "event_source",
}

# Per-attribute evidence. Every value the generator writes gets one of these;
# `provenance.validate` fails the panel if a value appears without a record.
_PRIOR_BEHAVIOR = ("behavioral-finance and brokerage-activity literature "
                   "priors, uncalibrated")
_FIELD_EVIDENCE = {
    "cls": ("panel construction (plan §3.1 class table)", "derived"),
    "archetype": ("panel construction (archetype weights, plan §3.1)", "derived"),
    "tier": ("panel construction (cognition tier assignment)", "derived"),
    "budget_usd": ("synthetic lognormal prior scaled to SCF/ICI aggregates, coarse", "prior"),
    "aum_w": ("class share of market AUM (plan §2), coarse", "prior"),
    "flow_w": ("class share of market flow (plan §2), coarse", "prior"),
    "universe": ("class and archetype configuration", "derived"),
    "leverage_cap": ("class and archetype configuration", "derived"),
    "can_short": ("class configuration", "derived"),
    "mandate": ("class configuration", "derived"),
    "size_scale": ("class turnover prior (institutional turnover is tens of bps/day)", "prior"),
    "style": ("archetype definition", "derived"),
    "attention_per_day": (_PRIOR_BEHAVIOR, "prior"),
    "news_beta": (_PRIOR_BEHAVIOR, "prior"),
    "price_beta": (_PRIOR_BEHAVIOR, "prior"),
    "disposition": (_PRIOR_BEHAVIOR, "prior"),
    "herding": (_PRIOR_BEHAVIOR, "prior"),
    "risk_aversion": ("literature priors, uncalibrated", "prior"),
    "loss_aversion": ("literature priors, uncalibrated", "prior"),
    "horizon_days": ("archetype definition", "prior"),
    "reaction_delay_rounds": ("attention-gating prior, uncalibrated", "prior"),
    "frictions": ("archetype definition", "prior"),
    "stop_loss": ("archetype definition", "prior"),
    "mm_asset": ("panel assignment", "derived"),
    "meta_role": ("panel assignment", "derived"),
    "card_kind": ("panel construction", "derived"),
    "start_weights": ("class starting-allocation prior (plan §3.1)", "prior"),
}

# Attributes a real-person source would fill and this panel cannot. They stay
# None, they are listed on every agent they apply to, and `provenance.report`
# counts them — this is the Phase-2 data ask, stated as data rather than prose.
_UNKNOWN_TRAITS = {
    "position": {
        "holdings_actual": "consented account snapshot",
        "redemption_history": "consented transaction history",
        "trading_frequency_observed": "consented transaction history",
        "loss_realization_observed": "consented transaction history",
        "statement_check_frequency": "app or statement telemetry, or self-report",
        "information_channels": "investor survey (self-report)",
        "fee_sensitivity_observed": "fee-change natural experiment on real accounts",
        "risk_questionnaire_grade": "institution's suitability assessment record",
        "product_comprehension": "investor survey (self-report)",
    },
    "mandate": {
        "mandate_document": "published prospectus or investment policy statement",
        "flow_rules_observed": "consented subscription and redemption records",
    },
    "inventory": {
        "quoting_policy_observed": "venue market-maker obligations or observed quotes",
    },
    "event_source": {},
}


def _id_seed(run_seed, persona_id):
    return int(hashlib.sha256(f"{run_seed}:{persona_id}".encode()).hexdigest()[:12], 16)


def _identity(cls, arch, rng, budget):
    ages = {"retail_direct": (25, 75), "retail_advised": (45, 80)}
    if cls in ages:
        age = rng.randint(*ages[cls])
        return (f"{arch['name']}-type {cls.replace('_', ' ')} agent; age {age}; "
                f"account ~${budget/1000:.0f}k; checks markets "
                f"{'rarely' if arch.get('att', 1) < 1 else 'frequently'}; "
                f"frictions: {', '.join(arch.get('frictions', []))}.")
    return f"{arch['name']} institutional agent, style={arch.get('style', 'n/a')}, AUM ~${budget/1e6:.0f}M."


def generate_panel(seed=7):
    rng = random.Random(seed)
    panel = []
    for cls, cfg in CLASSES.items():
        archs = ARCHETYPES[cls]
        weights = [a["w"] for a in archs]
        for i in range(cfg["n"]):
            arch = rng.choices(archs, weights=weights, k=1)[0]
            # Full class name, not a 6-char prefix: `retail_direct` and
            # `retail_advised` both truncate to "retail", which silently
            # collided 60 ids — and the engine keys accounts and RNG streams
            # by persona_id, so the advised twin overwrote the direct one.
            pid = f"{cls}-{i:04d}"
            a = dict(persona_id=pid, cls=cls, archetype=arch["name"], tier=cfg["tier"])
            budget = _sample_budget(rng, cfg)
            a["budget_usd"] = round(budget, 2)
            a["aum_w"] = cfg["aum"] / cfg["n"]
            a["flow_w"] = cfg["flow"] / cfg["n"]
            universe = _universe(cls, arch, rng)
            a["universe"] = universe
            a["leverage_cap"] = arch.get("lev", cfg["lev"])
            a["can_short"] = bool(cfg.get("can_short"))
            a["mandate"] = cfg["mandate"]
            a["size_scale"] = cfg.get("size_scale", 1.0)
            a["style"] = arch.get("style")
            a["attention_per_day"] = _jitter(rng, arch.get("att", 1.0), 0.3)
            a["news_beta"] = _jitter(rng, arch.get("news", 0.3), 0.25)
            a["price_beta"] = _jitter(rng, arch.get("price", 0.2), 0.25)
            a["disposition"] = _jitter(rng, arch.get("disp", 0.2), 0.25)
            a["herding"] = _jitter(rng, arch.get("herd", 0.2), 0.25)
            a["risk_aversion"] = arch.get("risk", 0.6)
            a["loss_aversion"] = arch.get("loss_av", 1.8)
            a["horizon_days"] = arch.get("horizon", 2000)
            a["reaction_delay_rounds"] = [max(0, int(rng.gauss(1, 3))),
                                          max(1, int(rng.gauss(12, 10)))]
            a["frictions"] = arch.get("frictions", [])
            if rng.random() < arch.get("stop_p", 0.0):
                a["stop_loss"] = arch["stop"]
            if cls == "market_maker":
                a["mm_asset"] = MM_ASSIGN[i % len(MM_ASSIGN)]
            if cls == "meta":
                a["meta_role"] = META_ROLES[i % len(META_ROLES)]
            a["card_kind"] = CARD_KIND[cls]
            a["start_weights"] = dict(START_WEIGHTS.get(cls, {}))
            prng = random.Random(_id_seed(seed, pid))
            a["identity_card"] = _identity(cls, arch, prng, budget)
            _attach_evidence(a)
            panel.append(a)
    return panel


def _attach_evidence(a):
    """Give every written attribute its own evidence record, then list the
    attributes a real-person source would fill and we have no evidence for.
    Called once per agent, after all values are set."""
    prov = {}
    for field_name in list(a):
        if field_name in ("persona_id", "identity_card"):
            continue
        src, kind = _FIELD_EVIDENCE.get(
            field_name, ("ungrounded generator default", "prior"))
        prov[field_name] = provenance.evidence(source=src, kind=kind,
                                               confidence="low")
    unknowns = _UNKNOWN_TRAITS.get(a["card_kind"], {})
    for field_name, needed in unknowns.items():
        a[field_name] = None
        prov[field_name] = provenance.unknown(needed)
    a["unknown_fields"] = sorted(unknowns)
    prov["unknown_fields"] = provenance.evidence(
        source="generator bookkeeping", kind="derived", confidence="high")
    prov["identity_card"] = provenance.evidence(
        source="rendered from the attributes above", kind="derived",
        confidence="low",
        note="prompt-facing text; adds no information beyond its fields")
    a["provenance"] = prov


def _sample_budget(rng, cfg):
    med, sigma = cfg["budget"]
    return max(med * 0.05, rng.lognormvariate(0, sigma) * med)


def _universe(cls, arch, rng):
    if cls == "market_maker":
        return [arch.get("mm_asset")] if "mm_asset" in arch else []
    base = list(CLASSES[cls]["universe"])
    if cls == "retail_direct":
        if arch.get("crypto") or (arch["name"] == "growth_trader" and rng.random() < 0.3):
            base = ["EQ", "CRYPTO"]
    if cls == "mf_pm":
        base = {"value_large": ["EQ"], "growth_large": ["EQ"],
                "bond_fund": ["IR"], "balanced": ["EQ", "IR"]}[arch["name"]]
    return base


def _jitter(rng, mu, rel):
    return max(0.0, min(2.0, rng.gauss(mu, abs(mu) * rel + 1e-9)))


def write_panel(path, seed=7):
    panel = generate_panel(seed)
    ids = [a["persona_id"] for a in panel]
    if len(set(ids)) != len(ids):
        from collections import Counter
        dupes = [k for k, v in Counter(ids).items() if v > 1]
        raise SystemExit(f"duplicate persona_ids ({len(dupes)}): {dupes[:5]} — "
                         "accounts and RNG streams are keyed by this id")
    problems = [p for a in panel for p in provenance.validate(a)]
    if problems:
        raise SystemExit("panel failed its own evidence check:\n  "
                         + "\n  ".join(problems[:10]))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(panel, indent=1))
    from collections import Counter
    print(f"panel: {len(panel)} agents -> {path}")
    print("  by class:", dict(Counter(a['cls'] for a in panel)))
    print("  tiers:", dict(Counter(a['tier'] for a in panel)))
    print("  cards:", dict(Counter(a['card_kind'] for a in panel)))
    cov = provenance.coverage(panel)
    print(f"  evidence: {cov['attribute_records']} records, "
          f"{cov['grounded_share']:.1%} grounded in real people")
    return panel


if __name__ == "__main__":
    write_panel(Path(__file__).resolve().parent.parent / "personas" / "panel_v3.json")

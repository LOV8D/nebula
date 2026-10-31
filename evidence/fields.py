"""Closed-value financial persona fields: schema, questionnaire, ingest.

The panel's behavioural parameters are continuous (attention_per_day 0.42,
news_beta 1.3...) — good for simulation, useless for receiving real-person
data: a survey answer cannot land on a float. This module adds the closed-
value layer beside the continuous one, following the borrow list:
closed sets a survey can map onto, dependency constraints that reject only
logically impossible combinations (rare-but-real gets flagged, not deleted),
and provenance riding on the existing evidence records (`self_report` with
granted consent lands as `calibration` split — never `train`).

Nothing here mutates personas/panel_v3.json. Survey answers become patch
files under personas/patches/; wiring patches into a panel is a later,
explicit step.

    python3 -m runtime.cli fields              # schema + panel consistency check
    python3 -m runtime.cli survey              # -> site/investor_survey.html
    python3 -m runtime.cli ingest ANSWERS.json # validate -> patch (dry-run)
"""
import hashlib
import json
from pathlib import Path

from . import provenance

ROOT = Path(__file__).resolve().parent.parent

#: Survey-reachable closed fields. Grouped for questionnaire flow; `maps_to`
#: names the continuous parameter a band is derived from (kind=derived) or
#: None when the panel only holds a prior (kind=prior, archetype/hash-based).
SCHEMA = {
    "Account & advice": {
        "account_type": {
            "q": "Which best describes your investment accounts?",
            "values": ["taxable_only", "retirement_only", "both",
                       "managed_discretionary"],
            "maps_to": None},
        "advice_channel": {
            "q": "How do you mainly decide on investments?",
            "values": ["pure_self_directed", "app_robo_advisor",
                       "human_advisor", "social_media_tips", "mixed"],
            "maps_to": None},
        "years_investing_band": {
            "q": "How long have you been investing?",
            "values": ["lt_1", "y1_5", "y6_20", "gt_20"],
            "maps_to": None},
    },
    "Attention & information": {
        "statement_check_frequency": {
            "q": "How often do you check your portfolio?",
            "values": ["daily", "weekly", "monthly", "quarterly_or_less"],
            "maps_to": "attention_per_day",
            "closes": "statement_check_frequency"},
        "information_channels": {
            "q": "Where do your market information mainly come from? "
                 "(pick all that apply)",
            "values": ["broker_app", "tv_finnews", "social_media", "forums",
                       "advisor", "word_of_mouth", "none"],
            "multi": True,
            "maps_to": None,
            "closes": "information_channels"},
        "reaction_speed": {
            "q": "When big market news breaks, how fast do you usually act?",
            "values": ["same_hour", "same_day", "within_week",
                       "later_or_never"],
            "maps_to": "reaction_delay_rounds"},
    },
    "Behaviour & experience": {
        "redemption_history": {
            "q": "In the last 12 months, how often did you sell out of a "
                 "fund or large position?",
            "values": ["none", "once", "few_2_5", "frequent_gt5"],
            "maps_to": None,
            "closes": "redemption_history"},
        "trading_frequency_selfreport": {
            "q": "How often do you trade?",
            "values": ["buy_and_hold", "few_times_year", "monthly",
                       "weekly_or_more"],
            "maps_to": None,
            "closes": "trading_frequency_observed"},
        "loss_response_2022": {
            "q": "In the 2022 drawdown, what did you do?",
            "values": ["sold_all_or_most", "trimmed", "held", "bought_more",
                       "not_invested_then"],
            "maps_to": None},
        "stop_loss_habit": {
            "q": "Do you use stop-losses?",
            "values": ["always_use", "sometimes", "never",
                       "dont_know_what_it_is"],
            "maps_to": None},
        "fee_sensitivity_selfreport": {
            "q": "A fund you hold raises its fee. What have you actually "
                 "done in the past?",
            "values": ["unaware", "noticed_but_stayed", "switched_for_fees",
                       "negotiated_fees"],
            "maps_to": None,
            "closes": "fee_sensitivity_observed"},
        "risk_questionnaire_grade": {
            "q": "If your broker graded your risk tolerance, closest match?",
            "values": ["c1_2_conservative", "c3_4_balanced", "c5_growth",
                       "na"],
            "maps_to": "risk_aversion",
            "closes": "risk_questionnaire_grade"},
        "product_comprehension_selfreport": {
            "q": "How well do you understand the products you hold?",
            "values": ["novice", "basic", "confident", "professional"],
            "maps_to": None,
            "closes": "product_comprehension"},
    },
    "Constraints": {
        "leverage_use": {
            "q": "Do you use margin?",
            "values": ["none", "margin_sometimes", "margin_routine"],
            "maps_to": None},
        "derivatives_use": {
            "q": "Do you use options or other derivatives?",
            "values": ["none", "options_occasionally", "derivatives_routine"],
            "maps_to": None},
    },
    "Wealth band": {
        "aum_band": {
            "q": "Total invested assets (band)?",
            "values": ["lt_10k", "b10_50k", "b50_250k", "b250_1m", "gt_1m"],
            "maps_to": "budget_usd"},
    },
}

#: Logically impossible combinations — an ingest with one of these is
#: rejected outright. Rarity is NOT here: rare-but-real stays answerable
#: (BP principle: exclude only the impossible, down-weight the rare).
IMPOSSIBLE = [
    ("account_type", "retirement_only", "leverage_use",
     ("margin_sometimes", "margin_routine"),
     "retirement accounts cannot hold margin"),
    ("account_type", "retirement_only", "derivatives_use",
     ("options_occasionally", "derivatives_routine"),
     "retirement accounts cannot trade derivatives"),
    ("account_type", "managed_discretionary", "advice_channel",
     ("pure_self_directed",),
     "a discretionary account is by definition not self-directed"),
    ("years_investing_band", "lt_1", "loss_response_2022",
     ("sold_all_or_most", "trimmed", "held", "bought_more"),
     "investing for under a year (asked 2026) means no 2022 position"),
]

#: Rare-but-real: kept, flagged in the ingest report, down-weighted when a
#: patch is eventually wired into a panel.
RARE = [
    ("aum_band", "lt_10k", "trading_frequency_selfreport", "weekly_or_more",
     "very active trading on a small account — real, uncommon"),
    ("risk_questionnaire_grade", "c1_2_conservative", "derivatives_use",
     "derivatives_routine", "conservative grade with routine derivatives"),
    ("stop_loss_habit", "dont_know_what_it_is", "derivatives_use",
     "derivatives_routine", "routine derivatives without knowing stops"),
]

_FIELDS = {f: spec for grp in SCHEMA.values() for f, spec in grp.items()}


def _pick(agent_id, field, weights):
    """Deterministic weighted choice per agent (no RNG state consumed)."""
    h = int(hashlib.sha256(f"{agent_id}|{field}".encode()).hexdigest()[:8], 16)
    acc, r = 0.0, (h % 10_000) / 10_000
    for v, w in weights:
        acc += w
        if r < acc:
            return v
    return weights[-1][0]


def _band(value, edges, labels):
    for (lo, hi), lab in zip(edges, labels):
        if lo <= value < hi:
            return lab
    return labels[-1]


def _repair(b):
    """Make the synthesized combination satisfy the dependency rules without
    touching the load-bearing continuous params (leverage/derivatives use is
    kept; the account type yields)."""
    if b.get("account_type") == "retirement_only" and (
            b.get("leverage_use", "none") != "none"
            or b.get("derivatives_use", "none") != "none"):
        b["account_type"] = "both"
    if (b.get("account_type") == "managed_discretionary"
            and b.get("advice_channel") == "pure_self_directed"):
        b["advice_channel"] = "human_advisor"
    if b.get("years_investing_band") == "lt_1":
        b["loss_response_2022"] = "not_invested_then"
    return b


def synthesize(agent):
    """Closed-field values for one panel agent, derived deterministically
    from its continuous parameters where a mapping exists. Returns
    {field: (value, evidence_record)}; retail investors only — institutional
    closed fields (mandate documents, MM obligations) belong to a different
    data surface and stay unset here."""
    if agent.get("card_kind") != "position" \
            or not str(agent.get("cls", "")).startswith("retail"):
        return None
    a = agent
    bands = {}
    att = a.get("attention_per_day", 0)
    bands["statement_check_frequency"] = _band(
        att, [(-1, 0.10), (0.10, 0.30), (0.30, 0.80), (0.80, 99)],
        ["quarterly_or_less", "monthly", "weekly", "daily"])
    rd = a.get("reaction_delay_rounds", [0, 1])
    rd = sum(rd[:2]) / 2 if isinstance(rd, (list, tuple)) else rd  # mid of the triangular support
    bands["reaction_speed"] = _band(
        rd, [(0, 2), (2, 8), (8, 30), (30, 9999)],
        ["same_hour", "same_day", "within_week", "later_or_never"])
    ra = a.get("risk_aversion", 0.5)
    bands["risk_questionnaire_grade"] = _band(
        ra, [(0.66, 1.01), (0.33, 0.66), (-1, 0.33)],
        ["c1_2_conservative", "c3_4_balanced", "c5_growth"])
    budget = a.get("budget_usd", 0)
    bands["aum_band"] = _band(
        budget, [(0, 10_000), (10_000, 50_000), (50_000, 250_000),
                 (250_000, 1_000_000), (1_000_000, float("inf"))],
        ["lt_10k", "b10_50k", "b50_250k", "b250_1m", "gt_1m"])
    disp = a.get("disposition", 0.3)
    if a.get("cls", "").startswith("retail"):
        bands["loss_response_2022"] = _pick(a["persona_id"], "loss2022", [
            ("sold_all_or_most", 0.10 + disp * 0.2), ("trimmed", 0.25),
            ("held", 0.35), ("bought_more", 0.15), ("not_invested_then", 0.15)])
    # prior-only fields: weighted deterministic picks, archetype-aware
    arch = a.get("archetype", "")
    chatty = arch in ("meme_chaser", "day_trader", "news_junkie")
    bands["account_type"] = _pick(a["persona_id"], "acct", [
        ("taxable_only", 0.45), ("retirement_only", 0.20), ("both", 0.30),
        ("managed_discretionary", 0.05)])
    bands["advice_channel"] = _pick(a["persona_id"], "advice", [
        ("pure_self_directed", 0.40 if chatty else 0.25),
        ("app_robo_advisor", 0.15), ("human_advisor", 0.15),
        ("social_media_tips", 0.20 if chatty else 0.10), ("mixed", 0.15)])
    bands["years_investing_band"] = _pick(a["persona_id"], "years", [
        ("lt_1", 0.05), ("y1_5", 0.25), ("y6_20", 0.45), ("gt_20", 0.25)])
    bands["redemption_history"] = _pick(a["persona_id"], "redempt", [
        ("none", 0.40), ("once", 0.30), ("few_2_5", 0.20),
        ("frequent_gt5", 0.10)])
    bands["trading_frequency_selfreport"] = _pick(a["persona_id"], "freq", [
        ("buy_and_hold", 0.40 if not chatty else 0.10),
        ("few_times_year", 0.30), ("monthly", 0.15),
        ("weekly_or_more", 0.05 if not chatty else 0.45)])
    bands["stop_loss_habit"] = _pick(a["persona_id"], "stops", [
        ("always_use", 0.10), ("sometimes", 0.25), ("never", 0.40),
        ("dont_know_what_it_is", 0.25)])
    bands["fee_sensitivity_selfreport"] = _pick(a["persona_id"], "fee", [
        ("unaware", 0.30), ("noticed_but_stayed", 0.40),
        ("switched_for_fees", 0.20), ("negotiated_fees", 0.10)])
    bands["product_comprehension_selfreport"] = _pick(a["persona_id"], "comp", [
        ("novice", 0.30), ("basic", 0.35), ("confident", 0.25),
        ("professional", 0.10)])
    lev = a.get("leverage_cap", 1.0)
    bands["leverage_use"] = ("margin_routine" if lev >= 2.0 else
                             "margin_sometimes" if lev > 1.0 else "none")
    bands["derivatives_use"] = ("none" if "CRYPTO" not in a.get("universe", [])
                                and arch not in ("day_trader", "hf_like")
                                else _pick(a["persona_id"], "deriv", [
                                    ("none", 0.4),
                                    ("options_occasionally", 0.4),
                                    ("derivatives_routine", 0.2)]))
    bands["information_channels"] = None  # multi-select: no single band
    bands = _repair(bands)
    errs, _ = check_answers({f: v for f, v in bands.items() if v is not None})
    if errs:
        raise AssertionError(f"synthesis violates dependency rules: {errs}")
    out = {}
    for f, spec in _FIELDS.items():
        v = bands.get(f)
        if v is None:
            continue
        if spec.get("maps_to"):
            rec = provenance.evidence(
                source=f"band derived from {spec['maps_to']} (panel prior)",
                kind="derived", confidence="low", split="none",
                note="derived layer: consistent with the continuous prior, "
                     "not human-grounded")
        else:
            rec = provenance.evidence(
                source="deterministic archetype/weights prior (un-calibrated)",
                kind="prior", confidence="low", split="none")
        out[f] = (v, rec)
    return out


def check_answers(ans):
    """(errors, warnings) for one respondent's answers against the schema.
    errors = out-of-vocabulary or logically impossible; warnings = rare."""
    errors, warnings = [], []

    def val(f):
        return ans.get(f)

    for f, spec in _FIELDS.items():
        v = val(f)
        if v is None:
            continue
        vs = [v] if not spec.get("multi") else (v if isinstance(v, list) else [v])
        for x in vs:
            if x not in spec["values"]:
                errors.append(f"{f}: {x!r} not in closed set "
                              f"{spec['values']}")
    for fa, va, fb, forbidden, why in IMPOSSIBLE:
        if val(fa) == va and val(fb) in forbidden:
            errors.append(f"{fa}={va} with {fb}={val(fb)} impossible: {why}")
    for fa, va, fb, vb, why in RARE:
        if val(fa) == va and val(fb) == vb:
            warnings.append(f"rare-but-real kept: {fa}={va} with {fb}={vb} "
                            f"({why})")
    return errors, warnings


def survey_json():
    items = []
    for group, fields in SCHEMA.items():
        for f, spec in fields.items():
            items.append({"id": f, "group": group, "question": spec["q"],
                          "values": spec["values"],
                          "multi": bool(spec.get("multi"))})
    return {"title": "Investor behavior & constraints survey",
            "version": "v1-2026-10-24",
            "consent": ("Answers are used to ground one simulated investor "
                        "persona (research calibration split). Respondent "
                        "may withdraw; no marketing use."),
            "items": items}


def survey_html():
    s = survey_json()
    rows = []
    for i, it in enumerate(s["items"], 1):
        opts = "".join(
            f"<label><input type='{'checkbox' if it['multi'] else 'radio'}' "
            f"name='{it['id']}' value='{v}'> {v.replace('_', ' ')}</label>"
            for v in it["values"])
        rows.append(f"<fieldset><legend>{i}. {_esc(it['question'])} "
                    f"<span class='grp'>{_esc(it['group'])}</span></legend>"
                    f"<div class='opts'>{opts}</div></fieldset>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<title>Investor survey — Nebula (Asterium Labs)</title><style>"
            ":root{color-scheme:light}"
            "body{font:14px/1.6 -apple-system,'Segoe UI',sans-serif;"
            "max-width:720px;margin:24px auto;padding:0 16px;"
            "background:#ffffff;color:#1a1a1a}"
            "h1{font-size:20px} fieldset{border:1px solid #ccc;"
            "border-radius:8px;margin:10px 0;padding:10px 14px}"
            "legend{font-weight:600} .grp{color:#888;font-weight:400;"
            "font-size:11px;margin-left:6px} .opts{display:flex;"
            "flex-wrap:wrap;gap:6px 16px} label{font-size:13px}"
            ".consent{background:#f6f6f8;border-radius:8px;padding:10px 14px;"
            "font-size:12.5px;color:#555}</style></head><body>"
            f"<h1>{_esc(s['title'])}</h1>"
            f"<div class='consent'><b>Consent.</b> {_esc(s['consent'])}</div>"
            + "".join(rows) +
            "<p style='color:#888;font-size:12px'>Closed-value answers map "
            "onto persona fields; free text is not collected. v1-2026-10-24"
            "</p></body></html>")


def ingest(answers_path, apply=False, out_dir=None):
    """Validate survey answers and write a patch file. The patch is the
    deliverable — panel wiring is a separate, explicit step."""
    answers_path = Path(answers_path)
    data = json.loads(answers_path.read_text())
    out_dir = Path(out_dir) if out_dir else ROOT / "personas" / "patches"
    patches, n_err, n_warn = [], 0, 0
    respondents = data["respondents"] if "respondents" in data else [data]
    for r in respondents:
        if not r.get("consent_granted"):
            n_err += 1
            patches.append({"respondent_id": r.get("respondent_id", "?"),
                            "status": "rejected", "reason": "no consent"})
            continue
        errors, warnings = check_answers(r.get("answers", {}))
        n_err += len(errors)
        n_warn += len(warnings)
        entry = {"respondent_id": r.get("respondent_id", "?"),
                 "source_file": answers_path.name,
                 "errors": errors, "warnings": warnings}
        if not errors:
            filled = {}
            for f, v in r["answers"].items():
                if v is None:
                    continue
                filled[f] = {"value": v,
                             "evidence": provenance.evidence(
                                 source=f"investor survey {answers_path.name}",
                                 kind="self_report", confidence="medium",
                                 consent="granted", split="calibration",
                                 as_of=r.get("as_of"))}
            entry["fields"] = filled
            entry["status"] = "valid"
        else:
            entry["status"] = "rejected"
        patches.append(entry)
    ok = [p for p in patches if p["status"] == "valid"]
    out = {"survey_version": "v1-2026-10-24", "patches": patches,
           "summary": {"respondents": len(patches), "valid": len(ok),
                       "rejected": len(patches) - len(ok),
                       "answer_errors": n_err, "rare_flags": n_warn,
                       "note": "patches only; panel wiring is an explicit "
                               "later step"}}
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if apply else ".dryrun"
    path = out_dir / f"{answers_path.stem}.patch{suffix}.json"
    path.write_text(json.dumps(out, indent=1))
    return path, out["summary"]


def _esc(s):
    import html
    return html.escape(s)

"""Field-level evidence records for persona attributes.

Panel-level provenance ("these agents came from literature priors") cannot
answer the only question an institutional reviewer actually asks: *where did
THIS number come from, and may I rely on it?* So every generated attribute
carries its own record, and an attribute nobody has evidence for stays
`None` and is listed in `unknown_fields` instead of being invented.

Vocabularies are closed on purpose. Closed sets are what make the panel
auditable, what lets a survey answer be mapped onto an attribute later, and
what makes coverage countable instead of rhetorical.
"""
from typing import Optional

# --- closed vocabularies -------------------------------------------------
EVIDENCE = (
    "self_report",    # the person answered a question about themselves
    "behavioral",     # observed traces (orders, holdings, logins)
    "biographical",   # public profile / filing / registry
    "technical",      # instrument or venue records
    "prior",          # literature or market-share prior, nobody specific
    "derived",        # computed from other attributes of the same agent
    "unknown",        # no evidence; value must stay None
)
CONSENT = ("not_applicable", "granted", "pending", "none")
CONFIDENCE = ("high", "medium", "low", "none")
SPLIT = ("train", "calibration", "holdout", "none")

#: evidence kinds that come from an identifiable real person
HUMAN_EVIDENCE = ("self_report", "behavioral", "biographical", "technical")


def evidence(source: str, kind: str = "prior", confidence: str = "low",
             consent: str = "not_applicable", as_of: Optional[str] = None,
             split: str = "none", note: str = "") -> dict:
    """One attribute's evidence record. Raises on an out-of-vocabulary value
    rather than silently storing a typo that a later audit would trust."""
    if kind not in EVIDENCE:
        raise ValueError(f"evidence kind {kind!r} not in {EVIDENCE}")
    if consent not in CONSENT:
        raise ValueError(f"consent {consent!r} not in {CONSENT}")
    if confidence not in CONFIDENCE:
        raise ValueError(f"confidence {confidence!r} not in {CONFIDENCE}")
    if split not in SPLIT:
        raise ValueError(f"split {split!r} not in {SPLIT}")
    rec = {"source": source, "evidence": kind, "confidence": confidence,
           "consent": consent, "split": split}
    if as_of:
        rec["as_of"] = as_of
    if note:
        rec["note"] = note
    return rec


def unknown(expected_source: str, note: str = "") -> dict:
    """An attribute a real-person source would fill and we cannot. The value
    stays None; this record says which source would close the gap."""
    return evidence(source=f"would need: {expected_source}", kind="unknown",
                    confidence="none", consent="not_applicable",
                    note=note or "no evidence; value left unset")


def is_grounded(rec: dict) -> bool:
    return rec.get("evidence") in HUMAN_EVIDENCE


def validate(agent: dict) -> list:
    """Problems that would make an audit fail. Empty list means the agent's
    evidence block is internally consistent — not that it is well grounded."""
    problems = []
    prov = agent.get("provenance")
    if not isinstance(prov, dict) or not prov:
        return [f"{agent.get('persona_id', '?')}: no provenance block"]
    pid = agent.get("persona_id", "?")
    skip = {"persona_id", "provenance", "unknown_fields", "card_kind",
            "identity_card"}
    for field_name, value in agent.items():
        if field_name in skip:
            continue
        if field_name not in prov:
            problems.append(f"{pid}.{field_name}: value with no evidence record")
    for field_name, rec in prov.items():
        if rec.get("evidence") == "unknown" and agent.get(field_name) is not None:
            problems.append(
                f"{pid}.{field_name}: evidence is 'unknown' but a value is set "
                f"({agent[field_name]!r}) — that is an invented attribute")
        if rec.get("evidence") in HUMAN_EVIDENCE \
                and rec.get("consent") not in ("granted", "not_applicable"):
            problems.append(
                f"{pid}.{field_name}: human evidence without granted consent")
    return problems


def coverage(panel: list) -> dict:
    """How much of the panel rests on real people. Reported per attribute so
    the honest answer survives contact with a slide."""
    by_kind, by_field, splits = {}, {}, {}
    unknown_fields = {}
    for a in panel:
        for field_name, rec in (a.get("provenance") or {}).items():
            kind = rec.get("evidence", "?")
            by_kind[kind] = by_kind.get(kind, 0) + 1
            slot = by_field.setdefault(field_name, {})
            slot[kind] = slot.get(kind, 0) + 1
            splits[rec.get("split", "none")] = splits.get(rec.get("split", "none"), 0) + 1
        for field_name in a.get("unknown_fields", []):
            unknown_fields[field_name] = unknown_fields.get(field_name, 0) + 1
    total = sum(by_kind.values()) or 1
    grounded = sum(by_kind.get(k, 0) for k in HUMAN_EVIDENCE)
    return {
        "agents": len(panel),
        "attribute_records": total,
        "by_evidence_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
        "grounded_share": grounded / total,
        "by_split": splits,
        "unknown_fields": dict(sorted(unknown_fields.items(), key=lambda kv: -kv[1])),
        "by_field": by_field,
    }


def report(panel: list) -> str:
    """Terminal readout. The headline number is the share of attributes that
    trace to a real person, which is currently zero by construction."""
    c = coverage(panel)
    lines = [f"panel: {c['agents']} agents, {c['attribute_records']} attribute records",
             f"grounded in real people: {c['grounded_share']:.1%}",
             "", "by evidence kind:"]
    for kind, n in c["by_evidence_kind"].items():
        lines.append(f"  {kind:<13} {n:>7}  {n / c['attribute_records']:.1%}")
    if c["by_split"]:
        lines.append("")
        lines.append("by split: " + ", ".join(f"{k}={v}" for k, v in c["by_split"].items()))
    if c["unknown_fields"]:
        lines.append("")
        lines.append("attributes left unset for want of evidence "
                     "(these are the Phase-2 data asks):")
        for field_name, n in c["unknown_fields"].items():
            lines.append(f"  {field_name:<28} missing on {n} agents")
    problems = [p for a in panel for p in validate(a)]
    lines.append("")
    lines.append(f"consistency: {'OK' if not problems else f'{len(problems)} problems'}")
    for p in problems[:10]:
        lines.append(f"  {p}")
    if len(problems) > 10:
        lines.append(f"  ... and {len(problems) - 10} more")
    return "\n".join(lines)

"""One-page decision brief per case (P3).

Reads the SAME case object the dashboard renders — no separate prose is
generated, so the brief cannot disagree with the page. Five fixed
sections: the question; A/B originals and parameter diffs; main results
by model/seed; what cannot be said; the next testable hypothesis. Real
market impact is stated as unknown because it is.

    python3 -m runtime.cli brief [case_id]        # -> runs/scratch/<id>/decision_brief.md
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def brief(case_id, out_dir=None):
    from ui.cases import get
    from ui import collect, viewer
    from experiments.demo import _panel
    c = get(case_id)
    panel = _panel()
    panel_hash = viewer.population_hash(panel)
    order, _classes, _rows = collect._agents(panel)
    idx = {a["persona_id"]: i for i, a in enumerate(order)}
    cls_of = {a["persona_id"]: a["cls"] for a in panel}
    payload = collect.collect_case(c, panel, panel_hash, idx, cls_of)
    F = payload["flagship"]

    def pct(v):
        return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) else "—"

    lines = [f"# Decision brief — {c['title']} ({c['case_id']})",
             "",
             f"*Generated from the same case object as the dashboard; "
             f"nothing here is written separately from the numbers. "
             f"Model: {payload['flagship'].get('model', '?')}.*", "",
             "## 1. The question", "", c["decision_question"], "",
             "## 2. What differs between the arms", ""]
    for what, a, b in c["input_diffs"]:
        lines += [f"- **{what}**", f"  - A: {a}", f"  - B: {b}"]
    lines += ["", f"> {c['attribution_note']}", "",
              "## 3. Main results (per seed, EQ full-day return)", ""]
    for arm in ("a", "b"):
        seeds = F["arms"][arm]
        per = " / ".join(pct(s.get("day_ret")) for s in seeds)
        mean = F["day_mean"].get(arm)
        lines.append(f"- **{c['arms'][arm]['label']}**: {per} "
                     f"(mean {pct(mean)})")
    lines += ["", f"Parity: {c['parity_note']}", ""]
    if payload["robustness"]:
        lines += ["Sensitivity (this case): see the dashboard robustness "
                  "page; per-seed directions are shown there, never only "
                  "the mean.", ""]
    else:
        lines += ["Sensitivity: **untested** — no prompt/seed matrix has "
                  "been run for this case.", ""]
    lines += ["## 4. What cannot be said", ""]
    lines += [f"- {lim}" for lim in c["limitations"]]
    lines += ["- Real market impact: **unknown** — no real outcome exists "
              "for this simulated case.",
              "- No effect sizes; direction and ranking only (BP red line).",
              "",
              "## 5. Next testable hypothesis", ""]
    if case_id == "earnings_disclosure":
        lines += ["If the guidance sentence (not the sentiment parameter) "
                  "carries the effect, then holding sentiment fixed at "
                  "-0.25 while varying only the guidance text should "
                  "reproduce most of the A/B gap. Pre-register the "
                  "direction before running."]
    else:
        lines += ["If the wording effect is robust, a prompt-p2 rerun with "
                  "more seeds should keep every seed's A−B sign positive; "
                  "the current matrix is mixed on p1 and inverted on p2, "
                  "so the sign question is open."]
    lines += ["", "---", "",
              f"Sources: arms from `{c['arms']['a']['source_file']}` / "
              f"`{c['arms']['b']['source_file']}`; runs under "
              f"`{F['root']}`; availability "
              f"{json_summary(c['available'])}.", ""]
    return "\n".join(lines)


def json_summary(available):
    import json
    parts = []
    for brain, arms in available.items():
        ok = all(all(s.values()) for s in arms.values())
        parts.append(f"{brain}: {'complete' if ok else 'partial'}")
    return ", ".join(parts)


def main(argv):
    import sys
    sys.path.insert(0, str(ROOT))
    case_id = argv[1] if len(argv) > 1 else None
    from ui.cases import CASES
    if case_id is None:
        print("cases:", ", ".join(CASES))
        return 0
    out_dir = Path(argv[2]) if len(argv) > 2 else \
        ROOT / "runs" / "scratch" / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    text = brief(case_id)
    out = out_dir / "decision_brief.md"
    out.write_text(text)
    print(f"brief -> {out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))

"""Issuer five-question freeze & scoring (P2).

Before an earnings call, an analyst (human or model) lists at most five
concerns they expect to be asked about, each with a source. The list is
FROZEN (SHA-256 manifest) before the call; only afterwards are actual
Q&A topics attached and scored. The manifest proves what the content was
and when it was frozen — self-reported time plus hashes make the content
checkable; they do not by themselves prove the list existed before the
real event, which is why a prospective result additionally requires
independent verification.

File contract (all paths given by the caller; nothing is fetched):
  case.json          {event_id, deadline_utc, allowed_sources[{id,path,sha256,use}]}
  predictions.jsonl  {"method", "rank" (1-5), "concern", "source" | "abstain"}
  -> freeze_manifest.json  {schema, frozen_at, case_sha256, predictions_sha256,
                            materials_sha256, n_predictions}
  outcome.json       {topics: [...]}     (added later, separate file)
  -> score           {hit_rate, coverage, per_prediction}

Validation (refuses):
  - more than five predictions, duplicate ranks, rank out of 1..5
  - a prediction lacking both source and abstain
  - predictions whose source is not in the case's allowed list
  - outcome added BEFORE a freeze exists; edits to a frozen list
    (any change to predictions.jsonl after freezing is detectable and
    the score is refused)
Scoring:
  - a prediction hits if an outcome topic matches its concern
    (topic-substring match, case-insensitive; same concern repeated in
    the predictions counts once)
  - hit_rate = hits / n_predictions ; coverage = distinct matched
    outcome topics / n_outcome_topics

    python3 -m evaluation.issuer_questions freeze CASE PREDICTIONS
    python3 -m evaluation.issuer_questions score CASE FREEZE OUTCOME
"""
import hashlib
import json
import sys
from pathlib import Path

MAX_PREDICTIONS = 5
SCHEMA = "issuer-five-questions-v1"


def _sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_predictions(path):
    preds = []
    for i, line in enumerate(Path(path).read_text().splitlines()):
        line = line.strip()
        if not line:
            continue
        p = json.loads(line)
        p["_line"] = i + 1
        preds.append(p)
    return preds


def validate_predictions(preds, allowed_source_ids):
    errors = []
    if len(preds) > MAX_PREDICTIONS:
        errors.append(f"{len(preds)} predictions exceed the maximum of 5")
    ranks = [p.get("rank") for p in preds]
    for i, p in enumerate(preds, 1):
        r = p.get("rank")
        where = f"line {p.get('_line', i)}"
        if not isinstance(r, int) or not 1 <= r <= MAX_PREDICTIONS:
            errors.append(f"{where}: rank {r!r} not an int in 1..5")
        if p.get("abstain"):
            continue
        src = p.get("source")
        if not src:
            errors.append(f"{where}: no source and not an abstain")
        elif src not in allowed_source_ids:
            errors.append(f"{where}: source {src!r} not in the "
                          f"case's allowed list")
        if not (p.get("concern") or "").strip():
            errors.append(f"{where}: empty concern")
    dupes = {r for r in ranks if ranks.count(r) > 1}
    if dupes:
        errors.append(f"duplicate ranks: {sorted(dupes)}")
    return errors


def freeze(case_path, predictions_path, out_path, now=None):
    """Validate and freeze. Returns the manifest dict; raises on any error."""
    import datetime
    case = json.loads(Path(case_path).read_text())
    preds = _read_predictions(predictions_path)
    allowed = [s["id"] for s in case.get("allowed_sources", [])]
    errors = validate_predictions(preds, allowed)
    if errors:
        raise SystemExit("predictions refused:\n  " + "\n  ".join(errors))
    materials = {s["id"]: _sha256_file(s["path"]) for s in case["allowed_sources"]}
    manifest = {
        "schema": SCHEMA,
        "event_id": case["event_id"],
        "deadline_utc": case["deadline_utc"],
        "frozen_at": now or datetime.datetime.now(datetime.timezone.utc)
                              .isoformat(timespec="seconds"),
        "case_sha256": _sha256_file(case_path),
        "predictions_sha256": _sha256_file(predictions_path),
        "materials_sha256": materials,
        "n_predictions": len(preds),
    }
    Path(out_path).write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def score(case_path, freeze_path, outcome_path, predictions_path):
    """Score a frozen list against actual Q&A topics. Refuses tampering."""
    case = json.loads(Path(case_path).read_text())
    manifest = json.loads(Path(freeze_path).read_text())
    outcome = json.loads(Path(outcome_path).read_text())
    # tamper check: the predictions file must hash to the frozen value
    if _sha256_file(predictions_path) != manifest["predictions_sha256"]:
        raise SystemExit("refused: predictions.jsonl no longer matches the "
                         "frozen hash — the list was edited after freezing")
    if _sha256_file(case_path) != manifest["case_sha256"]:
        raise SystemExit("refused: case.json changed after freezing")
    preds = _read_predictions(predictions_path)
    topics = [t for t in outcome.get("topics", []) if str(t).strip()]
    # topic-substring match, case-insensitive; one hit per prediction
    def hit(p):
        c = (p.get("concern") or "").lower()
        return any(c and (c in str(t).lower() or str(t).lower() in c)
                   for t in topics)
    hits = [p for p in preds if not p.get("abstain") and hit(p)]
    # repeated concerns count once for coverage
    matched_topics = set()
    for p in hits:
        c = (p.get("concern") or "").lower()
        for t in topics:
            if c in str(t).lower() or str(t).lower() in c:
                matched_topics.add(str(t))
    n_active = sum(1 for p in preds if not p.get("abstain")) or 1
    return {
        "schema": SCHEMA,
        "event_id": case["event_id"],
        "n_predictions": len(preds),
        "n_active": n_active,
        "n_hits": len(hits),
        "hit_rate": round(len(hits) / n_active, 4),
        "n_outcome_topics": len(topics),
        "n_matched_topics": len(matched_topics),
        "coverage": round(len(matched_topics) / len(topics), 4) if topics else None,
        "per_prediction": [
            {"rank": p.get("rank"), "concern": p.get("concern"),
             "abstain": bool(p.get("abstain")), "hit": bool(hit(p))}
            for p in preds],
        "note": ("fixture result — not an external validation; hit rate "
                 "measures question anticipation, not market reaction"),
    }


def main(argv):
    if len(argv) >= 4 and argv[1] == "freeze":
        m = freeze(argv[2], argv[3], argv[4] if len(argv) > 4 else
                   str(Path(argv[3]).with_name("freeze_manifest.json")))
        print(json.dumps(m, indent=1))
        return 0
    if len(argv) >= 5 and argv[1] == "score":
        print(json.dumps(score(argv[2], argv[3], argv[4], argv[5]), indent=1))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

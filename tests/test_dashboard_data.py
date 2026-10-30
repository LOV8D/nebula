"""Dashboard data-contract test (run: python3 tests/test_dashboard_data.py).

The page in ui/app/ reads the dict that ui/collect.py builds; this pins the
keys and shapes it relies on, and checks the bundle: one JSON block that
parses, no unreplaced markers, nothing that closes a script tag early.

Needs the flagship runs' bulk logs (gitignored). Without them it says so and
exits 0 — the logs are rebuilt by `make demo2`.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.paths import FLAGSHIP  # noqa: E402


def main():
    if not (FLAGSHIP / "news_a_s0" / "intents.jsonl").exists():
        print(f"dashboard data test: SKIPPED — no bulk logs under {FLAGSHIP}")
        return
    from ui.bundle import MARKERS, bundle
    from ui.collect import collect
    d = collect()
    assert set(d) == {"meta", "flagship", "agents", "replay", "who", "robustness", "evidence"}, set(d)
    f = d["flagship"]
    assert f["t0"] is not None and 0 < f["t0"] < f["rounds"], f["t0"]
    assert len(f["arms"]["a"]) == len(f["arms"]["b"]) == len(f["parity"]) > 0
    for arm in f["arms"].values():
        for s in arm:
            assert len(s["eq"]) == f["rounds"], (s["run"], len(s["eq"]))
            assert isinstance(s["day_ret"], float)
    n = sum(c["n"] for c in d["agents"]["classes"])
    assert n == len(d["agents"]["rows"]) == d["meta"]["n_agents"], n
    tiers = [c["tier"] for c in d["agents"]["classes"]]
    assert tiers == sorted(tiers, key=["llm", "policy", "rule", "meta"].index), tiers
    for arm in ("a", "b"):
        rp = d["replay"][arm]
        assert all(len(r) == 8 and 0 <= r[1] < n for r in rp["intents"])
        assert set(rp["books"]) == set(d["meta"]["assets"])
    rows = d["robustness"]["rows"]
    assert rows[0]["label"] == "Flagship" and all(r["seeds"] for r in rows)
    assert all(s["parity"] in (True, False, None) for r in rows for s in r["seeds"])
    assert d["evidence"]["cards"] and 0 <= d["evidence"]["coverage"]["grounded_share"] <= 1

    page = bundle(d)
    assert not any(m in page for m in MARKERS), "unreplaced marker"
    blocks = re.findall(r'<script id="wt-data" type="application/json">(.*?)</script>', page, re.S)
    assert len(blocks) == 1 and json.loads(blocks[0])["meta"]["n_agents"] == n
    print(f"dashboard data test: OK — {n} agents, {len(f['parity'])} A/B pairs, "
          f"{len(rows)} robustness rows, bundle {len(page) // 1024} KB")


if __name__ == "__main__":
    main()

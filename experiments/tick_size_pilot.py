"""SEC Tick Size Pilot replication pipeline (v0 skeleton + synthetic dry-run).

Implements docs/tick-size-pilot-plan.md. Direction-only, masked scoring:
`score` refuses to run without evaluation/tsp_predictions.json, and records
that file's hash with every result. Real data pulls cache under
runs/scratch/tsp_data/ (gitignored); nothing synthetic is ever registered
as benchmark evidence.

    python3 -m experiments.tick_size_pilot --dry-run     # synthetic e2e proof
    python3 -m experiments.tick_size_pilot --score       # real run (needs
                                                         # sample + fetched data)

Estimators (free daily data, direction only):
- Corwin-Schultz (2012) 2-day high-low relative spread
- Abdi-Ranaldo (2017) close-to-close spread (robustness)
- Parkinson (1980) range volatility + close-to-close stdev
- Lo-MacKinlay variance ratio VR(5) (diagnostic, no robust z in v0)
"""
import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PREDICTIONS = ROOT / "evaluation" / "tsp_predictions.json"
CACHE = ROOT / "runs" / "scratch" / "tsp_data"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
WINDOWS = {"pre": ("20160701", "20160930"),
           "post": ("20161003", "20170331")}
METRICS = ("corwin_schultz_spread", "ar_spread", "parkinson_vol",
           "close_close_vol", "vr5_deviation")


# ---------- estimators ----------

def corwin_schultz(high, low):
    """Mean 2-day relative spread estimate; negative alphas dropped to 0."""
    k2 = math.sqrt(2.0)
    k3 = 3.0 - 2.0 * k2
    spreads = []
    for t in range(len(high) - 1):
        h1, l1, h2, l2 = high[t], low[t], high[t + 1], low[t + 1]
        if not (h1 > 0 and h2 > 0 and l1 > 0 and l2 > 0):
            continue
        beta = math.log(h1 / l1) ** 2 + math.log(h2 / l2) ** 2
        hh, ll = max(h1, h2), min(l1, l2)
        gamma = math.log(hh / ll) ** 2
        alpha = (k2 * math.sqrt(beta) - math.sqrt(beta)) / k3 \
            - math.sqrt(gamma / k3)
        if alpha < 0:
            alpha = 0.0
        spreads.append(2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha)))
    return sum(spreads) / len(spreads) if spreads else None


def abdi_ranaldo(close):
    """Close-to-close spread estimate on 2-day windows (AR 2017, simplified)."""
    mids = close
    num, den = [], []
    for t in range(2, len(mids)):
        c2 = (mids[t] + mids[t - 1]) / 2
        c4 = (mids[t - 1] + mids[t - 2]) / 2
        if c2 > 0 and c4 > 0:
            num.append((math.log(c2 / c4)) ** 2)
            den.append(math.log(mids[t] / mids[t - 2]) ** 2)
    if not den or sum(den) <= 0:
        return None
    pt = sum(num) / len(num) - sum(den) / len(den)
    if pt < 0:
        return None
    return 2 * (math.exp(pt / 2) - 1) / (1 + math.exp(pt / 2)) * math.sqrt(4)


def parkinson(high, low):
    rs = [math.log(h / l) ** 2 for h, l in zip(high, low) if h > 0 and l > 0]
    if len(rs) < 5:
        return None
    return math.sqrt(sum(rs) / (4 * math.log(2) * len(rs)))


def close_close_vol(close):
    rets = [close[i] / close[i - 1] - 1 for i in range(1, len(close))
            if close[i - 1] > 0]
    if len(rets) < 5:
        return None
    mu = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))


def vr5_deviation(close, q=5):
    """|VR(q) - 1|: deviation from the random walk (price (in)efficiency)."""
    rets = [close[i] / close[i - 1] - 1 for i in range(1, len(close))
            if close[i - 1] > 0]
    n = len(rets)
    if n < q * 3:
        return None
    mu = sum(rets) / n
    var1 = sum((r - mu) ** 2 for r in rets) / n
    sums = [sum(rets[i:i + q]) for i in range(n - q + 1)]
    mq = sum(sums) / len(sums)
    varq = sum((s - mq) ** 2 for s in sums) / (n - q + 1)
    if var1 <= 0:
        return None
    return abs(varq / (q * var1) - 1.0)


def all_metrics(high, low, close):
    return {"corwin_schultz_spread": corwin_schultz(high, low),
            "ar_spread": abdi_ranaldo(close),
            "parkinson_vol": parkinson(high, low),
            "close_close_vol": close_close_vol(close),
            "vr5_deviation": vr5_deviation(close)}


# ---------- sample list ----------

def load_sample(path):
    """Parse FINRA's pipe format; sanity-gate the group counts."""
    groups = {"C": [], "G1": [], "G2": [], "G3": []}
    for line in Path(path).read_text().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5 or parts[0] in ("Ticker_Symbol", "END_FILE", ""):
            continue
        if parts[4] in groups:
            groups[parts[4]].append(parts[0])
    bad = [g for g, n in groups.items() if not 100 <= len(n) <= 700]
    if bad:
        raise SystemExit(f"group counts out of plausible range for {bad}: "
                         f"{ {g: len(v) for g, v in groups.items()} } — check "
                         "the list file (expect ~400 per group)")
    return groups


# ---------- data ----------

def _epoch(datestr):
    return int(time.mktime(time.strptime(datestr, "%Y%m%d"))) 


def fetch_daily(ticker, d1, d2):
    """Daily OHLC from Yahoo's public chart endpoint, cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{ticker.replace('=', '_').replace('^', '_')}_{d1}_{d2}.json"
    if f.exists():
        return json.loads(f.read_text())
    import requests
    last = None
    for attempt in range(4):
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                params={"period1": _epoch(d1), "period2": _epoch(d2),
                        "interval": "1d"},
                headers=HEADERS, timeout=20)
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            out = {"ticker": ticker, "window": [d1, d2],
                   "high": q["high"], "low": q["low"], "close": q["close"]}
            f.write_text(json.dumps(out))
            time.sleep(0.4)
            return out
        except Exception as e:  # noqa: BLE001 — public endpoint, transient 429s
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def series(d):
    return ([x for x in d["high"] if x], [x for x in d["low"] if x],
            [x for x in d["close"] if x])


def window_metrics(ticker, d1, d2):
    data = fetch_daily(ticker, d1, d2)
    h, l, c = series(data)
    if len(c) < 15:
        return None
    return all_metrics(h, l, c)


def group_window_metrics(sample, group, w):
    d1, d2 = WINDOWS[w]
    per_ticker = [m for t in sample[group]
                  if (m := window_metrics(t, d1, d2))]
    if not per_ticker:
        return None
    out = {}
    for metric in METRICS:
        vals = [m[metric] for m in per_ticker if m.get(metric) is not None]
        out[metric] = sum(vals) / len(vals) if vals else None
    out["n"] = len(per_ticker)
    return out


# ---------- masked scoring ----------

def _direction(metric, test_groups):
    """DiD sign: (test post-pre) - (control post-pre), pooled test groups."""
    def agg(groups, w):
        rows = [group_window_metrics(SAMPLE, g, w) for g in groups]
        rows = [r for r in rows if r and r.get(metric) is not None]
        if not rows:
            return None
        return sum(r[metric] for r in rows) / len(rows)
    test_pre = agg(test_groups, "pre")
    test_post = agg(test_groups, "post")
    ctrl_pre = agg(["C"], "pre")
    ctrl_post = agg(["C"], "post")
    if None in (test_pre, test_post, ctrl_pre, ctrl_post):
        return None
    return (test_post - test_pre) - (ctrl_post - ctrl_pre)


def score(sample, register=False):
    if not PREDICTIONS.exists():
        raise SystemExit("no registered predictions — refusing to score "
                         "(pre-registration discipline)")
    pred = json.loads(PREDICTIONS.read_text())
    pred_hash = hashlib.sha256(PREDICTIONS.read_bytes()).hexdigest()[:16]
    results = []
    for p in pred["predictions"]:
        did = _direction(p["metric"], p["groups"])
        realized = ("up" if did and did > 0 else "down" if did and did < 0
                    else None)
        results.append({"id": p["id"], "metric": p["metric"],
                        "registered_direction": p["direction"],
                        "realized_did": round(did, 6) if did is not None else None,
                        "realized_direction": realized,
                        "hit": realized == p["direction"]})
    hits = sum(r["hit"] for r in results if r["realized_direction"])
    scored = [r for r in results if r["realized_direction"]]
    verdict = ("REPLICATION HIT" if len(scored) == len(results)
               and hits == len(results)
               else "REPLICATION FAILED" if len(scored) == len(results)
               and hits <= 1
               else "PARTIAL / INCONCLUSIVE")
    print(f"predictions hash {pred_hash} (registered {pred['registered']})")
    for r in results:
        print(f"  {r['id']} {r['metric']:22s} registered={r['registered_direction']:4s} "
              f"realized={r['realized_direction']} did={r['realized_did']} "
              f"{'HIT' if r['hit'] else 'MISS'}")
    print(f"verdict: {verdict} ({hits}/{len(scored)} scored predictions hit)")
    print("direction and ranking only — no effect sizes (BP red line)")
    return {"predictions_hash": pred_hash, "results": results,
            "verdict": verdict}


# ---------- synthetic dry-run ----------

def _synth_ohlc(rng, n_days, s):
    """Daily OHLC of a mid process with bid-ask bounce of half-spread s/2."""
    mid, out = 20.0, {"high": [], "low": [], "close": []}
    for _ in range(n_days):
        ret = rng.gauss(0, 0.015)
        mid *= 1 + ret
        intraday = abs(rng.gauss(0, 0.008)) * mid
        out["high"].append(mid + intraday / 2 + s / 2)
        out["low"].append(mid - intraday / 2 - s / 2)
        out["close"].append(mid + s / 2 * (1 if rng.random() < 0.5 else -1))
    return out


def dry_run():
    """Plant a spread widening (+ mild mean reversion) in G2/G3 post only;
    verify load→fetch→estimators→score recovers all three directions."""
    rng = random.Random(20261101)
    global SAMPLE
    SAMPLE = {"C": [], "G1": [], "G2": [], "G3": []}
    n_days = {"pre": 63, "post": 124}
    synthetic = {}
    for g in SAMPLE:
        for i in range(4):
            synthetic[f"{g}-{i}"] = {
                w: _synth_ohlc(rng, n, s=0.0) for w, n in n_days.items()}
    for g in ("G2", "G3"):
        for i in range(4):
            synthetic[f"{g}-{i}"]["post"] = _synth_ohlc(rng, n_days["post"],
                                                        s=0.05)
            # mild mean reversion in post: efficiency declines
            base = synthetic[f"{g}-{i}"]["post"]
            for k in range(2, len(base["close"])):
                base["close"][k] = 0.6 * base["close"][k] + 0.4 * \
                    base["close"][k - 1]
    # inject synthetic data instead of the network
    globals()["fetch_daily"] = (
        lambda t, d1, d2:
        synthetic[t]["pre" if d1 == WINDOWS["pre"][0] else "post"])
    globals()["SAMPLE"] = {g: [f"{g}-{i}" for i in range(4)] for g in SAMPLE}
    out = score(SAMPLE)
    hits = [r["hit"] for r in out["results"]]
    assert all(hits), f"dry run must recover all planted directions: {out}"
    print("dry run OK: pipeline recovers all planted directions end to end "
          "(synthetic data, nothing registered)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--score", action="store_true",
                    help="score real fetched data (requires sample + cache)")
    ap.add_argument("--sample", default=None,
                    help="FINRA-format pilot list (TSPilotSecurities.txt)")
    args = ap.parse_args()
    SAMPLE = None
    if args.dry_run:
        dry_run()
    elif args.score:
        if not args.sample:
            raise SystemExit("--score needs --sample (FINRA pipe-format list)")
        SAMPLE = load_sample(args.sample)
        score(SAMPLE)
    else:
        print(__doc__)

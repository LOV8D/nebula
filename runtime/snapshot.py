"""Trigger-time market snapshot (step 3 of the 2026-10-21 work order).

Replaces hand-filled scenario `assets.start` with real market levels pulled
at trigger time. Dependency-free: Yahoo's public chart endpoint (no key).

Mapping (demo instruments):
  EQ      <- SPY last close                       (index proxy)
  FX      <- EURUSD=X
  CMD     <- GC=F (gold front month)
  CRYPTO  <- BTC-USD
  IR      <- ^TNX 10Y yield, mapped to a notional note price via a rough
             duration approximation P ≈ 100 - 7 * (y%% - 4%%); vol from
             yield changes x duration. Documented approximation, demo-only.

  vol_bps <- stdev of last ~3 months of daily returns x 1e4.

    python3 -m runtime.cli snapshot          # fetch -> config/snapshot.json
"""
import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP_PATH = ROOT / "config" / "snapshot.json"
TTL_HOURS = 24
_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

SYMBOLS = {"EQ": "SPY", "FX": "EURUSD=X", "CMD": "GC=F", "CRYPTO": "BTC-USD"}


def _fetch_closes(sym, range_="3mo"):
    import requests
    last = None
    for attempt in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"range": range_, "interval": "1d"},
                             headers=_HEADERS, timeout=15)
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            return [c for c in res["indicators"]["quote"][0]["close"] if c]
        except Exception as e:  # noqa: BLE001 — public endpoint, transient SSL/429s
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def _vol_bps(closes):
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes)) if closes[i - 1]]
    if len(rets) < 10:
        return None
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))
    return round(sd * 1e4, 1)


def fetch():
    out = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "source": "Yahoo public chart endpoint (delayed)", "assets": {}}
    for asset, sym in SYMBOLS.items():
        closes = _fetch_closes(sym)
        out["assets"][asset] = {
            "start": round(closes[-1], 6),
            "vol_bps": _vol_bps(closes),
            "provenance": f"{sym} last close + 3mo daily-return stdev",
        }
    # IR: yield -> notional note price (duration-7 approximation, demo-only)
    y_closes = _fetch_closes("^TNX")
    y = y_closes[-1]
    dy = [y_closes[i] - y_closes[i - 1] for i in range(1, len(y_closes))
          if y_closes[i - 1]]                     # absolute bps moves
    mu = sum(dy) / len(dy)
    sd_dy = math.sqrt(sum((r - mu) ** 2 for r in dy) / (len(dy) - 1))
    out["assets"]["IR"] = {
        "start": round(max(80.0, min(120.0, 100 - 7 * (y - 4))), 4),
        "vol_bps": round(sd_dy * 7 * 100, 1),   # Δy(stdev, pct-pts) x duration -> price %; ×100 -> bps
        "provenance": (f"^TNX 10Y yield {y:.3f}% -> notional note price via "
                       "P=100-7*(y-4), duration approximation (demo-only)"),
    }
    return out


def refresh(force=False):
    if SNAP_PATH.exists() and not force:
        age_h = (time.time() - SNAP_PATH.stat().st_mtime) / 3600
        if age_h < TTL_HOURS:
            return json.loads(SNAP_PATH.read_text()), False
    snap = fetch()
    SNAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAP_PATH.write_text(json.dumps(snap, indent=1))
    return snap, True


def apply_snapshot(scenario):
    """Overlay real levels onto a scenario's asset block if it asks for it.
    Falls back to the scenario's static values (with a note) if the fetch
    fails — the demo must stay runnable offline."""
    if not scenario.get("use_snapshot"):
        return scenario
    try:
        snap, _ = refresh()
    except Exception as e:  # noqa: BLE001 — offline fallback
        print(f"snapshot fetch failed ({e.__class__.__name__}); "
              "using static asset levels")
        return scenario
    scenario = dict(scenario)
    scenario["assets"] = dict(scenario.get("assets", {}))
    scenario["snapshot"] = {"fetched_at": snap["fetched_at"],
                            "source": snap["source"]}
    for a, meta in snap["assets"].items():
        cur = dict(scenario["assets"].get(a, {}))
        cur["start"] = meta["start"]
        if meta["vol_bps"]:
            cur["vol_bps"] = meta["vol_bps"]
        cur["provenance"] = meta["provenance"]
        scenario["assets"][a] = cur
    print(f"snapshot overlay: {snap['fetched_at']} — " +
          ", ".join(f"{a}={v['start']}" for a, v in snap["assets"].items()))
    return scenario


def cmd_snapshot(args):
    snap, fresh = refresh(force=getattr(args, "force", False))
    tag = "fetched fresh" if fresh else f"cached (<{TTL_HOURS}h old)"
    print(f"snapshot [{tag}] {snap['fetched_at']} via {snap['source']}")
    for a, meta in snap["assets"].items():
        print(f"  {a:7s} start {meta['start']:>12.4f}  vol {meta['vol_bps']}bps  "
              f"[{meta['provenance']}]")
    print(f"-> {SNAP_PATH}  (scenarios with use_snapshot: true pick this up)")

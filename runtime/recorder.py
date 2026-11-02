"""Run artifacts: evidence pack per run (JSONL + manifest + summary).

Every order/trade/intent row carries provenance (persona, tier, provider,
model, prompt version) so any market outcome can be audited back to the
brain and persona that produced it — the BP evidence-system requirement.
"""
import hashlib
import json
import time
from pathlib import Path
from . import __version__


def _code_hash():
    """Digest of every package that decides what a run produces (see
    paths.CODE_PACKAGES). The prompt templates live in `llm.py`, so this
    covers model prompts too — `runtime_version` alone cannot tell two builds
    apart, and a run whose code is unidentified is not reproducible."""
    from .paths import ROOT, CODE_PACKAGES
    h = hashlib.md5()
    for pkg in CODE_PACKAGES:
        for p in sorted((ROOT / pkg).glob("*.py")):
            h.update(f"{pkg}/{p.name}".encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:10]


class RunRecorder:
    def __init__(self, out_dir, scenario, panel, gateway):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.f = {name: open(self.dir / f"{name}.jsonl", "w")
                  for name in ("marks", "trades", "intents", "violations", "events")}
        pop_hash = hashlib.md5(json.dumps(panel, sort_keys=True).encode()).hexdigest()[:10]
        self.manifest = {
            "run_id": self.dir.name,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "runtime_version": __version__,
            "code_hash": _code_hash(),
            "five_tuple": {
                "population": pop_hash,
                "intervention": scenario["id"],
                "mechanism": scenario.get("mechanism", {}),
                # prompt_version is a label; prompt_sha8 is the text actually
                # sent. Without the digest a sensitivity verdict cannot prove
                # which prompt produced it.
                "model": {"provider": gateway.provider, "model_id": gateway.model_id,
                          "prompt_version": getattr(gateway, "prompt_version", "p1"),
                          "prompt_sha8": getattr(gateway, "prompt_sha8", None)},
                "seed": scenario["seed"],
            },
            "days": scenario["days"],
            "rounds_per_day": scenario["rounds_per_day"],
            "n_agents": len(panel),
        }
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=1, default=str))

    def _w(self, name, obj):
        self.f[name].write(json.dumps(obj, default=lambda o: o.__dict__) + "\n")

    def _flush(self):
        # summarize() reads files mid-run; keep them current on disk
        for fh in self.f.values():
            fh.flush()

    def log_events(self, events):
        for e in events:
            self._w("events", e)
        self._flush()

    def log_trades(self, trades):
        for tr in trades:
            self._w("trades", tr)
        self._flush()

    def log_intents(self, intents):
        for d in intents:
            self._w("intents", d)
        self._flush()

    def log_violations(self, violations):
        for v in violations:
            self._w("violations", v)
        self._flush()

    def log_mark(self, asset, world, halted_resumed=False):
        m = world.marks[asset]
        self._w("marks", {
            "t": world.t, "asset": asset, "price": m.price, "volume": m.volume,
            "best_bid": m.best_bid, "best_ask": m.best_ask,
            "sigma": m.sigma, "halted": m.halted,
            **({"note": "halt_resumed"} if halted_resumed else {}),
        })
        self._flush()

    def write_summary(self, summary):
        (self.dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))

    def close(self):
        for fh in self.f.values():
            fh.close()

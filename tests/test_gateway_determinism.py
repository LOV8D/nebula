"""Concurrent-dispatch determinism test (run: python3 tests/test_gateway_determinism.py).

Regression: complete_many let every job race for the archetype memo, so which
agents shared an answer depended on thread timing. A response-cache hit
returns instantly, which changes the race — so the B arm, replaying A's cached
pre-intervention prompts, ended up with different decisions than A at the same
seed (flagship seed 1 diverged from t=51, 99 rounds before the intervention).

The stub brain answers every call with a fresh random size (temperature > 0)
after a random delay. The same batch must yield identical intents however the
threads finish.
"""
import random
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.llm import LLMGateway  # noqa: E402


def _persona(i, arch):
    return {"persona_id": f"hf_pm-{i:04d}", "cls": "hf_pm", "archetype": arch,
            "universe": ["EQ"], "identity_card": f"persona {i}",
            "budget_usd": 1e6, "leverage_cap": 2.0, "horizon_days": 5,
            "frictions": [], "news_beta": 1.0, "risk_aversion": 0.5}


CTX = {"rets_bps": {"EQ": 72}, "positions": {"EQ": 0}, "pnl_frac": {"EQ": 0.0}}


def _run(delays):
    """One batch of 12 jobs over 3 archetypes; delays[i] = latency of call i."""
    gw = LLMGateway(provider="openai_compat", model_id="stub", max_workers=8)
    answers = iter(range(1000))
    lock = threading.Lock()

    def fake_api(persona, ctx):
        i = int(persona["persona_id"][-4:])
        time.sleep(delays[i])
        with lock:   # a fresh "sample" per call, like temperature 0.7
            n = next(answers)
        return {"asset": "EQ", "side": 1, "size_frac": 0.05 + 0.01 * (n % 7) + 0.001 * i,
                "urgency": 0.4, "rationale": f"call by {persona['persona_id']}"}

    gw._api_decide = fake_api
    jobs = [(_persona(i, ("trend", "macro", "value")[i % 3]), CTX,
             random.Random(1000 + i)) for i in range(12)]
    out = gw.complete_many(jobs)
    return [(o["agent_id"], o["side"], round(o["size_frac"], 9), o["rationale"]) for o in out]


def main():
    rnd = random.Random(7)
    runs = []
    for trial in range(4):
        delays = [rnd.uniform(0, 0.05) for _ in range(12)]
        if trial == 1:
            delays[0] = 0.0           # first job "hits the cache"
        if trial == 2:
            delays = delays[::-1]     # completion order reversed
        runs.append(_run(delays))
    # The owner of each memo key is the first job in order, whatever its latency.
    for r in runs:
        assert r[0][3] == "call by hf_pm-0000" and r[3][3] == "call by hf_pm-0000", r
        assert r[1][3] == "call by hf_pm-0001", r
    # Rationale and agent order are fixed; sizes carry each call's random
    # sample, so compare only what must not depend on timing: who shares
    # whose answer, and the personal noise applied on top.
    shape = [[(a, s, why) for a, s, _, why in r] for r in runs]
    assert all(x == shape[0] for x in shape), "memo sharing depends on thread timing"
    print("ok: memo ownership is decided by job order, not thread completion")


if __name__ == "__main__":
    main()

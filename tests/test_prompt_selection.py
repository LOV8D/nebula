"""Prompt-selection regression test (run: python3 tests/test_prompt_selection.py).

Guards the p1/p2 sensitivity design: the system prompt sent on the wire must
be the one the gateway's prompt_version names, and every Intent must carry
the hash of the prompt actually sent. Regression: labels said p2 while the
payload was hardcoded to SYSTEM_PROMPT, silently voiding the prompt axis of
the sensitivity matrix.
"""
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402
from runtime.llm import (LLMGateway, PROMPTS, SYSTEM_PROMPT,  # noqa: E402
                         SYSTEM_PROMPT_P2, state_bucket)

PERSONA = {"persona_id": "t0001", "cls": "retail_mass", "archetype": "saver",
           "universe": ["EQ"], "identity_card": "test persona",
           "budget_usd": 10000, "leverage_cap": 1.0, "horizon_days": 30,
           "frictions": [], "news_beta": 1.0, "risk_aversion": 0.5}
CTX = {"rets_bps": {"EQ": 0}, "positions": {"EQ": 0}, "pnl_frac": {"EQ": 0.0}}


class _Resp:
    def raise_for_status(self):
        pass

    def json(self):
        payload = ('{"asset": "EQ", "side": "pass", "size_frac": 0, '
                   '"urgency": 0, "rationale": "probe"}')
        return {"choices": [{"message": {"content": payload}}]}


def main():
    assert SYSTEM_PROMPT != SYSTEM_PROMPT_P2, "p2 must be a real variant"
    captured = []
    orig = requests.post
    requests.post = lambda url, **kw: (captured.append(kw), _Resp())[1]
    try:
        for pv in ("p1", "p2"):
            gw = LLMGateway(provider="openai_compat", model_id="stub",
                            base_url="http://localhost:1", api_key="k",
                            cache_path=None, prompt_version=pv)
            out = gw.complete(PERSONA, CTX, random.Random(0))
            sent = captured[-1]["json"]["messages"][0]["content"]
            assert sent == PROMPTS[pv], f"{pv}: wire payload is not {pv}'s prompt"
            assert out["prompt_version"] == pv
            want = hashlib.sha256(PROMPTS[pv].encode()).hexdigest()[:8]
            assert out["prompt_sha8"] == want, "Intent prompt hash mismatch"
        # memo path must stamp the instance version too: seed the memo with a
        # base decision whose score always lands below the personal threshold,
        # forcing the early-return Intent
        gw = LLMGateway(provider="openai_compat", model_id="stub",
                        base_url="http://localhost:1", api_key="k",
                        cache_path=None, prompt_version="p2")
        gw.memo[(PERSONA["cls"], PERSONA["archetype"],
                 state_bucket(CTX))] = {"asset": "EQ", "side": 1,
                                        "size_frac": 0.1, "urgency": 0.5,
                                        "_score": 0.0, "rationale": "memo"}
        out = gw.complete(PERSONA, CTX, random.Random(1))
        assert out["prompt_version"] == "p2", "memo path lost prompt_version"
        assert "prompt_sha8" in out
    finally:
        requests.post = orig
    print("prompt-selection test: OK — wire payload, Intent provenance and "
          "prompt hash all follow prompt_version")


if __name__ == "__main__":
    main()

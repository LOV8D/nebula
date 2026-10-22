"""LLM gateway: one call site for all Tier-A cognition.

Providers:
  mock         — deterministic persona-param heuristics; same Intent schema,
                 same provenance pipeline; lets the whole cluster run offline.
  openai_compat— any OpenAI-compatible endpoint (vLLM serving Qwen-8B-class,
                 DeepSeek API, ...). Set base_url/model via scenario or env.

Every Intent carries provider/model/prompt_version provenance so any order
can be audited to the brain that produced it. A (archetype, state-bucket)
memo cache collapses repeated decisions — the Tier-B "compiled policy"
amortization from plan §8.
"""
import hashlib
import json
import os
import random
import threading
from pathlib import Path

# Prompt variants for model × prompt sensitivity (BP red-line deliverable).
# p1: neutral market-participant framing. p2: deliberately different
# behavioral framing — if conclusions flip between variants, that
# instability is itself a reported result, not noise.
PROMPTS = {
    "p1": None,   # filled after SYSTEM_PROMPT is defined
    "p2": None,
}
_ENV_KEYS = ("BRAIN_BASE_URL", "BRAIN_API_KEY", "BRAIN_MODEL", "BRAIN_MAX_WORKERS")
_ENV_LOADED = False


def load_env():
    """Read repo-root .env into os.environ (existing env vars win).
    This is the single place users configure the remote brain."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    f = Path(__file__).resolve().parent.parent / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in _ENV_KEYS and k not in os.environ:
            os.environ[k] = v


def env_overrides():
    """(base_url, api_key, model_id) from .env/env — None where unset."""
    load_env()
    return (os.environ.get("BRAIN_BASE_URL"), os.environ.get("BRAIN_API_KEY"),
            os.environ.get("BRAIN_MODEL"))
SYSTEM_PROMPT = (
    "You are one participant in a simulated financial market. You are NOT an "
    "assistant. Stay inside your persona: your constraints, horizon, risk "
    "attitudes, information sources and frictions. You see only the "
    "information given. Respond ONLY with a JSON object: "
    '{"asset": str, "side": "buy"|"sell"|"pass", "size_frac": float 0..1, '
    '"urgency": float 0..1, "rationale": str<=200 chars}. size_frac is the '
    "fraction of your deployable budget for this decision. urgency>=0.7 means "
    "a market order; lower means a patient limit order."
)

SYSTEM_PROMPT_P2 = (
    "You are a real human investor with habits, limited attention and "
    "emotional biases — NOT an optimizer. Decide the way you personally "
    "would at your kitchen table, glancing at your phone. You see only the "
    "information given; it is normal to do nothing, to hesitate, or to "
    "follow the crowd. Respond ONLY with a JSON object: "
    '{"asset": str, "side": "buy"|"sell"|"pass", "size_frac": float 0..1, '
    '"urgency": float 0..1, "rationale": str<=200 chars}. urgency>=0.7 '
    "means act now at market; lower means a patient limit order."
)
PROMPTS["p1"] = SYSTEM_PROMPT
PROMPTS["p2"] = SYSTEM_PROMPT_P2


def state_bucket(ctx):
    """Canonicalize the decision context into a memo key."""
    ev = ctx.get("events", [])
    evk = ";".join(f"{e['headline'][:24]}:{round(e['sentiment'],1)}" for e in ev[:2])
    retk = ";".join(f"{a}:{'+' if r>0 else '-'}{min(9,abs(int(r)))}"
                    for a, r in sorted(ctx.get("rets_bps", {}).items()))
    return hashlib.md5(f"{evk}|{retk}".encode()).hexdigest()[:10]


class LLMGateway:
    def __init__(self, provider="mock", model_id="mock-heuristic-v1",
                 base_url=None, api_key=None, memo_on=True, cache_path=None,
                 max_workers=8, prompt_version="p1"):
        self.provider, self.model_id = provider, model_id
        self.prompt_version = prompt_version
        # Hash of the prompt text actually sent; the version name above is
        # only a label. Caught once already: labels said p2 while the wire
        # payload was still SYSTEM_PROMPT.
        self.prompt_sha8 = hashlib.sha256(
            PROMPTS[prompt_version].encode()).hexdigest()[:8]
        self.max_workers = max(1, int(max_workers))
        self._lock = threading.Lock()   # memo / cache / usage are thread-shared
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "EMPTY")
        self.memo = {}
        self.memo_on = memo_on
        # File-backed raw-response cache: makes real-model runs replayable
        # (temperature > 0 is not) and amortizes shared prompts across runs.
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache = {}
        if self.cache_path and self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text())
            except Exception:  # noqa: BLE001 — corrupt cache => cold start
                self.cache = {}
        self.usage = {"calls": 0, "cache_hits": 0, "memo_hits": 0,
                      "in_tokens": 0, "out_tokens": 0, "errors": 0,
                      "consecutive_errors": 0, "error_detail": None}

    # ------------------------------------------------------------------
    def complete(self, persona, ctx, rng):
        """persona: panel dict; ctx: decision-context digest. -> dict Intent."""
        key = (persona["cls"], persona["archetype"], state_bucket(ctx))
        base = None
        with self._lock:
            if self.memo_on and key in self.memo:
                base = self.memo[key]
                self.usage["memo_hits"] += 1
        if base is None:
            with self._lock:
                self.usage["calls"] += 1
            if self.provider == "mock":
                base = self._mock_decide(persona, ctx, rng)
            else:
                base = self._api_decide(persona, ctx)
            if base is not None:
                with self._lock:
                    self.memo[key] = base
        if base is None:
            return None
        # Individual noise on the DECISION itself, not just size: the memo
        # carries the archetype's base tendency; each person re-decides with
        # idiosyncratic dispersion. Without this, one archetype trades as a
        # synchronized block (one rng draw for 100 agents).
        out = dict(base)
        score_i = out.pop("_score", None)
        if score_i is not None:
            s_i = score_i + rng.uniform(-0.18, 0.18)
            thr = 0.22 / max(persona["news_beta"], 0.3)
            if abs(s_i) < thr:
                return {"asset": out["asset"], "side": 0, "size_frac": 0.0,
                        "urgency": 0.0, "rationale": "below personal threshold",
                        "agent_id": persona["persona_id"], "provider": self.provider,
                        "model": self.model_id, "prompt_version": self.prompt_version,
                        "prompt_sha8": self.prompt_sha8}
            out["side"] = 1 if s_i > 0 else -1
            out["size_frac"] = max(0.02, min(0.6, abs(s_i) * (1.3 - persona["risk_aversion"])))
            out["urgency"] = min(1.0, 0.3 + abs(s_i) * 0.45)
        out["size_frac"] = max(0.0, min(1.0, out["size_frac"] * rng.lognormvariate(0, 0.25)))
        out["urgency"] = max(0.0, min(1.0, out["urgency"] * rng.lognormvariate(0, 0.2)))
        out.update(agent_id=persona["persona_id"], provider=self.provider,
                   model=self.model_id, prompt_version=self.prompt_version,
                   prompt_sha8=self.prompt_sha8)
        return out

    # ------------------------------------------------------------------
    def complete_many(self, jobs):
        """Fire a batch of decisions concurrently. jobs: [(persona, ctx, rng)];
        returns results aligned with jobs (None where a call failed).
        Concurrency applies to API providers only; every job carries its own
        RNG, so results are independent of thread completion order.
        """
        if self.provider == "mock" or len(jobs) <= 1:
            return [self.complete(*j) for j in jobs]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(jobs))) as ex:
            return list(ex.map(lambda j: self.complete(*j), jobs))

    # ------------------------------------------------------------------
    def _mock_decide(self, persona, ctx, rng):
        """Persona-param heuristics standing in for the 8B brain offline.

        News-weighted directional tilt + momentum/herding + disposition +
        stop-loss. Deliberately crude: quality comes from the real model via
        openai_compat; provenance 'mock' marks these runs as pipeline tests.
        """
        uni = persona["universe"]
        if not uni:
            return None
        evs = ctx.get("events", [])
        news_score = {a: 0.0 for a in uni}
        for e in evs:
            for a in e["assets"]:
                if a in news_score:
                    news_score[a] += e["sentiment"] * e["impact"]
        rets = ctx.get("rets_bps", {})
        scores, rationale = {}, ""
        mr_styles = {"value", "bond", "balanced", "swf", "bank"}
        for a in uni:
            s = persona["news_beta"] * news_score[a]
            mom = rets.get(a, 0.0) / 1e4     # true fraction
            if abs(mom) > 0.0005:            # herding needs an actual move
                s += persona["herding"] * mom * 70.0
            if persona.get("style") in mr_styles:
                s -= mom * 150.0              # valuation-sensitive styles fade moves
            pnl = ctx.get("pnl_frac", {}).get(a, 0.0)
            if pnl > 0.05 and rng.random() < persona["disposition"]:
                s -= 0.6                      # disposition: sell winners
                rationale = "take the win"
            elif pnl < -0.10 and rng.random() < persona["disposition"] * 0.5:
                s -= 0.5                      # ...and only grudgingly cut losers
                rationale = "give up on the loser"
            day = ctx.get("day_ret", {}).get(a, 0.0)
            if "stop_loss" in persona and day < persona["stop_loss"]:
                s, rationale = -3.0, f"stop-loss hit ({day:.1%})"
            s += rng.uniform(-0.10, 0.10)   # exploration: dead books still trade
            scores[a] = s
        asset = max(scores, key=lambda a: abs(scores[a]))
        s = scores[asset]
        thr = 0.22 / max(persona["news_beta"], 0.3)
        if abs(s) < thr:
            return {"asset": asset, "side": 0, "size_frac": 0.0, "urgency": 0.0,
                    "rationale": "no signal above threshold"}
        side = 1 if s > 0 else -1
        size = min(0.6, abs(s) * (1.3 - persona["risk_aversion"]))
        urg = min(1.0, 0.3 + abs(s) * 0.45)   # strong signals pay the spread
        fee = ctx.get("fee_note")
        if fee and side == -1 and persona["cls"].startswith("retail") and rng.random() < 0.5:
            size *= 1.3                      # fee-driven redemption tilt
            rationale = (rationale or "redemption") + " +fee sensitivity"
        return {"asset": asset, "side": side, "size_frac": max(0.02, size),
                "urgency": urg, "_score": s,
                "rationale": rationale or f"signal {s:.2f} on {asset}"}

    # ------------------------------------------------------------------
    def _api_decide(self, persona, ctx):
        import requests
        user = self._build_user_prompt(persona, ctx)
        with self._lock:
            self.usage["in_tokens"] += (
                len(PROMPTS[self.prompt_version]) + len(user)) // 4  # estimate
        key = hashlib.sha256(
            f"{self.model_id}|{self.prompt_version}|{user}".encode()).hexdigest()
        txt = self.cache.get(key)
        if txt is None:
            import time as _time
            for attempt in range(3):
                try:
                    r = requests.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.model_id, "temperature": 0.7,
                              "messages": [{"role": "system",
                                            "content": PROMPTS[self.prompt_version]},
                                           {"role": "user", "content": user}]},
                        timeout=120)
                    r.raise_for_status()
                    txt = r.json()["choices"][0]["message"]["content"]
                    with self._lock:
                        self.usage["out_tokens"] += len(txt) // 4
                        if self.cache_path is not None:
                            self.cache[key] = txt
                            self._save_cache()
                        self.usage["consecutive_errors"] = 0
                    break
                except Exception as e:  # noqa: BLE001 — retry, then give up this call
                    with self._lock:
                        self.usage["errors"] += 1
                        self.usage["consecutive_errors"] = self.usage.get(
                            "consecutive_errors", 0) + 1
                        code = getattr(getattr(e, "response", None), "status_code", None)
                        if not self.usage.get("error_detail"):
                            self.usage["error_detail"] = str(code or e.__class__.__name__)
                    if attempt < 2:
                        _time.sleep(2 ** attempt * 2)  # 2 s, 4 s backoff
                        continue
                    return None
            # gentle pacing: stay under provider rate limits on sustained runs
            _time.sleep(0.3)
        else:
            self.usage["cache_hits"] += 1
        try:
            j = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
            side = {"buy": 1, "sell": -1}.get(str(j.get("side", "pass")).lower(), 0)
            return {"asset": j.get("asset", "EQ"), "side": side,
                    "size_frac": float(j.get("size_frac", 0)),
                    "urgency": float(j.get("urgency", 0.5)),
                    "rationale": str(j.get("rationale", ""))[:200]}
        except Exception:  # noqa: BLE001 — malformed JSON from the model
            self.usage["errors"] += 1
            return None

    def _save_cache(self):
        if self.cache_path is None:
            return
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache))
        tmp.replace(self.cache_path)



    def _build_user_prompt(self, persona, ctx):
        evs = "\n".join(f"- [{e['source']}] {e['headline']} "
                        f"(sentiment {e['sentiment']:+.1f}, assets {','.join(e['assets'])})"
                        for e in ctx.get("events", [])) or "- (quiet, no news)"
        rets = ", ".join(f"{a} {r:+.0f}bps" for a, r in ctx["rets_bps"].items())
        holdings = ", ".join(f"{a}: pos {ctx['positions'].get(a, 0):.4g} "
                             f"(pnl {ctx.get('pnl_frac', {}).get(a, 0):+.1%})"
                             for a in persona["universe"]) or "all cash"
        return (f"YOUR PERSONA:\n{persona['identity_card']}\n"
                f"Constraints: budget ${persona['budget_usd']:.0f}, leverage cap "
                f"{persona['leverage_cap']}, horizon {persona['horizon_days']}d, "
                f"universe {persona['universe']}, frictions {persona['frictions']}.\n\n"
                f"MARKET (this round):\nNews:\n{evs}\nMoves since last round: {rets}\n"
                f"Your holdings: {holdings}\n"
                f"{ctx.get('fee_note', '')}\n"
                f"Decide now. JSON only.")

def check_endpoint(base_url, model_id=None, api_key=None, probe_prompt=True):
    """Preflight gate for real-brain runs. The definitive test is a minimal
    chat completion (auth + model alive); /models is informational only
    because many providers list an incomplete set. Reasoning models burn
    tokens on the chain of thought before emitting content, so the probe
    budget must be generous and JSON-compliance is a warning, not a failure
    (production prompts have no max_tokens cap)."""
    import requests
    base = base_url.rstrip("/")
    hdr = {"Authorization": f"Bearer {api_key or 'EMPTY'}"}
    listed = None
    try:
        r = requests.get(f"{base}/models", headers=hdr, timeout=8)
        if r.status_code == 200:
            listed = [m.get("id") for m in r.json().get("data", [])][:8]
    except Exception:  # noqa: BLE001 — listing is optional information
        pass
    if not probe_prompt:
        if listed is None:
            return False, f"cannot reach {base}"
        return True, f"endpoint up, models: {listed}"
    try:
        r = requests.post(
            f"{base}/chat/completions", headers=hdr, timeout=90,
            json={"model": model_id, "max_tokens": 512, "messages": [
                {"role": "user", "content": 'Reply with exactly: {"ok":1}'}]})
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        txt = msg.get("content") or ""
        finish = r.json()["choices"][0].get("finish_reason")
        if "{" in txt and "}" in txt:
            json_note = "JSON ok"
        elif txt:
            json_note = "WARNING: responded but not JSON — verify prompt format"
        elif finish == "length" or msg.get("reasoning_content"):
            json_note = ("WARNING: empty content (reasoning consumed the "
                         "probe budget — endpoint fine, format untested)")
        else:
            return False, f"model '{model_id}' returned empty content (finish={finish})"
        note = "" if listed is None else f"; listed: {listed[:4]}"
        return True, f"chat probe ok, model '{model_id}' responds, {json_note}{note}"
    except Exception as e:  # noqa: BLE001
        return False, f"chat probe failed on {base}: {e.__class__.__name__}: {e}"

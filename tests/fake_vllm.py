"""Minimal OpenAI-compatible stub standing in for `vllm serve`.

For GPU-less end-to-end tests of the real-brain path only. Returns
plausible Intent JSON: keyword heuristics on the news lines in the prompt,
so the wording A/B actually differentiates. NOT a model.

    python3 tests/fake_vllm.py --port 8000
"""
import argparse
import json
import re
import time as _time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY = 0.0

NEG = ("warns", "intensified", "cannot be ruled out", "cuts", "tightens",
       "thin liquidity", "margin", "falling", "selloff")
POS = ("steady", "solid", "balanced", "resumes", "higher", "demand", "inflows")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            self._send({"object": "list", "data": [{"id": "fake-qwen-8b"}]})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        if DELAY:
            _time.sleep(DELAY)
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        user = req["messages"][-1]["content"]
        m = re.search(r"universe \[(.*?)\]", user)
        assets = re.findall(r'"([A-Z]+)"', m.group(1)) if m else ["EQ"]
        news = "\n".join(l for l in user.splitlines() if l.startswith("- ["))
        score = sum(w in news for w in NEG) - sum(w in news for w in POS)
        if abs(score) < 1 and "sell" in user.lower():
            score = -1  # losses mentioned
        side = "sell" if score > 0 else ("buy" if score < 0 else "pass")
        asset = assets[0] if assets else "EQ"
        content = json.dumps({
            "asset": asset, "side": side,
            "size_frac": round(0.1 + 0.12 * abs(score), 3),
            "urgency": round(0.3 + 0.15 * abs(score), 3),
            "rationale": f"stub: net tone score {score} on {asset}"})
        self._send({"id": "chatcmpl-stub", "object": "chat.completion",
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": 2500, "completion_tokens": 250}})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--delay", type=float, default=0.0, help="simulated latency per call, s")
    a = ap.parse_args()
    DELAY = a.delay
    print(f"fake vLLM on :{a.port} (stub heuristics, not a model)")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

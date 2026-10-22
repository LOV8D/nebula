"""Core value types shared across the runtime."""
from dataclasses import dataclass, field
from typing import Optional

BUY, SELL = 1, -1
ASSETS = ("EQ", "IR", "FX", "CMD", "CRYPTO")


@dataclass
class Order:
    asset: str
    agent_id: str
    side: int                 # +1 buy, -1 sell
    qty: float
    limit: Optional[float] = None   # None => market order
    t: int = 0
    origin: str = "policy"    # tier provenance: rule / policy / llm


@dataclass
class Trade:
    asset: str
    price: float
    qty: float
    t: int
    buyer: str = ""
    seller: str = ""


@dataclass
class MarketEvent:
    t: int
    headline: str
    sentiment: float          # -1..1, framing-dependent
    assets: list
    impact: float = 1.0       # attention reach 0..1
    source: str = "wire"


@dataclass
class Intent:
    """What an agent wants; the execution wrapper turns it into legal orders.
    The LLM never quotes prices — only direction/size/urgency."""
    agent_id: str
    asset: str
    side: int                 # +1 buy, -1 sell, 0 pass
    size_frac: float          # fraction of deployable budget
    urgency: float            # 0..1; >=0.7 => market order
    rationale: str = ""
    provider: str = ""        # llm provider provenance
    model: str = ""
    prompt_version: str = ""


@dataclass
class Violation:
    t: int
    agent_id: str
    kind: str                 # budget / mandate / info_timing / halted / min_size
    detail: str
    action: str = "clipped"   # clipped / dropped / deferred

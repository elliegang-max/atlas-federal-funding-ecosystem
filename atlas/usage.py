"""Token accounting.

Every API call in this project goes through `record`, so the numbers in the
report's tokenomics section come from the app itself rather than an estimate.
Prices are per million tokens.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path

# gpt-6-luna list price, USD per 1M tokens.
PRICE_INPUT = 1.25
PRICE_CACHED_INPUT = 0.125
PRICE_OUTPUT = 10.00

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "usage_log.jsonl"


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0          # uncached prompt tokens
    cached_input_tokens: int = 0   # prompt tokens served from cache
    output_tokens: int = 0
    by_stage: dict = field(default_factory=dict)

    @property
    def cost(self) -> float:
        return (
            self.input_tokens / 1e6 * PRICE_INPUT
            + self.cached_input_tokens / 1e6 * PRICE_CACHED_INPUT
            + self.output_tokens / 1e6 * PRICE_OUTPUT
        )

    def add(self, stage: str, response) -> None:
        u = getattr(response, "usage", None)
        if u is None:
            return
        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0
        prompt = (getattr(u, "prompt_tokens", 0) or 0) - cached
        out = getattr(u, "completion_tokens", 0) or 0

        self.calls += 1
        self.input_tokens += prompt
        self.cached_input_tokens += cached
        self.output_tokens += out

        s = self.by_stage.setdefault(
            stage, {"calls": 0, "input": 0, "cached": 0, "output": 0}
        )
        s["calls"] += 1
        s["input"] += prompt
        s["cached"] += cached
        s["output"] += out

    def summary(self) -> dict:
        d = asdict(self)
        d["cost_usd"] = round(self.cost, 6)
        for stage, s in d["by_stage"].items():
            s["cost_usd"] = round(
                s["input"] / 1e6 * PRICE_INPUT
                + s["cached"] / 1e6 * PRICE_CACHED_INPUT
                + s["output"] / 1e6 * PRICE_OUTPUT,
                6,
            )
        return d


_lock = threading.Lock()


def append_log(record: dict) -> None:
    """Append one run's usage to data/usage_log.jsonl for the report."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with LOG_PATH.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

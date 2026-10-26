"""Input guards for the researcher-facing agent.

Three distinct risks, three distinct defenses. They are kept here rather than
inside the prompt because a defense written only as a prompt instruction is a
request, not a control — the model is free to ignore it, and nothing records
that it did.

  1. Prompt injection. The research description is untrusted text that reaches a
     model which has a system prompt worth stealing or overriding. Pattern scan
     first, then the prompt isolates the text as data.
  2. Runaway spend. A long description costs more to process and a loop of them
     costs more again. Length cap plus a per-process spend ceiling.
  3. Off-task use. The app is a funding matcher; a general chatbot costs money
     and invites both of the above.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

MAX_CHARS = 6000
MIN_CHARS = 20

# Spend ceiling for one process lifetime. A bug that loops the matcher stops
# here instead of draining the course key.
SPEND_CEILING_USD = 5.00

# Requests per IP per window.
RATE_LIMIT = 20
RATE_WINDOW_S = 300


INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instruction|prompt|direction|rule)",
     "attempt to override prior instructions"),
    (r"disregard\s+(the\s+)?(system|above|previous|earlier)", "attempt to discard the system prompt"),
    (r"(reveal|show|print|repeat|output|dump)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instruction)",
     "attempt to extract the system prompt"),
    (r"you\s+are\s+now\s+(a|an)\s+", "attempt to reassign the assistant's role"),
    (r"\bnew\s+(instructions?|rules?|system\s+prompt)\b", "attempt to install new instructions"),
    (r"</?(system|assistant)\s*>", "attempt to forge a conversation role"),
    (r"\bDAN\b|\bjailbreak\b|developer\s+mode", "known jailbreak phrasing"),
    (r"(print|list|send|email|exfiltrate).{0,30}(api[_\s-]?key|secret|credential|env\s+var|portkey)",
     "attempt to extract credentials"),
    # \w+ misses every hyphenated agency name — ARPA-E, ARPA-H, SBIR/STTR —
    # which is most of the ones someone would try to promote.
    (r"\b(rank|put|place|list|show)\s+[\w\-/&.' ]{2,40}?\s*(first|top|#\s?1|number one|at the top)\b"
     r"[^.]{0,60}?\b(regardless|no matter|whatever|anyway|always|even if)\b",
     "attempt to rig the ranking"),
    (r"\b(always|must)\s+(rank|recommend|pick|choose)\b", "attempt to fix the output"),
]

_COMPILED = [(re.compile(p, re.I | re.S), why) for p, why in INJECTION_PATTERNS]


@dataclass
class GuardResult:
    ok: bool
    reason: str = ""
    detail: str = ""
    matched: str = ""


def check_input(text: str) -> GuardResult:
    """Run every input guard. Returns the first failure, or ok."""
    stripped = (text or "").strip()

    if len(stripped) < MIN_CHARS:
        return GuardResult(
            False, "too_short",
            "Describe the research in a sentence or two so there is something to match on.",
        )
    if len(stripped) > MAX_CHARS:
        return GuardResult(
            False, "too_long",
            f"Descriptions are capped at {MAX_CHARS:,} characters to keep the cost per "
            f"query bounded. Yours is {len(stripped):,}.",
        )

    for pattern, why in _COMPILED:
        hit = pattern.search(stripped)
        if hit:
            return GuardResult(
                False, "injection",
                "This looks like an attempt to change how the assistant behaves rather "
                "than a description of research, so it was not sent to the model.",
                f"{why}: {hit.group(0)[:80]!r}",
            )

    return GuardResult(True)


class SpendGuard:
    """Process-lifetime spend ceiling."""

    def __init__(self, ceiling: float = SPEND_CEILING_USD) -> None:
        self.ceiling = ceiling
        self.spent = 0.0

    def would_exceed(self) -> bool:
        return self.spent >= self.ceiling

    def record(self, usd: float) -> None:
        self.spent += usd

    @property
    def remaining(self) -> float:
        return max(0.0, self.ceiling - self.spent)


class RateLimiter:
    """Fixed-window per-key rate limit."""

    def __init__(self, limit: int = RATE_LIMIT, window_s: int = RATE_WINDOW_S) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < self.window_s]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

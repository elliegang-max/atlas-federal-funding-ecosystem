"""The researcher-facing matching agent.

Three stages, and only two of them cost tokens:

  1. brief    — one structured call turning free text into a ResearchBrief.
  2. retrieve — pure Python. Scores all 118 nodes against the brief and keeps
                the best dozen. No model involved.
  3. rank     — one structured call over those dozen condensed profiles.

Stage 2 is the reason this is affordable. Handing all 118 full profiles to the
model would be roughly 150,000 input tokens per question. Retrieving first and
sending twelve condensed ones costs around 6,000, for an answer that is better
rather than worse, because the model is reasoning over a short relevant list
instead of skimming a long one.
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone

from openai import LengthFinishReasonError

from atlas.config import MODEL, REPO_ROOT, make_async_client
from atlas.graph import load_graph, path_label
from atlas.schema import EnrichedNode, MatchResult, Match, ResearchBrief
from atlas.usage import Usage

BRIEF_PROMPT = REPO_ROOT / "prompts" / "brief.md"
RANK_PROMPT = REPO_ROOT / "prompts" / "rank.md"

SHORTLIST_SIZE = 12

# Ranking writes five prose fields per candidate, so output grows with the
# shortlist and the output cap — not the input bill — is what binds first.
# Measured in experiments/shortlist_sweep.py: twenty candidates overruns the
# cap and the call returns nothing at all. The ladder below retries with fewer
# candidates rather than failing the request.
RANK_MAX_OUTPUT = 9000
SHORTLIST_LADDER = [SHORTLIST_SIZE, 8, 6]


def _prompt(path) -> str:
    if not path.is_file():
        sys.exit(f"Prompt not found at {path}")
    return path.read_text()


# --- stage 1: brief ---------------------------------------------------------


async def make_brief(client, description: str, usage: Usage) -> ResearchBrief:
    response = await client.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": _prompt(BRIEF_PROMPT)},
            {
                "role": "user",
                # Delimiters matter: they are what lets the system prompt refer
                # to this span as data rather than as part of the conversation.
                "content": f"<research_description>\n{description}\n</research_description>",
            },
        ],
        response_format=ResearchBrief,
        max_completion_tokens=2000,
    )
    usage.add("brief", response)
    brief = response.choices[0].message.parsed
    if brief is None:
        raise ValueError("brief model returned nothing")
    return brief


# --- stage 2: retrieval (no model) ------------------------------------------


# Six-character stems, so "neurology" and "neurological" match but
# "neuroimmunology" does not. Exact token matching misses most morphological
# variation, and agencies describe themselves in different words than
# researchers use.
def _stems(text: str) -> set[str]:
    return {w[:6] for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def score_node(node: EnrichedNode, brief: ResearchBrief) -> tuple[float, list[str]]:
    """Heuristic relevance score plus the reasons it scored."""
    p = node.profile
    score = 0.0
    why: list[str] = []

    if node.level == "root":
        return -99, []

    # Only bodies that actually fund companies are useful answers.
    if p.has_venture_arm:
        score += 4
    else:
        score -= 6
        why.append("no venture arm")

    # A department is context for the map, not something you apply to.
    score += {"program": 2.5, "agency": 1.0, "department": -3.0}.get(node.level, 0)

    # Sector tags barely separate anything inside NIH — every institute is
    # "health" and "biotech" — so they count for little. What a body says it
    # funds is the signal that actually discriminates.
    shared = set(brief.sectors) & (set(node.sectors) | set(p.sectors))
    if shared:
        score += 1.2 * len(shared)
        why.append("sector: " + ", ".join(sorted(shared)))

    needles = _stems(" ".join(brief.keywords + [brief.modality, brief.indication]))

    focus_hits = _stems(" ".join(p.focus_areas)) & needles
    if focus_hits:
        score += 4.0 * min(len(focus_hits), 6)
        why.append("funds: " + ", ".join(sorted(focus_hits)[:5]))

    prose_hits = _stems(
        " ".join([node.name, node.full_name, node.note, p.overview, p.venture_arm])
    ) & needles
    if prose_hits:
        score += 1.2 * min(len(prose_hits), 8)
        why.append("mentions: " + ", ".join(sorted(prose_hits)[:4]))

    if brief.stage in p.stages or "any" in p.stages:
        score += 3
        why.append(f"stage: {brief.stage}")

    need = brief.amount_needed_usd
    if need and p.check_sizes:
        bands = [(c.min_usd, c.max_usd) for c in p.check_sizes if c.max_usd]
        if any(lo <= need <= hi for lo, hi in bands):
            score += 6
            why.append("check size covers the ask")
        elif any(need <= hi * 3 for _, hi in bands):
            score += 2
            why.append("ask is within a few awards of their ceiling")
        else:
            score -= 2
            why.append("ask exceeds their usual award")

    if p.confidence == "low":
        score -= 1

    return score, why


def shortlist(brief: ResearchBrief, k: int = SHORTLIST_SIZE) -> list[tuple[EnrichedNode, float, list[str]]]:
    scored = []
    for node in load_graph():
        s, why = score_node(node, brief)
        if s > 0:
            scored.append((node, s, why))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]


def condense(node: EnrichedNode) -> str:
    """A compact profile for the ranking prompt. Contacts and sources are left
    out — the interface fetches those from the graph once a match is shown, so
    paying to put them through the model would be waste."""
    p = node.profile
    checks = "; ".join(
        f"{c.label}: ${c.min_usd:,}-${c.max_usd:,}"
        + (f" over {c.duration_months}mo" if c.duration_months else "")
        + (f" ({c.note})" if c.note else "")
        for c in p.check_sizes
    ) or "not published"
    parent = path_label(node.id)
    return (
        f"### {node.id} — {node.name} ({node.full_name})\n"
        f"Sits under: {parent or 'top level'}\n"
        f"Venture arm: {p.venture_arm}\n"
        f"Overview: {p.overview}\n"
        f"Check sizes: {checks}\n"
        f"Stages: {', '.join(p.stages) or 'unknown'}\n"
        f"Focus: {', '.join(p.focus_areas[:8]) or 'unknown'}\n"
        f"Timeline: {p.application_timeline}\n"
        f"Eligibility: {p.eligibility}\n"
        f"Relationship: {p.relationship_note}\n"
        f"Profile confidence: {p.confidence}"
        + (f" — least certain: {p.uncertainty_note}" if p.uncertainty_note else "")
    )


# --- stage 3: rank ----------------------------------------------------------


async def rank(client, brief: ResearchBrief, candidates, usage: Usage) -> MatchResult:
    blocks = "\n\n".join(condense(n) for n, _, _ in candidates)
    user = (
        f"## The researcher's brief\n\n"
        f"- Summary: {brief.summary}\n"
        f"- Modality: {brief.modality}\n"
        f"- Indication: {brief.indication}\n"
        f"- Stage: {brief.stage}\n"
        f"- Sectors: {', '.join(brief.sectors)}\n"
        f"- Amount needed: "
        + (f"${brief.amount_needed_usd:,}" if brief.amount_needed_usd else "not stated")
        + "\n"
        f"- Timeframe: "
        + (f"{brief.duration_months} months" if brief.duration_months else "not stated")
        + "\n\n"
        f"## Candidate programmes ({len(candidates)}, pre-filtered by retrieval)\n\n"
        f"{blocks}\n\n"
        f"Rank every candidate above. Use the exact node id in `node_id`."
    )

    response = await client.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": _prompt(RANK_PROMPT)},
            {"role": "user", "content": user},
        ],
        response_format=MatchResult,
        max_completion_tokens=RANK_MAX_OUTPUT,
    )
    usage.add("rank", response)
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("ranking model returned nothing")

    # The model echoes the brief back; keep the authoritative one from stage 1,
    # and drop any node id it invented.
    known = {n.id for n, _, _ in candidates}
    result.brief = brief
    result.matches = [m for m in result.matches if m.node_id in known]
    result.matches.sort(key=lambda m: m.rank)
    return result


# --- orchestration ----------------------------------------------------------


async def run_match(description: str) -> tuple[MatchResult, Usage, dict]:
    usage = Usage()
    client = make_async_client()
    started = datetime.now(timezone.utc)

    brief = await make_brief(client, description, usage)

    if not shortlist(brief, k=1):
        raise ValueError(
            "No funding programme in the map scored above zero for this description. "
            "Try describing the science and the application area in more detail."
        )

    # Walk down the ladder if the ranking call overruns its output cap. Fewer
    # candidates is a worse answer; no answer at all is a broken one.
    degraded_from = 0
    for attempt, k in enumerate(SHORTLIST_LADDER):
        candidates = shortlist(brief, k=k)
        try:
            result = await rank(client, brief, candidates, usage)
            if attempt:
                degraded_from = SHORTLIST_LADDER[0]
            break
        except LengthFinishReasonError:
            if attempt == len(SHORTLIST_LADDER) - 1:
                raise
            continue

    trace = {
        "stages": [
            {"stage": "brief", "detail": f"free text -> structured brief, {len(brief.keywords)} keywords"},
            {"stage": "retrieve",
             "detail": (f"scored {len(load_graph())} nodes locally, kept {len(candidates)}"
                        + (f" (reduced from {degraded_from} to fit the output cap)"
                           if degraded_from else "")),
             "shortlist": [{"id": n.id, "name": n.name, "score": round(s, 1), "why": w}
                           for n, s, w in candidates]},
            {"stage": "rank", "detail": f"ranked {len(result.matches)} programmes"},
        ],
        "elapsed_s": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
    }
    return result, usage, trace


if __name__ == "__main__":
    import json

    text = " ".join(sys.argv[1:]) or (
        "I have a gene therapy targeting the TYK2 gene that slows progression of "
        "multiple sclerosis. I need about $2-3 million over two years."
    )
    res, usage, trace = asyncio.run(run_match(text))
    print(f"\nBrief: {res.brief.summary}")
    print(f"Modality: {res.brief.modality} | Stage: {res.brief.stage} | "
          f"Ask: ${res.brief.amount_needed_usd:,}\n")
    for m in res.matches[:6]:
        print(f"{m.rank}. [{m.relevance}] {m.node_id}")
        print(f"   {m.why}")
        if m.concerns:
            print(f"   concern: {m.concerns}")
    print(f"\nStrategy: {res.strategy_note}")
    print(f"\nUsage: {json.dumps(usage.summary()['by_stage'])}")
    print(f"Cost: ${usage.cost:.5f}  Elapsed: {trace['elapsed_s']}s")

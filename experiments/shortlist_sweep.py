"""Measure what the retrieval step actually buys.

Retrieval is the cost-reduction decision in this app: instead of handing the
ranking agent all 118 organization profiles, it scores them locally and sends
only the best k. This script sweeps k and records both halves of the trade —
what each setting costs, and whether the answer is still right.

    python -m experiments.shortlist_sweep

Writes data/experiments/shortlist_sweep.json. Costs roughly $0.70 to run.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from atlas.config import REPO_ROOT, make_async_client
from atlas.match import condense, make_brief, rank, shortlist
from atlas.usage import Usage

OUT = REPO_ROOT / "data" / "experiments" / "shortlist_sweep.json"

# Each case names the organization a knowledgeable program officer would expect
# at or near the top. That expectation is the quality metric: a cheaper setting
# that loses it has cost something real.
CASES = [
    {
        "id": "ms-gene-therapy",
        "expected": ["ninds", "ncats"],
        "text": (
            "My lab at Yale has developed a gene therapy that targets the TYK2 gene to slow "
            "the progression of multiple sclerosis. We use an AAV vector to deliver a "
            "TYK2-silencing construct to the central nervous system, and we have mouse "
            "efficacy data showing reduced demyelination over 12 weeks. No company has been "
            "formed yet and the IP is held by the university. We need roughly $2-3 million "
            "over two years to complete IND-enabling toxicology and manufacturing."
        ),
    },
    {
        "id": "co2-electrocatalyst",
        "expected": ["arpa-e", "doe-sbir", "leep"],
        "text": (
            "My lab developed an electrocatalyst that converts captured CO2 into ethylene at "
            "70% faradaic efficiency using an iron-based catalyst instead of copper. We have "
            "spun out a company and want to build a pilot reactor. We need roughly $5 million "
            "over three years."
        ),
    },
]

K_VALUES = [4, 8, 12, 20]
FULL_CATALOGUE = 118  # every node that scores above zero, i.e. no retrieval filter


async def run_case(client, case: dict) -> dict:
    usage_brief = Usage()
    brief = await make_brief(client, case["text"], usage_brief)

    rows = []
    for k in K_VALUES + [FULL_CATALOGUE]:
        candidates = shortlist(brief, k=k)
        prompt_chars = sum(len(condense(n)) for n, _, _ in candidates)

        usage = Usage()
        started = datetime.now(timezone.utc)
        try:
            result = await rank(client, brief, candidates, usage)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            ranked = [m.node_id for m in result.matches]
            failed = ""
        except Exception as exc:  # noqa: BLE001
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            ranked = []
            failed = f"{type(exc).__name__}: {exc}"

        expected = case["expected"]
        present = [e for e in expected if e in ranked]
        rows.append({
            "k_requested": k,
            "candidates_sent": len(candidates),
            "profile_chars": prompt_chars,
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": usage.cached_input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": round(usage.cost, 6),
            "elapsed_s": round(elapsed, 1),
            "returned": len(ranked),
            "top_1": ranked[0] if ranked else None,
            "expected_found": present,
            "expected_missing": [e for e in expected if e not in ranked],
            "rank_of_expected": {e: (ranked.index(e) + 1 if e in ranked else None)
                                 for e in expected},
            "error": failed,
        })
        print(f"  k={k:<4} sent={len(candidates):<4} in={usage.input_tokens:<7,} "
              f"out={usage.output_tokens:<6,} ${usage.cost:.4f}  "
              f"top={rows[-1]['top_1']}  missing={rows[-1]['expected_missing']}"
              + (f"  ERROR {failed[:60]}" if failed else ""), flush=True)

    return {
        "case": case["id"],
        "expected": case["expected"],
        "brief_cost_usd": round(usage_brief.cost, 6),
        "brief_keywords": brief.keywords,
        "rows": rows,
    }


async def main() -> None:
    client = make_async_client()
    results = []
    for case in CASES:
        print(f"\n{case['id']}  (expecting {', '.join(case['expected'])})")
        results.append(await run_case(client, case))

    total = sum(r["brief_cost_usd"] + sum(x["cost_usd"] for x in r["rows"]) for r in results)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "k_values": K_VALUES + [FULL_CATALOGUE],
        "results": results,
        "total_cost_usd": round(total, 4),
    }, indent=2))
    print(f"\nWrote {OUT}")
    print(f"Experiment cost ${total:.4f}")


if __name__ == "__main__":
    asyncio.run(main())

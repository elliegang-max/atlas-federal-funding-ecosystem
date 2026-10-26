"""Build step: turn the curated skeleton into an enriched ecosystem graph.

One structured call per organization, run concurrently. The expensive work
happens here, once; the running app only reads the JSON this produces. That
split is what keeps the per-query cost of the live app near zero.

The system prompt is long and identical on every call, so the provider's prompt
cache serves most of it back at a tenth of the input price after the first few
calls. The saving is visible in data/usage_log.jsonl.

Usage:
    python -m atlas.enrich                 # build, skipping nodes already done
    python -m atlas.enrich --force         # rebuild everything
    python -m atlas.enrich --limit 5       # smoke test on five nodes
    python -m atlas.enrich --only nih,barda
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from atlas.config import MODEL, REPO_ROOT, make_async_client
from atlas.schema import EnrichedNode, Profile, SeedNode
from atlas.seed import load_seed
from atlas.usage import Usage, append_log
from atlas.verify import sanitize

PROMPT_PATH = REPO_ROOT / "prompts" / "enrich.md"
OUT_PATH = REPO_ROOT / "data" / "ecosystem.json"

CONCURRENCY = 8
MAX_ATTEMPTS = 3


def system_prompt() -> str:
    if not PROMPT_PATH.is_file():
        sys.exit(f"Enrichment prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text()


def context_for(node: SeedNode, by_id: dict[str, SeedNode]) -> str:
    """Ancestors and siblings, so the model can write `relationship_note` well."""
    chain: list[SeedNode] = []
    cur: SeedNode | None = node
    while cur is not None and cur.parent_id:
        cur = by_id.get(cur.parent_id)
        if cur:
            chain.append(cur)
    chain.reverse()

    lines = ["## Where this organization sits", ""]
    if chain:
        path = " > ".join(f"{c.name} ({c.full_name})" for c in chain)
        lines.append(f"Hierarchy above it: {path}")
    else:
        lines.append("This is a top-level department.")

    siblings = [
        n for n in by_id.values() if n.parent_id == node.parent_id and n.id != node.id
    ]
    if siblings:
        lines.append("")
        lines.append("Siblings under the same parent:")
        lines += [f"  - {s.name}: {s.full_name}" for s in siblings[:24]]

    children = [n for n in by_id.values() if n.parent_id == node.id]
    if children:
        lines.append("")
        lines.append("Organizations nested inside it on this map:")
        lines += [f"  - {c.name}: {c.full_name}" for c in children[:24]]

    return "\n".join(lines)


def user_message(node: SeedNode, by_id: dict[str, SeedNode]) -> str:
    return (
        f"# Organization to profile\n\n"
        f"- Short name: {node.name}\n"
        f"- Official name: {node.full_name}\n"
        f"- Level in the hierarchy: {node.level}\n"
        f"- Homepage: {node.homepage or 'unknown'}\n"
        f"- Curator's note: {node.note or '(none)'}\n\n"
        f"{context_for(node, by_id)}\n"
    )


async def enrich_one(
    client, node: SeedNode, by_id: dict[str, SeedNode], usage: Usage, sem: asyncio.Semaphore
) -> EnrichedNode | None:
    async with sem:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await client.chat.completions.parse(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt()},
                        {"role": "user", "content": user_message(node, by_id)},
                    ],
                    response_format=Profile,
                    max_completion_tokens=4000,
                )
                usage.add("enrich", response)
                profile = response.choices[0].message.parsed
                if profile is None:
                    raise ValueError("model returned no parsed profile")
                # Strip citations we cannot vouch for before the profile is
                # ever stored. A plausible dead URL is worse than a blank.
                profile, removed = sanitize(profile)
                print(f"  ok   {node.id:<18} {profile.confidence:<6} "
                      f"{len(profile.contacts)} contact(s)"
                      + (f"  [stripped {len(removed)}: {removed[0][:48]}]" if removed else ""),
                      flush=True)
                return EnrichedNode(
                    **node.model_dump(),
                    profile=profile,
                    retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    model=MODEL,
                )
            except Exception as exc:  # noqa: BLE001 — one bad node must not kill the build
                if attempt == MAX_ATTEMPTS:
                    print(f"  FAIL {node.id:<18} {type(exc).__name__}: {exc}", flush=True)
                    return None
                await asyncio.sleep(2 * attempt)
    return None


def load_existing() -> dict[str, dict]:
    if not OUT_PATH.is_file():
        return {}
    try:
        raw = json.loads(OUT_PATH.read_text())
        return {n["id"]: n for n in raw.get("nodes", [])}
    except (json.JSONDecodeError, KeyError):
        return {}


async def main() -> None:
    ap = argparse.ArgumentParser(description="Build the enriched ecosystem graph.")
    ap.add_argument("--force", action="store_true", help="re-enrich nodes already present")
    ap.add_argument("--limit", type=int, default=0, help="only process the first N pending nodes")
    ap.add_argument("--only", default="", help="comma-separated node ids")
    ap.add_argument("--sanitize-only", action="store_true",
                    help="re-apply provenance rules to the existing graph, no API calls")
    args = ap.parse_args()

    if args.sanitize_only:
        raw = json.loads(OUT_PATH.read_text())
        total = 0
        for record in raw["nodes"]:
            node = EnrichedNode.model_validate(record)
            _, removed = sanitize(node.profile)
            if removed:
                total += len(removed)
                print(f"  {node.id:<18} stripped {len(removed)}: "
                      + "; ".join(r[:60] for r in removed))
            record.update(json.loads(node.model_dump_json()))
        OUT_PATH.write_text(json.dumps(raw, indent=2))
        print(f"\nSanitized {len(raw['nodes'])} profiles, removed {total} unverifiable citation(s)")
        return

    seed = load_seed()
    by_id = {n.id: n for n in seed}
    existing = {} if args.force else load_existing()

    pending = [n for n in seed if n.id not in existing]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        pending = [n for n in seed if n.id in wanted]
    if args.limit:
        pending = pending[: args.limit]

    print(f"{len(seed)} nodes in seed, {len(existing)} already built, {len(pending)} to do")
    if not pending:
        print("Nothing to do. Use --force to rebuild.")
        return

    usage = Usage()
    sem = asyncio.Semaphore(CONCURRENCY)
    client = make_async_client()
    started = datetime.now(timezone.utc)

    results = await asyncio.gather(
        *(enrich_one(client, n, by_id, usage, sem) for n in pending)
    )

    merged = dict(existing)
    for node in results:
        if node is not None:
            merged[node.id] = node.model_dump()

    # Keep the file in seed order so the map renders deterministically.
    ordered = [merged[n.id] for n in seed if n.id in merged]
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "nodes": ordered,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL,
        "usage": usage.summary(),
    }, indent=2))

    summary = usage.summary()
    append_log({
        "kind": "build",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nodes_built": len([r for r in results if r]),
        "nodes_failed": len([r for r in results if r is None]),
        "elapsed_s": round(elapsed, 1),
        **summary,
    })

    print(f"\nWrote {len(ordered)} nodes to {OUT_PATH}")
    print(f"  {usage.calls} calls in {elapsed:.0f}s")
    print(f"  input {usage.input_tokens:,} | cached {usage.cached_input_tokens:,} "
          f"| output {usage.output_tokens:,}")
    print(f"  cost ${usage.cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())

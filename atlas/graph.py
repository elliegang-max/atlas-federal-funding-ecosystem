"""Loading and querying the built ecosystem graph."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

from atlas.config import REPO_ROOT
from atlas.schema import EnrichedNode

GRAPH_PATH = REPO_ROOT / "data" / "ecosystem.json"


@lru_cache(maxsize=1)
def load_graph(path: str | None = None) -> list[EnrichedNode]:
    p = Path(path) if path else GRAPH_PATH
    if not p.is_file():
        sys.exit(
            f"Ecosystem graph not found at {p}.\n"
            "Build it first:  python -m atlas.enrich"
        )
    raw = json.loads(p.read_text())
    return [EnrichedNode.model_validate(n) for n in raw["nodes"]]


@lru_cache(maxsize=1)
def graph_meta(path: str | None = None) -> dict:
    p = Path(path) if path else GRAPH_PATH
    raw = json.loads(p.read_text())
    return {
        "built_at": raw.get("built_at", ""),
        "model": raw.get("model", ""),
        "node_count": len(raw.get("nodes", [])),
        "build_usage": raw.get("usage", {}),
    }


def by_id() -> dict[str, EnrichedNode]:
    return {n.id: n for n in load_graph()}


def ancestors(node_id: str) -> list[EnrichedNode]:
    """Root-first chain above a node."""
    index = by_id()
    chain: list[EnrichedNode] = []
    cur = index.get(node_id)
    while cur is not None and cur.parent_id:
        cur = index.get(cur.parent_id)
        if cur:
            chain.append(cur)
    chain.reverse()
    return chain


def path_label(node_id: str) -> str:
    chain = ancestors(node_id)
    return " > ".join(c.name for c in chain) if chain else ""

"""Atlas — web server.

Two interfaces over one graph:

  /        the ecosystem map, for a tech transfer office learning the landscape
  /match   the matching agent, for a researcher looking for funding

The map is served from the pre-built graph and costs nothing to run. Only
/api/match spends tokens, and it is wrapped in the guards from atlas.guard.

Run:
    python app.py
    open http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from atlas import guard
from atlas.config import MODEL
from atlas.graph import GRAPH_PATH, ancestors, by_id, graph_meta, load_graph
from atlas.match import run_match
from atlas.usage import LOG_PATH, PRICE_CACHED_INPUT, PRICE_INPUT, PRICE_OUTPUT, append_log

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

app = FastAPI(title="Atlas", docs_url=None, redoc_url=None)

spend_guard = guard.SpendGuard()
rate_limiter = guard.RateLimiter()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/match")
def match_page() -> FileResponse:
    return FileResponse(STATIC / "match.html")


@app.get("/api/graph")
def api_graph() -> JSONResponse:
    """Everything the map needs to draw itself. No profile prose — the detail
    panel fetches that per node, which keeps this payload small."""
    nodes = []
    for n in load_graph():
        p = n.profile
        nodes.append({
            "id": n.id,
            "name": n.name,
            "full_name": n.full_name,
            "parent_id": n.parent_id,
            "level": n.level,
            "group": n.group,
            "sectors": sorted(set(n.sectors) | set(p.sectors)),
            "has_venture_arm": p.has_venture_arm,
            "max_check_usd": max([c.max_usd for c in p.check_sizes], default=0),
            "confidence": p.confidence,
        })
    return JSONResponse({"nodes": nodes, "meta": graph_meta()})


@app.get("/api/node/{node_id}")
def api_node(node_id: str) -> JSONResponse:
    index = by_id()
    node = index.get(node_id)
    if node is None:
        return JSONResponse({"error": "no such organization"}, status_code=404)
    children = [
        {"id": c.id, "name": c.name, "level": c.level}
        for c in load_graph() if c.parent_id == node_id
    ]
    return JSONResponse({
        "node": json.loads(node.model_dump_json()),
        "path": [{"id": a.id, "name": a.name} for a in ancestors(node_id)],
        "children": children,
    })


class MatchRequest(BaseModel):
    description: str


@app.post("/api/match")
async def api_match(req: MatchRequest, request: Request) -> JSONResponse:
    client_key = request.client.host if request.client else "unknown"

    if not rate_limiter.allow(client_key):
        return JSONResponse(
            {"error": "rate_limited",
             "detail": f"More than {guard.RATE_LIMIT} searches in "
                       f"{guard.RATE_WINDOW_S // 60} minutes. Try again shortly."},
            status_code=429,
        )

    if spend_guard.would_exceed():
        return JSONResponse(
            {"error": "budget_exhausted",
             "detail": f"This instance has spent its ${spend_guard.ceiling:.2f} "
                       f"session ceiling. Restart the server to reset it."},
            status_code=429,
        )

    check = guard.check_input(req.description)
    if not check.ok:
        # Logged so a blocked attempt is visible in the usage log, with zero cost.
        append_log({
            "kind": "blocked",
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reason": check.reason,
            "detail": check.detail,
            "matched": check.matched,
            "cost_usd": 0.0,
        })
        return JSONResponse(
            {"error": check.reason, "detail": check.detail, "matched": check.matched},
            status_code=400,
        )

    try:
        result, usage, trace = await run_match(req.description)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": "match_failed", "detail": str(exc)}, status_code=500)

    spend_guard.record(usage.cost)
    summary = usage.summary()
    append_log({
        "kind": "match",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chars_in": len(req.description),
        "matches": len(result.matches),
        "elapsed_s": trace["elapsed_s"],
        **summary,
    })

    index = by_id()
    enriched_matches = []
    for m in result.matches:
        node = index.get(m.node_id)
        if node is None:
            continue
        p = node.profile
        enriched_matches.append({
            **json.loads(m.model_dump_json()),
            "name": node.name,
            "full_name": node.full_name,
            "path": " > ".join(a.name for a in ancestors(node.id)),
            "group": node.group,
            "application_timeline": p.application_timeline,
            "eligibility": p.eligibility,
            "materials_required": p.materials_required,
            "check_sizes": [json.loads(c.model_dump_json()) for c in p.check_sizes],
            "contacts": [json.loads(c.model_dump_json()) for c in p.contacts],
            "source_urls": p.source_urls,
            "confidence": p.confidence,
            "retrieved_at": node.retrieved_at,
        })

    return JSONResponse({
        "brief": json.loads(result.brief.model_dump_json()),
        "matches": enriched_matches,
        "strategy_note": result.strategy_note,
        "trace": trace,
        "usage": summary,
        "budget_remaining_usd": round(spend_guard.remaining, 4),
    })


@app.get("/api/usage")
def api_usage() -> JSONResponse:
    """Everything the tokenomics section of the report needs, from real logs."""
    runs: list[dict] = []
    if LOG_PATH.is_file():
        for line in LOG_PATH.read_text().splitlines():
            if line.strip():
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    matches = [r for r in runs if r.get("kind") == "match"]
    builds = [r for r in runs if r.get("kind") == "build"]
    blocked = [r for r in runs if r.get("kind") == "blocked"]

    def mean(key: str, rows: list[dict]) -> float:
        vals = [r.get(key, 0) for r in rows]
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    return JSONResponse({
        "model": MODEL,
        "prices_per_mtok": {
            "input": PRICE_INPUT, "cached_input": PRICE_CACHED_INPUT, "output": PRICE_OUTPUT,
        },
        "build": {
            "runs": len(builds),
            "total_cost_usd": round(sum(b.get("cost_usd", 0) for b in builds), 4),
            "nodes_built": sum(b.get("nodes_built", 0) for b in builds),
            "input_tokens": sum(b.get("input_tokens", 0) for b in builds),
            "cached_input_tokens": sum(b.get("cached_input_tokens", 0) for b in builds),
            "output_tokens": sum(b.get("output_tokens", 0) for b in builds),
        },
        "match": {
            "runs": len(matches),
            "avg_input_tokens": mean("input_tokens", matches),
            "avg_cached_input_tokens": mean("cached_input_tokens", matches),
            "avg_output_tokens": mean("output_tokens", matches),
            "avg_cost_usd": round(mean("cost_usd", matches), 6),
            "avg_elapsed_s": mean("elapsed_s", matches),
            "total_cost_usd": round(sum(m.get("cost_usd", 0) for m in matches), 4),
        },
        "blocked_requests": len(blocked),
        "session_spend_usd": round(spend_guard.spent, 4),
        "session_ceiling_usd": spend_guard.ceiling,
    })


@app.get("/api/health")
def api_health() -> JSONResponse:
    return JSONResponse({
        "ok": GRAPH_PATH.is_file(),
        "graph": str(GRAPH_PATH),
        "meta": graph_meta() if GRAPH_PATH.is_file() else {},
    })


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import os

    import uvicorn

    # PORT lets a host (or the grader) move the server without editing code.
    port = int(os.environ.get("PORT", "8010"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Atlas — http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

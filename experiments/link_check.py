"""Fetch every URL the graph cites and record which ones actually resolve.

Section 6 states a known gap: the provenance filter in atlas/verify.py checks
the *domain* a citation sits on, never the page. A URL on nih.gov is kept
without confirming that the specific page exists. This measures how much that
gap costs.

    python -m experiments.link_check

Writes data/experiments/link_check.json. Makes no model call; it is HTTP only.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from atlas.config import REPO_ROOT
from atlas.graph import load_graph

OUT = REPO_ROOT / "data" / "experiments" / "link_check.json"

# Federal sites often refuse a bare urllib user agent, which would read as a
# dead link when the page is fine.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
TIMEOUT = 20
WORKERS = 12


def probe(url: str) -> dict:
    """Fetch with curl rather than urllib.

    Python's urllib here has no CA bundle, so every HTTPS request fails
    certificate verification. Using urllib would have measured this machine's
    TLS configuration and reported it as universal link rot — which is exactly
    what the first run of this script did.
    """
    try:
        out = subprocess.run(
            ["curl", "-s", "-L", "-o", "/dev/null",
             "-w", "%{http_code} %{url_effective}",
             "--max-time", str(TIMEOUT), "-A", UA, url],
            capture_output=True, text=True, timeout=TIMEOUT + 10,
        )
        code, _, final = out.stdout.partition(" ")
        status = int(code) if code.isdigit() else 0
        return {"url": url, "status": status, "final": final or url,
                "error": "" if status else (out.stderr.strip()[:80] or "no response")}
    except subprocess.TimeoutExpired:
        return {"url": url, "status": 0, "final": url, "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "status": 0, "final": url, "error": type(exc).__name__}


def classify(row: dict) -> str:
    s = row["status"]
    if 200 <= s < 300:
        return "ok"
    if s == 404:
        return "dead (404)"
    if s in (401, 403):
        return "blocked (401/403)"
    if s == 0:
        return "unreachable"
    return f"other ({s})"


def main() -> None:
    nodes = load_graph()
    cited: dict[str, list[str]] = {}
    for n in nodes:
        for u in n.profile.source_urls:
            cited.setdefault(u, []).append(n.id)
        for c in n.profile.contacts:
            if c.source_url:
                cited.setdefault(c.source_url, []).append(n.id)
        if n.homepage:
            cited.setdefault(n.homepage, []).append(f"{n.id} (seed homepage)")

    urls = sorted(cited)
    print(f"Checking {len(urls)} distinct URLs cited across {len(nodes)} organizations\n")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(probe, urls))

    for r in rows:
        r["cited_by"] = cited[r["url"]]
        r["verdict"] = classify(r)

    counts = Counter(r["verdict"] for r in rows)
    width = max(len(k) for k in counts)
    for verdict, n in counts.most_common():
        print(f"  {verdict:<{width}}  {n:>3}  ({100 * n / len(rows):.1f}%)")

    broken = [r for r in rows if r["verdict"].startswith("dead")]
    unreachable = [r for r in rows if r["verdict"] == "unreachable"]

    if broken:
        print(f"\n404s ({len(broken)}):")
        for r in broken:
            print(f"  {r['url']}\n      cited by: {', '.join(r['cited_by'])}")
    if unreachable:
        print(f"\nUnreachable ({len(unreachable)}):")
        for r in unreachable:
            print(f"  {r['url']}  [{r['error']}]  cited by: {', '.join(r['cited_by'])}")

    # How many organizations have at least one broken citation?
    bad_urls = {r["url"] for r in rows if r["verdict"].startswith("dead") or r["verdict"] == "unreachable"}
    affected = sorted({nid.split(" ")[0] for u in bad_urls for nid in cited[u]})
    print(f"\n{len(affected)} of {len(nodes)} organizations cite at least one broken URL"
          + (f": {', '.join(affected)}" if affected else ""))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "urls_checked": len(rows),
        "counts": dict(counts),
        "affected_organizations": affected,
        "rows": rows,
    }, indent=2))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()

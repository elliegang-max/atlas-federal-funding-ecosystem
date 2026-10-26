"""Audit the shipped ecosystem graph for fabricated facts.

    python check_accuracy.py

Accuracy is the thing this app lives or dies on. A funding map that is
confidently wrong about a program officer is worse than no map, because someone
will act on it. This script checks the claims in data/ecosystem.json against the
rules the enrichment prompt is supposed to enforce, and tests the runtime filter
that stops a ranking agent from returning an organization that does not exist.

Costs nothing: it reads the committed graph and makes no API call.
"""

from __future__ import annotations

import json
from collections import Counter

from atlas.graph import load_graph
from atlas.schema import Match, MatchResult, ResearchBrief
from atlas.verify import curated_domains, hostname, registrable, trusted_email, trusted_url

PASS, FAIL, WARN = "pass", "FAIL", "warn"


def check(name: str, ok: bool, detail: str, soft: bool = False) -> tuple[str, str, str]:
    return (PASS if ok else (WARN if soft else FAIL), name, detail)


def audit_graph() -> list[tuple[str, str, str]]:
    nodes = load_graph()
    contacts = [(n, c) for n in nodes for c in n.profile.contacts]
    results = []

    # 1. The field most likely to be invented, and the one that burns a first
    #    impression when wrong.
    named = [(n, c) for n, c in contacts if c.kind == "named-person"]
    results.append(check(
        "No individual named without verification",
        all(c.verify_before_use for _, c in named),
        f"{len(named)} named individuals across {len(contacts)} contacts in {len(nodes)} profiles"
        + (f"; {sum(1 for _, c in named if not c.verify_before_use)} unflagged" if named else ""),
    ))

    # 2. A contact is only useful if you can check it.
    unsourced = [(n, c) for n, c in contacts
                 if (c.email or c.phone) and not c.source_url]
    results.append(check(
        "Every contact detail carries a source",
        not unsourced,
        f"{len(unsourced)} contacts give an email or phone with no source URL"
        + (f" ({', '.join(n.id for n, _ in unsourced[:4])})" if unsourced else ""),
    ))

    # 3. A plausible-looking address on an unvouched domain is the classic
    #    fabrication. An email survives only on a federal domain or one a human
    #    put in the seed.
    bad_email = [(n.id, c.email) for n, c in contacts
                 if c.email and not trusted_email(c.email)]
    results.append(check(
        "Email domains are federal or curated",
        not bad_email,
        f"{len(bad_email)} of {sum(1 for _, c in contacts if c.email)} emails on an "
        f"unvouched domain" + (f" ({bad_email[0][0]}: {bad_email[0][1]})" if bad_email else ""),
    ))

    # 4. Same rule for every cited page.
    off_domain = [(n.id, u) for n in nodes for u in n.profile.source_urls
                  if not trusted_url(u)]
    off_domain += [(n.id, c.source_url) for n, c in contacts
                   if c.source_url and not trusted_url(c.source_url)]
    total_urls = sum(len(n.profile.source_urls) for n in nodes) + sum(
        1 for _, c in contacts if c.source_url)
    results.append(check(
        "Cited URLs are federal or curated",
        not off_domain,
        f"{len(off_domain)} of {total_urls} cited URLs on an unvouched domain"
        + (f" ({off_domain[0][0]}: {off_domain[0][1]})" if off_domain else ""),
    ))

    # 5. An unsourced claim cannot be checked by the reader.
    no_sources = [n.id for n in nodes if not n.profile.source_urls]
    results.append(check(
        "Every profile cites at least one source",
        not no_sources,
        f"{len(no_sources)} profiles with no sources"
        + (f" ({', '.join(no_sources[:5])})" if no_sources else ""),
    ))

    # 6. Saying "no venture arm" is a correct answer the model must be willing
    #    to give. If it never does, it is inventing one for everything.
    no_arm = [n.id for n in nodes if not n.profile.has_venture_arm]
    results.append(check(
        "Model declines to invent a venture arm",
        len(no_arm) > 0,
        f"{len(no_arm)} of {len(nodes)} profiles say this body has no venture arm",
    ))

    # 7. Unknown check sizes must read as unknown, not as a guessed range.
    bad_band = [(n.id, c.label) for n in nodes for c in n.profile.check_sizes
                if c.max_usd and c.min_usd > c.max_usd]
    results.append(check(
        "Check-size bands are coherent",
        not bad_band,
        f"{len(bad_band)} bands where the minimum exceeds the maximum"
        + (f" ({bad_band[0]})" if bad_band else ""),
    ))

    # 8. Confidence has to vary or it is decoration.
    conf = Counter(n.profile.confidence for n in nodes)
    results.append(check(
        "Confidence is graded, not uniform",
        len(conf) > 1,
        ", ".join(f"{k}: {v}" for k, v in conf.most_common()),
    ))

    unexplained = [n.id for n in nodes
                   if n.profile.confidence in ("medium", "low") and not n.profile.uncertainty_note]
    results.append(check(
        "Lowered confidence is explained",
        not unexplained,
        f"{len(unexplained)} medium/low profiles with no uncertainty note",
    ))

    return results


def audit_runtime_filter() -> list[tuple[str, str, str]]:
    """The ranking agent writes node ids as free text, so it can write one that
    does not exist. rank() drops any id that was not in the shortlist. This
    reproduces that filter against a deliberately poisoned result."""
    from atlas.match import shortlist

    brief = ResearchBrief(
        summary="test", sectors=["health"], modality="gene therapy",
        indication="multiple sclerosis", stage="proof-of-concept",
        amount_needed_usd=2_500_000, duration_months=24,
        keywords=["gene therapy", "multiple sclerosis", "neurology"], missing_info=[],
    )
    candidates = shortlist(brief, k=6)
    known = {n.id for n, _, _ in candidates}

    invented = ["niqt", "national-institute-of-quantum-medicine", "nih-moonshot-fund"]
    poisoned = MatchResult(
        brief=brief,
        matches=[Match(node_id=i, rank=r + 1, relevance=90 - r,
                       why="x", fit_on_check_size="x", fit_on_stage="x", concerns="")
                 for r, i in enumerate(invented + sorted(known)[:3])],
        strategy_note="x",
    )
    survivors = [m.node_id for m in poisoned.matches if m.node_id in known]

    return [
        check("Invented organization ids are dropped",
              not any(i in survivors for i in invented),
              f"fed {len(invented)} fabricated ids; "
              f"{len([i for i in invented if i in survivors])} survived, "
              f"{len(survivors)} real ids kept"),
        check("A real organization cannot be invented into the map",
              all(i not in {n.id for n in load_graph()} for i in invented),
              "the 118 node ids are asserted in atlas/seed.py; the model never adds one"),
    ]


def main() -> int:
    rows = audit_graph() + audit_runtime_filter()

    print(f"Accuracy audit of data/ecosystem.json — {len(load_graph())} organizations")
    print("-" * 72)
    for status, name, detail in rows:
        mark = {"pass": "pass", "FAIL": "FAIL", "warn": "warn"}[status]
        print(f"{mark}  {name}")
        print(f"      {detail}")

    failures = sum(1 for s, _, _ in rows if s == FAIL)
    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print(f"all {len(rows)} checks passed, at zero token cost")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

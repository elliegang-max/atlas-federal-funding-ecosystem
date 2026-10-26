"""Provenance rules for enriched profiles.

The model is good at writing plausible URLs and plausible email addresses, and a
plausible one that does not resolve is worse than a blank field: a reader cannot
tell the difference until they have wasted the outreach.

So a citation is only kept if it lands somewhere we already trust. "Trusted"
means one of two things:

  * a federal domain — .gov, .mil, .edu
  * a domain that appears as the official homepage of an organization in
    atlas/seed.py, which a human curated

The second rule exists because a lot of real federal innovation arms deliberately
do not live on .gov: AFWERX is afwerx.com, In-Q-Tel is iqt.org, MTEC is
mtec-sc.org, SpaceWERX is spacewerx.us. Hard-coding ".gov only" would throw away
correct citations for exactly the organizations a spinout most needs. Anchoring
to the curated homepage list keeps those and still rejects a domain nobody
vouched for.

Anything outside both rules is stripped rather than shown.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from atlas.schema import Profile

FEDERAL_SUFFIXES = (".gov", ".mil", ".edu")


def hostname(url: str) -> str:
    try:
        return (urlparse(url.strip()).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def registrable(host: str) -> str:
    """Crude eTLD+1 — enough to tell nih.gov from lookalike-nih.com."""
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        return host
    if len(parts) > 2 and parts[-2] in {"co", "com", "org", "ac"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


@lru_cache(maxsize=1)
def curated_domains() -> frozenset[str]:
    """Registrable domains of every homepage a human put in the seed."""
    from atlas.seed import load_seed

    return frozenset(
        registrable(hostname(n.homepage)) for n in load_seed() if n.homepage
    ) - {""}


def trusted_host(host: str) -> bool:
    if not host:
        return False
    return host.endswith(FEDERAL_SUFFIXES) or registrable(host) in curated_domains()


def trusted_url(url: str) -> bool:
    return url.startswith(("http://", "https://")) and trusted_host(hostname(url))


def trusted_email(email: str) -> bool:
    if "@" not in email:
        return False
    return trusted_host(email.rsplit("@", 1)[-1].strip().lower())


def sanitize(profile: Profile) -> tuple[Profile, list[str]]:
    """Strip unverifiable citations. Returns the profile and what was removed."""
    removed: list[str] = []

    kept_sources = []
    for url in profile.source_urls:
        (kept_sources if trusted_url(url) else removed).append(
            url if trusted_url(url) else f"source {url}"
        )
    profile.source_urls = kept_sources

    for contact in profile.contacts:
        if contact.email and not trusted_email(contact.email):
            removed.append(f"email {contact.email}")
            contact.email = ""
            contact.verify_before_use = True
        if contact.source_url and not trusted_url(contact.source_url):
            removed.append(f"contact source {contact.source_url}")
            contact.source_url = ""
            contact.verify_before_use = True
        # A phone number has no domain to check it against, and the prompt
        # forbids inventing one. Anything left is flagged rather than trusted.
        if contact.phone and not contact.source_url:
            contact.verify_before_use = True
        if contact.kind == "named-person":
            contact.verify_before_use = True

    return profile, removed

"""Data types for the ecosystem graph and the matching agent.

Two groups of models:

  Seed*      — the hand-curated skeleton: which organizations exist and how
               they nest. Identity and hierarchy are facts we assert, not facts
               we ask a model to invent.
  Profile    — the fields the enrichment agent fills in for each node. This is
               turned into a JSON schema for structured output, so every field
               is required; "unknown" and [] are how the model says it cannot
               tell. Optional fields are not allowed in strict mode.

The split matters for honesty. A model that is asked to produce both the list
of agencies and their details will happily invent an agency. Fixing the
skeleton means every node on the map is one a human put there.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Where a node sits in the hierarchy. Used for layout and for deciding which
# nodes get a full enrichment pass.
NodeLevel = Literal["root", "department", "agency", "program"]

# Coarse sector buckets, kept small so filtering is meaningful.
Sector = Literal[
    "health",
    "biotech",
    "medical-device",
    "defense",
    "energy",
    "space",
    "agriculture",
    "environment",
    "transportation",
    "education",
    "advanced-manufacturing",
    "semiconductors",
    "ai-software",
    "security",
    "cross-sector",
]

# Roughly, where in a company's life this money arrives.
Stage = Literal[
    "pre-company",
    "proof-of-concept",
    "prototype",
    "clinical-translation",
    "scale-up",
    "procurement",
    "any",
]

FundingKind = Literal[
    "grant",
    "contract",
    "cooperative-agreement",
    "equity",
    "loan",
    "prize",
    "non-financial",
    "mixed",
]


class SeedNode(BaseModel):
    """One organization in the curated skeleton."""

    id: str
    name: str = Field(description="Short label shown on the map.")
    full_name: str = Field(description="Official name, spelled out.")
    parent_id: str = Field(description="Parent node id; '' for the root.")
    level: NodeLevel
    group: str = Field(description="Colour/cluster key, normally the department id.")
    sectors: list[Sector] = Field(default_factory=list)
    homepage: str = Field(default="", description="Canonical public URL.")
    note: str = Field(
        default="",
        description="One line of curator context passed to the enrichment agent.",
    )


class Contact(BaseModel):
    """A way to reach the organization.

    `kind` exists because an individual's name is the field most likely to be
    hallucinated and the one that goes stale fastest. A program inbox is both
    safer and more durable, so the agent is told to prefer it.
    """

    kind: Literal["program-office", "named-person", "web-form", "unknown"]
    name: str = Field(description="Person or office name; 'unknown' if not known.")
    title: str = Field(description="Role; 'unknown' if not known.")
    email: str = Field(description="Email address; '' if not known.")
    phone: str = Field(description="Phone; '' if not known.")
    source_url: str = Field(description="Page this was taken from; '' if none.")
    verify_before_use: bool = Field(
        description="True for any individual, or anything not read off an official page."
    )


class CheckSize(BaseModel):
    label: str = Field(description="e.g. 'SBIR Phase I', 'Seed deal'.")
    min_usd: int = Field(description="Lower bound in USD; 0 if unknown.")
    max_usd: int = Field(description="Upper bound in USD; 0 if unknown.")
    duration_months: int = Field(description="Typical period of performance; 0 if unknown.")
    note: str = Field(description="Caveats, e.g. hard cap vs typical award.")


class Profile(BaseModel):
    """Everything the enrichment agent fills in for one organization."""

    overview: str = Field(
        description=(
            "Three to five sentences: what this organization is, where it sits in "
            "its parent, and what it exists to fund. Written for a tech transfer "
            "officer who has never heard of it."
        )
    )
    venture_arm: str = Field(
        description=(
            "The specific entrepreneurial or venture mechanism a university spinout "
            "would actually apply to. 'unknown' if this organization has none."
        )
    )
    has_venture_arm: bool
    funding_kinds: list[FundingKind]
    check_sizes: list[CheckSize]
    annual_budget_usd: int = Field(
        description="Approximate annual budget of the venture arm in USD; 0 if unknown."
    )
    annual_budget_note: str = Field(description="What the budget figure refers to, and its year.")
    stages: list[Stage]
    sectors: list[Sector]
    focus_areas: list[str] = Field(description="Five to ten specific topics it funds.")
    application_timeline: str = Field(
        description="Cycle and deadlines in plain language, e.g. 'three NIH standard dates a year'."
    )
    eligibility: str = Field(description="Who may apply, including the small-business rules.")
    materials_required: list[str] = Field(description="What an application package contains.")
    relationship_note: str = Field(
        description=(
            "How this organization relates to its parent and siblings — shared "
            "mechanisms, hand-off ladders, co-funding. The thing a website will "
            "not tell you."
        )
    )
    contacts: list[Contact]
    source_urls: list[str]
    confidence: Literal["high", "medium", "low"]
    uncertainty_note: str = Field(
        description="What in this profile is least certain, and why. '' if nothing."
    )


class EnrichedNode(SeedNode):
    """A seed node plus its profile and provenance."""

    profile: Profile
    retrieved_at: str
    model: str


class Ecosystem(BaseModel):
    nodes: list[EnrichedNode]
    built_at: str
    model: str
    usage: dict


# --- matching ---------------------------------------------------------------


class ResearchBrief(BaseModel):
    """The structured reading of a researcher's free-text description."""

    summary: str = Field(description="One sentence restating the research in plain terms.")
    sectors: list[Sector]
    modality: str = Field(
        description="e.g. 'gene therapy', 'small molecule', 'class II device', 'software'."
    )
    indication: str = Field(description="Disease or application area; 'unknown' if general.")
    stage: Stage
    amount_needed_usd: int = Field(description="Midpoint of the stated need; 0 if not stated.")
    duration_months: int = Field(description="Stated timeframe in months; 0 if not stated.")
    keywords: list[str] = Field(description="Six to twelve terms for retrieval.")
    missing_info: list[str] = Field(
        description="What the researcher did not say that would change the ranking."
    )


class Match(BaseModel):
    node_id: str
    rank: int
    relevance: int = Field(description="0-100.")
    why: str = Field(description="Two or three sentences tied to this specific research.")
    fit_on_check_size: str = Field(description="How the ask lines up with what they write.")
    fit_on_stage: str
    concerns: str = Field(description="Honest reasons this might not work. '' if none.")


class MatchResult(BaseModel):
    brief: ResearchBrief
    matches: list[Match]
    strategy_note: str = Field(
        description="How to sequence these — which to approach first and why."
    )

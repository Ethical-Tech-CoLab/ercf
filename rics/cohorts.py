"""
RICS cohort vocabulary — category definitions only, per DESIGN.md §9's file layout
note: "cohort category definitions (not data — data lives in DB)". Actual aggregate
counts belong in the `cohorts` table (database.py), each row gated by
k_anonymity_floor (parameter_registry.py) — never here as hardcoded numbers.

Replaces India-EvacSimulation's ARCHETYPES (index.html:598-607) and generateGroups()
(index.html:663), which were illustrative archetypes for a synthetic thesis demo.
RICS cohorts are real, aggregate-only, disaggregated exactly the way LIAI's equity
axes require (DESIGN.md §6): nationality x vulnerability_category x legal_status.
"""

NATIONALITIES = ["drc", "burundi", "rwanda", "mozambique", "other"]

VULNERABILITY_CATEGORIES = [
    "elderly",
    "disabled",
    "unaccompanied_minor",
    "female_headed_household",
    "chronic_illness",
    "general",
]

LEGAL_STATUSES = ["registered_refugee", "asylum_seeker", "undetermined"]

# Maps a cohort's protection-priority tier to the assignment algorithm's processing
# order, replacing the original's evacuation "urgency" tiers (immediate/urgent/
# can-wait) with a durable-solutions analogue: how time-sensitive is this cohort's
# need for a pathway decision, not how fast they need to physically move.
PRIORITY_ORDER = {
    "high": 0,    # e.g. unaccompanied minors, chronic illness with unmet care
    "medium": 1,  # e.g. female-headed households, elderly
    "low": 2,     # e.g. general population, no acute vulnerability flag
}

# Maps a vulnerability category to the pathway "services" factor need it is
# most sensitive to, used by readiness_engine.composite_score()'s vuln_match term
# (replaces the original's single `needs == 'medical'` check).
VULNERABILITY_NEEDS = {
    "elderly": "health",
    "disabled": "health",
    "unaccompanied_minor": "protection",
    "female_headed_household": "protection",
    "chronic_illness": "health",
    "general": None,
}


def make_cohort(id_, nationality, vulnerability_category, legal_status, count, priority):
    """Build a cohort dict for readiness_engine.assign(). `count` must already
    satisfy the k-anonymity floor — this function does not enforce it; the
    database layer (database.py CHECK constraint) is the enforcement point, not
    this helper, to avoid two divergent sources of truth for the same rule."""
    if nationality not in NATIONALITIES:
        raise ValueError(f"unknown nationality: {nationality!r}")
    if vulnerability_category not in VULNERABILITY_CATEGORIES:
        raise ValueError(f"unknown vulnerability_category: {vulnerability_category!r}")
    if legal_status not in LEGAL_STATUSES:
        raise ValueError(f"unknown legal_status: {legal_status!r}")
    if priority not in PRIORITY_ORDER:
        raise ValueError(f"unknown priority: {priority!r}")
    return {
        "id": id_,
        "nationality": nationality,
        "vulnerability_category": vulnerability_category,
        "legal_status": legal_status,
        "size": count,
        "needs": VULNERABILITY_NEEDS[vulnerability_category],
        "priority": priority,
    }

"""
RICS parameter registry — single source of truth for both the cost engine (Layer 1)
and the readiness/uncertainty engine (Layer 2/3). Per DESIGN.md §5/§10.1/§13: every
parameter that feeds a RICS output must be tagged and publicly readable from here,
not left in docstring prose that can drift from the code (the exact failure BACKLOG.md
documents for the India-EvacSimulation methodology .docx).

Do not hand-edit PARAMETER_REGISTRY.md — it is generated from this file. Run:
    python3 parameter_registry.py
to regenerate it after any change here.

── MERGE STATUS (team split) ──────────────────────────────────────────────────
This file is the cost-layer contributor's deliverable and stays actively
maintained. It is a deliberately SHARED registry (DESIGN.md §5: "single source
of truth for both layers"), so it also holds pre-populated `readiness` params
(ported verbatim from India-EvacSimulation's PARAMS/PARAM_DOCS, tag=unvalidated
throughout) and `governance` params — these are starting points for the
readiness/matching teammate, not something actively curated from this side.
The `cost` and `watch` layers are this contributor's own entries. Zero imports
from pathways.py / readiness_engine.py / database.py — this file can be
reviewed and merged independently of those modules.
"""

from datetime import date

# Default uncertainty band width applied to a parameter's point estimate when no
# per-parameter override is given, keyed by tag. Used by cost_engine.py to widen
# Trajectory A/B into breakeven_year_low/high under confMult (DESIGN.md §7, v0.2).
# These defaults are themselves an unvalidated modeling assumption — flagged here
# rather than silently assumed, the same discipline India-EvacSimulation's own
# PARAMS/PARAM_DOCS apply to GK_BLOCKED_CAP, MAX_PERTURB_PROB, etc.
DEFAULT_UNCERTAINTY_BY_TAG = {
    "validated": 0.10,
    "estimated": 0.30,
    "unvalidated": 0.60,
}


def uncertainty_pct(key: str) -> float:
    """Effective base_uncertainty_pct for a registry entry: explicit override if
    present, else the default for its tag."""
    entry = PARAMETER_REGISTRY[key]
    if "base_uncertainty_pct" in entry:
        return entry["base_uncertainty_pct"]
    return DEFAULT_UNCERTAINTY_BY_TAG[entry["tag"]]


# ─────────────────────────────────────────────────────────────────────────────
# LAYER: cost — reused/annualized from calculators.py's calculate_resources(),
# tags carried over verbatim from ERCF's README.md cost-model table.
# ─────────────────────────────────────────────────────────────────────────────
_COST_PARAMS = {
    "water_l_per_person_day": {
        "value": 20, "unit": "L/person/day",
        "tag": "validated",
        "source": "UNHCR WASH Manual", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF calculate_resources(); RICS annualizes rather than sizing for a 3-day convoy.",
    },
    "food_kg_per_person_day": {
        "value": 0.45, "unit": "kg/person/day",
        "tag": "validated",
        "source": "Sphere Handbook 2018 (2,100 kcal/person/day dry-food equivalent)", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF calculate_resources().",
    },
    "tent_occupancy_persons": {
        "value": 5, "unit": "persons/tent",
        "tag": "validated",
        "source": "Sphere Handbook 2018 (3.5 m^2/person)", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF. RICS amortizes tent cost over a multi-year shelter lifetime, not a one-time convoy purchase.",
    },
    "medical_staff_ratio": {
        "value": 250, "unit": "persons/medical staff",
        "tag": "validated",
        "source": "Sphere Handbook 2018", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF calculate_resources().",
    },
    "unhas_air_rate_usd_per_pax_km": {
        "value": 2.08, "unit": "USD/passenger-km",
        "tag": "validated",
        "source": "WFP Executive Board, 'Update on UNHAS', Jan 2025", "source_url": None,
        "last_reviewed": "2025-01",
        "notes": "Not used directly by RICS Trajectory A/B (no air-evac leg); retained for Trajectory B transport-cost line if a resettlement pathway requires it.",
    },
    "water_usd_per_l": {
        "value": 0.05, "unit": "USD/L",
        "tag": "unvalidated",
        "source": "ERCF calculators.py — explicitly marked 'unvalidated for field contexts'; "
                   "Tavily field evidence (Jun 2026) found real range $2-23/m3 (i.e. $0.002-0.023/L), "
                   "below this baseline, not yet adopted",
        "source_url": None, "last_reviewed": "2026-06",
        "notes": "ERCF's own docstring flags this as unvalidated, not just this registry's caution — carried over verbatim, not upgraded.",
    },
    "food_usd_per_kg": {
        "value": 3.0, "unit": "USD/kg",
        "tag": "estimated",
        "source": "ERCF calculators.py calculate_resources() — no explicit validation tag in source docstring "
                   "(unlike the 0.45kg/day quantity, which cites Sphere 2018); carried over as 'estimated' "
                   "pending a real citation for the price itself",
        "source_url": None, "last_reviewed": "2026-06",
        "notes": "Gap inherited from ERCF: the quantity (0.45kg/person/day) is Sphere-sourced, but the $3/kg price has no cited source in calculators.py. Flagged here rather than silently upgraded to validated.",
    },
    "tent_usd_per_unit": {
        "value": 380, "unit": "USD/tent (5-person)",
        "tag": "estimated",
        "source": "ERCF calculators.py — bracketed between UNHCR Shelter Design Catalogue 2016 ($229 incl. "
                   "transport+labour) and a UNHCR $400 replacement-cost quote (The New Humanitarian, Dec 2022); "
                   "$380 is a conservative estimate within that range, not a single authoritative figure",
        "source_url": None, "last_reviewed": "2026-06",
        "notes": "RICS amortizes this over a multi-year shelter lifetime for Trajectory A rather than pricing a one-time convoy purchase — see tent_lifetime_years.",
    },
    "tent_lifetime_years": {
        "value": None, "unit": "years",
        "tag": "unvalidated",
        "source": "New to RICS — ERCF has no amortization concept (evacuation shelters are one-time convoy purchases, not multi-year camp infrastructure)",
        "source_url": None, "last_reviewed": None,
        "notes": "Placeholder pending UNHCR shelter-replacement-cycle data for Dzaleka's climate/materials.",
    },
    "wfp_baseline_cost_usd_per_person_day": {
        "value": 0.42, "unit": "USD/person/day",
        "tag": "validated",
        "source": "WFP Annual Performance Report 2023", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF; one input line among several composing Trajectory A's status-quo annual cost.",
    },
    "medical_staff_daily_usd": {
        "value": 200, "unit": "USD/day",
        "tag": "estimated",
        "source": "MSF 2024 (all-inclusive)", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF calculate_resources().",
    },
    "security_personnel_daily_usd": {
        "value": 300, "unit": "USD/day",
        "tag": "estimated",
        "source": "PSC mid-market", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF; relevance to Dzaleka's protection/admin line (a cost category ERCF's evacuation model never needed) is a Trajectory A addition, see rics_protection_admin_overhead_pct below.",
    },
    "ambulance_ratio_vulnerable": {
        "value": 150, "unit": "vulnerable persons/ambulance",
        "tag": "estimated",
        "source": "Field practice (PMC10068156)", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF; low relevance to a stable-camp Trajectory A (no evacuation convoy), retained for Trajectory B if emergency medical transport is priced into a resettlement pathway.",
    },
    "medical_kit_usd_per_100_persons": {
        "value": 21, "unit": "USD/kit (100-person kit)",
        "tag": "estimated",
        "source": "WHO IEHK (PMC5321368, 2017)", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "Reused verbatim from ERCF calculate_resources().",
    },
    "access_multiplier_l4": {
        "value": 4.0, "unit": "multiplier",
        "tag": "unvalidated",
        "source": "No published source >4x found", "source_url": None,
        "last_reviewed": "2026-06",
        "notes": "ERCF conflict-access multiplier; NOT reused directly by RICS (Dzaleka's friction is funding collapse, not conflict access denial — see rics_funding_shortfall_alpha).",
    },
    # ── New to RICS — no ERCF equivalent, explicitly flagged unvalidated pending calibration ──
    "rics_funding_shortfall_alpha": {
        "value": None, "unit": "dimensionless (multiplier exponent)",
        "tag": "unvalidated",
        "source": "Pending calibration against Dzaleka funding-shortfall case data (DESIGN.md §2: adapted from infra_denial_mult(), new driver). "
                   "Qualitative comparative support (not calibration data — no numeric derivation): AP, 'Trafficked, exploited, "
                   "married off: Rohingya children's lives crushed by foreign aid cuts,' Dec. 2025 — documents the same harm "
                   "mechanism (funding collapse -> protection harm, incl. trafficking/exploitation) in a different protracted-camp "
                   "context, distinct from this report's own Rohingya/BIMS citation (HRW 2021, biometric data misuse, unrelated mechanism).",
        "source_url": None, "last_reviewed": None,
        "notes": "Placeholder — Trajectory A's funding-shortfall multiplier needs its own alpha, jointly optimized the way ERCF's infra-denial alpha=0.4251 was, not borrowed from it. The AP citation supports the mechanism qualitatively, the same way ERCF's own extraction-probability formula cites qualitative-only historical support without a numeric derivation — it does not supply a value for alpha.",
    },
    "rics_protection_admin_overhead_pct": {
        "value": None, "unit": "% of Trajectory A subtotal",
        "tag": "unvalidated",
        "source": "New cost line per report §5 — protection/admin was not priced in ERCF's evacuation model",
        "source_url": None, "last_reviewed": None,
        "notes": "Placeholder pending sourcing (likely UNHCR Malawi operational budget breakdown once available).",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYER: readiness — ported from India-EvacSimulation's PARAMS/PARAM_DOCS
# (reference/india-evac/index.html:523-572). All tagged unvalidated: the
# simulator's own BACKLOG.md and CONCEPT.md call these "acknowledged-uncalibrated
# assumptions," not ERCF-style sourced figures.
# ─────────────────────────────────────────────────────────────────────────────
_READINESS_PARAMS = {
    "mc_runs": {
        "value": 500, "unit": "Monte Carlo iterations per (cohort, pathway) pair",
        "tag": "unvalidated", "base_uncertainty_pct": 0.0,
        "source": "India-EvacSimulation PARAMS.MC_RUNS", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim — a run-count choice, not an empirical claim; no uncertainty-band widening applies to this one (it's a precision knob, not a modeled quantity).",
    },
    "gatekeeper_weight": {
        "value": 2, "unit": "weight multiplier",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.GATEKEEPER_WEIGHT", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim in computeReadiness() port.",
    },
    "normal_weight": {
        "value": 1, "unit": "weight multiplier",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.NORMAL_WEIGHT", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim.",
    },
    "gk_blocked_cap": {
        "value": 0.20, "unit": "readiness fraction ceiling",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.GK_BLOCKED_CAP", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim — hard cap when any gatekeeper (Security/Legal Consent/Host Willingness) is blocked.",
    },
    "score_operational": {
        "value": 1.0, "unit": "factor score",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.SCORE_OP", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim.",
    },
    "score_partial": {
        "value": 0.5, "unit": "factor score",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.SCORE_PART", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim.",
    },
    "score_blocked": {
        "value": 0.0, "unit": "factor score",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.SCORE_BLOCKED", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim.",
    },
    "score_unknown_base": {
        "value": 0.30, "unit": "factor score base",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.SCORE_UNKNOWN_BASE", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim — epistemic-conservatism base score for 'Unknown' status.",
    },
    "w_readiness": {
        "value": 0.40, "unit": "composite score weight",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.W_READINESS", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim in compositeScore() port.",
    },
    "w_capacity": {
        "value": 0.30, "unit": "composite score weight",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.W_CAPACITY", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim.",
    },
    "w_admin": {
        "value": 0.20, "unit": "composite score weight",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.W_PROXIMITY (renamed per DESIGN.md §3: administrative complexity, not physical distance)",
        "source_url": None, "last_reviewed": None,
        "notes": "Same numeric value as the original W_PROXIMITY; only the underlying variable's meaning changed.",
    },
    "w_vuln": {
        "value": 0.10, "unit": "composite score weight",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.W_VULN", "source_url": None,
        "last_reviewed": None, "notes": "Reused verbatim.",
    },
    "success_min_readiness": {
        "value": 0.40, "unit": "readiness fraction threshold",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.SUCCESS_MIN_READINESS", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim — flagged in BACKLOG.md as one of the two parameters most worth checking first against real outcome data.",
    },
    "max_perturb_prob": {
        "value": 0.85, "unit": "probability at 100% uncertainty",
        "tag": "unvalidated",
        "source": "India-EvacSimulation PARAMS.MAX_PERTURB_PROB", "source_url": None,
        "last_reviewed": None,
        "notes": "Reused verbatim — flagged in BACKLOG.md alongside success_min_readiness for first empirical check.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYER: governance — new to RICS, not present in either source codebase.
# ─────────────────────────────────────────────────────────────────────────────
_GOVERNANCE_PARAMS = {
    "k_anonymity_floor": {
        "value": 20, "unit": "minimum aggregate cohort size",
        "tag": "unvalidated",
        "source": "DESIGN.md §6 placeholder, pending FSF field-survey design (Phase 2)",
        "source_url": None, "last_reviewed": None,
        "notes": "Cells below this floor must be merged into a coarser category before storage or reporting. Enforced by database.py CHECK constraint, not policy alone (report §7 principle).",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYER: watch — dated, sourced signals that are NOT yet policy/data changes and
# must not be used to upgrade any tag on their own. Kept structurally separate
# from cost/readiness/governance so a reader never mistakes "we're watching this"
# for "this is confirmed" — same Unknown-vs-Unwilling-style precision the rest
# of RICS insists on (DESIGN.md, [[feedback-epistemic-states]]).
# ─────────────────────────────────────────────────────────────────────────────
_WATCH_PARAMS = {
    "malawi_encampment_policy_review_signal_2026_05": {
        "value": None, "unit": "qualitative signal, not enacted policy",
        "tag": "unvalidated",
        "source": "Ivy Chihana, Deputy Commissioner for Refugees, radio interview, Times Malawi, May 2026 — "
                   "informal statement that government may review the Encampment Policy to permit work "
                   "outside the camp.",
        "source_url": None, "last_reviewed": "2026-05",
        "notes": "Explicitly NOT sufficient to upgrade pathways.py's malawi_local_integration "
                 "host_willingness factor status or tag — one official's informal remark, not approved "
                 "government policy. Recorded per explicit instruction as a dated watch-item; revisit if "
                 "and when this is formalized into policy.",
    },
}

PARAMETER_REGISTRY = {}
for _layer_name, _params in (
    ("cost", _COST_PARAMS),
    ("readiness", _READINESS_PARAMS),
    ("governance", _GOVERNANCE_PARAMS),
    ("watch", _WATCH_PARAMS),
):
    for _key, _entry in _params.items():
        _entry["layer"] = _layer_name
        PARAMETER_REGISTRY[_key] = _entry


def render_markdown() -> str:
    lines = [
        "# RICS Parameter Registry",
        "",
        f"Generated from `parameter_registry.py` — do not hand-edit. Last generated: {date.today().isoformat()}.",
        "",
        "Tag definitions: **validated** = sourced to a cited standard/dataset; "
        "**estimated** = plausible derivation, not directly sourced; "
        "**unvalidated** = placeholder or acknowledged-uncalibrated assumption.",
        "",
    ]
    for layer in ("cost", "readiness", "governance", "watch"):
        lines.append(f"## Layer: {layer}")
        lines.append("")
        lines.append("| Parameter | Value | Unit | Tag | Base uncertainty | Source | Last reviewed |")
        lines.append("|---|---|---|---|---|---|---|")
        for key, entry in PARAMETER_REGISTRY.items():
            if entry["layer"] != layer:
                continue
            lines.append(
                f"| `{key}` | {entry['value']} | {entry['unit']} | {entry['tag']} "
                f"| {uncertainty_pct(key):.0%} | {entry['source']} | {entry['last_reviewed'] or '—'} |"
            )
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    for key, entry in PARAMETER_REGISTRY.items():
        if entry.get("notes"):
            lines.append(f"- **`{key}`**: {entry['notes']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path(__file__).parent / "PARAMETER_REGISTRY.md"
    out.write_text(render_markdown())
    print(f"Wrote {out}")

"""
RICS durable-solutions pathways — replaces India-EvacSimulation's generateDestinations()
(index.html:636), which is RNG-synthetic by explicit design (CONCEPT.md: "nothing here
is real location data"). RICS cannot use synthetic pathways — §7/§9's evidence-not-
fabrication posture requires real, sourced, Validated/Estimated/Unvalidated-tagged
factor assessments, the same discipline as parameter_registry.py.

Three categories confirmed in scope for v1 (user decision, this session):
  1. Local integration in Malawi (work-rights pathway)
  2. Voluntary return, by origin (DRC, Burundi, Rwanda)
  3. Third-country resettlement quotas (USA, Canada, EU) + complementary pathways

HONESTY NOTE: only "malawi_local_integration" had real citations in the original
session, drawn directly from the report (After the Corridor §4). A July 2026
source-mining pass (see DESIGN.md §12b) added real, dated data for resettlement_usa
(with an explicit two-scenario capacity — a 2024 baseline and a post-FY2026-cut
estimate, since a single current number does not exist and forcing one would be
false precision) and a new "complementary_pathways" entry. The remaining pathways
(resettlement_canada, resettlement_eu, voluntary_return_drc) still have no
population-specific data and remain "unknown"/None pending research. Two
voluntary-return pathways (burundi, rwanda) now carry *comparative* evidence from a
different origin corridor (Tanzania/DRC, not Malawi) — explicitly caveated as
directional only, never as this population's capacity, per DESIGN.md §12b. Any code
consuming these must treat a None capacity/admin_complexity as "cannot compute
yet," matching cost_engine.py's _bounds() pattern of raising rather than assuming.
"""

_PENDING = "PENDING SOURCING — not yet researched this session; do not treat as a real assessment."

PATHWAYS = {
    "malawi_local_integration": {
        "category": "local_integration",
        "capacity": None,          # real work-permit-slot figure not yet sourced — see camp_population_context
        "capacity_tag": "unvalidated",
        "capacity_source": _PENDING + " (camp population size is NOT the same thing as legal-pathway admission "
                            "capacity — see camp_population_context below; do not conflate the two.)",
        "admin_complexity": None,  # processing-steps/days proxy (DESIGN.md §3) — not yet sourced
        "admin_complexity_tag": "unvalidated",
        "admin_complexity_source": _PENDING,
        # Camp-level overcrowding context (July 2026 update) — real, validated population figures, but
        # deliberately NOT written into the `capacity` field above: camp population size answers "how many
        # people are here," not "how many legal work-rights slots this pathway could admit," which is a
        # different question this data does not answer.
        "camp_population_context": {
            "design_capacity": 12000,
            "current_population_2025": "53,000-59,564",
            "projected_population_2026": 63028,
            "tag": "validated",
            "source": "UNHCR population figures, as cited in July 2026 update — camp built 1994 for "
                       "10,000-12,000; ~5x design capacity by 2025, projected 63,028 in 2026.",
        },
        "factors": {
            "security": {
                "status": "partial", "base_conf": 0.5, "tag": "estimated",
                "source": "Report §4: weakened protection oversight reported to embolden trafficking networks — degraded, not blocked",
            },
            "legal_consent": {
                "status": "blocked", "base_conf": 0.9, "tag": "validated",
                "source": "Malawi encampment policy, enforced since March 2023, bars most residents from working outside "
                           "the camp (report §4). Corroborated July 2026: no right to work, own property, freely move, or "
                           "access a path to citizenship, including for residents born in Dzaleka since 1994 (Human Rights "
                           "Watch, World Report 2026; Southern Africa Litigation Centre).",
            },
            "host_willingness": {
                "status": "blocked", "base_conf": 0.7, "tag": "estimated",
                "source": "Inua Advocacy civil-society reporting cited in report §4; estimated, not a confirmed government "
                           "policy-reversal signal. See parameter_registry.py watch-item "
                           "'malawi_encampment_policy_review_signal_2026_05' for a May 2026 informal signal — NOT "
                           "sufficient to change this status/tag; recorded separately by design.",
            },
            "housing": {
                "status": "partial", "base_conf": 0.6, "tag": "validated",
                "source": "UNHCR population figures (July 2026 update): camp designed for 10,000-12,000 (1994), now "
                           "53,000-59,564 (2025), projected 63,028 (2026) — ~5x design capacity. 'Partial' (not "
                           "'blocked') because shelter exists but is severely overcrowded, not absent; see "
                           "camp_population_context above for the full figures this status is derived from.",
            },
            "jobs": {
                "status": "blocked", "base_conf": 0.85, "tag": "estimated",
                "source": "Direct consequence of the encampment policy's work prohibition (report §4) — substitutable factor, does not itself gatekeep, but correlated with the legal_consent gatekeeper's status",
            },
            "services": {
                "status": "partial", "base_conf": 0.5, "tag": "estimated",
                "source": "Report §4: UNHCR budget ~90% cut, WFP cash support down from ~$100 to $5.90-8.60/person/month — degraded, not absent",
            },
        },
    },
    "voluntary_return_drc": {
        "category": "voluntary_return",
        "capacity": None, "capacity_tag": "unvalidated", "capacity_source": _PENDING,
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
        # No DRC-specific return-corridor data found in the July 2026 pass (the DRC-Rwanda peace
        # agreement below concerns a different population — see voluntary_return_rwanda). Field
        # present for structural consistency across the three voluntary_return_* pathways, not
        # because evidence exists for this one.
        "coercion_risk_flag": {
            "status": "not_assessed",
            "note": "No evidence reviewed this session, for or against, on this specific corridor.",
            "tag": "unvalidated", "source": None,
        },
    },
    "voluntary_return_burundi": {
        "category": "voluntary_return",
        "capacity": None, "capacity_tag": "unvalidated", "capacity_source": _PENDING,
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
        # Real return-volume data exists (July 2026), but it is the TANZANIA-Burundi corridor, not
        # Malawi-Burundi — Dzaleka's Burundian cohort is a different population. Recorded as
        # directional/comparative evidence only, per explicit instruction: max tag 'estimated',
        # never 'validated' for this population, and NEVER written into the `capacity` field above.
        "comparative_evidence": {
            "value": ">300,000 Burundian returns since 2017 (majority from Tanzania); >28,000 in the "
                     "first two months of 2026 from Tanzania alone, exceeding the weekly target of 3,000",
            "source": "Tripartite Commission Tanzania-Burundi-UNHCR, Nov 2025",
            "tag": "estimated",
            "population_mismatch_note": "This is the Tanzania-Burundi corridor — a different origin "
                "population than Dzaleka's Malawi-based Burundian cohort. Directional evidence that "
                "large-scale Burundian return is actively happening in the region, not a capacity "
                "figure for this pathway.",
        },
        "coercion_risk_flag": {
            "status": "flagged",
            "note": "UNHCR reported demolished shelters and mistreatment during this acceleration of "
                    "returns from Tanzania — a signal of possible coercion, not genuinely voluntary "
                    "return. Directly relevant to the report's IHL forcible-transfer line (movement into "
                    "which people are coerced is forcible transfer, a war crime regardless of motive, "
                    "§2). This is Tanzania-corridor evidence, not Malawi — but it is a documented "
                    "precedent that accelerated 'voluntary' return programs in this exact region have "
                    "produced coercion risk, and should inform how any future Malawi-Burundi pathway "
                    "is assessed, not be discarded as irrelevant.",
            "tag": "estimated",
            "source": "UNHCR reporting, cited via Tripartite Commission Tanzania-Burundi-UNHCR context, Nov 2025.",
        },
    },
    "voluntary_return_rwanda": {
        "category": "voluntary_return",
        "capacity": None, "capacity_tag": "unvalidated", "capacity_source": _PENDING,
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
        # Real return-volume data exists (July 2026), but it is Rwandans returning FROM DRC TO Rwanda —
        # not Dzaleka's Malawi-based Rwandan cohort. Directional/comparative evidence only, per
        # explicit instruction: max tag 'estimated', never 'validated' for this population, and
        # NEVER written into the `capacity` field above.
        "comparative_evidence": {
            "value": "DRC-Rwanda Peace Agreement (27 Jun 2025) -> Tripartite Roadmap 2025-2026; 5,000 "
                     "facilitated returns in 2025, target of 10,000 Rwandan-origin returns from DRC to "
                     "Rwanda in 2026",
            "source": "UNHCR, as cited in July 2026 update",
            "tag": "estimated",
            "population_mismatch_note": "This corridor returns Rwandans FROM DRC TO Rwanda — a "
                "different population than Dzaleka's Malawi-based Rwandan cohort. Directional evidence "
                "that a bilateral peace framework is actively enabling large-scale Rwandan return "
                "elsewhere in the region, not a capacity figure for this pathway.",
        },
        "coercion_risk_flag": {
            "status": "not_assessed",
            "note": "No evidence reviewed this session, for or against, on this specific corridor "
                    "(see voluntary_return_burundi for a documented coercion-risk case in a different "
                    "corridor within the same region).",
            "tag": "unvalidated", "source": None,
        },
    },
    "resettlement_usa": {
        "category": "third_country_resettlement",
        # No single current capacity number exists — see capacity_scenarios. Forcing one scalar here
        # (either the 2024 baseline or a guessed 2026 figure) would be false precision the report's
        # own §14 principle warns against, so `capacity` stays None and both scenarios are exposed
        # for a caller to choose from explicitly (same "raise, don't assume" discipline as
        # cost_engine._bounds()).
        "capacity": None,
        "capacity_tag": "estimated",  # richer than pure "unvalidated" — real numbers exist, but genuinely unresolved as a single figure
        "capacity_source": "No single current-capacity figure — see capacity_scenarios (2024 validated baseline "
                            "vs. 2026 estimated post-cut). A caller must pick one explicitly via capacity_override.",
        "capacity_scenarios": {
            "baseline_2024_pre_cut": {
                "value": 2137, "tag": "validated",
                "source": "UNHCR Malawi Annual Results Report 2024 — Malawi/Dzaleka referred 2,431 people for "
                           "resettlement; USA accepted 2,137 (~90% of submissions, and historically ~90% of "
                           "Malawi's total resettlement channel).",
            },
            "fy2026_post_cut": {
                "value": None, "tag": "estimated",
                "source": "No official Malawi/Africa-specific FY2026 admission number has been published. "
                           "Estimate is inferred from the legal_consent factor below (channel effectively "
                           "closed), not a directly published statistic — recorded as None rather than a "
                           "guessed figure, consistent with not inventing numbers absent a source.",
            },
        },
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {
            "legal_consent": {
                "status": "blocked", "base_conf": 0.85, "tag": "validated",
                "source": "US FY2026 refugee admissions quota cut to 7,500 total (historic low) with NO regional "
                           "allocation for Africa — nearly all slots allocated to South African 'Afrikaners' under "
                           "Executive Order 14204, ending the region-based allocation standard used through FY2020 "
                           "(Federal Register, Presidential Determination on Refugee Admissions for FY2026, 31 Oct "
                           "2025). This closes the channel that carried ~90% of Malawi's 2024 resettlement quota.",
            },
            **{fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
               for fid in ("security", "host_willingness", "housing", "jobs", "services")},
        },
    },
    "resettlement_canada": {
        "category": "third_country_resettlement",
        "capacity": None, "capacity_tag": "unvalidated",
        "capacity_source": _PENDING + " Context only, not a Canada-specific figure: the 2024 UNHCR Malawi Annual "
                            "Results Report reports 1,770 people resettled to Australia/Canada/Norway COMBINED, "
                            "undifferentiated by country — no Canada-only split is available, so no number is "
                            "extracted from it here.",
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
    },
    "resettlement_eu": {
        "category": "third_country_resettlement",
        "capacity": None, "capacity_tag": "unvalidated",
        "capacity_source": _PENDING + " Note: the 2024 Australia/Canada/Norway combined figure (see "
                            "resettlement_canada) does not apply here — Norway is not an EU member state, so it "
                            "does not evidence this pathway either.",
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
    },
    "complementary_pathways": {
        "category": "third_country_resettlement",
        # New pathway, July 2026 — resolves the earlier DESIGN.md §12 open question on Fratzke &
        # Zanzuchi's "Complementary Pathways" (MPI, Dec 2024): that source was flagged as likely
        # covering labor-mobility/education/family-reunification routes to third countries,
        # complementary TO formal resettlement, not the same as RICS's local-integration/return split.
        # This entry gives that category a real, small, quantified channel size for this population.
        "capacity": 71,
        "capacity_tag": "validated",
        "capacity_source": "UNHCR Malawi Annual Results Report 2024 — +71 individuals via complementary "
                            "pathways (labor mobility/education/family-reunification-type routes), alongside "
                            "formal resettlement, 2024 baseline. Whether this channel is affected by the "
                            "FY2026 US quota cut is not established — it may span multiple destination "
                            "countries, not only the USA — so no FY2026 adjustment is applied here.",
        "admin_complexity": None, "admin_complexity_tag": "unvalidated", "admin_complexity_source": _PENDING,
        "factors": {fid: {"status": "unknown", "base_conf": 0.2, "tag": "unvalidated", "source": _PENDING}
                    for fid in ("security", "legal_consent", "host_willingness", "housing", "jobs", "services")},
    },
}


def to_engine_pathway(pathway_id: str, capacity_override=None, admin_complexity_override=None) -> dict:
    """Build the {id, capacity, admin_complexity, factors} shape readiness_engine.py's
    functions expect, from the sourced PATHWAYS record. Raises if capacity/
    admin_complexity is unsourced and no override is supplied — same pattern as
    cost_engine._bounds(), refusing to silently assume a number."""
    p = PATHWAYS[pathway_id]
    capacity = capacity_override if capacity_override is not None else p["capacity"]
    admin_complexity = admin_complexity_override if admin_complexity_override is not None else p["admin_complexity"]
    if capacity is None:
        raise ValueError(f"{pathway_id}: capacity not sourced ({p['capacity_source']}) — supply capacity_override")
    if admin_complexity is None:
        raise ValueError(f"{pathway_id}: admin_complexity not sourced ({p['admin_complexity_source']}) — supply admin_complexity_override")
    return {
        "id": pathway_id,
        "capacity": capacity,
        "admin_complexity": admin_complexity,
        "factors": {fid: {"status": f["status"], "base_conf": f["base_conf"]} for fid, f in p["factors"].items()},
    }


def to_readiness_only_pathway(pathway_id: str) -> dict:
    """Same shape as to_engine_pathway() but WITHOUT capacity/admin_complexity —
    compute_readiness() never reads those fields (only monte_carlo()/
    composite_score() do), so gatekeeper-status views don't need to raise on
    unsourced capacity, unlike the full assign()/Monte Carlo pipeline."""
    p = PATHWAYS[pathway_id]
    return {
        "id": pathway_id,
        "factors": {fid: {"status": f["status"], "base_conf": f["base_conf"]} for fid, f in p["factors"].items()},
    }


TAG_SEVERITY = {"validated": 0, "estimated": 1, "unvalidated": 2}


def overall_tag(pathway_id: str) -> str:
    """Worst-of-tags rollup across every sourced field on a pathway (each
    factor's tag, plus capacity_tag and admin_complexity_tag) — deliberately
    conservative: a pathway is only as trustworthy as its least-sourced field,
    the same "don't overstate confidence" principle as everywhere else in RICS."""
    p = PATHWAYS[pathway_id]
    tags = [f["tag"] for f in p["factors"].values()] + [p["capacity_tag"], p["admin_complexity_tag"]]
    return max(tags, key=lambda t: TAG_SEVERITY[t])

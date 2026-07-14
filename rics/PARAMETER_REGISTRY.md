# RICS Parameter Registry

Generated from `parameter_registry.py` — do not hand-edit. Last generated: 2026-07-11.

Tag definitions: **validated** = sourced to a cited standard/dataset; **estimated** = plausible derivation, not directly sourced; **unvalidated** = placeholder or acknowledged-uncalibrated assumption.

## Layer: cost

| Parameter | Value | Unit | Tag | Base uncertainty | Source | Last reviewed |
|---|---|---|---|---|---|---|
| `water_l_per_person_day` | 20 | L/person/day | validated | 10% | UNHCR WASH Manual | 2026-06 |
| `food_kg_per_person_day` | 0.45 | kg/person/day | validated | 10% | Sphere Handbook 2018 (2,100 kcal/person/day dry-food equivalent) | 2026-06 |
| `tent_occupancy_persons` | 5 | persons/tent | validated | 10% | Sphere Handbook 2018 (3.5 m^2/person) | 2026-06 |
| `medical_staff_ratio` | 250 | persons/medical staff | validated | 10% | Sphere Handbook 2018 | 2026-06 |
| `unhas_air_rate_usd_per_pax_km` | 2.08 | USD/passenger-km | validated | 10% | WFP Executive Board, 'Update on UNHAS', Jan 2025 | 2025-01 |
| `water_usd_per_l` | 0.05 | USD/L | unvalidated | 60% | ERCF calculators.py — explicitly marked 'unvalidated for field contexts'; Tavily field evidence (Jun 2026) found real range $2-23/m3 (i.e. $0.002-0.023/L), below this baseline, not yet adopted | 2026-06 |
| `food_usd_per_kg` | 3.0 | USD/kg | estimated | 30% | ERCF calculators.py calculate_resources() — no explicit validation tag in source docstring (unlike the 0.45kg/day quantity, which cites Sphere 2018); carried over as 'estimated' pending a real citation for the price itself | 2026-06 |
| `tent_usd_per_unit` | 380 | USD/tent (5-person) | estimated | 30% | ERCF calculators.py — bracketed between UNHCR Shelter Design Catalogue 2016 ($229 incl. transport+labour) and a UNHCR $400 replacement-cost quote (The New Humanitarian, Dec 2022); $380 is a conservative estimate within that range, not a single authoritative figure | 2026-06 |
| `tent_lifetime_years` | None | years | unvalidated | 60% | New to RICS — ERCF has no amortization concept (evacuation shelters are one-time convoy purchases, not multi-year camp infrastructure) | — |
| `wfp_baseline_cost_usd_per_person_day` | 0.42 | USD/person/day | validated | 10% | WFP Annual Performance Report 2023 | 2026-06 |
| `medical_staff_daily_usd` | 200 | USD/day | estimated | 30% | MSF 2024 (all-inclusive) | 2026-06 |
| `security_personnel_daily_usd` | 300 | USD/day | estimated | 30% | PSC mid-market | 2026-06 |
| `ambulance_ratio_vulnerable` | 150 | vulnerable persons/ambulance | estimated | 30% | Field practice (PMC10068156) | 2026-06 |
| `medical_kit_usd_per_100_persons` | 21 | USD/kit (100-person kit) | estimated | 30% | WHO IEHK (PMC5321368, 2017) | 2026-06 |
| `access_multiplier_l4` | 4.0 | multiplier | unvalidated | 60% | No published source >4x found | 2026-06 |
| `rics_funding_shortfall_alpha` | None | dimensionless (multiplier exponent) | unvalidated | 60% | Pending calibration against Dzaleka funding-shortfall case data (DESIGN.md §2: adapted from infra_denial_mult(), new driver). Qualitative comparative support (not calibration data — no numeric derivation): AP, 'Trafficked, exploited, married off: Rohingya children's lives crushed by foreign aid cuts,' Dec. 2025 — documents the same harm mechanism (funding collapse -> protection harm, incl. trafficking/exploitation) in a different protracted-camp context, distinct from this report's own Rohingya/BIMS citation (HRW 2021, biometric data misuse, unrelated mechanism). | — |
| `rics_protection_admin_overhead_pct` | None | % of Trajectory A subtotal | unvalidated | 60% | New cost line per report §5 — protection/admin was not priced in ERCF's evacuation model | — |

## Layer: readiness

| Parameter | Value | Unit | Tag | Base uncertainty | Source | Last reviewed |
|---|---|---|---|---|---|---|
| `mc_runs` | 500 | Monte Carlo iterations per (cohort, pathway) pair | unvalidated | 0% | India-EvacSimulation PARAMS.MC_RUNS | — |
| `gatekeeper_weight` | 2 | weight multiplier | unvalidated | 60% | India-EvacSimulation PARAMS.GATEKEEPER_WEIGHT | — |
| `normal_weight` | 1 | weight multiplier | unvalidated | 60% | India-EvacSimulation PARAMS.NORMAL_WEIGHT | — |
| `gk_blocked_cap` | 0.2 | readiness fraction ceiling | unvalidated | 60% | India-EvacSimulation PARAMS.GK_BLOCKED_CAP | — |
| `score_operational` | 1.0 | factor score | unvalidated | 60% | India-EvacSimulation PARAMS.SCORE_OP | — |
| `score_partial` | 0.5 | factor score | unvalidated | 60% | India-EvacSimulation PARAMS.SCORE_PART | — |
| `score_blocked` | 0.0 | factor score | unvalidated | 60% | India-EvacSimulation PARAMS.SCORE_BLOCKED | — |
| `score_unknown_base` | 0.3 | factor score base | unvalidated | 60% | India-EvacSimulation PARAMS.SCORE_UNKNOWN_BASE | — |
| `w_readiness` | 0.4 | composite score weight | unvalidated | 60% | India-EvacSimulation PARAMS.W_READINESS | — |
| `w_capacity` | 0.3 | composite score weight | unvalidated | 60% | India-EvacSimulation PARAMS.W_CAPACITY | — |
| `w_admin` | 0.2 | composite score weight | unvalidated | 60% | India-EvacSimulation PARAMS.W_PROXIMITY (renamed per DESIGN.md §3: administrative complexity, not physical distance) | — |
| `w_vuln` | 0.1 | composite score weight | unvalidated | 60% | India-EvacSimulation PARAMS.W_VULN | — |
| `success_min_readiness` | 0.4 | readiness fraction threshold | unvalidated | 60% | India-EvacSimulation PARAMS.SUCCESS_MIN_READINESS | — |
| `max_perturb_prob` | 0.85 | probability at 100% uncertainty | unvalidated | 60% | India-EvacSimulation PARAMS.MAX_PERTURB_PROB | — |

## Layer: governance

| Parameter | Value | Unit | Tag | Base uncertainty | Source | Last reviewed |
|---|---|---|---|---|---|---|
| `k_anonymity_floor` | 20 | minimum aggregate cohort size | unvalidated | 60% | DESIGN.md §6 placeholder, pending FSF field-survey design (Phase 2) | — |

## Layer: watch

| Parameter | Value | Unit | Tag | Base uncertainty | Source | Last reviewed |
|---|---|---|---|---|---|---|
| `malawi_encampment_policy_review_signal_2026_05` | None | qualitative signal, not enacted policy | unvalidated | 60% | Ivy Chihana, Deputy Commissioner for Refugees, radio interview, Times Malawi, May 2026 — informal statement that government may review the Encampment Policy to permit work outside the camp. | 2026-05 |

## Notes

- **`water_l_per_person_day`**: Reused verbatim from ERCF calculate_resources(); RICS annualizes rather than sizing for a 3-day convoy.
- **`food_kg_per_person_day`**: Reused verbatim from ERCF calculate_resources().
- **`tent_occupancy_persons`**: Reused verbatim from ERCF. RICS amortizes tent cost over a multi-year shelter lifetime, not a one-time convoy purchase.
- **`medical_staff_ratio`**: Reused verbatim from ERCF calculate_resources().
- **`unhas_air_rate_usd_per_pax_km`**: Not used directly by RICS Trajectory A/B (no air-evac leg); retained for Trajectory B transport-cost line if a resettlement pathway requires it.
- **`water_usd_per_l`**: ERCF's own docstring flags this as unvalidated, not just this registry's caution — carried over verbatim, not upgraded.
- **`food_usd_per_kg`**: Gap inherited from ERCF: the quantity (0.45kg/person/day) is Sphere-sourced, but the $3/kg price has no cited source in calculators.py. Flagged here rather than silently upgraded to validated.
- **`tent_usd_per_unit`**: RICS amortizes this over a multi-year shelter lifetime for Trajectory A rather than pricing a one-time convoy purchase — see tent_lifetime_years.
- **`tent_lifetime_years`**: Placeholder pending UNHCR shelter-replacement-cycle data for Dzaleka's climate/materials.
- **`wfp_baseline_cost_usd_per_person_day`**: Reused verbatim from ERCF; one input line among several composing Trajectory A's status-quo annual cost.
- **`medical_staff_daily_usd`**: Reused verbatim from ERCF calculate_resources().
- **`security_personnel_daily_usd`**: Reused verbatim from ERCF; relevance to Dzaleka's protection/admin line (a cost category ERCF's evacuation model never needed) is a Trajectory A addition, see rics_protection_admin_overhead_pct below.
- **`ambulance_ratio_vulnerable`**: Reused verbatim from ERCF; low relevance to a stable-camp Trajectory A (no evacuation convoy), retained for Trajectory B if emergency medical transport is priced into a resettlement pathway.
- **`medical_kit_usd_per_100_persons`**: Reused verbatim from ERCF calculate_resources().
- **`access_multiplier_l4`**: ERCF conflict-access multiplier; NOT reused directly by RICS (Dzaleka's friction is funding collapse, not conflict access denial — see rics_funding_shortfall_alpha).
- **`rics_funding_shortfall_alpha`**: Placeholder — Trajectory A's funding-shortfall multiplier needs its own alpha, jointly optimized the way ERCF's infra-denial alpha=0.4251 was, not borrowed from it. The AP citation supports the mechanism qualitatively, the same way ERCF's own extraction-probability formula cites qualitative-only historical support without a numeric derivation — it does not supply a value for alpha.
- **`rics_protection_admin_overhead_pct`**: Placeholder pending sourcing (likely UNHCR Malawi operational budget breakdown once available).
- **`mc_runs`**: Reused verbatim — a run-count choice, not an empirical claim; no uncertainty-band widening applies to this one (it's a precision knob, not a modeled quantity).
- **`gatekeeper_weight`**: Reused verbatim in computeReadiness() port.
- **`normal_weight`**: Reused verbatim.
- **`gk_blocked_cap`**: Reused verbatim — hard cap when any gatekeeper (Security/Legal Consent/Host Willingness) is blocked.
- **`score_operational`**: Reused verbatim.
- **`score_partial`**: Reused verbatim.
- **`score_blocked`**: Reused verbatim.
- **`score_unknown_base`**: Reused verbatim — epistemic-conservatism base score for 'Unknown' status.
- **`w_readiness`**: Reused verbatim in compositeScore() port.
- **`w_capacity`**: Reused verbatim.
- **`w_admin`**: Same numeric value as the original W_PROXIMITY; only the underlying variable's meaning changed.
- **`w_vuln`**: Reused verbatim.
- **`success_min_readiness`**: Reused verbatim — flagged in BACKLOG.md as one of the two parameters most worth checking first against real outcome data.
- **`max_perturb_prob`**: Reused verbatim — flagged in BACKLOG.md alongside success_min_readiness for first empirical check.
- **`k_anonymity_floor`**: Cells below this floor must be merged into a coarser category before storage or reporting. Enforced by database.py CHECK constraint, not policy alone (report §7 principle).
- **`malawi_encampment_policy_review_signal_2026_05`**: Explicitly NOT sufficient to upgrade pathways.py's malawi_local_integration host_willingness factor status or tag — one official's informal remark, not approved government policy. Recorded per explicit instruction as a dated watch-item; revisit if and when this is formalized into policy.

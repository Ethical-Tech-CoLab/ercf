"""
walking_evac.py — On-foot evacuation time, cost, and exposure-risk calculator.

Extends the ERCF resource model to cover walking (on-foot) evacuation,
relevant when no vehicle, fuel, runway, or helicopter access exists and
the population must travel by foot. This is a TIME and RISK-EXPOSURE
calculator first, and a cost calculator second — unlike ground/air/heli
modes, walking has no transport fare; the "cost" here is the
water/food provisioning needed to sustain the population during transit.

VALIDATION STATUS (June 2026)
==============================
WALKING SPEED: ESTIMATED, with a documented and transparent derivation.

1. BASE SPEED (literature-derived, citable): the agent-based refugee
   migration model *Flee* (Suleimenova, Bell & Groen — validated against
   ten historical conflicts, published in Phil. Trans. R. Soc. A and
   ScienceDirect, in active use by Save the Children) uses a maximum
   movement speed of 200km/day in its base configuration. A separate
   peer-reviewed-adjacent critique (arXiv:1903.08255, "Markov Chain Models
   of Refugee Migration Data") argues this is overly optimistic since most
   refugees travel on foot, and proposes a more realistic threshold of
   120km/day, derived as 15 hours at 8km/h. We adopt the 8km/h figure as
   our BASE (healthy adult) walking speed, since it is the most
   specifically-sourced and defensible number in the literature for
   refugee/displacement movement on foot.

2. VULNERABILITY ADJUSTMENT (estimated, clinically grounded): the 8km/h
   base figure describes a general/healthy adult population and does not
   account for children, elderly, disabled, or medically vulnerable group
   members — exactly the "Vulnerable Population %" field already used
   elsewhere in this tool. Clinical gait-speed literature (UK Health Survey
   for England data on adults 65+) finds average walking speed of
   0.8-0.9 m/s in that age group (~2.9-3.2 km/h), roughly HALF the healthy
   adult pace. Because evacuating groups travel together at the pace of
   their slowest members (families do not leave behind an elderly
   relative or an injured child), we model the GROUP's effective speed as
   linearly bottlenecked toward this slower pace in proportion to the
   vulnerable population percentage:

       effective_kmh = 8.0 - (8.0 - 3.0) * (vulnerable_pct / 100)

   At 0% vulnerable, effective speed = 8.0 km/h (literature base).
   At 100% vulnerable, effective speed = 3.0 km/h (elderly clinical floor).
   This is a simplifying linear interpolation, not a validated functional
   form — a more granular model would require group-composition-specific
   pacing data that does not appear to exist in the public literature.

3. EFFECTIVE TRAVEL HOURS PER DAY (estimated, conservative): rather than
   the arXiv paper's 15 hours/day (near-continuous walking), we use 8
   hours/day of effective walking time, to account for rest, security
   considerations (avoiding night movement in active conflict areas),
   water/food breaks, and the needs of vulnerable group members. This is
   a deliberate conservative choice — see ERCF's general pattern of
   favoring conservative (higher cost / longer time) estimates in
   ambiguous cases to avoid underestimating risk in worst-case planning.

4. WATER/FOOD COST: uses the project's existing UNHCR Baseline Operational
   Cost anchor of USD 3.50/person/day (already catalogued in ERCF's
   Sources list) as the daily provisioning cost during transit. This
   figure was not separately re-derived for walking specifically — it is
   a reuse of an existing project anchor, flagged as estimated.

5. EXPOSURE RISK: longer travel time means more days of exposure to
   conflict risk en route. This module reports the number of exposure-days
   as qualitative/quantitative output, but does NOT automatically feed
   back into D1 (Kinetic Threat) or D6 (Urgency) — that remains a manual
   judgment call for the analyst, flagged here only as a feasibility note.

REAL-WORLD REFERENCE EXAMPLES (qualitative, UNHCR-sourced, not used in
the calculation itself, included for context/calibration sanity-checking)
----------------------------------------------------------------------
- South Sudanese refugees to Kenya (2016): ~644km on foot.
- Rohingya refugees to Bangladesh (2017): ~80-97km on foot.
- Syrian refugees to Za'atari camp, Jordan: ~145km on foot.
(Source: UNHCR "1 Billion Miles to Safety" campaign reporting, via ReliefWeb.)

WHAT IS NOT MODELLED
---------------------
- Terrain difficulty (the existing D4/terrain road-factor multiplier in
  calculators.py is NOT applied here; walking off-road through rugged
  terrain would be slower than this model assumes).
- Checkpoints, border crossings, or deliberate obstruction/delay by armed
  actors.
- Weather conditions during the walk (extreme heat/cold would change both
  speed and water requirements).
- Injury or death risk during transit — this module reports exposure time
  only, not a mortality estimate.
"""

import math
from typing import Dict

# ── Walking speed parameters (estimated, see module docstring) ───────────
HEALTHY_ADULT_KMH = 8.0     # Flee/arXiv-derived base speed
VULNERABLE_FLOOR_KMH = 3.0  # clinical elderly (65+) walking speed, HSE data
EFFECTIVE_HOURS_PER_DAY = 8  # conservative, accounts for rest/security/breaks

# ── Cost parameters (reusing existing project anchor) ────────────────────
COST_PER_PERSON_PER_DAY_USD = 3.50  # UNHCR Baseline Operational Cost (existing ERCF anchor)

# ── Physical supply requirements (validated, Sphere Handbook standard) ───
WATER_L_PER_PERSON_DAY = 15  # Sphere minimum emergency water standard (already an ERCF source anchor)
FOOD_KG_PER_PERSON_DAY = 0.5  # approximate dry-ration mass to meet Sphere's 2,100 kcal/person/day baseline
                               # (WFP general food distribution ration-planning convention; the kcal figure
                               # itself is Sphere-validated, the kg-per-day conversion is an approximation)

# ── Personnel ratios (estimated, humanitarian field conventions) ──────────
MEDICS_PAX_RATIO = 30        # 1 medic per N pax (estimated, MSF/ICRC field convention)
GUIDES_PAX_RATIO = 50        # 1 guide/escort per N pax (estimated)
COORDINATOR_PAX_RATIO = 100  # 1 coordinator per N pax (estimated)

# ── Personnel cost (reusing existing ERCF project anchor) ────────────────
STAFF_DAILY_RATE_USD = 92  # MSF international field salary midpoint ($87-97/day, 2022)
                           # Source: doctorswithoutborders.org/careers/work-internationally/pay-benefits
                           # Already cited as source #18 in the ERCF Sources list.


def calculate_walking_evacuation(
    population: int,
    distance_km: float,
    vulnerable_pct: float = 0,
) -> Dict:
    """
    Calculate time, cost, and exposure risk for on-foot evacuation.

    Args:
        population: number of people evacuating on foot.
        distance_km: distance to safe destination.
        vulnerable_pct: percentage (0-100) of the population that is
            elderly, disabled, a child, or medically vulnerable — reuses
            the same field already present elsewhere in the ERCF tool.

    Returns a dict with effective speed, days needed, total water/food
    cost, exposure-day count, and sourcing/confidence metadata.
    """
    if population <= 0:
        raise ValueError("population must be positive")
    if distance_km <= 0:
        raise ValueError("distance_km must be positive")
    if not (0 <= vulnerable_pct <= 100):
        raise ValueError("vulnerable_pct must be between 0 and 100")

    effective_kmh = HEALTHY_ADULT_KMH - (HEALTHY_ADULT_KMH - VULNERABLE_FLOOR_KMH) * (vulnerable_pct / 100)
    daily_distance_km = effective_kmh * EFFECTIVE_HOURS_PER_DAY
    days_needed = math.ceil(distance_km / daily_distance_km)

    total_water_l = round(population * days_needed * WATER_L_PER_PERSON_DAY)
    total_food_kg = round(population * days_needed * FOOD_KG_PER_PERSON_DAY)

    # Personnel counts
    medical_staff = math.ceil(population / MEDICS_PAX_RATIO)
    guides_escorts = math.ceil(population / GUIDES_PAX_RATIO)
    coordinators = math.ceil(population / COORDINATOR_PAX_RATIO)
    total_staff = medical_staff + guides_escorts + coordinators

    # Cost breakdown
    provisions_cost = round(population * days_needed * COST_PER_PERSON_PER_DAY_USD)
    personnel_cost = round(total_staff * days_needed * STAFF_DAILY_RATE_USD)
    total_cost_usd = provisions_cost + personnel_cost

    feasibility_notes = [
        f"Estimated group walking speed: {effective_kmh:.1f} km/h "
        f"(bottlenecked by {vulnerable_pct:.0f}% vulnerable population share).",
        f"At {EFFECTIVE_HOURS_PER_DAY}h/day effective walking time, "
        f"covering {distance_km:.0f}km requires an estimated {days_needed} day(s).",
        f"Population is exposed to conflict-zone risk for the full duration of transit "
        f"({days_needed} day(s)) — this exposure time is not automatically reflected in "
        f"D1 (Kinetic Threat) or D6 (Urgency) and should be considered manually.",
    ]

    if days_needed > 14:
        feasibility_notes.append(
            "Journey exceeds two weeks — multi-day walking evacuations of this length carry "
            "substantial additional risk (exhaustion, exposure, supply shortfall) not fully "
            "captured by this calculator. Consider whether intermediate way-stations or partial "
            "vehicle/air transport segments are available."
        )

    return {
        "mode": "walking",
        "feasible": True,  # walking is always nominally "feasible" absent a physical barrier; this is a time/cost/risk calculator, not a hard gate
        "feasibility_notes": feasibility_notes,
        "effective_speed_kmh": round(effective_kmh, 1),
        "daily_distance_km": round(daily_distance_km, 1),
        "days_needed": days_needed,
        "exposure_days": days_needed,
        "total_cost_usd": total_cost_usd,
        "cost_breakdown": {
            "provisions_usd": provisions_cost,
            "personnel_usd": personnel_cost,
        },
        "cost_per_person_per_day_usd": COST_PER_PERSON_PER_DAY_USD,
        "supplies": {
            "water_l": total_water_l,
            "water_l_per_person_per_day": WATER_L_PER_PERSON_DAY,
            "food_kg": total_food_kg,
            "food_kg_per_person_per_day": FOOD_KG_PER_PERSON_DAY,
        },
        "personnel": {
            "medical_staff": medical_staff,
            "guides_escorts": guides_escorts,
            "coordinators": coordinators,
            "total_staff": total_staff,
            "daily_rate_usd": STAFF_DAILY_RATE_USD,
            "note": (
                f"Medical staff: 1 per {MEDICS_PAX_RATIO} pax (estimated, MSF/ICRC field convention). "
                f"Guides/escorts: 1 per {GUIDES_PAX_RATIO} pax (estimated humanitarian field convention). "
                f"Coordinators: 1 per {COORDINATOR_PAX_RATIO} pax (estimated). "
                f"Daily rate: MSF international field salary midpoint ${STAFF_DAILY_RATE_USD}/day "
                f"(doctorswithoutborders.org/careers/work-internationally/pay-benefits, 2022)."
            ),
        },
        "distance_km": distance_km,
        "population": population,
        "vulnerable_pct": vulnerable_pct,
        "confidence": "estimated",
        "source": (
            "Walking speed: Flee migration model (Suleimenova, Bell & Groen) and "
            "arXiv:1903.08255 critique (8km/h base, 120km/day realistic threshold). "
            "Vulnerability adjustment: UK Health Survey for England gait-speed data for "
            "adults 65+. Provisions cost: UNHCR Baseline Operational Cost ($3.50/person/day), "
            "an existing ERCF project anchor. Personnel cost: MSF international field salary "
            "$87-97/day (midpoint $92), an existing ERCF project anchor. "
            "See walking_evac.py module docstring for full derivation chain and caveats."
        ),
    }

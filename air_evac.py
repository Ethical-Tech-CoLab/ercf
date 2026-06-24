"""
air_evac.py — Air and helicopter evacuation cost/feasibility calculator.

Extends the ERCF resource model to cover air-based evacuation modes
(fixed-wing aircraft, helicopter) alongside the existing ground transport
model in calculators.py. Used when D4 Logistics or terrain conditions make
ground evacuation infeasible (e.g. no road access, active front line
crossing required, terrain impassable).

VALIDATION STATUS (June 2026)
==============================
FIXED-WING (aircraft): cost figure is VALIDATED — sourced directly from
WFP Executive Board document WFP/EB.A/2025/8-D (10 June 2025), reporting
UNHAS fleet-wide operational cost of USD 2.08 per passenger-kilometre in
2023 (USD 1.98 in 2024). This is a real, audited, fleet-wide operational
figure covering UNHAS's mixed fixed-wing fleet across 21 countries.

HELICOPTER: cost figure is ESTIMATED, with a documented and transparent
derivation chain, because no single published "cost per passenger-km"
figure exists for humanitarian helicopter operations specifically (UNHAS's
$2.08 figure is fleet-wide, mixing fixed-wing and helicopter operations,
and does not break out helicopter-only economics).

Derivation chain for the helicopter estimate:
1. ANCHOR (validated, primary source): UN Procurement Division contract
   PD/C0164/14, "Medium Utility Helicopter Mi-8MTV in support of MINUSCA"
   (Central African Republic peacekeeping mission), awarded to OJSC
   "Nizhnevartovskavia", NTE (Not-To-Exceed) value USD 5,594,000 for a
   12-month period (9 Oct 2014 - 8 Oct 2015). This is a real, audited UN
   procurement record, not a market estimate.
2. ASSUMPTION (estimated, undocumented for this specific contract): annual
   guaranteed flight hours. UN helicopter charter contracts typically
   guarantee a minimum monthly flight-hour block in the broad range of
   50-90 hours/month (600-1,080 hours/year) per industry literature on UN
   aviation "letters of assist" and commercial helicopter contracts, but
   the exact guaranteed-hours figure for THIS specific MINUSCA contract is
   not publicly disclosed. We use the midpoint of that range (840 hrs/yr)
   as the central estimate, with the full range carried through as a
   sensitivity band.
3. RESULT: USD 5,594,000 / 840 hrs ≈ USD 6,660/flight-hour (central
   estimate; range USD 5,180-9,323/hr across the 600-1,080 hr assumption).
4. AIRCRAFT SPECS (validated, manufacturer/technical specs): Mi-8/Mi-17
   family — the "workhorse" of UNHAS helicopter operations per WFP/Rotor &
   Wing/Royal Aeronautical Society reporting — cruise speed ~250 km/h,
   internal fuel range ~450-465km (up to ~960km with auxiliary tanks),
   typical passenger configuration ~24 seats.
5. LOAD FACTOR (estimated, conservative): 50%, deliberately lower than a
   typical scheduled-flight load factor, because emergency evacuation
   demand is lumpy and inelastic — flights may depart under-full due to
   urgency, security windows, or casualty prioritization, unlike a
   commercial route optimized for occupancy. This is a deliberate
   conservative choice to avoid underestimating evacuation cost in the
   highest-risk scenarios (where helicopter access is most likely to be
   the only option).
6. RESULT: USD 6,660/hr ÷ 250 km/h ÷ (24 seats × 0.50) ≈ USD 2.22 per
   passenger-km (central estimate; range USD 1.73-3.11/pax-km).

WHAT IS NOT MODELLED
---------------------
- Landing zone / helipad preparation costs (assumed zero marginal cost if
  any open ground is available; this is a simplification).
- Weather-driven flight cancellation risk (UNHAS reporting confirms
  helicopter flights are frequently cancelled in DRC due to weather; this
  delay risk is not priced into the cost figure, only flagged qualitatively
  in feasibility output).
- Aircraft type variation beyond the Mi-8/17 reference class (e.g. larger
  Chinook-class or smaller utility helicopters would have different
  per-seat economics).
- War-risk insurance premium variation by conflict intensity (the MINUSCA
  contract reflects a specific risk environment in CAR circa 2014-2015;
  costs in an active high-intensity conflict today could be materially
  higher).
"""

import math
from typing import Dict, Optional

# ── Fixed-wing (validated) ──────────────────────────────────────────────
FIXEDWING_COST_PER_PAX_KM = 2.08  # WFP/EB.A/2025/8-D, 2023 fleet-wide figure
FIXEDWING_COST_PER_PAX_KM_2024 = 1.98  # same source, 2024 figure
FIXEDWING_MAX_RANGE_KM = 3000  # generic UNHAS fixed-wing range assumption (Dash 8 class), not type-specific
FIXEDWING_REQUIRES_RUNWAY = True
FIXEDWING_TYPICAL_CAPACITY_PAX = 37  # Dash 8-300 typical config, the most common UNHAS fixed-wing type per WFP fleet reporting
FIXEDWING_CRUISE_KMH = 500  # Dash 8-300 typical cruise speed (manufacturer spec), used only for en-route supply timing

# ── Helicopter (estimated, see module docstring for full derivation) ─────
HELI_HOURLY_COST_LOW = 5180
HELI_HOURLY_COST_MID = 6660
HELI_HOURLY_COST_HIGH = 9323
HELI_CRUISE_KMH = 250
HELI_CAPACITY_PAX = 24
HELI_LOAD_FACTOR = 0.50
HELI_RANGE_KM_INTERNAL = 460   # internal fuel only
HELI_RANGE_KM_AUX = 960        # with auxiliary tanks
HELI_REQUIRES_RUNWAY = False

HELI_COST_PER_PAX_KM_LOW = round(HELI_HOURLY_COST_LOW / HELI_CRUISE_KMH / (HELI_CAPACITY_PAX * HELI_LOAD_FACTOR), 2)
HELI_COST_PER_PAX_KM_MID = round(HELI_HOURLY_COST_MID / HELI_CRUISE_KMH / (HELI_CAPACITY_PAX * HELI_LOAD_FACTOR), 2)
HELI_COST_PER_PAX_KM_HIGH = round(HELI_HOURLY_COST_HIGH / HELI_CRUISE_KMH / (HELI_CAPACITY_PAX * HELI_LOAD_FACTOR), 2)

# ── En-route supplies (reusing the same Sphere-based rates as walking_evac.py) ──
WATER_L_PER_PERSON_DAY = 15
FOOD_KG_PER_PERSON_DAY = 0.5

# ── Fuel consumption (validated, manufacturer/technical source) ───────────
HELI_FUEL_L_PER_HR = 800  # Mi-8T fuel burn ~800 L/hr (PPRuNe industry pilots forum +
                           # Airborne Ops Mi-8T datasheet; consistent across multiple technical sources)
FIXEDWING_FUEL_L_PER_HR = 800  # Dash 8-300 fuel burn ~800 L/hr (manufacturer spec class)

# ── Personnel ratios ──────────────────────────────────────────────────────
PILOTS_PER_AIRCRAFT = 2           # ICAO Annex 1: mandatory for IFR/multi-crew operations
HELI_FLIGHT_ENGINEERS = 1         # Mi-8 standard crew (Airborne Ops datasheet; airliners.net)
MEDICS_PAX_RATIO = 30             # 1 medic per N pax transported (estimated, MSF/ICRC field convention)
WALK_GUIDES_RATIO = 50            # 1 guide/escort per N pax (estimated, humanitarian field convention)
WALK_COORDINATOR_RATIO = 100      # 1 coordinator per N pax (estimated)

# ── Operational tempo (1 aircraft assumed, conservative UNHAS conflict-zone convention) ─
OPS_HOURS_PER_DAY = 8       # flying operations hours per day (matches walking_evac.py convention)
GROUND_TURNAROUND_H = 0.5   # 30-min ground turnaround between sorties (loading/unloading)
FIXEDWING_CRUISE_KMH_OPS = 500  # already defined above as FIXEDWING_CRUISE_KMH — reuse that


def calculate_air_evacuation(
    population: int,
    distance_km: float,
    mode: str = "fixed_wing",
    has_runway: Optional[bool] = None,
) -> Dict:
    """
    Calculate cost and feasibility for air-based evacuation.

    Args:
        population: number of people to evacuate.
        distance_km: straight-line (or routed) distance to safe destination.
        mode: "fixed_wing" or "helicopter".
        has_runway: whether a usable runway/airstrip exists at the origin.
            If False and mode is "fixed_wing", feasibility is flagged as
            blocked (fixed-wing aircraft require a runway; helicopters do
            not). If None, no runway-based feasibility check is applied
            (assumes the question is unanswered, not necessarily that one
            exists).

    Returns a dict with cost, feasibility flags, sourcing/confidence
    metadata, and a low/mid/high range for the helicopter estimate.
    """
    if mode not in ("fixed_wing", "helicopter"):
        raise ValueError("mode must be 'fixed_wing' or 'helicopter'")

    feasibility_notes = []
    feasible = True

    if mode == "fixed_wing":
        if has_runway is False:
            feasible = False
            feasibility_notes.append(
                "No runway/airstrip reported at origin — fixed-wing aircraft cannot operate. "
                "Consider helicopter evacuation instead."
            )
        if distance_km > FIXEDWING_MAX_RANGE_KM:
            feasibility_notes.append(
                f"Distance ({distance_km:.0f}km) exceeds typical UNHAS fixed-wing range "
                f"assumption (~{FIXEDWING_MAX_RANGE_KM}km) — refueling stop or relay likely required."
            )

        cost_per_pax_km = FIXEDWING_COST_PER_PAX_KM
        total_cost = round(population * distance_km * cost_per_pax_km)
        flights_needed = max(1, -(-population // FIXEDWING_TYPICAL_CAPACITY_PAX))
        cost_per_flight = round(total_cost / flights_needed) if flights_needed else total_cost
        feasibility_notes.append(
            f"Estimated {int(flights_needed)} flight(s) needed at typical Dash 8-class capacity "
            f"({FIXEDWING_TYPICAL_CAPACITY_PAX} pax/flight)."
        )

        transit_days = (distance_km / FIXEDWING_CRUISE_KMH) / 24
        enroute_water_l = round(population * transit_days * WATER_L_PER_PERSON_DAY, 1)
        enroute_food_kg = round(population * transit_days * FOOD_KG_PER_PERSON_DAY, 1)

        # Operation duration assuming 1 aircraft (conservative, UNHAS conflict-zone standard)
        round_trip_h = 2 * (distance_km / FIXEDWING_CRUISE_KMH)
        time_per_cycle_h = round_trip_h + GROUND_TURNAROUND_H
        cycles_per_day = max(1, int(OPS_HOURS_PER_DAY / time_per_cycle_h))
        operation_days = math.ceil(flights_needed / cycles_per_day)

        op_duration_note = (
            f"Assuming 1 aircraft operating {OPS_HOURS_PER_DAY}h/day with "
            f"{int(GROUND_TURNAROUND_H*60)}-min ground turnaround: "
            f"{cycles_per_day} flight(s)/day → {operation_days} day(s) total."
        )
        if operation_days > 14:
            op_duration_note += (
                f" WARNING: {operation_days}-day operation with 1 aircraft may exceed "
                f"tactical window — consider multiple aircraft in parallel."
            )
        feasibility_notes.append(op_duration_note)

        return {
            "mode": "fixed_wing",
            "feasible": feasible,
            "feasibility_notes": feasibility_notes,
            "total_cost_usd": total_cost,
            "cost_per_pax_km_usd": cost_per_pax_km,
            "distance_km": distance_km,
            "population": population,
            "flights_needed": int(flights_needed),
            "cost_per_flight_usd": cost_per_flight,
            "operation_days": operation_days,
            "supplies": {"water_l": enroute_water_l, "food_kg": enroute_food_kg},
            "personnel": {
                "pilots": PILOTS_PER_AIRCRAFT,
                "cabin_crew": 1,
                "medical_staff": math.ceil(population / MEDICS_PAX_RATIO),
                "coordinators": 1,
                "note": (
                    f"Pilots/cabin crew are per-aircraft (ICAO Annex 1 mandatory 2-pilot crew). "
                    f"With 1 aircraft, {PILOTS_PER_AIRCRAFT} pilots rotate across all {int(flights_needed)} flights. "
                    f"Medical staff: 1 per {MEDICS_PAX_RATIO} pax (estimated, MSF/ICRC field convention)."
                ),
            },
            "fuel_l": round(FIXEDWING_FUEL_L_PER_HR * (distance_km / FIXEDWING_CRUISE_KMH) * flights_needed),
            "confidence": "validated",
            "source": (
                "WFP Executive Board WFP/EB.A/2025/8-D (10 Jun 2025), "
                "UNHAS fleet-wide 2023 operational cost per passenger-km. "
                "Aircraft capacity assumption (Dash 8-class, 37 pax) is an approximation, "
                "not part of the validated WFP cost figure itself."
            ),
            "requires_runway": FIXEDWING_REQUIRES_RUNWAY,
        }

    # mode == "helicopter"
    max_range = HELI_RANGE_KM_AUX
    if distance_km > max_range:
        feasible = False
        feasibility_notes.append(
            f"Distance ({distance_km:.0f}km) exceeds Mi-8/17-class helicopter maximum range "
            f"even with auxiliary tanks (~{max_range}km). Refueling stop(s) required, or "
            "evacuation is not feasible by helicopter without an intermediate base."
        )
    elif distance_km > HELI_RANGE_KM_INTERNAL:
        feasibility_notes.append(
            f"Distance ({distance_km:.0f}km) exceeds standard internal-fuel range "
            f"(~{HELI_RANGE_KM_INTERNAL}km) — auxiliary fuel tanks or a refueling stop required."
        )

    flights_needed = max(1, -(-population // (HELI_CAPACITY_PAX * HELI_LOAD_FACTOR)))  # ceil division
    feasibility_notes.append(
        f"Estimated {int(flights_needed)} helicopter sorties needed at {HELI_LOAD_FACTOR*100:.0f}% "
        f"load factor ({int(HELI_CAPACITY_PAX*HELI_LOAD_FACTOR)} pax/sortie)."
    )

    flight_hours_per_sortie = round(distance_km / HELI_CRUISE_KMH, 2)
    total_flight_hours = round(flight_hours_per_sortie * flights_needed, 1)
    cost_per_sortie_mid = round(HELI_HOURLY_COST_MID * flight_hours_per_sortie)

    total_cost_mid = round(population * distance_km * HELI_COST_PER_PAX_KM_MID)
    total_cost_low = round(population * distance_km * HELI_COST_PER_PAX_KM_LOW)
    total_cost_high = round(population * distance_km * HELI_COST_PER_PAX_KM_HIGH)

    transit_days = (distance_km / HELI_CRUISE_KMH) / 24
    enroute_water_l = round(population * transit_days * WATER_L_PER_PERSON_DAY, 1)
    enroute_food_kg = round(population * transit_days * FOOD_KG_PER_PERSON_DAY, 1)

    # Operation duration assuming 1 aircraft
    heli_round_trip_h = 2 * (distance_km / HELI_CRUISE_KMH)
    heli_cycle_h = heli_round_trip_h + GROUND_TURNAROUND_H
    heli_cycles_per_day = max(1, int(OPS_HOURS_PER_DAY / heli_cycle_h))
    heli_operation_days = math.ceil(int(flights_needed) / heli_cycles_per_day)

    heli_op_note = (
        f"Assuming 1 helicopter operating {OPS_HOURS_PER_DAY}h/day with "
        f"{int(GROUND_TURNAROUND_H*60)}-min ground turnaround: "
        f"{heli_cycles_per_day} sortie(s)/day → {heli_operation_days} day(s) total."
    )
    if heli_operation_days > 14:
        heli_op_note += (
            f" WARNING: {heli_operation_days}-day operation with 1 helicopter likely exceeds "
            f"tactical window — multiple helicopters strongly recommended."
        )
    feasibility_notes.append(heli_op_note)

    # Fleet planning: how many helicopters needed for each tactical window
    tactical_windows = [3, 7, 14, 30]
    fleet_planning = {}
    for days in tactical_windows:
        sorties_per_day_needed = math.ceil(int(flights_needed) / days)
        helis_needed = math.ceil(sorties_per_day_needed / max(1, heli_cycles_per_day))
        fleet_planning[f'{days}_days'] = {
            'helicopters_needed': helis_needed,
            'sorties_per_day': sorties_per_day_needed,
            'days': days,
        }

    return {
        "mode": "helicopter",
        "feasible": feasible,
        "feasibility_notes": feasibility_notes,
        "total_cost_usd": total_cost_mid,
        "total_cost_usd_range": {"low": total_cost_low, "mid": total_cost_mid, "high": total_cost_high},
        "cost_per_pax_km_usd": HELI_COST_PER_PAX_KM_MID,
        "cost_per_pax_km_range": {
            "low": HELI_COST_PER_PAX_KM_LOW,
            "mid": HELI_COST_PER_PAX_KM_MID,
            "high": HELI_COST_PER_PAX_KM_HIGH,
        },
        "distance_km": distance_km,
        "population": population,
        "flights_needed": int(flights_needed),
        "flight_hours_per_sortie": flight_hours_per_sortie,
        "total_flight_hours": total_flight_hours,
        "cost_per_sortie_usd": cost_per_sortie_mid,
        "operation_days": heli_operation_days,
        "fleet_planning": fleet_planning,
        "supplies": {"water_l": enroute_water_l, "food_kg": enroute_food_kg},
        "personnel": {
            "pilots": PILOTS_PER_AIRCRAFT,
            "flight_engineers": HELI_FLIGHT_ENGINEERS,
            "medical_staff": math.ceil(population / MEDICS_PAX_RATIO),
            "coordinators": 1,
            "note": (
                f"Pilots/engineers are per-aircraft (ICAO Annex 1: 2-pilot mandatory for IFR ops; "
                f"Mi-8 standard crew includes flight engineer per manufacturer spec). "
                f"With 1 helicopter, {PILOTS_PER_AIRCRAFT} pilots + {HELI_FLIGHT_ENGINEERS} engineer "
                f"rotate across all {int(flights_needed)} sorties. "
                f"Medical staff: 1 per {MEDICS_PAX_RATIO} pax (estimated, MSF/ICRC field convention)."
            ),
        },
        "fuel_l": round(HELI_FUEL_L_PER_HR * flight_hours_per_sortie * int(flights_needed)),
        "confidence": "estimated",
        "source": (
            "Derived from UN Procurement Division contract PD/C0164/14 "
            "(Mi-8MTV, MINUSCA, USD 5.59M/year) combined with an estimated "
            "600-1,080 annual flight-hour range typical of UN helicopter charter "
            "contracts, and Mi-8/17 manufacturer cruise speed and capacity specs. "
            "See air_evac.py module docstring for full derivation chain and caveats."
        ),
        "requires_runway": HELI_REQUIRES_RUNWAY,
    }

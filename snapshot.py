"""Pre-compute historical-case results for static (GitHub Pages) deployment.

Mirrors /api/historical-cases (index.json — all 31 cases + three_index) and
adds per-case cost snapshots (cases/{id}.json — resources/staying/remaining
costs) for the 16 in-scope cases, using the same parameter derivation as
computeHistCaseCosts() in static/app.js so snapshot and live numbers agree.
"""
import json
import os

from historical_data import HISTORICAL_CASES
from calculators import (
    calculate_risk,
    calculate_resources,
    calculate_staying_costs,
    calculate_remaining_costs,
)

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshot")
CASES_DIR = os.path.join(SNAPSHOT_DIR, "cases")

# No per-case terrain data available — matches HIST_TERRAIN_DEFAULT in static/app.js
TERRAIN_DEFAULT = 3


def _is_out_of_scope(case):
    return case.get("model_calibration", {}).get("out_of_scope", False)


def _remaining_pct(case):
    displaced = case.get("displaced")
    pop = case.get("population_at_risk")
    if displaced is not None and pop:
        return max(0.0, 1 - displaced / pop)
    return 0.5


def build_case_costs(case):
    ri = case.get("risk_indicators", {})
    vulnerable_pct = case.get("vulnerable_pct", 20)
    distance_km = case.get("distance_km", 50)
    risk_level = case["risk_level"]
    population = case["population_at_risk"]
    days = case["duration_days"]

    resources = calculate_resources(
        population, vulnerable_pct, risk_level, distance_km,
        ri.get("d2_vulnerability", 3.0), TERRAIN_DEFAULT,
        None, ri.get("d4_logistics", 3.0), ri.get("d5_destination", 3.0),
    )
    staying_costs = calculate_staying_costs(
        population, risk_level, days, ri,
        _remaining_pct(case), case.get("exposure_type", "auto"),
    )
    remaining_costs = calculate_remaining_costs(
        population, vulnerable_pct, risk_level, days,
        distance_km, ri, TERRAIN_DEFAULT,
    )

    return {
        "id": case["id"],
        "name": case["name"],
        "resources": resources,
        "staying_costs": staying_costs,
        "remaining_costs": remaining_costs,
    }


def main():
    os.makedirs(CASES_DIR, exist_ok=True)

    index_cases = []
    in_scope_count = 0
    for case in HISTORICAL_CASES:
        indicators = case.get("risk_indicators", {})
        three_index = calculate_risk(indicators) if indicators else None
        index_cases.append({**case, "three_index": three_index})

        if not _is_out_of_scope(case):
            snap = build_case_costs(case)
            with open(os.path.join(CASES_DIR, f"{case['id']}.json"), "w") as f:
                json.dump(snap, f, indent=2)
            in_scope_count += 1

    with open(os.path.join(SNAPSHOT_DIR, "index.json"), "w") as f:
        json.dump(index_cases, f, indent=2)

    print(f"snapshot/index.json: {len(index_cases)} cases")
    print(f"snapshot/cases/: {in_scope_count} in-scope cost snapshots")


if __name__ == "__main__":
    main()

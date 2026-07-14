"""
RICS cost engine — Layer 1.

Adapts ERCF's calculate_resources()/infra_denial_mult() (calculators.py) into the
two-trajectory break-even RICS needs, per DESIGN.md §2/§7 (v0.2: confMult widens
the break-even band itself, not only Layer 2's readiness match).

── MERGE STATUS (team split) ──────────────────────────────────────────────────
This file is the cost-layer contributor's full deliverable within RICS. It has
no dependency on pathways.py (matching/capacity — readiness teammate's module),
readiness_engine.py (ported from India-EvacSimulation, readiness teammate's
module), or database.py — every function here takes plain values/dataclasses
as input and returns plain dataclasses/dicts, so it can be imported and tested
standalone (see the `__main__` block below) ahead of the team merge. Its only
internal dependency is parameter_registry.py (also this contributor's file).
When the team merges, main.py is the integration point that wires this
module's outputs alongside the other two layers — nothing in cost_engine.py
itself needs to change for that merge to happen.

FORMULA DOCUMENTATION
======================
TRAJECTORY A — status-quo annual cost, per person in a cohort
  Reuses ERCF's Sphere/UNHCR/WFP per-person-day line items, annualized (×365)
  instead of sized for a 3-day evacuation convoy, plus one line ERCF's evacuation
  model never needed (protection/admin overhead — currently uncosted, see below):

    water_per_person_year    = water_l_per_person_day × 365 × water_usd_per_l
    food_per_person_year     = food_kg_per_person_day × 365 × food_usd_per_kg
    shelter_per_person_year  = (tent_usd_per_unit / tent_occupancy_persons) / tent_lifetime_years
    medical_per_person_year  = (medical_staff_daily_usd / medical_staff_ratio) × 365

    subtotal_per_person_year = sum of the above
    protection_admin_line    = subtotal × rics_protection_admin_overhead_pct  (if set; else 0, flagged)
    pre_multiplier_total     = subtotal + protection_admin_line

    funding_shortfall_mult   = f(funding_shortfall_pct, rics_funding_shortfall_alpha)
                               — if alpha is unset (current state — see parameter_registry.py),
                                 multiplier = 1.0 and the output is flagged not_calibrated=True.
                               — once calibrated: (1 + funding_shortfall_pct) ** alpha,
                                 the same shape as ERCF's infra_denial_mult(), new driver.

    trajectory_a_per_person_year = pre_multiplier_total × funding_shortfall_mult
    trajectory_a_annual_total    = trajectory_a_per_person_year × cohort.count

  tent_lifetime_years has no registry value yet (parameter_registry.py: None,
  unvalidated) — callers MUST supply tent_lifetime_years_override until a real
  UNHCR shelter-replacement-cycle figure is sourced. This raises rather than
  silently assuming a number, per the "no false precision" principle §14 insists on.

TRAJECTORY B — front-loaded inclusion/resettlement investment
  No ERCF equivalent exists (DESIGN.md §2: "New — no ERCF equivalent"). This
  function does NOT invent placeholder dollar figures for documentation, skills
  credentialing, transport, start-up capital, or host co-investment — it sums
  whatever the caller supplies, each tagged, and flags any component left at 0
  as "not yet costed" rather than treating zero as a real estimate.

BREAK-EVEN
  Trajectory B is modeled as one-time with an optional small residual annual
  cost after transition (default 0 — assumes a successfully included/resettled
  cohort leaves the aid caseload; ERCF's evacuation model needed a nonzero
  "Option B" recurring term because its whole population stayed in zone, RICS's
  Trajectory B does not, by design — this is a modeling assumption, stated here
  rather than left implicit):

    breakeven_year = trajectory_b_upfront / (trajectory_a_annual − trajectory_b_residual_annual)

  If trajectory_a_annual <= trajectory_b_residual_annual, there is no break-even
  (the inclusion pathway costs as much or more per year than the status quo) —
  the function returns None for that bound rather than a negative/nonsensical year.

UNCERTAINTY BAND (v0.2 correction — DESIGN.md §7)
  confMult (shared with Layer 2/3, NOT a second slider) widens every contributing
  parameter's point estimate to (low, high) via its registry tag's
  base_uncertainty_pct × (2 − confMult), per parameter_registry.uncertainty_pct().
  Bounds propagate through the (purely multiplicative/divisive) formulas above via
  interval arithmetic — the low/high total is the product of each line's low/high
  bound, not a re-run of a stochastic engine (§14: cost is the reliable half; no
  Monte Carlo duplication here).

    breakeven_year_low  = breakeven(trajectory_a_high, trajectory_b_low)   # fastest crossover
    breakeven_year_high = breakeven(trajectory_a_low,  trajectory_b_high)  # slowest crossover
"""

from dataclasses import dataclass, field
from typing import Optional

from parameter_registry import PARAMETER_REGISTRY, uncertainty_pct


def _bounds(key: str, conf_mult: float):
    """(point, low, high) for a registry parameter under confMult. Raises if the
    registry value is None — callers must supply an explicit override rather than
    silently computing against a missing number."""
    entry = PARAMETER_REGISTRY[key]
    point = entry["value"]
    if point is None:
        raise ValueError(
            f"parameter_registry['{key}'] has no value yet (tag={entry['tag']}, "
            f"source={entry['source']!r}) — supply an explicit override, do not assume a figure."
        )
    pct = uncertainty_pct(key) * (2 - conf_mult)
    return point, point * (1 - pct), point * (1 + pct)


def _override_bounds(value: float, conf_mult: float, base_uncertainty_pct: float = 0.60):
    """Same shape as _bounds() for a caller-supplied override not yet in the registry.
    Defaults to the 'unvalidated' band width (60%) since anything not in the registry
    is by definition not yet validated."""
    pct = base_uncertainty_pct * (2 - conf_mult)
    return value, value * (1 - pct), value * (1 + pct)


def _mul(*terms):
    """terms: (point, low, high, power) where power=+1 multiplies, -1 divides.
    Valid interval arithmetic for chains of strictly positive quantities."""
    point = low = high = 1.0
    for p, lo, hi, power in terms:
        if power == 1:
            point *= p
            low *= lo
            high *= hi
        elif power == -1:
            point /= p
            low /= hi   # dividing by a larger denominator shrinks the result -> use denominator's high bound for the overall low bound
            high /= lo
        else:
            raise ValueError("power must be +1 or -1")
    return point, low, high


def _add(*triples):
    point = sum(t[0] for t in triples)
    low = sum(t[1] for t in triples)
    high = sum(t[2] for t in triples)
    return point, low, high


@dataclass
class TrajectoryAResult:
    per_person_year: tuple       # (point, low, high) USD/person/year
    annual_total: tuple          # (point, low, high) USD/year for the full cohort
    funding_shortfall_calibrated: bool
    protection_admin_costed: bool
    line_items: dict = field(default_factory=dict)  # per-line (point, low, high), for audit


@dataclass
class TrajectoryBResult:
    upfront_total: tuple         # (point, low, high) USD, one-time
    residual_annual_total: tuple # (point, low, high) USD/year after transition (default 0)
    uncosted_components: list    # component names left at 0 — NOT assumed free, just not yet priced
    line_items: dict = field(default_factory=dict)


def compute_trajectory_a(
    cohort_count: int,
    conf_mult: float,
    tent_lifetime_years_override: float,
    funding_shortfall_pct: float = 0.0,
) -> TrajectoryAResult:
    if not (0.0 <= conf_mult <= 1.0):
        raise ValueError("conf_mult must be in [0,1] (1 - uncertaintyLevel, shared with Layer 2/3)")

    water_qty   = _bounds("water_l_per_person_day", conf_mult)
    water_price = _bounds("water_usd_per_l", conf_mult)
    water_line  = _mul((*water_qty, 1), (*water_price, 1), (365, 365, 365, 1))

    food_qty   = _bounds("food_kg_per_person_day", conf_mult)
    food_price = _bounds("food_usd_per_kg", conf_mult)
    food_line  = _mul((*food_qty, 1), (*food_price, 1), (365, 365, 365, 1))

    tent_price = _bounds("tent_usd_per_unit", conf_mult)
    tent_occ   = _bounds("tent_occupancy_persons", conf_mult)
    tent_life  = _override_bounds(tent_lifetime_years_override, conf_mult)
    shelter_line = _mul((*tent_price, 1), (*tent_occ, -1), (*tent_life, -1))

    med_daily = _bounds("medical_staff_daily_usd", conf_mult)
    med_ratio = _bounds("medical_staff_ratio", conf_mult)
    medical_line = _mul((*med_daily, 1), (*med_ratio, -1), (365, 365, 365, 1))

    subtotal = _add(water_line, food_line, shelter_line, medical_line)

    protection_entry = PARAMETER_REGISTRY["rics_protection_admin_overhead_pct"]
    protection_costed = protection_entry["value"] is not None
    if protection_costed:
        pct = _bounds("rics_protection_admin_overhead_pct", conf_mult)
        pre_mult_total = _add(subtotal, _mul((*subtotal, 1), (*pct, 1)))
    else:
        pre_mult_total = subtotal

    alpha_entry = PARAMETER_REGISTRY["rics_funding_shortfall_alpha"]
    calibrated = alpha_entry["value"] is not None
    if calibrated:
        alpha = _bounds("rics_funding_shortfall_alpha", conf_mult)
        mult_point = (1 + funding_shortfall_pct) ** alpha[0]
        mult_low = (1 + funding_shortfall_pct) ** alpha[1]
        mult_high = (1 + funding_shortfall_pct) ** alpha[2]
        per_person = _mul((*pre_mult_total, 1), (mult_point, mult_low, mult_high, 1))
    else:
        per_person = pre_mult_total  # multiplier=1.0, flagged via calibrated=False

    annual_total = tuple(v * cohort_count for v in per_person)

    return TrajectoryAResult(
        per_person_year=per_person,
        annual_total=annual_total,
        funding_shortfall_calibrated=calibrated,
        protection_admin_costed=protection_costed,
        line_items={
            "water": water_line, "food": food_line,
            "shelter": shelter_line, "medical": medical_line,
            "subtotal": subtotal, "pre_multiplier_total": pre_mult_total,
        },
    )


def compute_trajectory_b(
    conf_mult: float,
    documentation_usd: float = 0.0,
    skills_credentialing_usd: float = 0.0,
    transport_usd: float = 0.0,
    startup_capital_usd: float = 0.0,
    host_coinvestment_offset_usd: float = 0.0,
    residual_annual_usd: float = 0.0,
) -> TrajectoryBResult:
    """Every component defaults to 0 (uncosted), NOT an assumption that the
    component is free — uncosted components are returned in `uncosted_components`
    so a caller/report can never mistake a missing figure for a zero estimate."""
    components = {
        "documentation": documentation_usd,
        "skills_credentialing": skills_credentialing_usd,
        "transport": transport_usd,
        "startup_capital": startup_capital_usd,
    }
    uncosted = [name for name, v in components.items() if v == 0.0]

    bounds = {name: _override_bounds(v, conf_mult) for name, v in components.items() if v}
    upfront = _add(*bounds.values()) if bounds else (0.0, 0.0, 0.0)

    offset = _override_bounds(host_coinvestment_offset_usd, conf_mult) if host_coinvestment_offset_usd else (0.0, 0.0, 0.0)
    upfront_net = (
        upfront[0] - offset[0],
        upfront[1] - offset[2],  # subtracting a larger offset shrinks the low bound less -> use offset's high for net's low
        upfront[2] - offset[1],
    )

    residual = _override_bounds(residual_annual_usd, conf_mult) if residual_annual_usd else (0.0, 0.0, 0.0)

    return TrajectoryBResult(
        upfront_total=upfront_net,
        residual_annual_total=residual,
        uncosted_components=uncosted,
        line_items=bounds,
    )


def breakeven_year(trajectory_a_annual: float, trajectory_b_upfront: float, trajectory_b_residual_annual: float = 0.0) -> Optional[float]:
    diff = trajectory_a_annual - trajectory_b_residual_annual
    if diff <= 0:
        return None
    return trajectory_b_upfront / diff


def compute_breakeven(traj_a: TrajectoryAResult, traj_b: TrajectoryBResult) -> dict:
    a_point, a_low, a_high = traj_a.annual_total
    b_point, b_low, b_high = traj_b.upfront_total
    r_point, r_low, r_high = traj_b.residual_annual_total

    point = breakeven_year(a_point, b_point, r_point)
    # fastest crossover: status quo costed pessimistically (high), inclusion costed optimistically (low)
    low = breakeven_year(a_high, b_low, r_low)
    # slowest crossover: status quo costed optimistically (low), inclusion costed pessimistically (high)
    high = breakeven_year(a_low, b_high, r_high)

    band_width = (high - low) if (low is not None and high is not None) else None

    return {
        "breakeven_year_point": point,
        "breakeven_year_low": low,
        "breakeven_year_high": high,
        "breakeven_year_band_width": band_width,
        "funding_shortfall_calibrated": traj_a.funding_shortfall_calibrated,
        "protection_admin_costed": traj_a.protection_admin_costed,
        "trajectory_b_uncosted_components": traj_b.uncosted_components,
    }


def compute_breakeven_series(traj_a: TrajectoryAResult, traj_b: TrajectoryBResult, horizon_years: Optional[int] = None) -> list:
    """Ready-to-plot year-by-year series for the break-even chart — every value
    computed here, not in the frontend (per RICS's frontend spec: the chart must
    only render arrays handed to it, unlike ERCF's original app.js chart, which
    computes `lineA`/`lineB` client-side from raw cost inputs).

    Trajectory A is plotted as a single cumulative line (point estimate only, per
    the frontend spec). Trajectory B is plotted as a constant band (low/high,
    since it's a one-time upfront cost, not a per-year accumulation) plus its own
    point estimate line, to be filled between low/high in the chart.
    """
    a_point = traj_a.annual_total[0]
    b_point, b_low, b_high = traj_b.upfront_total

    be = compute_breakeven(traj_a, traj_b)
    default_horizon = 15
    candidates = [default_horizon]
    if be["breakeven_year_high"] is not None:
        candidates.append(int(be["breakeven_year_high"]) + 2)
    horizon = horizon_years if horizon_years is not None else min(max(candidates), 30)

    return [
        {
            "year": year,
            "trajectory_a_cumulative": a_point * year,
            "trajectory_b_point": b_point,
            "trajectory_b_low": b_low,
            "trajectory_b_high": b_high,
        }
        for year in range(1, horizon + 1)
    ]


if __name__ == "__main__":
    # Illustrative run — NOT a Dzaleka estimate. cohort_count, tent_lifetime_years,
    # and every Trajectory B component below are placeholders pending real sourcing
    # (pathways.py / cohorts.py, next in the scaffolding order per DESIGN.md §11).
    traj_a = compute_trajectory_a(
        cohort_count=1000,
        conf_mult=0.70,  # illustrative 30% global uncertainty level
        tent_lifetime_years_override=5.0,
        funding_shortfall_pct=0.90,  # report §4: ~90% UNHCR budget cut
    )
    traj_b = compute_trajectory_b(
        conf_mult=0.70,
        documentation_usd=50_000,
        skills_credentialing_usd=20_000,
        transport_usd=80_000,
        startup_capital_usd=150_000,
        host_coinvestment_offset_usd=30_000,
    )
    result = compute_breakeven(traj_a, traj_b)
    print("Trajectory A per-person/year (point, low, high):", traj_a.per_person_year)
    print("Trajectory A annual total    (point, low, high):", traj_a.annual_total)
    print("Trajectory B upfront total   (point, low, high):", traj_b.upfront_total)
    print("Funding-shortfall multiplier calibrated:", traj_a.funding_shortfall_calibrated,
          "(funding_shortfall_pct=0.90 passed above was a no-op — multiplier stays 1.0 until alpha is calibrated)")
    print("Protection/admin line costed:", traj_a.protection_admin_costed)
    print("Break-even:", result)

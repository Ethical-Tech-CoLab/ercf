#!/usr/bin/env python3
"""
ERCF Mortality Model — Calibration script
Runs calculate_staying_costs() against 20 in-scope historical cases,
then computes R² (Pearson log-log), within-2× count, and LOOCV R².

No external dependencies — stdlib + math only.

Usage:
    python calibration/calibrate.py
    python calibration/calibrate.py --by-level   (breakdown per risk level)
"""
import math
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from historical_data import HISTORICAL_CASES
from calculators import calculate_staying_costs, infra_denial_mult


# ── Metric helpers ────────────────────────────────────────────────────────────

def _log_pairs(xs, ys):
    """Return (log10 x, log10 y) pairs, skipping zeros."""
    return [(math.log10(x), math.log10(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]


def pearson_r2_log(xs, ys):
    """R² from Pearson correlation on log10-transformed (recorded, model) pairs."""
    pairs = _log_pairs(xs, ys)
    n = len(pairs)
    if n < 2:
        return float('nan')
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num   = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    denom = math.sqrt(
        sum((p[0] - mx) ** 2 for p in pairs) *
        sum((p[1] - my) ** 2 for p in pairs)
    )
    if denom == 0:
        return float('nan')
    return (num / denom) ** 2


def loocv_r2(xs, ys):
    """
    Leave-One-Out Cross-Validation R² on log10 space.
    Fits a simple OLS line on n-1 points, predicts the left-out point,
    then computes R² from the LOOCV residuals.
    """
    pairs = _log_pairs(xs, ys)
    n = len(pairs)
    if n < 3:
        return float('nan')

    loo_preds = []
    for i in range(n):
        train = [p for j, p in enumerate(pairs) if j != i]
        tx = [p[0] for p in train]
        ty = [p[1] for p in train]
        mtx = sum(tx) / (n - 1)
        mty = sum(ty) / (n - 1)
        cov_xy = sum((tx[j] - mtx) * (ty[j] - mty) for j in range(n - 1))
        var_x  = sum((tx[j] - mtx) ** 2 for j in range(n - 1))
        if var_x == 0:
            loo_preds.append(pairs[i][1])
            continue
        slope     = cov_xy / var_x
        intercept = mty - slope * mtx
        loo_preds.append(slope * pairs[i][0] + intercept)

    actual   = [p[1] for p in pairs]
    mean_act = sum(actual) / n
    ss_res   = sum((actual[i] - loo_preds[i]) ** 2 for i in range(n))
    ss_tot   = sum((a - mean_act) ** 2 for a in actual)
    return float('nan') if ss_tot == 0 else 1 - ss_res / ss_tot


# ── Case runner ───────────────────────────────────────────────────────────────

def run_case(case, apply_infra_denial=True):
    """
    Call calculate_staying_costs() with the case's parameters.
    remaining_pct derived from remaining_count / population_at_risk.
    For cases with infra_denial_flag=True, applies the multiplier manually
    (calculate_staying_costs hardcodes infra_denial=False for live scenarios).
    Pass apply_infra_denial=False to skip the manual correction entirely.
    Returns model_deaths (float).
    """
    pop          = case["population_at_risk"]
    days         = case["duration_days"]
    level        = case["risk_level"]
    dims         = case["risk_indicators"]
    exposure     = case.get("exposure_type", "auto")
    # Prefer v2_parameters.remaining_pct (calibrated from actual displacement data)
    # over remaining_count/pop, which is inconsistent for enclave cases (e.g. Gaza:
    # entire pop stayed in enclave but 83% internally displaced from front lines).
    cal = case.get("model_calibration", {})
    v2p = cal.get("v2_parameters", {})
    if "remaining_pct" in v2p:
        remaining_pct = v2p["remaining_pct"]
        rp_source = "v2_params"
    else:
        remaining_ct = case.get("remaining_count", pop)
        remaining_pct = remaining_ct / pop if pop > 0 else 1.0
        rp_source = "count/pop"

    # exposure_type keys match CONFLICT_TYPE_EXPOSURE keys directly
    conflict_type = exposure if exposure in ("urban_siege", "enclave", "city_conflict", "regional") else "auto"

    result = calculate_staying_costs(
        population=pop,
        risk_level=level,
        days=days,
        dims=dims,
        remaining_pct=remaining_pct,
        conflict_type=conflict_type,
    )
    model_deaths = result["totals"]["deaths"]

    # Infra-denial correction for flagged cases (manual, since function hardcodes False)
    if apply_infra_denial and cal.get("infra_denial_flag", False):
        d1 = float(dims.get("d1_kinetic", dims.get("d1", 3.0)))
        d4 = float(dims.get("d4_logistics", dims.get("d4", 3.0)))
        id_mult = infra_denial_mult(True, d1, d4)
        model_deaths = model_deaths * id_mult

    return model_deaths, result["parameters"], rp_source


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ERCF calibration runner")
    parser.add_argument("--by-level", action="store_true", help="Show per-level breakdown")
    parser.add_argument("--no-infra-denial", action="store_true", help="Skip infra_denial multiplier for all cases")
    args = parser.parse_args()
    apply_id = not args.no_infra_denial

    in_scope = [
        c for c in HISTORICAL_CASES
        if not c.get("model_calibration", {}).get("out_of_scope", False)
    ]

    print(f"ERCF Calibration — {len(HISTORICAL_CASES)} total cases, {len(in_scope)} in-scope")
    print()

    col_w = 42
    print(f"{'Case':<{col_w}} {'Rec':>8} {'Model':>8} {'Ratio':>7}  W2x  {'Level':>5}")
    print("─" * (col_w + 35))

    recorded_all, model_all = [], []
    within_2x_total = 0
    by_level: dict = {}
    rows = []

    for case in in_scope:
        cal      = case.get("model_calibration", {})
        recorded = cal.get("recorded_deaths")
        if not recorded:
            continue

        model_deaths, params, rp_src = run_case(case, apply_infra_denial=apply_id)
        ratio = model_deaths / recorded
        w2x   = 0.5 <= ratio <= 2.0
        level = case["risk_level"]
        infra = cal.get("infra_denial_flag", False)

        if w2x:
            within_2x_total += 1
        recorded_all.append(recorded)
        model_all.append(model_deaths)

        lvl_data = by_level.setdefault(level, {"rec": [], "mdl": [], "w2x": 0, "n": 0})
        lvl_data["rec"].append(recorded)
        lvl_data["mdl"].append(model_deaths)
        lvl_data["n"] += 1
        if w2x:
            lvl_data["w2x"] += 1

        rows.append((case["name"], recorded, model_deaths, ratio, w2x, level, infra, rp_src))

    for name, rec, mdl, ratio, w2x, level, infra, rp_src in rows:
        flag = "✓" if w2x else "✗"
        inf  = " [ID]" if infra else ""
        rp   = "*" if rp_src == "count/pop" else ""
        print(f"{(name + inf):<{col_w}} {rec:>8,} {mdl:>8,.0f} {ratio:>7.2f}×   {flag}{rp:<2}  L{level}")

    n = len(rows)
    print("─" * (col_w + 35))
    print()

    r2  = pearson_r2_log(recorded_all, model_all)
    loo = loocv_r2(recorded_all, model_all)

    print(f"Cases evaluated : {n}")
    print(f"Within 2×       : {within_2x_total}/{n} ({100*within_2x_total/n:.0f}%)")
    print(f"R² (Pearson log): {r2:.3f}")
    print(f"LOOCV R²        : {loo:.3f}")
    print(f"LOOCV gap       : {r2 - loo:.3f}")

    if args.by_level:
        print()
        print("Per-level breakdown:")
        print(f"  {'Level':>5}  {'n':>3}  {'W2x':>8}  {'R²':>6}")
        print("  " + "─" * 30)
        for lvl in sorted(by_level):
            d    = by_level[lvl]
            w2x_ = d["w2x"]
            n_   = d["n"]
            r2_  = pearson_r2_log(d["rec"], d["mdl"])
            r2_s = f"{r2_:.3f}" if not math.isnan(r2_) else "  n/a"
            print(f"  L{lvl}    {n_:>3}  {w2x_}/{n_} ({100*w2x_//n_:.0f}%)  {r2_s}")

    print()
    print("Notes:")
    print("  [ID] = infra_denial_flag=True — multiplier applied manually on top of base model")
    print("  *    = remaining_pct from remaining_count/population_at_risk (no v2_parameters)")
    print("         all others use model_calibration.v2_parameters.remaining_pct")
    print("  Days > 90: saturation formula applied inside calculate_staying_costs()")


if __name__ == "__main__":
    main()

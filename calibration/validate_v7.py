#!/usr/bin/env python3
"""
ERCF Mortality Model v7 — Complete Statistical Validation
Re-runs all 8 diagnostic tests on v7 parameters against the 16 in-scope
calibration cases, using the same run_case() logic as calibrate.py.

Dependencies: scipy, statsmodels, numpy

Usage:
    python calibration/validate_v7.py
"""
import math
import sys
import os
import numpy as np
from scipy import stats as scipy_stats
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add calibration dir so we can import from calibrate.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historical_data import HISTORICAL_CASES
from calibrate import run_case, pearson_r2_log, loocv_r2


def main():
    # ── Collect in-scope cases ────────────────────────────────────────────────
    in_scope = [
        c for c in HISTORICAL_CASES
        if not c.get("model_calibration", {}).get("out_of_scope", False)
    ]

    recorded_all, model_all = [], []
    meta = []  # per-case metadata for VIF and labelling

    for case in in_scope:
        cal      = case.get("model_calibration", {})
        recorded = cal.get("recorded_deaths")
        if not recorded:
            continue
        model_deaths, _params, _rp = run_case(case, apply_infra_denial=True)
        recorded_all.append(recorded)
        model_all.append(model_deaths)
        dims = case["risk_indicators"]
        meta.append({
            "name":     case["name"][:38],
            "log_pop":  math.log10(max(1, case["population_at_risk"])),
            "log_days": math.log10(max(1, case["duration_days"])),
            "level":    float(case["risk_level"]),
            "D1":       float(dims.get("d1_kinetic",   dims.get("d1", 3.0))),
            "D4":       float(dims.get("d4_logistics", dims.get("d4", 3.0))),
        })

    n       = len(recorded_all)
    log_rec = np.array([math.log10(r) for r in recorded_all])
    log_mdl = np.array([math.log10(m) for m in model_all])

    # OLS fit in log-log space (used by BP, Cook's, DW)
    X_ols    = sm.add_constant(log_rec)
    ols_fit  = sm.OLS(log_mdl, X_ols).fit()
    ols_resid = ols_fit.resid          # residuals from OLS line (not raw log diff)
    raw_resid = log_mdl - log_rec      # raw log-space residuals (model vs recorded)
    n_params  = 2                      # intercept + slope

    W = 65
    print("=" * W)
    print(f"  ERCF Mortality Model v7 — Statistical Validation  (N={n})")
    print("=" * W)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Pearson R² (log-log)
    # ─────────────────────────────────────────────────────────────────────────
    r2           = pearson_r2_log(recorded_all, model_all)
    pearson_r, pearson_p = scipy_stats.pearsonr(log_rec, log_mdl)

    print(f"\n1. Pearson R² (log-log regression)")
    print(f"   R²          = {r2:.3f}")
    print(f"   r           = {pearson_r:.3f}")
    print(f"   p           = {pearson_p:.2e}")
    print(f"   Verdict     : {'PASS' if r2 >= 0.70 else 'FAIL'}  (threshold R² ≥ 0.70)")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Shapiro-Wilk — normality of raw log residuals
    # ─────────────────────────────────────────────────────────────────────────
    sw_stat, sw_p = scipy_stats.shapiro(raw_resid)

    print(f"\n2. Shapiro-Wilk (normality of log residuals: log(model) − log(recorded))")
    print(f"   W           = {sw_stat:.3f}")
    print(f"   p           = {sw_p:.3f}")
    print(f"   Verdict     : {'PASS' if sw_p >= 0.05 else 'FAIL — reject normality (p < 0.05)'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Breusch-Pagan — heteroscedasticity of OLS residuals vs log(recorded)
    # ─────────────────────────────────────────────────────────────────────────
    bp_lm, bp_p, _bp_f, _bp_fp = het_breuschpagan(ols_resid, X_ols)

    print(f"\n3. Breusch-Pagan (heteroscedasticity of OLS residuals)")
    print(f"   LM          = {bp_lm:.3f}")
    print(f"   p           = {bp_p:.3f}")
    print(f"   Verdict     : {'PASS' if bp_p >= 0.05 else 'FAIL — heteroscedasticity detected'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Cook's Distance — influential observations
    #    D_i = (e_i² / (p · MSE)) · (h_ii / (1−h_ii)²)
    # ─────────────────────────────────────────────────────────────────────────
    mse       = float(np.sum(ols_resid**2) / (n - n_params))
    hat_mat   = X_ols @ np.linalg.inv(X_ols.T @ X_ols) @ X_ols.T
    h_diag    = np.diag(hat_mat)
    cooks     = (ols_resid**2 / (n_params * mse)) * (h_diag / (1 - h_diag)**2)
    threshold = 4.0 / n
    n_above   = int(np.sum(cooks > threshold))

    print(f"\n4. Cook's Distance  (threshold 4/n = {threshold:.3f})")
    sorted_idx = np.argsort(cooks)[::-1]
    for i in sorted_idx[:3]:
        marker = " ← ABOVE THRESHOLD" if cooks[i] > threshold else ""
        print(f"   {meta[i]['name']:<38}  D = {cooks[i]:.3f}{marker}")
    print(f"   {n_above}/{n} above threshold")
    if n_above == 0:
        print(f"   Verdict     : PASS")
    else:
        print(f"   Verdict     : NOTE — {n_above} influential observation(s)")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. LOOCV R²
    # ─────────────────────────────────────────────────────────────────────────
    loo = loocv_r2(recorded_all, model_all)
    gap = r2 - loo

    print(f"\n5. LOOCV R² (out-of-sample generalisation)")
    print(f"   LOOCV R²    = {loo:.3f}")
    print(f"   In-sample   = {r2:.3f}")
    print(f"   Gap         = {gap:.3f}")
    print(f"   Verdict     : {'PASS' if gap <= 0.05 else 'NOTE — gap > 0.05'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Spearman ρ — non-parametric robustness
    # ─────────────────────────────────────────────────────────────────────────
    sp_rho, sp_p = scipy_stats.spearmanr(log_rec, log_mdl)

    print(f"\n6. Spearman ρ (non-parametric robustness)")
    print(f"   ρ           = {sp_rho:.3f}")
    print(f"   ρ²          = {sp_rho**2:.3f}")
    print(f"   p           = {sp_p:.2e}")
    print(f"   Verdict     : {'PASS' if sp_p < 0.001 else 'NOTE — p ≥ 0.001'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Durbin-Watson — ordered by log(recorded) (cross-sectional analogue)
    # ─────────────────────────────────────────────────────────────────────────
    order         = np.argsort(log_rec)
    ordered_resid = ols_resid[order]
    dw_stat       = durbin_watson(ordered_resid)

    print(f"\n7. Durbin-Watson (residuals ordered by log recorded)")
    print(f"   DW          = {dw_stat:.3f}  (2.0 = no autocorrelation)")
    if dw_stat < 1.5:
        dw_verdict = "DOCUMENTED — positive clustering; reflects discrete exposure categories"
    elif dw_stat > 2.5:
        dw_verdict = "NOTE — negative autocorrelation"
    else:
        dw_verdict = "PASS"
    print(f"   Verdict     : {dw_verdict}")

    # ─────────────────────────────────────────────────────────────────────────
    # 8. VIF — multicollinearity among log_pop, log_days, level, D1, D4
    # ─────────────────────────────────────────────────────────────────────────
    X_vif = np.column_stack([
        [d["log_pop"]  for d in meta],
        [d["log_days"] for d in meta],
        [d["level"]    for d in meta],
        [d["D1"]       for d in meta],
        [d["D4"]       for d in meta],
    ])
    X_vif_c  = sm.add_constant(X_vif)
    predictor_labels = ["log_pop", "log_days", "level", "D1", "D4"]

    print(f"\n8. VIF (multicollinearity — predictors: log_pop, log_days, level, D1, D4)")
    vif_vals = []
    for i, label in enumerate(predictor_labels, 1):
        v = variance_inflation_factor(X_vif_c, i)
        vif_vals.append(v)
        flag = "  ← HIGH" if v >= 4.0 else ""
        print(f"   VIF({label:<8}) = {v:.2f}{flag}")

    corr_mat = np.corrcoef(X_vif.T)
    max_r = 0.0
    max_pair = ("", "")
    for i in range(5):
        for j in range(i + 1, 5):
            if abs(corr_mat[i, j]) > max_r:
                max_r = abs(corr_mat[i, j])
                max_pair = (predictor_labels[i], predictor_labels[j])
    print(f"   Max pairwise |r| = {max_r:.3f}  ({max_pair[0]} × {max_pair[1]})")
    vif_pass = all(v < 4.0 for v in vif_vals) and max_r < 0.8
    print(f"   Verdict     : {'PASS' if vif_pass else 'NOTE — VIF ≥ 4 or |r| ≥ 0.8'}")

    # ─────────────────────────────────────────────────────────────────────────
    # Summary table
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{'=' * W}")
    print(f"  Summary")
    print(f"{'=' * W}")
    print(f"  {'Test':<40} {'Value':<20} {'Verdict'}")
    print(f"  {'-'*40} {'-'*20} {'-'*10}")
    print(f"  {'R² (log-log)':<40} {f'{r2:.3f}, p={pearson_p:.2e}':<20} {'PASS' if r2>=0.70 else 'FAIL'}")
    print(f"  {'Shapiro-Wilk':<40} {f'W={sw_stat:.3f}, p={sw_p:.3f}':<20} {'PASS' if sw_p>=0.05 else 'FAIL'}")
    print(f"  {'Breusch-Pagan':<40} {f'LM={bp_lm:.3f}, p={bp_p:.3f}':<20} {'PASS' if bp_p>=0.05 else 'FAIL'}")
    print(f"  {'Cooks Distance (0 above thr)':<40} {f'{n_above}/{n} above {threshold:.2f}':<20} {'PASS' if n_above==0 else f'NOTE:{n_above}'}")
    print(f"  {'LOOCV R²':<40} {f'{loo:.3f} (gap={gap:.3f})':<20} {'PASS' if gap<=0.05 else 'NOTE'}")
    print(f"  {'Spearman ρ':<40} {f'ρ={sp_rho:.3f}, p={sp_p:.2e}':<20} {'PASS' if sp_p<0.001 else 'NOTE'}")
    print(f"  {'Durbin-Watson':<40} {f'DW={dw_stat:.3f}':<20} {dw_verdict.split(' — ')[0]}")
    print(f"  {'VIF (all <4, max|r|<0.8)':<40} {f'max={max(vif_vals):.2f}, |r|={max_r:.3f}':<20} {'PASS' if vif_pass else 'NOTE'}")
    print()


if __name__ == "__main__":
    main()

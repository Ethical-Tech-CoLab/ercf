#!/usr/bin/env python3
"""
ERCF Mortality Model — Full Calibration via Differential Evolution
Two variants on 16 in-scope cases:

  Variant A: no infra_denial for any case
             5 parameters: [L0, L1, L2, L3, L4]

  Variant B: infra_denial for Mariupol, Vukovar, Huambo only, alpha optimised
             6 parameters: [L0, L1, L2, L3, L4, alpha]

Constraints (both variants):
  L0 < L1 < L2  (monotone baseline)
  L3, L4 unconstrained w.r.t. each other (empirical dataset may favour L3>L4)
  All rates > 0, alpha > 0
"""
import numpy as np
from scipy.optimize import differential_evolution
from scipy import stats
from scipy.stats import linregress
import sys

sys.path.insert(0, '/Users/yagorocha/evacuation-risk-tool')
from historical_data import HISTORICAL_CASES
import calculators
from calculators import INFRA_DENIAL_D1_THRESHOLD, INFRA_DENIAL_D4_THRESHOLD

# Cases where infra_denial is applied in Variant B
INFRA_B_NAMES = {'Mariupol, Ukraine', 'Aleppo, Syria',
                 'Siege of Vukovar, Croatia',
                 'Siege of Huambo — Guerra dos 55 Dias, Angola',
                 'Eastern Ghouta, Syria (2018)'}

# ── 1. Filter and prepare 16 in-scope cases ───────────────────────────────────

def _prepare(c):
    cal = c.get('model_calibration', {})
    v2p = cal.get('v2_parameters', {})
    pop = c['population_at_risk']
    if 'remaining_pct' in v2p:
        remaining_pct = v2p['remaining_pct']
    else:
        remaining_count = c.get('remaining_count', pop)
        remaining_pct = remaining_count / pop if pop > 0 else 1.0
    ct = c.get('exposure_type', 'auto')
    conflict_type = ct if ct in ('urban_siege', 'enclave', 'city_conflict', 'regional') else 'auto'
    return {
        'name':          c['name'],
        'population':    pop,
        'days':          c['duration_days'],
        'risk_level':    c['risk_level'],
        'dims':          c['risk_indicators'],
        'remaining_pct': remaining_pct,
        'conflict_type': conflict_type,
        'infra_flag_any': cal.get('infra_denial_flag', False),
        'infra_flag_b':   c['name'] in INFRA_B_NAMES and cal.get('infra_denial_flag', False),
        'recorded':      cal.get('recorded_deaths', 0),
    }

cases_raw = [
    c for c in HISTORICAL_CASES
    if not c.get('model_calibration', {}).get('out_of_scope', False)
]
cases = [_prepare(c) for c in cases_raw]
cases = [c for c in cases if c['recorded'] > 0]
print(f'In-scope cases: {len(cases)}')
print(f'Infra-denial cases (Variant B): {[c["name"] for c in cases if c["infra_flag_b"]]}')
print()

# ── 2. Helpers ────────────────────────────────────────────────────────────────

def _id_mult(alpha, dims):
    """Infra-denial multiplier with custom alpha."""
    d1 = float(dims.get('d1_kinetic', dims.get('d1', 3.0)))
    d4 = float(dims.get('d4_logistics', dims.get('d4', 3.0)))
    if d1 >= INFRA_DENIAL_D1_THRESHOLD and d4 >= INFRA_DENIAL_D4_THRESHOLD:
        return 1.0 + alpha * (d1 - 3.0) * (d4 - 3.0)
    return 1.0


def run_model(case, base_rates, alpha=None):
    """
    Run calculate_staying_costs with custom base rates.
    alpha=None → no infra_denial; alpha=float → apply for infra_flag_b cases.
    """
    orig = calculators.DEATH_RATE_10K_EMPIRICAL[:]
    calculators.DEATH_RATE_10K_EMPIRICAL[:] = list(base_rates)
    try:
        result = calculators.calculate_staying_costs(
            population=case['population'],
            risk_level=case['risk_level'],
            days=case['days'],
            dims=case['dims'],
            remaining_pct=case['remaining_pct'],
            conflict_type=case['conflict_type'],
        )
        deaths = result['totals']['deaths']
        if alpha is not None and case['infra_flag_b']:
            deaths *= _id_mult(alpha, case['dims'])
        return deaths
    finally:
        calculators.DEATH_RATE_10K_EMPIRICAL[:] = orig


def msle(params, use_infra_b=False):
    """Mean squared log error loss function."""
    rates = params[:5]
    alpha = float(params[5]) if use_infra_b else None
    if any(r <= 0 for r in rates):
        return 1e10
    if not (rates[0] < rates[1] < rates[2]):
        return 1e10
    if use_infra_b and alpha <= 0:
        return 1e10
    errors = []
    for case in cases:
        model = run_model(case, rates, alpha)
        if model <= 0:
            continue
        errors.append((np.log(model) - np.log(case['recorded'])) ** 2)
    return np.mean(errors) if errors else 1e10


# ── 3. Metrics ────────────────────────────────────────────────────────────────

def compute_metrics(base_rates, alpha, label):
    """Print results table and return (r2, loocv_r2, within_2x)."""
    print(f'\n{"─"*72}')
    print(f'  {label}')
    print(f'{"─"*72}')
    print(f'  Rates: L0={base_rates[0]:.3f}  L1={base_rates[1]:.3f}  L2={base_rates[2]:.3f}'
          f'  L3={base_rates[3]:.3f}  L4={base_rates[4]:.3f}')
    if alpha is not None:
        print(f'  Alpha: {alpha:.4f}')
    print(f'  Order: L0<L1<L2={"✓" if base_rates[0]<base_rates[1]<base_rates[2] else "✗"}'
          f'  L3<L4={"✓" if base_rates[3]<base_rates[4] else "✗ (L3>L4)"}'
          f'  L3>L2={"✓" if base_rates[3]>base_rates[2] else "✗"}')
    print()

    col = 42
    print(f'  {"Case":<{col}} {"Rec":>8} {"Model":>10} {"Ratio":>8}  W2x  Lvl')
    print('  ' + '─' * 74)

    rec_log, mod_log = [], []
    within_2x = 0
    for case in cases:
        model = run_model(case, base_rates, alpha)
        ratio = model / case['recorded']
        w2x   = 0.5 <= ratio <= 2.0
        if w2x:
            within_2x += 1
        flag  = '✓' if w2x else '✗'
        id_tag = '[ID]' if (alpha is not None and case['infra_flag_b']) else '    '
        print(f'  {case["name"]:<{col-5}}{id_tag}  {case["recorded"]:>8,}'
              f' {model:>10,.0f} {ratio:>8.2f}×  {flag}   L{case["risk_level"]}')
        rec_log.append(np.log(case['recorded']))
        mod_log.append(np.log(model))

    n = len(cases)
    print('  ' + '─' * 74)

    corr, pval = stats.pearsonr(rec_log, mod_log)
    r2 = corr ** 2

    loo_preds = []
    for i in range(n):
        tx = [rec_log[j] for j in range(n) if j != i]
        ty = [mod_log[j]  for j in range(n) if j != i]
        sl, ic, *_ = linregress(tx, ty)
        loo_preds.append(sl * rec_log[i] + ic)
    ss_res = sum((mod_log[i] - loo_preds[i]) ** 2 for i in range(n))
    ss_tot = sum((mod_log[i] - np.mean(mod_log)) ** 2 for i in range(n))
    loocv  = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')

    print(f'\n  Within 2×    : {within_2x}/{n} ({100*within_2x/n:.0f}%)')
    print(f'  R² log-log   : {r2:.3f}  (p={pval:.5f})')
    print(f'  LOOCV R²     : {loocv:.3f}')
    print(f'  LOOCV gap    : {r2 - loocv:.3f}')

    # Per-level
    print(f'\n  Per-level:')
    for lvl in [3, 4]:
        idx = [i for i, c in enumerate(cases) if c['risk_level'] == lvl]
        recs = [rec_log[i] for i in idx]; mods = [mod_log[i] for i in idx]
        n_l  = len(idx)
        w2x_l = sum(1 for i in idx if 0.5 <= np.exp(mod_log[i])/cases[i]['recorded'] <= 2.0)
        if n_l >= 2:
            c_l, _ = stats.pearsonr(recs, mods); r2_l = c_l**2
            r2_s = f'{r2_l:.3f}'
        else:
            r2_s = '  n/a'
        print(f'    L{lvl}  n={n_l}  within-2×={w2x_l}/{n_l}  R²={r2_s}')

    return r2, loocv, within_2x


# ── 4. Optimise Variant A (no infra_denial) ───────────────────────────────────

import argparse as _ap
_parser = _ap.ArgumentParser(add_help=False)
_parser.add_argument('--variant', choices=['a','b','both'], default='both')
_args, _ = _parser.parse_known_args()

bounds_a = [
    (0.1, 2.0),   # L0
    (0.2, 3.0),   # L1
    (0.5, 5.0),   # L2
    (1.0, 15.0),  # L3
    (1.0, 15.0),  # L4
]

res_a = None
opt_a = None
if _args.variant in ('a', 'both'):
    print('='*72)
    print('VARIANT A — optimising [L0..L4], no infra_denial (popsize=20, maxiter=500)')
    print('='*72)
    res_a = differential_evolution(
        lambda p: msle(p, use_infra_b=False),
        bounds_a, seed=42, maxiter=500, tol=1e-6, workers=1, popsize=20,
    )
    print(f'Done: {res_a.message}  MSLE={res_a.fun:.4f}')
    opt_a = list(res_a.x)
    compute_metrics(opt_a, alpha=None, label='VARIANT A — optimal rates, no infra_denial')

# ── 5. Optimise Variant B (infra_denial for 3 cases, alpha as 6th param) ──────

bounds_b = bounds_a + [(0.1, 3.0)]   # alpha

if _args.variant in ('b', 'both'):
 pass  # always run B
print('\n' + '='*72)
print('VARIANT B — optimising [L0..L4, alpha], infra_denial for: %s' % ', '.join(sorted(INFRA_B_NAMES)))
print('='*72)
res_b = differential_evolution(
    lambda p: msle(p, use_infra_b=True),
    bounds_b, seed=42, maxiter=500, tol=1e-6, workers=1, popsize=20,
)
print(f'Done: {res_b.message}  MSLE={res_b.fun:.4f}')
opt_b = list(res_b.x[:5])
alpha_b = float(res_b.x[5])
compute_metrics(opt_b, alpha=alpha_b, label='VARIANT B — optimal rates + alpha, infra_denial for 3 cases')

# ── 6. Summary comparison ─────────────────────────────────────────────────────

print('\n' + '='*72)
print('SUMMARY')
print('='*72)
current = [0.3, 0.5, 0.8, 6.0, 4.0]
loss_cur_a = msle(current + [0.0], use_infra_b=False)
loss_cur_b = msle(current + [calculators.INFRA_DENIAL_ALPHA], use_infra_b=True)
print(f'\nCurrent rates [0.3, 0.5, 0.8, 6.0, 4.0]:')
print(f'  MSLE (no infra_denial) : {loss_cur_a:.4f}')
print(f'  MSLE (with infra α={calculators.INFRA_DENIAL_ALPHA}) : {loss_cur_b:.4f}')
if res_a is not None:
    print(f'Variant A  MSLE={res_a.fun:.4f}  rates={[round(x,2) for x in opt_a]}')
    print(f'  Improvement vs current (no infra): {(loss_cur_a - res_a.fun)/loss_cur_a*100:.1f}%')
print(f'Variant B  MSLE={res_b.fun:.4f}  rates={[round(x,2) for x in opt_b]}  α={alpha_b:.4f}')
print(f'  Improvement vs current (with infra): {(loss_cur_b - res_b.fun)/loss_cur_b*100:.1f}%')

print(f'\n# Ready to paste into calculators.py (pending confirmation):')
if res_a is not None:
    print(f'# Variant A:')
    print(f'DEATH_RATE_10K_EMPIRICAL = [{opt_a[0]:.2f}, {opt_a[1]:.2f}, {opt_a[2]:.2f}, {opt_a[3]:.2f}, {opt_a[4]:.2f}]')
print(f'# Variant B:')
print(f'DEATH_RATE_10K_EMPIRICAL = [{opt_b[0]:.2f}, {opt_b[1]:.2f}, {opt_b[2]:.2f}, {opt_b[3]:.2f}, {opt_b[4]:.2f}]')
print(f'INFRA_DENIAL_ALPHA = {alpha_b:.4f}')

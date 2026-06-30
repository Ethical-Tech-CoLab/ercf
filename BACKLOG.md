# ERCF — Product Backlog

## Priority 1 — High Impact, Feasible

- **Supply price volatility** — fuel, food, and medical supply costs as configurable variables (user-adjustable per country context). Teresa Cantero suggestion.
- **Data freshness indicators** — show in UI when ACAPS/INFORM and UCDP were last updated; flag stale data (>30 days for ACAPS, >1 year for UCDP).
- **Mass atrocity / genocide indicator** — structured UI flag for OOS cases that are genocide or deliberate massacre (currently only in `out_of_scope_reason` text). Teresa Cantero suggestion.
- **Recalibration with new cases** — pipeline to add new cases to the corpus and re-run `full_calibration.py` when the historical dataset expands.

## Priority 2 — Medium Impact

- **Dynamic D-scores** — model conflict escalation over time (D1/D6 drift); currently static snapshot.
- **Multi-corridor scenario** — compare two evacuation routes side-by-side (different distance, terrain, D4).
- **Export to PDF/Word** — generate funding appeal template with scenario summary, cost breakdown, and historical comparisons.
- **Mobile responsive improvements** — current layout optimised for desktop; radar and charts need responsive sizing for tablets.
- **Walking evacuation integration** — walking mode currently calls a separate endpoint but is not fully integrated into the decision analysis break-even.

## Priority 3 — Research / Academic

- **Expert panel validation of D1–D7 weights** — current weights are calibration-derived; no peer review yet.
- **L4 structural limitation resolution** — L4 cannot simultaneously capture high-mortality urban sieges (Aleppo: 31,000 deaths) and large-enclave precision operations (Gaza Cast Lead: 965 deaths). Requires either sub-levels or a separate model branch.
- **Confidence intervals on cost estimates** — current outputs are point estimates; uncertainty bands would improve funding appeal usefulness.
- **Integration with OCHA FTS** — link evacuation cost estimates to the OCHA Financial Tracking Service for real-operation comparisons.
- **LOOCV within-2× computation** — not recomputed for v7 (only R² LOOCV available); requires implementing leave-one-out within-2× rate.

## Known Technical Debt

| Item | Status | Impact |
|------|--------|--------|
| LOOCV within-2× not recomputed for v7 | Open | Low — R² LOOCV is the primary metric |
| GeoNames population data is pre-conflict | By design | Medium — users should adjust for displacement manually |
| Access multiplier L4 (×4.0) unvalidated | Open | Low — conservative estimate, no published source >4× |
| `ercf_auditoria.zip` (75 MB) in git history | Open | Low — GitHub warns, doesn't block; `.gitignore` fix pending |
| `context_ai.py` Claude API — prompt not cached | Open | Low — single-call endpoint, not high-frequency |
| `weather_data.py` seasonal factors not validated | Open | Low — used as modifier, not primary output |

## Data Update Frequency

| Dataset | Update cycle | Current version | How to update |
|---------|-------------|-----------------|---------------|
| UCDP GED | Annual (typically March/April) | v26.1 (data through 2025) | Replace `data/ged261.csv`; update endpoint version string |
| ACAPS/INFORM | Monthly | Live via API | Automatic (API client with session cache) |
| GeoNames | Continuous (crowdsourced) | Live via API | Automatic (`/api/city-population`) |
| Historical cases | Manual | 31 cases (1991–2024) | Edit `historical_data.py`; re-run `calibrate.py` |

## Out of Scope (deliberately excluded)

- Real-time conflict monitoring or event streaming
- Individual-level civilian tracking or identification
- Legal or operational advice of any kind
- Mortality forecasting beyond the 0–90 day calibration window
- Non-conflict natural disaster scenarios (different cost and mortality structures)
- Conflict forecasting or escalation prediction

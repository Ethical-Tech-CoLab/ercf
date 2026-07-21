# ERCF — Evacuation Risk and Cost Framework

**[Live site](https://ercf-production.up.railway.app/)** ·
**[Research report](ERCF-Paper.md)** (plain-language, non-technical)

**Version:** v7.2

A decision-support tool for estimating the human and financial cost of civilian evacuation in armed conflict. Developed as part of doctoral research in International Humanitarian Law and civilian protection at NYU.

**Philosophy:** The ERCF presents data to support decisions — it does not prescribe actions. Labels are descriptive, not imperative.

> ⚖️ **Ethical Notice:** This tool estimates the operational cost of humanitarian evacuation logistics — to support planning and resource mobilisation. It does not place a monetary value on human life. All cost figures represent logistics estimates only.

## Live Demo

**[https://ercf-production.up.railway.app](https://ercf-production.up.railway.app)**

## Key Features

- **Scenario Builder** — 7-dimension risk scoring (D1 Kinetic Threat, D2 Mobility, D3 Authorization, D4 Logistics, D5 Destination, D6 Urgency, D7 Information)
- **Cost Estimation** — evacuation resources (vehicles, personnel, fuel, supplies) + in-situ assistance for population remaining in zone
- **Evacuation Decision Analysis** — break-even chart: compares one-time evacuation cost vs cumulative daily in-zone assistance cost; identifies the day after which evacuation becomes the lower-cost option
- **Transport Consistency Warnings** — alerts when selected transport mode is inconsistent with D-scores (e.g. ground transport + D4≥4.0, walking + large population, air + D3≤2.0)
- **Demographic Suggestions** — suggests vulnerable population % based on UNICEF/UN DESA 2023 data for 18 conflict-affected countries
- **Historical Cases** — 31 documented cases (1991–2024), 16 used for calibration
- **Compare on Radar** — overlay current scenario against historical case profiles
- **Cost Benchmarking** — real evacuation operations (Kosovo 1999, Libya 2011, Lebanon 2006) for contextualisation
- **Map View** — country-level conflict severity (ACAPS/INFORM data)
- **UCDP GED v26.1** — integrated conflict event validation

## Mortality Model — v7 Calibration

The mortality model is **indicative, not predictive**. Financial cost estimates are substantially more reliable.

| Metric | Value |
|--------|-------|
| Calibration cases | 16 of 31 (15 out-of-scope) |
| Within 2× | 7/16 (44%) |
| R² (log-log) | 0.855 |
| LOOCV R² | 0.807 |
| LOOCV gap | 0.048 |
| L3 R² | 0.958 |
| L4 R² | 0.624 |
| Base rates [L0–L4] | [0.777, 0.964, 3.625, 1.805, 1.000] /10K/day |
| Infra-denial α | 0.4251 (4 cases: Mariupol, Aleppo, Vukovar, Huambo) |

**Known structural limitation:** L4 cannot simultaneously capture high-mortality urban sieges (Aleppo: 31,000 deaths) and large-enclave precision operations (Gaza Cast Lead: 965 deaths). Two challenge cases (Eastern Ghouta 2018, Pillar of Defense 2012) document this boundary explicitly. See Model Limitations panel in the app.

Calibration is fully reproducible: `python3 calibration/calibrate.py`

**Statistical Validation (v7, N=16, June 2026)** — full re-validation via `calibration/validate_v7.py`:

| Test | Result | Verdict |
|------|--------|---------|
| R² (log-log) | 0.855, p=3.01e-07 | PASS |
| Shapiro-Wilk | W=0.974, p=0.902 | PASS |
| Breusch-Pagan | LM=0.316, p=0.574 | PASS |
| Cook's Distance | 1/16 above threshold — Aleppo D=0.613 | NOTE |
| LOOCV R² | 0.807 (gap=0.048) | PASS |
| Spearman ρ | ρ=0.845, p=3.83e-05 | PASS |
| Durbin-Watson | DW=1.413 | DOCUMENTED |
| VIF | max=3.90 (D1), max\|r\|=0.758 (D1×D4) | PASS |

## Cost Model — Key Parameters

| Parameter | Value | Source | Status |
|-----------|-------|--------|--------|
| Water per person/day | 20 L | UNHCR WASH Manual | Validated |
| Food per person/day | 0.45 kg | Sphere 2018 | Validated |
| Tent occupancy | 5 persons | Sphere 2018 | Validated |
| Medical staff ratio | 1:250 | Sphere 2018 | Validated |
| UNHAS air rate | $2.08/pax-km | WFP Executive Board 2025 | Validated |
| WFP baseline cost | $0.42/person/day | WFP APR 2023 | Validated |
| Medical staff daily | $200/day | MSF 2024 (all-inclusive) | Estimated |
| Security personnel | $300/day | PSC mid-market | Estimated |
| Ambulance ratio | 1:150 vulnerable | Field practice (PMC10068156) | Estimated |
| Medical kit | $21/kit (100 persons) | WHO IEHK (PMC5321368, 2017) | Estimated |
| Access multiplier L4 | ×4.0 | No published source >4× | Unvalidated |

## Cost Validation — Real Operations

ERCF models the immediate field evacuation operation only (~$134/person at L2, 50 km, ground). Real operations include international transport, reception, and multi-week hosting — substantially increasing per-person cost.

| Operation | Year | Evacuees | Cost/Person | Mode | Source | Status |
|-----------|------|----------|-------------|------|--------|--------|
| Kosovo HEP | 1999 | 60,549 | $562 | Air (international, 20 countries) | IOM/UNHCR HEP, ReliefWeb | Validated |
| Libya | 2011 | ~50,000 | ~$984 | Air + maritime | IOM 7-Month Report 2011 | Estimated (appeal budget) |
| Lebanon → Canada | 2006 | ~15,000 | ~$4,500–5,700 | Naval + military air | Canadian Senate Committee, May 2007 | Estimated (incl. military assets) |

## Historical Corpus — 31 Cases

| Status | Count | Examples |
|--------|-------|---------|
| In-scope (calibration) | 16 | Mariupol, Mosul, Aleppo, Gaza 2023 |
| Out-of-scope (structural) | 13 | Srebrenica, Sarajevo, Kosovo, CAR, Sudan, Raqqa |
| Challenge cases | 2 | Eastern Ghouta 2018, Pillar of Defense 2012 |

Badge legend in Historical Cases tab: **OOS** (grey) = out-of-scope, excluded from calibration. **CHAL** (orange) = challenge/boundary case (Eastern Ghouta 2018, Pillar of Defense 2012) — retained in corpus but structurally outside model domain.

## Decision Support Features

- **Break-even Analysis** — compares two options: (A) evacuate now + daily assistance for remaining population vs (B) no evacuation with full population assistance. Break-even = `evacCost / (dailyCostB - dailyCostA)`. Daily costs derived from the Assistance Cost module (access overhead, terrain, extraction, medical). Special case: 0% remaining shows evacuate-all vs no-evacuation comparison using `BASE_DAILY[level] × population` as the no-evacuation baseline.
- **Transport Warnings** — alerts for five inconsistency patterns: Ground + D4≥4.0 (logistics breakdown), Ground + D1≥4.5 (kinetic exposure), Walking + pop>5,000 (scale infeasibility), Walking + D2≥3.5 (mobility constraints), Air + D3≤2.0 (airspace authorization gap).
- **Demographic Context** — calls `/api/demographics/{country}` to suggest vulnerable population % from 18-country dataset (UNICEF/UN DESA 2023). Suggestion is always advisory — user confirms or dismisses.
- **Historical Comparison** — radar overlay of D1–D7 scores for current scenario vs any of 31 documented historical cases. Highlights which cases are structurally most similar.
- **Cost Comparison Table in Compare on Radar** — side-by-side table (population, evac cost, cost/evacuee, duration, deaths) for current scenario vs selected historical case.

## Tech Stack

- **Backend:** FastAPI + SQLite + Python
- **Frontend:** HTML/JS + Leaflet + Chart.js
- **Data:** UCDP GED v26.1 API + CSV, ACAPS INFORM Severity Index
- **Demographics:** `demographic_data.py` — 18-country dataset, UNICEF/UN DESA 2023
- **Calibration:** `calibration/calibrate.py` + `calibration/full_calibration.py` + `calibration/validate_v7.py`

## Installation

```bash
git clone https://github.com/yagorocha-web/ercf
cd ercf
pip install -r requirements.txt
pip install numpy scipy statsmodels  # required for calibration scripts
cp .env.example .env  # add UCDP_API_TOKEN
uvicorn main:app --reload
```

Access at `http://localhost:8000`

## Calibration Scripts

```bash
# Run v7 model against 16 in-scope cases — outputs R², LOOCV R², within-2× table
python3 calibration/calibrate.py
python3 calibration/calibrate.py --by-level     # per-level (L3/L4) breakdown
python3 calibration/calibrate.py --no-infra-denial  # without infra-denial multiplier

# Optimise base rates and α via differential_evolution (requires scipy)
# Variant A: no infra-denial  |  Variant B: infra-denial for 4 cases + α as 6th parameter
python3 calibration/full_calibration.py --variant b

# Full statistical re-validation: Shapiro-Wilk, Breusch-Pagan, Cook's D, Spearman, DW, VIF
python3 calibration/validate_v7.py
```

The v7 parameters were derived by running Variant B against 16 in-scope cases:
- Base rates: `[0.777, 0.964, 3.625, 1.805, 1.000]` /10K/day
- Infra-denial α: `0.4251` (jointly optimised with base rates)
- MSLE: 0.8051 (70.8% reduction vs prior v6 rates)

## Academic Context

Developed by Yago Rocha in collaboration with the Microsoft Ethical Tech CoLab. Presented to Teresa Cantero, PhD Researcher, as part of research on IHL civilian protection and evacuation decision-support frameworks.

**This tool does not constitute operational advice.** All estimates require validation against country-specific intelligence and field assessment before any operational application.

## License

MIT

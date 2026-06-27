# ERCF — Evacuation Risk and Cost Framework

A decision-support tool for estimating the human and financial cost of civilian evacuation in armed conflict. Developed as part of doctoral research in International Humanitarian Law and civilian protection at NYU.

**Philosophy:** The ERCF presents data to support decisions — it does not prescribe actions. Labels are descriptive, not imperative.

## Live Demo

Hosted locally — see Installation below.

## Key Features

- **Scenario Builder** — 7-dimension risk scoring (D1 Kinetic Threat, D2 Mobility, D3 Authorization, D4 Logistics, D5 Destination, D6 Urgency, D7 Information)
- **Cost Estimation** — evacuation resources (vehicles, personnel, fuel, supplies) + in-situ assistance for population remaining in zone
- **Historical Cases** — 31 documented cases (1945–2024), 16 used for calibration
- **Compare on Radar** — overlay current scenario against historical case profiles
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
| L3 R² | 0.958 |
| L4 R² | 0.624 |

**Known structural limitation:** L4 cannot simultaneously capture high-mortality urban sieges (Aleppo: 31,000 deaths) and large-enclave precision operations (Gaza Cast Lead: 965 deaths). See Model Limitations panel in the app.

Calibration is fully reproducible: `python3 calibration/calibrate.py`

## Cost Model — Key Parameters

| Parameter | Value | Source | Status |
|-----------|-------|--------|--------|
| Water per person/day | 20L | UNHCR WASH Manual | Validated |
| Food per person/day | 0.45 kg | Sphere 2018 | Validated |
| Tent occupancy | 5 persons | Sphere 2018 | Validated |
| Medical staff ratio | 1:250 | Sphere 2018 | Validated |
| UNHAS air rate | $2.08/pax-km | WFP Executive Board 2025 | Validated |
| WFP baseline cost | $0.42/person/day | WFP APR 2023 | Validated |
| Medical staff daily | $200/day | MSF 2024 (all-inclusive) | Estimated |
| Security personnel | $300/day | PSC mid-market | Estimated |
| Access multiplier L4 | ×4.0 | No published source >4× | Unvalidated |

## Historical Corpus — 31 Cases

| Status | Count | Examples |
|--------|-------|---------|
| In-scope (calibration) | 16 | Mariupol, Mosul, Aleppo, Gaza 2023 |
| Out-of-scope (structural) | 13 | Srebrenica, Sarajevo, Kosovo, Sudan |
| Challenge cases | 2 | Eastern Ghouta 2018, Pillar of Defense 2012 |

## Tech Stack

- **Backend:** FastAPI + SQLite + Python
- **Frontend:** HTML/JS + Leaflet + Chart.js
- **Data:** UCDP GED v26.1 API + CSV, ACAPS INFORM Severity Index
- **Calibration:** `calibration/calibrate.py` + `calibration/full_calibration.py`

## Installation

```bash
git clone https://github.com/yagorocha-web/ercf
cd ercf
pip install -r requirements.txt
cp .env.example .env  # add UCDP_API_TOKEN
uvicorn main:app --reload
```

Access at `http://localhost:8000`

## Academic Context

Developed independently by Yago Rocha as part of doctoral research at NYU under supervision of Teresa Cantero. Focuses on IHL civilian protection and evacuation decision-support frameworks.

**This tool does not constitute operational advice.** All estimates require validation against country-specific intelligence and field assessment before any operational application.

## License

MIT

# ERCF — Concept Document

## Problem Statement

When a humanitarian organisation or government authority faces a civilian evacuation decision in an active conflict zone, they typically lack rapid, structured access to three critical estimates:

1. **What will it cost to evacuate?** — vehicles, fuel, personnel, supplies, medical support
2. **What will it cost to keep civilians in place?** — daily in-zone assistance under conflict conditions
3. **At what point does staying become more expensive than evacuating?** — the operational break-even

These estimates exist in operational manuals and case studies, but no publicly available tool integrates them with a historical calibration dataset and an IHL-grounded risk framework. The ERCF fills that gap.

## Ethical Framework

The ERCF estimates the **operational cost of evacuation logistics** — vehicles, personnel, fuel, supplies, and in-zone assistance. It does not place a monetary value on human life.

The break-even analysis compares the cost of evacuation operations against the cost of in-zone humanitarian assistance. It is designed to help organisations answer: "At what point does the cost of maintaining in-zone operations exceed the cost of evacuation?" — a resource planning question, not a valuation of human welfare.

All mortality estimates are contextual indicators to support operational planning. They are not predictions, not forecasts, and not measures of acceptable loss. The decision to evacuate civilians is a matter of IHL obligations and humanitarian judgment — not financial optimisation.

**Vulnerable population retention assumption:** the Assistance Cost model assumes vulnerable individuals (elderly, disabled) are ~2× less likely to evacuate than the general population, based on documented evacuation/transportation barriers (ref: AARP/FEMA Post-Katrina Look Back 2006; WHO Disability, Disaster Risk Reduction and Emergency Preparedness 2005). This shapes both the estimated composition of the population remaining in-zone and the added per-capita assistance cost for that group. It is an operational planning assumption, not a normative judgment about whose evacuation matters more — the tool surfaces this composition shift so planners can account for it, not to justify deprioritising anyone's evacuation.

This tool is intended for:
- Humanitarian planners estimating resource requirements
- Organisations preparing funding appeals
- Researchers studying civilian protection frameworks
- Decision-makers seeking cost transparency before crises escalate

This tool is not intended to:
- Determine whether evacuation is "worth it"
- Rank the value of civilian lives
- Replace field assessment or expert judgment
- Constitute operational or legal advice

## Core Philosophy

- **Decision support, not prescription** — the tool presents estimates; the decision belongs to the humanitarian actor
- **Descriptive labels, not imperative recommendations** — "Level 4" describes a risk profile, it does not order an action
- **Financial cost as primary output** — the most operationally useful and empirically grounded output
- **Mortality as contextual support only** — model estimates of cumulative deaths and injuries provide scale context, not targets or thresholds

## Target Users

| User | Use case |
|------|----------|
| Humanitarian programme officers | Rapid cost estimation for funding proposals |
| Emergency coordinators | Comparative scenario analysis before crisis escalation |
| Donors and fund managers | Cost benchmarking against documented operations |
| IHL researchers | Historical case comparison and methodology transparency |
| Government civil protection | Preparedness planning and resource pre-positioning |

## What ERCF Is

- **Evacuation cost calculator** — ground transport, personnel, fuel, food, water, shelter, medical, communications, contingency
- **In-zone assistance calculator** — daily cost with conflict access overhead, terrain multipliers, supply loss rates
- **Break-even analysis** — day at which cumulative in-zone assistance exceeds one-time evacuation cost
- **Historical context tool** — 31 documented cases (1991–2024), radar profile overlay, cost benchmarks
- **Decision analysis framework** — IHL-grounded 7-dimension risk score with NATO equivalents

## What ERCF Is Not

- Not a real-time conflict monitoring system
- Not a forecasting model (no time-series projection)
- Not a substitute for field assessment, OCHA situation reports, or expert judgment
- Not operational or legal advice
- Not a mass casualty prediction tool

## Key Design Decisions

### Why 7 dimensions (D1–D7)?

The 7-dimension framework (Kinetic Threat, Vulnerability, Political Authorization, Logistics, Destination Quality, Urgency, Information Quality) was designed to capture the factors that field coordinators consistently cite when assessing evacuation feasibility — without requiring real-time data feeds or proprietary intelligence. Each dimension is scored 1–5; thresholds and weights are derived from calibration against 31 historical cases.

### Why historical calibration instead of pure modelling?

Pure analytical models for conflict mortality are structurally unreliable without empirical grounding. The ERCF uses 16 in-scope cases for calibration (R²=0.855, LOOCV R²=0.807) and 15 out-of-scope cases to document model boundaries. Known failure modes (genocide, large-enclave precision operations, duration >90 days) are explicitly excluded and flagged.

### Why the break-even analysis?

Fund mobilisation decisions frequently involve a comparison between evacuation costs and the cost of maintaining in-zone operations indefinitely. Making this comparison explicit — with real cost components — reduces reliance on intuition and supports evidence-based funding requests.

### Why separate evacuation cost from mortality?

Cost and mortality are independent estimates. Cost estimates are substantially more reliable (validated against real operations: Kosovo 1999, Libya 2011, Lebanon 2006). Mortality estimates are calibrated but uncertain. Separating them avoids conflating financial planning with casualty prediction.

## Limitations by Design

| Limitation | Reason |
|-----------|--------|
| Static D-scores | No real-time data feed; scores represent a snapshot |
| 0–90 day planning window | Calibration corpus is bounded; saturation formula applied beyond 90 days |
| Ground transport primary | Air and walking modes are supplementary; cost models are less validated |
| No escalation modelling | D-scores are fixed inputs; dynamic conflict evolution is not modelled |
| Single corridor | Multi-route comparison not yet implemented |
| Pre-conflict population data | GeoNames population figures do not reflect displacement |

## Academic Context

Developed by Yago Rocha in collaboration with the **Microsoft Ethical Tech CoLab**. Presented to Teresa Cantero, PhD Researcher, as part of research on IHL civilian protection and evacuation decision-support frameworks.

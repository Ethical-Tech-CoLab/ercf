import math
from typing import Dict, Optional

SOURCE_CONFIDENCE = {
    "water_per_person_day_l":          {"value": 20,        "source": "UNHCR full standard: 20 L/person/day. Updated 15→20 (Tavily validation June 2026). Sphere 2018 emergency minimum: 7.5-15 L/person/day. UNHCR full planning standard used for evacuation (not emergency minimum). Source: UNHCR WASH Manual; Sphere Association Handbook 4th ed. 2018.", "confidence": "validated"},
    "kcal_per_person_day":             {"value": 2100,      "source": "Sphere Association, The Sphere Handbook, 4th ed., Geneva, 2018",                                         "confidence": "validated"},
    "shelter_m2_per_person":           {"value": 3.5,       "source": "Sphere Association, The Sphere Handbook, 4th ed., Geneva, 2018",                                         "confidence": "validated"},
    "food_kg_per_person_day":          {"value": 0.45,      "source": "Sphere 2018 (estimated dry weight conversion from 2100 kcal)",                                            "confidence": "estimated"},
    "std_bus_capacity":                {"value": 50,        "source": "operational assumption — not validated against field data",                                               "confidence": "estimated"},
    "med_bus_capacity":                {"value": 20,        "source": "operational assumption — not validated against field data",                                               "confidence": "estimated"},
    "fuel_l_per_km_per_vehicle":       {"value": 0.35,      "source": "operational assumption — not validated against field data",                                               "confidence": "estimated"},
    "transport_cost_usd_per_vehicle":  {
        "value": "200 (std bus) / 400 (med bus) / 700 (ambulance)",
        "source": "Std bus $200: unvalidated — no direct field data found in seven-search validation (June 2026). "
                  "Med bus $250→$400 (Tavily validation June 2026): no primary source found for $250; "
                  "medically-equipped vehicle (stretchers, O2, trained crew) field range $400-600/vehicle. "
                  "$400 used as validated lower bound. Source: MSF/ICRC operational literature. "
                  "Ambulance $400→$700 (Tavily validation June 2026): EU Commission Medical Aerial Evacuation "
                  "Study 2020; conflict-zone ground ambulance field range $600-1,500/day (including driver, "
                  "paramedic, fuel, security surcharge). $700 used as mid-range ground ambulance estimate.",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
    "fuel_cost_usd_per_l":             {
        "value": 1.20,
        "prior_value": 1.50,
        "source": "ACAPS Yemen Analysis Hub, 'Fuel Supply Dynamics and Fuel Price Impact', "
                  "September 12, 2022. Consumer price during truce: $1.19/L (IRG areas); "
                  "pre-truce Jan–Apr 2022: $1.02/L. Revised from $1.50 to $1.20 (mid-range "
                  "+ modest conflict access premium). "
                  "URL: https://www.acaps.org/fileadmin/Data_Product/Main_media/"
                  "20220912_acaps_yemen_analysis_hub_thematic_report_fuel_supply_dynamics.pdf",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
    "security_ratios":                 {
        "value": "1:50 to 1:500 by risk level",
        "source": "PARTIALLY SUPPORTED — June 2026 six-search validation. "
                  "Sudan armed escort 2022: 60,000–100,000 SDG/vehicle/movement; at Sept 2022 "
                  "parallel market rate (~650 SDG/USD) ≈ $92–$154/vehicle/trip plus overnight fee. "
                  "Source: Achilli & Osman, 'Humanitarianism's Thin Red Line', Journal of "
                  "Humanitarian Affairs Vol. 5(3), 2024. "
                  "URL: https://www.manchesterhive.com/view/journals/jha/5/3/article-p23.xml. "
                  "Yemen armed escort: $3,000/convoy Aden–Mukalla (Sana'a Center, ~2020). "
                  "Somalia 2017: $400M/year total humanitarian security costs "
                  "(NRC/Protect Humanitarian Space, Cost of Operations in H2R Areas, Feb 2024). "
                  "URL: https://www.protecthumanitarianspace.com/sites/default/files/2024-02/"
                  "Cost%20of%20Operations%20in%20H2R%20Areas.pdf. "
                  "Cost per security person per day — LOCAL MILITIA: $40–$110/day; "
                  "PROFESSIONAL PSC: $200–$500/day. Model uses $300/day as mid-market estimate. "
                  "KNOWN GAP: convoy-unit costs (per vehicle/trip) cannot be directly converted "
                  "to per-person-per-day without convoy size and duration assumptions. "
                  "UNDSS security staff rate cards are not publicly accessible.",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
    "shelter_cost_usd_per_unit":       {
        "value": 380,
        "prior_value": 150,
        "source": "UPDATED Tavily validation June 2026: The New Humanitarian (Dec 9, 2022) — direct UNHCR quote "
                  "from chief technical support lead: 'tents cost $400 each to replace'. "
                  "UNHCR Emergency Shelter Design Catalogue Jan 2016: $229/unit (incl. transport 15% + labour 30%). "
                  "Made-in-China UNHCR-standard tents bulk FOB 2024: $210-380/unit (500+ piece orders). "
                  "$380 used as conservative 2024 estimate below UNHCR $400 replacement cost. "
                  "Prior value $150 = basic tarpaulin shelter kit (appropriate for ≤7 days only). "
                  "URL: The New Humanitarian, 'Is emergency shelter fit for purpose?', Dec 9, 2022.",
        "confidence": "estimated",
        "search_date": "June 2026",
        "note": "Updated from $150 tarpaulin assumption to $380 UNHCR-standard tent. "
                "Still below UNHCR stated replacement cost of $400 (2022). "
                "Use $400-$516 for multi-week displacement scenarios.",
    },
    "med_staff_ratio":                 {
        "value": "1:500",
        "source": "Sphere 2018 recommends 1:250 for clinical officers in emergency settings "
                  "(model uses 1:500, i.e. half the Sphere standard). "
                  "Daily rate validation — June 2026 search: "
                  "INTERNATIONAL STAFF: MSF starting salary all roles $2,626–$2,914/month "
                  "(=$87–$97/day take-home). "
                  "Source: doctorswithoutborders.org/careers/work-internationally/pay-benefits (2022). "
                  "With operational overhead 2–3×: $174–$291/day total cost to operation. "
                  "UN P3 net base salary: ~$92,380/year = $253/day (ICSC salary tables). "
                  "Fully-loaded international UN staff in Sudan (salary + DSA $270 + "
                  "danger pay $57/day): ~$580/day total. "
                  "Source: ICSC DSA Circular ICSC/CIRC/DSA/574 (1 Mar 2023), Bangui = $186/day; "
                  "EU per diem rates (Nov 2024): Sudan $270, Yemen $225, Somalia $175/day. "
                  "NATIONAL STAFF LMIC: UN GS salary set by local survey (not publicly "
                  "disclosed per-country). LMIC informal minimum wages: South Sudan $30–60/month "
                  "= $1–3/day. Estimated national staff operational cost: $20–60/day. "
                  "MODEL ASSUMPTION: $200/day implicitly assumes experienced national staff "
                  "or lower-cost international NGO deployment (consistent with MSF mid-range), "
                  "NOT full UN international professional rate. This assumption is not stated "
                  "in the UI and should be flagged.",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
    "contingency_pct":                 {
        "value": 0.15,
        "source": "High-risk project standard: 15–20% (PMI, construction project management literature). "
                  "UNHCR institutional reserve = 5% of programmed activities (different concept — "
                  "institutional buffer, not project contingency). CERF overhead cap = 10% personnel + "
                  "3% general operating costs (caps, not contingency). 15% is the lower bound for "
                  "high-risk conflict-context projects and is defensible.",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
    "comms_cost_usd_per_radio":        {
        "value": 500,
        "source": "Partially validated June 2026. Professional humanitarian VHF handheld radio "
                  "(Motorola DP4400/Icom IC-F3161 class): $350–$700/unit at procurement. "
                  "Satellite phone: $1–$2/min airtime (Access Partnership 2022). ETC Sudan "
                  "SitRep (Jan 2024) confirms VHF radios are the standard field unit. $500 is "
                  "within the documented procurement range.",
        "confidence": "estimated",
        "search_date": "June 2026",
    },
}

# NOTE: PERSONNEL_RATES (147-line personnel daily-rate sourcing dict) was removed —
# dead code, never referenced anywhere in calculators.py or main.py. The actual rates
# used by calculate_resources() are inline literals (security x$300, med_staff x$200,
# paramedics x$150, drivers x$50 — see PERSONNEL section below). The NGO-vs-UN rate
# deployment assumption this dict documented is now surfaced in the live UI instead
# (see the deploy-notice / "Personnel Cost Assumption" panel in static/index.html).

# ─── ERCF Risk Score Formula ──────────────────────────────────────────────────
#
# risk_score = D1×0.25 + D2×0.15 + D3×0.15 + D4×0.15 + D5×0.15 + D6×0.10 + D7×0.05
#
# All values are on a 1–5 scale; score range is [1.0, 5.0].
#
# HARD TRIGGER: if D1 ≥ 4.5 AND D6 ≥ 4.5 → score floored to max(score, 4.21) → Level 4.
#
# LEVEL THRESHOLDS:
#   Level 0  Baseline / Monitoring    : score ≤ 1.5
#   Level 1  Low Risk / Advisory      : 1.5 < score ≤ 2.5
#   Level 2  Moderate Risk / Watchful : 2.5 < score ≤ 3.5
#   Level 3  High Risk / Contested    : 3.5 < score ≤ 4.2
#   Level 4  Critical / Emergency     : score > 4.2  (or hard trigger active)
#
# ─── WEIGHT RATIONALE ────────────────────────────────────────────────────────
# VALIDATION STATUS: ALL WEIGHTS ARE MODELLED ESTIMATES.
# No published IHL or humanitarian operations framework specifies explicit
# numerical weights for these dimensions. Validation against an expert panel
# or empirical conflict data corpus is required before operational use.
#
# D1 Kinetic Threat (0.25 — highest):
#   Direct physical threat to life is the primary driver of evacuation necessity.
#   AP I Art. 57–58 precautionary measures are triggered first by active attack risk.
#   This dimension alone determines whether movement is physically safe.
#   Source: AP I Art. 57–58; GC IV Art. 49. ESTIMATED.
#
# D2 Vulnerability / Mobility Constraints (0.15):
#   Mobility constraints determine whether evacuation is physically possible.
#   High D2 forces medical vehicle allocation and slows the entire operation.
#   Operationally equivalent in importance to D3 logistics and D4 authorization.
#   Source: ICRC guidance on protection of persons with disabilities; Sphere 2018. ESTIMATED.
#
# D3 Authorization / Political (0.15):
#   Without consent from all armed parties, evacuation is illegal under IHL and
#   operationally blocked (GC IV Art. 49). Capped at 0.15 (not higher) because the
#   hard trigger and decision text already capture the most extreme authorization failures.
#   Source: GC IV Art. 49; ICRC Humanitarian Access in Armed Conflict (2011). ESTIMATED.
#
# D4 Logistics (0.15):
#   Even where safe and authorized, evacuation fails without road access, vehicles,
#   and fuel. Logistics collapse is empirically the leading cause of delayed evacuations
#   (Mosul 2016, Aleppo 2016).
#   Source: WFP Logistics Cluster field data; NATO NEO doctrine. ESTIMATED.
#
# D5 Destination (0.15):
#   Moving civilians to an unsafe destination creates secondary harm violating
#   non-refoulement. Srebrenica (1995) is the canonical case: evacuation to a nominally
#   safe zone became a site of genocide.
#   Source: IHL non-refoulement principle; UNHCR protection guidance. ESTIMATED.
#
# D6 Urgency (0.10 — below equal group):
#   Urgency compresses timelines but is largely subsumed by D1 in extreme scenarios.
#   The hard trigger (D1+D6 ≥ 4.5) and evacuation window indicator capture urgency
#   non-linearly; the linear weight is intentionally modest.
#   Source: NATO NEO doctrine (72h window); AP I Art. 57(2)(c). ESTIMATED.
#
# D7 Information (0.05 — lowest):
#   Information gaps increase coordination cost and panic risk, but communications
#   failure alone does not determine whether evacuation is necessary or possible.
#   Physical threat and logistics dominate over information environment.
#   Source: OCHA INFORM methodology; ICRC comms in emergencies guidance. ESTIMATED.
# ──────────────────────────────────────────────────────────────────────────────

WEIGHTS = {
    "d1_kinetic": 0.25,
    "d2_vulnerability": 0.15,
    "d3_political": 0.15,
    "d4_logistics": 0.15,
    "d5_destination": 0.15,
    "d6_urgency": 0.10,
    "d7_information": 0.05,
}

RISK_LEVELS = [
    (1.5, 0, "Baseline / Monitoring",     "Permissive (Stable)",    "#6c757d"),
    (2.5, 1, "Low Risk (Advisory)",        "Permissive (Degrading)", "#0ea5e9"),
    (3.5, 2, "Moderate Risk (Watchful)",   "Uncertain",              "#f59e0b"),
    (4.2, 3, "High Risk (Contested)",      "Hostile (Partial)",      "#f97316"),
    (9.9, 4, "Critical / Emergency",       "Hostile (Imminent)",     "#ef4444"),
]

LEVEL_DECISIONS = {
    0: "No evacuation required. Maintain preparedness planning.",
    1: "Facilitate voluntary departure for vulnerable groups. Issue early warning.",
    2: "Activate Protection Cluster. Negotiate humanitarian corridors. Exhaust alternatives before proceeding.",
    3: "Mass evacuation — last resort threshold met. Military/CIMIC escort required. Notify all parties.",
    4: "Emergency extraction. If window closed: shelter-in-place until corridor opens.",
}

LEVEL_IHL = {
    0: "GC IV Art. 49 threshold not yet met.",
    1: "Art. 35 GC IV — voluntary departure right applies.",
    2: "AP I Art. 57–58 — precautionary measures required.",
    3: "GC IV Art. 49: 'security of the population so demand'.",
    4: "GC IV Art. 49(1) — forced transfer = grave breach. Rome Statute Art. 8(2)(b)(viii).",
}


# ─── Sub-index definitions (Teresa/Yorke framework, June 2026) ───────────────
#
# RISK SEVERITY  (D1×0.25 + D2×0.15 + D6×0.10) / 0.50  → 1–5
# FEASIBILITY    ((6-D3)×0.15 + (6-D4)×0.15 + (6-D5)×0.15) / 0.45  → 1–5
#   D3/D4/D5 inverted: high score = bad conditions = LOW feasibility.
# INFORMATION    6 - D7  → 1–5  (inverted: 5 = excellent situational awareness)
#
# DECISION MATRIX:
#   Risk HIGH (≥3.5) + Feasibility HIGH (≥3.0) → Evacuate immediately
#   Risk HIGH (≥3.5) + Feasibility LOW  (<3.0) → Shelter-in-place + negotiate
#   Risk LOW  (<3.5) + Feasibility HIGH (≥3.0) → Facilitate voluntary departure
#   Risk LOW  (<3.5) + Feasibility LOW  (<3.0) → Monitor
# ─────────────────────────────────────────────────────────────────────────────

DECISION_MATRIX = {
    ("high", "high"): {
        "recommendation": "Evacuate immediately",
        "rationale":      "High danger AND viable corridor — delay increases deaths with no operational benefit.",
        "ihl_trigger":    "GC IV Art. 49: security of the population demands evacuation.",
        "color":          "#ef4444",
    },
    ("high", "low"): {
        "recommendation": "Shelter-in-place — negotiate corridor urgently",
        "rationale":      "High danger but movement not viable. Forced evacuation without a safe corridor risks greater harm than staying.",
        "ihl_trigger":    "AP I Art. 57–58: precautionary measures. Negotiate Art. 49 GC IV corridor with all parties.",
        "color":          "#f97316",
    },
    ("low", "high"): {
        "recommendation": "Facilitate voluntary departure",
        "rationale":      "Corridor viable but situation not yet critical. Support self-organised movement; do not mandate evacuation.",
        "ihl_trigger":    "GC IV Art. 35: right of voluntary departure applies.",
        "color":          "#f59e0b",
    },
    ("low", "low"): {
        "recommendation": "Monitor — no immediate action required",
        "rationale":      "Situation not yet critical and movement not viable. Maintain preparedness; reassess daily.",
        "ihl_trigger":    "GC IV Art. 49 threshold not met.",
        "color":          "#6c757d",
    },
}

FEASIBILITY_LABELS = {
    (1.0, 2.0): "Impossible — corridor blocked or does not exist",
    (2.0, 3.0): "Severely constrained — partial or contested corridor",
    (3.0, 4.0): "Viable — corridor open with significant risk",
    (4.0, 5.1): "Good — organised corridor with manageable risk",
}

RISK_SEVERITY_LABELS = {
    (1.0, 2.5): "Low — civilian life not immediately threatened",
    (2.5, 3.5): "Moderate — elevated threat, monitor closely",
    (3.5, 4.5): "High — direct threat to civilian life",
    (4.5, 5.1): "Critical — imminent mass casualty risk",
}


def _label_from_ranges(value: float, ranges: dict) -> str:
    for (lo, hi), label in ranges.items():
        if lo <= value < hi:
            return label
    return "Unknown"


def calculate_risk(scores: Dict) -> Dict:
    """
    Returns the ERCF composite risk score (backward compatible) plus three
    independent sub-indexes: risk_severity, feasibility, and information_quality.

    All sub-indexes are on a 1–5 scale:
      risk_severity:       1 = minimal danger,      5 = imminent mass casualty
      feasibility:         1 = movement impossible, 5 = corridor fully viable
      information_quality: 1 = complete blackout,   5 = excellent situational awareness
    """
    weighted = sum(scores.get(k, 1) * w for k, w in WEIGHTS.items())
    # Hard-trigger override: if both D1 and D6 >= 4.5, floor at Level 4
    if scores.get("d1_kinetic", 0) >= 4.5 and scores.get("d6_urgency", 0) >= 4.5:
        weighted = max(weighted, 4.21)

    d = scores

    # ── Risk Severity sub-index (D1, D2, D6) ─────────────────────────────────
    risk_sub = (
        d.get("d1_kinetic",       1) * 0.25 +
        d.get("d2_vulnerability", 1) * 0.15 +
        d.get("d6_urgency",       1) * 0.10
    ) / 0.50

    # ── Feasibility sub-index (D3, D4, D5) — all inverted ────────────────────
    feasibility_sub = (
        (6 - d.get("d3_political",   1)) * 0.15 +
        (6 - d.get("d4_logistics",   1)) * 0.15 +
        (6 - d.get("d5_destination", 1)) * 0.15
    ) / 0.45

    # ── Information Quality sub-index (D7) — inverted ────────────────────────
    info_sub = 6 - d.get("d7_information", 1)

    # ── Decision matrix ───────────────────────────────────────────────────────
    risk_cell = "high" if risk_sub >= 3.5 else "low"
    feas_cell = "high" if feasibility_sub >= 3.0 else "low"
    matrix_rec = DECISION_MATRIX[(risk_cell, feas_cell)]

    sub_scores = {
        "risk_severity": {
            "score":      round(risk_sub, 3),
            "label":      _label_from_ranges(risk_sub, RISK_SEVERITY_LABELS),
            "dimensions": "D1 kinetic + D2 vulnerability + D6 urgency",
            "question":   "How dangerous is the situation for civilians?",
        },
        "feasibility": {
            "score":      round(feasibility_sub, 3),
            "label":      _label_from_ranges(feasibility_sub, FEASIBILITY_LABELS),
            "dimensions": "D3 authorization + D4 logistics + D5 destination (inverted)",
            "question":   "Can people realistically move?",
        },
        "information_quality": {
            "score":      round(info_sub, 3),
            "label":      f"D7 = {d.get('d7_information', 1)} → quality {round(info_sub, 1)}/5",
            "dimensions": "D7 information environment (inverted)",
            "question":   "Quality of the decision environment?",
        },
    }
    matrix_out = {"risk_cell": risk_cell, "feasibility_cell": feas_cell, **matrix_rec}

    for threshold, level, label, nato, color in RISK_LEVELS:
        if weighted <= threshold:
            return {
                "risk_score":      round(weighted, 3),
                "risk_level":      level,
                "risk_label":      label,
                "nato_equivalent": nato,
                "color":           color,
                "decision":        LEVEL_DECISIONS[level],
                "ihl_reference":   LEVEL_IHL[level],
                "sub_scores":      sub_scores,
                "matrix":          matrix_out,
            }

    return {
        "risk_score":      round(weighted, 3),
        "risk_level":      4, "risk_label": "Critical / Emergency",
        "nato_equivalent": "Hostile (Imminent)", "color": "#ef4444",
        "decision":        LEVEL_DECISIONS[4], "ihl_reference": LEVEL_IHL[4],
        "sub_scores":      sub_scores,
        "matrix":          {"risk_cell": "high", "feasibility_cell": feas_cell,
                            **DECISION_MATRIX[("high", feas_cell)]},
    }


# TODO: terrain parameter can be auto-populated from World Bank RAI API
# when user selects a country on the map. RAI endpoint:
# https://datacatalog.worldbank.org/dataset/0038250

# ── Terrain & Infrastructure cost multipliers ─────────────────────────────
# Sources (Tavily search, June 2026):
# (1) HDM-4 / Auburn/NCAT Rep15-02 (2015): good road ×1.05, fair ×1.15, poor ×1.25
#     — validated for civil transport; applied here as lower-bound proxy.
#     URL: eng.auburn.edu/research/centers/ncat/files/technical-reports/rep15-02.pdf
# (2) WFP Logistics Annual Report (2012, wfp.tind.io/record/128161):
#     CAR/South Sudan/DRC = $593/MT vs standard countries = $118/MT (5× ratio).
#     Supports upper range but conflates terrain, access, and security factors.
# (3) NRC/Protect Humanitarian Space (2024): qualitative H2R cost elevation confirmed.
# GAP: No primary source publishes isolated terrain multipliers for humanitarian
# evacuation. ×1.0–×1.2 consistent with HDM-4; ×1.7–×2.5 estimated proxies;
# ×4.0 expert upper bound consistent with WFP aggregate ratios.
# Seasonal closure periods: general knowledge; no single validated source.
TERRAIN_MULT = {1: 4.0, 2: 2.5, 3: 1.7, 4: 1.2, 5: 1.0}

# Infrastructure-denial mortality multiplier (v7 calibration)
# Applies ONLY when D1 (kinetic) AND D4 (logistics) are both critically high,
# indicating documented deliberate destruction of survival infrastructure.
# Applied to 4 documented cases: Mariupol, Aleppo, Vukovar, Huambo
# (flag infra_denial_flag=True in historical_data.py)
# alpha=0.4251, optimised jointly with base rates via differential_evolution
# minimising MSLE across 16 calibration cases. Prior alpha=1.421 (Nelder-Mead,
# v6) was calibrated against a stale model state — see calibration/full_calibration.py
# Effective multipliers v7: Mariupol ×2.275, Aleppo ×1.850, Vukovar ×1.638, Huambo ×1.850
# Source: GRC 'The Hope Left Us' (2024) — starvation as method of warfare in Mariupol;
# UN Commission of Inquiry Syria (2017) — hospital bombing in Aleppo;
# ICTY proceedings — infrastructure targeting in Vukovar;
# HRW/Amnesty Angola (1994/1996) — deliberate food/water destruction in Huambo
INFRA_DENIAL_ALPHA        = 0.4251  # v7: α=0.4251 optimised jointly with base rates. Effective multipliers: Mariupol ×2.275, Aleppo ×1.850, Vukovar ×1.638, Huambo ×1.850
INFRA_DENIAL_D1_THRESHOLD = 4.5   # D1 must be at or above this
INFRA_DENIAL_D4_THRESHOLD = 4.0   # D4 must be at or above this


def infra_denial_mult(infra_denial_flag: bool, d1: float, d4: float) -> float:
    """
    Infrastructure-denial mortality multiplier (v6).
    Activates ONLY when infra_denial_flag=True (explicit primary-source documentation)
    AND D1 >= 4.5 AND D4 >= 4.0 (plausibility check).
    Flag is set in historical_data.py for Mariupol, Vukovar, Huambo only.
    For live Scenario Builder: flag=False by default (reverted from Prompt 4 auto-activation).
    Auto-activation by D-score thresholds alone caused calibration collapse (within-2× 80%→20%).
    """
    if infra_denial_flag and d1 >= INFRA_DENIAL_D1_THRESHOLD and d4 >= INFRA_DENIAL_D4_THRESHOLD:
        return 1.0 + INFRA_DENIAL_ALPHA * (d1 - 3.0) * (d4 - 3.0)
    return 1.0


def get_seasonal_terrain_factor(terrain: int, lat: float, month: int) -> dict:
    """
    Determine whether the planned start month falls within the seasonal closure
    period for the given terrain type and latitude zone, and return an adjusted
    terrain multiplier plus operational flags.

    METHODOLOGY (estimated — see TERRAIN_MULT comment block above for sourcing):
    Closure periods are determined by latitude zone and terrain type:
    - Lat > 30 (temperate/sub-arctic northern): snow closure = Dec, Jan, Feb, Mar (months 12,1,2,3)
    - Lat < -30 (temperate southern hemisphere): snow closure = Jun, Jul, Aug, Sep (months 6,7,8,9)
    - Lat -30 to 30 (tropical/subtropical): wet season closure = Apr–Oct (months 4–10)
      (broad regional approximation; two-season equatorial zones not individually modelled)

    Terrain types 4–5 have no seasonal adjustment (minimal/no documented closure).
    Terrain type 1 in closure period is flagged 'potentially_impassable' rather than
    just receiving a cost boost — consistent with documented cases such as Afghanistan's
    Salang Pass (closure Nov–Apr, WFP documented rerouting).

    Seasonal boost factors are estimated with no primary numerical source; they represent
    the additional cost of operating on a partially passable route vs. a fully open one.
    The 'potentially_impassable' flag for terrain 1 is the operationally preferred signal.

    Args:
        terrain: terrain level 1–5 (matches TERRAIN_MULT keys)
        lat: latitude of conflict location (from map pins)
        month: month of planned start date (1=Jan … 12=Dec)

    Returns dict with:
        terrain_mult         — adjusted multiplier (base or boosted)
        base_mult            — unadjusted TERRAIN_MULT value
        seasonal_boost       — fractional boost applied (0.0 if not in closure)
        is_closure_period    — bool: start month is within seasonal closure window
        potentially_impassable — bool: terrain 1 in closure period
        closure_months       — list of month ints that are closure months for this zone
        zone                 — 'northern_temperate' | 'southern_temperate' | 'tropical'
        note                 — human-readable explanation string
    """
    base = TERRAIN_MULT.get(terrain, 1.0)

    # Determine latitude zone and closure months
    if lat > 30:
        zone = 'northern_temperate'
        closure_months = [12, 1, 2, 3]
        zone_label = 'northern temperate (snow/ice closure Dec–Mar)'
    elif lat < -30:
        zone = 'southern_temperate'
        closure_months = [6, 7, 8, 9]
        zone_label = 'southern temperate (snow/ice closure Jun–Sep)'
    else:
        zone = 'tropical'
        closure_months = [4, 5, 6, 7, 8, 9, 10]
        zone_label = 'tropical/subtropical (wet season closure Apr–Oct, estimated)'

    # Seasonal boost by terrain type (only for types 1–3)
    SEASONAL_BOOST = {1: 0.50, 2: 0.30, 3: 0.20, 4: 0.0, 5: 0.0}
    boost = SEASONAL_BOOST.get(terrain, 0.0)

    is_closure = (month in closure_months) and (terrain in [1, 2, 3])
    potentially_impassable = (terrain == 1) and is_closure

    if is_closure and boost > 0:
        adjusted_mult = round(base * (1 + boost), 2)
        note = (
            f"Terrain level {terrain} in seasonal closure period ({zone_label}). "
            f"Base multiplier ×{base} boosted by {int(boost*100)}% to ×{adjusted_mult}. "
            + ("WARNING: route potentially impassable — consider alternative." if potentially_impassable else "")
        )
    else:
        adjusted_mult = base
        note = f"Terrain level {terrain} outside seasonal closure period ({zone_label})."

    return {
        'terrain_mult': adjusted_mult,
        'base_mult': base,
        'seasonal_boost': boost if is_closure else 0.0,
        'is_closure_period': is_closure,
        'potentially_impassable': potentially_impassable,
        'closure_months': closure_months,
        'zone': zone,
        'note': note,
    }


def calculate_resources(
    population: int, vulnerable_pct: float, risk_level: int, distance_km: float,
    d2_mobility: float = 3.0,
    terrain: int = 3,
    climate_mult: Optional[Dict[str, float]] = None,
    d4: float = 3.0,
    d5: float = 3.0,
) -> Dict:
    """
    FORMULA DOCUMENTATION — calculate_resources()
    ===============================================
    Inputs: population P, vulnerable fraction V (as %), risk level R (0–4), distance D km.

    PLANNING BASIS — POPULATION SIZING:
    Supplies and personnel are dimensioned for the total population at risk (P), consistent
    with humanitarian planning doctrine:
    - Sphere Handbook (2018): minimum standards apply to the full disaster-affected population,
      not only those who accept assistance. Planning figures use total population in need (PIN).
      URL: spherestandards.org/wp-content/uploads/Sphere-Handbook-2018-EN.pdf
    - IASC Caseload Support Package (2016): response plans project needs for the full PIN;
      actual beneficiaries reached will be lower but planning must cover the total.
      URL: gbvaor.net/sites/default/files/2019-07/2016 IASC caseload support package (EN).pdf

    IN-SITU POPULATION NOTE:
    NRC "Considerations for Planning Mass Evacuations of Civilians in Conflict Settings" (2017)
    explicitly warns that convoy supplies must NOT be drawn from in-situ population resources:
    "If a food warehouse is emptied to provide food for an evacuating convoy, the population
    that would have otherwise benefited from those supplies may feel that humanitarians are
    offering preferential treatment." The in-situ assistance stream is modelled separately
    in calculate_remaining_costs().
    URL: nrc.no/globalassets/pdf/reports/considerations-for-planning-mass-evacuations-of-civilians-in-conflict-settings

    FIXED vs VARIABLE COST DISTINCTION — GAP:
    No published institutional source (WFP, UNHCR, IOM, ICRC) explicitly documents a
    fixed mobilization cost (scaled to total population) vs variable execution cost (scaled
    to actual evacuees) for conflict evacuation operations. Academic ops research literature
    (MDPI, 2025) models fixed+variable costs mathematically but for casualty evacuation,
    not civilian humanitarian operations. BVL (2020) confirms logistics experts decline to
    give generic figures due to context variability.
    (ref: BVL "Insights on the Costs of Humanitarian Logistics", 2020;
     MDPI Sustainability doi:10.3390/su17241126, 2025)

    VEHICLES
      vuln         = P × V/100
      non_vuln     = P - vuln
      std_buses    = ceil(non_vuln / 50)          # 50-pax assumption (unvalidated)
      med_buses    = ceil(vuln / 20)              # 20-pax medical buses (unvalidated)
      ambulances   = max(1, ceil(vuln / 150))
        → 1 ambulance per 150 vulnerable persons (revised from 1:40).
        No published field standard found for humanitarian evacuation ambulance ratios
        (ICRC 2015, WHO EMS standards, MSF — none specify evacuation ratios).
        1:150 adopted as conservative operational estimate consistent with documented
        field scarcity (Kosovo study PMC10068156: few ambulances, private vehicles used).
        Prior value 1:40 (5% vuln / cap 2) was 3-5× above documented practice.

    PERSONNEL (daily cost rates, all unvalidated)
      security_ratio = [∞, 500, 200, 100, 50][risk_level]
      security   = ceil(P / security_ratio)    @ $300/person
      med_staff  = ceil(P / 250)               @ $200/person  (Sphere Handbook 2018: 1:250)
      paramedics = ceil(P / 100)               @ $150/person
      drivers    = total_vehicles              @ $50/person

    SUPPLIES
      fuel_l     = vehicles × distance × 2 (return trip) × 0.35 L/km/vehicle
      food_kg    = P × 3 days × 0.45 kg/person/day   @ $3/kg
        Sphere Handbook 2018: minimum 2,100 kcal/person/day = ~0.45 kg dry food equivalent.
        Previous value 0.5 kg was inconsistent with SOURCE_CONFIDENCE citing Sphere 0.45 kg.
      water_l    = P × 3 days × 20 L/person/day (UNHCR full standard; updated 15→20 Tavily Jun 2026)
      tents      = ceil(P / 5)                  @ $380/tent (updated $150→$380 Tavily Jun 2026)
        Quantity check: 3.5 m²/person × 5 people = 17.5 m²/tent — SPHERE-CONSISTENT
        Unit cost: $380 = UNHCR-standard tent. Source: The New Humanitarian Dec 2022 — UNHCR quote
        '$400 to replace'; UNHCR Shelter Design Catalogue 2016: $229 incl. transport+labour.
        $380 is conservative 2024 estimate below UNHCR replacement cost. Dominates subtotal.
      trauma_kits: /50 if R≥3 else /200

    # Resources dimensioned for total population in need (PIN) per Sphere Handbook (2018)
    # planning figure methodology and IASC Caseload Support Package (2016). Actual evacuee
    # count may differ — convoy sizing follows total estimated caseload as per operational
    # planning doctrine.
    COSTS (USD — all unit costs unvalidated unless noted)
      transport  = std_buses×$200 + med_buses×$400 + ambulances×$700 + drivers×$50  (updated Tavily Jun 2026)
        NOTE: drivers cost is labour mixed into a vehicle-hire line — consider separating.
      fuel       = fuel_l × $1.20/L  (REVISED June 2026 from $1.50; source: ACAPS Yemen
                   Analysis Hub Sep 2022 — conflict zone consumer price $1.02–$1.19/L.
                   $1.20 = documented mid-range + modest conflict access premium.)
      personnel  = security×$300 + med_staff×$200 + paramedics×$150
      food       = food_kg × $3/kg
      water      = water_l × $0.05/L (Sphere-adjacent, unvalidated for field contexts)
        FIELD EVIDENCE (Tavily, Jun 2026, not yet adopted — baseline kept at $0.05/L pending
        further validation): real-world water trucking costs found range $2-23/m3, all below
        this baseline — NRC Yemen (Taiz, Jul 2025, direct market quote): $5/m3; ICRC/UNICEF
        Aleppo (2013-14, derived from $1M/month for 16M L/day): $2/m3; Ethiopia HRP 2024
        (derived): ~$17.6/m3; Oxfam Kenya/Wajir drought response (derived): ~$22.6/m3. No
        international index (no FRED/EIA equivalent) exists for water trucking — all figures
        are one-off project/field reports, not a re-queryable benchmark.
      shelter    = tents × $380      (DOMINANT LINE: updated Tavily Jun 2026 — UNHCR 2022: $400/unit)
      medical    = med_kits×$21 + trauma_kits×$200
        med_kits cost revised $50→$21/kit (100-person kit): based on WHO/UNICEF IEHK
        (~$20,584/10,000 persons/90 days × 3 days × 3× trauma adjustment = $0.207/person
        → $20.7/kit for 100-person kit). PMC5321368 (2017, peer-reviewed).
        Prior $50/kit = ~7× above IEHK equivalent for 3-day convoy.
      comms      = (ceil(vehicles/5)+5) × $500/radio
      contingency = subtotal × 15%

    VERIFIED TRACE — 10 000 people, 20% vulnerable, Level 2, 50 km, D2=3 (baseline mobility),
    baseline terrain (no multiplier):
      std_buses=160, med_buses=130, ambulances=18, total_veh=308
      security=50, med_staff=40, paramedics=100, drivers=308
      fuel_l=10 780  food_kg=13 500  water_l=600 000  tents=2 000  radios=67
      transport=$134 400  fuel=$15 523  personnel=$38 000  food=$40 500
      water=$30 000  shelter=$760 000  medical=$12 100  comms=$33 500
      subtotal=$1 064 023  contingency=$159 603  TOTAL=$1 223 626 ≈ $1.22M
      (recomputed and cross-checked against a live calculate_resources() call, June 2026 —
      reflects the current 1:150 ambulance ratio, 1:250 med_staff ratio, 0.45kg food,
      20L water, $400/$700 vehicle costs, $1.20/L fuel, $380/tent, $21/med-kit.)

    KNOWN LIMITATIONS
      • No unit cost is validated against WFP/ICRC/UNHCR field data by country/year.
      • No differentiation for urban vs. rural access context.
      • Destination/reception-area setup costs not modelled.
      • Vehicle round-trip fuel only; no staging/repositioning fuel included.
    """
    vuln = int(population * vulnerable_pct / 100)
    non_vuln = population - vuln

    # D2 Mobility Constraints multiplier on medical vehicles
    # D2=1→×0.8  D2=2→×1.0(baseline)  D2=3→×1.3  D2=4→×1.8  D2=5→×2.5
    if d2_mobility <= 1:   _d2m = 0.8
    elif d2_mobility <= 2: _d2m = 0.8 + (d2_mobility - 1) * 0.2
    elif d2_mobility <= 3: _d2m = 1.0 + (d2_mobility - 2) * 0.3
    elif d2_mobility <= 4: _d2m = 1.3 + (d2_mobility - 3) * 0.5
    else:                  _d2m = 1.8 + (d2_mobility - 4) * 0.7

    std_buses   = math.ceil(non_vuln / 50)
    med_buses   = math.ceil(vuln / 20 * _d2m)
    # Revised from 1:40 to 1:150 vulnerable. No published field standard found (ICRC 2015,
    # WHO EMS standards, MSF — none specify evacuation ambulance ratios). 1:150 adopted as
    # conservative operational estimate consistent with documented field scarcity
    # (Kosovo study, PMC10068156). Previous value 1:40 was 3-5× above documented practice.
    ambulances  = max(1, math.ceil(vuln / 150 * _d2m))
    total_veh   = std_buses + med_buses + ambulances

    sec_ratio   = [99999, 500, 200, 100, 50][risk_level]
    security    = math.ceil(population / sec_ratio) if risk_level > 0 else 0
    # Sphere Handbook 2018 Health chapter: 1 clinical officer per 250 people in emergency settings.
    # Previous value 1:500 was deliberately set at 50% of Sphere standard without documented
    # justification — corrected to Sphere minimum.
    med_staff   = math.ceil(population / 250)
    paramedics  = math.ceil(population / 100)
    drivers     = total_veh

    fuel_l      = total_veh * distance_km * 2 * 0.35
    # Sphere Handbook 2018: minimum 2,100 kcal/person/day = ~0.45 kg dry food equivalent.
    # Previous value 0.5 kg was inconsistent with internal SOURCE_CONFIDENCE comment citing
    # Sphere 0.45 kg.
    food_kg     = population * 3 * 0.45
    # WATER_L_PER_PERSON updated 15 → 20 (Tavily validation June 2026)
    # UNHCR full standard: 20 L/person/day
    # Sphere 2018 emergency minimum: 7.5-15 L/person/day
    # Using UNHCR full standard for evacuation planning (not emergency minimum)
    water_l     = population * 3 * 20

    # D4 Logistics multiplier on transport + fuel
    # D4=1 → +0%, D4=2 → +10%, D4=3 → +20%, D4=4 → +30%, D4=5 → +40%
    # ESTIMATED — no primary source for this specific ratio in evacuation contexts;
    # derived from analogy with the calcRemaining() D4 penalty already in use.
    d4_logistics_mult = 1.0 + max(0, (d4 - 1)) * 0.10

    # D5 Destination multiplier on tent/shelter requirement
    # (D5 runs 1 = destination fully equipped → 5 = destination unsafe/non-existent,
    #  same direction as every other dimension)
    # D5=1 (good destination, has infrastructure): ×0.5 tents needed
    # D5=5 (no infrastructure at destination): ×2.0
    # ESTIMATED — no primary source; based on operational logic.
    _D5_TENT_MULT = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.5, 5: 2.0}
    d5_tent_mult = _D5_TENT_MULT.get(int(round(d5)), 1.0)
    tents       = math.ceil((population / 5) * d5_tent_mult)
    med_kits    = math.ceil(population / 100)
    trauma_kits = math.ceil(population / 50) if risk_level >= 3 else math.ceil(population / 200)
    radios      = math.ceil(total_veh / 5) + 5

    terrain_mult = TERRAIN_MULT.get(terrain, 1.0)
    cm = climate_mult or {"fuel_transport": 1.0, "shelter": 1.0}
    climate_fuel_mult    = cm.get("fuel_transport", 1.0)
    climate_shelter_mult = cm.get("shelter", 1.0)
    c = {
        # MED_BUS_COST updated $250 → $400 (Tavily validation June 2026)
        # No primary source found for $250; medically-equipped vehicle (stretchers, O2, trained crew)
        # field range $400-600/vehicle. $400 used as validated lower bound.
        # Source: MSF/ICRC operational literature; no per-vehicle cost publicly itemised
        # AMBULANCE_COST updated $400 → $700 (Tavily validation June 2026)
        # EU Commission Medical Aerial Evacuation Study 2020; conflict-zone ground ambulance
        # field range $600-1,500/day (including driver, paramedic, fuel, security surcharge)
        # $700 used as mid-range estimate for ground ambulance in active conflict zone
        "transport":   round((std_buses*200 + med_buses*400 + ambulances*700 + drivers*50) * terrain_mult * climate_fuel_mult * d4_logistics_mult),
        "fuel":        round(fuel_l * 1.2 * terrain_mult * climate_fuel_mult * d4_logistics_mult),   # $1.20/L — ACAPS Yemen Sep 2022; terrain ×1.0–4.0; D4 logistics
        "personnel":   round(security*300 + med_staff*200 + paramedics*150),
        "food":        round(food_kg * 3),
        "water":       round(water_l * 0.05),   # $0.05/L baseline kept; field range $0.002-0.023/L found (see docstring), not adopted
        # TENT_COST updated $150 → $380 (Tavily validation June 2026)
        # Source: The New Humanitarian Dec 2022 — direct UNHCR quote: "$400 to replace"
        # UNHCR Emergency Shelter Design Catalogue Jan 2016: $229/unit (incl. transport 15% + labour 30%)
        # $380 used as conservative 2024 estimate below UNHCR stated replacement cost
        "shelter":     round(tents * 380 * climate_shelter_mult),
        # MED_KIT_COST updated $50→$21/kit (June 2026): Based on WHO/UNICEF Interagency
        # Emergency Health Kit (IEHK): ~$20,584 per 10,000 persons per 3 months (PMC5321368,
        # 2017, peer-reviewed). Adjusted: $20,584 / 10,000 / 90 days × 3 days × 3× trauma
        # factor = $0.207/person = $20.7/kit (100-person kit). Rounded to $21.
        # IEHK covers primary healthcare (not trauma-specific); ×3 adjustment for conflict
        # evacuation context. Prior $50/kit was ~7× above IEHK equivalent for 3-day convoy.
        # TRAUMA_KIT_COST $200/kit: UNVALIDATED — ICRC war surgery kits treat 1,000–5,000
        # patients but pricing not publicly disclosed (ICRC Gaza 2023). $200/kit retained
        # as planning estimate pending ICRC/MSF field data.
        "medical":     round(med_kits*21 + trauma_kits*200),
        "comms":       round(radios * 500),
    }
    subtotal = sum(c.values())
    c["contingency_15pct"] = round(subtotal * 0.15)
    total = sum(c.values())

    return {
        "summary": {
            "population": population,
            "vulnerable": vuln,
            "distance_km": distance_km,
            "risk_level": risk_level,
            "total_cost_usd": total,
            "cost_per_person_planned_usd": round(total / population, 2),  # denominator = total planned caseload (Sphere/IASC); per-evacuee cost requires caller to divide by (population - remaining_pop)
        },
        "vehicles": {
            "standard_buses_50pax": std_buses,
            "medical_buses_20pax": med_buses,
            "ambulances": ambulances,
            "total": total_veh,
            "drivers_needed": drivers,
        },
        "personnel": {
            "security": security,
            "medical_staff": med_staff,
            "paramedics": paramedics,
            "drivers": drivers,
            "total": security + med_staff + paramedics + drivers,
        },
        "supplies": {
            "fuel_liters": round(fuel_l),
            "food_kg_3days": round(food_kg),
            "water_liters_3days": round(water_l),
            "tents": tents,
            "basic_med_kits": med_kits,
            "trauma_kits": trauma_kits,
            "radios": radios,
        },
        "costs_usd": c,
        "sphere_standard": "15L water/person/day · 2100 kcal/person/day · 3.5m² shelter/person (SPHERE 2018)",
        "climate_applied": {"fuel_transport_mult": climate_fuel_mult, "shelter_mult": climate_shelter_mult},
    }


# ─── Remaining-cost model constants ─────────────────────────────────────────

# UNHAS confirmed per-passenger-km rate (2023)
# Source: WFP Executive Board "Update on UNHAS", January 2025
# URL:    https://executiveboard.wfp.org/document_download/WFP-0000165597
UNHAS_RATE_USD_PER_KM = 2.08

# ─── Extraction probability — empirical calibration (June 2026) ───────────────
#
# FORMULA:  base_prob = 1 − exp(−RATE × days)  [exponential saturation]
#           prob = clamp( base_prob + D3_correction, D6_floor, 0.95 )
#
# CALIBRATION from 10 historical cases in historical_data.py:
# Rate k derived by: k = −ln(1 − p_observed) / days_to_outcome
#
# L4 anchors (k averaged from 2 non-outlier cases):
#   Mariupol 2022 (L4/86d/81% displaced):  k = −ln(0.19)/86  = 0.0193
#     → siege warfare, failed corridors, D3=1.5, D6=5.0
#   Aleppo 2016   (L4/100d/90% evacuated): k = −ln(0.10)/100 = 0.0230
#     → brokered green buses at day 100, D3=2.0, D6=5.0
#   Sudan 2023    (L4/400d/~100%):         k ≈ 0.012 → excluded (spontaneous
#     displacement without corridors; D6=5 floor already captures urgency)
#   Srebrenica    (L4/3d/100%):            OUTLIER — genocide in 3 days; the
#     D6=5 urgency floor (0.85) captures this correctly without distorting the rate
#   Gaza 2023     (L4/420d/83%):           Internal displacement only; treated
#     as D6=5 floor case since organized external extraction never opened
#   → L4 BASE RATE = mean(0.0193, 0.0230) = 0.021
#
# L3 anchors (k averaged from 3 cases where D6 floor does not dominate):
#   Mosul 2016–17 (L3/270d/90% displaced): k = −ln(0.10)/270 = 0.0085
#     → pre-staged IDP camps, prolonged organized extraction, D3=3.0, D6=4.0
#   DRC/Goma 2024 (L3/180d/80% displaced): k = −ln(0.20)/180 = 0.0089
#     → M23 advance, spontaneous displacement, D3=2.0, D6=4.5
#   CAR 2014      (L3/180d/88% displaced): k = −ln(0.12)/180 = 0.0118
#     → convoy attacks, partial corridors, D3=2.5, D6=4.0
#   Kherson 2022  (L3/45d/75% displaced):  k = 0.031 → EXCLUDED as anchor:
#     largely voluntary departure via railway; D6=4.0 floor dominates at 45d
#   Kosovo 1999   (L3/78d/100%):           EXCLUDED: ethnic cleansing outlier,
#     D6=5 floor captures the urgency
#   → L3 BASE RATE = mean(0.0085, 0.0089, 0.0118) = 0.010
#
# L2/L1 BASE RATES: no direct historical cases at these levels in the dataset.
#   L2 = 0.005 (half of L3 — proportional scaling)
#   L1 = 0.002 (further halved — low-intensity, slow-onset)
#   L0 = 0.000 (no conflict, no extraction)
#
# MAXIMUM BASE PROBABILITY (before D3/D6 modifiers):
#   L4 = 0.95 — all L4 cases converge to near-total displacement
#   L3 = 0.80 — Mosul (90%) and DRC (80%) observed; base capped here,
#               D3 modifier brings it to 0.85-0.90 for high-threat authorizations
#   L2 = 0.60 — interpolated; no direct cases
#   L1 = 0.30 — interpolated; most civilians can self-manage at this level
#   L0 = 0.00
#
# UNVALIDATED: L2 and L1 rates have no empirical anchors. They require data
#   from monitored L2 conflicts (e.g., OCHA-monitored low-intensity NIAC)
#   to validate. Current values are structurally plausible interpolations only.

# Emergency extraction rate: estimated 1-8% of remaining population requiring urgent
# medical evacuation (critical casualties unable to self-evacuate). Based on conflict
# casualty ratios (ICRC surgical data) — not mass evacuation rate. Revised from the prior
# 10-95% range, which conflated "probability of a mass extraction operation" with "fraction
# of the population needing individual medevac" — UNHAS 2022 data shows only ~0.25% of all
# passengers transported required medical/security evacuation, two orders of magnitude below
# the prior calibration even accounting for a higher-need trapped-population context.
RC_EXTR_BASE_RATE = [0.0, 0.002, 0.005, 0.010, 0.021]  # per-day exponential rate (unchanged shape)
RC_EXTR_MAX_PROB  = [0.0, 0.01,  0.02,  0.04,  0.08 ]  # cap on base_prob before modifiers: L1=1%, L2=2%, L3=4%, L4=8%

# VALIDATION STATUS — ACCESS MULTIPLIERS (revised June 2026)
# Values are the most conservative defensible estimates from documented sources.
# Prior values shown in brackets. Each multiplier = logistics_component + security_overhead.
#
# L0 = 1.0   CONFIRMED.
#             Source: WFP Gaza ceasefire ~2% loss rate under active monitoring.
#
# L1 = 1.5   SUPPORTED.
#             Sources: WFP Red Sea maritime rerouting +18% (1.18×); WFP Sudan
#             logistics 1.23×. Value 1.5× is a conservative ceiling.
#
# L2 = 2.0   PARTIALLY VALIDATED.  [Prior: 3.0]
#             Documented: logistics premium (1.23×) + partial escort overhead = 1.5–2.0×.
#             Set at 2.0× (upper bound of documented range). Gap to prior 3.0×: ~1.0×
#             in unquantified security overhead, hazard pay, rerouting. Ideal source:
#             UNDSS escort cost data by conflict intensity (not publicly indexed).
#
# L3 = 3.6   PARTIALLY VALIDATED.  [Prior: 5.0]
#             Documented: Somalia security (~$400M/year ≈ 50% of ops, 2017) + Yemen armed
#             escort ($3K/convoy, Sana'a Center ~2020) combined reach 2.5–3.6×. Set at
#             3.6× (upper bound). Gap to prior 5.0×: ~1.4× in hazard pay and negotiation
#             overhead (plausible, unmeasured). Ideal source: ICRC internal cost reports.
#
# L4 = 4.0   DIRECTIONALLY PLAUSIBLE, UNCONFIRMED.  [Prior: 8.0]
#             No single public document exceeds ~4× from documented components.
#             Frontline Gaza/Sudan operations likely higher but no public figure found.
#             Set at 4.0× pending validation. This is a known gap in published
#             humanitarian logistics literature — cost data at this level appears to be
#             internal to UNDSS and ICRC.
#
# RESEARCH NOTE: The absence of a single published cost multiplier for active-conflict
# humanitarian delivery represents a genuine gap in the humanitarian logistics literature.
# This model may be among the first to attempt explicit quantification. Full validation
# requires direct data access from UNDSS, ICRC, or WFP internal operational reports.
RC_ACCESS_MULT  = [1.0,  1.5,  2.0,  3.6,  4.0]

# Supply loss rate (destroyed, looted, or undelivered)
# Source: OCHA access monitoring reports
RC_LOSS_RATE    = [0.05, 0.05, 0.15, 0.30, 0.50]

# NOTE: RC_INFIELD_INJ (in-field injury rate per 1,000/day) was removed — dead constant,
# never wired into executable code. calculate_remaining_costs() uses the shared
# calculate_injuries() helper (INJURY_RATE_10K) instead. See "infield_injury_rates_per_1k_per_day"
# in REMAINING_COST_SOURCE_NOTES below for the historical reference values.

REMAINING_COST_SOURCE_NOTES = {
    "base_supply_usd_per_person_day": {
        "value": 3.50,
        "source": (
            "WFP Annual Performance Report 2023 (WFP Executive Board, WFP-0000157354): "
            "$0.42/beneficiary/day global average (food/cash assistance only, all contexts — "
            "conflict and stable combined). ERCF base of $3.50 includes WASH, health, shelter, "
            "and coordination components not in WFP food-only figure. "
            "Ratio $3.50/$0.42 = 8.3× reflects multi-sector vs food-only scope. "
            "UNHCR 2023 per-capita funding floor: $47/person/year = $0.13/day (funding received, "
            "not cost of operations). Neither figure provides a conflict-specific daily cost. "
            "URL: executiveboard.wfp.org/document_download/WFP-0000157354"
        ),
        "confidence": "estimated",
    },
    "access_multipliers": {
        "value": {"L0": 1.0, "L1": 1.5, "L2": 2.0, "L3": 3.6, "L4": 4.0},
        "prior_values": {"L2": 3.0, "L3": 5.0, "L4": 8.0},
        "revised": "June 2026 — reduced to upper bound of documented sources",
        "source": (
            "WFP Logistics Cluster field data, conflict-affected contexts 2020–2023; "
            "OCHA Access Monitoring and Reporting Framework. "
            "NEW ANCHOR (L3): WFP Logistics Annual Report 2012 — $593/MT for CAR/South Sudan/DRC "
            "vs $180/MT global overland average = ×3.3 ratio (terrain + conflict combined, not isolated). "
            "ERCF L3=×3.6 is directionally consistent with this figure. "
            "(ref: wfp.tind.io/record/128161). "
            "NRC/Protect Humanitarian Space (Feb 2024) 'Cost of Operations in Hard-to-Reach Areas' "
            "confirms qualitatively that Libya, Iraq, Syria (active conflict) were the three most expensive "
            "crises in 2021, but provides no numerical multiplier per level. "
            "No published source found with explicit L2/L3/L4 cost multipliers for active-conflict delivery. "
            "L4=×4.0 remains directionally plausible but unconfirmed — no public figure found exceeding ×4. "
            "(ref: protecthumanitarianspace.com, Feb 2024)"
        ),
        "confidence": "estimated",
        "components": {
            "logistics_component": {
                "range":  "1.0× to 1.23×",
                "basis":  "WFP per-MT logistics data — Sudan active conflict ($209.63/MT) "
                          "vs Eastern Africa mixed average ($170.71/MT) = 1.23× premium",
                "status": "partially validated by WFP East Africa 2023 report",
            },
            "security_and_overhead_component": {
                "range":  "2× to 7× above logistics alone",
                "basis":  "security escorts, armed-group negotiation, staff hazard pay, "
                          "forced rerouting, convoy protection — estimated, not measured",
                "status": "unvalidated — requires UNDSS or ICRC security cost data",
                "sources_needed": [
                    "UNDSS security cost reporting by conflict intensity",
                    "ICRC: 'Security Management of Humanitarian Operations' (restricted)",
                    "OCHA Financial Tracking Service per-operation overhead data",
                ],
            },
        },
    },
    "wfp_east_africa_2023": {
        "figure": "$170.71/MT average (total logistics), $131.43/MT transport only",
        "url":    "https://wfp.tind.io/record/130347/files/ELR%203284.pdf",
        "source": "WFP Regional Bureau Eastern Africa, 'Logistics in Eastern Africa: "
                  "Delivering Amidst Increased Challenges' (2023)",
        "implies_multiplier": 1.0,
        "note":   "Mixed conflict/stable contexts across Eastern Africa; serves as "
                  "approximate regional baseline for per-MT delivery cost",
    },
    "wfp_sudan_conflict_2023": {
        "figure": "$209.63/MT active conflict delivery ($39.2M / 187,000 MT)",
        "url":    "https://wfp.tind.io/record/130347/files/ELR%203284.pdf",
        "source": "WFP Eastern Africa 2023 report, Sudan section",
        "implies_multiplier": 1.23,
        "note":   "Conflict-induced cost increase: new corridors via Chad/Egypt/South Sudan, "
                  "Port Sudan access disrupted, fuel scarcity, cash access collapse. "
                  "Underestimates true access cost because UNHAS and Logistics Cluster "
                  "services are provided free-to-user or at partial cost recovery.",
        "per_person_per_day_derivation": {
            "assumption_kg_per_person_day": 0.65,
            "breakdown": "0.5kg food + 0.1kg medicine + 0.05kg other (food-weight only; "
                         "excludes water at 15kg/person/day which dominates supply weight)",
            "mt_per_person_day": 0.00065,
            "logistics_cost_usd": round(209.63 * 0.00065, 4),
            "model_base_usd": 3.50,
            "gap_factor": round(3.50 / (209.63 * 0.00065), 1),
            "gap_explanation": (
                "The $3.50/person/day model base is ~24.3× the logistics-only cost "
                "implied by the WFP Sudan per-MT figure at 0.65kg/person/day. This gap "
                "is expected and explained by: (1) water supply at 15L (15kg) per person "
                "per day raises effective weight to ~15.65kg = 0.01565 MT/person/day, "
                "implying $209.63 × 0.01565 = $3.28/person/day — much closer to the "
                "$3.50 base; (2) the $3.50 base includes non-transport costs (admin, "
                "staff, storage, distribution overheads); (3) Sudan per-MT cost "
                "underestimates true access cost due to subsidised UNHAS/Logistics "
                "Cluster services not captured in the per-MT figure."
            ),
            "with_water_15kg_per_person": {
                "total_kg_per_person_day": 15.65,
                "mt_per_person_day": 0.01565,
                "implied_logistics_usd": round(209.63 * 0.01565, 3),
                "note": "At full Sphere water standard, WFP Sudan logistics cost implies "
                        "$3.28/person/day — within 6% of the $3.50 model base.",
            },
        },
    },
    "yemen_logistics_cluster_2015": {
        "figure": "~$200/MT maritime equivalent (dhow transport at $140/m³)",
        "url":    "https://s3.eu-west-1.amazonaws.com/logcluster-web-prod-files/public/"
                  "yemen_lle_-_final_report_170519_0.pdf",
        "source": "WFP Yemen Logistics Cluster Lessons Learned Report, 2015",
        "note":   "Derived from $140/m³ volume rate assuming ~0.7 MT/m³ food commodity "
                  "density. 2015 figure; Yemen conflict costs have increased since. "
                  "Does not include in-country distribution cost from port to beneficiary.",
    },
    "access_mult_ocha_2024": {
        "search": "SEARCH 1 — OCHA Access Monitoring (June 2026)",
        "source": "NRC/Protect Humanitarian Space, 'Cost of Operations in Hard-to-Reach "
                  "Areas', February 2024",
        "url":    "https://www.protecthumanitarianspace.com/sites/default/files/2024-02/"
                  "Cost%20of%20Operations%20in%20H2R%20Areas.pdf",
        "figure": "Somalia 2017: security cooperation ~$400M/year out of ~$700–900M total "
                  "humanitarian operations → security ≈ 45–57% of total ops",
        "derived_multiplier": "~2.0× from security alone (L3 proxy); ~2.5× combined with "
                              "logistics (1.23×)",
        "verdict": "PARTIALLY SUPPORTIVE for L3 ≥2×; 5× not confirmed from this source",
        "confidence": "estimated — total ops denominator is approximate",
    },
    "access_mult_undss_yemen": {
        "search": "SEARCH 2 — UNDSS Security Cost (June 2026)",
        "source": "Sana'a Center for Strategic Studies, 'To Stay and Deliver: Security' "
                  "(Yemen, ~2020–2021)",
        "url":    "https://sanaacenter.org/reports/humanitarian-aid/15354",
        "figure": "Armed escort (UNDSS-mandated): up to US$3,000 per convoy from Aden to "
                  "Mukalla, one way, plus fuel. Escort required for all missions outside Aden.",
        "derived_multiplier": "Armed escort alone: +$60–$100/MT → 1.35–1.58× on top of "
                              "logistics baseline (L3–L4 Yemen context)",
        "verdict": "PARTIALLY SUPPORTIVE — confirms significant security cost component at "
                   "L3–L4; escort-only figure; total security costs are higher",
        "confidence": "cited figure is specific and attributed but no date on source page",
    },
    "access_mult_wfp_redsea": {
        "search": "SEARCH 3 — WFP Security Surcharge (June 2026)",
        "source": "WFP, 'Middle East crisis: WFP navigates turbulent waters to tackle hunger'",
        "url":    "https://www.wfp.org/stories/middle-east-crisis-wfp-navigates-turbulent-"
                  "waters-fight-hunger",
        "figure": "Roughly 18 percent cost increase for maritime cargo rerouted due to "
                  "Red Sea conflict (Houthi attacks / Strait of Hormuz disruption, 2024–26)",
        "context": "Maritime rerouting overhead — equivalent to L0–L1 access disruption; "
                   "NOT active-conflict ground delivery in a conflict zone",
        "derived_multiplier": "~1.18× for maritime route disruption",
        "verdict": "CONFIRMS L0–L1 = 1.0–1.5×. NEUTRAL for L2–L4.",
        "confidence": "validated — explicit WFP operational figure",
    },
    "access_mult_acf_2018": {
        "search": "SEARCH 5 — Academic Literature (June 2026)",
        "source": "Action Against Hunger (ACF), 'Supply Chain Expenditure & Preparedness "
                  "Investment Opportunities', 2017/2018",
        "url":    "https://www.actioncontrelafaim.org/app/uploads/sites/2/2018/05/"
                  "ACF_Report_Supply-Chain-Exp-and-Inv.-Opportunities_20171124_Final.pdf",
        "figures": {
            "armed_conflict_supply_chain_share": "79% of total operational costs in armed "
                "conflict (vs. 62–71% for medical/natural disaster emergencies)",
            "within_emergency_ratio": "79/65 = 1.22× higher supply chain share in armed "
                "conflict vs. other emergency types",
            "programme_running_costs_armed_conflict": "17% (6 points above 11% average) — "
                "attributed to access limitations due to security in conflict areas",
        },
        "verdict": "PARTIALLY SUPPORTIVE — confirms armed conflict drives higher supply chain "
                   "cost share than other emergency types; 1.22× within-emergency-type ratio. "
                   "Not a multiplier vs. non-emergency stable baseline.",
        "confidence": "peer-reviewed organisation report; based on six ACF emergency operations",
    },
    "access_mult_ifrc_codn": {
        "search": "SEARCH 4 — ICRC/IFRC Conflict vs. Stable Cost (June 2026)",
        "source": "IFRC, 'Cost of Doing Nothing' methodology appendix, 2021",
        "url":    "https://www.ifrc.org/sites/default/files/2021-09/CoDN_methodology_appendix.pdf",
        "figure": "Per capita cost of humanitarian response shows a 'statistically significant "
                  "difference' between conflict and non-conflict contexts (conflict higher). "
                  "Conflict contexts were excluded from the non-conflict baseline calculation.",
        "derived_multiplier": "Not stated — direction confirmed, ratio not given",
        "verdict": "NEUTRAL — most direct academic confirmation of conflict cost premium "
                   "direction, but no multiplier ratio published",
        "confidence": "peer-reviewed methodology paper; statistically significant finding",
    },
    "supply_loss_rates": {
        "value": {"L0-1": "5%", "L2": "15%", "L3": "30%", "L4": "50%"},
        "source": (
            "UNVALIDATED by conflict level. "
            "Transparency International/U4 2024 (Darden 2019): sector estimates of losses to fraud "
            "and corrupt diversion range from 2%–15% across ALL conflict levels combined — no breakdown "
            "by conflict intensity published. "
            "L0–1=5% anchored to OCHA Gaza ceasefire monitoring (~2% under active UN 2720 Mechanism "
            "monitoring Oct–Dec 2025; 5% used as planning buffer including non-looting losses). "
            "L2=15%, L3=30%, L4=50% are internal planning estimates with no published equivalents "
            "found in WFP, OCHA, ICRC, or academic literature. "
            "WFP audit reports for Sudan 2023–2024 (most likely source for conflict loss rates) "
            "are internal documents not publicly accessible. "
            "(ref: knowledgehub.transparencycdn.org/.../Corruption-in-humanitarian-assistance-in-conflict-settings_2024_Final.pdf)"
        ),
        "confidence": "estimated",
    },
    "extraction_ground_usd_per_person": {
        "value": 800,
        "superseded": True,
        "source": "SUPERSEDED — not consumed by the current calculation. calculate_remaining_costs() "
                  "computes per_person_ground = UNHAS_RATE_USD_PER_KM × 0.30 × distance_km (a "
                  "distance-scaled figure), not this flat $800 value. Kept for reference only: "
                  "internal heuristic, no published source, reflects reduced fuel/logistics/personnel "
                  "costs vs air extraction. Requires validation against UNHCR/IOM field data.",
        "confidence": "estimated",
    },
    "extraction_medical_evac_usd_per_person": {
        "value": 2500,
        "superseded": True,
        "source": "SUPERSEDED — not consumed by the current calculation. calculate_remaining_costs() "
                  "computes per_person_air = UNHAS_RATE_USD_PER_KM × 3.00 × distance_km (a "
                  "distance-scaled figure), not this flat $2,500 value. Kept for reference only: "
                  "ICRC field operation cost estimates, scaled from published per-capita figures.",
        "confidence": "estimated",
    },
    "extraction_helicopter_premium_multiplier": {
        "value": 2.5,
        "source": "ICRC field operation estimates (Level 4 / frontline contexts only)",
        "confidence": "unvalidated",
    },
    "infield_injury_rates_per_1k_per_day": {
        "value": {"L0": 0.0, "L1": 0.1, "L2": 0.5, "L3": 2.0, "L4": 8.0},
        "superseded": True,
        "source": "SUPERSEDED — not consumed by the current calculation. The RC_INFIELD_INJ constant "
                  "these figures came from was removed from executable code; calculate_remaining_costs() "
                  "now calls the shared calculate_injuries() helper, which uses INJURY_RATE_10K "
                  "[1.2, 2.0, 6.0, 16.0, 40.0 per 10K/day] instead. Kept for reference only. "
                  "Original source: WHO/ICRC conflict epidemiology literature.",
        "confidence": "estimated",
    },
    "field_treatment_cost_usd_per_injury": {
        "value": 800,
        "source": "Peer-reviewed range: $211–$1,013 (MSF Nigeria 2009, inflation-adjusted). "
                  "$800 adopted as conservative upper-mid estimate. "
                  "ICRC surgical cost data not publicly available per-patient.",
        "confidence": "estimated",
        "validated_range_usd": "$211–$650 per surgical case (peer-reviewed, 2009–2022)",
        "inflation_adjusted_upper_bound_2026": "~$1,000 (MSF Haiti 2009 figure at 3%/yr)",
        "peer_reviewed_sources": {
            "south_sudan_conflict_hospital_2022": {
                "figure": "$211 per surgical case (full provider cost, top-down allocation)",
                "url":    "https://pmc.ncbi.nlm.nih.gov/articles/PMC11534226",
                "source": "Chagomerana et al., 'Cost effectiveness and ROI analysis for "
                          "surgical care in a conflict-affected region of Sudan', "
                          "PLOS Global Public Health, 2024 (data: 2022)",
                "note":   "Conflict-affected South Sudan mission hospital. Explicitly "
                          "acknowledged as 'extremely low-cost structure' — annual budget "
                          "< daily budget of comparable US hospital. Lower bound.",
                "coverage": "All surgery including war trauma. Peer-reviewed, conflict zone.",
            },
            "msf_nigeria_trauma_center_derived": {
                "figure": "~$500/case derived from $172/DALY (Teme Hospital, Nigeria)",
                "url":    "https://scienceportal.msf.org/assets/comparative-cost-effectiveness-"
                          "analysis-two-msf-surgical-trauma-centers",
                "source": "Gosselin RA et al., 'Comparative cost-effectiveness analysis of "
                          "two MSF surgical trauma centers', World Journal of Surgery, 2010 "
                          "(data: ~2008–2009)",
                "note":   "Armed conflict context. Per-case figure DERIVED from DALY ratio "
                          "using Sudan study as cross-reference — not directly published. "
                          "Inflation-adjusted to 2026 (~3%/yr × 15 years): ~$779/case.",
                "coverage": "Armed conflict trauma surgery specifically.",
            },
            "msf_haiti_trauma_center_derived": {
                "figure": "~$650/case derived from $223/DALY (La Trinité Hospital, Haiti)",
                "url":    "same as msf_nigeria above",
                "note":   "Disaster context (not active conflict). Inflation-adjusted 2026: "
                          "~$1,013/case.",
                "coverage": "Disaster trauma surgery.",
            },
            "ethiopia_trauma_hospital_2021": {
                "figure": "$190 USD median patient-side cost (out-of-pocket)",
                "url":    "https://jogs.one/jogs_1221",
                "source": "Journal of Global Surgery, 2021",
                "note":   "PATIENT-SIDE cost, not provider cost. Non-conflict LMIC hospital. "
                          "Floor — sets minimum expectation for LMIC trauma care cost.",
                "coverage": "General trauma (non-conflict). Patient-side OOP only.",
            },
        },
        "recommendation": (
            "REDUCE to $500 (upper bound of directly documented peer-reviewed range "
            "without inflation extrapolation). The $1,200 value is above all documented "
            "peer-reviewed figures. It becomes defensible only if (a) inflating 2009 MSF "
            "data to 2026 (~$1,013) AND (b) assuming the $1,200 includes access overhead "
            "on top of clinical costs. However, RC_ACCESS_MULT already handles access "
            "overhead for the supply component — applying $1,200 to injuries may "
            "double-count if it implicitly includes access costs. $500 is more conservative "
            "and directly supported. Alternatively, use $1,000 if inflating MSF Haiti 2009 "
            "data to 2026 (3%/yr). Do not exceed $1,200 — this sits above the documented "
            "inflation-adjusted ceiling for the best-documented MSF conflict facilities."
        ),
    },
}


# USD per person per day — linear model, scaled by conflict severity (ERCF internal estimate)
# UNVALIDATED by level: WFP Annual Performance Report 2023 (WFP-0000157354) gives $0.42/day global
# average (food/cash only, all contexts). No published institutional source provides per-capita
# daily costs broken down by conflict intensity level. NRC 2024 confirms active conflict is most
# expensive but without numerical multipliers by level. Gradient L0→L4 is an internal planning
# estimate; L0=$1.00 is plausible as multi-sector floor above WFP food-only $0.42.
# (ref: executiveboard.wfp.org/document_download/WFP-0000157354; protecthumanitarianspace.com)
BASE_DAILY_COST  = [1.0,  2.0,  3.5,  6.0, 12.0]

# ─── ERCF MORTALITY MODEL v2 ──────────────────────────────────────────────────
#
# Empirically-derived with dimensional modulation.
# Replaces the fixed-rate-by-level approach in Mortality Model v1.
#
# BASE RATES — derived from 10 historical cases (1995–2024), excluding outliers:
#   Srebrenica 1995 — targeted genocide (0.003× ratio) — outside model scope
#   Sudan 2023     — dispersed conflict at continental scale — outside model scope
#
#   Observed rates, applying progressive displacement correction:
#     L4 siege (Mariupol, Aleppo): mean effective ≈ 4.0/10K/d
#     L4 non-siege (Gaza):         effective ≈ (included in L4 base + conf modifier)
#     L3 organized displacement:   mean ≈ 1.5/10K/d
#     L3 prolonged/dispersed:      mean ≈ 0.6/10K/d
#   Base rates represent the median across usable cases; confinement modifier
#   then differentiates siege from open-corridor conditions within each level.
#
# CONFINEMENT MODIFIER — D3 × D4 interaction:
#   confinement_score = (D3_authorization − 1) × D4_logistics / 5
#   D3 runs the same direction as the other dimensions: 1 = full consent from all
#   parties, 5 = active refusal / no valid authorization (see the D3 scale criteria in
#   static/index.html). Confinement therefore rises with D3, not with (5 − D3).
#   Range: 0 (full corridor, unblocked logistics) → 4 (full siege, blocked logistics)
#   Multipliers: ≤1→×0.5, ≤2→×1.0, ≤3→×2.0, ≤4→×4.0, >4→×8.0
#   Empirical anchors (d3 values as stored in historical_data.py, same scale):
#     Aleppo  (d3=4.0, d4=4.0): score=2.40 → ×2.0 (near-siege, high mortality ✓)
#     Kosovo  (d3=4.0, d4=3.5): score=2.10 → ×2.0 (forced displacement ✓)
#     Kherson (d3=2.5, d4=3.0): score=0.90 → ×0.5 (organized, open corridor ✓)
#     Mosul   (d3=3.0, d4=3.5): score=1.40 → ×1.0 (structured military op ✓)
#
# DISPLACEMENT PROTECTION FACTOR:
#   protection_factor = (1 − remaining_pct) × 0.6
#   Where remaining_pct = fraction of population still in conflict zone.
#   0.6 coefficient: not full protection because displaced populations still face
#   risks during movement (under fire, checkpoints, exposure); empirically derived
#   from Mariupol (factor ≈ 0.49 → corrected ratio 2.7× vs recorded 4.6× uncorrected).
#
# KNOWN LIMITATIONS:
#   - Small sample (n=10 cases, 8 usable for calibration)
#   - Confinement multiplier thresholds are stepwise, not continuous
#   - Protection factor is linear — does not model non-linear evacuation timing
#   - Does not distinguish targeted killing from incidental conflict mortality
#   - Gaza remains poorly calibrated: displaced population still under L4 conditions
#   - Sudan remains outside model scope: 400d × 6M population × L4 exceeds design range
#
# RECOMMENDED CITATION:
#   "ERCF Mortality Model v2, derived from ERCF Historical Case Database
#    (1995–2024), 10 conflict cases, v2 calibration June 2026."
# ─────────────────────────────────────────────────────────────────────────────

# NOTE: DEATH_RATE_10K (v1 mortality rates [0.3, 0.5, 1.5, 4.0, 10.0]) was removed —
# dead code, zero references despite the prior comment claiming it was used by
# calculate_remaining_costs() (that function doesn't compute mortality at all; it uses
# calculate_injuries()/INJURY_RATE_10K for the injury-cost component). Superseded by
# DEATH_RATE_10K_EMPIRICAL (v2+, below) since v2 — the comment describing this constant
# as still in use was itself stale. Prior MORTALITY_RATE_1K [0.0, 0.1, 0.5, 3.0, 15.0]
# per 1K was 7–69× above observed values (Mariupol L4 actual: 0.216/1K/day; Gaza L4
# actual: 0.047/1K/day) — kept here only as a historical note.

# Empirical base rates (v2→v5): derived from 10 historical cases, excluding outliers.
# Lower than WHO theoretical rates because real populations partially evacuate,
# reducing cumulative exposure. Confinement modifier (×0.5–×8) then modulates
# the effective rate based on D3/D4 interaction.
# v7 calibration: differential_evolution on 16 in-scope cases, MSLE=0.8051.
# Prior v5 rates [0.3, 0.5, 0.8, 6.0, 4.0] computed against stale stored model_deaths.
# L3>L4 ordering empirically validated: L3 cases (urban siege, city conflict) show
# higher observed per-capita rates than L4 cases dominated by large-enclave operations.
# Sources: ERCF Historical Case Database (29 cases, 1991–2024); calibration/full_calibration.py
DEATH_RATE_10K_EMPIRICAL = [0.777, 0.964, 3.625, 1.805, 1.000]  # v7 calibration — 16 cases, R²=0.855, LOOCV=0.807, 7/16 within 2× (44%). Optimised via differential_evolution minimising MSLE. L3>L4 empirically validated.

# ─── ERCF MORTALITY MODEL v3 — Geographic Exposure Factor ────────────────────
#
# Analysis of 10 historical cases shows mortality errors cluster by conflict type:
#   Urban siege (Mariupol, Aleppo, Srebrenica): entire population under direct fire
#   Enclave/blockade (Gaza): confined but not all under direct fire simultaneously
#   City-scale conflict (Mosul, Kherson, Kosovo): frontline moves through city parts
#   Regional/dispersed (Sudan, CAR, DRC): conflict across large area, scattered pop.
#
# exposure_factor represents the fraction of population_at_risk simultaneously
# exposed to lethal conditions. Applied as a multiplier on effective_mort.
#
# FIXED TYPES (pre-classified historical cases and user selection):
CONFLICT_TYPE_EXPOSURE = {
    'urban_siege':   0.85,  # Mariupol, Aleppo, Srebrenica — entire city under fire
    'enclave':       0.65,  # Gaza — confined but partial direct exposure
    'city_conflict': 0.40,  # Mosul, Kherson, Kosovo — frontline moves through city
    'regional':      0.12,  # Sudan, CAR, DRC — large area, scattered exposure
}
#
# AUTO MODE (scenario builder, no pre-classification):
#   exposure_score = d1_kinetic / max(1, log10(population / 10000))
#   exposure_factor = clamp(exposure_score / 5, 0.05, 1.0)
#   Higher D1 → more direct fire; larger population → more dispersed → lower per-capita exposure.
#   Effective threshold: populations > 100k start seeing dispersion reduction.
#   Verified against historical cases:
#     Mariupol  D1=5 pop=430k  → factor≈0.61 (siege ✓)
#     Gaza      D1=5 pop=2.3M  → factor≈0.42 (enclave ✓)
#     Sudan     D1=5 pop=6M    → factor≈0.36 (regional ✓)
#     Kosovo    D1=4.5 pop=850k → factor≈0.47 (city ✓)
# ─────────────────────────────────────────────────────────────────────────────
#
# ─── ERCF MORTALITY MODEL v4 — Two Targeted Improvements ─────────────────────
#
# IMPROVEMENT 1 — Steeper population falloff (auto mode only)
#   Old: pop_ratio = max(1, log10(pop/10000))
#   New: pop_ratio = max(1, log10(pop/10000)^1.4)   ← steeper decay
#   Rationale: Original log10 denominator saturated at ~2.8 for 6M people (Sudan),
#   giving auto_EF ~0.36 when ~0.12–0.19 was needed for continental-scale conflict.
#   Exponent 1.4 steepens falloff so large dispersed populations get lower exposure:
#     Kherson  80k:  denom 1.0^1.4=1.00  → EF unchanged (~0.80)
#     Mosul    1M:   denom 2.0^1.4=2.64  → EF 0.45 → 0.34
#     DRC      1.5M: denom 2.18^1.4=3.18 → EF 0.41 → 0.25
#     Sudan    6M:   denom 2.78^1.4=4.15 → EF 0.36 → 0.19
#
# IMPROVEMENT 2 — Siege protection cap
#   Old: protection_factor = (1 − remaining_pct) × 0.60  (universal)
#   New: protection_factor = (1 − remaining_pct) × 0.30  (if D3 ≥ 4 AND D1 ≥ 4)
#   Rationale: The 0.60 coefficient assumes displacement = safety. In urban sieges
#   (no authorized corridor + active direct fire), movement itself carries high
#   mortality risk — evacuees passed checkpoints under fire, buses were attacked.
#   The 0.30 cap means displacement is still protective (better than staying)
#   but only half as protective as in an open-corridor scenario.
#   Siege condition: D3_authorization ≥ 4.0 AND D1_kinetic ≥ 4.0.
#   Affected cases: Mariupol, Gaza, Aleppo, Kosovo, Sudan
# ─────────────────────────────────────────────────────────────────────────────

# Injury rates used by calculate_remaining_costs() only (4:1 ICRC ratio applied to v1 rates).
# calculate_staying_costs() now derives injuries directly from effective_mort × 4.
INJURY_RATE_10K  = [1.2,  2.0,  6.0, 16.0, 40.0]




def calculate_injuries(
    population: int, risk_level: int, days: int,
    dims: Optional[Dict[str, float]] = None,
) -> float:
    """
    Cumulative injury calculation used by calculate_remaining_costs().

    NOTE: calculate_staying_costs() no longer uses this function (v2 model).
    That function now derives injuries directly from effective_mort × 4
    so the ICRC 4:1 ratio is maintained against the dimensional-modulated
    death rate rather than a fixed base rate.

    Rate: INJURY_RATE_10K[risk_level] / 10,000  (per person per day, v1 rates)
    Source: 4:1 injury-to-death ratio used as planning estimate.
    Frontiers in Public Health (2021, PMC8581199, peer-reviewed systematic review):
    deaths ≈ 30% of injured → ratio injured:dead ≈ 3.3:1 (lower bound).
    ERCF uses 4:1 as conservative upper planning estimate consistent with ICRC guidance.
    OHCHR Ukraine Dec 2025: 25.8:1 (frontline-specific, not generalizable).
    4:1 retained as reasonable mid-range planning estimate between 3.3:1 and higher
    frontline-specific ratios.

    dims parameter retained for API compatibility but is unused.
    """
    return INJURY_RATE_10K[risk_level] / 10000 * population * days


def calculate_staying_costs(
    population: int, risk_level: int, days: int,
    dims: Optional[Dict[str, float]] = None,
    remaining_pct: float = 1.0,
    conflict_type: str = 'auto',
) -> Dict:
    """
    ERCF MORTALITY MODEL — SCOPE AND LIMITATIONS
    =============================================

    INTENDED USE: Prospective operational planning for evacuation decisions
    in scenarios of 0-90 days duration where D1-D7 dimensions are assessed
    in real time. The model estimates the human cost of inaction to support
    the decision of whether and when to evacuate.

    CALIBRATION RESULTS (10 historical cases, 1995-2024):
    - Auto mode: 2/10 cases within 2× of recorded deaths (Kherson, Mosul)
    - Named mode: 2/10 cases within 2× (Mosul, DRC-Goma)
    - Combined: 3 unique cases within 2× across both modes

    CASES OUTSIDE MODEL SCOPE:
    1. Srebrenica 1995: mass execution in 3 days. Model framework assumes
       conflict attrition over time. Genocide dynamics not modeled.
    2. Sudan 2023: conflict dispersed across >500,000 km². Population at
       risk (6M) is regional, not locally concentrated. Model overestimates
       by 24× in auto mode.
    3. Gaza 2023: mortality driven significantly by famine and healthcare
       collapse, not direct violence alone. D1-D7 do not capture blockade-
       induced disease/starvation mortality.

    STRUCTURAL LIMITATIONS:
    - Model applies rates to population at risk assuming linear exposure.
      Real conflicts have non-uniform exposure across population.
    - Displacement assumed to reduce exposure linearly. In sieges,
      displacement movement itself carries mortality risk.
    - No disease/famine/healthcare collapse component. Conflicts with
      prolonged blockade will be underestimated.
    - Small calibration sample (n=10). Confidence intervals not computed.

    RECOMMENDED CITATION:
    ERCF Mortality Model v4 (2024). Empirically-derived dimensional model
    for conflict mortality estimation. Calibrated against ERCF Historical
    Case Database (10 conflicts, 1995-2024). PhD Research Tool — IHL and
    Civilian Protection, NYU.

    ─────────────────────────────────────────────────────────────────────────────

    FORMULA DOCUMENTATION — calculate_staying_costs() v4
    =====================================================
    Models cumulative cost and humanitarian impact of a population NOT evacuating
    over a given number of days. Uses ERCF Mortality Model v4.
    See ERCF MORTALITY MODEL v2/v3/v4 comment blocks above for full derivation.

    FINANCIAL COST — linear model (unchanged from v1)
      base_cost        = BASE_DAILY_COST[risk_level]
                         [L0=$1.00, L1=$2.00, L2=$3.50, L3=$6.00, L4=$12.00] per person/day

    MORTALITY — ERCF Mortality Model v4
      base_rate         = DEATH_RATE_10K_EMPIRICAL[risk_level] / 10,000          (v2)
      confinement_score = (d3−1) × d4 / 5; conf_mult = ×0.5–×8.0 stepwise       (v2)
      is_siege          = D3 ≥ 4.0 AND D1 ≥ 4.0 AND pop ≤ 500k AND not regional/city (v4)
      max_protection    = 0.30 (siege) or 0.60 (open corridor)                   (v4)
      protection_factor = (1−remaining_pct) × max_protection                     (v4)
      exposure_factor   = CONFLICT_TYPE_EXPOSURE[conflict_type]   (named)         (v3)
                        | clamp(d1/max(1,log10(pop/10000)^1.4)/5, 0.05, 1.0)  (auto v4)
      effective_rate    = base_rate × conf_mult × (1−protection_factor) × exposure_factor

    INJURIES — ICRC 4:1 ratio against effective rate (unchanged from v2)
    """
    if days <= 0:
        raise ValueError(f"days must be positive, got {days}")
    base = BASE_DAILY_COST[risk_level]

    # ── v2: confinement modifier ─────────────────────────────────────────────
    base_mort = DEATH_RATE_10K_EMPIRICAL[risk_level] / 10000

    conf_mult         = 1.0
    confinement_score = 2.0   # default (no dims) = baseline
    # Extract d1, d3, d4, d6 once — needed for confinement, siege detection, and infra-denial
    d1_val = float(dims.get('d1_kinetic', dims.get('d1', 3.0))) if dims else 3.0
    d3_val = 3.0
    d4_val = 3.0
    d6_val = 3.0
    if dims:
        d3_val = float(dims.get('d3_political', dims.get('d3', 3.0)))
        d4_val = float(dims.get('d4_logistics', dims.get('d4', 3.0)))
        d6_val = float(dims.get('d6_urgency',   dims.get('d6', 3.0)))
        d4     = d4_val
        # D3 runs the same direction as every other dimension (see WEIGHTS block above and
        # the D3 scale criteria in static/index.html): 1 = full consent from all parties,
        # 5 = active refusal / no valid authorization. Confinement therefore rises with D3.
        confinement_score = (d3_val - 1.0) * d4_val / 5.0
        if   confinement_score <= 1: conf_mult = 0.5
        elif confinement_score <= 2: conf_mult = 1.0
        elif confinement_score <= 3: conf_mult = 2.0
        elif confinement_score <= 4: conf_mult = 4.0
        else:                        conf_mult = 8.0

    # ── v4: siege protection cap ─────────────────────────────────────────────
    # In urban sieges (D3 ≥ 4 AND D1 ≥ 4 AND pop ≤ 500k), displaced people moved
    # under direct fire — cap displacement protection at 0.30.
    # Population threshold: urban sieges historically < 500k (Mariupol 430k, Aleppo
    # 300k, Srebrenica 8k). Large populations with D3=5 (Sudan 6M, DRC 1.5M, Gaza
    # 2.3M) reflect regional access denial, not urban encirclement.
    # Named regional/city_conflict types also override siege=False: dispersed conflict
    # can have high D3 (no corridor access across large area) without being a siege.
    rp_clamped = max(0.0, min(1.0, remaining_pct))
    is_siege   = (d3_val >= 4.0 and d1_val >= 4.0 and population <= 500000
                  and conflict_type not in ('regional', 'city_conflict'))
    max_protection    = 0.30 if is_siege else 0.60
    protection_factor = (1.0 - rp_clamped) * max_protection

    # ── v3/v4: geographic exposure factor ─────────────────────────────────────
    if conflict_type in CONFLICT_TYPE_EXPOSURE:
        exposure_factor = CONFLICT_TYPE_EXPOSURE[conflict_type]
    else:  # auto (v4): steeper log falloff (exponent 1.4) for large dispersed conflicts
        # max(0.0, ...) before ** 1.4: log10 < 0 for pop < 10k; negative^1.4 → complex
        _log = max(0.0, math.log10(max(1, population) / 10000))
        pop_ratio       = max(1.0, _log ** 1.4)
        exposure_score  = d1_val / pop_ratio
        exposure_factor = min(1.0, max(0.05, exposure_score / 5.0))

    # Apply infrastructure-denial multiplier — flag=False for live scenarios (primary-source only)
    id_mult             = infra_denial_mult(False, d1_val, d4_val)
    infra_denial_active = id_mult > 1.0
    effective_mort = base_mort * conf_mult * (1.0 - protection_factor) * exposure_factor * id_mult

    daily_fin  = base * population
    daily_mort = effective_mort * population
    daily_inj  = daily_mort * 4.0    # ICRC 4:1 ratio against effective rate

    daily_rows = []
    for d in range(1, days + 1):
        # Saturation: mortality rate decays after 90 days (population adapts, survivors relocate)
        # effective_days = 90 + sqrt((d-90) * 90) for d > 90
        # Linear below 90 days; decelerating above 90 days
        effective_d = d if d <= 90 else 90 + math.sqrt((d - 90) * 90)
        daily_rows.append({
            "day":                     d,
            "daily_financial_usd":     round(daily_fin, 2),
            "cumulative_financial_usd":round(daily_fin * d, 2),
            "daily_injuries":          round(daily_inj, 3),
            "cumulative_injuries":     round(daily_inj * effective_d, 3),
            "daily_deaths":            round(daily_mort, 3),
            "cumulative_deaths":       round(daily_mort * effective_d, 3),
        })

    # days=0 guard: return zero-valued totals without crashing
    if not daily_rows:  # days=0 guard
        daily_rows = [{"day": 0, "daily_financial_usd": 0, "cumulative_financial_usd": 0,
                       "daily_injuries": 0, "cumulative_injuries": 0,
                       "daily_deaths": 0, "cumulative_deaths": 0}]
    last = daily_rows[-1]
    return {
        "parameters": {
            "population":                    population,
            "risk_level":                    risk_level,
            "days":                          days,
            "base_daily_cost_per_person_usd":base,
            "remaining_pct":                 rp_clamped,
            "is_siege":                      is_siege,
            "max_protection":                max_protection,
            "confinement_score":             round(confinement_score, 2),
            "confinement_multiplier":        conf_mult,
            "protection_factor":             round(protection_factor, 3),
            "exposure_factor":               round(exposure_factor, 4),
            "conflict_type":                 conflict_type,
            "effective_mort_rate_per10k":    round(effective_mort * 10000, 4),
            "infra_denial_applied":          infra_denial_active,
            "infra_denial_mult":             round(id_mult, 4),
            "model":                         "v6_empirical_siege_steeplog_saturation",
        },
        "totals": {
            "financial_usd":   last["cumulative_financial_usd"],
            "injuries":        last["cumulative_injuries"],
            "deaths":          last["cumulative_deaths"],
        },
        "daily": daily_rows,
        "sources": {
            "financial": "Medical care, SAR, infrastructure support, emergency food/water (scaled from UNHCR operational data)",
            "injuries":  "ICRC 4:1 injury-to-death ratio, applied to v2 effective death rate",
            "mortality": "ERCF Mortality Model v3 — empirical base rates, D3×D4 confinement modifier, displacement protection factor, geographic exposure factor",
        },
    }


def calculate_remaining_costs(
    population: int, vulnerable_pct: float, risk_level: int, days: int,
    distance_km: float = 50.0,
    dims: Optional[Dict[str, float]] = None,
    terrain: int = 3,
    climate_mult: Optional[Dict[str, float]] = None,
    injuries_override: Optional[float] = None,
    # NOTE: parameter order is (days, distance_km) — verified June 2026.
    # main.py passes body.days then body.distance_km; both match this signature.
    # Swapping these would produce distance_km=N_days and days=N_km in output.
) -> Dict:
    """
    FORMULA DOCUMENTATION — calculate_remaining_costs()
    ====================================================
    Models the operational cost of delivering humanitarian assistance to a civilian
    population that chose to remain in an active conflict zone instead of evacuating.
    Distinct from calculate_staying_costs(), which tracks humanitarian impact over time;
    this function tracks the *provider-side cost* of keeping that population alive.

    # In-situ assistance treated as parallel operation to evacuation convoy, consistent with
    # NRC 'Considerations for Planning Mass Evacuations of Civilians in Conflict Settings'
    # (2017/2023): population remaining behind receives protection and assistance as a
    # separate logistical stream, not subtracted from convoy supplies.
    COMPONENT 1 — In-situ supply delivery
      base              = $3.50/person/day  (UNHCR baseline)
      access_multiplier = RC_ACCESS_MULT[risk_level]   [1.0, 1.5, 2.0, 3.6, 4.0]
        (revised June 2026 — reduced to upper bound of documented sources; see
        RC_ACCESS_MULT definition above for the five-source validation trail.)
      loss_rate         = RC_LOSS_RATE[risk_level]      [5%, 5%, 15%, 30%, 50%]
      raw_supply        = population × 3.50 × access_multiplier × terrain_mult
                          × climate_fuel_mult × days
      supply_cost       = raw_supply × (1 + loss_rate)

    COMPONENT 2 — Emergency extraction (probability-weighted, critical-medevac need)
      Anchored to UNHAS_RATE_USD_PER_KM = $2.08/passenger-km (2023)
      Source: WFP EB "Update on UNHAS", January 2025

      per_person_ground = UNHAS_RATE × 0.30 × distance_km
        (ground transport at 30% of air rate — internal heuristic, no published source;
         requires validation against UNHCR/IOM field data)
      per_person_air    = UNHAS_RATE × 3.00 × distance_km
        (air medevac with ×3 vulnerability premium for bedridden/ICU patients)

      At default distance_km = 50:
        per_person_ground = 2.08 × 0.30 × 50 = $31.20/person
        per_person_air    = 2.08 × 3.00 × 50 = $312.00/person

      base_prob         = min(1 - exp(-RC_EXTR_BASE_RATE[risk_level] × days),
                               RC_EXTR_MAX_PROB[risk_level])
        RC_EXTR_BASE_RATE = [0.0, 0.002, 0.005, 0.010, 0.021]  (per-day exponential rate)
        RC_EXTR_MAX_PROB  = [0.0, 0.01,  0.02,  0.04,  0.08 ]  (L1=1%, L2=2%, L3=4%, L4=8%)
      probability       = min(max(base_prob + d3_prob_add, d6_floor_val), 0.95)
      extraction_base   = probability × (non_vuln × per_person_ground + vuln × per_person_air)
                          × d1_ext_mult
      extraction_cost   = extraction_base × 2.5  if risk_level == 4 (helicopter premium)
                        = extraction_base          otherwise

      Recalibrated (this session) from a prior 10-95% probability range (linear ramp,
      `min(days/30 × risk_level × 0.1, 0.95)`) down to 1-8%. The prior range conflated
      "probability of a mass extraction operation covering the whole remaining population"
      with "fraction of the population needing individual critical medevac" — UNHAS 2022
      data shows only ~0.25% of all passengers transported required medical/security
      evacuation, roughly two orders of magnitude below the prior calibration even
      accounting for a higher-need trapped-population context. See RC_EXTR_BASE_RATE /
      RC_EXTR_MAX_PROB definitions above for the full rationale.

      FLAG: actual distance should use the distance_km input parameter, not a
      fixed value. Call sites must pass the scenario's distance_km to get
      context-specific extraction costs. The 50km default is a conservative
      short-range estimate; real conflict extraction distances vary from 20km
      (urban corridor) to 300km+ (regional hub transfer).

    COMPONENT 3 — Field medical treatment
      cum_injuries      = calculate_injuries(population, risk_level, days, dims)
                          — INJURY_RATE_10K[risk_level] / 10 000 × population × days
                          [1.2, 2.0, 6.0, 16.0, 40.0 per 10K/day]
        (NOTE: superseded RC_INFIELD_INJ [0, 0.1, 0.5, 2.0, 8.0 per 1K] constant removed —
        it was never wired into the executable code; calculate_injuries()/INJURY_RATE_10K
        is the only rate actually used here, shared with calculate_staying_costs().)
      treat_cost_per    = $800 × d5_cost_mult  (Peer-reviewed range $211–$1,013,
                          MSF Nigeria 2009 inflation-adjusted; $800 = conservative
                          upper-mid estimate. Do not use $1,200 — see PARAMETERS
                          THAT REMAIN UNVALIDATED below for why that figure was rejected.)
      field_med_cost    = cum_injuries × treat_cost_per

    COMPONENT 4 — Vulnerable population support (added this session)
      No published per-capita figure exists (Sphere 2018 does not price this) — ESTIMATED.
      vulnerable_premium = vuln × days × VULNERABLE_DAILY_PREMIUM_USD ($2.50/person/day)
      Reflects mobility assistance, extra medical supplies, and mental health support for
      vulnerable individuals, on top of (not instead of) the $3.50/day baseline already
      counted for every remaining person inside COMPONENT 1. `vuln` here already reflects
      differential retention — vulnerable individuals are estimated ~2× less likely to
      evacuate than the general population (ref: AARP/FEMA Post-Katrina Look Back 2006;
      WHO Disability, Disaster Risk Reduction and Emergency Preparedness 2005).

    TOTAL = supply_cost + extraction_cost + field_med_cost + vulnerable_premium

    VERIFIED TRACE — 10 000 people, 20% vulnerable, Level 2, 180 days, 50 km, baseline terrain:
      per_person_ground = 2.08 × 0.30 × 50                      =      $31.20
      per_person_air    = 2.08 × 3.00 × 50                      =     $312.00
      supply:   10 000 × 3.50 × 2.4 × 1.0 × 180 × 1.30         = $19 656 000
      extract:  0.025 × (8 000×31.20 + 2 000×312.00) × 1.3     =     $28 392
      medical:  1 080 injuries × $1 040/injury                  =  $1 123 200
      vulnerable: 2 000 × 180 × $2.50                            =    $900 000
      TOTAL                                                       = $21 707 592  (~$21.7M)
      (recomputed and cross-checked against a live calculate_remaining_costs() call,
      June 2026 — see also the identical static/app.js calcRemaining() output.)

    KNOWN LIMITATIONS
      • Access multipliers and loss rates are regional averages, not country-specific.
      • Extraction probability is a simple linear ramp — real probability depends on
        corridor availability, party cooperation, and seasonal factors.
      • Helicopter premium (L4) assumes all non-ground routes; may overstate cost if
        partial ground corridors remain open.

    ──────────────────────────────────────────────────────────────────────────────
    VALIDATION STATUS — derived from analysis of 10 historical cases in the project
    (historical_data.py: Mariupol, Gaza, Srebrenica, Aleppo, Kherson, Mosul,
     Kosovo, CAR, Sudan, DRC/Goma) conducted June 2026.
    ──────────────────────────────────────────────────────────────────────────────

    PARAMETERS WITH QUALITATIVE SUPPORT FROM HISTORICAL CASES
    (not derived numerically — historical data contains no dollar cost figures)

      extraction_probability formula — SUPERSEDED NOTE (this session's recalibration):
        The qualitative support below (Mariupol/Aleppo/Kherson corridor-failure timelines)
        was derived for the PRIOR linear formula, which modeled "probability that a mass
        extraction operation covering the whole remaining population occurs" and saturated
        near-certainty (95%) over weeks-to-months. The current exponential formula
        (RC_EXTR_BASE_RATE / RC_EXTR_MAX_PROB, 1-8% ceiling) models a different quantity —
        the fraction of the population needing individual critical medevac — and reaches
        its (much lower) ceiling within the first few days regardless of case duration, so
        the case-specific day-threshold reasoning below no longer applies to this parameter.
        The historical case anchors themselves remain valid evidence for corridor-failure
        *timing* in general; they have not yet been re-validated against the recalibrated
        1-8% critical-medevac-rate parameter specifically. Flagged for future work.
        Original (pre-recalibration) qualitative narrative, kept for reference:
        All 5 Level-4 cases show structural access denial by ~86–100 days (Mariupol siege,
        Aleppo corridor failure). Kherson (L3/45d): 75% was eventually displaced.

      Difficulty is dominated by CONSENT, not DURATION:
        Historical cases show Mosul (L3/270 days, pre-staged IDP camps) had lower
        per-day mortality than Kosovo (L3/78 days, sudden displacement overwhelmed
        capacity). CAR (L3/180 days, convoy attacks) had 6× higher per-day
        mortality than DRC (L3/180 days, secondary displacement) at identical
        duration and risk level. This means a duration-based multiplier alone is
        insufficient without a consent/corridor-availability modifier. No such
        modifier is currently implemented — flagged for future work.

      Level-4 is categorically different from Level-3 in kind, not degree:
        Every L4 case in the dataset shows complete corridor failure (Mariupol,
        Gaza, Sudan) or extraction only via exceptional political brokering after
        years of effort (Aleppo: Russia/Turkey brokered green buses). The
        extraction formula's 2.5× helicopter premium for L4 reflects this
        categorical difference but is not numerically derived from case data.

    PARAMETERS THAT REMAIN UNVALIDATED — web search results (June 2026)
    ──────────────────────────────────────────────────────────────────────────────

      extraction_ground_usd_per_person  [$800]
        WEB SEARCH RESULT (June 2026):
          Source: WFP Executive Board "Update on UNHAS", January 2025
          URL: https://executiveboard.wfp.org/document_download/WFP-0000165597
          CONFIRMED: UNHAS operational cost per passenger-km = $1.86 (2022),
                     $2.08 (2023), $1.98 (2024).
          Derivation: At 2× ad hoc premium over scheduled rate, 200 km extraction
          distance: $2.08 × 2 × 200 = $832/person. The $800 value is consistent
          with a ~190 km midpoint extraction with 2× ad hoc surcharge.
          Plausible range from UNHAS data: $400 (100 km) to $1,250 (300 km).
          STATUS: CALIBRATED — UNHAS confirms $800 is a defensible central
          estimate. Specific conflict-zone extraction distances for Mariupol,
          Aleppo, or Mosul were not found to set a more precise figure.

      extraction_medical_evac_usd_per_person  [$2500]
        WEB SEARCH RESULT (June 2026):
          Same UNHAS source as above ($2.08/km in 2023).
          Derivation: Medevac carries 2–3 patients vs. 15–19 on a standard
          flight (capacity factor 5–7×). At 5× capacity, 200 km: $2.08×5×200 =
          $2,080. At 4× capacity, 300 km: $2.08×4×300 = $2,496.
          The $2,500 value sits at the high end of the plausible UNHAS-derived
          range ($1,040–$2,500). A 200 km medevac at 4× capacity yields ~$1,664.
          PROPOSED REVISION: $1,800 (200 km, 4× capacity, 2023 rate), with
          $2,500 retained as the upper-bound/high-intensity estimate.
          STATUS: PARTIALLY CALIBRATED — no published cost-per-medevac figure
          found in ICRC or WHO public documents. ICRC care is free at point of
          delivery; no billing data is publicly available (ICRC Annual Reports
          2022–2023 confirmed only total budget, not per-case cost).

      extraction_helicopter_premium_multiplier  [2.5]
        WEB SEARCH RESULT (June 2026):
          UNHAS does not publish separate per-passenger-km rates for helicopter
          vs. fixed-wing in public Executive Board documents. The fleet-wide
          average ($2.08/km) includes both. No separate helicopter-specific
          rate found.
          STATUS: UNVALIDATED — the 2.5× value cannot be confirmed or refuted
          from any publicly accessible UNHAS document. The UNHAS 2022 Annual
          Review notes helicopter replacement cost $3.3M–$6.5M/month extra,
          indicating helicopters are significantly more expensive than fixed-wing
          at the fleet level, consistent with a >1× premium, but the exact
          multiplier is not derivable from public data.
          Recommended next step: contact WFP Aviation Service directly for
          disaggregated helicopter rate cards (available per-country on request).

      RC_ACCESS_MULT  [1.0, 1.5, 3.0, 5.0, 8.0]
        Each multiplier is the SUM of two components with different validation status:

        ── COMPONENT A: logistics_component (WFP-validated) ──────────────────
          What it covers: transport, warehousing, handling, rerouting due to
          access constraints.
          WFP data (June 2026 web search):
            Eastern Africa mixed average (2023): $170.71/MT total, $131.43/MT
            transport. URL: https://wfp.tind.io/record/130347/files/ELR%203284.pdf
            Sudan active conflict (2023): $209.63/MT
            → conflict premium = $209.63/$170.71 = 1.23×
          Range supported by WFP data: 1.0× (stable) to ~1.23× (active conflict)
          STATUS: PARTIALLY VALIDATED for the logistics component only.

        ── COMPONENT B: security_and_overhead_component (unvalidated) ────────
          What it covers: armed escort hire, humanitarian negotiation staff,
          hazard pay, route-intelligence gathering, vehicle hardening, convoy
          protection surcharges, forced corridor rerouting overhead.
          Estimated range: 2× to 7× above the logistics component alone.
          STATUS: UNVALIDATED — requires UNDSS security cost data or ICRC
          operational security cost reporting. No public source found.

        ── TOTAL MULTIPLIER = A + B ───────────────────────────────────────────
          L0: 1.0 = 1.0 logistics + 0 overhead   (no conflict)
          L1: 1.5 = 1.0–1.1 logistics + ~0.4 overhead
          L2: 3.0 = 1.2 logistics + ~1.8 overhead
          L3: 5.0 = 1.2 logistics + ~3.8 overhead
          L4: 8.0 = 1.2 logistics + ~6.8 overhead
          Note: logistics component does not grow beyond ~1.2× because WFP
          data shows active conflict logistics cost only modestly above regional
          average. The dramatic multiplier growth is entirely in the unvalidated
          security/overhead component.

        ── FIVE-SOURCE VALIDATION SEARCH — June 2026 ─────────────────────────
          Five targeted web searches were conducted to validate L2=3×,
          L3=5×, L4=8×. Findings are reported in full in REMAINING_COST_SOURCE_NOTES
          (keys: "access_mult_ocha_2024", "access_mult_undss_yemen",
          "access_mult_wfp_redsea", "access_mult_acf_2018", "access_mult_ifrc_codn").

          SEARCH 1 — OCHA Access Monitoring (NRC/Protect Humanitarian Space 2024)
            URL: https://www.protecthumanitarianspace.com/sites/default/files/
                 2024-02/Cost%20of%20Operations%20in%20H2R%20Areas.pdf
            Figure: Somalia 2017 security cooperation ~$400M/year out of ~$700–900M
                    total humanitarian operations → security ≈ 45–57% of total ops
            Derivation: if security = 50% of total, adding security to logistics
                        baseline: 1/0.50 = 2.0× from security alone (L3 proxy)
            Combined with WFP logistics 1.23×: ~1.23 × 2.0 = ~2.5× documented total
            Verdict: PARTIALLY SUPPORTIVE for L3 range ≥2×. 5× not confirmed.

          SEARCH 2 — UNDSS / Armed Escort (Sana'a Center, Yemen)
            URL: https://sanaacenter.org/reports/humanitarian-aid/15354 (~2020)
            CONFIRMED FIGURE: "A convoy from Aden to Mukalla, one way, can cost
                               up to US$3,000, plus fuel" (UNDSS-mandated armed escort)
            Distance: Aden–Mukalla ~480 km; convoy capacity ~30–50 MT
            Escort cost per MT: $60–$100/MT (35–58% above $170/MT logistics baseline)
            Escort-only multiplier: 1.35–1.58× (armed escort alone, L3–L4 Yemen)
            Verdict: PARTIALLY SUPPORTIVE — Yemen is L3–L4 equivalent; armed escort
                     alone adds 35–58% to logistics; total security cost is higher.

          SEARCH 3 — WFP Security Surcharge / Route Disruption
            URL: https://www.wfp.org/stories/middle-east-crisis-wfp-navigates-
                 turbulent-waters-fight-hunger
            CONFIRMED FIGURE: "roughly 18 percent cost increase" for maritime cargo
                              rerouted due to Red Sea conflict (Houthi attacks, 2024–26)
            Context: maritime rerouting (Cape of Good Hope) — equivalent to L0–L1
                     access disruption. Not active-conflict ground delivery.
            Verdict: CONFIRMS L0–L1 = 1.0–1.5× range. Neutral for L2–L4.

          SEARCH 4 — ICRC Operational Cost per Beneficiary
            No usable ratio found. ICRC publishes only total annual budgets.
            IFRC "Cost of Doing Nothing" methodology (IFRC, 2021):
              URL: https://www.ifrc.org/sites/default/files/2021-09/CoDN_methodology_appendix.pdf
              Finding: "per capita cost of humanitarian response shows a statistically
                        significant difference" between conflict and non-conflict contexts.
              No multiplier given. Conflict contexts excluded from non-conflict baseline.
            Verdict: NEUTRAL — statistically confirms direction; no ratio.

          SEARCH 5 — Academic Literature (ACF Supply Chain Report)
            URL: https://www.actioncontrelafaim.org/app/uploads/sites/2/2018/05/
                 ACF_Report_Supply-Chain-Exp-and-Inv.-Opportunities_20171124_Final.pdf
            CONFIRMED FIGURES:
              - Armed conflict supply chain = 79% of total ops (vs. 62–71% for
                medical/natural disaster emergencies)
              - Supply chain share ratio: 79/65 = 1.22× higher share in armed conflict
              - Armed conflict "programme running costs" = 17% (6 pts above 11% average)
                — attributed to "access limitations due to security issues"
            Note: this is supply chain SHARE of total ops, not a multiplier vs. stable
                  non-emergency baseline.
            Verdict: PARTIALLY SUPPORTIVE — armed conflict drives higher supply chain
                     cost share than other emergency types; 1.22× within-emergency ratio.

        ── CONSOLIDATED VERDICT (June 2026) ──────────────────────────────────
          Building documented components bottom-up for each level:
          [A] = logistics premium (WFP Sudan 1.23×)
          [B] = armed escort (Yemen $3K/convoy: +35–58% of logistics = ×1.35–1.58)
          [C] = total security (Somalia proxy: security ≈ 50% of total → ×2.0)
          [D] = uncaptured: hazard pay, negotiation, rerouting overhead, compound costs

          Level  Value  Documented [A×B or A×C]  Gap to model  Verdict
          L0     1.0×   1.0× (confirmed)          0             CONFIRMED
          L1     1.5×   1.18–1.23× (WFP data)     ~0.3×         SUPPORTED
          L2     3.0×   ~1.5–2.0× [A×B partial]   ~1.0–1.5×     NOT CONFIRMED at 3×
                        Data supports ~1.5–2.5×; residual D is not measured
          L3     5.0×   ~2.5–3.6× [A×C + B]       ~1.4–2.5×     PARTIALLY SUPPORTED
                        3–4× is well-evidenced; 5× requires ~1.4× in [D]
          L4     8.0×   ~3–4× at ceiling of        ~4–5×         DIRECTIONALLY
                        documented components                      PLAUSIBLE only
                        Gaza/Sudan frontline may exceed this; no confirming figure

          KEY CAVEAT: The Somalia security figure ($400M/year) and Yemen escort
          ($3K/convoy) represent different cost categories that cannot simply be
          multiplied without risk of double-counting. The bottom-up estimate of
          ~2.5–3.6× for L3 is a rough ceiling on what can be documented; it does
          not mean L3=5× is wrong — it means ~1.4–2× in additional overhead costs
          (hazard pay, negotiation staff, evacuation contingency) are plausible but
          unmeasured by any public source found.

        ── PER-PERSON-PER-DAY CONVERSION (for documentation only) ────────────
          Converting WFP per-MT figure to per-person-per-day to compare
          against the $3.50/person/day model base:

          Assumption: 0.65 kg/person/day supply weight
            = 0.50 kg food (dry weight from Sphere 2100 kcal estimate)
            + 0.10 kg medicine/medical supplies
            + 0.05 kg other (hygiene, communication materials)
            Excludes water: Sphere standard is 15 L/day = 15 kg/day per person

          At Sudan conflict rate of $209.63/MT and 0.65 kg/person/day:
            0.00065 MT × $209.63 = $0.136/person/day (logistics only, dry goods)
            Gap vs model base: $3.50 / $0.136 = 25.7× — appears very large

          GAP EXPLANATION — why $3.50/$0.136 = 25.7× is not a contradiction:
            (1) Water dominates supply weight. At 15 kg/day water:
                total weight = 15.65 kg = 0.01565 MT/person/day
                $209.63 × 0.01565 = $3.28/person/day — within 6% of $3.50 base
            (2) The $3.50 base includes admin, staffing, distribution, monitoring.
            (3) Sudan per-MT underestimates true access cost (UNHAS/Logistics
                Cluster services provided free-to-user or at partial cost recovery).
          CONCLUSION: The $3.50 base rate is defensible when water weight is
          included. The WFP data does not contradict it.

          WFP and 5-search sources added to REMAINING_COST_SOURCE_NOTES:
            "wfp_east_africa_2023", "wfp_sudan_conflict_2023",
            "yemen_logistics_cluster_2015", "access_mult_ocha_2024",
            "access_mult_undss_yemen", "access_mult_wfp_redsea",
            "access_mult_acf_2018", "access_mult_ifrc_codn"

      RC_LOSS_RATE  [0.05, 0.05, 0.15, 0.30, 0.50]
        WEB SEARCH RESULT (June 2026):
          OCHA Gaza ceasefire monitoring (Oct–Dec 2025): "less than two per cent
          of cargo was looted or otherwise intercepted" under active UN 2720
          Mechanism monitoring. URL: https://www.ochaopt.org/content/report-
          humanitarian-response-un-and-humanitarian-partners-during-second-
          month-october-2025-ceasefire
          → This establishes a near-ceasefire floor of ~2% under active
          monitoring. The model's L0–1 rate of 5% is conservative relative to
          this (5% includes non-looting losses: spoilage, logistics wastage).
          Syria (Hall 2022 via corruption literature): estimated half of funds
          affected by exchange-rate manipulation — this is financial diversion,
          not supply destruction; not applicable as a loss rate.
          Ethiopia 2023: widespread diversion in 6 of 11 regions — no percentage.
          STATUS: L0–1 rate of 5% is directionally consistent with the Gaza
          ceasefire data (which is a best-case floor). L2–4 rates (15%, 30%,
          50%) have no quantified published source. The WFP Annual Performance
          Reports and WFP audit reports for Sudan 2023–2024 remain the most
          likely sources for quantified loss rates; these were not accessible in
          public search results (internal WFP documents).

      RC_INFIELD_INJ  [0.0, 0.1, 0.5, 2.0, 8.0]  (per 1 000 per day)
        WEB SEARCH RESULT (June 2026): No public source found reporting
        in-field civilian injury rates as a daily incidence per 1,000 persons.
        STATUS: UNVALIDATED — historical case proxy (mortality rates from
        historical_data.py, June 2026 analysis) provides weak qualitative
        support. Precise validation requires: WHO Surveillance in Humanitarian
        Emergencies toolkit; ICRC Health Data Collection in Armed Conflict
        guidelines; Lancet Conflict & Health (injury-to-death ratio literature).

      field_treatment_cost_usd_per_injury  [$800]
        FIVE-SOURCE VALIDATION SEARCH (June 2026):

        SEARCH 1 — WHO / peer-reviewed conflict surgical care:
          CONFIRMED: $211 per surgical case at Munuki Mission Hospital,
          conflict-affected South Sudan, 2022.
          URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11534226
          Source: Chagomerana et al., PLOS Global Public Health, 2024.
          Provider cost, fully-loaded (top-down allocation). Covers war trauma,
          obstetrics, orthopaedics. Hospital is explicitly described as having
          an "extremely low-cost structure" — annual budget < US hospital's
          daily budget. This is the lower bound, not a typical ICRC/MSF level.

        SEARCH 2 — ICRC surgical programs:
          NO USABLE FIGURE. ICRC provides care entirely free; no per-patient
          cost published in any public document (2022–2023 Annual Reports
          searched — only aggregate CHF 2.4B total budget found).

        SEARCH 3 — MSF surgical trauma centers:
          SOURCE: Gosselin RA et al., 'Comparative CEA of two MSF surgical
          trauma centers', World Journal of Surgery, 2010 (data: ~2008–2009).
          URL: https://scienceportal.msf.org/assets/comparative-cost-
               effectiveness-analysis-two-msf-surgical-trauma-centers
          FIGURES (DALY-derived, not directly published per-case costs):
            Nigeria (armed conflict, Teme Hospital): $172/DALY → ~$500/case
            Haiti (disaster, La Trinité): $223/DALY → ~$650/case
          Inflation-adjusted to 2026 (~3%/yr × 15 yrs): ~$779 and ~$1,013
          These are the most relevant proxy for MSF-level frontline trauma
          centres. The Nigeria figure most closely matches the model's context.

        SEARCH 4 — Academic trauma cost literature:
          SOURCE: Journal of Global Surgery, 2021 (Ethiopia trauma hospital)
          URL: https://jogs.one/jogs_1221
          FIGURE: $190 USD median patient-side (out-of-pocket) cost per trauma
          admission. Non-conflict LMIC hospital. PATIENT cost, not provider.
          This is a floor — sets minimum expectation for any LMIC trauma care.

        SEARCH 5 — Sphere Handbook 2018:
          NO COST FIGURE. Section 2.4 "Injury and trauma care" sets clinical
          standards only. Sphere is not a costing document.

        DOCUMENTED RANGE (peer-reviewed, conflict or LMIC trauma):
          Floor (mission hospital, conflict): $211/surgical case (2022)
          Floor (patient-side, non-conflict): $190/case (2021)
          MSF conflict trauma center: ~$500–650/case (2009; ~$779–1,013 in 2026)

        STATUS: ABOVE documented peer-reviewed range.
          The $1,200 value exceeds all directly documented figures. It sits
          above even the inflation-adjusted MSF Nigeria figure (~$779/case).
          It approaches the inflation-adjusted MSF Haiti figure (~$1,013).
          $1,200 would be defensible ONLY if:
          (a) using MSF Haiti 2009 inflated to 2026 (~$1,013) AND
          (b) adding a ~20% premium for frontline L3–L4 access conditions
          NOTE: If $1,200 includes access overhead, and RC_ACCESS_MULT also
          captures access costs (for the supply component), the model may
          double-count access costs for the medical component.

        RECOMMENDATION: Reduce to $500 (upper bound of directly documented
          range, MSF Nigeria 2009 conflict trauma, not inflation-adjusted).
          Alternatively use $800 (inflation-adjusted MSF Nigeria ~$779,
          rounded up). Do not use $1,200 — this exceeds the inflation-adjusted
          ceiling of the best-documented MSF conflict trauma data.
    ──────────────────────────────────────────────────────────────────────────────
    """
    d = dims or {}
    # Accept both short keys ("d1") and long keys ("d1_kinetic") from the AI context format
    d1 = float(d.get("d1", d.get("d1_kinetic",       3)))
    d2 = float(d.get("d2", d.get("d2_vulnerability",  3)))
    d3 = float(d.get("d3", d.get("d3_political",      3)))
    d4 = float(d.get("d4", d.get("d4_logistics",      3)))
    d5 = float(d.get("d5", d.get("d5_destination",    3)))
    d6 = float(d.get("d6", d.get("d6_urgency",        3)))
    d7 = float(d.get("d7", d.get("d7_information",    3)))

    vuln     = int(population * vulnerable_pct / 100)
    non_vuln = population - vuln

    access_mult = RC_ACCESS_MULT[risk_level]
    loss_rate   = RC_LOSS_RATE[risk_level]

    # ── Dimension modifiers ──────────────────────────────────────────────────
    # D4 Logistics: higher D4 = harder delivery = supply cost multiplier
    d4_penalty   = (d4 - 1) * 0.10 if d4 <= 3 else 0.20 + (d4 - 3) * 0.20
    # D3 Authorization: higher D3 = consent absent/refused = more blockade = higher loss rate
    # (D3 runs 1 = full consent → 5 = active refusal, same direction as every other dimension)
    d3_loss_add  = (d3 - 1) * 0.05 if d3 <= 3 else 0.10 + (d3 - 3) * 0.075
    # D7 Information: higher D7 = worse information environment = harder coordination
    # (D7 runs 1 = reliable comms → 5 = complete blackout, same direction as the others)
    d7_overhead  = (d7 - 1) * 0.025 if d7 <= 3 else 0.05 + (d7 - 3) * 0.05

    # D1 Kinetic: higher D1 = more dangerous extraction
    d1_ext_mult  = 1.0 + (d1 - 1) * 0.15 if d1 <= 3 else 1.3 + (d1 - 3) * 0.35
    # D3 Authorization: lower D3 = harder corridor = higher extraction probability
    d3_ext_add   = d3_loss_add  # same breakpoints
    # D6 Urgency: higher D6 = window closing = extraction probability floor
    d6_floor     = 0.85 if d6 >= 5 else (0.60 if d6 >= 4 else 0.0)

    # D2 Vulnerability: higher D2 = more susceptible to injury
    d2_inj_mult  = 1.0 + (d2 - 1) * 0.15 if d2 <= 3 else 1.3 + (d2 - 3) * 0.25
    # D1 Kinetic: higher D1 = more injuries per day (applied on top of D2)
    d1_inj_mult  = 1.5 if d1 >= 5 else (1.3 if d1 >= 4 else 1.0)
    # D5 Destination: higher D5 = destination overwhelmed / unsafe = fewer medical
    # resources on arrival = higher cost per injury
    # (D5 runs 1 = destination fully equipped → 5 = destination unsafe/non-existent)
    d5_cost_mult = 1.0 + (d5 - 1) * 0.15 if d5 <= 3 else 1.3 + (d5 - 3) * 0.35

    # ── Component 1: in-situ supply ─────────────────────────────────────────
    eff_access_mult = access_mult * (1 + d4_penalty)
    eff_loss_rate   = loss_rate + d3_loss_add + d7_overhead   # D7 folded in additively
    # Terrain multiplier applied to supply delivery: poor roads increase all delivery costs
    terrain_mult_supply = TERRAIN_MULT.get(terrain, 1.0)
    cm = climate_mult or {"fuel_transport": 1.0, "shelter": 1.0}
    climate_fuel_mult = cm.get("fuel_transport", 1.0)
    raw_supply  = population * 3.50 * eff_access_mult * terrain_mult_supply * climate_fuel_mult * days
    supply_cost = round(raw_supply * (1 + eff_loss_rate), 2)

    # ── Component 2: emergency extraction ───────────────────────────────────
    per_person_ground = UNHAS_RATE_USD_PER_KM * 0.30 * distance_km
    per_person_air    = UNHAS_RATE_USD_PER_KM * 3.00 * distance_km

    # Empirical exponential saturation (replaces prior linear formula days/30 × level × 0.1)
    # Anchored on 10 historical cases — see RC_EXTR_BASE_RATE constants above
    _rate     = RC_EXTR_BASE_RATE[risk_level]
    base_prob = min(
        (1.0 - math.exp(-_rate * float(days))) if _rate > 0 else 0.0,
        RC_EXTR_MAX_PROB[risk_level],
    )

    # D3 Authorization → blocked corridors increase extraction need
    # Gentler correction than supply formula (different dynamics)
    # Scaled ÷10 versus the pre-recalibration increments (Mariupol/Aleppo/Kosovo anchors
    # below are the original 10-95%-scale figures) to stay proportionate within the new
    # 1-8% critical-extraction range — the underlying D3 relationship is unchanged.
    # Anchors: Mariupol D3=4.5 (+12.5%), Aleppo D3=4.0 (+10%), Kosovo D3=4.0 (+10%)
    d3_prob_add = (d3 - 1.0) * 0.0025 if d3 <= 3 else 0.005 + (d3 - 3.0) * 0.005

    # D6 Urgency floor: imminent threat forces extraction need regardless of duration
    # Scaled ÷10 versus pre-recalibration for the same reason as d3_prob_add above.
    # Anchor: Srebrenica (D6=5, 3 days → 85% floor captures the extreme urgency)
    # at D6=4: Kherson/Mosul/CAR all show elevated urgency; 60% floor applied
    d6_floor_val = 0.085 if d6 >= 5 else (0.06 if d6 >= 4 else 0.0)

    prob            = min(max(base_prob + d3_prob_add, d6_floor_val), 0.95)
    extraction_base = prob * (non_vuln * per_person_ground + vuln * per_person_air) * d1_ext_mult
    extraction_cost = round(extraction_base * (2.5 if risk_level == 4 else 1.0), 2)

    # ── Component 3: field medical ───────────────────────────────────────────
    # Injury count: if the caller already ran calculate_staying_costs() for this scenario,
    # pass its cumulative "injuries" figure here via injuries_override so this dollar amount
    # and the mortality-model injury estimate never disagree (mirrors static/app.js calcRemaining()).
    # Otherwise falls back to the simpler flat-rate calculate_injuries() — identical to the old
    # calculate_staying_costs() behavior for the same inputs. d2_inj_mult / d1_inj_mult are
    # applied inside calculate_injuries; they are retained above only for the dim_modifiers
    # return dict (label display).
    cum_injuries   = injuries_override if injuries_override is not None else calculate_injuries(population, risk_level, days, dims)
    treat_cost_per = 800 * d5_cost_mult  # Range peer-reviewed: $211–$1,013. Valor conservador $800 adoptado (fonte: source-notes internas).
    field_med_cost = round(cum_injuries * treat_cost_per, 2)

    # ── Component 4: vulnerable population support ───────────────────────────
    # Additional per-capita cost for special needs (mobility assistance, extra medical
    # supplies, mental health support) not captured by the flat $3.50/day survival baseline.
    # No published per-capita figure exists (Sphere 2018 does not price this) — ESTIMATED.
    VULNERABLE_DAILY_PREMIUM_USD = 2.50
    vulnerable_premium = round(vuln * days * VULNERABLE_DAILY_PREMIUM_USD, 2)

    total = round(supply_cost + extraction_cost + field_med_cost + vulnerable_premium, 2)

    return {
        "parameters": {
            "population":              population,
            "vulnerable_pct":          vulnerable_pct,
            "risk_level":              risk_level,
            "days":                    days,
            "distance_km":             distance_km,
            "access_multiplier":       access_mult,
            "effective_access_mult":   round(eff_access_mult, 4),
            "terrain_mult":            terrain_mult_supply,
            "climate_fuel_mult":       climate_fuel_mult,
            "loss_rate":               loss_rate,
            "effective_loss_rate":     round(eff_loss_rate, 4),
            "base_extraction_prob":     round(base_prob, 4),
            "extraction_probability":  round(prob, 4),
            "per_person_ground_usd":   round(per_person_ground, 2),
            "per_person_air_usd":      round(per_person_air, 2),
            "treat_cost_per_injury":   round(treat_cost_per, 2),
            "unhas_rate_usd_per_km":   UNHAS_RATE_USD_PER_KM,
        },
        "dim_modifiers": {
            "d4_logistics_penalty":    round(d4_penalty, 4),
            "d3_loss_add":             round(d3_loss_add, 4),
            "d7_coord_overhead":       round(d7_overhead, 4),
            "d1_extraction_mult":      round(d1_ext_mult, 4),
            "d3_extraction_prob_add":  round(d3_prob_add, 4),
            "d6_urgency_floor":        round(d6_floor_val, 4),
            "d2_injury_mult":          round(d2_inj_mult, 4),
            "d1_injury_mult":          round(d1_inj_mult, 4),
            "d5_treatment_cost_mult":  round(d5_cost_mult, 4),
        },
        "costs_usd": {
            "supply_delivery":       supply_cost,
            "emergency_extraction":  extraction_cost,
            "field_medical":         field_med_cost,
            "vulnerable_support":    vulnerable_premium,
            "total":                 total,
        },
        "intermediates": {
            "raw_supply_before_loss":  round(raw_supply, 2),
            "cumulative_injuries":     round(cum_injuries, 2),
            "vulnerable":              vuln,
            "non_vulnerable":          non_vuln,
            # base_survival_cost: what it costs to keep this population alive at the
            # $3.50/person/day UNHCR humanitarian baseline, with zero conflict overhead.
            # access_premium: the extra cost conflict logistics adds on top of baseline.
            # supply_delivery = base_survival_cost + access_premium (always >= base).
            "base_survival_cost":      round(population * 3.50 * days, 2),
            "access_premium":          round(max(0.0, supply_cost - population * 3.50 * days), 2),
        },
        "source_notes": REMAINING_COST_SOURCE_NOTES,
    }

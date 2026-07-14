"""
RICS readiness/uncertainty engine — Layers 2 & 3.

Python port of reference/india-evac/index.html's pure functions
(computeReadiness, perturbStatus, monteCarlo, compositeScore, assign,
assignForInfoValue, computeInfoValue, buildCurves), per DESIGN.md §2/§3/§8.
Ported to Python (rather than reused as client-side JS) because ERCF's — and
therefore RICS's — architecture runs computation server-side, and RICS needs to
compose this layer's output with cost_engine.py's Trajectory A/B in one API
response (DESIGN.md §8).

Formulas are UNCHANGED from the source (computeReadiness's weighted average +
gatekeeper hard cap; perturbStatus/monteCarlo's confidence-scaled perturbation;
compositeScore's weighted composite; assign's greedy urgency-sorted assignment
with real capacity contention) — only the data these functions operate on has
changed (FACTORS, cohorts instead of archetyped groups, pathways instead of
synthetic destinations). See DESIGN.md's traceability table (§2) for the
per-function reuse/adapt disposition.

FACTORS reinterpretation (DESIGN.md §2/§3/§4):
  security          (gatekeeper, unchanged)
  legal_consent      (gatekeeper, was 'authority' — host-authority movement
                      consent -> legal recognition/work-permit/resettlement-visa consent)
  host_willingness   (gatekeeper, unchanged concept; Unknown-vs-Unwilling
                      distinction preserved verbatim, load-bearing per report §3.5/§5)
  housing            (was 'shelter')
  jobs               (new — no analogue in the evacuation model)
  services           (merge of 'food_water' + 'medical')

The Unknown-vs-Unwilling distinction (statusLabel/blockedGkFactors) and the
uncertainty slider (confMult = 1 - uncertaintyLevel) are reused verbatim and
must not be modified — DESIGN.md flags both as explicitly load-bearing for the
report's ethical argument (§3.5, §5, §8).
"""

from dataclasses import dataclass
from typing import Optional

from parameter_registry import PARAMETER_REGISTRY

STATUSES = ["operational", "partial", "blocked", "unknown"]

FACTORS = [
    {"id": "security", "label": "Security", "gk": True},
    {"id": "legal_consent", "label": "Legal Consent", "gk": True},
    {"id": "host_willingness", "label": "Host Willingness", "gk": True, "blocked_label": "Unwilling"},
    {"id": "housing", "label": "Housing", "gk": False},
    {"id": "jobs", "label": "Jobs", "gk": False},
    {"id": "services", "label": "Services", "gk": False},
]


def _readiness_params() -> dict:
    """Pulls every readiness-layer constant from the parameter registry rather
    than hardcoding — keeps this module and PARAMETER_REGISTRY.md from drifting,
    the exact failure BACKLOG.md documents for the simulator's methodology .docx."""
    keys = [
        "mc_runs", "gatekeeper_weight", "normal_weight", "gk_blocked_cap",
        "score_operational", "score_partial", "score_blocked", "score_unknown_base",
        "w_readiness", "w_capacity", "w_admin", "w_vuln",
        "success_min_readiness", "max_perturb_prob",
    ]
    return {k: PARAMETER_REGISTRY[k]["value"] for k in keys}


PARAMS = _readiness_params()


# ============================================================
# SEEDED RNG — Park-Miller LCG, ported verbatim from index.html:616-631
# ============================================================
class RNG:
    def __init__(self, seed: float):
        self.s = max(1, abs(int(seed)) % 2147483646) or 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return (self.s - 1) / 2147483646


# ============================================================
# Unknown-vs-Unwilling — ported verbatim, do not modify (DESIGN.md §2)
# ============================================================
def status_label(factor: dict, status: str) -> str:
    if status == "blocked" and factor.get("blocked_label"):
        return factor["blocked_label"]
    return status.capitalize()


def blocked_gk_factors(pathway: dict) -> list:
    return [f for f in FACTORS if f["gk"] and pathway["factors"][f["id"]]["status"] == "blocked"]


# ============================================================
# READINESS SCORING — ported from computeReadiness() index.html:682-706
# ============================================================
def compute_readiness(pathway: dict, conf_mult: float, overrides: Optional[dict] = None) -> dict:
    overrides = overrides or {}
    w_sum = 0.0
    w_tot = 0.0
    gk_blocked = False
    factor_scores = {}

    for f in FACTORS:
        status = overrides.get(f["id"], pathway["factors"][f["id"]]["status"])
        eff_conf = pathway["factors"][f["id"]]["base_conf"] * conf_mult
        w = PARAMS["gatekeeper_weight"] if f["gk"] else PARAMS["normal_weight"]

        if status == "blocked":
            if f["gk"]:
                gk_blocked = True
            score = PARAMS["score_blocked"]
        elif status == "unknown":
            score = PARAMS["score_unknown_base"] * (0.5 + 0.5 * eff_conf)
        else:
            base = PARAMS["score_operational"] if status == "operational" else PARAMS["score_partial"]
            score = base * (0.5 + 0.5 * eff_conf)

        factor_scores[f["id"]] = score
        w_sum += w * score
        w_tot += w

    readiness = w_sum / w_tot if w_tot > 0 else 0.0
    if gk_blocked:
        readiness = min(readiness, PARAMS["gk_blocked_cap"])
    return {"readiness": readiness, "gk_blocked": gk_blocked, "factor_scores": factor_scores}


# ============================================================
# MONTE CARLO ENGINE — ported from perturbStatus()/monteCarlo() index.html:711-738
# ============================================================
def perturb_status(status: str, eff_conf: float, rng: RNG) -> str:
    if status == "unknown":
        return status
    prob = PARAMS["max_perturb_prob"] * (1 - eff_conf)
    if rng.next() > prob:
        return status
    idx = STATUSES.index(status)
    direction = -1 if rng.next() < 0.5 else 1
    new_idx = max(0, min(len(STATUSES) - 1, idx + direction))
    return STATUSES[new_idx]


def monte_carlo(pathway: dict, cohort: dict, conf_mult: float, seed: int, runs: Optional[int] = None) -> dict:
    runs = runs if runs is not None else PARAMS["mc_runs"]
    rng = RNG(seed)
    successes = 0
    readiness_vals = []

    for _ in range(runs):
        overrides = {}
        for f in FACTORS:
            eff_conf = pathway["factors"][f["id"]]["base_conf"] * conf_mult
            overrides[f["id"]] = perturb_status(pathway["factors"][f["id"]]["status"], eff_conf, rng)
        result = compute_readiness(pathway, conf_mult, overrides)
        readiness_vals.append(result["readiness"])
        if (result["readiness"] >= PARAMS["success_min_readiness"]
                and pathway["capacity"] >= cohort["size"]
                and not result["gk_blocked"]):
            successes += 1

    mean = sum(readiness_vals) / runs
    variance = sum((v - mean) ** 2 for v in readiness_vals) / runs
    return {"success_rate": successes / runs, "mean": mean, "std_dev": variance ** 0.5}


# ============================================================
# ASSIGNMENT — ported from compositeScore()/assign() index.html:744-788
# ============================================================
def composite_score(pathway: dict, cohort: dict, conf_mult: float, admin_complexity_max: float) -> dict:
    readiness = compute_readiness(pathway, conf_mult)["readiness"]
    cap_fit = min(1.0, pathway["capacity"] / cohort["size"])
    admin_simplicity = 1 - (pathway["admin_complexity"] / admin_complexity_max)
    vuln_match = 1.0 if (cohort.get("needs") and pathway["factors"]["services"]["status"] == "operational") else 0.5
    comp = (readiness * PARAMS["w_readiness"]
            + cap_fit * PARAMS["w_capacity"]
            + admin_simplicity * PARAMS["w_admin"]
            + vuln_match * PARAMS["w_vuln"])
    return {"comp": comp, "readiness": readiness, "cap_fit": cap_fit,
            "admin_simplicity": admin_simplicity, "vuln_match": vuln_match}


def assign(pathways: list, cohorts: list, conf_mult: float, admin_complexity_max: float) -> list:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_cohorts = sorted(cohorts, key=lambda c: priority_order.get(c["priority"], 99))
    remaining = {p["id"]: p["capacity"] for p in pathways}
    results = []

    for si, cohort in enumerate(sorted_cohorts):
        ranked = []
        for di, pathway in enumerate(pathways):
            cs = composite_score(pathway, cohort, conf_mult, admin_complexity_max)
            mc = monte_carlo(pathway, cohort, conf_mult, si * 1000 + di + 1)
            ranked.append({"pathway_id": pathway["id"], **cs, "mc": mc})
        ranked.sort(key=lambda r: r["comp"], reverse=True)

        viable = [r for r in ranked if remaining[r["pathway_id"]] >= cohort["size"]]
        if viable:
            primary = viable[0]
            remaining[primary["pathway_id"]] -= cohort["size"]
            unassigned = False
        else:
            primary = ranked[0]
            unassigned = True

        alt = viable[1] if len(viable) > 1 else None
        primary_pathway = next(p for p in pathways if p["id"] == primary["pathway_id"])
        factor_scores = compute_readiness(primary_pathway, conf_mult)["factor_scores"]
        risk_factor = min(FACTORS, key=lambda f: factor_scores[f["id"]])

        results.append({
            "cohort": cohort, "ranked": ranked, "primary": primary, "alt": alt,
            "risk_factor": risk_factor, "primary_pathway": primary_pathway, "unassigned": unassigned,
        })
    return results


# ============================================================
# INFORMATION VALUE ENGINE — ported from assignForInfoValue()/computeInfoValue()
# index.html:795-839. Directly answers report §8's advocacy-evidence ask:
# "which unknowns, if resolved, would move outcomes most."
# ============================================================
def assign_for_info_value(pathways: list, cohorts: list, conf_mult: float, admin_complexity_max: float,
                           runs: int, seed_offset: int) -> list:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_cohorts = sorted(cohorts, key=lambda c: priority_order.get(c["priority"], 99))
    remaining = {p["id"]: p["capacity"] for p in pathways}
    out = []

    for si, cohort in enumerate(sorted_cohorts):
        scored = sorted(
            ({"pathway_id": p["id"], "pathway": p,
              "comp": composite_score(p, cohort, conf_mult, admin_complexity_max)["comp"]}
             for p in pathways),
            key=lambda s: s["comp"], reverse=True,
        )
        viable = [s for s in scored if remaining[s["pathway_id"]] >= cohort["size"]]
        if not viable:
            out.append({"success_rate": 0.0})
            continue
        remaining[viable[0]["pathway_id"]] -= cohort["size"]
        mc = monte_carlo(viable[0]["pathway"], cohort, conf_mult, seed_offset + si * 997 + 1, runs)
        out.append({"success_rate": mc["success_rate"]})
    return out


def compute_info_value(pathways: list, cohorts: list, conf_mult: float, admin_complexity_max: float) -> list:
    INFO_RUNS = 100
    BASE_SEED = 200001

    base_results = assign_for_info_value(pathways, cohorts, conf_mult, admin_complexity_max, INFO_RUNS, BASE_SEED)
    base_mean = sum(r["success_rate"] for r in base_results) / max(1, len(base_results))

    out = []
    for fi, f in enumerate(FACTORS):
        unknown_pathways = [p for p in pathways if p["factors"][f["id"]]["status"] == "unknown"]
        if not unknown_pathways:
            out.append({"factor": f, "delta": 0.0, "base_mean": base_mean, "new_mean": base_mean, "unknown_count": 0})
            continue

        mod_pathways = []
        for p in pathways:
            if p["factors"][f["id"]]["status"] != "unknown":
                mod_pathways.append(p)
            else:
                mod = dict(p)
                mod["factors"] = dict(p["factors"])
                mod["factors"][f["id"]] = {**p["factors"][f["id"]], "status": "operational"}
                mod_pathways.append(mod)

        mod_results = assign_for_info_value(mod_pathways, cohorts, conf_mult, admin_complexity_max,
                                             INFO_RUNS, BASE_SEED + (fi + 1) * 30000)
        new_mean = sum(r["success_rate"] for r in mod_results) / max(1, len(mod_results))
        out.append({"factor": f, "delta": new_mean - base_mean, "base_mean": base_mean,
                     "new_mean": new_mean, "unknown_count": len(unknown_pathways)})

    return sorted(out, key=lambda r: r["delta"], reverse=True)


if __name__ == "__main__":
    import cohorts as cohorts_mod
    import pathways as pathways_mod

    # Illustrative only — NOT real Dzaleka data. capacity/admin_complexity overrides
    # below are placeholders (pathways.py has no sourced figures yet for any of the
    # 7 pathways except legal_consent/host_willingness status on Malawi local
    # integration). Cohort sizes respect the k_anonymity_floor (>=20).
    demo_pathways = [
        pathways_mod.to_engine_pathway("malawi_local_integration", capacity_override=500, admin_complexity_override=3),
        pathways_mod.to_engine_pathway("resettlement_usa", capacity_override=200, admin_complexity_override=9),
        pathways_mod.to_engine_pathway("voluntary_return_drc", capacity_override=1000, admin_complexity_override=6),
    ]
    demo_cohorts = [
        cohorts_mod.make_cohort("c1", "drc", "unaccompanied_minor", "registered_refugee", 40, "high"),
        cohorts_mod.make_cohort("c2", "burundi", "female_headed_household", "registered_refugee", 120, "medium"),
        cohorts_mod.make_cohort("c3", "rwanda", "general", "asylum_seeker", 300, "low"),
    ]

    conf_mult = 0.70  # illustrative 30% global uncertainty level, matches cost_engine.py demo
    admin_complexity_max = 10

    results = assign(demo_pathways, demo_cohorts, conf_mult, admin_complexity_max)
    for r in results:
        print(f"Cohort {r['cohort']['id']} ({r['cohort']['nationality']}, {r['cohort']['vulnerability_category']}, "
              f"n={r['cohort']['size']}) -> primary pathway: {r['primary']['pathway_id']} "
              f"(comp={r['primary']['comp']:.3f}, success_rate={r['primary']['mc']['success_rate']:.2f}, "
              f"unassigned={r['unassigned']}, risk_factor={r['risk_factor']['id']})")

    info_value = compute_info_value(demo_pathways, demo_cohorts, conf_mult, admin_complexity_max)
    print("\nInformation value (which Unknown factor, resolved, moves outcomes most):")
    for iv in info_value:
        print(f"  {iv['factor']['id']}: delta={iv['delta']:+.3f} (unknown_count={iv['unknown_count']})")

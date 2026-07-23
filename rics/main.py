"""
RICS API — composes cost_engine.py (Layer 1) and readiness_engine.py (Layer 2/3)
behind one FastAPI surface, pattern reused from ERCF's main.py (Pydantic request
models with Field constraints, one endpoint per calculation, scenario CRUD).

Per DESIGN.md §8, cost and readiness are two separately-computed engines composed
in the API layer, not merged into one function — cost stays deterministic-with-
bounds (§14: the reliable half), readiness stays Monte Carlo (a genuinely
probabilistic match), and confMult is the single shared input tying both together
(v0.2 correction, DESIGN.md §7).
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import cost_engine
import readiness_engine
import pathways as pathways_mod
import cohorts as cohorts_mod
from database import (
    init_db, create_cohort, get_cohort, list_cohorts, update_cohort, delete_cohort,
    create_cost_scenario, get_cost_scenario, list_cost_scenarios, K_ANON_FLOOR,
)
from parameter_registry import PARAMETER_REGISTRY

app = FastAPI(title="RICS — Resettlement & Inclusion Capacity Simulator")


# ─── Request models ──────────────────────────────────────────────────────────

class CohortIn(BaseModel):
    snapshot_date:          str
    nationality:            str
    vulnerability_category: str
    legal_status:           str
    count:                  int   = Field(..., ge=K_ANON_FLOOR)  # mirrors the DB CHECK constraint's floor, for a clean 422 instead of a raw IntegrityError
    priority:               str   = Field("medium")
    source:                 Optional[str] = None
    tag:                    str   = Field("unvalidated")


class TrajectoryAReq(BaseModel):
    cohort_count:                int   = Field(..., gt=0)
    conf_mult:                   float = Field(..., ge=0, le=1)
    tent_lifetime_years_override: float = Field(..., gt=0)
    funding_shortfall_pct:        float = Field(0.0, ge=0, le=1)  # a fraction, not a percentage; the dashboard's 0-100 input is divided by 100 before it gets here


class TrajectoryBReq(BaseModel):
    conf_mult:                    float = Field(..., ge=0, le=1)
    documentation_usd:            float = Field(0.0, ge=0)
    skills_credentialing_usd:     float = Field(0.0, ge=0)
    transport_usd:                float = Field(0.0, ge=0)
    startup_capital_usd:          float = Field(0.0, ge=0)
    host_coinvestment_offset_usd: float = Field(0.0, ge=0)
    residual_annual_usd:          float = Field(0.0, ge=0)


class BreakevenReq(BaseModel):
    trajectory_a: TrajectoryAReq
    trajectory_b: TrajectoryBReq
    cohort_id:    Optional[int] = None
    pathway_id:   Optional[str] = None
    year:         Optional[int] = None
    persist:      bool = False


class CohortForAssign(BaseModel):
    id:                     str
    nationality:            str
    vulnerability_category: str
    legal_status:           str
    size:                   int   = Field(..., ge=20)
    priority:               str   = Field("medium")


class AssignReq(BaseModel):
    pathway_ids:           list[str]
    pathway_overrides:     dict = Field(default_factory=dict)  # {pathway_id: {"capacity": ..., "admin_complexity": ...}}
    cohorts:               list[CohortForAssign]
    conf_mult:             float = Field(..., ge=0, le=1)
    admin_complexity_max:  float = Field(..., gt=0)


class InfoValueReq(AssignReq):
    pass


class GatekeeperReq(BaseModel):
    pathway_id: str
    conf_mult:  float = Field(..., ge=0, le=1)


# ─── Startup ──────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()


# ─── Static files ───────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ─── Cohort CRUD ──────────────────────────────────────────────────────────

@app.get("/api/cohorts")
async def list_all_cohorts():
    return list_cohorts()


@app.post("/api/cohorts", status_code=201)
async def create(body: CohortIn):
    if body.nationality not in cohorts_mod.NATIONALITIES:
        raise HTTPException(422, f"unknown nationality: {body.nationality}")
    if body.vulnerability_category not in cohorts_mod.VULNERABILITY_CATEGORIES:
        raise HTTPException(422, f"unknown vulnerability_category: {body.vulnerability_category}")
    if body.legal_status not in cohorts_mod.LEGAL_STATUSES:
        raise HTTPException(422, f"unknown legal_status: {body.legal_status}")
    return create_cohort(body.model_dump())


@app.get("/api/cohorts/{cid}")
async def get(cid: int):
    c = get_cohort(cid)
    if not c:
        raise HTTPException(404, "Not found")
    return c


@app.put("/api/cohorts/{cid}")
async def update(cid: int, body: CohortIn):
    updated = update_cohort(cid, body.model_dump())
    if not updated:
        raise HTTPException(404, "Not found")
    return updated


@app.delete("/api/cohorts/{cid}")
async def delete(cid: int):
    if not delete_cohort(cid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ─── Layer 1: cost ────────────────────────────────────────────────────────

@app.post("/api/calculate/trajectory-a")
async def calc_trajectory_a(body: TrajectoryAReq):
    result = cost_engine.compute_trajectory_a(
        cohort_count=body.cohort_count, conf_mult=body.conf_mult,
        tent_lifetime_years_override=body.tent_lifetime_years_override,
        funding_shortfall_pct=body.funding_shortfall_pct,
    )
    return {
        "per_person_year": result.per_person_year,
        "annual_total": result.annual_total,
        "funding_shortfall_calibrated": result.funding_shortfall_calibrated,
        "protection_admin_costed": result.protection_admin_costed,
        "line_items": result.line_items,
    }


@app.post("/api/calculate/trajectory-b")
async def calc_trajectory_b(body: TrajectoryBReq):
    result = cost_engine.compute_trajectory_b(**body.model_dump())
    return {
        "upfront_total": result.upfront_total,
        "residual_annual_total": result.residual_annual_total,
        "uncosted_components": result.uncosted_components,
        "line_items": result.line_items,
    }


@app.post("/api/calculate/breakeven")
async def calc_breakeven(body: BreakevenReq):
    traj_a = cost_engine.compute_trajectory_a(
        cohort_count=body.trajectory_a.cohort_count, conf_mult=body.trajectory_a.conf_mult,
        tent_lifetime_years_override=body.trajectory_a.tent_lifetime_years_override,
        funding_shortfall_pct=body.trajectory_a.funding_shortfall_pct,
    )
    traj_b = cost_engine.compute_trajectory_b(**body.trajectory_b.model_dump())
    result = cost_engine.compute_breakeven(traj_a, traj_b)
    result["chart_series"] = cost_engine.compute_breakeven_series(traj_a, traj_b)
    result["trajectory_a_per_person_year"] = traj_a.per_person_year
    result["trajectory_a_annual_total"] = traj_a.annual_total
    result["trajectory_b_upfront_total"] = traj_b.upfront_total
    # Per-person view of Trajectory B for the metric card (same cohort_count
    # Trajectory A already required) — computed here, not in the frontend.
    count = body.trajectory_a.cohort_count
    result["trajectory_b_per_person"] = tuple(v / count for v in traj_b.upfront_total)

    if body.persist:
        if body.cohort_id is None or body.pathway_id is None or body.year is None:
            raise HTTPException(422, "cohort_id, pathway_id, and year are required when persist=true")
        create_cost_scenario({
            "cohort_id": body.cohort_id, "pathway_id": body.pathway_id, "year": body.year,
            "trajectory_a_annual_cost": traj_a.annual_total[0],
            "trajectory_b_upfront_cost": traj_b.upfront_total[0],
            "funding_shortfall_pct": body.trajectory_a.funding_shortfall_pct,
            "breakeven_year_point": result["breakeven_year_point"],
            "breakeven_year_low": result["breakeven_year_low"],
            "breakeven_year_high": result["breakeven_year_high"],
            "conf_mult": body.trajectory_a.conf_mult,
        })

    return result


@app.get("/api/cost-scenarios")
async def list_scenarios(cohort_id: Optional[int] = None):
    return list_cost_scenarios(cohort_id)


@app.get("/api/cost-scenarios/{sid}")
async def get_scenario(sid: int):
    s = get_cost_scenario(sid)
    if not s:
        raise HTTPException(404, "Not found")
    return s


# ─── Layer 2/3: readiness, uncertainty ────────────────────────────────────

def _build_pathways(pathway_ids: list[str], overrides: dict) -> list[dict]:
    out = []
    for pid in pathway_ids:
        ov = overrides.get(pid, {})
        try:
            out.append(pathways_mod.to_engine_pathway(
                pid, capacity_override=ov.get("capacity"),
                admin_complexity_override=ov.get("admin_complexity"),
            ))
        except KeyError:
            raise HTTPException(422, f"unknown pathway_id: {pid}")
        except ValueError as e:
            raise HTTPException(422, str(e))
    return out


@app.get("/api/pathways")
async def list_pathways():
    """Returns every pathway's sourcing status as-is, including unsourced
    capacity/admin_complexity — callers must see the gap, not a silently
    filled-in number (DESIGN.md / pathways.py honesty pattern). Adds an
    `overall_tag` (worst-of-tags rollup, computed server-side) per pathway
    for the frontend's sourcing badge — never computed client-side."""
    return {
        pid: {**record, "overall_tag": pathways_mod.overall_tag(pid)}
        for pid, record in pathways_mod.PATHWAYS.items()
    }


@app.post("/api/readiness/assign")
async def readiness_assign(body: AssignReq):
    engine_pathways = _build_pathways(body.pathway_ids, body.pathway_overrides)
    engine_cohorts = [c.model_dump() for c in body.cohorts]
    for c in engine_cohorts:
        c["needs"] = cohorts_mod.VULNERABILITY_NEEDS.get(c["vulnerability_category"])
    results = readiness_engine.assign(engine_pathways, engine_cohorts, body.conf_mult, body.admin_complexity_max)
    return results


@app.post("/api/readiness/info-value")
async def readiness_info_value(body: InfoValueReq):
    engine_pathways = _build_pathways(body.pathway_ids, body.pathway_overrides)
    engine_cohorts = [c.model_dump() for c in body.cohorts]
    for c in engine_cohorts:
        c["needs"] = cohorts_mod.VULNERABILITY_NEEDS.get(c["vulnerability_category"])
    return readiness_engine.compute_info_value(engine_pathways, engine_cohorts, body.conf_mult, body.admin_complexity_max)


@app.post("/api/readiness/gatekeepers")
async def readiness_gatekeepers(body: GatekeeperReq):
    """Gatekeeper-status view (Security/Legal Consent/Host Willingness) for a
    single pathway. Deliberately bypasses assign()'s capacity/admin_complexity
    requirement — compute_readiness() never reads those fields, so this works
    today even though 6 of 7 pathways have no sourced capacity yet, unlike
    /api/readiness/assign which needs them for the Monte Carlo/ranking layer."""
    if body.pathway_id not in pathways_mod.PATHWAYS:
        raise HTTPException(422, f"unknown pathway_id: {body.pathway_id}")

    engine_pathway = pathways_mod.to_readiness_only_pathway(body.pathway_id)
    result = readiness_engine.compute_readiness(engine_pathway, body.conf_mult)
    source_record = pathways_mod.PATHWAYS[body.pathway_id]

    factors_out = {}
    for f in readiness_engine.FACTORS:
        if not f["gk"]:
            continue
        status = engine_pathway["factors"][f["id"]]["status"]
        factors_out[f["id"]] = {
            "status": status,
            "label": readiness_engine.status_label(f, status),
            "base_conf": engine_pathway["factors"][f["id"]]["base_conf"],
            "score": result["factor_scores"][f["id"]],
            "tag": source_record["factors"][f["id"]]["tag"],
            "source": source_record["factors"][f["id"]]["source"],
        }

    return {"pathway_id": body.pathway_id, "gk_blocked": result["gk_blocked"],
            "readiness": result["readiness"], "factors": factors_out}


# ─── Transparency (report §10.1/§13: full parameter table public) ────────

@app.get("/api/parameters")
async def get_parameters():
    return PARAMETER_REGISTRY


@app.get("/api/cohort-vocabulary")
async def get_cohort_vocabulary():
    return {
        "nationalities": cohorts_mod.NATIONALITIES,
        "vulnerability_categories": cohorts_mod.VULNERABILITY_CATEGORIES,
        "legal_statuses": cohorts_mod.LEGAL_STATUSES,
        "priority_order": cohorts_mod.PRIORITY_ORDER,
        "k_anonymity_floor": PARAMETER_REGISTRY["k_anonymity_floor"]["value"],
    }

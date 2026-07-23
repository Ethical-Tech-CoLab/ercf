"""
RICS Cost Dashboard — standalone server for the cost-layer contributor's solo
brainstorm tool. Imports ONLY cost_engine.py, parameter_registry.py, cohorts.py,
and database.py — all confirmed self-contained, zero dependency on pathways.py
or readiness_engine.py (the readiness/matching teammates' modules, see
cost_engine.py's own "MERGE STATUS" header). This means the dashboard runs even
if those modules are mid-edit or temporarily broken.

Runs its own SQLite file: sqlite3 resolves database.py's DB_PATH ("rics.db")
relative to the process's current working directory, so running this from
*inside* cost-dashboard/ creates cost-dashboard/rics.db — a separate database
from rics/rics.db (the full app's shared database). Brainstorm data entered
here never touches the team's shared database.

This is NOT the merged RICS app — it has no gatekeeper or pathway UI on
purpose, so it can't be mistaken for a merged deliverable before the team's
other modules are ready. static/ (the full RICS frontend) is untouched.

Run:
    cd rics/cost-dashboard
    uvicorn server:app --reload --port 8200
Then open http://localhost:8200/
"""

import sys
import os

# cost-dashboard/ is a hyphenated directory name, which is not a valid Python
# package identifier — `import cost-dashboard.server` would be a SyntaxError.
# Running uvicorn from *inside* this directory (server:app, not a dotted path)
# sidesteps that; this sys.path addition is what lets server.py reach the
# shared modules (cost_engine.py etc.) one directory up, in rics/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import cost_engine
import cohorts as cohorts_mod
from database import init_db, create_cohort, list_cohorts, delete_cohort, K_ANON_FLOOR
from parameter_registry import PARAMETER_REGISTRY

app = FastAPI(title="RICS Cost Dashboard — cost-layer brainstorm tool (not the merged app)")


# ─── Request models — identical shape to main.py's, cost-layer endpoints only ─

class CohortIn(BaseModel):
    snapshot_date:          str
    nationality:            str
    vulnerability_category: str
    legal_status:           str
    count:                  int   = Field(..., ge=K_ANON_FLOOR)
    priority:               str   = Field("medium")
    source:                 Optional[str] = None
    tag:                    str   = Field("unvalidated")


class TrajectoryAReq(BaseModel):
    cohort_count:                 int   = Field(..., gt=0)
    conf_mult:                    float = Field(..., ge=0, le=1)
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


# ─── Startup ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()


# ─── Frontend (2 files, no static/ subfolder needed for a tool this small) ──

@app.get("/")
async def root():
    return FileResponse("index.html")


@app.get("/app.js")
async def app_js():
    return FileResponse("app.js")


# ─── Cohorts (item 1: populated from cohorts.py's vocabulary, never hardcoded) ─

@app.get("/api/cohort-vocabulary")
async def get_cohort_vocabulary():
    return {
        "nationalities": cohorts_mod.NATIONALITIES,
        "vulnerability_categories": cohorts_mod.VULNERABILITY_CATEGORIES,
        "legal_statuses": cohorts_mod.LEGAL_STATUSES,
        "priority_order": cohorts_mod.PRIORITY_ORDER,
        "k_anonymity_floor": K_ANON_FLOOR,
    }


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


@app.delete("/api/cohorts/{cid}")
async def delete(cid: int):
    if not delete_cohort(cid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ─── Cost calculation (item 2 + 3) — identical logic to main.py's endpoint ──

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
    count = body.trajectory_a.cohort_count
    result["trajectory_b_per_person"] = tuple(v / count for v in traj_b.upfront_total)
    return result


# ─── Transparency (same as main.py — report §10.1/§13) ──────────────────────

@app.get("/api/parameters")
async def get_parameters():
    return PARAMETER_REGISTRY

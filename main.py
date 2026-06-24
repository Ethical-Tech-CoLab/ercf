from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import os
import uvicorn

from database import init_db, create_scenario, get_scenario, list_scenarios, update_scenario, delete_scenario
from calculators import calculate_risk, calculate_resources, calculate_staying_costs, calculate_remaining_costs
from historical_data import HISTORICAL_CASES
from world_risk import get_all_risk_levels, get_risk_by_iso3, NUM_TO_ISO3
from context_ai import analyze_country
from weather_data import get_climate_context
from air_evac import calculate_air_evacuation
from walking_evac import calculate_walking_evacuation

app = FastAPI(title="ERCF — Evacuation Risk Classification Framework", version="1.0.0")


# ─── Pydantic models ────────────────────────────────────────────────────────

class Dims(BaseModel):
    d1_kinetic:       float = Field(..., ge=1, le=5)
    d2_vulnerability: float = Field(..., ge=1, le=5)
    d3_political:     float = Field(..., ge=1, le=5)
    d4_logistics:     float = Field(..., ge=1, le=5)
    d5_destination:   float = Field(..., ge=1, le=5)
    d6_urgency:       float = Field(..., ge=1, le=5)
    d7_information:   float = Field(..., ge=1, le=5)

class ScenarioIn(Dims):
    name:                str
    description:         Optional[str]   = ""
    population:          int             = Field(..., gt=0)
    vulnerable_pct:      float           = Field(20.0, ge=0, le=100)
    distance_km:         float           = Field(50.0, gt=0)
    terrain:             int             = Field(3, ge=1, le=5)
    conflict_pattern:    int             = Field(5, ge=1, le=5)  # 1=urban_siege 2=enclave 3=city_conflict 4=regional 5=auto
    conflict_lat:        Optional[float] = None
    conflict_lng:        Optional[float] = None
    safe_zone_lat:       Optional[float] = None
    safe_zone_lng:       Optional[float] = None
    safe_zone_name:      Optional[str]   = None
    distance_source:     str             = 'manual'
    road_factor_applied: bool            = False
    haversine_km:        Optional[float] = None

class ResourceReq(BaseModel):
    population:     int   = Field(..., gt=0)
    vulnerable_pct: float = Field(20.0, ge=0, le=100)
    distance_km:    float = Field(50.0, gt=0)
    risk_level:     int   = Field(..., ge=0, le=4)
    d2_mobility:    float = Field(3.0, ge=1, le=5)
    terrain:        int   = Field(3, ge=1, le=5)

class StayReq(BaseModel):
    population:    int   = Field(..., gt=0)
    risk_level:    int   = Field(..., ge=0, le=4)
    days:          int   = Field(..., ge=1, le=365)
    d1:            float = Field(3.0, ge=1, le=5)
    d2:            float = Field(3.0, ge=1, le=5)
    d3:            float = Field(3.0, ge=1, le=5)   # Authorization — drives confinement modifier
    d4:            float = Field(3.0, ge=1, le=5)   # Logistics — drives confinement modifier
    remaining_pct: float = Field(1.0, ge=0, le=1)  # Fraction still in zone (0=all evacuated, 1=none)
    conflict_type: str   = Field('auto')            # 'urban_siege'|'enclave'|'city_conflict'|'regional'|'auto'

class RemainingReq(BaseModel):
    population:     int   = Field(..., gt=0)
    vulnerable_pct: float = Field(20.0, ge=0, le=100)
    risk_level:     int   = Field(..., ge=0, le=4)
    days:           int   = Field(..., ge=1, le=365)
    distance_km:    float = Field(50.0, gt=0)
    terrain:        int   = Field(3, ge=1, le=5)
    d1:             float = Field(3.0, ge=1, le=5)
    d2:             float = Field(3.0, ge=1, le=5)
    d3:             float = Field(3.0, ge=1, le=5)
    d4:             float = Field(3.0, ge=1, le=5)
    d5:             float = Field(3.0, ge=1, le=5)
    d6:             float = Field(3.0, ge=1, le=5)
    d7:             float = Field(3.0, ge=1, le=5)

class ClimateReq(BaseModel):
    lat:        Optional[float] = None
    lng:        Optional[float] = None
    start_date: Optional[str]   = None

class AirEvacReq(BaseModel):
    population:  int
    distance_km: float
    mode:        str             # "fixed_wing" or "helicopter"
    has_runway:  Optional[bool] = None

class WalkingEvacReq(BaseModel):
    population:     int
    distance_km:    float
    vulnerable_pct: float = 0


# ─── Startup ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()


# ─── Static files ───────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ─── Scenario CRUD ──────────────────────────────────────────────────────────

@app.get("/api/scenarios")
async def list_all():
    return list_scenarios()

@app.post("/api/scenarios", status_code=201)
async def create(body: ScenarioIn):
    risk = calculate_risk(body.model_dump())
    data = {**body.model_dump(), **risk}
    return create_scenario(data)

@app.get("/api/scenarios/{sid}")
async def get(sid: int):
    s = get_scenario(sid)
    if not s:
        raise HTTPException(404, "Not found")
    return s

@app.put("/api/scenarios/{sid}")
async def update(sid: int, body: ScenarioIn):
    risk = calculate_risk(body.model_dump())
    data = {**body.model_dump(), **risk}
    updated = update_scenario(sid, data)
    if not updated:
        raise HTTPException(404, "Not found")
    return updated

@app.delete("/api/scenarios/{sid}")
async def delete(sid: int):
    if not delete_scenario(sid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ─── Calculation endpoints ───────────────────────────────────────────────────

@app.post("/api/calculate/risk")
async def calc_risk(body: Dims):
    return calculate_risk(body.model_dump())

@app.post("/api/calculate/resources")
async def calc_resources(body: ResourceReq):
    return calculate_resources(body.population, body.vulnerable_pct, body.risk_level, body.distance_km, body.d2_mobility, body.terrain)

@app.post("/api/calculate/staying-cost")
async def calc_staying(body: StayReq):
    dims = {"d1": body.d1, "d2": body.d2, "d3": body.d3, "d4": body.d4}
    return calculate_staying_costs(
        body.population, body.risk_level, body.days, dims,
        body.remaining_pct, body.conflict_type,
    )

@app.post("/api/calculate/remaining-cost")
async def calc_remaining(body: RemainingReq):
    dims = {k: getattr(body, k) for k in ("d1","d2","d3","d4","d5","d6","d7")}
    return calculate_remaining_costs(
        body.population, body.vulnerable_pct, body.risk_level, body.days,
        body.distance_km, dims, body.terrain,
    )

@app.post("/api/air-evacuation")
async def air_evacuation(body: AirEvacReq):
    """Calculate cost and feasibility for fixed-wing or helicopter evacuation. Fixed-wing cost is validated (WFP UNHAS figure). Helicopter cost is an estimated derivation from a UN procurement contract — see air_evac.py for sourcing."""
    try:
        return calculate_air_evacuation(
            population=body.population,
            distance_km=body.distance_km,
            mode=body.mode,
            has_runway=body.has_runway,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/walking-evacuation")
async def walking_evacuation(body: WalkingEvacReq):
    """Calculate time, cost, and exposure risk for on-foot evacuation. Estimated figures derived from the Flee migration model literature and UK gait-speed clinical data — see walking_evac.py for full sourcing."""
    try:
        return calculate_walking_evacuation(
            population=body.population,
            distance_km=body.distance_km,
            vulnerable_pct=body.vulnerable_pct,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/api/climate")
async def climate_context(body: ClimateReq):
    """Returns historical climate regime and cost multipliers for a location/date, using Open-Meteo ERA5 reanalysis."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, get_climate_context, body.lat, body.lng, body.start_date
    )


# ─── Historical cases ────────────────────────────────────────────────────────

@app.get("/api/historical-cases")
async def historical():
    enriched = []
    for c in HISTORICAL_CASES:
        indicators = c.get("risk_indicators", {})
        three_index = calculate_risk(indicators) if indicators else None
        enriched.append({**c, "three_index": three_index})
    return enriched

@app.get("/api/historical-cases/{cid}")
async def historical_one(cid: int):
    for c in HISTORICAL_CASES:
        if c["id"] == cid:
            indicators = c.get("risk_indicators", {})
            three_index = calculate_risk(indicators) if indicators else None
            return {**c, "three_index": three_index}
    raise HTTPException(404, "Not found")


# ─── World risk map ──────────────────────────────────────────────────────────

@app.get("/api/world-risk")
async def world_risk():
    """All country risk levels keyed by ISO_A3."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_all_risk_levels)

@app.get("/api/world-risk/{iso3}")
async def country_risk(iso3: str):
    iso3u = iso3.upper()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_risk_by_iso3, iso3u)

@app.get("/api/iso-lookup")
async def iso_lookup():
    """TopoJSON numeric → ISO_A3 lookup table."""
    return NUM_TO_ISO3


class CountryContextReq(BaseModel):
    iso3: str
    country_name: Optional[str] = ""

@app.post("/api/country-context")
async def country_context(body: CountryContextReq):
    return analyze_country(body.iso3.upper(), body.country_name or "")


# ─── ACAPS live crisis data ──────────────────────────────────────────────────

@app.get("/api/acaps/{iso3}")
async def acaps_country(iso3: str):
    """Structured ACAPS data for a country: INFORM severity, humanitarian access,
    risk radar, and active crises — all filtered by ISO3, cached 24h server-side."""
    from acaps_data import get_country_data
    iso3u = iso3.upper()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_country_data, iso3u)


@app.get("/api/country-context-acaps/{iso3}")
async def country_context_acaps(iso3: str):
    """Return raw ACAPS INFORM crisis data for a country (ISO3).

    Requires ACAPS_API_KEY to be set. Returns a structured error when not
    configured so the frontend can display a helpful message rather than crash.
    """
    if not os.environ.get("ACAPS_API_KEY", "").strip():
        return {
            "error":   "ACAPS_API_KEY not configured",
            "results": [],
            "_note":   "Add ACAPS_API_KEY=<token> to your .env file. Register at https://api.acaps.org/register/",
        }
    from acaps_data import get_country_data
    iso3u = iso3.upper()
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, get_country_data, iso3u)
    # Return inform crises in the legacy format expected by renderAcapsSection
    return {"results": data.get("inform", []), "count": len(data.get("inform", []))}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

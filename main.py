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
from demographic_data import get_demographics
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

@app.get("/README.md")
async def serve_readme():
    return FileResponse("README.md", media_type="text/plain; charset=utf-8")


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


# ─── GeoNames city population lookup ─────────────────────────────────────────

GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME", "demo")

@app.get("/api/city-population/{city_name}")
async def city_population(city_name: str):
    import urllib.request, urllib.parse, json as _json
    url = (
        f"http://api.geonames.org/searchJSON"
        f"?q={urllib.parse.quote(city_name)}"
        f"&maxRows=20&featureClass=P&orderby=population"
        f"&username={GEONAMES_USERNAME}"
    )
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(503, f"GeoNames unavailable: {e}")

    q_lower = city_name.lower().strip()
    all_with_pop = [g for g in data.get("geonames", []) if (g.get("population") or 0) > 0]

    # Prioritise exact name matches, then partial matches, then fall back to highest population
    def _score(g):
        name = (g.get("name") or "").lower()
        topo = (g.get("toponymName") or "").lower()
        if name == q_lower or topo == q_lower:
            return 0       # exact match
        if name.startswith(q_lower) or topo.startswith(q_lower):
            return 1       # prefix match
        if q_lower in name or q_lower in topo:
            return 2       # substring match
        return 3           # no name match — probably a nearby place

    ranked = sorted(all_with_pop, key=lambda g: (_score(g), -g.get("population", 0)))

    results = []
    seen_names = set()
    for g in ranked:
        key = (g.get("name", "").lower(), g.get("countryCode", ""))
        if key in seen_names:
            continue
        seen_names.add(key)
        results.append({
            "name":        g.get("name", ""),
            "country":     g.get("countryName", ""),
            "countryCode": g.get("countryCode", ""),
            "adminName1":  g.get("adminName1", ""),
            "population":  g.get("population", 0),
            "lat":         float(g.get("lat", 0)),
            "lng":         float(g.get("lng", 0)),
        })
        if len(results) == 3:
            break

    if not results:
        raise HTTPException(404, f"No populated city found for '{city_name}'")
    return {"results": results}


# ─── Demographics ─────────────────────────────────────────────────────────────

@app.get("/api/demographics/{country_name}")
async def get_demographic_data(country_name: str):
    data = get_demographics(country_name)
    if data is None:
        raise HTTPException(404, f"No demographic data for '{country_name}'")
    return data


# ─── Commodity prices (World Bank Pink Sheet) ─────────────────────────────────

EIA_API_KEY = os.getenv("EIA_API_KEY", "")

# FAO FFPI fallback constant (Jan 2025, base 2014-2016=100)
FAO_FFPI_FALLBACK       = 127.5
FAO_FFPI_FALLBACK_DATE  = "2025-01"
BRENT_BASELINE_BBL      = 80.0   # ERCF baseline crude proxy
FAO_FFPI_BASELINE       = 127.5  # Jan 2025 baseline for adjustment

@app.get("/api/commodity-prices/{country_iso3}")
async def commodity_prices(country_iso3: str):
    import urllib.request, json as _json, concurrent.futures as _cf

    ERCF_BASELINE = {"fuel_l_usd": 1.20, "food_kg_usd": 3.0}

    def _fetch_eia():
        """Fetch most recent Brent crude spot price from EIA."""
        if not EIA_API_KEY:
            return None, ""
        url = (
            "https://api.eia.gov/v2/petroleum/pri/spt/data/"
            f"?api_key={EIA_API_KEY}"
            "&frequency=monthly&data[0]=value"
            "&sort[0][column]=period&sort[0][direction]=desc"
            "&offset=0&length=1&facets[series][]=RBRTE"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ERCF/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                payload = _json.loads(resp.read().decode())
            rows = payload.get("response", {}).get("data", [])
            if rows and rows[0].get("value") is not None:
                return round(float(rows[0]["value"]), 2), rows[0].get("period", "")
        except Exception:
            pass
        return None, ""

    def _fetch_fao():
        """Fetch FAO FFPI from official public CSV (fao.org/worldfoodsituation).
        CSV URL discovered Jun 2026 — no API key required.
        Format: Date(YYYY-MM), Food Price Index, Meat, Dairy, Cereals, Oils, Sugar
        To update the fallback constant manually: check latest value at
        https://www.fao.org/worldfoodsituation/foodpricesindex/en/ and update
        FAO_FFPI_FALLBACK / FAO_FFPI_FALLBACK_DATE at the top of this file.
        """
        import io as _io, csv as _csv
        url = (
            "https://www.fao.org/media/docs/worldfoodsituationlibraries"
            "/default-document-library/food_price_indices_data.csv"
            "?sfvrsn=523ebd2a_80&download=true"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ERCF/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            lines = text.strip().splitlines()
            # First 3 rows are header; row 3 is column names
            reader = _csv.reader(lines[3:])
            latest_date, latest_val = "", None
            for row in reader:
                if not row or not row[0].strip():
                    continue
                date_str = row[0].strip()
                val_str  = row[1].strip() if len(row) > 1 else ""
                try:
                    val = float(val_str)
                    if date_str > latest_date:
                        latest_date, latest_val = date_str, val
                except (ValueError, IndexError):
                    continue
            if latest_val is not None:
                return round(latest_val, 1), latest_date
        except Exception:
            pass
        return None, ""

    # Run both fetches in parallel
    with _cf.ThreadPoolExecutor(max_workers=2) as pool:
        eia_future = pool.submit(_fetch_eia)
        fao_future = pool.submit(_fetch_fao)
        brent_price, fuel_date = eia_future.result()
        fao_ffpi,    fao_date  = fao_future.result()

    # FAO fallback to hardcoded constant when API unavailable
    fao_source_note = "FAO FAOSTAT"
    if fao_ffpi is None:
        fao_ffpi   = FAO_FFPI_FALLBACK
        fao_date   = FAO_FFPI_FALLBACK_DATE
        fao_source_note = "FAO FFPI (hardcoded Jan 2025 fallback)"

    fuel_adjustment = round(brent_price / BRENT_BASELINE_BBL, 3) if brent_price else None
    food_adjustment = round(fao_ffpi   / FAO_FFPI_BASELINE,   3) if fao_ffpi   else None

    return {
        "country_iso3":      country_iso3.upper(),
        "fuel_brent_usd_bbl": brent_price,
        "fuel_date":          fuel_date or "unknown",
        "fao_ffpi":           fao_ffpi,
        "fao_date":           fao_date  or "unknown",
        "ercf_baseline":      ERCF_BASELINE,
        "fuel_adjustment":    fuel_adjustment,
        "food_adjustment":    food_adjustment,
        "source":             f"EIA Brent (fuel) + {fao_source_note} (food)",
        "note":               "International benchmark prices — humanitarian operations typically source supplies outside conflict zones",
    }


# ─── UCDP GED data ───────────────────────────────────────────────────────────

@app.get("/api/ucdp")
async def get_ucdp_data(
    country: str,
    year_start: int,
    year_end: int,
    adm1: str = None,
    use_api: bool = False
):
    """
    Query UCDP GED data for a given country and year range.
    use_api=true queries the live UCDP API (uses daily quota).
    use_api=false (default) uses the local CSV cache.
    """
    try:
        from ucdp_data import summarise_ucdp
        result = summarise_ucdp(
            country=country,
            year_start=year_start,
            year_end=year_end,
            adm1=adm1,
            use_api=use_api
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"UCDP API not configured: {e}")
    except (TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=503, detail=f"UCDP service unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UCDP query failed: {e}")

@app.get("/api/ucdp/status")
async def get_ucdp_status():
    """Check UCDP API connectivity and token validity."""
    from ucdp_data import check_api_status
    return check_api_status()


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

"""
weather_data.py — Historical climate context for evacuation cost modeling.
 
Uses the Open-Meteo Historical Weather API (ERA5/ERA5-Land reanalysis, free,
no API key, global coverage from 1940). Given a location and a start date,
fetches the climate conditions over the planned operational window and
derives a documented climate_multiplier applied to fuel, transport, and
shelter cost lines in calculators.py.
 
VALIDATION STATUS (June 2026)
==============================
The underlying weather data (temperature, precipitation, wind, snowfall) is
VALIDATED — it comes directly from ERA5 reanalysis, a peer-reviewed,
operationally-used meteorological dataset (ECMWF/Copernicus Climate Change
Service). This is NOT modelled or estimated data.
 
The MULTIPLIER VALUES derived from that data (e.g. "heavy rain → ×1.8 fuel
cost") are ESTIMATED, following the same transparency standard as the rest
of this project's cost model (see SOURCE_CONFIDENCE in calculators.py).
Qualitative humanitarian-logistics sources confirm the *direction* and
*rough magnitude* of seasonal cost impact (roads becoming impassable in
rainy season, forced shift to costlier air transport, winterized-shelter
premiums), but no single published source gives an exact numeric multiplier
for "rainy season road delivery cost increase" the way WFP's per-MT figures
do for conflict-zone access. This mirrors the RC_ACCESS_MULT gap already
documented in calculators.py for conflict-driven access costs.
 
SOURCES
-------
- Open-Meteo / ERA5 reanalysis (Hersbach et al. 2023, ECMWF, DOI:
  10.24381/cds.adbb2d47) — the weather data itself, VALIDATED.
- Logistics Cluster, "Logistics in peak rainy season" (CAR), 2019 — roads
  "mostly impassable" in peak rainy season, forcing reliance on airlift.
- World Vision / MSF / Devex (2018-2026) — Sudan, South Sudan, CAR field
  reporting: rainy season consistently described as making roads
  impassable for 1-4 months, forcing a shift to air transport (which is
  several times more expensive per tonne than road transport).
- UNHCR Emergency Shelter Solutions and Standards (2018, reaffirmed 2025):
  winterization kits required for cold-climate tent deployment; cold
  climates also require 4.5-5.5 m2/person indoor space vs Sphere's 3.5 m2
  baseline (a ~30-57% space/material increase before any kit cost).
- Whatcom County (Mansfield, dissertation, citing UNHCR cold-climate
  shelter program) — winterized shelter unit cost ~$2,000 vs ~$150-300 for
  a standard tarpaulin/canvas emergency tent — roughly 7-13x.
  This is the upper bound for a fully winterized unit, not a multiplier on
  the whole shelter line; the model applies a more conservative blended
  multiplier (see CLIMATE_SHELTER_MULT below) because not 100% of tents in
  an evacuation response would be the premium winterized version.
 
WHAT IS NOT MODELLED
---------------------
- Disease/health impact of climate (e.g. heat stress mortality, cold
  exposure mortality) — out of scope per the human/user decision to limit
  climate effects to cost/logistics only, not the mortality model.
- Flooding-specific costs (water pumps, boat transport) — only the generic
  "wet season access penalty" is modelled, not flood-specific equipment.
- Sub-national microclimate variation — Open-Meteo's grid cell (9-25km) is
  used as-is; no downscaling beyond what the API already provides.
"""
 
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
 
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
 
DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "snowfall_sum",
    "wind_speed_10m_max",
]
 
 
def fetch_historical_weather(
    lat: float, lng: float, start_date: str, days: int = 14
) -> Dict:
    """
    Fetch daily historical weather from Open-Meteo for `days` days starting
    at `start_date` (YYYY-MM-DD). Returns the raw daily arrays plus a
    `_meta` block noting the source and any fetch error.
 
    `days` defaults to 14: long enough to capture a representative window
    of the operational period without over-fetching for a single-point
    cost estimate. The evacuation/staying cost models already take their
    own `days` parameter for the financial projection; this 14-day weather
    window is independent and only used to classify the *climate regime*
    (e.g. "wet season", "deep winter") at the start of the scenario.
    """
    try:
        end_dt = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=days - 1)
        end_date = end_dt.strftime("%Y-%m-%d")
 
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lng, 4),
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(DAILY_VARS),
            "timezone": "UTC",
        }
        url = OPEN_METEO_ARCHIVE_URL + "?" + urllib.parse.urlencode(params)
 
        req = urllib.request.Request(url, headers={"User-Agent": "ERCF-research-tool/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
 
        if "error" in data and data["error"]:
            return {"_meta": {"ok": False, "error": data.get("reason", "Unknown API error")}}
 
        return {**data, "_meta": {"ok": True, "source": "Open-Meteo ERA5/ERA5-Land reanalysis"}}
 
    except Exception as e:
        return {"_meta": {"ok": False, "error": str(e)}}
 
 
def classify_climate(weather: Dict) -> Dict:
    """
    Classify the fetched weather window into a climate regime and derive
    a documented cost multiplier. See module docstring for sourcing.
 
    Returns:
        {
            "regime": str,              # human-readable label
            "regime_code": str,         # machine key
            "avg_temp_c": float,
            "total_precip_mm": float,
            "max_wind_kmh": float,
            "total_snowfall_cm": float,
            "climate_mult": {           # multipliers applied in calculators.py
                "fuel_transport": float,
                "shelter": float,
            },
            "rationale": str,
            "confidence": "estimated",
            "data_ok": bool,
        }
    """
    meta = weather.get("_meta", {})
    if not meta.get("ok"):
        return {
            "regime": "Unknown (weather data unavailable)",
            "regime_code": "unknown",
            "climate_mult": {"fuel_transport": 1.0, "shelter": 1.0},
            "rationale": f"Weather fetch failed: {meta.get('error', 'unknown error')}. "
                         "No climate adjustment applied (multiplier defaults to 1.0).",
            "confidence": "unavailable",
            "data_ok": False,
        }
 
    daily = weather.get("daily", {})
    temps = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
    precip = [p for p in daily.get("precipitation_sum", []) if p is not None]
    snow = [s for s in daily.get("snowfall_sum", []) if s is not None]
    wind = [w for w in daily.get("wind_speed_10m_max", []) if w is not None]
 
    if not temps:
        return {
            "regime": "Unknown (no data returned)",
            "regime_code": "unknown",
            "climate_mult": {"fuel_transport": 1.0, "shelter": 1.0},
            "rationale": "Open-Meteo returned no usable daily values for this location/date.",
            "confidence": "unavailable",
            "data_ok": False,
        }
 
    avg_temp = sum(temps) / len(temps)
    total_precip = sum(precip) if precip else 0.0
    total_snow = sum(snow) if snow else 0.0
    max_wind = max(wind) if wind else 0.0
    days_n = len(temps)
    precip_per_day = total_precip / days_n if days_n else 0.0
 
    # ── Regime classification thresholds ──────────────────────────────────
    # These thresholds are descriptive boundaries (e.g. WMO heavy-rain day
    # = >20mm/24h), not cost-validated cutoffs. The multiplier VALUES below
    # them are the estimated component — see module docstring.
    if total_snow > 5 or avg_temp <= -5:
        regime, code = "Deep winter / heavy snow", "deep_winter"
        fuel_mult, shelter_mult = 1.35, 2.2
        rationale = (
            f"Average temperature {avg_temp:.1f}\u00b0C with {total_snow:.1f}cm cumulative "
            "snowfall over the window. Cold-climate evacuation requires winterized shelter "
            "(UNHCR winterization kits; cold-climate Sphere standard 4.5-5.5m2/person vs "
            "3.5m2 baseline) and snow/ice-affected road transport. Fuel/transport penalty "
            "reflects reduced vehicle speed and increased breakdown risk in freezing "
            "conditions; shelter penalty reflects winterized tent/kit cost vs standard "
            "tarpaulin (UNHCR cold-climate program, ~$2,000 vs ~$150-300 per unit at the "
            "premium end \u2014 blended multiplier here is conservative, assuming a mix of "
            "winterized and standard units, not 100% premium)."
        )
    elif avg_temp <= 0:
        regime, code = "Winter / freezing", "winter"
        fuel_mult, shelter_mult = 1.2, 1.6
        rationale = (
            f"Average temperature {avg_temp:.1f}\u00b0C (at or below freezing) over the "
            "window. Increased shelter/heating requirement and moderate transport friction "
            "from cold-affected roads, consistent with UNHCR cold-climate shelter guidance."
        )
    elif precip_per_day > 15 or total_precip > 100:
        regime, code = "Heavy rainy season", "heavy_rain"
        fuel_mult, shelter_mult = 1.8, 1.15
        rationale = (
            f"{total_precip:.0f}mm cumulative precipitation over {days_n} days "
            f"({precip_per_day:.1f}mm/day average). Humanitarian logistics reporting "
            "(Logistics Cluster CAR 2019; MSF/World Vision/Devex Sudan and South Sudan "
            "2018-2026) consistently describes roads as 'mostly impassable' or forcing a "
            "shift to airlift during peak rainy season. Fuel/transport multiplier reflects "
            "detours, reduced vehicle speed on muddy/flooded roads, and partial reliance on "
            "costlier air transport where ground routes fail. This multiplier is a "
            "qualitative estimate \u2014 no single published numeric figure for 'rainy "
            "season road cost increase' was found; treat as directional, not precise."
        )
    elif precip_per_day > 5:
        regime, code = "Moderate rain", "moderate_rain"
        fuel_mult, shelter_mult = 1.25, 1.05
        rationale = (
            f"{total_precip:.0f}mm cumulative precipitation over {days_n} days. Some road "
            "degradation and delivery delay expected but not full impassability."
        )
    elif avg_temp >= 38:
        regime, code = "Extreme heat", "extreme_heat"
        fuel_mult, shelter_mult = 1.15, 1.1
        rationale = (
            f"Average temperature {avg_temp:.1f}\u00b0C. Extreme heat increases vehicle "
            "cooling/maintenance load and water requirement, and shelter must provide shade "
            "and ventilation rather than insulation. Multiplier is a conservative estimate; "
            "no published per-degree cost curve was found."
        )
    else:
        regime, code = "Mild / stable conditions", "mild"
        fuel_mult, shelter_mult = 1.0, 1.0
        rationale = (
            f"Average temperature {avg_temp:.1f}\u00b0C, {total_precip:.0f}mm cumulative "
            "precipitation. No significant climate-driven cost adjustment indicated; "
            "baseline multipliers (1.0x) applied."
        )
 
    if max_wind > 60:
        fuel_mult = round(fuel_mult * 1.1, 3)
        rationale += (
            f" High wind observed (max {max_wind:.0f}km/h daily peak) adds a further +10% "
            "transport penalty (road/air operational caution, debris risk)."
        )
 
    return {
        "regime": regime,
        "regime_code": code,
        "avg_temp_c": round(avg_temp, 1),
        "total_precip_mm": round(total_precip, 1),
        "max_wind_kmh": round(max_wind, 1),
        "total_snowfall_cm": round(total_snow, 1),
        "window_days": days_n,
        "climate_mult": {
            "fuel_transport": round(fuel_mult, 3),
            "shelter": round(shelter_mult, 3),
        },
        "rationale": rationale,
        "confidence": "estimated",
        "weather_data_confidence": "validated",
        "data_ok": True,
    }
 
 
def get_climate_context(lat: Optional[float], lng: Optional[float], start_date: Optional[str]) -> Dict:
    """
    Top-level entry point used by main.py. Returns a complete climate
    context block, or a clean no-op default if location/date are missing
    (so callers don't need None-checks scattered through their code).

    FUTURE-DATE HANDLING (added June 2026)
    ----------------------------------------
    Open-Meteo's Historical Weather API only has data up to ~5 days before
    today (ERA5 reanalysis has a processing delay). If the requested
    start_date is in the future (or within that delay window) \u2014 which is
    expected when a researcher is building a *planning* scenario rather
    than validating a *historical* case \u2014 this function falls back to the
    same calendar month/day in the most recent prior year(s) for which data
    exists, as a climatological proxy. This is standard practice for
    short-lead seasonal estimation when no forecast model is used: "what
    were conditions like at this same time of year historically" is a
    defensible proxy for "what conditions to plan for", though it is NOT
    a forecast and carries no skill about anomalous years (e.g. an
    unusually severe winter). The UI surfaces this explicitly via the
    `proxy_year` and `is_proxy` fields so it is never silently substituted.
    """
    if lat is None or lng is None or not start_date:
        return {
            "regime": "Not specified",
            "regime_code": "not_specified",
            "climate_mult": {"fuel_transport": 1.0, "shelter": 1.0},
            "rationale": "No location and/or start date provided \u2014 climate adjustment "
                         "not applied. Set a conflict location and start date to enable "
                         "seasonal cost modeling.",
            "confidence": "n/a",
            "data_ok": False,
            "is_proxy": False,
        }

    requested_date = start_date
    is_proxy = False
    proxy_year = None

    try:
        requested_dt = datetime.strptime(start_date, "%Y-%m-%d")
        cutoff = datetime.utcnow() - timedelta(days=6)  # ERA5 processing delay safety margin

        if requested_dt > cutoff:
            is_proxy = True
            proxy_dt = requested_dt
            while proxy_dt > cutoff:
                try:
                    proxy_dt = proxy_dt.replace(year=proxy_dt.year - 1)
                except ValueError:
                    proxy_dt = proxy_dt.replace(month=2, day=28, year=proxy_dt.year - 1)
            proxy_year = proxy_dt.year
            start_date = proxy_dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    weather = fetch_historical_weather(lat, lng, start_date)
    result = classify_climate(weather)
    result["is_proxy"] = is_proxy
    result["proxy_year"] = proxy_year
    result["requested_date"] = requested_date
    result["data_date_used"] = start_date

    if is_proxy and result.get("data_ok"):
        target_year = datetime.strptime(requested_date, "%Y-%m-%d").year
        result["rationale"] = (
            f"PLANNING ESTIMATE: {requested_date} is in the future, so no historical "
            f"weather record exists for it yet. This uses the same calendar date in "
            f"{proxy_year} as a climatological proxy (i.e. \u201cwhat conditions were like "
            f"at this time of year historically\u201d), not a forecast \u2014 it carries no "
            f"information about whether {target_year} will be an anomalous year. "
            + result["rationale"]
        )

    return result
 
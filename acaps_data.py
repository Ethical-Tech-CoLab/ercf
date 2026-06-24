"""
ACAPS API client with 24-hour in-memory cache.
Register at https://api.acaps.org/register/ to get a free API key.

Confirmed working endpoints (June 2026):
  /risk-radar/risk-radar/  — 115+ records, iso3 field is a list
  /crises/                 — 384+ records, iso3 field is a list
  /inform-severity-index/  — consistently times out; handled gracefully
  /humanitarian-access/    — consistently times out; handled gracefully
"""
import os
import time
from typing import Dict, List, Optional, Union

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.acaps.org/api/v1"
ACAPS_API_KEY: str = os.getenv("ACAPS_API_KEY", "")
headers: Dict[str, str] = {"Authorization": f"Token {ACAPS_API_KEY}"} if ACAPS_API_KEY else {}

_cache: Dict = {}
_CACHE_TTL = 86400   # 24 hours in seconds
_TIMEOUT   = 20      # seconds per request


# ─── Cache helpers ────────────────────────────────────────────────────────────

def _cached(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _store(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}
    return data


# ─── HTTP helper ──────────────────────────────────────────────────────────────

def _get_pages(path: str, params: Optional[dict] = None) -> List[dict]:
    """Fetch all pages from a paginated DRF endpoint; returns [] on any error."""
    if not ACAPS_API_KEY:
        return []
    all_results: List[dict] = []
    url: Optional[str] = f"{BASE}{path}"
    p = {**(params or {})}
    while url:
        try:
            r = requests.get(url, headers=headers, params=p, timeout=_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception:
            break
        all_results.extend(data.get("results", []))
        url = data.get("next")
        p = {}   # params are already embedded in the `next` URL
    return all_results


def _iso3_matches(field: Union[str, list, None], iso3: str) -> bool:
    """ACAPS API returns iso3 as a list ['SDN'] OR a plain string 'SDN'."""
    if field is None:
        return False
    if isinstance(field, list):
        return iso3 in [v.upper() for v in field]
    return str(field).upper() == iso3


# ─── Public fetchers ──────────────────────────────────────────────────────────

def fetch_inform_severity(date: str = "latest") -> List[dict]:
    """GET {BASE}/inform-severity-index/{date}/

    Returns list of {crisis_id, crisis_name, iso3, country, inform_severity_score}.
    Note: this endpoint is slow and may return an empty list on timeout.
    """
    key = f"inform_severity:{date}"
    cached = _cached(key)
    if cached is not None:
        return cached

    rows = _get_pages(f"/inform-severity-index/{date}/")
    result = [
        {
            "crisis_id":             r.get("crisis_id") or r.get("id"),
            "crisis_name":           r.get("crisis_name") or r.get("name", ""),
            "iso3":                  _normalise_iso3(r.get("iso3")),
            "country":               _normalise_country(r.get("country")),
            "inform_severity_score": r.get("inform_severity_score") or r.get("score"),
        }
        for r in rows
    ]
    return _store(key, result)


def fetch_humanitarian_access(date: str = "latest") -> List[dict]:
    """GET {BASE}/humanitarian-access/{date}/

    Returns list of {iso3, country, access_score, weighted_score}.
    Note: this endpoint is slow and may return an empty list on timeout.
    """
    key = f"humanitarian_access:{date}"
    cached = _cached(key)
    if cached is not None:
        return cached

    rows = _get_pages(f"/humanitarian-access/{date}/")
    result = [
        {
            "iso3":           _normalise_iso3(r.get("iso3")),
            "country":        _normalise_country(r.get("country")),
            "access_score":   r.get("access_score") or r.get("score"),
            "weighted_score": r.get("weighted_score"),
        }
        for r in rows
    ]
    return _store(key, result)


def fetch_risk_radar() -> List[dict]:
    """GET {BASE}/risk-radar/risk-radar/

    Returns list of {risk_id, iso3, country, risk_title, risk_level, risk_trend,
                      intensity_of_hazard, probability, impact}.
    """
    key = "risk_radar"
    cached = _cached(key)
    if cached is not None:
        return cached

    rows = _get_pages("/risk-radar/risk-radar/")
    result = [
        {
            "risk_id":             r.get("risk_id"),
            "iso3":                _normalise_iso3(r.get("iso3")),
            "country":             _normalise_country(r.get("country")),
            "risk_title":          r.get("risk_title") or r.get("title", ""),
            "risk_level":          r.get("risk_level"),
            "risk_trend":          r.get("risk_trend"),
            "intensity_of_hazard": r.get("intensity_of_hazard") or r.get("intensity"),
            "probability":         r.get("probability"),
            "impact":              r.get("impact"),
        }
        for r in rows
    ]
    return _store(key, result)


def fetch_active_crises() -> List[dict]:
    """GET {BASE}/crises/

    Returns list of {crisis_id, crisis_name, iso3, country, active}.
    """
    key = "active_crises"
    cached = _cached(key)
    if cached is not None:
        return cached

    rows = _get_pages("/crises/")
    result = [
        {
            "crisis_id":   r.get("crisis_id"),
            "crisis_name": r.get("crisis_name") or r.get("name", ""),
            "iso3":        _normalise_iso3(r.get("iso3")),
            "country":     _normalise_country(r.get("country")),
            "active":      r.get("active", True),
        }
        for r in rows
    ]
    return _store(key, result)


# ─── Combined country view ────────────────────────────────────────────────────


def get_country_data(iso3: str) -> dict:
    """Call all four endpoints, filter by ISO3, return combined dict.

    Returns {"inform": [...], "access": [...], "risks": [...], "crises": [...]}.
    iso3 is matched case-insensitively against the API's list or string field.
    """
    iso3 = iso3.upper()
    return {
        "inform": [r for r in fetch_inform_severity()     if _iso3_matches(r["iso3"], iso3)],
        "access": [r for r in fetch_humanitarian_access() if _iso3_matches(r["iso3"], iso3)],
        "risks":  [r for r in fetch_risk_radar()          if _iso3_matches(r["iso3"], iso3)],
        "crises": [r for r in fetch_active_crises()       if _iso3_matches(r["iso3"], iso3)],
    }


# ─── Field normalisation ──────────────────────────────────────────────────────


def _normalise_iso3(field) -> str:
    """Return a plain uppercase string regardless of whether the API sent a list or string."""
    if isinstance(field, list):
        return field[0].upper() if field else ""
    return str(field).upper() if field else ""


def _normalise_country(field) -> str:
    if isinstance(field, list):
        return field[0] if field else ""
    return str(field) if field else ""

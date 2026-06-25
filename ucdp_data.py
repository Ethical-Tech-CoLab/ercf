"""
UCDP GED (Georeferenced Event Dataset) integration for ERCF.

Source: Uppsala Conflict Data Program, GED v26.1
API: https://ucdpapi.pcr.uu.se/api/gedevents/26.1
Auth: x-ucdp-access-token header (5,000 requests/day limit)
Bulk CSV: https://ucdp.uu.se/downloads/ged/ged261-csv.zip (no auth, 37MB)
License: CC BY 4.0

Cite as:
  Davies et al. (2025). Organized violence 1989-2024.
  Journal of Peace Research, 62(4).
  Sundberg & Melander (2013). UCDP GED. Journal of Peace Research 50(4).

Query priority:
  1. API (if UCDP_API_TOKEN in env and use_api=True) — real-time, paginated
  2. Local CSV cache (data/ged261.csv) — fast, no rate limit
  3. Download CSV if not cached
"""

import os
import csv
import json
import zipfile
import urllib.request
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

UCDP_API_TOKEN  = os.getenv("UCDP_API_TOKEN", "")
UCDP_API_BASE   = "https://ucdpapi.pcr.uu.se/api/gedevents/26.1"
UCDP_CSV_URL    = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
UCDP_LOCAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ged261.csv")
UCDP_ZIP_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ged261-csv.zip")

# GW (Gleditsch-Ward) numeric country codes required by UCDP API.
# 'Year' parameter is silently ignored by the API — use StartDate/EndDate instead.
# Covers ERCF historical cases; extend as needed.
COUNTRY_GW = {
    "angola":                540,
    "ukraine":               369,
    "israel":                666,   # Gaza Strip coded under Israel in UCDP
    "palestine":             666,
    "bosnia-herzegovina":    346,
    "syria":                 652,
    "iraq":                  645,
    "serbia (yugoslavia)":   345,
    "yugoslavia":            345,
    "central african republic": 482,
    "sudan":                 625,
    "dr congo (zaire)":      490,
    "russia (soviet union)": 365,
    "russia":                365,
    "croatia":               344,
    "vietnam":               816,
    "philippines":           840,
    "lebanon":               660,
    "azerbaijan":            373,
    "myanmar (burma)":       775,
    "ethiopia":               530,
    "somalia":               520,
    "afghanistan":           700,
    "colombia":              100,
    "nigeria":               475,
    "mali":                  432,
    "mozambique":            541,
    "yemen":                 678,
}

# ── API-based query ────────────────────────────────────────────────────────────

def query_ucdp_api(country: str = None,
                   year_start: int = None,
                   year_end: int = None,
                   adm1: str = None,
                   violence_types: list = None,
                   max_pages: int = 20) -> list:
    """
    Query UCDP GED via live API (requires token).
    Limited to 5,000 requests/day. Each page = 1 request.
    Uses pagesize=1000 to minimise request count.

    Args:
        country: Country name as in UCDP (e.g. 'Ukraine', 'Syria')
        year_start / year_end: Year range (inclusive)
        adm1: Province/state filter (partial match applied client-side)
        violence_types: [1=state-based, 2=non-state, 3=one-sided]
        max_pages: Safety cap to avoid burning daily quota (default 20 = 20,000 events max)

    Returns:
        List of event dicts (same schema as query_ucdp CSV version)
    """
    if not UCDP_API_TOKEN:
        raise ValueError("UCDP_API_TOKEN not set in environment. "
                         "Add it to .env or use query_ucdp() for CSV-based queries.")

    headers = {"x-ucdp-access-token": UCDP_API_TOKEN}
    results = []
    page = 0  # UCDP API uses zero-based pagination

    # Resolve country name to GW code for server-side filter
    gw_code = COUNTRY_GW.get(country.lower()) if country else None

    while page <= max_pages:
        params = {"pagesize": 1000, "page": page}
        # Server-side filters — reduces pages from ~418 (full scan) to 1–5.
        # API requires GW numeric codes; 'Year' param is silently ignored, use dates.
        if gw_code:
            params["Country"] = gw_code
        if year_start:
            params["StartDate"] = f"{year_start}-01-01"
        if year_end:
            params["EndDate"] = f"{year_end}-12-31"
        url = f"{UCDP_API_BASE}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[UCDP API] Error on page {page}: {e}")
            break

        events = data.get("Result", [])
        if not events:
            break

        for row in events:
            # Client-side filters (API doesn't support all filters natively)
            if country and row.get("country", "").lower() != country.lower():
                continue
            year = row.get("year", 0)
            if year_start and year < year_start:
                continue
            if year_end and year > year_end:
                continue
            if adm1 and adm1.lower() not in (row.get("adm_1") or "").lower():
                continue
            if violence_types and int(row.get("type_of_violence", 0)) not in violence_types:
                continue

            results.append(_normalise_event(row))

        total_pages = data.get("TotalPages", 1)
        if page >= total_pages:
            break
        page += 1

    return results


def _normalise_event(row: dict) -> dict:
    """Normalise API or CSV row to a consistent schema."""
    return {
        "date_start":        row.get("date_start"),
        "date_end":          row.get("date_end"),
        "year":              int(row.get("year", 0)),
        "country":           row.get("country"),
        "adm_1":             row.get("adm_1"),
        "adm_2":             row.get("adm_2"),
        "where_description": row.get("where_description") or row.get("where_coordinates"),
        "deaths_civilians":  int(row.get("deaths_civilians") or 0),
        "deaths_a":          int(row.get("deaths_a") or 0),
        "deaths_b":          int(row.get("deaths_b") or 0),
        "deaths_unknown":    int(row.get("deaths_unknown") or 0),
        "best":              int(row.get("best") or 0),
        "low":               int(row.get("low") or 0),
        "high":              int(row.get("high") or 0),
        "type_of_violence":  int(row.get("type_of_violence") or 0),
        "conflict_name":     row.get("conflict_name"),
        "dyad_name":         row.get("dyad_name"),
        "source_headline":   (row.get("source_headline") or "")[:200],
    }


# ── CSV-based query (existing, unchanged) ─────────────────────────────────────

def ensure_ucdp_data() -> bool:
    """Download UCDP GED CSV if not already cached locally."""
    os.makedirs(os.path.dirname(UCDP_LOCAL_PATH), exist_ok=True)
    if os.path.exists(UCDP_LOCAL_PATH):
        return True
    print("Downloading UCDP GED v26.1 (~37MB)...")
    try:
        urllib.request.urlretrieve(UCDP_CSV_URL, UCDP_ZIP_PATH)
        with zipfile.ZipFile(UCDP_ZIP_PATH, "r") as z:
            csv_name = [f for f in z.namelist() if f.endswith(".csv")][0]
            with z.open(csv_name) as src, open(UCDP_LOCAL_PATH, "wb") as dst:
                dst.write(src.read())
        os.remove(UCDP_ZIP_PATH)
        print(f"UCDP GED saved to {UCDP_LOCAL_PATH}")
        return True
    except Exception as e:
        print(f"Failed to download UCDP GED: {e}")
        return False


def query_ucdp(country: str = None,
               year_start: int = None,
               year_end: int = None,
               adm1: str = None,
               violence_types: list = None) -> list:
    """
    Query UCDP GED from local CSV cache (no rate limit, fast).
    Falls back to API if CSV not available.
    """
    if not ensure_ucdp_data():
        if UCDP_API_TOKEN:
            print("[UCDP] CSV unavailable, falling back to API...")
            return query_ucdp_api(country, year_start, year_end, adm1, violence_types)
        return []

    results = []
    with open(UCDP_LOCAL_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if country and row.get("country", "").lower() != country.lower():
                continue
            year = int(row.get("year", 0))
            if year_start and year < year_start:
                continue
            if year_end and year > year_end:
                continue
            if adm1 and adm1.lower() not in (row.get("adm_1") or "").lower():
                continue
            if violence_types and int(row.get("type_of_violence", 0)) not in violence_types:
                continue
            results.append(_normalise_event(row))
    return results


# ── Summarise (works with both API and CSV results) ────────────────────────────

def summarise_ucdp(country: str, year_start: int, year_end: int,
                   adm1: str = None, use_api: bool = False) -> dict:
    """
    Summarise UCDP data for a given location/period.

    Args:
        use_api: If True, query live API instead of CSV (uses 1+ requests from daily quota)
    """
    if use_api and UCDP_API_TOKEN:
        events = query_ucdp_api(country, year_start, year_end, adm1)
    else:
        events = query_ucdp(country, year_start, year_end, adm1)

    if not events:
        return {"error": "No events found", "country": country,
                "years": f"{year_start}-{year_end}", "adm1": adm1}

    total_civ  = sum(e["deaths_civilians"] for e in events)
    total_best = sum(e["best"] for e in events)
    total_low  = sum(e["low"] for e in events)
    total_high = sum(e["high"] for e in events)
    one_sided  = [e for e in events if e["type_of_violence"] == 3]

    return {
        "country":                    country,
        "adm1_filter":                adm1,
        "period":                     f"{year_start}-{year_end}",
        "data_source":                "API" if use_api else "CSV",
        "total_events":               len(events),
        "one_sided_events":           len(one_sided),
        "deaths_civilians_explicit":  total_civ,
        "deaths_civilians_one_sided": sum(e["deaths_civilians"] for e in one_sided),
        "total_best":                 total_best,
        "total_low":                  total_low,
        "total_high":                 total_high,
        "uncertainty_range":          f"{total_low:,}–{total_high:,}",
        "note": ("deaths_civilians = explicitly identified civilian deaths (floor). "
                 "best/low/high = total fatality range including combatants."),
        "ucdp_citation": ("Davies et al. (2025), Journal of Peace Research 62(4); "
                          "Sundberg & Melander (2013), JPR 50(4)."),
    }


# ── API health check ───────────────────────────────────────────────────────────

def check_api_status() -> dict:
    """Test API connectivity and token validity. Uses 1 request."""
    if not UCDP_API_TOKEN:
        return {"status": "no_token", "message": "UCDP_API_TOKEN not set"}
    try:
        url = f"{UCDP_API_BASE}?pagesize=1&page=0"
        req = urllib.request.Request(url, headers={"x-ucdp-access-token": UCDP_API_TOKEN})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return {
            "status":       "ok",
            "total_events": data.get("TotalCount"),
            "token_valid":  True,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "token_valid": False}


if __name__ == "__main__":
    print("=== UCDP API status ===")
    status = check_api_status()
    print(status)
    print()
    print("=== Angola 1993 Huambo (CSV) ===")
    r = summarise_ucdp("Angola", 1993, 1993, adm1="Huambo")
    for k, v in r.items():
        print(f"  {k}: {v}")
    print()
    print("=== Angola 1993 Huambo (API) ===")
    r2 = summarise_ucdp("Angola", 1993, 1993, adm1="Huambo", use_api=True)
    for k, v in r2.items():
        print(f"  {k}: {v}")

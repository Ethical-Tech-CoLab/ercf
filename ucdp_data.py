"""
UCDP GED (Georeferenced Event Dataset) integration for ERCF.

Source: Uppsala Conflict Data Program, GED v26.1
URL: https://ucdp.uu.se/downloads/ged/ged261-csv.zip
License: CC BY 4.0 — cite as:
  Davies et al. (2025). Organized violence 1989–2024.
  Journal of Peace Research, 62(4).
  Sundberg & Melander (2013). UCDP GED. Journal of Peace Research 50(4).

No API token required — bulk CSV is publicly accessible.
deaths_civilians: explicitly identified civilian deaths (floor estimate)
best/low/high: total fatality uncertainty range
type_of_violence: 1=state-based, 2=non-state, 3=one-sided (deliberate civilian targeting)
"""

import os
import csv
import zipfile
import urllib.request

UCDP_CSV_URL = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
UCDP_LOCAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ged261.csv")
UCDP_ZIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ged261-csv.zip")


def ensure_ucdp_data():
    """Download UCDP GED CSV if not already cached locally."""
    os.makedirs(os.path.dirname(UCDP_LOCAL_PATH), exist_ok=True)
    if os.path.exists(UCDP_LOCAL_PATH):
        return True
    print("Downloading UCDP GED v26.1 (~37MB)...")
    try:
        urllib.request.urlretrieve(UCDP_CSV_URL, UCDP_ZIP_PATH)
        with zipfile.ZipFile(UCDP_ZIP_PATH, 'r') as z:
            csv_name = [f for f in z.namelist() if f.endswith('.csv')][0]
            with z.open(csv_name) as src, open(UCDP_LOCAL_PATH, 'wb') as dst:
                dst.write(src.read())
        os.remove(UCDP_ZIP_PATH)
        print(f"UCDP GED saved to {UCDP_LOCAL_PATH}")
        return True
    except Exception as e:
        print(f"Failed to download UCDP GED: {e}")
        return False


def query_ucdp(country=None, year_start=None, year_end=None,
               adm1=None, violence_types=None):
    """
    Query UCDP GED data with filters.

    Args:
        country: Country name (e.g. 'Angola', 'Syria', 'Ukraine')
        year_start: Start year (inclusive)
        year_end: End year (inclusive)
        adm1: Admin level 1 filter (province/state name, partial match)
        violence_types: List of int [1=state-based, 2=non-state, 3=one-sided]

    Returns:
        List of event dicts with fields: date_start, date_end, country, adm_1, adm_2,
        where_description, deaths_civilians, deaths_a, deaths_b, deaths_unknown,
        best, low, high, type_of_violence, conflict_name, dyad_name, source_headline
    """
    if not ensure_ucdp_data():
        return []

    results = []
    with open(UCDP_LOCAL_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if country and row.get('country', '').lower() != country.lower():
                continue
            year = int(row.get('year', 0))
            if year_start and year < year_start:
                continue
            if year_end and year > year_end:
                continue
            if adm1 and adm1.lower() not in row.get('adm_1', '').lower():
                continue
            if violence_types and int(row.get('type_of_violence', 0)) not in violence_types:
                continue
            results.append({
                'date_start': row.get('date_start'),
                'date_end': row.get('date_end'),
                'year': year,
                'country': row.get('country'),
                'adm_1': row.get('adm_1'),
                'adm_2': row.get('adm_2'),
                'where_description': row.get('where_description'),
                'deaths_civilians': int(row.get('deaths_civilians') or 0),
                'deaths_a': int(row.get('deaths_a') or 0),
                'deaths_b': int(row.get('deaths_b') or 0),
                'deaths_unknown': int(row.get('deaths_unknown') or 0),
                'best': int(row.get('best') or 0),
                'low': int(row.get('low') or 0),
                'high': int(row.get('high') or 0),
                'type_of_violence': int(row.get('type_of_violence') or 0),
                'conflict_name': row.get('conflict_name'),
                'dyad_name': row.get('dyad_name'),
                'source_headline': row.get('source_headline', '')[:200],
            })
    return results


def summarise_ucdp(country, year_start, year_end, adm1=None):
    """
    Summarise UCDP data for a given location/period.
    Returns aggregate statistics suitable for ERCF calibration.
    """
    events = query_ucdp(country=country, year_start=year_start, year_end=year_end, adm1=adm1)
    if not events:
        return {"error": "No events found", "country": country, "years": f"{year_start}-{year_end}"}

    total_civilian = sum(e['deaths_civilians'] for e in events)
    total_best = sum(e['best'] for e in events)
    total_low = sum(e['low'] for e in events)
    total_high = sum(e['high'] for e in events)
    one_sided = [e for e in events if e['type_of_violence'] == 3]

    return {
        "country": country,
        "adm1_filter": adm1,
        "period": f"{year_start}-{year_end}",
        "total_events": len(events),
        "one_sided_events": len(one_sided),
        "deaths_civilians_explicit": total_civilian,
        "deaths_civilians_one_sided": sum(e['deaths_civilians'] for e in one_sided),
        "total_best": total_best,
        "total_low": total_low,
        "total_high": total_high,
        "uncertainty_range": f"{total_low:,}–{total_high:,}",
        "sources": list(set(e['source_headline'] for e in events if e['source_headline']))[:5],
        "note": "deaths_civilians = explicitly identified civilian deaths (floor). best/low/high = total fatality range including combatants.",
        "ucdp_citation": "Davies et al. (2025), Journal of Peace Research 62(4); Sundberg & Melander (2013), JPR 50(4).",
    }


if __name__ == "__main__":
    # Test: Angola 1993 Huambo
    print("=== UCDP GED — Angola 1993, Huambo ===")
    result = summarise_ucdp("Angola", 1993, 1993, adm1="Huambo")
    for k, v in result.items():
        print(f"  {k}: {v}")

    print()
    print("=== UCDP GED — Angola 1993, All ===")
    result2 = summarise_ucdp("Angola", 1993, 1993)
    for k, v in result2.items():
        print(f"  {k}: {v}")

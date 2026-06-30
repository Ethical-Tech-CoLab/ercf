# ERCF — Architecture Document

## System Overview

```
Browser (HTML/JS/Chart.js/Leaflet)
         ↕ HTTP / JSON
FastAPI (Python 3.x)
         ↕                    ↕                      ↕                    ↕
      SQLite            UCDP GED API           ACAPS/INFORM API      GeoNames API
  (evacuation_risk.db)  (ucdp.uu.se/api)      (api.acaps.org)     (api.geonames.org)
```

All computation runs server-side in Python. The browser receives JSON and renders results — no client-side calculation of cost or mortality figures except for the real-time UI feedback path in app.js (which replicates the server-side formulas for instant response without a round-trip).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI 0.111.0 |
| ASGI server | Uvicorn 0.29.0 |
| Data validation | Pydantic 2.7.1 |
| Database | SQLite (via stdlib `sqlite3`) |
| AI context | Anthropic SDK ≥0.107.0 |
| HTTP client | requests ≥2.31.0 |
| Config | python-dotenv ≥1.0.0 |
| Frontend framework | Bootstrap 5.3.3 |
| Charts | Chart.js 4.4.3 |
| Maps | Leaflet 1.9.4 |
| Topology | TopoJSON client 3.1.0 |
| Markdown render | marked.js 9.1.6 |
| Calibration | scipy 1.13.1, statsmodels 0.14.6, numpy |

## File Structure

```
evacuation-risk-tool/
├── main.py                 # FastAPI app, all API endpoints, startup hook
├── calculators.py          # Core computation: risk, resources, mortality, remaining costs
├── database.py             # SQLite schema, migrations, CRUD for saved scenarios
├── historical_data.py      # 31 documented conflict cases (1991–2024) with full metadata
├── demographic_data.py     # 18-country vulnerable population dataset (UNICEF/UN DESA 2023)
├── acaps_data.py           # ACAPS/INFORM API client with in-memory caching
├── world_risk.py           # World risk index: ACAPS data → country-level risk levels
├── context_ai.py           # Claude API integration for country context narratives
├── air_evac.py             # Air evacuation cost model (UNHAS rate, sorties, fleet)
├── walking_evac.py         # Walking evacuation model (speed, attrition, days)
├── weather_data.py         # Seasonal terrain factor calculation by lat/month
├── ucdp_data.py            # UCDP GED v26.1 API client and CSV fallback
├── requirements.txt        # Python dependencies
├── evacuation_risk.db      # SQLite database (auto-created on startup)
├── data/
│   └── ged261.csv          # UCDP GED v26.1 local CSV (fallback when API unavailable)
├── static/
│   ├── index.html          # Single-page application (all tabs, modals, UI)
│   ├── app.js              # All frontend logic (~4,900 lines)
│   └── countries-110m.json # TopoJSON for world map choropleth
├── calibration/
│   ├── calibrate.py        # Run v7 model against 16 in-scope cases; R², LOOCV, within-2×
│   ├── full_calibration.py # Optimise base rates + α via differential_evolution (scipy)
│   └── validate_v7.py      # Full statistical validation: Shapiro-Wilk, BP, Cook's D, etc.
├── CONCEPT.md              # Concept document: problem, ethics, philosophy, limitations
├── ARCHITECTURE.md         # This file
├── BACKLOG.md              # Product backlog and known technical debt
└── README.md               # Project overview, calibration metrics, installation
```

## Key Modules

### calculators.py

| Function | Description |
|----------|-------------|
| `calculate_risk(scores)` | 7-dimension weighted score → risk level (0–4) + NATO equivalent |
| `infra_denial_mult(flag, d1, d4)` | Infrastructure-denial multiplier (α=0.4251) for 4 calibration cases |
| `get_seasonal_terrain_factor(terrain, lat, month)` | Seasonal terrain modifier by latitude and month |
| `calculate_resources(pop, ...)` | Full evacuation cost: transport, fuel, personnel, food, water, shelter, medical, comms, contingency |
| `calculate_injuries(pop, level, days)` | Cumulative injury estimate (ICRC 4:1 ratio) |
| `calculate_staying_costs(pop, level, days, ...)` | Mortality model v7: base rates × confinement × exposure × infra-denial |
| `calculate_remaining_costs(pop, vuln_pct, level, days, ...)` | In-zone assistance cost: supply delivery + emergency extraction + field medical |

### app.js (frontend, ~4,900 lines)

| Function | Description |
|----------|-------------|
| `updateAll()` | Main calculation loop — called on every input change |
| `calcRisk(dims)` | Client-side risk score replication for instant feedback |
| `calcResources(pop, ...)` | Client-side evacuation cost replication |
| `calcStay(pop, level, days, ...)` | Client-side mortality model for chart rendering |
| `calcRemaining(pop, ...)` | Client-side in-zone assistance cost |
| `updateDecisionAnalysis(evacCost, dailyCostA, dailyCostB)` | Break-even chart: Option A vs Option B |
| `renderHistTable(filter)` | Historical cases tab with OOS/CHAL badges |
| `renderRadarUcdpBlock(compHistCase)` | Compare on Radar: UCDP validation + cost comparison table |
| `renderCostComparePanel()` | Full 7-metric comparison panel (current vs historical/saved) |
| `applyCityPop(r)` | City autocomplete: populate population, open pin modal automatically |
| `confirmPinDistance()` | Confirm pin positions, calculate haversine distance |
| `_runAiSuggestion(lat, lng)` | Load world risk data, compute nearest safe zones |

### main.py (API endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve index.html |
| GET | `/README.md` | Serve README.md as plain text (for About modal) |
| GET | `/api/scenarios` | List all saved scenarios |
| POST | `/api/scenarios` | Create a new saved scenario |
| GET | `/api/scenarios/{id}` | Get a single saved scenario |
| PUT | `/api/scenarios/{id}` | Update a saved scenario |
| DELETE | `/api/scenarios/{id}` | Delete a saved scenario |
| POST | `/api/calculate/risk` | Calculate risk score from 7 dimensions |
| POST | `/api/calculate/resources` | Calculate evacuation cost |
| POST | `/api/calculate/staying-cost` | Calculate mortality model output |
| POST | `/api/calculate/remaining-cost` | Calculate in-zone assistance cost |
| POST | `/api/air-evacuation` | Calculate air evacuation (sorties, cost) |
| POST | `/api/walking-evacuation` | Calculate walking evacuation (days, attrition) |
| POST | `/api/climate` | Get climate/seasonal context for a location |
| GET | `/api/historical-cases` | List all 31 historical cases with enriched data |
| GET | `/api/historical-cases/{id}` | Get a single historical case |
| GET | `/api/city-population/{name}` | GeoNames city population lookup (18 countries) |
| GET | `/api/demographics/{country}` | Vulnerable population % suggestion |
| GET | `/api/ucdp` | UCDP GED event query (date/bbox filter) |
| GET | `/api/ucdp/status` | UCDP API availability status |
| GET | `/api/world-risk` | All country risk levels (ACAPS/INFORM) |
| GET | `/api/world-risk/{iso3}` | Single country risk level |
| GET | `/api/iso-lookup` | ISO3 → country name lookup table |
| POST | `/api/country-context` | Claude API country narrative (AI-generated) |
| GET | `/api/acaps/{iso3}` | Raw ACAPS data for a country |
| GET | `/api/country-context-acaps/{iso3}` | ACAPS-enriched country context |

## Data Flow

```
User input (sliders, fields)
        ↓
updateAll() [app.js]
        ↓
calcRisk() / calcResources() / calcStay() / calcRemaining()  [client-side replicas]
        ↓
DOM update (cards, charts, decision analysis)

[On save]         POST /api/scenarios           →  SQLite
[On map pin]      haversine(conflict, safezone) →  state.distanceKm
[On city select]  GET /api/city-population      →  GeoNames API
[On UCDP]         GET /api/ucdp                 →  UCDP GED API or ged261.csv fallback
[On world map]    GET /api/world-risk            →  ACAPS/INFORM API (cached per session)
[On country ctx]  POST /api/country-context      →  Anthropic Claude API
```

## Database Schema

SQLite, single table `scenarios` with versioned migrations (`_migrate_db`):

```sql
CREATE TABLE scenarios (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT    NOT NULL,
    description          TEXT    DEFAULT '',
    population           INTEGER NOT NULL,
    vulnerable_pct       REAL    DEFAULT 20.0,
    distance_km          REAL    DEFAULT 50.0,
    d1_kinetic           REAL    NOT NULL,
    d2_vulnerability     REAL    NOT NULL,
    d3_political         REAL    NOT NULL,
    d4_logistics         REAL    NOT NULL,
    d5_destination       REAL    NOT NULL,
    d6_urgency           REAL    NOT NULL,
    d7_information       REAL    NOT NULL,
    risk_score           REAL,
    risk_level           INTEGER,
    risk_label           TEXT,
    nato_equivalent      TEXT,
    created_at           TEXT    DEFAULT CURRENT_TIMESTAMP,
    -- Migration v1 (geolocation + operational columns):
    conflict_lat         REAL    DEFAULT NULL,
    conflict_lng         REAL    DEFAULT NULL,
    safe_zone_lat        REAL    DEFAULT NULL,
    safe_zone_lng        REAL    DEFAULT NULL,
    safe_zone_name       TEXT    DEFAULT NULL,
    distance_source      TEXT    DEFAULT 'manual',
    road_factor_applied  INTEGER DEFAULT 0,
    haversine_km         REAL    DEFAULT NULL,
    terrain              INTEGER DEFAULT 3,
    conflict_pattern     INTEGER DEFAULT 5
);
```

## Calibration Pipeline

```
historical_data.py  ──→  31 documented cases (1991–2024)
                              │
                    ┌─────────┴──────────┐
                    │ 16 in-scope cases   │  15 out-of-scope (OOS badge)
                    └─────────┬──────────┘  + 2 challenge cases (CHAL badge)
                              │
              calibration/full_calibration.py
              (scipy.optimize.differential_evolution)
              Variant B: base rates [L0–L4] + α jointly optimised
                              │
                    Base rates v7: [0.777, 0.964, 3.625, 1.805, 1.000] /10K/day
                    α = 0.4251  (infra-denial multiplier for 4 cases)
                              │
              calibration/calibrate.py
              R²=0.855, LOOCV R²=0.807, 7/16 within 2× (44%)
                              │
              calibration/validate_v7.py
              Shapiro-Wilk W=0.974, Breusch-Pagan LM=0.316,
              Cook's D (Aleppo D=0.613, NOTE), Spearman ρ=0.845,
              DW=1.413, VIF max=3.90
```

## External Data Sources

| Source | Endpoint | Update frequency | Auth required | Notes |
|--------|----------|-----------------|---------------|-------|
| UCDP GED v26.1 | `ucdp.uu.se/api/gedevents/v26.1` | Annual | `UCDP_API_TOKEN` env var | CSV fallback: `data/ged261.csv` |
| ACAPS/INFORM | `api.acaps.org` | Monthly | Public API | In-memory cache per session |
| GeoNames | `api.geonames.org` | Continuous | `GEONAMES_USERNAME` env var | 10,000 free credits/day; 18-country scope |
| Anthropic Claude | Anthropic SDK | On-demand | `ANTHROPIC_API_KEY` env var | Country context narratives only |

ERCF — Evacuation Risk Classification Framework
=================================================

Overview
--------
This Python project is a small web service and UI for modelling evacuation risk and resource estimates. It provides a REST API (FastAPI), calculation logic, country/context enrichment (ACAPS + optional AI), a small static frontend, and a local SQLite database storing "scenarios".

Primary components
------------------
- API server: main.py (FastAPI), exposes CRUD and calculation endpoints.
- Calculations: calculators.py — risk, resources, staying and remaining cost calculations.
- Persistence: database.py — SQLite (evacuation_risk.db) with a single main table `scenarios`.
- External data: acaps_data.py — ACAPS HTTP client with 24h in-memory cache.
- Context AI: context_ai.py — Anthropics/Claude integration with a static fallback (uses world_risk).
- Static frontend: static/ (index.html, app.js, topojson assets).
- World risk data: world_risk.py — static country risk lookup used by context_ai and API.
- Historical reference: historical_data.py — list of historical cases exposed by API.

Database (persistence)
----------------------
- Database: SQLite at DB_PATH = "evacuation_risk.db" (file in project). init_db() creates table if missing.

Main table: scenarios
- id (INTEGER PK AUTOINCREMENT)
- name (TEXT, NOT NULL)
- description (TEXT)
- population (INTEGER)
- vulnerable_pct (REAL)
- distance_km (REAL)
- d1_kinetic .. d7_information (REAL) — the 7 ERCF dimensions
- risk_score (REAL)
- risk_level (INTEGER) — ERCF 0..4
- risk_label (TEXT)
- nato_equivalent (TEXT)
- created_at (TEXT, default CURRENT_TIMESTAMP)
- conflict_lat, conflict_lng, safe_zone_lat, safe_zone_lng, safe_zone_name
- distance_source, road_factor_applied, haversine_km, terrain, conflict_pattern

Notes: migrations are handled idempotently by _migrate_db adding columns if missing.

API surface (high level)
-------------------------
- /api/scenarios [GET] — list
- /api/scenarios [POST] — create (calculates risk before insert)
- /api/scenarios/{id} [GET|PUT|DELETE] — CRUD
- /api/calculate/risk [POST] — returns risk dimensions->score/level
- /api/calculate/resources [POST] — resource planning
- /api/calculate/staying-cost [POST] — cost to remain
- /api/calculate/remaining-cost [POST] — cost of remaining population
- /api/historical-cases [GET]
- /api/world-risk [GET], /api/world-risk/{iso3} — static lookup
- /api/acaps/{iso3} — ACAPS combined country data (requires ACAPS_API_KEY)
- /api/country-context [POST] — AI-powered analysis (requires ANTHROPIC_API_KEY, otherwise fallback)

Data flow
---------
1. Client -> FastAPI endpoints (static UI or external client)
2. For scenario create/update: request validated via Pydantic, calculators.calculate_risk invoked (local CPU), merged with input and stored in SQLite.
3. For country context: context_ai -> world_risk + optional Anthropics API; fallback uses static world_risk data.
4. For ACAPS: acaps_data queries external ACAPS endpoints with Token, caches results in-process for 24h.
5. Static UI reads /api endpoints and consumes TopoJSON assets from static/.

External dependencies and environment
-------------------------------------
- ACAPS API: requires ACAPS_API_KEY in env (.env supported). acaps_data.py does requests with 20s timeout and 24h TTL cache.
- Anthropics (Claude): optional ANTHROPIC_API_KEY for AI-powered country analysis. If missing, context_ai uses fallback static data.
- Python packages: fastapi, uvicorn, pydantic, requests, python-dotenv, anthropic (optional) — see requirements.txt.

Operational considerations & recommendations
-------------------------------------------
Short-term (minimal):
- Run as a container or via uvicorn for local/demo use. Keep SQLite for small scale.
- Ensure .env has ACAPS_API_KEY and ANTHROPIC_API_KEY if AI/ACAPS features desired.

Production-hardening suggestions:
- Replace SQLite with PostgreSQL (data durability, concurrent writes). Add SQLAlchemy or use connection pooling.
- Move ACAPS cache to Redis (shared cache across instances) and add background refresh jobs.
- Protect APIs with auth (API key or OAuth) if exposed publicly.
- Add structured logging and monitoring (Prometheus/Cloudwatch), and health checks.
- Rate-limit calls to external APIs and implement retry/backoff for ACAPS/Anthropic.

Security & privacy
------------------
- Do not commit API keys. Use .env for local dev and secrets management for production.
- The code does not currently authenticate requests — add authentication before public deployment.

Testing & validation
--------------------
- Add unit tests for calculators.py (risk and resource logic) and for database CRUD flows.
- Add integration tests covering endpoints and ACAPS fallback behavior (mock external APIs).

Short diagram (text)
---------------------
Client (browser) --> FastAPI (main.py)
    - Serves static/ (UI)
    - Exposes REST endpoints
    - Calls calculators.py (local) -> returns risk/resource results
    - Persists scenarios to SQLite via database.py
    - Calls acaps_data.py (external) or world_risk.py (static)

Files of interest
-----------------
- main.py — application entry, endpoints, startup
- calculators.py — core business logic
- database.py — SQLite helpers + schema
- acaps_data.py — external data client + cache
- context_ai.py — AI + fallback
- world_risk.py — static country risk dataset
- static/ — frontend

Next steps (suggested)
----------------------
- Confirm desired filename/location (ARCHITECTURE.md created in repo root).
- If wanted, generate a diagram image (PlantUML) or a README section for deploy/ops.
- Optionally migrate DB to Postgres and add a simple docker-compose for local dev.

Generated: June 2026

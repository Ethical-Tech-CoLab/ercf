# RICS — Resettlement & Inclusion Capacity Simulator
## Design Document v0.2

v0.2 correction: confMult now propagates into Layer 1's break-even band (§7), not only
Layer 2's readiness match — per report p.9/§5's explicit framing. See §7 for the resolved
mechanism (interval arithmetic via `base_uncertainty_pct`, not a second Monte Carlo).

Grounding: *After the Corridor* (Ethical Tech CoLab / NYU CGA, Jul 2026) §5, §7, §9;
`evacuation-risk-tool/calculators.py`, `main.py`, `database.py` (ERCF v7.2);
`reference/india-evac/index.html`, `ARCHITECTURE.md`, `BACKLOG.md` (Readiness & Uncertainty Simulator).

This document exists because §14 of the report states the operating principle directly:
*"Measurement before deployment... nothing here is operational decision-support before
validation."* Every component below is mapped against a specific function in an existing,
read codebase before any new code is written. Where no source function exists, that is
stated explicitly rather than implied.

---

## 1. Three-layer architecture

RICS is not a new application — it is ERCF's cost engine and the Readiness & Uncertainty
Simulator's capacity engine, re-pointed at Dzaleka and composed behind one API, per §9's
table ("Adapt — engine in place").

```
Layer 1 — Cost           Layer 2 — Capacity/Willingness      Layer 3 — Uncertainty
(calculators.py,          (index.html: computeReadiness,      (index.html: confMult,
 app.js break-even)        monteCarlo, assign)                 uncertaintyLevel slider)
      │                          │                                    │
      └──────────────┬───────────┴───────────────┬────────────────────┘
                      │                           │
              cost_engine.py              readiness_engine.py
                      │                           │
                      └───────────┬───────────────┘
                                   │
                              main.py (FastAPI)
                                   │
                              static/ (break-even chart + capacity matrix)
```

---

## 2. Traceability — every RICS module against its source

| RICS component | Source | Function/section | Disposition |
|---|---|---|---|
| Trajectory A (status-quo annual cost) | `calculators.py:666` | `calculate_resources()` line items (water/food/shelter/medical) | **Adapt** — Sphere unit costs reused verbatim; annualized instead of 3-day convoy sizing; new protection/admin line |
| Funding-shortfall multiplier | `calculators.py:569` | `infra_denial_mult()` | **Adapt** — same α-scaled-penalty shape, new driver (% appeal funded, not D1/D4 conflict score), needs its own α |
| Trajectory B (upfront inclusion investment) | — | — | **New** — no ERCF equivalent; documentation/legal cost, skills credentialing (§6.3 Arts Provenance Agent VC), transport (reuses `calculate_resources()` vehicle/fuel lines), start-up capital, host co-investment |
| Break-even computation + chart | `static/app.js:1873–2032` | `updateDecisionAnalysis`, `_renderDecisionChart` | **Adapt** — `Math.ceil(evacCost / diff)` arithmetic unchanged; day-axis → year-axis; 90-day cap → multi-year horizon; Option A/B relabeled; now also takes shared `confMult` to widen the output into `breakeven_year_low/high` (§7 — corrected in v0.2, per report p.9/§5) |
| Gatekeeper scoring (Security, Legal Consent, Host Willingness) | `index.html:682` | `computeReadiness()` | **Direct reuse** — weighted-avg formula + `GK_BLOCKED_CAP=0.20` unchanged |
| Unknown-vs-Unwilling distinction | `index.html:590–596` | `statusLabel()`, `blockedGkFactors()` | **Direct reuse, do not modify** — explicitly load-bearing per report §3.5/§5 |
| Monte Carlo outcome distribution | `index.html:711–738` | `perturbStatus()`, `monteCarlo()` | **Direct reuse** — 500 runs, confMult-scaled perturbation unchanged |
| Uncertainty slider | `index.html:1188,1259,1305` | `confMult = 1 - uncertaintyLevel` | **Direct reuse** |
| Counterfactual info-value ("resolve this Unknown, gain X% success") | `index.html:795+` | `assignForInfoValue()`, `computeInfoValue()` | **Direct reuse** — directly answers §8's advocacy-evidence ask |
| Cohort/pathway assignment | `index.html:756` | `assign()` | **Direct reuse of algorithm** — urgency-sort → protection-priority sort; capacity contention becomes real (finite quotas) |
| Composite ranking score | `index.html:744` | `compositeScore()` | **Adapt** — `vulnMatch` heuristic re-keyed to new `services` factor; `prox` term reinterpreted (§3 below) |
| Standard factor set (Capacity, Shelter, Food&water, Medical) | `index.html:574–582` | `FACTORS` | **Redesigned** — collapses to Housing, Jobs, Services per report's exact "housing, jobs, services" wording; `Jobs` has no prior analogue |
| Synthetic destinations | `index.html:636` | `generateDestinations()` | **Not reused** — RNG-synthetic by design (CONCEPT.md: "nothing here is real location data"); replaced by 3 sourced pathway categories (§4 below) |
| Synthetic evacuee archetypes | `index.html:598–607,663` | `ARCHETYPES`, `generateGroups()` | **Not reused** — replaced by aggregate Dzaleka cohorts (nationality × vulnerability × legal status), counts only, per §7 |
| `distance` factor | `index.html:543–544,747` | `DIST_MIN/MAX`, `prox` term | **Reinterpreted** — becomes administrative-complexity proxy (processing steps/days), not physical km; formula shape unchanged |
| Cost/readiness/uncertainty constants | `calculators.py` docstrings; `index.html:523–572` `PARAMS`/`PARAM_DOCS` | prose only, no machine-readable tags today | **New artifact required** — `parameter_registry.py` (§5 below), since §10.1/§13 commit to "full parameter table public" |
| Scenario storage | `database.py` (single `scenarios` table, one row per evacuation decision) | `_migrate_db`, `create_scenario` | **Pattern reuse, new schema** — RICS needs cohort snapshots + pathway definitions + cost scenarios, never individual-level rows (§6) |
| Biometric/identity data | — | DDC-0001 (report §7, §9) | **Explicitly excluded** — no field, no table, no exception |

---

## 3. Composite score reinterpretation

Original `compositeScore()`:
```
comp = readiness × W_READINESS + capFit × W_CAPACITY + prox × W_PROXIMITY + vulnMatch × W_VULN
```
RICS keeps this shape. Reinterpretations:
- `capFit = min(1, pathway.capacity / cohort.size)` — `capacity` is now a real annual quota
  (resettlement slots, work permits), not an exponentially-distributed synthetic bed count.
- `prox` — renamed `adminSimplicity`, computed the same way against `admin_complexity`
  (processing steps or median days) instead of km. `W_PROXIMITY` renamed `W_ADMIN` in
  `PARAMS`; value unchanged pending sensitivity review.
- `vulnMatch` — keyed to the new `services` factor (health/education/protection access)
  against the cohort's actual need tag (child-protection, chronic-illness care, GBV
  response), replacing the original's single `medical.status==='operational'` check.

---

## 4. Pathway data model (replaces `generateDestinations`)

Three categories, confirmed in scope for v1:

1. **Local integration in Malawi** (work-rights pathway) — Legal Consent gatekeeper is
   currently high-confidence `blocked` per the encampment policy documented in report §4,
   not an `Unknown`. This is a real, sourced status, not a Monte Carlo draw.
2. **Voluntary return**, disaggregated by origin — DRC, Burundi, Rwanda each get an
   independent Security/Legal Consent/Willingness assessment (conditions differ materially
   by country).
3. **Third-country resettlement**, disaggregated by destination state — US/Canada/EU quotas,
   each a distinct pathway with its own sourced `capacity` (real quota size) and legal-status
   factors.

Each pathway factor status carries the same Validated/Estimated/Unvalidated tag as ERCF's
cost parameters — sourced to UNHCR resettlement statistics, host-state policy documents, or
explicitly marked as an unconfirmed placeholder pending field validation (§10.1's FSF
partnership is the mechanism for closing Unvalidated → Validated over the grant term).

```python
# pathways.py — illustrative shape, not final schema
PATHWAYS = {
    "malawi_local_integration": {
        "category": "local_integration",
        "capacity": {"value": None, "tag": "unvalidated", "source": "pending FSF/government data"},
        "admin_complexity": {"value": None, "tag": "unvalidated", "source": None},
        "factors": {
            "security":        {"status": "operational", "base_conf": 0.7, "tag": "estimated", "source": "..."},
            "legal_consent":   {"status": "blocked",     "base_conf": 0.9, "tag": "validated",  "source": "Malawi encampment policy, Mar 2023 (report §4)"},
            "host_willingness":{"status": "blocked",     "base_conf": 0.8, "tag": "estimated",  "source": "Inua Advocacy reporting (report §4)"},
            "housing":         {"status": "unknown",      "base_conf": 0.3, "tag": "unvalidated", "source": None},
            "jobs":            {"status": "unknown",      "base_conf": 0.3, "tag": "unvalidated", "source": None},
            "services":        {"status": "partial",      "base_conf": 0.5, "tag": "estimated",  "source": "..."},
        },
    },
    # "voluntary_return_drc", "voluntary_return_burundi", "voluntary_return_rwanda",
    # "resettlement_usa", "resettlement_canada", "resettlement_eu" — same shape
}
```

---

## 5. Parameter registry (new, shared across all 3 layers)

Report §10.1/§13 commit to shipping "every cost parameter tagged... full parameter table
public" as a grant deliverable. Today that discipline lives only in `calculators.py`
docstring prose and `index.html`'s `PARAM_DOCS` (descriptions, no tags). RICS needs one
machine-readable source of truth both layers read from and the grant report exports from.

```python
# parameter_registry.py — schema, one entry per parameter
{
    "water_l_per_person_day": {
        "value": 20, "unit": "L/person/day", "layer": "cost",
        "tag": "validated", "base_uncertainty_pct": 0.10,
        "source": "UNHCR WASH Manual",
        "source_url": "...", "last_reviewed": "2026-06",
    },
    "gk_blocked_cap": {
        "value": 0.20, "unit": "readiness fraction", "layer": "readiness",
        "tag": "unvalidated", "source": "India-EvacSimulation PARAMS (uncalibrated per its own BACKLOG.md)",
        "source_url": None, "last_reviewed": None,
    },
    "success_min_readiness": {
        "value": 0.40, "unit": "readiness fraction", "layer": "readiness",
        "tag": "unvalidated", "source": "India-EvacSimulation PARAMS",
        "source_url": None, "last_reviewed": None,
    },
    # ... every calculators.py cost line + every index.html PARAMS entry
}
```
`base_uncertainty_pct` defaults by tag (`validated=0.10`, `estimated=0.30`, `unvalidated=0.60`)
unless a parameter overrides it explicitly — this is the value `cost_engine.py` reads to widen
Layer 1's break-even band under `confMult` (§7 below).

`PARAMETER_REGISTRY.md` is a generated (not hand-written) rendering of this file — closes
the exact drift risk BACKLOG.md flags for the simulator's methodology docx ("claims to be
auto-generated... isn't").

---

## 6. Cohort data model — aggregate only, no individual records

Hard constraint from §7 (Rohingya/BIMS case) and §9 ("Absent by design: any biometric or
identity system"), extended here beyond identity into **statistical aggregation**: a cohort
cell small enough to be re-identifiable is itself a risk, even with no name attached.

```sql
CREATE TABLE cohorts (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date        TEXT    NOT NULL,
    nationality          TEXT    NOT NULL,   -- drc | burundi | rwanda | other
    vulnerability_category TEXT  NOT NULL,   -- elderly | disabled | unaccompanied_minor |
                                              -- female_headed_household | chronic_illness | general
    legal_status         TEXT    NOT NULL,   -- registered_refugee | asylum_seeker | undetermined
    count                INTEGER NOT NULL CHECK (count >= 20),  -- k-anonymity floor, see below
    source                TEXT,
    tag                   TEXT    DEFAULT 'unvalidated'
);
```
`count >= 20` is a placeholder k-anonymity floor (open item — needs a real minimum-cell-size
decision, likely from FSF's field-survey design in Phase 2 per the report's work plan). Cells
below the floor must be merged into a coarser category, never reported at sub-floor
granularity, never linked across snapshots by anything but the aggregate keys above.

No `name`, no `id_number`, no biometric field, no free-text field capable of holding one —
enforced by schema, not by policy alone (mirrors §7's "by design, not policy alone").

---

## 7. Cost-scenario schema

```sql
CREATE TABLE cost_scenarios (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_id                INTEGER REFERENCES cohorts(id),
    pathway_id               TEXT,      -- FK into pathways.py definitions
    year                     INTEGER NOT NULL,
    trajectory_a_annual_cost REAL,      -- status quo, per capita/year × cohort.count
    trajectory_b_upfront_cost REAL,     -- inclusion/resettlement investment
    funding_shortfall_pct    REAL,      -- input driving the funding-shortfall multiplier
    breakeven_year           INTEGER,   -- computed output
    uncertainty_band_low     REAL,
    uncertainty_band_high    REAL,
    created_at               TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Resolved (corrected from v0.1's open question):** the report anchors this explicitly at
p.9/§5 — "breaks even in year Z, **subject to these gatekeepers and this uncertainty band**."
The uncertainty band attaches to the break-even output itself, not only to the readiness
match. `confMult` is therefore **one shared slider feeding both layers**, not a Layer-2-only
control with a separate cost slider bolted on later.

**Mechanism — interval arithmetic, not a second Monte Carlo.** Report §14 states costs are
"more reliable than modeled outcomes" and warns against treating modeled figures as more
precise than they are. Layer 2 already carries the stochastic engine (500-run Monte Carlo)
appropriate for a genuinely probabilistic outcome (does this cohort get matched to this
pathway). Cost is different: `calculate_resources()`'s line items are point-estimate sums,
not draws from a distribution, so Layer 1 should widen its output into a band via bounded
interval arithmetic, not duplicate Layer 2's Monte Carlo machinery.

1. Every `parameter_registry.py` entry gets a `base_uncertainty_pct`, derived from its
   existing tag: `validated → 10%`, `estimated → 30%`, `unvalidated → 60%` (placeholder
   splits — themselves an `unvalidated` modeling assumption, flagged the same way
   `GK_BLOCKED_CAP`/`MAX_PERTURB_PROB` are self-flagged in the simulator's own `PARAMS`).
2. `cost_engine.py`'s break-even function takes `confMult` as an input (the *same* value
   Layer 2/3's slider produces — `1 - uncertaintyLevel` — not a second, independent slider
   in the RICS UI).
3. Each contributing parameter's point estimate is widened to
   `value × (1 ± base_uncertainty_pct × (2 − confMult))` — at `confMult = 1` (no added
   global uncertainty) the band equals the parameter's own tag-margin; as `confMult → 0`
   (maximum field-intelligence degradation) the margin doubles. Same "uncertainty widens
   what confidence already narrowed" shape as `perturbStatus`'s
   `prob = MAX_PERTURB_PROB × (1 − effConf)`, applied to a magnitude instead of a status flip.
4. `trajectory_a_low/high` and `trajectory_b_low/high` are computed by propagating each
   parameter's widened range through the existing summation formulas (no re-derivation of
   `calculate_resources()`'s arithmetic — only its inputs move).
5. `breakeven_year_low = breakeven(trajectory_a_high, trajectory_b_low)` (fastest
   crossover: status quo costed pessimistically, inclusion pathway costed optimistically);
   `breakeven_year_high = breakeven(trajectory_a_low, trajectory_b_high)` (slowest
   crossover) — standard interval-arithmetic bounding through a monotonic formula, populating
   the `uncertainty_band_low/high` columns already present in the schema above.

This keeps the asymmetry the report itself insists on (§14: lead with cost as the reliable
half; treat modeled outcomes as indicative) while still honoring p.9's explicit framing that
the uncertainty band covers the break-even year, not just the pathway match.

---

## 8. Language/runtime note

`index.html`'s engine is client-side JS with no backend (ARCHITECTURE.md: "single-file HTML/JS
application with no external dependencies"). ERCF's engine is server-side Python
(`calculators.py` behind FastAPI). RICS needs both layers' outputs composed into one API
response (a cohort's break-even year *and* its pathway-match readiness together). Recommended:
port `computeReadiness`/`perturbStatus`/`monteCarlo`/`compositeScore`/`assign` to Python inside
`readiness_engine.py`, following ERCF's own precedent of a server-side source of truth with an
optional client-side mirror for instant UI feedback (ARCHITECTURE.md: "no client-side
calculation... except the real-time UI feedback path in app.js"). The JS versions remain the
spec to port against, not dead code — same role the original `Evacuation_Simulator_
Methodology.docx` was supposed to play before it drifted (BACKLOG.md's documented warning).

---

## 9. File layout

```
rics/
├── DESIGN.md                  # this document
├── PARAMETER_REGISTRY.md      # generated rendering of parameter_registry.py — never hand-edited
├── parameter_registry.py      # single source of truth, both layers
├── cost_engine.py             # Trajectory A/B + break-even; adapted from calculators.py
├── readiness_engine.py        # Python port of index.html's pure functions
├── pathways.py                # 3 real pathway categories, sourced factor assessments
├── cohorts.py                 # cohort category definitions (not data — data lives in DB)
├── database.py                # cohorts, pathways refs, cost_scenarios — pattern from ERCF database.py
├── main.py                    # FastAPI endpoints — pattern from ERCF main.py
└── static/
    ├── index.html             # break-even chart (app.js pattern) + capacity/readiness matrix (index.html render* pattern)
    └── app.js
```

---

## 10. Explicitly out of scope for v1 (per §9's "absent by design" table)

- Any biometric or identity system
- Any bespoke ledger/blockchain (value-transfer layer is §6.2, not RICS)
- Individual-level cohort records below the k-anonymity floor
- Factor correlation between Security/Legal Consent (flagged as unmodeled in the simulator's
  own BACKLOG.md and CONCEPT.md §13 future-extensions list) — inherited limitation, not solved
  here

---

## 11. Next decision point

This document is the "merged artifact" checkpoint before code. Once reviewed, the natural
next step is scaffolding in the order the traceability table implies: `parameter_registry.py`
first (both engines depend on it), then `cost_engine.py` (fewest open questions), then
`readiness_engine.py` + `pathways.py` together (the JS→Python port), then `database.py`/
`main.py` to compose them.

*Scaffolding complete as of this writing — all four modules built and verified (registry
generates and loads; cost engine's interval arithmetic and funding-shortfall no-op both
confirmed by running it; readiness engine reproduces the source model's gatekeeper-cap
behavior on a live example; database enforces the k-anonymity floor and a mechanical
PII-column check at startup; the full API composes both engines end-to-end via TestClient).*

---

## 12. Source-mining findings (`docs/refugees-idp-syllabus.md` cross-reference)

Cross-referenced against NYU GLOB1-GC2320's reading list (Barbara Borst, Spring 2026) at
the point where the bibliography claimed direct overlap with RICS. None of the entries
below have been read in full — only titles/authors/venues from the syllabus — so
confidence is calibrated accordingly, and nothing here is cited as if it were a full-text
review. Per instruction: only what actually survives is recorded; the rest is stated as
not incorporated, with the reason, so it isn't re-litigated later.

**Incorporated:**
- AP, "Trafficked, exploited, married off: Rohingya children's lives crushed by foreign aid
  cuts," Dec. 2025 — added to `parameter_registry.py`'s `rics_funding_shortfall_alpha` entry
  as qualitative comparative support for the funding-shortfall-harm mechanism, explicitly
  distinct from this report's own Rohingya/BIMS citation (§7, HRW 2021, a different
  mechanism — biometric data misuse, not funding collapse). Framed the same way ERCF frames
  its own qualitative-only support for `calculate_remaining_costs()`'s extraction-probability
  formula: directional support, not a numeric derivation. Does **not** supply a value for
  alpha, which remains an unset placeholder pending real calibration.

**Considered, not incorporated (with reason):**
- UNHCR, "Policy on Alternatives to Camps," 2014, and the Uganda literature (World Bank
  2016 assessment; Kreibaum, "Build Towns Instead of Camps," 2016; Ilcan et al., Nakivale
  case, CIGI 2015) — legitimate, but describe a different country's policy or a normative
  UNHCR position, not Malawi's current conditions; they don't move any tag on
  `malawi_local_integration`. Their actual value: they are the *primary* sources underlying
  the Uganda/Kakuma economic claims the report's own §5 already makes via *secondary*
  citations (a UNHCR blog post, a WEF article) — worth citing directly if Trajectory B's
  inclusion-economics rationale is written up formally, but that's a citation-quality
  upgrade, not a parameter change, and hasn't been done here.
- Kenya's "Shirika Plan for Refugees and Host Communities," March 2025 — a real, timely
  comparative precedent, but a different country's *unimplemented* reform; validates
  nothing about Malawi today. Worth a watch-item note if Malawi ever moves toward a similar
  model (would require reworking `malawi_local_integration`'s factor assessments), not a
  present-tense citation.
- Kuch, "Naturalization of Burundi Refugees in Tanzania," *Journal of Refugee Studies*, 2016
  — same origin nationality as a fraction of Dzaleka's population, but a different host
  country (Tanzania, not Malawi) and a different legal mechanism (naturalization *in*
  Tanzania is not a pathway available to someone displaced *in* Malawi). Citing it here
  would conflate two unrelated host-state policy decisions under a shared-nationality
  coincidence. Not incorporated.
- Fratzke & Zanzuchi, "Complementary Pathways," MPI, Dec. 2024 — flagged by title as a
  near-1:1 match to RICS's three pathway categories, but "complementary pathways" is
  standard MPI/UNHCR terminology for labor-mobility/education/family-reunification routes
  to third countries, complementary *to* resettlement — narrower than, and not the same
  split as, RICS's three durable-solutions categories (local integration / voluntary return
  / resettlement). If that reading holds, this source would refine the
  `resettlement_usa/canada/eu` category alone (e.g., splitting formal quota admission from
  labor-mobility/education/sponsorship routes), not validate all three pathways at once.
  Not cited pending an actual read of the paper — recommended as a follow-up verification
  task before it appears in any funder-facing citation list.

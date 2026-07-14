"""
RICS database layer — pattern reused from ERCF's database.py (get_conn/_migrate_db/
versioned schema, CRUD-per-table), schema redesigned per DESIGN.md §6/§7: aggregate
cohort snapshots and cost scenarios, never individual-level rows.

Two tables only, matching DESIGN.md exactly:
  cohorts        — aggregate counts, k-anonymity floor enforced by CHECK constraint
  cost_scenarios — Trajectory A/B outputs + break-even band per cohort/pathway/year

Pathway *definitions* live in pathways.py (code, not DB) per DESIGN.md's file layout —
sourced capacity/admin_complexity values are supplied at request time via
pathways.to_engine_pathway()'s override parameters until a decision is made on
persisting field-sourced pathway data (not yet reviewed — flagged, not assumed).
"""

import sqlite3
from typing import Dict, List, Optional

from parameter_registry import PARAMETER_REGISTRY

DB_PATH = "rics.db"

K_ANON_FLOOR = PARAMETER_REGISTRY["k_anonymity_floor"]["value"]

# Column-name blocklist for the do-no-harm check below — DDC-0001 / report §7's
# "by design, not policy alone" principle, made mechanically enforced rather than
# only documented. Not exhaustive; extend if a future migration adds a column.
_PII_BLOCKLIST = (
    "name", "first_name", "last_name", "dob", "date_of_birth", "id_number",
    "national_id", "passport", "biometric", "iris", "fingerprint", "photo",
    "phone", "email", "address", "gps", "individual_id",
)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version    INTEGER NOT NULL,
            applied_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    row = conn.execute("SELECT MAX(version) FROM _schema_version").fetchone()
    current = row[0] if row[0] is not None else 0
    # No migrations beyond the v0 schema below yet — placeholder for future ALTER TABLE steps.
    return current


def _assert_no_pii_columns(conn):
    """Mechanical check, not just a design note: fails loudly if any table gains a
    column name that looks like individual-identifying data. Run at startup."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_schema_version'"
    ).fetchall()]
    for table in tables:
        cols = [r[1].lower() for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        hits = [c for c in cols if any(bad in c for bad in _PII_BLOCKLIST)]
        if hits:
            raise RuntimeError(
                f"Table '{table}' has column(s) {hits} matching the PII blocklist — "
                f"report §7/DDC-0001 forbids individual-identifying fields. Fix the schema, "
                f"do not suppress this check."
            )


def init_db():
    conn = get_conn()
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS cohorts (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date          TEXT    NOT NULL,
            nationality            TEXT    NOT NULL,
            vulnerability_category TEXT    NOT NULL,
            legal_status           TEXT    NOT NULL,
            count                  INTEGER NOT NULL CHECK (count >= {K_ANON_FLOOR}),
            priority               TEXT    NOT NULL DEFAULT 'medium',
            source                 TEXT,
            tag                    TEXT    DEFAULT 'unvalidated',
            created_at             TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cost_scenarios (
            id                        INTEGER PRIMARY KEY AUTOINCREMENT,
            cohort_id                 INTEGER REFERENCES cohorts(id),
            pathway_id                TEXT    NOT NULL,
            year                      INTEGER NOT NULL,
            trajectory_a_annual_cost  REAL,
            trajectory_b_upfront_cost REAL,
            funding_shortfall_pct     REAL,
            breakeven_year_point      REAL,
            breakeven_year_low        REAL,
            breakeven_year_high       REAL,
            conf_mult                 REAL,
            created_at                TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _migrate_db(conn)
    conn.commit()
    _assert_no_pii_columns(conn)
    conn.close()


def _row(r) -> Optional[Dict]:
    return dict(r) if r else None


# ─── Cohort CRUD ─────────────────────────────────────────────────────────────

def create_cohort(data: Dict) -> Dict:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO cohorts (
            snapshot_date, nationality, vulnerability_category, legal_status,
            count, priority, source, tag
        ) VALUES (?,?,?,?,?,?,?,?)
    """, (
        data["snapshot_date"], data["nationality"], data["vulnerability_category"],
        data["legal_status"], data["count"], data.get("priority", "medium"),
        data.get("source"), data.get("tag", "unvalidated"),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_cohort(new_id)


def get_cohort(cid: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM cohorts WHERE id=?", (cid,)).fetchone()
    conn.close()
    return _row(row)


def list_cohorts() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cohorts ORDER BY snapshot_date DESC, id DESC").fetchall()
    conn.close()
    return [_row(r) for r in rows]


def update_cohort(cid: int, data: Dict) -> Optional[Dict]:
    conn = get_conn()
    res = conn.execute("""
        UPDATE cohorts SET
            snapshot_date=?, nationality=?, vulnerability_category=?, legal_status=?,
            count=?, priority=?, source=?, tag=?
        WHERE id=?
    """, (
        data["snapshot_date"], data["nationality"], data["vulnerability_category"],
        data["legal_status"], data["count"], data.get("priority", "medium"),
        data.get("source"), data.get("tag", "unvalidated"), cid,
    ))
    conn.commit()
    conn.close()
    return get_cohort(cid) if res.rowcount else None


def delete_cohort(cid: int) -> bool:
    conn = get_conn()
    res = conn.execute("DELETE FROM cohorts WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return res.rowcount > 0


# ─── Cost scenario CRUD ──────────────────────────────────────────────────────

def create_cost_scenario(data: Dict) -> Dict:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO cost_scenarios (
            cohort_id, pathway_id, year, trajectory_a_annual_cost,
            trajectory_b_upfront_cost, funding_shortfall_pct,
            breakeven_year_point, breakeven_year_low, breakeven_year_high, conf_mult
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        data["cohort_id"], data["pathway_id"], data["year"],
        data.get("trajectory_a_annual_cost"), data.get("trajectory_b_upfront_cost"),
        data.get("funding_shortfall_pct"),
        data.get("breakeven_year_point"), data.get("breakeven_year_low"), data.get("breakeven_year_high"),
        data.get("conf_mult"),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_cost_scenario(new_id)


def get_cost_scenario(sid: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM cost_scenarios WHERE id=?", (sid,)).fetchone()
    conn.close()
    return _row(row)


def list_cost_scenarios(cohort_id: Optional[int] = None) -> List[Dict]:
    conn = get_conn()
    if cohort_id is not None:
        rows = conn.execute(
            "SELECT * FROM cost_scenarios WHERE cohort_id=? ORDER BY year", (cohort_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cost_scenarios ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row(r) for r in rows]

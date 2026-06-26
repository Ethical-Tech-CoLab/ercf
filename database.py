import sqlite3
from typing import Dict, List, Optional

DB_PATH = "evacuation_risk.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_db(conn):
    """Versioned schema migrations — idempotent, safe to re-run."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version    INTEGER NOT NULL,
            applied_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    row = conn.execute("SELECT MAX(version) FROM _schema_version").fetchone()
    current = row[0] if row[0] is not None else 0

    if current < 1:
        # v1: add geolocation and operational columns to scenarios
        v1_columns = [
            ("conflict_lat",         "REAL DEFAULT NULL"),
            ("conflict_lng",         "REAL DEFAULT NULL"),
            ("safe_zone_lat",        "REAL DEFAULT NULL"),
            ("safe_zone_lng",        "REAL DEFAULT NULL"),
            ("safe_zone_name",       "TEXT DEFAULT NULL"),
            ("distance_source",      "TEXT DEFAULT 'manual'"),
            ("road_factor_applied",  "INTEGER DEFAULT 0"),
            ("haversine_km",         "REAL DEFAULT NULL"),
            ("terrain",              "INTEGER DEFAULT 3"),
            ("conflict_pattern",     "INTEGER DEFAULT 5"),
        ]
        for col_name, col_def in v1_columns:
            try:
                conn.execute(f"ALTER TABLE scenarios ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass  # Column already exists
        conn.execute("INSERT INTO _schema_version (version) VALUES (1)")
        current = 1


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
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
            created_at           TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _migrate_db(conn)
    conn.commit()
    conn.close()


def _row(r) -> Optional[Dict]:
    return dict(r) if r else None


def create_scenario(data: Dict) -> Dict:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO scenarios (
            name, description, population, vulnerable_pct, distance_km,
            d1_kinetic, d2_vulnerability, d3_political, d4_logistics,
            d5_destination, d6_urgency, d7_information,
            risk_score, risk_level, risk_label, nato_equivalent,
            conflict_lat, conflict_lng, safe_zone_lat, safe_zone_lng,
            safe_zone_name, distance_source, road_factor_applied, haversine_km,
            terrain, conflict_pattern
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["name"], data.get("description", ""), data["population"],
        data["vulnerable_pct"], data["distance_km"],
        data["d1_kinetic"], data["d2_vulnerability"], data["d3_political"],
        data["d4_logistics"], data["d5_destination"], data["d6_urgency"],
        data["d7_information"],
        data.get("risk_score"), data.get("risk_level"),
        data.get("risk_label"), data.get("nato_equivalent"),
        data.get("conflict_lat"), data.get("conflict_lng"),
        data.get("safe_zone_lat"), data.get("safe_zone_lng"),
        data.get("safe_zone_name"), data.get("distance_source", "manual"),
        int(bool(data.get("road_factor_applied", False))),
        data.get("haversine_km"),
        data.get("terrain", 3),
        data.get("conflict_pattern", 5),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return get_scenario(new_id)


def get_scenario(sid: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM scenarios WHERE id=?", (sid,)).fetchone()
    conn.close()
    return _row(row)


def list_scenarios() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM scenarios ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row(r) for r in rows]


def update_scenario(sid: int, data: Dict) -> Optional[Dict]:
    conn = get_conn()
    res = conn.execute("""
        UPDATE scenarios SET
            name=?, description=?, population=?, vulnerable_pct=?, distance_km=?,
            d1_kinetic=?, d2_vulnerability=?, d3_political=?, d4_logistics=?,
            d5_destination=?, d6_urgency=?, d7_information=?,
            risk_score=?, risk_level=?, risk_label=?, nato_equivalent=?,
            conflict_lat=?, conflict_lng=?, safe_zone_lat=?, safe_zone_lng=?,
            safe_zone_name=?, distance_source=?, road_factor_applied=?, haversine_km=?,
            terrain=?, conflict_pattern=?
        WHERE id=?
    """, (
        data["name"], data.get("description", ""), data["population"],
        data["vulnerable_pct"], data["distance_km"],
        data["d1_kinetic"], data["d2_vulnerability"], data["d3_political"],
        data["d4_logistics"], data["d5_destination"], data["d6_urgency"],
        data["d7_information"],
        data.get("risk_score"), data.get("risk_level"),
        data.get("risk_label"), data.get("nato_equivalent"),
        data.get("conflict_lat"), data.get("conflict_lng"),
        data.get("safe_zone_lat"), data.get("safe_zone_lng"),
        data.get("safe_zone_name"), data.get("distance_source", "manual"),
        int(bool(data.get("road_factor_applied", False))),
        data.get("haversine_km"),
        data.get("terrain", 3),
        data.get("conflict_pattern", 5),
        sid,
    ))
    conn.commit()
    conn.close()
    return get_scenario(sid) if res.rowcount else None


def delete_scenario(sid: int) -> bool:
    conn = get_conn()
    res = conn.execute("DELETE FROM scenarios WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return res.rowcount > 0

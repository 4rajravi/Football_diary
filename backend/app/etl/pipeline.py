"""
ETL Pipeline — Download CSVs from transfermarkt-datasets and load into SQLite.

Tables are created DYNAMICALLY from CSV headers so the pipeline never breaks
when the upstream dataset adds or renames columns.

Usage:
    python -m app.etl.pipeline          # full refresh
    python -m app.etl.pipeline --table games   # single table
"""

import csv
import gzip
import hashlib
import io
import os
import shutil
import sqlite3
import time
from datetime import datetime

import httpx

from app.config import CSV_TABLES, DATA_BASE_URL, DATABASE_PATH


# ── Helpers ──────────────────────────────────────────────────────────

def get_db_path() -> str:
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    return DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")   # OFF during ETL — critical!
    conn.row_factory = sqlite3.Row
    return conn


def download_csv(table_name: str, timeout: float = 120.0) -> bytes:
    """Download a gzipped CSV from the R2 bucket."""
    url = f"{DATA_BASE_URL}/{table_name}.csv.gz"
    print(f"  Downloading {url} ...")
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return gzip.decompress(resp.content)


def compute_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ── Dynamic table creation ───────────────────────────────────────────

# Primary keys per table (for INSERT OR REPLACE to work correctly)
TABLE_PRIMARY_KEYS = {
    "competitions": ["competition_id"],
    "clubs": ["club_id"],
    "players": ["player_id"],
    "games": ["game_id"],
    "appearances": ["appearance_id"],
    "player_valuations": ["player_id", "date"],
    "club_games": ["club_id", "game_id"],
    "game_events": None,               # no natural PK — use rowid
    "game_lineups": None,              # has its own id column
    "transfers": None,                 # no natural PK — use rowid
}


def create_table_from_headers(conn: sqlite3.Connection, table_name: str, columns: list[str]):
    """DROP and CREATE a table with TEXT columns matching the CSV headers."""
    conn.execute(f"DROP TABLE IF EXISTS [{table_name}]")

    pk_cols = TABLE_PRIMARY_KEYS.get(table_name)
    clean_cols = [c.strip() for c in columns]

    col_defs = []
    for col in clean_cols:
        col_defs.append(f"  [{col}] TEXT")

    # Add composite primary key if defined
    pk_clause = ""
    if pk_cols and all(pk in clean_cols for pk in pk_cols):
        pk_list = ", ".join([f"[{pk}]" for pk in pk_cols])
        pk_clause = f",\n  PRIMARY KEY ({pk_list})"

    create_sql = f"CREATE TABLE [{table_name}] (\n" + ",\n".join(col_defs) + pk_clause + "\n)"
    conn.execute(create_sql)


def load_csv_to_table(table_name: str, csv_bytes: bytes) -> int:
    """Dynamically create table from CSV headers and bulk-insert all rows.
    Returns the number of rows loaded."""
    text = csv_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames
    if not columns:
        return 0

    rows = list(reader)
    if not rows:
        return 0

    conn = get_connection()
    try:
        # Create table from actual CSV columns
        create_table_from_headers(conn, table_name, columns)

        # Bulk insert
        clean_cols = [c.strip() for c in columns]
        placeholders = ", ".join(["?"] * len(clean_cols))
        col_names = ", ".join([f"[{c}]" for c in clean_cols])
        sql = f"INSERT OR REPLACE INTO [{table_name}] ({col_names}) VALUES ({placeholders})"

        batch = []
        for row in rows:
            values = []
            for col in columns:
                val = row.get(col, "")
                if val == "" or val is None:
                    values.append(None)
                else:
                    values.append(val)
            batch.append(tuple(values))

        # Insert in chunks of 10000 for memory efficiency
        chunk_size = 10000
        for i in range(0, len(batch), chunk_size):
            conn.executemany(sql, batch[i:i + chunk_size])

        conn.commit()
        return len(rows)
    finally:
        conn.close()


# ── Views ────────────────────────────────────────────────────────────
# All numeric columns are stored as TEXT (dynamic schema), so we CAST everywhere.

VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_head_to_head AS
SELECT
    g.home_club_id   AS club_a_id,
    g.home_club_name AS club_a_name,
    g.away_club_id   AS club_b_id,
    g.away_club_name AS club_b_name,
    g.competition_id,
    COUNT(*)         AS total_matches,
    SUM(CASE WHEN CAST(g.home_club_goals AS INTEGER) > CAST(g.away_club_goals AS INTEGER) THEN 1 ELSE 0 END)  AS club_a_wins,
    SUM(CASE WHEN CAST(g.home_club_goals AS INTEGER) < CAST(g.away_club_goals AS INTEGER) THEN 1 ELSE 0 END)  AS club_b_wins,
    SUM(CASE WHEN CAST(g.home_club_goals AS INTEGER) = CAST(g.away_club_goals AS INTEGER) THEN 1 ELSE 0 END)  AS draws,
    SUM(CAST(g.home_club_goals AS INTEGER)) AS club_a_goals,
    SUM(CAST(g.away_club_goals AS INTEGER)) AS club_b_goals
FROM games g
GROUP BY g.home_club_id, g.away_club_id, g.competition_id;

CREATE VIEW IF NOT EXISTS v_player_season_stats AS
SELECT
    a.player_id,
    a.player_name,
    a.competition_id,
    g.season,
    a.player_club_id AS club_id,
    COUNT(DISTINCT a.game_id)                                AS appearances,
    SUM(CAST(a.goals AS INTEGER))                            AS goals,
    SUM(CAST(a.assists AS INTEGER))                          AS assists,
    SUM(CAST(a.goals AS INTEGER)) + SUM(CAST(a.assists AS INTEGER)) AS goal_contributions,
    SUM(CAST(a.minutes_played AS INTEGER))                   AS total_minutes,
    SUM(CAST(a.yellow_cards AS INTEGER))                     AS yellow_cards,
    SUM(CAST(a.red_cards AS INTEGER))                        AS red_cards,
    CASE WHEN SUM(CAST(a.minutes_played AS INTEGER)) > 0
        THEN ROUND(CAST(SUM(CAST(a.goals AS INTEGER)) AS REAL) / SUM(CAST(a.minutes_played AS INTEGER)) * 90, 2)
        ELSE 0 END AS goals_per_90,
    CASE WHEN SUM(CAST(a.minutes_played AS INTEGER)) > 0
        THEN ROUND(CAST(SUM(CAST(a.assists AS INTEGER)) AS REAL) / SUM(CAST(a.minutes_played AS INTEGER)) * 90, 2)
        ELSE 0 END AS assists_per_90,
    CASE WHEN SUM(CAST(a.minutes_played AS INTEGER)) > 0
        THEN ROUND(CAST(SUM(CAST(a.goals AS INTEGER)) + SUM(CAST(a.assists AS INTEGER)) AS REAL) / SUM(CAST(a.minutes_played AS INTEGER)) * 90, 2)
        ELSE 0 END AS contributions_per_90
FROM appearances a
JOIN games g ON a.game_id = g.game_id
GROUP BY a.player_id, a.player_name, a.competition_id, g.season, a.player_club_id;

CREATE VIEW IF NOT EXISTS v_player_impact AS
SELECT
    a.player_id,
    a.player_name,
    g.season,
    a.competition_id,
    COUNT(CASE WHEN CAST(a.minutes_played AS INTEGER) >= 45 THEN 1 END) AS games_started,
    COUNT(CASE WHEN CAST(a.minutes_played AS INTEGER) >= 45
               AND CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER)
          THEN 1 END) AS wins_when_started,
    COUNT(CASE WHEN CAST(a.minutes_played AS INTEGER) > 0 AND CAST(a.minutes_played AS INTEGER) < 45 THEN 1 END) AS games_as_sub,
    COUNT(CASE WHEN CAST(a.minutes_played AS INTEGER) > 0 AND CAST(a.minutes_played AS INTEGER) < 45
               AND CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER)
          THEN 1 END) AS wins_as_sub
FROM appearances a
JOIN games g ON a.game_id = g.game_id
JOIN club_games cg ON cg.game_id = g.game_id AND cg.club_id = a.player_club_id
GROUP BY a.player_id, a.player_name, g.season, a.competition_id;

CREATE VIEW IF NOT EXISTS v_club_form AS
SELECT
    cg.club_id,
    g.competition_id,
    g.season,
    g.date,
    g.game_id,
    cg.own_goals,
    cg.opponent_goals,
    cg.opponent_id,
    CASE
        WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 'W'
        WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 'L'
        ELSE 'D'
    END AS result,
    cg.hosting
FROM club_games cg
JOIN games g ON cg.game_id = g.game_id;

CREATE VIEW IF NOT EXISTS v_standings AS
SELECT
    cg.club_id,
    COALESCE(cl.name,
        MAX(CASE WHEN g.home_club_id = cg.club_id THEN g.home_club_name ELSE NULL END),
        MAX(CASE WHEN g.away_club_id = cg.club_id THEN g.away_club_name ELSE NULL END)
    ) AS club_name,
    g.competition_id,
    g.season,
    COUNT(*)                                 AS played,
    SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END)  AS wins,
    SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END)  AS draws,
    SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) < CAST(cg.opponent_goals AS INTEGER) THEN 1 ELSE 0 END)  AS losses,
    SUM(CAST(cg.own_goals AS INTEGER))       AS goals_for,
    SUM(CAST(cg.opponent_goals AS INTEGER))  AS goals_against,
    SUM(CAST(cg.own_goals AS INTEGER)) - SUM(CAST(cg.opponent_goals AS INTEGER)) AS goal_difference,
    SUM(CASE WHEN CAST(cg.own_goals AS INTEGER) > CAST(cg.opponent_goals AS INTEGER) THEN 3
             WHEN CAST(cg.own_goals AS INTEGER) = CAST(cg.opponent_goals AS INTEGER) THEN 1
             ELSE 0 END)                     AS points
FROM club_games cg
JOIN games g ON cg.game_id = g.game_id
LEFT JOIN clubs cl ON cg.club_id = cl.club_id
GROUP BY cg.club_id, g.competition_id, g.season;

CREATE VIEW IF NOT EXISTS v_top_scorers AS
SELECT
    a.player_id,
    a.player_name,
    a.player_club_id AS club_id,
    cl.name AS club_name,
    p.position,
    p.country_of_citizenship,
    a.competition_id,
    g.season,
    SUM(CAST(a.goals AS INTEGER))                            AS goals,
    SUM(CAST(a.assists AS INTEGER))                          AS assists,
    SUM(CAST(a.goals AS INTEGER)) + SUM(CAST(a.assists AS INTEGER)) AS goal_contributions,
    COUNT(DISTINCT a.game_id)                                AS appearances,
    SUM(CAST(a.minutes_played AS INTEGER))                   AS minutes_played
FROM appearances a
JOIN games g ON a.game_id = g.game_id
LEFT JOIN clubs cl ON a.player_club_id = cl.club_id
LEFT JOIN players p ON a.player_id = p.player_id
GROUP BY a.player_id, a.competition_id, g.season
HAVING SUM(CAST(a.goals AS INTEGER)) > 0;
"""


def create_views():
    """Create all derived views."""
    conn = get_connection()
    try:
        for vname in ['v_head_to_head', 'v_player_season_stats', 'v_player_impact',
                      'v_club_form', 'v_standings', 'v_top_scorers']:
            conn.execute(f"DROP VIEW IF EXISTS {vname}")
        conn.executescript(VIEWS_SQL)
        conn.commit()
        print("  ✓ All views created successfully")
    except Exception as e:
        print(f"  ⚠ View creation error: {e}")
    finally:
        conn.close()


def create_indexes():
    """Create indexes for query performance."""
    INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_games_competition    ON games(competition_id);
    CREATE INDEX IF NOT EXISTS idx_games_season         ON games(season);
    CREATE INDEX IF NOT EXISTS idx_games_date           ON games(date);
    CREATE INDEX IF NOT EXISTS idx_games_home_club      ON games(home_club_id);
    CREATE INDEX IF NOT EXISTS idx_games_away_club      ON games(away_club_id);
    CREATE INDEX IF NOT EXISTS idx_appearances_game     ON appearances(game_id);
    CREATE INDEX IF NOT EXISTS idx_appearances_player   ON appearances(player_id);
    CREATE INDEX IF NOT EXISTS idx_appearances_club     ON appearances(player_club_id);
    CREATE INDEX IF NOT EXISTS idx_appearances_comp     ON appearances(competition_id);
    CREATE INDEX IF NOT EXISTS idx_events_game          ON game_events(game_id);
    CREATE INDEX IF NOT EXISTS idx_events_player        ON game_events(player_id);
    CREATE INDEX IF NOT EXISTS idx_lineups_game         ON game_lineups(game_id);
    CREATE INDEX IF NOT EXISTS idx_lineups_player       ON game_lineups(player_id);
    CREATE INDEX IF NOT EXISTS idx_valuations_player    ON player_valuations(player_id);
    CREATE INDEX IF NOT EXISTS idx_club_games_club      ON club_games(club_id);
    CREATE INDEX IF NOT EXISTS idx_club_games_opponent  ON club_games(opponent_id);
    CREATE INDEX IF NOT EXISTS idx_transfers_player     ON transfers(player_id);
    CREATE INDEX IF NOT EXISTS idx_players_club         ON players(current_club_id);
    CREATE INDEX IF NOT EXISTS idx_players_position     ON players(position);
    """
    conn = get_connection()
    try:
        conn.executescript(INDEX_SQL)
        conn.commit()
        print("  ✓ All indexes created successfully")
    except Exception as e:
        print(f"  ⚠ Some indexes failed (non-critical): {e}")
    finally:
        conn.close()


# ── Metadata tracking ────────────────────────────────────────────────

def ensure_metadata_table():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _etl_metadata (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name    TEXT NOT NULL,
                rows_loaded   INTEGER,
                loaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_hash   TEXT,
                status        TEXT DEFAULT 'success'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def log_etl_status(table_name: str, rows: int, source_hash: str, status: str = "success"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO _etl_metadata (table_name, rows_loaded, source_hash, status) VALUES (?, ?, ?, ?)",
            (table_name, rows, source_hash, status),
        )
        conn.commit()
    finally:
        conn.close()


# ── Backup ────────────────────────────────────────────────────────────

def backup_db():
    if os.path.exists(DATABASE_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DATABASE_PATH}.bak_{ts}"
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"  Backup created: {backup_path}")
        backup_dir = os.path.dirname(DATABASE_PATH) or "."
        backups = sorted(
            [f for f in os.listdir(backup_dir) if ".bak_" in f],
            reverse=True,
        )
        for old in backups[3:]:
            os.remove(os.path.join(backup_dir, old))


# ── Main pipeline ─────────────────────────────────────────────────────

def run_pipeline(tables: list[str] | None = None):
    """Run the full ETL pipeline."""
    target_tables = tables or CSV_TABLES

    print("=" * 60)
    print("Football Diary — ETL Pipeline")
    print(f"Started at {datetime.now().isoformat()}")
    print("=" * 60)

    print("\n[1/5] Backing up database...")
    backup_db()

    print("\n[2/5] Ensuring metadata table...")
    ensure_metadata_table()

    print("\n[3/5] Downloading and loading tables...")
    total_rows = 0
    for table in target_tables:
        try:
            start = time.time()
            csv_bytes = download_csv(table)
            source_hash = compute_hash(csv_bytes)
            rows = load_csv_to_table(table, csv_bytes)
            elapsed = time.time() - start
            log_etl_status(table, rows, source_hash, "success")
            total_rows += rows
            print(f"  ✓ {table}: {rows:,} rows loaded ({elapsed:.1f}s)")
        except Exception as e:
            log_etl_status(table, 0, "", f"failed: {e}")
            print(f"  ✗ {table}: FAILED — {e}")

    print("\n[4/5] Creating indexes...")
    create_indexes()

    print("\n[5/5] Creating derived views...")
    create_views()

    print(f"\nComplete! {total_rows:,} total rows loaded.")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if "--table" in sys.argv:
        idx = sys.argv.index("--table")
        table = sys.argv[idx + 1]
        run_pipeline([table])
    else:
        run_pipeline()

import sqlite3
import os
from contextlib import contextmanager
from app.config import DATABASE_PATH


def get_db_path() -> str:
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    return DATABASE_PATH


@contextmanager
def get_connection():
    """Yield a SQLite connection with WAL mode."""
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_readonly(query: str, params: tuple = ()) -> list[dict]:
    """Execute a read-only query and return results as list of dicts.
    Used by the AI agent — enforces read-only access."""
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH"]
    upper = query.strip().upper()
    for keyword in forbidden:
        if upper.startswith(keyword):
            raise ValueError(f"Write operations are not allowed: {keyword}")

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

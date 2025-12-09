import os
import sqlite3


def conection():
    """Create a SQLite connection using env var DATABASE_URL if provided."""
    db_path = os.getenv("DATABASE_URL", "database.db")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

import os
import sqlite3


def conection():
    """Create a SQLite connection using env var DATABASE_URL if provided."""
    # En entornos como Railway/Render el volumen persistente suele montarse en /data.
    # Usar `/data/database.db` como valor por defecto facilita el deploy sin cambios.
    db_path = os.getenv("DATABASE_URL", "/data/database.db")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

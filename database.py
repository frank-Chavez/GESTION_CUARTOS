import os
import sqlite3


def conection():
    """Create a SQLite connection using env var DATABASE_URL if provided.

    Logic:
    - If `DATABASE_URL` env var is set, use it.
    - Otherwise prefer `/data/database.db` when `/data` exists and is writable
      (hosts like Railway/Render mount persistent disk there).
    - Fallback to a project-local `database.db` (same folder as this file)
      which works on Windows and local development.

    The function ensures the parent directory exists before connecting, to
    avoid `sqlite3.OperationalError: unable to open database file` when the
    directory is missing.
    """
    db_env = os.getenv("DATABASE_URL")
    if db_env:
        db_path = db_env
    else:
        data_dir = "/data"
        # prefer /data when available and writable (typical for hosting)
        try:
            if os.path.isdir(data_dir) and os.access(data_dir, os.W_OK):
                db_path = os.path.join(data_dir, "database.db")
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(base_dir, "database.db")
        except Exception:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "database.db")

    # Ensure parent directory exists (sqlite will fail if directory missing)
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            # Provide a clearer error message for troubleshooting
            raise RuntimeError(f"No se pudo crear el directorio de la base de datos {db_dir}: {e}")

    conn = sqlite3.connect(db_path, timeout=10)
    # Return rows as plain dicts to make templates and downstream code more robust
    def dict_row_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    conn.row_factory = dict_row_factory
    return conn


def first_value(row):
    """Return the first column value from a row returned by the connection.

    Works for dict rows (our dict_row_factory) and for sequence rows.
    """
    if row is None:
        return None
    if isinstance(row, dict):
        # return first value in column order
        for v in row.values():
            return v
        return None
    # fallback for sequences/tuples
    try:
        return row[0]
    except Exception:
        return None

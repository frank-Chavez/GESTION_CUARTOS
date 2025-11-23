import sqlite3


def conection():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

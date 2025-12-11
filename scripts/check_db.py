#!/usr/bin/env python3
import os
import sqlite3
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'database.db')
print('DB path:', DB)
if not os.path.exists(DB):
    print('No existe el archivo de base de datos:', DB)
    raise SystemExit(1)
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, usuario, nombre FROM usuarios")
print('usuarios:', cur.fetchall())
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', cur.fetchall())
cur.close()
conn.close()

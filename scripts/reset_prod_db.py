#!/usr/bin/env python3
"""Resetea la base de datos local a estado mínimo para producción.

- Borra todos los registros de las tablas: pagos, inquilinos, cuartos, usuarios
- Reinicia las secuencias de autoincrement
- Crea un único usuario admin con usuario `admin` y la contraseña indicada

USO (ejecutar desde la raíz del proyecto):
venv\Scripts\python.exe scripts\reset_prod_db.py --yes

Advertencia: esto sobreescribe la base de datos localizada por `database.conection()`.
"""
import argparse
import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Asegurar que el directorio raíz del proyecto está en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import conection

parser = argparse.ArgumentParser()
parser.add_argument("--yes", action="store_true", help="Confirmar ejecución sin pedir interacción")
parser.add_argument("--password", default="Frank975@", help="Contraseña para el usuario admin (por defecto: Frank975@)")
args = parser.parse_args()

if not args.yes:
    resp = input("ATENCIÓN: Se eliminarán todos los datos de la base. Continuar? (si/no): ")
    if not resp.lower().startswith("s"):
        print("Operación cancelada.")
        raise SystemExit(1)

conn = conection()
cur = conn.cursor()
try:
    print("Desactivando claves foráneas y borrando tablas...")
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("DELETE FROM pagos;")
    cur.execute("DELETE FROM inquilinos;")
    cur.execute("DELETE FROM cuartos;")
    cur.execute("DELETE FROM usuarios;")

    # Reiniciar secuencias (si existe la tabla sqlite_sequence)
    try:
        cur.execute("DELETE FROM sqlite_sequence;")
    except Exception:
        pass

    pw_hash = generate_password_hash(args.password)
    ahora = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO usuarios (nombre, usuario, password, rol, fecha_creacion) VALUES (?, ?, ?, 'admin', ?)",
        ("Admin", "admin", pw_hash, ahora),
    )

    conn.commit()
    print("Base de datos reiniciada. Usuario creado: usuario=admin, contraseña (proporcionada).")
except Exception as e:
    conn.rollback()
    print("Error ejecutando reseteo:", e)
    raise
finally:
    cur.close()
    conn.close()

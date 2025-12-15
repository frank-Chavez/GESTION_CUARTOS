from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from database import conection

agregar_inquilino_bp = Blueprint(
    "agregar_inquilino", __name__, template_folder="templates", static_folder="static", url_prefix="/agregar-inquilino"
)


@agregar_inquilino_bp.route("/form")
def form():
    conn = conection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero, piso, precio FROM cuartos WHERE estado = 'libre' ORDER BY numero")
    cuartos_disponibles = cursor.fetchall()
    print(f"[DEBUG] Cuartos libres encontrados: {len(cuartos_disponibles)}")
    for c in cuartos_disponibles:
        print(f"[DEBUG] Cuarto: id={c[0]}, numero={c[1]}, piso={c[2]}, precio={c[3]}")
    cursor.close()
    conn.close()
    return render_template("agregar_inquilino_dashboard.html", cuartos_disponibles=cuartos_disponibles)

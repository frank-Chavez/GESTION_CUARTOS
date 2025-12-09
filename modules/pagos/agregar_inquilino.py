from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from database import conection

agregar_inquilino_bp = Blueprint(
    "agregar_inquilino", __name__, template_folder="templates", static_folder="static", url_prefix="/agregar-inquilino"
)


@agregar_inquilino_bp.route("/form")
def form():
    conn = conection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero, piso, precio FROM cuartos WHERE estado = 'disponible' ORDER BY numero")
    cuartos_disponibles = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("agregar_inquilino_dashboard.html", cuartos_disponibles=cuartos_disponibles)

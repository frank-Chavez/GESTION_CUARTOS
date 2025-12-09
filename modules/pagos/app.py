from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_wtf import FlaskForm
from wtforms import DecimalField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange
from database import conection
from datetime import datetime
import csv
import io

# Crear el Blueprint
pagos_bp = Blueprint("pagos", __name__, template_folder="templates", static_folder="static", url_prefix="/pagos")


class PagoForm(FlaskForm):
    id_inquilino = SelectField("Inquilino", coerce=int, validators=[DataRequired()])
    monto = DecimalField(
        "Monto", validators=[DataRequired(), NumberRange(min=0.01, message="El monto debe ser positivo")]
    )
    metodo_pago = SelectField(
        "Método de Pago",
        choices=[
            ("efectivo", "Efectivo"),
            ("transferencia", "Transferencia"),
            ("yape", "Yape"),
            ("plin", "Plin"),
            ("deposito", "Depósito"),
        ],
        validators=[DataRequired()],
    )
    fecha = DateField("Fecha", validators=[DataRequired()], format="%Y-%m-%d")


@pagos_bp.route("/")
def index():
    from flask import session, redirect, url_for

    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    """Lista todos los pagos"""
    conn = conection()
    cursor = conn.cursor()

    # Mostrar todos los inquilinos con su estado de pago mensual
    cursor.execute(
        """
        SELECT 
            i.id,
            i.nombre,
            i.apellido,
            c.numero AS cuarto,
            i.monto_mensual,
            i.dia_pago,
            strftime('%d/%m/%Y', i.fecha_ingreso) AS fecha_ingreso,
            COALESCE(pagos_mes.total, 0) AS monto_pagado,
            (i.monto_mensual - COALESCE(pagos_mes.total, 0)) AS monto_faltante,
            CASE 
                WHEN COALESCE(pagos_mes.total, 0) >= i.monto_mensual THEN 'Pagado'
                WHEN date('now') > date(strftime('%Y-%m-', 'now') || printf('%02d', i.dia_pago)) THEN 'Atrasado'
                ELSE 'Pendiente'
            END AS estado,
            strftime('%d/%m/%Y', date(strftime('%Y-%m-', 'now') || printf('%02d', i.dia_pago))) AS fecha_vencimiento
        FROM inquilinos i
        JOIN cuartos c ON i.id_cuarto = c.id
        LEFT JOIN (
            SELECT id_inquilino, SUM(monto) AS total
            FROM pagos
            WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
            GROUP BY id_inquilino
        ) pagos_mes ON i.id = pagos_mes.id_inquilino
        ORDER BY i.nombre
    """
    )
    pagos = cursor.fetchall()

    # Obtener lista de inquilinos para el formulario
    cursor.execute("SELECT id, nombre || ' ' || apellido AS nombre_completo FROM inquilinos ORDER BY nombre")
    inquilinos = cursor.fetchall()

    # Calcular estadísticas
    # Total cobrado (suma de todos los pagos)
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos")
    total_cobrado = cursor.fetchone()[0]

    # Pendiente: suma de lo que falta pagar este mes por cada inquilino
    cursor.execute(
        """
        SELECT COALESCE(SUM(monto_pendiente), 0) FROM (
            SELECT i.id,
                   i.monto_mensual - COALESCE(pagos_mes.total, 0) AS monto_pendiente
            FROM inquilinos i
            JOIN cuartos c ON i.id_cuarto = c.id
            LEFT JOIN (
                SELECT id_inquilino, SUM(monto) AS total
                FROM pagos
                WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
                GROUP BY id_inquilino
            ) pagos_mes ON i.id = pagos_mes.id_inquilino
            WHERE i.monto_mensual - COALESCE(pagos_mes.total, 0) > 0
        )
        """
    )
    pendiente = cursor.fetchone()[0]

    # Atrasado (pagos que fueron marcados como no puntuales)
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE puntual = 0")
    atrasado = cursor.fetchone()[0]

    stats = {"total_cobrado": total_cobrado, "pendiente": pendiente, "atrasado": atrasado}

    cursor.close()
    conn.close()

    form = PagoForm()
    form.id_inquilino.choices = [(i[0], i[1]) for i in inquilinos]

    return render_template("pagos.html", pagos=pagos, form=form, inquilinos=inquilinos, stats=stats)


@pagos_bp.route("/agregar", methods=["POST"])
def agregar():
    """Registrar un nuevo pago"""
    conn = conection()
    cursor = conn.cursor()

    # Obtener inquilinos para el formulario
    cursor.execute("SELECT id, nombre || ' ' || apellido FROM inquilinos ORDER BY nombre")
    inquilinos = cursor.fetchall()

    form = PagoForm()
    form.id_inquilino.choices = [(i[0], i[1]) for i in inquilinos]

    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        cursor.close()
        conn.close()
        return redirect(url_for("pagos.index"))

    id_inquilino = form.id_inquilino.data
    monto = float(form.monto.data)
    fecha = form.fecha.data.isoformat()
    metodo_pago = form.metodo_pago.data

    # Determinar si el pago es puntual
    cursor.execute("SELECT dia_pago FROM inquilinos WHERE id = ?", (id_inquilino,))
    result = cursor.fetchone()
    dia_pago = result[0] if result else 1

    fecha_pago = form.fecha.data
    puntual = 1 if fecha_pago.day <= dia_pago else 0

    try:
        cursor.execute(
            """
            INSERT INTO pagos (id_inquilino, fecha, monto, puntual, metodo_pago)
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_inquilino, fecha, monto, puntual, metodo_pago),
        )
        conn.commit()
        flash("Pago registrado exitosamente", "success")
    except Exception as e:
        flash(f"Error al registrar pago: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("pagos.index"))


@pagos_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    """Eliminar un pago"""
    try:
        with conection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pagos WHERE id = ?", (id,))
            flash("Pago eliminado exitosamente", "success")
    except Exception as e:
        flash(f"Error al eliminar pago: {str(e)}", "error")

    return redirect(url_for("pagos.index"))


@pagos_bp.route("/exportar")
def exportar():
    """Exportar pagos a CSV"""
    conn = conection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            i.nombre || ' ' || i.apellido AS inquilino,
            c.numero AS cuarto,
            p.monto,
            p.fecha,
            CASE WHEN p.puntual = 1 THEN 'Puntual' ELSE 'Atrasado' END AS estado,
            p.observacion
        FROM pagos p
        JOIN inquilinos i ON p.id_inquilino = i.id
        JOIN cuartos c ON i.id_cuarto = c.id
        ORDER BY p.fecha DESC
    """
    )
    pagos = cursor.fetchall()
    cursor.close()
    conn.close()

    # Crear CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Inquilino", "Cuarto", "Monto", "Fecha", "Estado", "Observación"])

    for pago in pagos:
        writer.writerow(pago)

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename=pagos_{datetime.now().strftime("%Y%m%d")}.csv'},
    )


@pagos_bp.route("/historial/<int:id_inquilino>")
def historial(id_inquilino):
    """Ver historial de pagos de un inquilino"""
    conn = conection()
    cursor = conn.cursor()

    # Obtener información del inquilino
    cursor.execute(
        """
        SELECT i.nombre, i.apellido, c.numero AS cuarto
        FROM inquilinos i
        JOIN cuartos c ON i.id_cuarto = c.id
        WHERE i.id = ?
    """,
        (id_inquilino,),
    )
    inquilino = cursor.fetchone()

    if not inquilino:
        flash("Inquilino no encontrado", "error")
        cursor.close()
        conn.close()
        return redirect(url_for("pagos.index"))

    # Obtener historial de pagos
    cursor.execute(
        """
        SELECT 
            p.id,
            p.monto,
            strftime('%d/%m/%Y', p.fecha) AS fecha,
            p.puntual,
            p.observacion
        FROM pagos p
        WHERE p.id_inquilino = ?
        ORDER BY p.fecha DESC
    """,
        (id_inquilino,),
    )
    pagos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("pagos.html", pagos=pagos, inquilino=inquilino, historial=True)

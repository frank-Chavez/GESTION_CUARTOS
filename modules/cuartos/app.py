from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, IntegerField, DecimalField
from wtforms.validators import DataRequired, NumberRange, Optional
from database import conection, first_value
import sqlite3

# Crear el Blueprint
cuartos_bp = Blueprint("cuartos", __name__, template_folder="templates", static_folder="static", url_prefix="/cuartos")


class CuartoForm(FlaskForm):
    numero = StringField(validators=[DataRequired()])
    piso = IntegerField(validators=[DataRequired(), NumberRange(min=1)])
    precio = DecimalField(validators=[DataRequired(), NumberRange(min=0)])
    descripcion = TextAreaField(validators=[Optional()])
    estado = SelectField(
        choices=[("disponible", "Disponible"), ("ocupado", "Ocupado"), ("mantenimiento", "Mantenimiento")],
        validators=[DataRequired()],
    )


@cuartos_bp.route("/")
def index():
    from flask import session, redirect, url_for

    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    """Lista todos los cuartos"""
    conn = conection()
    cursor = conn.cursor()

    # Obtener cuartos con información del inquilino
    cursor.execute(
        """
        SELECT 
            c.id,
            c.numero,
            c.piso,
            c.precio,
            c.descripcion,
            c.estado,
            COALESCE(i.nombre || ' ' || i.apellido, '') AS inquilino
        FROM cuartos c
        LEFT JOIN inquilinos i ON c.id = i.id_cuarto
        ORDER BY c.numero
    """
    )
    cuartos = cursor.fetchall()

    # Obtener estadísticas
    cursor.execute("SELECT COUNT(*) FROM cuartos")
    total = first_value(cursor.fetchone())

    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'disponible'")
    disponibles = first_value(cursor.fetchone())

    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'ocupado'")
    ocupados = first_value(cursor.fetchone())

    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'mantenimiento'")
    mantenimiento = first_value(cursor.fetchone())

    cursor.close()
    conn.close()

    stats = {"total": total, "disponibles": disponibles, "ocupados": ocupados, "mantenimiento": mantenimiento}

    return render_template("cuartos.html", cuartos=cuartos, form=CuartoForm(), stats=stats)


@cuartos_bp.route("/agregar", methods=["POST"])
def agregar():
    """Agregar un nuevo cuarto"""
    form = CuartoForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("cuartos.index"))

    numero = form.numero.data.strip()
    piso = form.piso.data
    precio = float(form.precio.data)
    descripcion = form.descripcion.data.strip() if form.descripcion.data else ""
    estado = form.estado.data

    conn = conection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO cuartos (numero, piso, precio, descripcion, estado) VALUES (?, ?, ?, ?, ?)",
            (numero, piso, precio, descripcion, estado),
        )
        conn.commit()
        flash("Cuarto agregado correctamente", "success")
    except sqlite3.IntegrityError:
        flash("El número de cuarto ya existe", "error")
    except Exception as e:
        flash(f"Error al agregar cuarto: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("cuartos.index"))


@cuartos_bp.route("/editar/<int:id>", methods=["POST"])
def editar(id):
    """Editar un cuarto existente"""
    form = CuartoForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("cuartos.index"))

    numero = form.numero.data.strip()
    piso = form.piso.data
    precio = float(form.precio.data)
    descripcion = form.descripcion.data.strip() if form.descripcion.data else ""
    estado = form.estado.data

    conn = conection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE cuartos SET numero = ?, piso = ?, precio = ?, descripcion = ?, estado = ? WHERE id = ?",
            (numero, piso, precio, descripcion, estado, id),
        )
        conn.commit()
        flash("Cuarto actualizado correctamente", "success")
    except sqlite3.IntegrityError:
        flash("El número de cuarto ya existe", "error")
    except Exception as e:
        flash(f"Error al actualizar cuarto: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("cuartos.index"))


@cuartos_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    """Eliminar un cuarto"""
    conn = conection()
    cursor = conn.cursor()

    try:
        # Verificar si hay inquilinos asociados
        cursor.execute("SELECT COUNT(*) FROM inquilinos WHERE id_cuarto = ?", (id,))
        count = first_value(cursor.fetchone())

        if count > 0:
            flash("No se puede eliminar el cuarto porque tiene inquilinos asociados", "error")
        else:
            cursor.execute("DELETE FROM cuartos WHERE id = ?", (id,))
            conn.commit()
            flash("Cuarto eliminado correctamente", "success")
    except Exception as e:
        flash(f"Error al eliminar cuarto: {str(e)}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("cuartos.index"))


@cuartos_bp.route("/obtener/<int:id>")
def obtener(id):
    """Obtener datos de un cuarto para edición"""
    conn = conection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.id, c.numero, c.piso, c.precio, c.descripcion, c.estado,
               i.nombre || ' ' || i.apellido AS inquilino
        FROM cuartos c
        LEFT JOIN inquilinos i ON i.id_cuarto = c.id
        WHERE c.id = ?
    """,
        (id,),
    )
    cuarto = cursor.fetchone()

    cursor.close()
    conn.close()

    if cuarto:
        return jsonify(
            {
                "id": cuarto.get('id'),
                "numero": cuarto.get('numero'),
                "piso": cuarto.get('piso'),
                "precio": cuarto.get('precio'),
                "descripcion": cuarto.get('descripcion') or "",
                "estado": cuarto.get('estado'),
                "inquilino": cuarto.get('inquilino') or None,
            }
        )
    return jsonify({"error": "Cuarto no encontrado"}), 404

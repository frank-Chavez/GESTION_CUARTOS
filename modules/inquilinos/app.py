from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, BooleanField, DateField
from wtforms.validators import DataRequired, NumberRange, Regexp
from database import conection
import sqlite3

# Crear el Blueprint
inquilinos_bp = Blueprint(
    "inquilinos", __name__, template_folder="templates", static_folder="static", url_prefix="/inquilinos"
)


class InquilinoForm(FlaskForm):
    nombre = StringField(validators=[DataRequired()])
    apellido = StringField(validators=[DataRequired()])
    dni = StringField(validators=[DataRequired(), Regexp(r"^\d+$", message="El DNI debe ser numérico")])
    telefono = StringField(validators=[DataRequired()])
    cuarto = StringField(validators=[DataRequired()])
    renta_mensual = DecimalField(
        validators=[DataRequired(), NumberRange(min=0.01, message="La renta debe ser positiva")]
    )
    fecha_inicio = DateField(validators=[DataRequired()], format="%Y-%m-%d")
    ya_pago = BooleanField()


@inquilinos_bp.route("/")
def index():
    from flask import session, redirect, url_for

    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    """Lista todos los inquilinos"""
    conn = conection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            i.id,
            i.nombre,
            i.apellido,
            i.dni,
            i.telefono,
            c.numero AS cuarto,
            i.monto_mensual,
            strftime('%d/%m/%Y', i.fecha_ingreso) AS fecha_ingreso,
            CASE 
                WHEN pagos_mes.total IS NULL OR pagos_mes.total = 0 THEN 
                    CASE 
                        WHEN ultimo.ultimo_pago IS NOT NULL AND julianday('now') - julianday(ultimo.ultimo_pago) > 30 THEN 'Atrasado'
                        ELSE 'Pendiente'
                    END
                WHEN pagos_mes.total < i.monto_mensual THEN 'Pendiente'
                WHEN pagos_mes.total >= i.monto_mensual THEN 'Pagado'
                ELSE 'Pendiente'
            END AS estado_pago,
            COALESCE(i.monto_mensual - pagos_mes.total, i.monto_mensual) AS monto_pendiente
        FROM inquilinos i
        JOIN cuartos c ON i.id_cuarto = c.id
        LEFT JOIN (
            SELECT id_inquilino, SUM(monto) AS total
            FROM pagos
            WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
            GROUP BY id_inquilino
        ) pagos_mes ON i.id = pagos_mes.id_inquilino
        LEFT JOIN (
            SELECT id_inquilino, MAX(fecha) AS ultimo_pago
            FROM pagos
            GROUP BY id_inquilino
        ) ultimo ON i.id = ultimo.id_inquilino
        ORDER BY i.nombre
    """
    )
    inquilinos = cursor.fetchall()

    # Obtener cuartos disponibles
    cursor.execute(
        """
        SELECT id, numero, piso, precio 
        FROM cuartos 
        WHERE estado = 'disponible'
        ORDER BY numero
    """
    )
    cuartos_disponibles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "inquilinos.html", inquilinos=inquilinos, form=InquilinoForm(), cuartos_disponibles=cuartos_disponibles
    )


@inquilinos_bp.route("/agregar", methods=["POST"])
def agregar():
    """Agregar un nuevo inquilino"""
    form = InquilinoForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("inquilinos.index"))

    nombre = form.nombre.data.strip()
    apellido = form.apellido.data.strip()
    dni = form.dni.data.strip()
    telefono = form.telefono.data.strip()
    cuarto = form.cuarto.data.strip()
    renta_mensual = float(form.renta_mensual.data)
    fecha_inicio_date = form.fecha_inicio.data
    fecha_inicio = fecha_inicio_date.isoformat()
    dia_pago = fecha_inicio_date.day
    ya_pago = bool(form.ya_pago.data)

    try:
        with conection() as conn:
            cursor = conn.cursor()

            # 1. Crear o actualizar cuarto respetando estado actual
            cursor.execute("SELECT id, estado FROM cuartos WHERE numero = ?", (cuarto,))
            cuarto_row = cursor.fetchone()

            if cuarto_row:
                id_cuarto, estado_cuarto = cuarto_row["id"], cuarto_row["estado"]
                if estado_cuarto == "ocupado":
                    flash("El cuarto ya está ocupado", "error")
                    return redirect(url_for("inquilinos.index"))
                cursor.execute("UPDATE cuartos SET estado = 'ocupado' WHERE id = ?", (id_cuarto,))
            else:
                cursor.execute("INSERT INTO cuartos (numero, estado) VALUES (?, 'ocupado')", (cuarto,))
                id_cuarto = cursor.lastrowid

            # 2. Insertar el inquilino
            cursor.execute(
                """
                INSERT INTO inquilinos 
                (nombre, apellido, dni, telefono, id_cuarto, monto_mensual, dia_pago, fecha_ingreso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (nombre, apellido, dni, telefono, id_cuarto, renta_mensual, dia_pago, fecha_inicio),
            )

            inquilino_id = cursor.lastrowid

            # 3. Si marcó "ya pagó", crear pago inicial
            if ya_pago:
                cursor.execute(
                    """
                    INSERT INTO pagos 
                    (id_inquilino, fecha, monto, puntual, metodo_pago, observacion)
                    VALUES (?, ?, ?, 1, ?, 'Pago al momento de ingreso')
                    """,
                    (inquilino_id, fecha_inicio, renta_mensual, 'efectivo'),
                )

        flash("Inquilino agregado exitosamente", "success")
        return redirect(url_for("inquilinos.index"))

    except sqlite3.IntegrityError:
        flash("No se pudo agregar: datos duplicados o inválidos (DNI único)", "error")
        return redirect(url_for("inquilinos.index"))
    except Exception as e:
        import traceback
        print("[ERROR agregar inquilino]", type(e), e, traceback.format_exc())
        flash(f"Error al agregar inquilino: {type(e).__name__}: {e}", "error")
        return redirect(url_for("inquilinos.index"))


@inquilinos_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    """Editar un inquilino existente"""
    conn = conection()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            nombre = request.form.get("nombre", "").strip()
            apellido = request.form.get("apellido", "").strip()
            dni = request.form.get("dni", "").strip()
            telefono = request.form.get("telefono", "").strip()
            renta_mensual = request.form.get("renta_mensual", 0)

            # Validaciones básicas
            if not all([nombre, apellido, dni, telefono, renta_mensual]):
                flash("Todos los campos son obligatorios", "error")
                return redirect(url_for("inquilinos.index"))

            cursor.execute(
                """
                UPDATE inquilinos 
                SET nombre = ?, apellido = ?, dni = ?, telefono = ?, monto_mensual = ?
                WHERE id = ?
                """,
                (nombre, apellido, dni, telefono, float(renta_mensual), id),
            )
            conn.commit()
            flash("Inquilino actualizado exitosamente", "success")
        except Exception as e:
            flash(f"Error al actualizar: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("inquilinos.index"))

    # GET: obtener datos del inquilino
    cursor.execute(
        """
        SELECT i.*, c.numero AS cuarto
        FROM inquilinos i
        JOIN cuartos c ON i.id_cuarto = c.id
        WHERE i.id = ?
    """,
        (id,),
    )
    inquilino = cursor.fetchone()
    cursor.close()
    conn.close()

    if not inquilino:
        flash("Inquilino no encontrado", "error")
        return redirect(url_for("inquilinos.index"))

    return render_template("inquilinos.html", inquilino=inquilino, form=InquilinoForm())


@inquilinos_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    """Eliminar un inquilino"""
    try:
        with conection() as conn:
            cursor = conn.cursor()

            # Obtener el cuarto del inquilino
            cursor.execute("SELECT id_cuarto FROM inquilinos WHERE id = ?", (id,))
            result = cursor.fetchone()

            if result:
                id_cuarto = result[0]

                # Eliminar pagos asociados al inquilino primero
                cursor.execute("DELETE FROM pagos WHERE id_inquilino = ?", (id,))

                # Eliminar el inquilino
                cursor.execute("DELETE FROM inquilinos WHERE id = ?", (id,))

                # Liberar el cuarto (estado debe ser 'disponible' según el CHECK constraint)
                cursor.execute("UPDATE cuartos SET estado = 'disponible' WHERE id = ?", (id_cuarto,))

                flash("Inquilino eliminado exitosamente", "success")
            else:
                flash("Inquilino no encontrado", "error")

    except Exception as e:
        flash(f"Error al eliminar: {str(e)}", "error")

    return redirect(url_for("inquilinos.index"))

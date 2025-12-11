from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_wtf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, BooleanField, DateField
from wtforms.validators import DataRequired, NumberRange, Regexp
from database import conection, first_value
from datetime import datetime, timedelta

# removed remember-me token imports
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

from modules.inquilinos.app import inquilinos_bp
from modules.pagos.app import pagos_bp
from modules.config.app import config_bp
from modules.cuartos.app import cuartos_bp


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
app.config["DEBUG"] = os.getenv("FLASK_DEBUG") == "1"
# Persistir la sesión entre cierres del navegador (por defecto 30 días)
app.permanent_session_lifetime = timedelta(days=int(os.getenv("PERMANENT_DAYS", "30")))

# Cookie/session settings (can be adjusted via env vars)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_REFRESH_EACH_REQUEST=True,
)

# Inicializar CSRFProtect
csrf = CSRFProtect(app)


# Registrar los Blueprints
app.register_blueprint(inquilinos_bp)
app.register_blueprint(pagos_bp)
app.register_blueprint(config_bp)
app.register_blueprint(cuartos_bp)


def ensure_db_initialized():
    """If the database has no tables, initialize it using `script.sql`.

    This helps first-time deployments on hosting platforms (Railway) where
    the SQLite file may be empty. It will create the schema from
    `script.sql`. If no `script.sql` is present, this is a no-op.
    """
    try:
        conn = conection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios';")
        row = cur.fetchone()
        if row is None:
            # no usuarios table -> assume fresh DB
            sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "script.sql")
            if os.path.exists(sql_path):
                with open(sql_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                cur.executescript(sql)
                conn.commit()
                # Create a default admin user to allow initial login. Password: 'admin'
                try:
                    pw = generate_password_hash("admin")
                    cur.execute(
                        "INSERT INTO usuarios (nombre, usuario, password, rol, fecha_creacion) VALUES (?, ?, ?, 'admin', ?)",
                        ("Administrador", "admin", pw, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                    print("DB inicializada y usuario admin creado (usuario: admin, contraseña: admin)")
                except Exception:
                    # ignore user creation errors but keep DB created
                    pass
        cur.close()
        conn.close()
    except Exception as e:
        # Do not crash the app if DB initialization fails; log instead.
        print("Advertencia: no se pudo inicializar la base de datos automáticamente:", e)


# Intentamos inicializar la base de datos en arranque (útil en despliegues)
ensure_db_initialized()


def ensure_schema_migrations():
    """Apply lightweight schema migrations for existing databases.

    This checks for columns that newer code expects and adds them if missing.
    It keeps migrations minimal and safe (uses ALTER TABLE ADD COLUMN).
    """
    try:
        conn = conection()
        cur = conn.cursor()
        # Check cuartos table columns
        cur.execute("PRAGMA table_info('cuartos')")
        cols = [r[1] for r in cur.fetchall()]
        if 'piso' not in cols:
            try:
                cur.execute("ALTER TABLE cuartos ADD COLUMN piso INTEGER DEFAULT 1")
            except Exception:
                pass
        if 'precio' not in cols:
            try:
                cur.execute("ALTER TABLE cuartos ADD COLUMN precio REAL DEFAULT 0.0")
            except Exception:
                pass
        # Check pagos table for new columns required by code
        try:
            cur.execute("PRAGMA table_info('pagos')")
            pagos_cols = [r[1] for r in cur.fetchall()]
            if 'metodo_pago' not in pagos_cols:
                try:
                    cur.execute("ALTER TABLE pagos ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'")
                except Exception:
                    pass
        except Exception:
            # ignore if pagos table doesn't exist yet
            pass
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print('Advertencia: error al aplicar migraciones ligeras de esquema:', e)


# Ensure schema migrations run at startup to support older DBs
ensure_schema_migrations()


# Remember-me/token-based persistence removed per user request


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


class LoginForm(FlaskForm):
    usuario = StringField(validators=[DataRequired()])
    password = StringField(validators=[DataRequired()])
    # remember field removed: Mantener sesión iniciada deshabilitado


@app.route("/", methods=["GET", "POST"])
def loguin():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        usuario = form.usuario.data.strip()
        password = form.password.data.strip()
        conn = conection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, usuario, password FROM usuarios WHERE usuario = ?", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            # Support both dict rows (new row_factory) and sequence rows (old)
            if isinstance(user, dict):
                pw_hash = user.get('password')
                uid = user.get('id')
            else:
                # tuple/sequence fallback
                try:
                    pw_hash = user[2]
                except Exception:
                    pw_hash = None
                try:
                    uid = user[0]
                except Exception:
                    uid = None

            if pw_hash and check_password_hash(pw_hash, password):
                session["user_id"] = uid
                # Mantener sesión eliminado: no persistimos entre cierres del navegador
                session.permanent = False
                return redirect(url_for("dashboard"))
            else:
                error = "Usuario o contraseña incorrectos"
    else:
        # Si se envió el formulario pero no pasó validación, mostrar errores para depuración
        if request.method == 'POST':
            errs = []
            try:
                for f, e in form.errors.items():
                    errs.append(f + ': ' + '; '.join(e))
            except Exception:
                errs.append('error desconocido en validación')
            error = 'Error en formulario: ' + (', '.join(errs) if errs else 'validación fallida')
    return render_template("loguin.html", form=form, error=error)


@app.route("/logout", methods=["POST"])
def logout():
    # Simple logout: clear session and redirect to login
    user_id = session.get("user_id")
    if user_id:
        session.clear()
        flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("loguin"))


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    conn = conection()
    cursor = conn.cursor()

    # Ganancias por mes
    cursor.execute(
        """
        SELECT strftime('%Y-%m', fecha), SUM(monto)
        FROM pagos
        GROUP BY strftime('%Y-%m', fecha)
    """
    )
    data = cursor.fetchall()

    # Pagos recientes (4)
    cursor.execute(
        """
SELECT 
    i.id,
    i.nombre,
    i.apellido,
    i.dni,
    i.telefono,
    i.fecha_ingreso,
    i.monto_mensual,
    i.dia_pago,
    c.numero AS cuarto,
    CASE
        WHEN pagos_mes.total IS NULL OR pagos_mes.total = 0 THEN 
            CASE 
                WHEN ultimo.ultimo_pago IS NOT NULL AND julianday('now') - julianday(ultimo.ultimo_pago) > 30 THEN 'Atrasado'
                ELSE 'Pendiente'
            END
        WHEN pagos_mes.total < i.monto_mensual THEN 'Pendiente'
        WHEN pagos_mes.total >= i.monto_mensual THEN 'Pagado'
        ELSE 'Pendiente'
    END AS estado_pago
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
    # Convertir sqlite3.Row a dict para evitar errores de atributo en las plantillas
    inquilinos = [dict(r) for r in inquilinos]

    # Estadísticas para las tarjetas del dashboard

    # Total de cuartos y cuartos ocupados
    cursor.execute("SELECT COUNT(*) FROM cuartos")
    total_cuartos = first_value(cursor.fetchone()) or 0

    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'ocupado'")
    cuartos_ocupados = first_value(cursor.fetchone()) or 0

    # Ganancias del mes actual
    cursor.execute(
        """
        SELECT COALESCE(SUM(monto), 0)
        FROM pagos
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    """
    )
    ganancias_mes = first_value(cursor.fetchone()) or 0

    # Total de inquilinos activos
    cursor.execute("SELECT COUNT(*) FROM inquilinos")
    total_inquilinos = first_value(cursor.fetchone()) or 0

    # Pagos pendientes (inquilinos sin pago en los últimos 30 días)
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM inquilinos i
        LEFT JOIN (
            SELECT id_inquilino, MAX(fecha) AS ultimo_pago
            FROM pagos
            GROUP BY id_inquilino
        ) ultimo ON i.id = ultimo.id_inquilino
        WHERE ultimo.ultimo_pago IS NULL 
           OR julianday('now') - julianday(ultimo.ultimo_pago) > 30
    """
    )
    pagos_pendientes = first_value(cursor.fetchone()) or 0

    # Obtener cuartos disponibles para el formulario
    cursor.execute(
        """
        SELECT id, numero, piso, precio 
        FROM cuartos 
        WHERE estado = 'disponible'
        ORDER BY numero
        """
    )
    cuartos_disponibles = cursor.fetchall()
    cuartos_disponibles = [dict(r) for r in cuartos_disponibles]

    cursor.close()
    conn.close()

    # Datos para el gráfico
    meses = [row[0] for row in data]
    ganancias = [row[1] for row in data]

    return render_template(
        "dashboard.html",
        meses=meses,
        ganancias=ganancias,
        inquilinos=inquilinos,
        total_cuartos=total_cuartos,
        cuartos_ocupados=cuartos_ocupados,
        ganancias_mes=ganancias_mes,
        total_inquilinos=total_inquilinos,
        pagos_pendientes=pagos_pendientes,
        form=InquilinoForm(),
        cuartos_disponibles=cuartos_disponibles,
    )


@app.route("/agregar", methods=["POST"])
def agregar_inquilino():
    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    form = InquilinoForm()
    if not form.validate_on_submit():
        # Mostrar el primer error encontrado para no saturar el usuario
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("dashboard"))

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
                id_cuarto, estado_cuarto = cuarto_row[0], cuarto_row[1]
                if estado_cuarto == "ocupado":
                    flash("El cuarto ya está ocupado", "error")
                    return redirect(url_for("dashboard"))
                cursor.execute("UPDATE cuartos SET estado = 'ocupado' WHERE id = ?", (id_cuarto,))
            else:
                cursor.execute("INSERT INTO cuartos (numero, estado) VALUES (?, 'ocupado')", (cuarto,))
                id_cuarto = cursor.lastrowid

            # 2. Insertar el inquilino con fecha_ingreso y apellido
            cursor.execute(
                """
                INSERT INTO inquilinos 
                (nombre, apellido, dni, telefono, id_cuarto, monto_mensual, dia_pago, fecha_ingreso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (nombre, apellido, dni, telefono, id_cuarto, renta_mensual, dia_pago, fecha_inicio),
            )

            inquilino_id = cursor.lastrowid

            # 3. Si marcó "ya pagó", crear pago inicial automáticamente
            if ya_pago:
                cursor.execute(
                    """
                    INSERT INTO pagos 
                    (id_inquilino, fecha, monto, puntual, observacion)
                    VALUES (?, ?, ?, 1, 'Pago al momento de ingreso')
                    """,
                    (inquilino_id, fecha_inicio, renta_mensual),
                )

        flash("Inquilino agregado exitosamente", "success")
        return redirect(url_for("dashboard"))

    except sqlite3.IntegrityError as e:
        # Captura violaciones de UNIQUE (por ejemplo DNI duplicado)
        flash("No se pudo agregar: datos duplicados o inválidos (DNI único)", "error")
        return redirect(url_for("dashboard"))
    except Exception as e:
        flash(f"Error al agregar inquilino: {str(e)}", "error")
        return redirect(url_for("dashboard"))


@app.route("/editar_inquilino/<int:id>", methods=["POST"])
def editar_inquilino(id):
    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    form = InquilinoForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("dashboard"))

    nombre = form.nombre.data.strip()
    apellido = form.apellido.data.strip()
    dni = form.dni.data.strip()
    telefono = form.telefono.data.strip()
    cuarto = form.cuarto.data.strip()
    renta_mensual = float(form.renta_mensual.data)
    fecha_inicio_date = form.fecha_inicio.data
    fecha_inicio = fecha_inicio_date.isoformat()
    dia_pago = fecha_inicio_date.day

    try:
        with conection() as conn:
            cursor = conn.cursor()

            # Obtener el cuarto actual del inquilino
            cursor.execute("SELECT id_cuarto FROM inquilinos WHERE id = ?", (id,))
            inquilino_row = cursor.fetchone()
            if not inquilino_row:
                flash("Inquilino no encontrado", "error")
                return redirect(url_for("dashboard"))

            cuarto_actual_id = inquilino_row[0]

            # Verificar si el nuevo cuarto existe y está disponible
            cursor.execute("SELECT id, estado FROM cuartos WHERE numero = ?", (cuarto,))
            cuarto_row = cursor.fetchone()

            if cuarto_row:
                id_cuarto, estado_cuarto = cuarto_row[0], cuarto_row[1]
                # Si el cuarto es diferente al actual y está ocupado, error
                if id_cuarto != cuarto_actual_id and estado_cuarto == "ocupado":
                    flash("El cuarto ya está ocupado por otro inquilino", "error")
                    return redirect(url_for("dashboard"))
            else:
                # Crear el nuevo cuarto
                cursor.execute("INSERT INTO cuartos (numero, estado) VALUES (?, 'ocupado')", (cuarto,))
                id_cuarto = cursor.lastrowid

            # Si cambió de cuarto, liberar el anterior y ocupar el nuevo
            if id_cuarto != cuarto_actual_id:
                cursor.execute("UPDATE cuartos SET estado = 'libre' WHERE id = ?", (cuarto_actual_id,))
                cursor.execute("UPDATE cuartos SET estado = 'ocupado' WHERE id = ?", (id_cuarto,))

            # Actualizar el inquilino
            cursor.execute(
                """
                UPDATE inquilinos 
                SET nombre = ?, apellido = ?, dni = ?, telefono = ?, id_cuarto = ?, 
                    monto_mensual = ?, dia_pago = ?, fecha_ingreso = ?
                WHERE id = ?
                """,
                (nombre, apellido, dni, telefono, id_cuarto, renta_mensual, dia_pago, fecha_inicio, id),
            )

        flash("Inquilino actualizado exitosamente", "success")
        return redirect(url_for("dashboard"))

    except sqlite3.IntegrityError:
        flash("No se pudo actualizar: datos duplicados o inválidos (DNI único)", "error")
        return redirect(url_for("dashboard"))
    except Exception as e:
        flash(f"Error al actualizar inquilino: {str(e)}", "error")
        return redirect(url_for("dashboard"))


@app.route("/eliminar_inquilino/<int:id>", methods=["POST"])
def eliminar_inquilino(id):
    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    try:
        with conection() as conn:
            cursor = conn.cursor()

            # Obtener el cuarto del inquilino antes de eliminarlo
            cursor.execute("SELECT id_cuarto FROM inquilinos WHERE id = ?", (id,))
            inquilino_row = cursor.fetchone()

            if not inquilino_row:
                flash("Inquilino no encontrado", "error")
                return redirect(url_for("dashboard"))

            id_cuarto = inquilino_row[0]

            # Eliminar los pagos del inquilino primero
            cursor.execute("DELETE FROM pagos WHERE id_inquilino = ?", (id,))

            # Eliminar el inquilino
            cursor.execute("DELETE FROM inquilinos WHERE id = ?", (id,))

            # Liberar el cuarto
            cursor.execute("UPDATE cuartos SET estado = 'disponible' WHERE id = ?", (id_cuarto,))

        flash("Inquilino eliminado exitosamente", "success")
        return redirect(url_for("dashboard"))

    except Exception as e:
        flash(f"Error al eliminar inquilino: {str(e)}", "error")
        return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)

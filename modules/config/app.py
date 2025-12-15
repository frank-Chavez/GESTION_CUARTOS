from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import re
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField
from wtforms.validators import DataRequired, NumberRange
from database import conection
import os
import subprocess
import json
from pywebpush import webpush, WebPushException
from typing import Optional

# Crear el Blueprint
config_bp = Blueprint(
    "config", __name__, template_folder="templates", static_folder="static", url_prefix="/configuracion"
)


class CuartoForm(FlaskForm):
    numero = StringField("Número", validators=[DataRequired()])
    estado = SelectField(
        "Estado",
        choices=[("libre", "Disponible"), ("ocupado", "Ocupado"), ("mantenimiento", "Mantenimiento")],
        validators=[DataRequired()],
    )


@config_bp.route("/")
def index():
    from flask import session, redirect, url_for

    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    """Página de configuración"""
    conn = conection()
    cursor = conn.cursor()

    # Obtener todos los cuartos
    cursor.execute(
        """
        SELECT 
            c.id,
            c.numero,
            c.estado,
            i.nombre AS inquilino_nombre
        FROM cuartos c
        LEFT JOIN inquilinos i ON c.id = i.id_cuarto
        ORDER BY c.numero
    """
    )
    cuartos = cursor.fetchall()

    # Estadísticas generales
    cursor.execute("SELECT COUNT(*) FROM cuartos")
    total_cuartos = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'libre'")
    cuartos_disponibles = cursor.fetchone()[0] or 0

    # Cargar clave pública VAPID para uso en la plantilla (si existe)
    vapid_public_key = None
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        vapid_file = os.path.join(base_dir, "vapid_keys.json")
        if os.path.exists(vapid_file):
            with open(vapid_file, "r", encoding="utf-8") as f:
                vk = json.load(f)
                vapid_public_key = vk.get("publicKey")
    except Exception:
        vapid_public_key = None
    cursor.execute("SELECT COUNT(*) FROM cuartos WHERE estado = 'ocupado'")
    cuartos_ocupados = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM inquilinos")
    total_inquilinos = cursor.fetchone()[0] or 0

    # Obtener datos del usuario logueado
    usuario_id = session.get("user_id")
    usuario = None
    if usuario_id:
        cursor.execute("SELECT nombre, usuario, rol, fecha_creacion FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = cursor.fetchone()

        vapid_public_key = (vapid_public_key,)
    cursor.close()
    conn.close()

    # Detectar si el acceso directo ya existe en el Escritorio
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_name = os.path.join(desktop, "sistema cuartos.lnk")
        shortcut_exists = os.path.exists(shortcut_name)
    except Exception:
        shortcut_exists = False

    # Cargar preferencias de usuario (si aplica)
    noti_pendientes = False
    noti_atrasados = False
    try:
        if usuario_id:
            # helper inline: obtener setting
            def _get_setting(user_id: int, key: str) -> Optional[str]:
                try:
                    with conection() as c:
                        cur = c.cursor()
                        cur.execute(
                            "CREATE TABLE IF NOT EXISTS settings (user_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(user_id, key))"
                        )
                        cur.execute("SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key))
                        r = cur.fetchone()
                        return r[0] if r else None
                except Exception:
                    return None

            v1 = _get_setting(usuario_id, "noti_pendientes")
            v2 = _get_setting(usuario_id, "noti_atrasados")
            noti_pendientes = True if v1 == "1" else False
            noti_atrasados = True if v2 == "1" else False
    except Exception:
        noti_pendientes = False
        noti_atrasados = False

    return render_template(
        "config.html",
        cuartos=cuartos,
        form=CuartoForm(),
        total_cuartos=total_cuartos,
        cuartos_disponibles=cuartos_disponibles,
        cuartos_ocupados=cuartos_ocupados,
        total_inquilinos=total_inquilinos,
        usuario=usuario,
        shortcut_exists=shortcut_exists,
        noti_pendientes=noti_pendientes,
        noti_atrasados=noti_atrasados,
    )


@config_bp.route("/usuario/editar", methods=["POST"])
def editar_perfil():
    """Editar nombre/usuario del usuario logueado"""
    from flask import session

    if not session.get("user_id"):
        return redirect(url_for("loguin"))
    usuario_field = request.form.get("usuario", "").strip()

    if not usuario_field:
        flash("El usuario es requerido", "error")
        return redirect(url_for("config.index"))

    try:
        with conection() as conn:
            cursor = conn.cursor()
            # Verificar unicidad del usuario
            cursor.execute(
                "SELECT id FROM usuarios WHERE usuario = ? AND id != ?", (usuario_field, session.get("user_id"))
            )
            if cursor.fetchone():
                flash("El nombre de usuario ya está en uso", "error")
                return redirect(url_for("config.index"))

            # Actualizar solo el campo usuario
            cursor.execute(
                "UPDATE usuarios SET usuario = ? WHERE id = ?",
                (usuario_field, session.get("user_id")),
            )
            flash("Perfil actualizado", "success")
    except Exception as e:
        flash(f"Error al actualizar perfil: {str(e)}", "error")

    return redirect(url_for("config.index"))


@config_bp.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    from flask import session

    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "No autenticado"}), 401

    data = request.get_json() or {}
    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({"ok": False, "message": "Suscripción inválida"}), 400

    try:
        with conection() as conn:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS push_subscriptions (user_id INTEGER, endpoint TEXT PRIMARY KEY, p256dh TEXT, auth TEXT)"
            )
            cur.execute(
                "INSERT OR REPLACE INTO push_subscriptions (user_id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?)",
                (session.get("user_id"), endpoint, p256dh, auth),
            )
            conn.commit()
        return jsonify({"ok": True, "message": "Suscripción guardada"}), 200
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@config_bp.route("/push/send_test", methods=["POST"])
def push_send_test():
    from flask import session

    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "No autenticado"}), 401

    # Intentar obtener una suscripción para el usuario
    try:
        with conection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?", (session.get("user_id"),)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"ok": False, "message": "No hay suscripciones para este usuario"}), 404
            sub = {"endpoint": row[0], "keys": {"p256dh": row[1], "auth": row[2]}}
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500

    # Cargar clave privada VAPID
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        vapid_file = os.path.join(base_dir, "vapid_keys.json")
        if not os.path.exists(vapid_file):
            return jsonify({"ok": False, "message": "VAPID keys no configuradas"}), 500
        with open(vapid_file, "r", encoding="utf-8") as f:
            vk = json.load(f)
        vapid_private_pem = vk.get("privateKeyPem")
        vapid_claims = {"sub": "mailto:admin@example.com"}

        # Enviar notificación de prueba
        payload = json.dumps({"title": "Prueba", "body": "Notificación de prueba desde Sistema Gestión Cuartos"})
        webpush(subscription_info=sub, data=payload, vapid_private_key=vapid_private_pem, vapid_claims=vapid_claims)
        return jsonify({"ok": True, "message": "Notificación enviada"}), 200
    except WebPushException as ex:
        return jsonify({"ok": False, "message": str(ex)}), 500
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# Endpoints para crear/eliminar acceso directo en Escritorio
@config_bp.route("/shortcut/create", methods=["POST"])
def crear_shortcut():
    from flask import session

    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "No autenticado"}), 401

    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        script = os.path.join(base_dir, "crear_shortcut_url.ps1")
        url = request.json.get("url") if request.is_json else request.form.get("url")
        name = request.json.get("name") if request.is_json else request.form.get("name")
        if not name:
            name = "sistema cuartos"

        # Intentar usar icono .ico incluido en static/img si existe
        icon_default = os.path.join(base_dir, "static", "img", "acceso_directo.ico")
        icon_arg = icon_default if os.path.exists(icon_default) else None

        # Ejecutar PowerShell para crear el .lnk
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Url", url, "-Name", name]
        if icon_arg:
            cmd += ["-IconPath", icon_arg]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            return jsonify({"ok": False, "message": proc.stderr or "Error al crear acceso directo"}), 500

        return jsonify({"ok": True, "message": "Acceso directo creado"}), 200
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@config_bp.route("/shortcut/delete", methods=["POST"])
def eliminar_shortcut():
    from flask import session

    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "No autenticado"}), 401

    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        name = request.json.get("name") if request.is_json else request.form.get("name")
        if not name:
            name = "sistema cuartos"
        shortcut_path = os.path.join(desktop, f"{name}.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            return jsonify({"ok": True, "message": "Acceso directo eliminado"}), 200
        else:
            return jsonify({"ok": False, "message": "No existe el acceso directo"}), 404
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# Endpoint para actualizar preferencias (notificaciones)
@config_bp.route("/preferences/update", methods=["POST"])
def update_preference():
    from flask import session

    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "No autenticado"}), 401

    data = request.get_json() or {}
    key = data.get("key")
    value = data.get("value")
    if key not in ("noti_pendientes", "noti_atrasados"):
        return jsonify({"ok": False, "message": "Clave no válida"}), 400

    # Normalizar valor a '1' o '0'
    val = "1" if value in (True, "1", 1, "true", "True") else "0"

    try:
        with conection() as conn:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS settings (user_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(user_id, key))"
            )
            cur.execute(
                "INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)",
                (session.get("user_id"), key, val),
            )
            conn.commit()
        return jsonify({"ok": True, "message": "Preferencia actualizada"}), 200
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@config_bp.route("/cuartos/agregar", methods=["POST"])
def agregar_cuarto():
    """Agregar un nuevo cuarto"""
    form = CuartoForm()

    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()), ["Datos inválidos"])[0]
        flash(first_error, "error")
        return redirect(url_for("config.index"))

    numero = form.numero.data.strip()
    estado = form.estado.data

    try:
        with conection() as conn:
            cursor = conn.cursor()

            # Verificar si el cuarto ya existe
            cursor.execute("SELECT id FROM cuartos WHERE numero = ?", (numero,))
            if cursor.fetchone():
                flash("Ya existe un cuarto con ese número", "error")
                return redirect(url_for("config.index"))

            cursor.execute("INSERT INTO cuartos (numero, estado) VALUES (?, ?)", (numero, estado))
            flash("Cuarto agregado exitosamente", "success")
    except Exception as e:
        flash(f"Error al agregar cuarto: {str(e)}", "error")

    return redirect(url_for("config.index"))


@config_bp.route("/cuartos/editar/<int:id>", methods=["POST"])
def editar_cuarto(id):
    """Editar estado de un cuarto"""
    estado = request.form.get("estado")

    if estado not in ["libre", "ocupado", "mantenimiento"]:
        flash("Estado inválido", "error")
        return redirect(url_for("config.index"))

    try:
        with conection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE cuartos SET estado = ? WHERE id = ?", (estado, id))
            flash("Cuarto actualizado exitosamente", "success")
    except Exception as e:
        flash(f"Error al actualizar cuarto: {str(e)}", "error")

    return redirect(url_for("config.index"))


@config_bp.route("/cuartos/eliminar/<int:id>", methods=["POST"])
def eliminar_cuarto(id):
    """Eliminar un cuarto"""
    try:
        with conection() as conn:
            cursor = conn.cursor()

            # Verificar si el cuarto tiene inquilinos
            cursor.execute("SELECT COUNT(*) FROM inquilinos WHERE id_cuarto = ?", (id,))
            if cursor.fetchone()[0] > 0:
                flash("No se puede eliminar: el cuarto tiene inquilinos asignados", "error")
                return redirect(url_for("config.index"))

            cursor.execute("DELETE FROM cuartos WHERE id = ?", (id,))
            flash("Cuarto eliminado exitosamente", "success")
    except Exception as e:
        flash(f"Error al eliminar cuarto: {str(e)}", "error")

    return redirect(url_for("config.index"))


@config_bp.route("/usuario/seguridad", methods=["POST"])
def cambiar_contrasena():
    """Cambiar la contraseña del usuario logueado"""
    from flask import session

    if not session.get("user_id"):
        return redirect(url_for("loguin"))

    new = request.form.get("new_password", "").strip()
    confirm = request.form.get("confirm_password", "").strip()

    if not new or not confirm:
        flash("Todos los campos son requeridos", "error")
        return redirect(url_for("config.index"))

    if new != confirm:
        flash("La nueva contraseña y la confirmación no coinciden", "error")
        return redirect(url_for("config.index"))

    # Reglas de contraseña:
    # - Debe contener al menos una mayúscula, una minúscula, un número y un carácter especial
    # - Longitud mínima: 8 caracteres (se actualiza a política más segura)
    if len(new) < 8:
        flash("La contraseña debe tener al menos 8 caracteres", "error")
        return redirect(url_for("config.index"))

    if not re.search(r"[A-Z]", new):
        flash("La contraseña debe contener al menos una letra mayúscula", "error")
        return redirect(url_for("config.index"))

    if not re.search(r"[a-z]", new):
        flash("La contraseña debe contener al menos una letra minúscula", "error")
        return redirect(url_for("config.index"))

    if not re.search(r"\d", new):
        flash("La contraseña debe contener al menos un número", "error")
        return redirect(url_for("config.index"))

    if not re.search(r"[^A-Za-z0-9]", new):
        flash("La contraseña debe contener al menos un carácter especial", "error")
        return redirect(url_for("config.index"))

    try:
        with conection() as conn:
            cursor = conn.cursor()
            # Actualizamos sin comprobar la contraseña anterior (según solicitud)
            new_hash = generate_password_hash(new)
            cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_hash, session.get("user_id")))
            flash("Contraseña actualizada", "success")
    except Exception as e:
        flash(f"Error al actualizar contraseña: {str(e)}", "error")

    return redirect(url_for("config.index"))

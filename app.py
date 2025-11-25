from flask import Flask, render_template, request, redirect, url_for, flash
from database import conection
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para flash messages


@app.route("/")
@app.route("/dashboard")
def dashboard():
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
            i.nombre,
            c.numero AS cuarto,
            i.monto_mensual,
            strftime('%d/%m/%Y', p.fecha) AS fecha,
            p.puntual
        FROM pagos p
        JOIN inquilinos i ON p.id_inquilino = i.id
        JOIN cuartos c ON i.id_cuarto = c.id
        ORDER BY p.fecha DESC
        LIMIT 4;
    """
    )
    Pagos = cursor.fetchall()

    # Obtener 5 inquilinos con su información más reciente
    cursor.execute("""
        SELECT 
            i.nombre AS nombre,
            c.numero AS cuarto,
            MIN(strftime('%d/%m/%Y', p.fecha)) AS fecha_ingreso,
            CASE 
                WHEN p2.puntual = 1 THEN 'Pagado'
                ELSE 'Pendiente'
            END AS estado_pago
        FROM inquilinos i
        JOIN cuartos c ON i.id_cuarto = c.id
        JOIN pagos p ON i.id = p.id_inquilino
        LEFT JOIN (
            SELECT id_inquilino, puntual, fecha
            FROM pagos
            WHERE (id_inquilino, fecha) IN (
                SELECT id_inquilino, MAX(fecha)
                FROM pagos
                GROUP BY id_inquilino
            )
        ) p2 ON i.id = p2.id_inquilino
        GROUP BY i.id, i.nombre, c.numero, p2.puntual
        ORDER BY i.id
        LIMIT 4
    """)
    inquilinos = cursor.fetchall()

    cursor.close()
    conn.close()

    # Datos para el gráfico
    meses = [row[0] for row in data]
    ganancias = [row[1] for row in data]

    return render_template("dashboard.html", meses=meses, ganancias=ganancias, Pagos=Pagos, inquilinos=inquilinos)


@app.route("/agregar_inquilino", methods=["POST"])
def agregar_inquilino():
    try:
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        dni = request.form.get('dni')
        telefono = request.form.get('telefono')
        cuarto = request.form.get('cuarto')
        renta_mensual = request.form.get('renta_mensual')
        fecha_inicio = request.form.get('fecha_inicio')
        
        # Validación básica
        if not all([nombre, dni, cuarto, renta_mensual]):
            flash('Por favor completa todos los campos obligatorios', 'error')
            return redirect(url_for('dashboard'))
        
        conn = conection()
        cursor = conn.cursor()
        
        # Verificar si el cuarto existe, si no, crearlo
        cursor.execute("SELECT id FROM cuartos WHERE numero = ?", (cuarto,))
        cuarto_existente = cursor.fetchone()
        
        if cuarto_existente:
            id_cuarto = cuarto_existente['id']
            # Actualizar estado del cuarto a ocupado
            cursor.execute("UPDATE cuartos SET estado = 'ocupado' WHERE id = ?", (id_cuarto,))
        else:
            # Crear nuevo cuarto
            cursor.execute(
                "INSERT INTO cuartos (numero, estado) VALUES (?, 'ocupado')",
                (cuarto,)
            )
            id_cuarto = cursor.lastrowid
        
        # Insertar el nuevo inquilino
        # Si no se proporciona día de pago, usar el día 1
        dia_pago = 1
        cursor.execute(
            """
            INSERT INTO inquilinos (nombre, dni, telefono, id_cuarto, monto_mensual, dia_pago)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nombre, dni, telefono, id_cuarto, float(renta_mensual), dia_pago)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Inquilino agregado exitosamente', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Error al agregar inquilino: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True)

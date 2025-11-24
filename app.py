from flask import Flask, render_template
from database import conection
from datetime import datetime

app = Flask(__name__)


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
    inquilinos = cursor.fetchall()

    cursor.close()
    conn.close()

    # Datos para el gráfico
    meses = [row[0] for row in data]
    ganancias = [row[1] for row in data]

    return render_template("dashboard.html", meses=meses, ganancias=ganancias, inquilinos=inquilinos)


if __name__ == "__main__":
    app.run(debug=True)

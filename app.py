from flask import Flask, render_template
from database import conection
from datetime import datetime


app = Flask(__name__)


@app.route("/")
@app.route("/dashboard")
def dashboard():
    conn = conection()
    cursor = conn.cursor()

    cursor.execute("SELECT strftime('%Y-%m', fecha), SUM(monto) FROM pagos GROUP BY strftime('%Y-%m', fecha)")
    data = cursor.fetchall()
    conn.close()

    meses = [row[0] for row in data]
    ganancias = [row[1] for row in data]

    return render_template("dashboard.html", meses=meses, ganancias=ganancias)


if __name__ == "__main__":
    app.run(debug=True)

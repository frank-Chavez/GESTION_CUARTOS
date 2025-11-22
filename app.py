from flask import Flask, render_template, url_for


app = Flask(__name__)


@app.route("/")
@app.route("/dashboard")
def home():
    return render_template("dashboard.html")



def init_db():
    import os
    import sqlite3
    
    if not os.path.exists("database.db"):
        conn = sqlite3.connect("database.db")
        with open("script.sql", "r") as f:
            conn.executescript(f.read())
        conn.close()
        print("Base de datos inicializada.")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

from sqlite3 import connect


def conn():
    conn = connect("database.db")
    return conn

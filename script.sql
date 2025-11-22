CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('admin', 'usuario')),
    fecha_creacion TEXT NOT NULL
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE inquilinos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    dni TEXT NOT NULL UNIQUE,
    telefono TEXT,
    cuarto TEXT NOT NULL,
    monto_mensual REAL NOT NULL,
    dia_pago INTEGER NOT NULL,
    notas TEXT
);
CREATE TABLE pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_inquilino INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    monto REAL NOT NULL,
    observacion TEXT,
    puntual BOOLEAN NOT NULL,
    FOREIGN KEY (id_inquilino) REFERENCES inquilinos(id)
);
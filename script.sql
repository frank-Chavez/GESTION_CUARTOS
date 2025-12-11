CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('admin', 'usuario')),
    fecha_creacion TEXT NOT NULL
);
CREATE TABLE inquilinos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    dni TEXT NOT NULL UNIQUE,
    telefono TEXT,
    id_cuarto INTEGER,
    monto_mensual REAL NOT NULL,
    dia_pago INTEGER NOT NULL,
    notas TEXT,
    fecha_ingreso TEXT,
    apellido TEXT,
    FOREIGN KEY (id_cuarto) REFERENCES cuartos(id)
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
CREATE TABLE cuartos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    estado TEXT NOT NULL CHECK(estado IN ('ocupado', 'libre'))
);
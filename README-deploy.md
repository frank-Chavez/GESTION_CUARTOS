# Despliegue rápido en Railway (gratis para uso ligero)

Este archivo explica paso a paso cómo desplegar esta app Flask (SQLite) en Railway, que es la opción más fácil y gratuita para uso de pocas visitas.

Requisitos previos

- Cuenta en https://railway.app (puedes entrar con GitHub).
- Código subido a GitHub (este repo ya está en `https://github.com/frank-Chavez/GESTION_CUARTOS.git`).

Comandos útiles (Windows `cmd.exe`)

1. Para generar un `requirements.txt` con versiones exactas (opcional, recomendado):

```
python -m pip freeze > requirements.txt
```

2. Si necesitas subir cambios y ya tienes el remoto configurado:

```
git add .
git commit -m "Actualiza deploy: README-deploy"
git push
```

Configuración en Railway

1. New Project → "Deploy from GitHub" → selecciona `frank-Chavez/GESTION_CUARTOS`.
2. Railway detectará Python/Flask. Si te pide el comando de arranque, usa:

```
gunicorn app:app -b 0.0.0.0:$PORT -w 2
```

3. Añade variables de entorno en Settings → Variables:

- `SECRET_KEY`: una cadena secreta larga (ej: `change-me` → cámbiala por seguridad).
- `DATABASE_URL`: ruta donde se guardará el archivo SQLite en el disco persistente. Por defecto esta app usa `/data/database.db`.

Nota sobre inicialización de la base de datos

- Al iniciarse, la aplicación intentará inicializar el esquema si la base de datos está vacía usando `script.sql` incluido en el repo. Si no existe un usuario, se creará un usuario administrador por defecto `usuario: admin`, `contraseña: admin` para facilitar el primer acceso — cambia la contraseña al iniciar sesión.
- `FLASK_DEBUG`: `0` en producción.

Volumen persistente (importante para SQLite)

1. En Railway añade el plugin **Persistent Disk** (o el plugin **SQLite** si aparece).
2. Railway te indicará una ruta donde montar el disco (típicamente `/data`); apunta ahí el `DATABASE_URL`, por ejemplo `/data/database.db`.
3. La aplicación ya usa `DATABASE_URL` (variable de entorno) y por defecto apunta a `/data/database.db` si la variable no está establecida.

Notas sobre `database.py`

La función `conection()` lee `DATABASE_URL` y, si no existe, usa `/data/database.db`:

```python
db_path = os.getenv("DATABASE_URL", "/data/database.db")
```

Probar localmente con Gunicorn

1. Instala dependencias:

```
python -m pip install -r requirements.txt
```

2. Ejecuta localmente (cmd.exe):

```
set PORT=8000
gunicorn app:app -b 0.0.0.0:%PORT% -w 2
```

Luego abre `http://localhost:8000` en el navegador.

Acciones posteriores sugeridas

- Cambiar `SECRET_KEY` por una cadena segura en Railway.
- Si prefieres no usar SQLite en producción en el futuro, migrar a PostgreSQL (Railway ofrece PostgreSQL como plugin).

Problemas comunes

- Si ves errores de permisos al crear el archivo SQLite, asegúrate de que Railway haya montado un volumen persistente y que `DATABASE_URL` apunte a una ruta dentro de él (p.ej. `/data/database.db`).

Contacto

- Si quieres, puedo guiarte paso a paso dentro del panel de Railway o preparar un script de deploy más automatizado.

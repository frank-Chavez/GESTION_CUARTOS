# Despliegue en Railway — mantener datos persistentes

Esta guía muestra los pasos concretos para desplegar esta aplicación en Railway y asegurarte de que los datos (SQLite) no se pierdan cuando el contenedor se reinicie o se redeploye.

Resumen rápido
- Si NO configuras almacenamiento persistente en Railway, el archivo SQLite se perderá cuando el contenedor sea recreado. NO uses el despliegue sin persistencia para producción.
- Para que NO se reinicien los datos: añade un volumen persistente en Railway y apunta `DATABASE_URL` a `/data/database.db`.

Pasos detallados

1) Preparar el repositorio

- Revisa que `requirements.txt` contenga todas las dependencias necesarias (ya incluye `Flask`, `Flask-WTF`, `WTForms`, `gunicorn`, `Werkzeug`).
- Revisa que `Procfile` exista con algo similar a:

```
web: gunicorn app:app -b 0.0.0.0:$PORT -w 2
```

2) Crear el proyecto en Railway y conectar GitHub

- Abre https://railway.app/ y entra con tu cuenta.
- Crea un proyecto nuevo → `Deploy from GitHub`.
- Autoriza Railway para acceder a tu cuenta de GitHub si es la primera vez.
- Selecciona el repositorio `frank-Chavez/GESTION_CUARTOS` y la rama `main`.

Railway detectará automáticamente que es un proyecto Python y usará `requirements.txt` y `Procfile`.

3) Añadir almacenamiento persistente (IMPORTANTE)

- En el panel del proyecto, ve a `Plugins` o `Add Plugin`.
- Añade `Persistent Storage` o `Volume` (nombre exacto puede variar según la UI de Railway).
- Mapea el volumen al directorio `/data` dentro del contenedor (opción que Railway suele ofrecer).

4) Configurar variables de entorno (Environment Variables)

- En el panel del proyecto ve a `Variables` (Environment) y añade:

  - `DATABASE_URL` = `/data/database.db`
  - `SECRET_KEY` = (genera una cadena segura, p. ej. `python -c "import secrets; print(secrets.token_hex(32))"`)
  - `SESSION_COOKIE_SECURE` = `1` (recomendado si usas HTTPS)
  - `PERMANENT_DAYS` = `30` (opcional)

Nota: `database.py` en este repo respeta `DATABASE_URL` y prefiere `/data/database.db` cuando existe, por eso con esto el archivo SQLite se guardará en el volumen persistente.

5) Despliegue y verificación

- Tras guardar las variables, Railway hará un build automático o puedes forzarlo con `Deploy` → `Redeploy`.
- Abre la URL pública que Railway proporciona y realiza algunas acciones (crear un inquilino, registrar pagos, etc.).

Verificar persistencia:

- Forzar un redeploy (desde la UI de Railway o haciendo un commit vacío y push):

  - Puedes forzar con un commit vacío:

    ```bash
    git commit --allow-empty -m "trigger redeploy"
    git push origin main
    ```

- Tras el redeploy, revisa la app: los datos que creaste deben seguir presentes.
- Si no aparecen, revisa los logs (Railway → Logs) para errores de escritura en `/data` o errores de path.

6) Alternativa (recomendada para producción): usar Postgres

- Para una solución más sólida en producción, añade el plugin PostgreSQL de Railway en `Plugins`.
- Cambia la configuración para usar Postgres. Opciones:
  - Añadir `SQLAlchemy` y configurar `SQLALCHEMY_DATABASE_URI` apuntando a la variable `DATABASE_URL` que Railway provee para Postgres.
  - O usar `psycopg2-binary` y reescribir `database.py` para conectar a Postgres.
- Ventajas: seguridad, backups, conexiones gestionadas y persistencia sin preocuparse por volúmenes.

7) Cosas a tener en cuenta

- Backups: incluso con volumen persistente, considera descargar periódicamente `database.db` o usar Postgres y su snapshot.
- Inicialización: la app ejecuta `script.sql` en el primer arranque si la DB está vacía — esto es correcto para crear tablas y un admin por defecto.
- HTTPS: Railway garantiza TLS en la URL pública; activa `SESSION_COOKIE_SECURE=1`.

Comandos útiles (localmente)

Generar `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Forzar un redeploy desde local:

```bash
git commit --allow-empty -m "trigger redeploy"
git push origin main
```

Comprobar logs en Railway: usa la sección `Logs` del proyecto.

Si quieres, puedo:

- A) Añadir este archivo `DEPLOY_RAILWAY.md` al repo (hecho ahora).
- B) Generar los valores recomendados (ej. `SECRET_KEY`) y dejarlo listo en el `README` para copiar/pegar.
- C) Ayudarte paso a paso mientras haces la configuración en la UI (me dices cuándo estás en cada pantalla y yo te guío).

No puedo interactuar directamente con tu cuenta de Railway por permisos, pero preparé todo lo necesario en el repo para que el proceso sea sólo seguir pasos y pegar variables en la UI.

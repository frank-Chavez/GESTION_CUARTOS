Prueba rápida: instalación PWA y acceso directo

Requisitos

- La app Flask debe estar corriendo localmente (por ejemplo en el puerto 5000).
- `ngrok` o equivalente para exponer HTTPS local (recomendado para pruebas en Android).

Pasos (ngrok)

1. Inicia tu app Flask localmente:

```cmd
C:\Users\Frank\Desktop\gestion_cuartos\venv\Scripts\python.exe app.py
```

(Ajusta el comando según cómo arrancas la app; el entorno virtual puede variar.)

2. Abre un terminal y ejecuta ngrok para exponer el puerto (suponiendo 5000):

```cmd
ngrok http 5000
```

3. Copia la URL pública que ngrok te muestra (https://xxxxx.ngrok.app) y ábrela en Chrome en tu Android.

4. En la aplicación web, ve a `Configuración` y activa el toggle `Acceso Directo`.

   - Si el navegador soporta `beforeinstallprompt`, se disparará el prompt nativo.
   - Si no, verás un modal con instrucciones manuales: "Añadir a pantalla de inicio".

5. Comprueba el icono en la pantalla de inicio de Android: debería usar `static/img/icon-192.png`.

Notas

- El acceso directo `.lnk` en el escritorio se crea en la máquina donde corre el servidor Flask (Windows). Si tu servidor no es la misma máquina, el `.lnk` aparecerá en el servidor, no en el móvil.
- Si el icono no cambia inmediatamente en Android, prueba a desinstalar la PWA y volver a instalar (el sistema puede cachear iconos).

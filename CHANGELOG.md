# Changelog

## [Unreleased]

- Integración PWA:
  - Generados iconos PNG `icon-192.png`, `icon-512.png` y `apple-touch-icon.png` desde `acceso_directo.ico`.
  - `static/manifest.json` actualizado para priorizar los PNG para Android.
  - `static/sw.js` actualizado para usar los PNG al servir recursos.
- Interfaz:
  - Toggle `Acceso Directo` en `Configuración` ahora dispara el flujo de instalación PWA en dispositivos compatibles y crea/elimina `.lnk` en Windows para escritorios.
  - Se añadió un modal de instrucciones para instalación/desinstalación en la página de configuración.
  - Se eliminó el botón `Instalar` del header; la instalación se gestiona desde el toggle en `Configuración`.
- Scripts:
  - `crear_shortcut_url.ps1` actualizado para aceptar parámetro `-IconPath` (si aplica).

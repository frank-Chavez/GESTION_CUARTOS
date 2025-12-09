# update_shortcut_icon.ps1
# Actualiza el icono de un acceso directo del Escritorio
param(
    [string]$ShortcutPath = "C:\\Users\\Frank\\Desktop\\sistema cuartos.lnk",
    [string]$IcoPath = "C:\\Users\\Frank\\Desktop\\gestion_cuartos\\static\\img\\acceso_directo.ico"
)

if (-not (Test-Path $ShortcutPath)) {
    Write-Error "Acceso directo no encontrado: $ShortcutPath"
    exit 1
}

if (-not (Test-Path $IcoPath)) {
    Write-Error "Icono no encontrado: $IcoPath"
    exit 1
}

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($ShortcutPath)
$sc.IconLocation = $IcoPath
$sc.Save()

Write-Output "Icono actualizado: $ShortcutPath -> $IcoPath"

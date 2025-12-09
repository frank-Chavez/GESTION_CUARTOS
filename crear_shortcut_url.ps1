# crear_shortcut_url.ps1
# Crea un acceso directo en el Escritorio que abre una URL en el navegador por defecto
# Uso:
# powershell -NoProfile -ExecutionPolicy Bypass -File "crear_shortcut_url.ps1" -Url "http://localhost:5000" -Name "sistema cuartos"

param(
    [Parameter(Mandatory=$true)]
    [string]$Url,

    [string]$Name = "sistema cuartos",
    [string]$IconPath
)

try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $link = Join-Path $desktop ($Name + ".lnk")

    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($link)
    $s.TargetPath = "C:\Windows\System32\cmd.exe"
    # Construimos los argumentos concatenando para evitar problemas de escape
    $s.Arguments = '/c start "" "' + $Url + '"'
    $s.WorkingDirectory = $env:USERPROFILE
    # Si se proporciona un IconPath válido, úsalo; si no, usar icono por defecto del sistema
    if ($IconPath) {
        try {
            if (Test-Path $IconPath) {
                # WScript.Shortcut acepta IconLocation como 'ruta,indice' o ruta a .ico
                $s.IconLocation = $IconPath
            } else {
                Write-Output "Icono no encontrado en: $IconPath - usando icono por defecto"
                $s.IconLocation = "C:\\Windows\\System32\\shell32.dll,1"
            }
        } catch {
            $s.IconLocation = "C:\\Windows\\System32\\shell32.dll,1"
        }
    } else {
        $s.IconLocation = "C:\\Windows\\System32\\shell32.dll,1"
    }
    $s.Save()

    Write-Output "Acceso directo creado: $link"
}
catch {
    Write-Error "No se pudo crear el acceso directo: $_"
    exit 1
}

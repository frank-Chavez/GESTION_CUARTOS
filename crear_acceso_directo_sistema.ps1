# Script: crear_acceso_directo_sistema.ps1
# Crea un acceso directo en el Escritorio que ejecuta acciones del sistema
# Uso:
# powershell -NoProfile -ExecutionPolicy Bypass -File "crear_acceso_directo_sistema.ps1" -Action Lock -Name "Bloquear equipo"

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Lock","Logoff","SwitchUser","Sleep")]
    [string]$Action,

    [string]$Name = "AccesoDirectoSistema"
)

try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop ($Name + ".lnk")

    switch ($Action) {
        "Lock" {
            $target = Join-Path $env:windir "system32\rundll32.exe"
            $arguments = "user32.dll,LockWorkStation"
        }
        "Logoff" {
            $target = Join-Path $env:windir "system32\shutdown.exe"
            $arguments = "/l"
        }
        "SwitchUser" {
            $target = Join-Path $env:windir "system32\tsdiscon.exe"
            $arguments = ""
        }
        "Sleep" {
            # Pone el equipo en suspensión (puede requerir privilegios)
            $target = Join-Path $env:windir "system32\rundll32.exe"
            $arguments = "powrprof.dll,SetSuspendState 0,1,0"
        }
    }

    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($shortcutPath)
    $sc.TargetPath = $target
    if ($arguments) { $sc.Arguments = $arguments }
    $sc.WorkingDirectory = Split-Path $target -Parent
    $sc.IconLocation = "$target,0"
    $sc.Save()

    Write-Output "Acceso directo creado: $shortcutPath (Acción: $Action)"
}
catch {
    Write-Error "No se pudo crear el acceso directo: $_"
    exit 1
}

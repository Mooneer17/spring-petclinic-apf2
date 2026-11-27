# APF3 - Prueba movil. Ejecuta, en orden, cada linea de accion.txt y registra todo en logs\ejecucion.txt.
# Acciones: app | emulador <avd> | boot | info | http <url> | url <url> | tap <x> <y> | swipe <x1> <y1> <x2> <y2> [ms]
#           texto <texto> | tecla <keycode> | captura <id> | rotar <0|1> | esperar <seg> | python
#           medir <vertical|horizontal> <registro|sin> <nombre del dispositivo> | adb <argumentos>
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
$java = 'C:\Users\pc\Desktop\APF2_Defensa\paquete\APF2_Entregable\.runtime\jdk\jdk-21.0.13+9\bin\java.exe'
$py = 'C:\Users\pc\AppData\Local\Programs\Python\Python314\python.exe'
$sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'Android\Sdk' }
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$emu = Join-Path $sdk 'emulator\emulator.exe'
New-Item -ItemType Directory -Force 'logs', 'evidencias\capturas' | Out-Null
$marca = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = "logs\ejecucion_$marca.txt"


function Log([string]$t) { Add-Content -Encoding UTF8 $log ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $t) }
function Adb([string[]]$a) { $o = & $adb @a 2>&1 | ForEach-Object { "$_" } | Out-String; if ($o.Trim()) { Add-Content -Encoding UTF8 $log $o.TrimEnd() }; return $o }

foreach ($linea in Get-Content -Encoding UTF8 'accion.txt') {
    $linea = $linea.Trim()
    if (-not $linea -or $linea.StartsWith('#')) { continue }
    $partes = $linea -split '\s+', 2
    $acc = $partes[0]
    $arg = if ($partes.Count -gt 1) { $partes[1] } else { '' }
    Log "> $linea"
    try {
        switch ($acc) {
            'app' { Start-Process cmd.exe -ArgumentList '/k', "`"$java`" -jar petclinic-corregida.jar --server.port=8080" -WorkingDirectory $PSScriptRoot; Log 'app iniciada en otra ventana' }
            'emulador' { Start-Process $emu -ArgumentList '-avd', $arg; Log "emulador iniciado: $arg" }
            'boot' {
                Adb @('wait-for-device') | Out-Null
                $t0 = Get-Date
                while (((& $adb shell getprop sys.boot_completed) -join '').Trim() -ne '1' -and ((Get-Date) - $t0).TotalSeconds -lt 240) { Start-Sleep 3 }
                Log ("boot_completed={0} tras {1:N0} s" -f ((& $adb shell getprop sys.boot_completed) -join '').Trim(), ((Get-Date) - $t0).TotalSeconds)
            }
            'info' {
                $p = { param($k) ((& $adb shell getprop $k) -join '').Trim() }
                $chrome = (& $adb shell 'dumpsys package com.android.chrome | grep versionName') -join ' '
                $lineas = @(
                    "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
                    'Tipo: emulador de Android Studio (AVD)',
                    "AVD: $(((& $adb emu avd name) | Select-Object -First 1))",
                    "Fabricante: $(& $p 'ro.product.manufacturer')",
                    "Modelo: $(& $p 'ro.product.model')",
                    "Android: $(& $p 'ro.build.version.release') (API $(& $p 'ro.build.version.sdk'))",
                    "Chrome: $($chrome.Trim())",
                    "Pantalla: $(((& $adb shell wm size) -join ' ').Trim())",
                    "Densidad: $(((& $adb shell wm density) -join ' ').Trim())",
                    "PC: $env:COMPUTERNAME, $((Get-CimInstance Win32_OperatingSystem).Caption)"
                )
                $lineas | Set-Content -Encoding UTF8 'evidencias\info_dispositivo.txt'
                $lineas | ForEach-Object { Log $_ }
            }
            'http' { try { $r = Invoke-WebRequest -UseBasicParsing -Uri $arg -TimeoutSec 15; Log "HTTP $($r.StatusCode) $arg" } catch { Log "HTTP error $arg : $($_.Exception.Message)" } }
            'url' { Adb @('shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', $arg, 'com.android.chrome') | Out-Null }
            'tap' { $xy = $arg -split '\s+'; Adb (@('shell', 'input', 'tap') + $xy) | Out-Null }
            'swipe' { $v = $arg -split '\s+'; Adb (@('shell', 'input', 'swipe') + $v) | Out-Null }
            'texto' { Adb @('shell', 'input', 'text', ($arg -replace ' ', '%s')) | Out-Null }
            'tecla' { Adb @('shell', 'input', 'keyevent', $arg) | Out-Null }
            'captura' {
                Adb @('shell', 'screencap', '-p', '/sdcard/apf3_captura.png') | Out-Null
                Adb @('pull', '/sdcard/apf3_captura.png', "evidencias\capturas\$arg.png") | Out-Null
                Adb @('shell', 'rm', '/sdcard/apf3_captura.png') | Out-Null
            }
            'rotar' { Adb @('shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0') | Out-Null; Adb @('shell', 'settings', 'put', 'system', 'user_rotation', $arg) | Out-Null }
            'esperar' { Start-Sleep -Seconds ([int]$arg) }
            'python' {
                if (-not (Test-Path '.venv')) { & $py -m venv .venv 2>&1 | Out-File -Append -Encoding utf8 $log }
                & '.venv\Scripts\python.exe' -m pip install --disable-pip-version-check playwright 2>&1 | Out-File -Append -Encoding utf8 $log
            }
            'medir' {
                $v = $arg -split '\s+', 3
                Adb @('forward', 'tcp:9222', 'localabstract:chrome_devtools_remote') | Out-Null
                $extra = @(); if ($v[1] -eq 'registro') { $extra = @('--registro') }
                & '.venv\Scripts\python.exe' movil_cdp.py --base http://10.0.2.2:8080 --dispositivo $v[2] --orientacion $v[0] --out "evidencias\medicion_$($v[0])" @extra 2>&1 | Out-File -Append -Encoding utf8 $log
            }
            'adb' { Adb ($arg -split '\s+') | Out-Null }
            default { Log "accion desconocida: $acc" }
        }
    } catch { Log "ERROR en '$linea': $($_.Exception.Message)" }
}
Log 'FIN'
Set-Content -Encoding UTF8 "logs\fin_$marca.txt" 'FIN'

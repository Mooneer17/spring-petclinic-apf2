# APF3 - Preparación y apoyo para la prueba de compatibilidad móvil (sección 14.2, CO-M01 a CO-M04).
# Uso desde la raíz del repositorio o desde esta carpeta:
#   .\apf3\movil\movil.ps1 -Accion app              # compila y levanta la versión corregida en el puerto 8080 (H2)
#   .\apf3\movil\movil.ps1 -Accion ip               # muestra la IP de la PC y la URL para el celular real
#   .\apf3\movil\movil.ps1 -Accion firewall         # (como administrador) permite el puerto 8080 en redes privadas
#   .\apf3\movil\movil.ps1 -Accion dispositivos     # lista emuladores y celulares conectados por adb
#   .\apf3\movil\movil.ps1 -Accion info -Nombre M1  # guarda modelo, Android, Chrome y pantalla del dispositivo
#   .\apf3\movil\movil.ps1 -Accion rotar -Orientacion horizontal
#   .\apf3\movil\movil.ps1 -Accion captura -Nombre M1 -Id CO-M01_inicio_vertical
#   .\apf3\movil\movil.ps1 -Accion medir -Nombre M1 -Base http://10.0.2.2:8080 -Dispositivo "AVD Pixel 7 API 35" -Orientacion vertical
#   .\apf3\movil\movil.ps1 -Accion quitar-firewall  # (como administrador) elimina la regla creada
# Todo lo que se genera queda en apf3\ev\12_movil\<Nombre>\.
param(
    [ValidateSet('app','ip','firewall','quitar-firewall','dispositivos','info','rotar','captura','medir')]
    [string]$Accion = 'dispositivos',
    [string]$Nombre = 'M1',
    [string]$Id = '',
    [string]$Base = 'http://10.0.2.2:8080',
    [string]$Dispositivo = '',
    [ValidateSet('vertical','horizontal')]
    [string]$Orientacion = 'vertical',
    [string]$Serial = '',
    [int]$Puerto = 8080,
    [switch]$Registro
)
$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$salida = Join-Path $raiz "apf3\ev\12_movil\$Nombre"
$reglaFirewall = "Petclinic APF3 puerto $Puerto"

function Get-Adb {
    $candidatos = @()
    if ($env:ANDROID_HOME) { $candidatos += (Join-Path $env:ANDROID_HOME 'platform-tools\adb.exe') }
    if ($env:ANDROID_SDK_ROOT) { $candidatos += (Join-Path $env:ANDROID_SDK_ROOT 'platform-tools\adb.exe') }
    if ($env:LOCALAPPDATA) { $candidatos += (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe') }
    foreach ($c in $candidatos) { if (Test-Path -LiteralPath $c) { return $c } }
    $enPath = Get-Command adb -ErrorAction SilentlyContinue
    if ($enPath) { return $enPath.Source }
    throw 'No se encontró adb. Instala "Android SDK Platform-Tools" desde Android Studio (SDK Manager > SDK Tools).'
}

function Invoke-Adb {
    param([string[]]$Argumentos)
    $adb = Get-Adb
    if ($Serial) { $Argumentos = @('-s', $Serial) + $Argumentos }
    & $adb @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "adb terminó con código $LASTEXITCODE ($($Argumentos -join ' '))" }
}

function Get-AdbSalida {
    param([string[]]$Argumentos)
    $adb = Get-Adb
    if ($Serial) { $Argumentos = @('-s', $Serial) + $Argumentos }
    return (& $adb @Argumentos | Out-String).Trim()
}

function New-Salida { New-Item -ItemType Directory -Force $salida | Out-Null; New-Item -ItemType Directory -Force (Join-Path $salida 'capturas') | Out-Null }

switch ($Accion) {
    'app' {
        # La versión corregida se compila en una copia aparte (git worktree) para no cambiar la rama actual.
        $copia = Join-Path $raiz '.runtime\correcciones-apf3'
        Push-Location $raiz
        try {
            git fetch origin correcciones-apf3
            if (-not (Test-Path -LiteralPath $copia)) { git worktree add --detach $copia origin/correcciones-apf3 }
            else { git -C $copia checkout --detach origin/correcciones-apf3 }
        } finally { Pop-Location }
        $jdk = Get-ChildItem -LiteralPath (Join-Path $raiz '.runtime\jdk') -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName 'bin\java.exe') } | Select-Object -First 1
        if ($jdk) { $env:JAVA_HOME = $jdk.FullName; $env:Path = (Join-Path $jdk.FullName 'bin') + ';' + $env:Path }
        elseif (-not (Get-Command java -ErrorAction SilentlyContinue)) {
            throw 'No hay JDK. Ejecuta primero: .\herramientas\ejecutar_apf2.ps1 -Accion preparar'
        }
        $env:MAVEN_OPTS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NUL'
        Push-Location (Join-Path $copia 'proyecto')
        try {
            .\mvnw.cmd -q -DskipTests package
            if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación.' }
            $jar = Get-ChildItem target\spring-petclinic-*.jar | Select-Object -First 1
            Write-Host "Versión corregida: $(git -C $copia rev-parse --short HEAD). Abriendo en el puerto $Puerto (H2, datos de ejemplo)."
            Write-Host "Emulador: http://10.0.2.2:$Puerto   Celular real: ver -Accion ip   Detener: Ctrl+C"
            & java -jar $jar.FullName --server.port=$Puerto --server.address=0.0.0.0
        } finally { Pop-Location }
    }
    'ip' {
        $ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' }
        foreach ($i in $ips) { Write-Host ("{0,-28} http://{1}:{2}" -f $i.InterfaceAlias, $i.IPAddress, $Puerto) }
        Write-Host 'El celular debe estar en la misma red Wi-Fi. Usa la IP de la interfaz Wi-Fi o Ethernet de la PC.'
    }
    'firewall' {
        New-NetFirewallRule -DisplayName $reglaFirewall -Direction Inbound -Protocol TCP -LocalPort $Puerto -Action Allow -Profile Private | Out-Null
        Write-Host "Regla creada: $reglaFirewall (solo redes privadas). Al terminar: -Accion quitar-firewall"
    }
    'quitar-firewall' {
        Remove-NetFirewallRule -DisplayName $reglaFirewall
        Write-Host "Regla eliminada: $reglaFirewall"
    }
    'dispositivos' { Invoke-Adb @('devices', '-l') }
    'info' {
        New-Salida
        $prop = { param($k) Get-AdbSalida @('shell', 'getprop', $k) }
        $chrome = (Get-AdbSalida @('shell', 'dumpsys', 'package', 'com.android.chrome')) -split "`n" |
            Where-Object { $_ -match 'versionName=' } | Select-Object -First 1
        $lineas = @(
            "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
            "Nombre en el registro: $Nombre",
            "Fabricante: $(& $prop 'ro.product.manufacturer')",
            "Modelo: $(& $prop 'ro.product.model')",
            "Emulador (ro.kernel.qemu=1): $(& $prop 'ro.kernel.qemu')",
            "Android: $(& $prop 'ro.build.version.release') (API $(& $prop 'ro.build.version.sdk'))",
            "Chrome: $(if ($chrome) { $chrome.Trim() } else { 'no encontrado' })",
            "Pantalla: $(Get-AdbSalida @('shell', 'wm', 'size'))",
            "Densidad: $(Get-AdbSalida @('shell', 'wm', 'density'))"
        )
        $lineas | Set-Content -Encoding UTF8 (Join-Path $salida 'info_dispositivo.txt')
        $lineas | ForEach-Object { Write-Host $_ }
    }
    'rotar' {
        # Fija la orientación (útil en el emulador). 0 = vertical, 1 = horizontal.
        Invoke-Adb @('shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')
        Invoke-Adb @('shell', 'settings', 'put', 'system', 'user_rotation', $(if ($Orientacion -eq 'horizontal') { '1' } else { '0' }))
        Write-Host "Orientación fijada: $Orientacion"
    }
    'captura' {
        if (-not $Id) { throw 'Indica -Id, por ejemplo CO-M01_inicio_vertical' }
        New-Salida
        $remoto = "/sdcard/$Id.png"
        Invoke-Adb @('shell', 'screencap', '-p', $remoto)
        Invoke-Adb @('pull', $remoto, (Join-Path $salida "capturas\$Id.png"))
        Invoke-Adb @('shell', 'rm', $remoto)
        Write-Host "Captura guardada: $(Join-Path $salida "capturas\$Id.png")"
    }
    'medir' {
        if (-not $Dispositivo) { throw 'Indica -Dispositivo, por ejemplo "AVD Pixel 7 API 35" o "Moto G54 (real)"' }
        Invoke-Adb @('forward', 'tcp:9222', 'localabstract:chrome_devtools_remote')
        $destino = Join-Path $salida "medicion_$Orientacion"
        $argumentos = @((Join-Path $PSScriptRoot 'movil_cdp.py'), '--base', $Base, '--dispositivo', $Dispositivo, '--orientacion', $Orientacion, '--out', $destino)
        if ($Registro) { $argumentos += '--registro' }
        py @argumentos
        if ($LASTEXITCODE -ne 0) { throw 'La medición terminó con error. Revisa que Chrome esté abierto en el dispositivo.' }
        Write-Host "Resultados en $destino"
    }
}

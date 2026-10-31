# APF2 - Medicion del tiempo de arranque de Petclinic con MySQL (evaluacion complementaria)
# Uso (desde APF2_Programa):
#   powershell -NoProfile -ExecutionPolicy Bypass -File herramientas\medir_arranque.ps1 [-Repeticiones 3] [-Usuario root]
# - NO detiene la aplicacion que ya esta corriendo: inicia una instancia aparte en un puerto libre (8090-8099)
#   y al terminar cierra solo esa instancia.
# - Mide dos cosas: el tiempo que informa Spring Boot ("Started ... in X seconds") y el tiempo hasta la
#   primera respuesta HTTP 200 en "/", medido por este script.
# - Usa el JAR ya compilado. Si no existe, lo compila antes y reporta ese tiempo por separado
#   (la compilacion no forma parte del arranque).
# - La contrasena de MySQL se pide oculta y no se guarda.
param([int]$Repeticiones = 1, [string]$Usuario = 'petclinic', [string]$Url = 'jdbc:mysql://localhost:3306/petclinic')

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$RtDefensa = Join-Path $HOME 'Desktop\APF2_Defensa\paquete\APF2_Entregable\.runtime'
$M2 = Join-Path $RtDefensa 'm2'
$Build = Join-Path $Raiz '.runtime\demo_build'

# --- Java ---
$java = $null
foreach ($c in @($env:JAVA_HOME, 'C:\Program Files\Android\Android Studio\jbr')) {
    if ($c -and (Test-Path (Join-Path $c 'bin\java.exe'))) { $java = Join-Path $c 'bin\java.exe'; break }
}
if (-not $java) {
    $t = Get-ChildItem (Join-Path $RtDefensa 'jdk') -Directory -ErrorAction SilentlyContinue |
         Where-Object { Test-Path (Join-Path $_.FullName 'bin\java.exe') } | Select-Object -First 1
    if ($t) { $java = Join-Path $t.FullName 'bin\java.exe' }
}
if (-not $java) { throw 'No se encontro Java (JAVA_HOME, JBR de Android Studio o JDK portatil de APF2_Defensa).' }

# --- JAR ---
function Buscar-Jar {
    foreach ($d in @((Join-Path $Raiz 'proyecto\target'), (Join-Path $Build 'target'))) {
        $j = Get-ChildItem $d -Filter 'spring-petclinic-*.jar' -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -notlike '*plain*' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($j) { return $j.FullName }
    }
    return $null
}
$jar = Buscar-Jar
$compilacion = 'no fue necesaria (JAR existente)'
if (-not $jar) {
    Write-Host 'No hay JAR compilado. Compilando una copia aislada (necesita internet la primera vez)...' -ForegroundColor Yellow
    New-Item -ItemType Directory -Force $Build | Out-Null
    robocopy (Join-Path $Raiz 'proyecto') $Build /E /XD target .git /NFL /NDL /NJH /NJS /NP | Out-Null
    $env:MAVEN_USER_HOME = Join-Path $RtDefensa 'maven-home'
    $swB = [Diagnostics.Stopwatch]::StartNew()
    Push-Location $Build
    try { & .\mvnw.cmd -B -q "-Dmaven.repo.local=$M2" -DskipTests package | Out-Null } finally { Pop-Location }
    $swB.Stop()
    $jar = Buscar-Jar
    if (-not $jar) { throw 'La compilacion no produjo el JAR.' }
    $compilacion = ('{0:N1} s (Maven package; NO forma parte del arranque)' -f $swB.Elapsed.TotalSeconds)
}

# --- puerto libre ---
function Puerto-Libre {
    foreach ($p in 8090..8099) {
        $c = New-Object System.Net.Sockets.TcpClient
        try { $r = $c.BeginConnect('localhost', $p, $null, $null); $ocupado = $r.AsyncWaitHandle.WaitOne(300) -and $c.Connected }
        catch { $ocupado = $false } finally { $c.Close() }
        if (-not $ocupado) { return $p }
    }
    throw 'No hay puertos libres entre 8090 y 8099.'
}

$s = Read-Host "Contrasena de MySQL para el usuario '$Usuario' (no se guarda)" -AsSecureString
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
$clave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b); [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)

$ev = Join-Path $Raiz ('nuevas_evidencias\' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '_arranque_MySQL')
New-Item -ItemType Directory -Force $ev | Out-Null
$filas = @()

for ($i = 1; $i -le $Repeticiones; $i++) {
    $port = Puerto-Libre
    $log = Join-Path $ev ("arranque_$i.log"); $err = Join-Path $ev ("arranque_${i}_stderr.log")
    $env:MYSQL_URL = $Url; $env:MYSQL_USER = $Usuario; $env:MYSQL_PASS = $clave
    Write-Host "Arranque $i de $Repeticiones en el puerto $port ..." -ForegroundColor Cyan
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $proc = Start-Process -FilePath $java -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err `
        -ArgumentList @('-jar', "`"$jar`"", '--spring.profiles.active=mysql', "--server.port=$port", '--spring.docker.compose.enabled=false')
    'MYSQL_URL', 'MYSQL_USER', 'MYSQL_PASS' | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
    $http = $null
    try {
        while ($sw.Elapsed.TotalSeconds -lt 180) {
            if ($proc.HasExited) { break }
            try {
                $r = Invoke-WebRequest "http://localhost:$port/" -UseBasicParsing -TimeoutSec 2
                if ($r.StatusCode -eq 200) { $http = $sw.Elapsed.TotalSeconds; break }
            } catch { }
            Start-Sleep -Milliseconds 250
        }
    } finally {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }   # cierra SOLO la instancia de esta medicion
    }
    Start-Sleep -Milliseconds 500
    $txt = if (Test-Path $log) { Get-Content $log -Raw } else { '' }
    $m = [regex]::Match($txt, 'Started PetClinicApplication in ([0-9.]+) seconds \(process running for ([0-9.]+)\)')
    $jdbcUrl = [regex]::Match($txt, 'Database JDBC URL \[([^\]]+)\]').Groups[1].Value
    $ver = [regex]::Match($txt, 'Database version: ([0-9.]+)').Groups[1].Value
    $esMysql = $jdbcUrl -like 'jdbc:mysql:*'
    $fila = [pscustomobject]@{
        Corrida = $i; Puerto = $port
        Spring_Started_s = if ($m.Success) { $m.Groups[1].Value } else { 'no encontrado' }
        Proceso_s = if ($m.Success) { $m.Groups[2].Value } else { 'no encontrado' }
        Primera_respuesta_HTTP_200_s = if ($http) { '{0:N2}' -f $http } else { 'sin respuesta' }
        Base = if ($esMysql) { "MySQL $ver ($jdbcUrl)" } else { 'NO se confirmo MySQL' }
    }
    $filas += $fila
    $fila | Format-List
    if ($txt -match 'Access denied') {
        Write-Host "MySQL rechazo el usuario '$Usuario' o su contrasena (Access denied). No se hacen mas intentos." -ForegroundColor Yellow
        Write-Host 'Usa las mismas credenciales con las que levantaste la app del puerto 8081 (opcion -Usuario).' -ForegroundColor Yellow
        break
    }
    if ($txt -match 'Communications link failure') { Write-Host 'No hay conexion con MySQL en localhost:3306.' -ForegroundColor Yellow; break }
}

$res = @(
    'Medicion de arranque de Spring Petclinic (evaluacion complementaria)',
    "Fecha: $(Get-Date -Format s)   Equipo: $env:COMPUTERNAME",
    "JAR: $jar",
    "Usuario MySQL: $Usuario   URL: $Url",
    "Java: $java",
    "Compilacion previa: $compilacion",
    '',
    ($filas | Format-Table -AutoSize | Out-String).Trim(),
    '',
    'Spring_Started_s: tiempo informado por Spring Boot. Proceso_s: desde el inicio del proceso Java.',
    'Primera_respuesta_HTTP_200_s: medido por este script desde el lanzamiento hasta el primer 200 en "/".',
    'Son observaciones puntuales de este equipo; no hay criterio de aceptacion definido.'
)
$res | Set-Content (Join-Path $ev 'resultado.txt') -Encoding UTF8
Write-Host ''; $res | ForEach-Object { Write-Host $_ }
Write-Host "Evidencia guardada en: $ev" -ForegroundColor Green

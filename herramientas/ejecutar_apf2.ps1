# APF2 - ejecucion en Windows. Extiende herramientas/ejecutar.ps1 (JDK portatil verificado por SHA256,
# almacen Windows-ROOT solo para el proceso). Las acciones HTTP requieren Python 3.10+ con:
#   py -m pip install requests locust playwright ; py -m playwright install chromium
# MySQL 8 local con la base y el usuario de proyecto/src/main/resources/db/mysql/user.sql.
param(
    [ValidateSet('preparar','casos','casos-mysql','suite','app','funcionales','seguridad','e01','rendimiento','navegador')]
    [string]$Accion = 'preparar',
    [string]$Base = 'http://localhost:8080'
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $raiz '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$marca = Get-Date -Format 'yyyyMMdd-HHmmss'
$salida = Join-Path $raiz ("nuevas_evidencias/" + $marca)
New-Item -ItemType Directory -Force $salida | Out-Null
$scripts = Join-Path $raiz 'scripts'

if ($Accion -in @('funcionales','seguridad','e01','rendimiento','navegador')) {
    switch ($Accion) {
        'funcionales' { py "$scripts/funcionales_http.py" --base $Base --out "$salida/funcionales" --bd MySQL }
        'seguridad'   { py "$scripts/seguridad_http.py" --base $Base --out "$salida/seguridad" --bd MySQL }
        'e01'         { py "$scripts/exploratorio_duplicado_concurrente.py" --base $Base --out "$salida/e01" --bd MySQL --owners 20 }
        'navegador'   { py "$scripts/navegador_flujos.py" --base $Base --out "$salida/navegador" }
        'rendimiento' {
            New-Item -ItemType Directory -Force "$salida/rendimiento" | Out-Null
            py -m locust -f "$scripts/locustfile.py" --headless -H $Base -u 10 -r 2 -t 60s --only-summary --csv "$salida/rendimiento/calentamiento" *> "$salida/rendimiento/calentamiento.log"
            py -m locust -f "$scripts/locustfile.py" --headless -H $Base -u 10 -r 2 -t 180s --only-summary --csv "$salida/rendimiento/carga10" --html "$salida/rendimiento/carga10.html" *> "$salida/rendimiento/carga10.log"
            py -m locust -f "$scripts/locustfile.py" --headless -H $Base -u 30 -r 3 -t 180s --only-summary --csv "$salida/rendimiento/carga30" --html "$salida/rendimiento/carga30.html" *> "$salida/rendimiento/carga30.log"
        }
    }
    Write-Host "Salida en $salida"
    return
}

# --- Acciones Java: JDK portatil (misma logica que ejecutar.ps1) ---
$jdkConfig = Get-Content -Raw (Join-Path $PSScriptRoot 'jdk-source.json') | ConvertFrom-Json
$rutaJdkBase = Join-Path $runtime 'jdk'
$jdk = Get-ChildItem -LiteralPath $rutaJdkBase -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'bin/java.exe') } | Select-Object -First 1
if (-not $jdk) {
    $zip = Join-Path $runtime $jdkConfig.name
    if (-not (Test-Path -LiteralPath $zip)) { Invoke-WebRequest -Uri $jdkConfig.link -OutFile $zip }
    if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower() -ne $jdkConfig.checksum.ToLower()) { throw 'El checksum del JDK no coincide.' }
    Expand-Archive -LiteralPath $zip -DestinationPath $rutaJdkBase -Force
    $jdk = Get-ChildItem -LiteralPath $rutaJdkBase -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'bin/java.exe') } | Select-Object -First 1
}
$prev = @{ JAVA_HOME = $env:JAVA_HOME; Path = $env:Path; MAVEN_USER_HOME = $env:MAVEN_USER_HOME; MAVEN_OPTS = $env:MAVEN_OPTS }
try {
    $env:JAVA_HOME = $jdk.FullName
    $env:Path = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:Path
    $env:MAVEN_USER_HOME = Join-Path $runtime 'maven-home'
    $env:MAVEN_OPTS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NUL'
    if ($Accion -eq 'preparar') { & java -version; return }
    $repo = Join-Path $runtime 'm2'
    $tests = 'AvanceUnitTests,AvanceIntegrationTests,DiagnosticoFixtureTests'
    $mysql = @('-Ddatabase=mysql', '-Dspring.datasource.url=jdbc:mysql://localhost:3306/petclinic',
               '-Dspring.datasource.username=petclinic', '-Dspring.datasource.password=petclinic', '-Dspring.sql.init.mode=always')
    $args_ = @('-B', "-Dmaven.repo.local=$repo")
    switch ($Accion) {
        'casos'       { $args_ += @("-Dtest=$tests", '-Dsurefire.failIfNoSpecifiedTests=false', 'test') }
        'casos-mysql' { $args_ += @("-Dtest=$tests", '-Dsurefire.failIfNoSpecifiedTests=false') + $mysql + @('test') }
        'suite'       { $args_ += @('test') }
        'app'         { $args_ += @('spring-boot:run', '-Dspring-boot.run.profiles=mysql', '-Dspring-boot.run.arguments=--spring.docker.compose.enabled=false') }
    }
    Push-Location (Join-Path $raiz 'proyecto')
    try {
        & './mvnw.cmd' @args_ 2>&1 | Tee-Object -FilePath (Join-Path $salida "$Accion.log")
        $rep = 'target/surefire-reports'
        if ($Accion -ne 'app' -and (Test-Path $rep)) { Copy-Item $rep (Join-Path $salida "$Accion-reportes") -Recurse }
    } finally { Pop-Location }
} finally {
    foreach ($k in $prev.Keys) {
        if ($null -eq $prev[$k]) { Remove-Item -Path "env:$k" -ErrorAction SilentlyContinue } else { Set-Item -Path "env:$k" -Value $prev[$k] }
    }
}
Write-Host "Salida en $salida"

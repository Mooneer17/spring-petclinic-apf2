# APF2 - Spring Petclinic (commit 500158f): preparar Java, ejecutar pruebas y levantar la aplicacion con H2.
# Uso (desde VS Code: Terminal > Run Task):
#   powershell -ExecutionPolicy Bypass -File .\apf2.ps1 -Accion preparar
#   powershell -ExecutionPolicy Bypass -File .\apf2.ps1 -Accion pruebas      (CP01-CP06 y DIAG01)
#   powershell -ExecutionPolicy Bypass -File .\apf2.ps1 -Accion app          (http://localhost:8080)
#   powershell -ExecutionPolicy Bypass -File .\apf2.ps1 -Accion funcionales  (F01-F31; app levantada y Python)
param(
    [ValidateSet('preparar', 'pruebas', 'app', 'funcionales')]
    [string]$Accion = 'app'
)
$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
$proyecto = Join-Path $raiz 'proyecto'
$runtime = Join-Path $raiz '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
# Runtime ya descargado en APF2_Defensa (se reutiliza para no descargar de nuevo)
$runtimePrevio = Join-Path $HOME 'Desktop\APF2_Defensa\paquete\APF2_Entregable\.runtime'

function Find-Jdk([string]$dir) {
    Get-ChildItem (Join-Path $dir 'jdk') -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'bin\java.exe') } | Select-Object -First 1
}

Write-Host '[Java] Preparando JDK portatil Temurin 21...'
$jdk = Find-Jdk $runtime
if (-not $jdk) { $jdk = Find-Jdk $runtimePrevio; if ($jdk) { Write-Host '       Se reutiliza el JDK de APF2_Defensa.' } }
if (-not $jdk) {
    $cfg = Get-Content -Raw (Join-Path $raiz 'herramientas\jdk-source.json') | ConvertFrom-Json
    $zip = Join-Path $runtime $cfg.name
    if (-not (Test-Path $zip)) {
        Write-Host '       Descargando JDK (unos 200 MB, solo la primera vez)...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $cfg.link -OutFile $zip
    }
    if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $cfg.checksum.ToLower()) {
        throw 'El checksum del JDK no coincide. No se usara el archivo descargado.'
    }
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $runtime 'jdk') -Force
    $jdk = Find-Jdk $runtime
}
$env:JAVA_HOME = $jdk.FullName
$env:Path = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:Path
$env:MAVEN_USER_HOME = Join-Path $runtime 'maven-home'
$env:MAVEN_OPTS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NUL'
$m2 = Join-Path $runtime 'm2'
if (-not (Test-Path $m2) -and (Test-Path (Join-Path $runtimePrevio 'm2'))) { $m2 = Join-Path $runtimePrevio 'm2' }
Write-Host "       Java: $env:JAVA_HOME"
$ErrorActionPreference = 'Continue'
& java -version 2>&1 | ForEach-Object { Write-Host "       $_" }
if ($Accion -eq 'preparar') { Write-Host 'Preparacion completa.'; return }

$ev = Join-Path $raiz ('nuevas_evidencias\' + (Get-Date -Format 'yyyyMMdd-HHmm') + '_PC_Windows_H2')

switch ($Accion) {
    'pruebas' {
        New-Item -ItemType Directory -Force $ev | Out-Null
        Set-Location $proyecto
        Write-Host '[Pruebas] CP01-CP06 y DIAG01 con H2 (la primera vez Maven descarga dependencias)...'
        & .\mvnw.cmd -B "-Dmaven.repo.local=$m2" test "-Dtest=AvanceUnitTests,AvanceIntegrationTests,DiagnosticoFixtureTests" "-Dsurefire.failIfNoSpecifiedTests=false" 2>&1 |
            Tee-Object (Join-Path $ev '01_casos_H2.log')
        if (Test-Path 'target\surefire-reports') { Copy-Item 'target\surefire-reports' (Join-Path $ev '01_casos_H2_reportes') -Recurse }
        Write-Host ''
        Write-Host "Evidencias guardadas en: $ev"
    }
    'app' {
        Set-Location $proyecto
        Write-Host '[App] Iniciando Spring Petclinic con H2. Cuando aparezca "Started PetClinicApplication", abrir http://localhost:8080'
        Write-Host '      Para detener: icono de papelera de este terminal o Ctrl+C.'
        & .\mvnw.cmd -B "-Dmaven.repo.local=$m2" spring-boot:run "-Dspring-boot.run.arguments=--spring.docker.compose.enabled=false"
    }
    'funcionales' {
        $py = Get-Command python -ErrorAction SilentlyContinue
        if (-not $py) { Write-Host 'No se encontro Python. Instale Python 3.10+ para esta accion.'; return }
        $venv = Join-Path $runtime 'venv'
        if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { & python -m venv $venv }
        $vpy = Join-Path $venv 'Scripts\python.exe'
        & $vpy -m pip install --quiet requests
        New-Item -ItemType Directory -Force $ev | Out-Null
        Set-Location (Join-Path $raiz 'scripts')
        & $vpy funcionales_http.py --base http://localhost:8080 --out (Join-Path $ev '03_funcionales_H2') --bd 'H2 (PC Windows)'
        & $vpy seguridad_http.py --base http://localhost:8080 --out (Join-Path $ev '04_seguridad_H2') --bd 'H2 (PC Windows)'
        Write-Host "Evidencias guardadas en: $ev"
    }
}

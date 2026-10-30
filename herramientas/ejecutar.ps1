param(
    [ValidateSet('preparar','casos','originales','iniciar')]
    [string]$Accion = 'preparar'
)
$ErrorActionPreference = 'Stop'
$raizPaquete = Split-Path -Parent $PSScriptRoot
$rutaRuntime = Join-Path $raizPaquete '.runtime'
New-Item -ItemType Directory -Force $rutaRuntime | Out-Null
$jdkConfig = Get-Content -Raw (Join-Path $PSScriptRoot 'jdk-source.json') | ConvertFrom-Json
$rutaJdkBase = Join-Path $rutaRuntime 'jdk'
$jdkLocal = Get-ChildItem -LiteralPath $rutaJdkBase -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'bin/java.exe') } | Select-Object -First 1
if (-not $jdkLocal) {
    $rutaZip = Join-Path $rutaRuntime $jdkConfig.name
    if (-not (Test-Path -LiteralPath $rutaZip)) {
        Write-Host 'Descargando JDK portatil...'
        Invoke-WebRequest -Uri $jdkConfig.link -OutFile $rutaZip
    }
    if ((Get-FileHash -LiteralPath $rutaZip -Algorithm SHA256).Hash.ToLower() -ne $jdkConfig.checksum.ToLower()) {
        throw 'El checksum del JDK no coincide. No se ejecutara el archivo descargado.'
    }
    Expand-Archive -LiteralPath $rutaZip -DestinationPath $rutaJdkBase -Force
    $jdkLocal = Get-ChildItem -LiteralPath $rutaJdkBase -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'bin/java.exe') } | Select-Object -First 1
}
if (-not $jdkLocal) { throw 'No se encontro el JDK extraido.' }
$javaPrevio = $env:JAVA_HOME
$pathPrevio = $env:Path
$mavenHomePrevio = $env:MAVEN_USER_HOME
$mavenOptsPrevio = $env:MAVEN_OPTS
try {
    $env:JAVA_HOME = $jdkLocal.FullName
    $env:Path = (Join-Path $env:JAVA_HOME 'bin') + ';' + $env:Path
    $env:MAVEN_USER_HOME = Join-Path $rutaRuntime 'maven-home'
    $env:MAVEN_OPTS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NUL'
    & (Join-Path $env:JAVA_HOME 'bin/java.exe') -version
    if ($Accion -eq 'preparar') { Write-Host 'JDK listo. Maven descargara las dependencias en la primera ejecucion.'; return }
    $rutaProyecto = Join-Path $raizPaquete 'proyecto'
    $repoMaven = Join-Path $rutaRuntime 'm2'
    $rutaLogs = Join-Path $raizPaquete 'nuevas_evidencias'
    New-Item -ItemType Directory -Force $rutaLogs | Out-Null
    $marca = Get-Date -Format 'yyyyMMdd-HHmmss'
    $rutaLog = Join-Path $rutaLogs ($Accion + '-' + $marca + '.log')
    Push-Location $rutaProyecto
    try {
        $argumentos = @('-B', "-Dmaven.repo.local=$repoMaven")
        switch ($Accion) {
            'casos' { $argumentos += @('spring-javaformat:apply','-Dtest=AvanceUnitTests,AvanceIntegrationTests','test') }
            'originales' { $argumentos += @('-Dtest=ValidatorTests,PetValidatorTests,ClinicServiceTests','test') }
            'iniciar' { $argumentos += @('spring-boot:run') }
        }
        & './mvnw.cmd' @argumentos 2>&1 | Tee-Object -FilePath $rutaLog
        $codigoMaven = $LASTEXITCODE
        if ($Accion -ne 'iniciar') {
            $rutaReportes = Join-Path $rutaProyecto 'target/surefire-reports'
            if (Test-Path -LiteralPath $rutaReportes) {
                Copy-Item -LiteralPath $rutaReportes -Destination (Join-Path $rutaLogs ($Accion + '-' + $marca + '-reportes')) -Recurse
            }
        }
        if ($codigoMaven -ne 0) { throw "Maven termino con codigo $codigoMaven. Revisar $rutaLog" }
    } finally { Pop-Location }
} finally {
    $env:JAVA_HOME = $javaPrevio
    $env:Path = $pathPrevio
    $env:MAVEN_USER_HOME = $mavenHomePrevio
    $env:MAVEN_OPTS = $mavenOptsPrevio
}

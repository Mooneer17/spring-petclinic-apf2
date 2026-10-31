# APF2 - Menu de demostracion en vivo sobre MySQL (Windows PowerShell 5.1+)
# Ejecuta UN caso por opcion y guarda todo en nuevas_evidencias\<fecha-hora>_DEMO_MySQL\
# No modifica proyecto\src, scripts\ ni evidencias\. No detiene la app, MySQL ni H2.
param([switch]$Preparar)

$ErrorActionPreference = 'Stop'
$Raiz      = Split-Path -Parent $PSScriptRoot
$Proyecto  = Join-Path $Raiz 'proyecto'
$Build     = Join-Path $Raiz '.runtime\demo_build'      # copia aislada para compilar y probar
$Venv      = Join-Path $Raiz '.runtime\venv'
$Py        = Join-Path $Venv 'Scripts\python.exe'
$DemoPy    = Join-Path $PSScriptRoot 'demo_caso.py'
$Marca     = Join-Path $Raiz '.runtime\demo_preparado.txt'
$RtDefensa = Join-Path $HOME 'Desktop\APF2_Defensa\paquete\APF2_Entregable\.runtime'
$M2        = Join-Path $RtDefensa 'm2'

$AppUrl    = 'http://localhost:8081'
$MysqlUrl  = 'jdbc:mysql://localhost:3306/petclinic'
$MysqlUser = 'petclinic'
$EtiquetaBD = 'MySQL 8.0.46 (PC Windows)'
$script:Clave = $null   # SecureString, solo en memoria

# ---------------- Java y Maven (configuracion que ya funciono) ----------------
$jbr = 'C:\Program Files\Android\Android Studio\jbr'
$p12 = Join-Path $HOME 'Desktop\APF2_Defensa\nuevas_evidencias\20261030-1050_PC_Windows\windows-roots.p12'
if ((Test-Path "$jbr\bin\java.exe") -and (Test-Path $p12)) {
    $env:JAVA_HOME = $jbr
    $env:MAVEN_OPTS = "-Djavax.net.ssl.trustStoreType=PKCS12 -Djavax.net.ssl.trustStore=$p12 -Djavax.net.ssl.trustStorePassword=changeit"
} else {
    $t = Get-ChildItem (Join-Path $RtDefensa 'jdk') -Directory -ErrorAction SilentlyContinue |
         Where-Object { Test-Path (Join-Path $_.FullName 'bin\java.exe') } | Select-Object -First 1
    if ($t) { $env:JAVA_HOME = $t.FullName }
    $env:MAVEN_OPTS = '-Djavax.net.ssl.trustStoreType=Windows-ROOT -Djavax.net.ssl.trustStore=NUL'
}
if ($env:JAVA_HOME) { $env:Path = "$env:JAVA_HOME\bin;$env:Path" }
$env:MAVEN_USER_HOME = Join-Path $RtDefensa 'maven-home'

# ---------------- utilidades ----------------
function Linea { Write-Host ('-' * 66) -ForegroundColor DarkGray }
function Pausa { Write-Host ''; Read-Host 'Pulsa Enter para volver al menu' | Out-Null }

function Probar-Http([string]$url) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { return $false }
}
function Probar-Puerto([int]$puerto) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $r = $c.BeginConnect('localhost', $puerto, $null, $null); return ($r.AsyncWaitHandle.WaitOne(2000) -and $c.Connected) }
    catch { return $false } finally { $c.Close() }
}

function Requisitos([switch]$Silencioso) {
    $lista = [ordered]@{
        'Proyecto Maven (proyecto\mvnw.cmd)'   = (Test-Path (Join-Path $Proyecto 'mvnw.cmd'))
        'Java (JAVA_HOME)'                      = [bool]($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe"))
        'Repositorio Maven local (m2)'          = (Test-Path $M2)
        'Dependencias preparadas (opcion P)'    = (Test-Path $Marca)
        "Aplicacion en $AppUrl"                 = (Probar-Http $AppUrl)
        'MySQL escuchando en puerto 3306'       = (Probar-Puerto 3306)
        'Locust para la opcion 5 (opcion P)'    = (Test-Path (Join-Path $Venv 'Scripts\locust.exe'))
    }
    if (-not $Silencioso) {
        foreach ($k in $lista.Keys) {
            if ($lista[$k]) { Write-Host "  [OK]    $k" -ForegroundColor Green } else { Write-Host "  [FALTA] $k" -ForegroundColor Yellow }
        }
    }
    return $lista
}

function Pedir-Clave {
    if (-not $script:Clave) {
        $script:Clave = Read-Host "Contrasena de MySQL para el usuario '$MysqlUser' (no se guarda)" -AsSecureString
    }
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($script:Clave)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

function Nueva-Carpeta([string]$caso) {
    $d = Join-Path $Raiz ("nuevas_evidencias\" + (Get-Date -Format 'yyyyMMdd-HHmmss') + "_DEMO_MySQL\$caso")
    New-Item -ItemType Directory -Force $d | Out-Null
    return $d
}

function Sincronizar-Copia {
    robocopy $Proyecto $Build /E /XD target .git /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "No se pudo copiar el proyecto a $Build (robocopy $LASTEXITCODE)" }
}

function Ejecutar-Proceso([string]$exe, [string]$argumentos, [string]$log, [string]$dir) {
    # Toda la salida va al archivo; en pantalla solo el resultado.
    $cmd = "`"$exe`" $argumentos > `"$log`" 2>&1"
    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/d', '/s', '/c', "`"$cmd`"" -WorkingDirectory $dir -NoNewWindow -Wait -PassThru
    return $p.ExitCode
}

function Resumen-Maven([string]$log) {
    if (-not (Test-Path $log)) { return @('(no se genero maven.log)') }
    $pat = 'Running org\.|Tests run:.* in org|Database JDBC URL|Database version|HikariPool-1 - Added connection|Access denied|Communications link failure|BUILD (SUCCESS|FAILURE)|Total time'
    $out = @()
    foreach ($m in (Select-String -Path $log -Pattern $pat)) {
        $l = $m.Line.Trim() -replace '^\[(INFO|ERROR|WARNING)\]\s*', ''
        if ($l -match ' : ') { $l = ($l -split ' : ', 2)[1] }   # quita fecha, hilo y clase del log de Spring
        if ($l.Length -gt 140) { $l = $l.Substring(0, 140) + '...' }
        if ($out -notcontains $l) { $out += $l }
    }
    return ($out | Select-Object -First 10)
}

function Resumen-Http([string]$carpeta, [bool]$cabeceras) {
    $out = @()
    $dir = Join-Path $carpeta 'respuestas'
    foreach ($f in (Get-ChildItem $dir -Filter *.http.txt -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)) {
        $ls = @(Get-Content $f.FullName -TotalCount 60 -Encoding UTF8)
        $i = 0; while ($i -lt $ls.Count -and $ls[$i] -notmatch '^HTTP \d{3}$') { $i++ }
        if ($i -ge $ls.Count) { continue }
        $hdr = @(); $j = $i + 1
        while ($j -lt $ls.Count -and $ls[$j] -ne '') { $hdr += $ls[$j]; $j++ }
        $loc = $hdr | Where-Object { $_ -like 'Location:*' } | Select-Object -First 1
        $linea = "$($ls[0]) -> $($ls[$i])"
        if ($loc) { $linea += ", $loc" }
        $out += $linea
        if ($cabeceras) { $out += 'Cabeceras recibidas: ' + (($hdr | ForEach-Object { ($_ -split ':', 2)[0] }) -join ', ') }
    }
    $sal = Join-Path $carpeta 'salida.log'
    if (Test-Path $sal) { $out += @(Get-Content $sal | Where-Object { $_ -match '^\[(OK |FAIL|BLOQ)\]|^Confirmacion' } | ForEach-Object { $_.Trim() }) }
    if ($out.Count -eq 0) { $out = @('(sin respuestas HTTP registradas)') }
    return $out
}

function Mostrar-Ficha($f, [string]$carpeta) {
    $texto = @(
        "CASO Y TIPO         : $($f.Caso)",
        "QUE SE COMPRUEBA    : $($f.Que)",
        "AMBIENTE Y URL      : $($f.Ambiente)",
        "RESULTADO ESPERADO  : $($f.Esperado)",
        "RESULTADO OBTENIDO  : $($f.Obtenido)",
        "ESTADO              : $($f.Estado)",
        "DURACION            : $($f.Duracion)",
        "RUTA DE EVIDENCIA   : $carpeta"
    )
    if ($f.Extra) { $texto += $f.Extra }
    $texto += "Referencia en el informe: $($f.Referencia)"
    if ($f.Log) { $texto += 'LOG RESUMIDO (completo en la ruta de evidencia):'; $texto += @($f.Log | ForEach-Object { "  $_" }) }
    $texto += 'Ejecucion de demostracion: nueva y separada de las evidencias historicas.'
    $texto | Set-Content -Path (Join-Path $carpeta 'ficha.txt') -Encoding UTF8

    Write-Host ''; Linea
    foreach ($l in $texto) {
        if ($l -like 'LOG RESUMIDO*') { Write-Host $l -ForegroundColor Cyan }
        elseif ($l -like '  *') { Write-Host $l -ForegroundColor Gray }
        elseif ($l -like 'ESTADO*') {
            $color = @{ 'APROBADO' = 'Green'; 'FALLIDO' = 'Red'; 'BLOQUEADO' = 'Yellow' }[$f.Estado]
            Write-Host $l -ForegroundColor $color
        } else { Write-Host $l }
    }
    Linea
    if ($f.Estado -ne 'APROBADO' -and $f.Detalle) {
        $r = Read-Host 'Ver detalles del resultado? (s/n)'
        if ($r -match '^[sS]') { Write-Host ''; $f.Detalle | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray } }
    }
}

# ---------------- preparar dependencias (antes de exponer) ----------------
function Preparar {
    Write-Host 'Preparando dependencias. Puede descargar archivos; hazlo ANTES de exponer.' -ForegroundColor Cyan
    Sincronizar-Copia
    $log = Join-Path $Raiz '.runtime\demo_preparacion.log'
    Write-Host '  1/2 Maven: compilar y resolver dependencias de prueba (corre CP01, sin base de datos)...'
    $rc = Ejecutar-Proceso (Join-Path $Build 'mvnw.cmd') "-B `"-Dmaven.repo.local=$M2`" test `"-Dtest=AvanceUnitTests#CP01_telephoneNineDigitsRejectedTenAccepted`" -Dsurefire.failIfNoSpecifiedTests=false" $log $Build
    if ($rc -ne 0) { Write-Host "  ERROR en Maven (codigo $rc). Revisa $log" -ForegroundColor Red; return }
    Write-Host '  2/2 Python: entorno local con requests, pymysql, cryptography y locust...'
    if (-not (Test-Path $Py)) {
        $base = (Get-Command py -ErrorAction SilentlyContinue)
        if ($base) { & py -3 -m venv $Venv } else { & python -m venv $Venv }
    }
    & $Py -m pip install -q --disable-pip-version-check requests pymysql cryptography locust 2>&1 | Out-File -Append $log
    if ($LASTEXITCODE -ne 0) { Write-Host "  ERROR en pip. Revisa $log" -ForegroundColor Red; return }
    "Preparado: $(Get-Date -Format s)" | Set-Content $Marca
    Write-Host '  Listo. Ya no se necesitan descargas para la demostracion.' -ForegroundColor Green
}

# ---------------- casos Maven (CP01, CP02) ----------------
function Caso-Maven([string]$id, [string]$clase, [string]$metodo, [bool]$conMysql, [string]$okTxt) {
    $tipo = if ($conMysql) { 'integracion' } else { 'unitaria' }
    $carpeta = Nueva-Carpeta "${id}_$tipo"
    Sincronizar-Copia
    $rep = Join-Path $Build 'target\surefire-reports'
    $inicio = (Get-Date).AddSeconds(-2)   # solo se usan reportes escritos en esta ejecucion (no se borra nada)
    $log = Join-Path $carpeta 'maven.log'
    $args_ = "-B -o `"-Dmaven.repo.local=$M2`" test `"-Dtest=$clase#$metodo`" -Dsurefire.failIfNoSpecifiedTests=false"
    "mvnw.cmd $args_" | Set-Content (Join-Path $carpeta 'comando.txt')
    $vars = 'DATABASE', 'SPRING_DATASOURCE_URL', 'SPRING_DATASOURCE_USERNAME', 'SPRING_DATASOURCE_PASSWORD', 'SPRING_SQL_INIT_MODE'
    if ($conMysql) {
        $env:DATABASE = 'mysql'; $env:SPRING_DATASOURCE_URL = $MysqlUrl; $env:SPRING_DATASOURCE_USERNAME = $MysqlUser
        $env:SPRING_DATASOURCE_PASSWORD = Pedir-Clave; $env:SPRING_SQL_INIT_MODE = 'always'
        "Variables de entorno (sin contrasena): DATABASE=mysql SPRING_DATASOURCE_URL=$MysqlUrl SPRING_DATASOURCE_USERNAME=$MysqlUser SPRING_SQL_INIT_MODE=always" |
            Add-Content (Join-Path $carpeta 'comando.txt')
    }
    Write-Host "Ejecutando $id con Maven/JUnit (solo el metodo $metodo)..." -ForegroundColor Cyan
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try { $rc = Ejecutar-Proceso (Join-Path $Build 'mvnw.cmd') $args_ $log $Build }
    finally { foreach ($v in $vars) { Remove-Item "Env:$v" -ErrorAction SilentlyContinue } }
    $sw.Stop()
    $nuevos = @(Get-ChildItem $rep -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $inicio })
    if ($nuevos.Count -gt 0) {
        $dRep = Join-Path $carpeta 'surefire-reports'; New-Item -ItemType Directory -Force $dRep | Out-Null
        $nuevos | Copy-Item -Destination $dRep -ErrorAction SilentlyContinue
    }

    $tc = $null
    $xmlF = Join-Path $rep "TEST-org.springframework.samples.petclinic.owner.$clase.xml"
    if ((Test-Path $xmlF) -and ((Get-Item $xmlF).LastWriteTime -ge $inicio)) {
        $x = [xml](Get-Content $xmlF -Raw -Encoding UTF8)
        $tc = @($x.testsuite.testcase) | Where-Object { $_.name -eq $metodo } | Select-Object -First 1
    }
    $logTxt = if (Test-Path $log) { Get-Content $log -Raw } else { '' }
    $falla = if ($tc) { @($tc.failure) + @($tc.error) | Where-Object { $_ } | Select-Object -First 1 } else { $null }
    $detalle = @(Select-String -Path $log -Pattern 'Tests run:|ERROR|Caused by|Access denied|expected|Expecting' -ErrorAction SilentlyContinue |
                 Select-Object -First 12 | ForEach-Object { $_.Line.Trim() })

    $bdTxt = 'Sin acceso a base de datos (JUnit + Bean Validation, sin Spring)'
    $extra = @()
    $mysqlOk = $true
    if ($conMysql) {
        $u = [regex]::Match($logTxt, 'Database JDBC URL \[([^\]]+)\]').Groups[1].Value
        $v = [regex]::Match($logTxt, 'Database version: ([0-9.]+)').Groups[1].Value
        $h2 = $logTxt -match 'jdbc:h2:'
        $mysqlOk = ($u -like 'jdbc:mysql:*') -and -not $h2
        $bdTxt = if ($mysqlOk) { "MySQL $v confirmado en el log JDBC ($u)" } else { 'NO se confirmo MySQL en el log JDBC' }
        $extra += 'Datos: la prueba es @Transactional; sus cambios se revierten al terminar (no deja filas en MySQL).'
        if ($logTxt -match 'Access denied') { $script:Clave = $null }
    }

    if (-not $tc) {
        $estado = 'BLOQUEADO'
        $obtenido = "No se genero el reporte JUnit (Maven termino con codigo $rc)."
        if ($logTxt -match 'Access denied') { $obtenido = 'MySQL rechazo la contrasena (Access denied). Se pedira de nuevo.' }
        elseif ($logTxt -match 'Communications link failure') { $obtenido = 'No hay conexion con MySQL en localhost:3306.' }
        elseif ($logTxt -match 'offline|Cannot access .* in offline mode') { $obtenido = 'Faltan dependencias: ejecuta la opcion P antes de exponer.' }
    } elseif ($falla) {
        $msg = "$($falla.message)"; if (-not $msg) { $msg = "$($falla.type)" }
        if ($conMysql -and ($logTxt -match 'Access denied|Communications link failure|Failed to load ApplicationContext')) {
            $estado = 'BLOQUEADO'
            if ($logTxt -match 'Access denied') { $obtenido = 'MySQL rechazo la contrasena (Access denied). Se pedira de nuevo.' }
            elseif ($logTxt -match 'Communications link failure') { $obtenido = 'No hay conexion con MySQL en localhost:3306.' }
            else { $obtenido = 'El contexto de Spring no arranco; ver maven.log.' }
        } else { $m1 = $msg.Split("`n")[0]; if ($m1.Length -gt 200) { $m1 = $m1.Substring(0, 200) + '...' }
                 $estado = 'FALLIDO'; $obtenido = "Asercion no cumplida: $m1" }
    } elseif ($conMysql -and -not $mysqlOk) {
        $estado = 'BLOQUEADO'; $obtenido = 'La prueba paso, pero no se confirmo que usara MySQL; no vale como evidencia MySQL.'
    } else {
        $estado = 'APROBADO'
        $obtenido = $okTxt
    }
    $durTest = if ($tc) { "; metodo de prueba: $($tc.time) s" } else { '' }
    return @{ Estado = $estado; Obtenido = $obtenido; Ambiente = $bdTxt; Extra = $extra; Detalle = $detalle; Log = (Resumen-Maven $log)
              Duracion = ('{0:N1} s en total (incluye arranque de Maven{1})' -f $sw.Elapsed.TotalSeconds, $durTest); Carpeta = $carpeta }
}

# ---------------- casos HTTP (F.. y S..) ----------------
function Caso-Http([string]$id, [bool]$conMysql) {
    $tipo = switch -Wildcard ($id) { 'CARGA' { 'carga' } 'E01' { 'concurrencia' } 'F*' { 'funcional' } default { 'seguridad' } }
    $carpeta = Nueva-Carpeta "${id}_$tipo"
    $log = Join-Path $carpeta 'salida.log'
    if (-not (Test-Path $Py)) { return @{ Estado = 'BLOQUEADO'; Obtenido = 'Falta el entorno Python: ejecuta la opcion P.'; Carpeta = $carpeta; Duracion = '-' } }
    $args_ = "`"$DemoPy`" --caso $id --base $AppUrl --out `"$carpeta`" --bd `"$EtiquetaBD`""
    "python $args_" | Set-Content (Join-Path $carpeta 'comando.txt')
    if ($conMysql) { $env:MYSQL_URL = $MysqlUrl; $env:MYSQL_USER = $MysqlUser; $env:MYSQL_PASS = Pedir-Clave }
    Write-Host "Ejecutando $id por HTTP contra $AppUrl ..." -ForegroundColor Cyan
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try { $rc = Ejecutar-Proceso $Py $args_ $log $Raiz }
    finally { 'MYSQL_URL', 'MYSQL_USER', 'MYSQL_PASS' | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue } }
    $sw.Stop()
    $dur = '{0:N1} s' -f $sw.Elapsed.TotalSeconds
    $jf = Join-Path $carpeta 'demo.json'
    $detalle = if (Test-Path $log) { @(Get-Content $log | Select-Object -Last 8) } else { @() }
    if (-not (Test-Path $jf)) {
        return @{ Estado = 'BLOQUEADO'; Obtenido = "El caso no llego a ejecutarse (codigo $rc). Revisa que la app responda en $AppUrl."; Carpeta = $carpeta; Duracion = $dur; Detalle = $detalle; Log = $detalle }
    }
    $j = Get-Content $jf -Raw -Encoding UTF8 | ConvertFrom-Json
    $estado = @{ 'Aprobado' = 'APROBADO'; 'Fallido' = 'FALLIDO'; 'Bloqueado' = 'BLOQUEADO' }["$($j.caso.estado)"]
    if (-not $estado) { $estado = 'BLOQUEADO' }
    $extra = @()
    if ($id -eq 'F01') {
        $extra += "Propietario creado: id=$($j.extra.owner_id), apellido=$($j.extra.apellido)"
        $extra += "Confirmacion directa en MySQL: $($j.extra.mysql)"
        $extra += "Consulta para Workbench: $($j.extra.sql)"
        if ("$($j.extra.mysql)" -match 'Access denied') { $script:Clave = $null }
        $extra += 'Datos: este registro queda guardado en MySQL (es ficticio y se reconoce por el prefijo DemoF01).'
    } else {
        if ($j.extra.origen) { $extra += "Codigo ejecutado: $($j.extra.origen) (solo este caso)" }
        if ($j.extra.nota) { $extra += "Nota: $($j.extra.nota)" }
        if ($j.extra.sql -and $id -notin 'S02', 'S12') {
            $extra += "Consulta para Workbench: $($j.extra.sql)"
            if ($j.extra.tag) { $extra += "Datos: si la prueba creo registros, quedan en MySQL con apellidos terminados en $($j.extra.tag)." }
        }
        if ($id -eq 'CARGA') {
            $extra += 'Codigo ejecutado: scripts/locustfile.py sin cambios (Locust, modo sin interfaz).'
            $extra += 'Datos: cada usuario virtual crea en MySQL un propietario Perf..., una mascota y visitas.'
            $extra += "Reporte grafico de Locust: $(Join-Path $carpeta 'carga.html')"
        }
        if ($id -eq 'E01') {
            $extra += 'Codigo ejecutado: scripts/exploratorio_duplicado_concurrente.py sin cambios.'
            $extra += 'Datos: crea 5 propietarios Cc... y puede dejar mascotas duplicadas o sin propietario (DEF-P02).'
        }
    }
    return @{ Estado = $estado; Obtenido = "$($j.caso.obtenido)"; Carpeta = $carpeta; Duracion = $dur; Extra = $extra; Detalle = $detalle
              Log = (Resumen-Http $carpeta ($id -eq 'S12')); Esperado = "$($j.caso.esperado)" }
}

# ---------------- catalogo de pruebas ----------------
# T: U = unitaria (JUnit, sin BD), I = integracion (JUnit + MySQL), H = HTTP contra la app
function C($n, $id, $t, $menu, $que, $esp, $ref, $metodo = '', $ok = '', $mysql = $false) {
    [pscustomobject]@{ N = $n; Id = $id; T = $t; Menu = $menu; Que = $que; Esperado = $esp; Ref = $ref; Metodo = $metodo; Ok = $ok; Mysql = $mysql }
}
$FALLA = ' Es un fallo esperado y documentado: sigue siendo FALLIDO.'
$Catalogo = @(
  (C '1'  'CP01' 'U' 'CP01  Telefono de 10 digitos (sin base de datos)' 'La regla del telefono de Owner: exactamente 10 digitos' 'Telefono 987654321 (9 digitos) rechazado; 9876543210 (10 digitos) aceptado' 'CP01 Aprobado' 'CP01_telephoneNineDigitsRejectedTenAccepted' 'El telefono de 9 digitos genero error de validacion y el de 10 digitos no genero errores.')
  (C '2'  'CP02' 'I' 'CP02  Recuperar propietario persistido en MySQL' 'Guardar un propietario en MySQL y recuperarlo por apellido' "Ana TorresAPF se guarda y la busqueda 'TorresAPF' devuelve 1 registro con el mismo id, nombre y telefono" 'CP02 Aprobado (R3, MySQL)' 'CP02_findOwnerByLastName' 'Se guardo y se recupero 1 propietario por apellido con el mismo id, nombre y telefono.')
  (C '3'  'F01'  'H' 'F01   Registro de propietario valido' 'Registrar un propietario con datos validos desde el formulario' "302 a /owners/{id}; mensaje 'New Owner Created'; el detalle muestra los datos" 'F01 Aprobado' '' '' $true)
  (C '4'  'S12'  'H' 'S12   Cabeceras de seguridad HTTP' 'Cabeceras X-Content-Type-Options, X-Frame-Options, Content-Security-Policy y Cache-Control en GET /' 'Presencia de las cuatro cabeceras defensivas' ('S12 Fallido (SEC-03).' + $FALLA))
  (C '6'  'CP05' 'U' 'CP05  Nombre de mascota obligatorio (sin base de datos)' 'La validacion del nombre de mascota (PetValidator)' "Nombre vacio: error en name; 'Luna': sin errores" 'CP05 Aprobado' 'CP05_emptyPetNameRejectedValidNameAccepted' "El nombre vacio genero error en name y 'Luna' no genero errores.")
  (C '7'  'CP03' 'I' 'CP03  Actualizar telefono y releer de MySQL' 'Actualizar el telefono de un propietario en MySQL y volver a leerlo' 'Mismo id y telefono 9123456780 tras recargar' 'CP03 Aprobado (R3, MySQL)' 'CP03_updatePhoneAndReload' 'Tras guardar y recargar, el propietario conserva su id y el telefono 9123456780.')
  (C '8'  'CP04' 'I' 'CP04  Guardar mascota con su propietario' 'Guardar una mascota asociada a su propietario y volver a leerla' 'Mascota LunaAPF no nula, con fecha 2022-05-10 y tipo registrado' 'CP04 Aprobado tras corregir la prueba (INC-T01)' 'CP04_savePetWithCorrectOwner' 'La mascota LunaAPF se recupero de MySQL con su fecha y su tipo.')
  (C '9'  'CP06' 'I' 'CP06  Registrar visita por la web y releer' 'Registrar una visita por la web (MockMvc) y leerla desde MySQL' "Redireccion 3xx y 1 visita con la fecha de manana y 'Control general APF'" 'CP06 Aprobado tras corregir la prueba (INC-T01)' 'CP06_registerVisitViaWebAndReload' 'Hubo redireccion y se recupero 1 visita con la fecha y la descripcion enviadas.')
  (C '10' 'F02'  'H' 'F02   Telefono de 9 digitos rechazado' 'Rechazo del registro con telefono de 9 digitos' "200 con 'Telephone must be a 10-digit number'; el propietario no se guarda" 'F02 Aprobado')
  (C '11' 'F09'  'H' 'F09   Busqueda sin resultados' 'Buscar un apellido que no existe' "200 con mensaje 'has not been found'" 'F09 Aprobado')
  (C '12' 'F15'  'H' 'F15   Registro de mascota valida' 'Registrar una mascota valida para un propietario' "302; mensaje 'New Pet has been Added'; la mascota aparece con nombre, fecha y tipo" 'F15 Aprobado')
  (C '13' 'F17'  'H' 'F17   Mascota con nombre duplicado' "Rechazo de una mascota 'LUNA' cuando ya existe 'Luna'" "200 con 'is already in use'; sigue existiendo una sola mascota" 'F17 Aprobado')
  (C '14' 'F18'  'H' 'F18   Fecha de nacimiento futura' 'Rechazo de una mascota con nacimiento manana' "200 con 'invalid date'; no se registra la mascota" 'F18 Aprobado')
  (C '15' 'F26'  'H' 'F26   Visita valida (manana)' 'Registrar una visita con fecha de manana' "302; mensaje 'Your visit has been booked'; la visita aparece" 'F26 Aprobado')
  (C '16' 'F27'  'H' 'F27   Visita con fecha de hoy' 'Rechazo de una visita con fecha de hoy (valor limite)' "200 con 'Visit date must be in the future'; no se registra" 'F27 Aprobado')
  (C '17' 'S02'  'H' 'S02   Actuator expuesto sin credenciales' 'Acceso anonimo a /actuator, /actuator/env y otros endpoints' 'Endpoints sensibles no accesibles de forma anonima' ('S02 Fallido (SEC-01).' + $FALLA))
  (C '18' 'S03'  'H' 'S03   XSS almacenado' 'Que el HTML guardado en direccion y ciudad se muestre escapado' 'El contenido se muestra escapado; no hay etiqueta <script> ejecutable' 'S03 Aprobado')
  (C '19' 'S04'  'H' 'S04   Inyeccion SQL en la busqueda' 'Tres cargas de inyeccion SQL en el campo apellido' "Se tratan como texto: 200 'has not been found', sin trazas" 'S04 Aprobado')
  (C '20' 'S08'  'H' 'S08   Editar mascota de otro propietario' 'GET y POST para editar la mascota de B desde la URL del propietario A' 'Rechazo controlado (4xx); la mascota de B no cambia' ('S08 Fallido (DEF-P01): responde 500.' + $FALLA))
  (C '5'  'CARGA' 'H' 'Carga basica: 10 usuarios durante 30 s (Locust)' 'Tiempo de respuesta y errores con 10 usuarios simultaneos durante 30 s' 'p95 < 1000 ms y errores < 1 % (umbral propuesto por el equipo)' 'Informe (180 s): 10 usuarios p95 21 ms y 30 usuarios p95 16 ms; 0 errores en 4804 solicitudes')
  (C '22' 'E01'  'H' 'E01   Concurrencia: misma mascota enviada 4 veces a la vez' 'Altas simultaneas de una mascota con el mismo nombre en 5 propietarios' 'Una mascota por propietario; el resto rechazado; ninguna fila sin propietario; sin HTTP 500' ('E01 Fallido (DEF-P02, DEF-P03): en MySQL hubo HTTP 500 y mascotas sin propietario.' + $FALLA) '' '' $true)
  (C '21' 'S13'  'H' 'S13   Id de sesion en la URL' 'Que la redireccion no incluya ;jsessionid= en la URL' 'La redireccion no incluye el identificador de sesion' ('S13 Fallido (SEC-04).' + $FALLA))
)
$SinBD = 'S02', 'S12'
$Avisos = @{
    'CARGA' = @('PRUEBA DE CARGA (version corta)',
                '- Envia solicitudes a localhost:8081 con 10 usuarios simultaneos durante 30 segundos.',
                '- Crea en MySQL unos 10 propietarios Perf..., cada uno con una mascota y visitas.',
                '- No detiene la aplicacion ni MySQL.')
    'E01'   = @('PRUEBA DE CONCURRENCIA (version corta)',
                '- Crea 5 propietarios y envia 4 altas simultaneas de la mascota Gemela a cada uno.',
                '- Segun el informe (DEF-P02), en MySQL puede dejar mascotas duplicadas o sin propietario (owner_id NULL).',
                '- No borra ni reinicia datos existentes.')
}

function Confirmar([string[]]$aviso) {
    Write-Host ''
    foreach ($l in $aviso) { Write-Host $l -ForegroundColor Yellow }
    $r = Read-Host 'Escribe SI para ejecutarla (cualquier otra cosa cancela)'
    return ($r.Trim().ToUpper() -eq 'SI')
}

function Ejecutar-Caso($c) {
    switch ($c.T) {
        'U' { $r = Caso-Maven $c.Id 'AvanceUnitTests' $c.Metodo $false $c.Ok; $tipo = 'Prueba unitaria' }
        'I' {
            if (-not (Probar-Puerto 3306)) {
                $r = @{ Estado = 'BLOQUEADO'; Obtenido = 'MySQL no responde en localhost:3306; la prueba no se ejecuto.'
                        Ambiente = 'MySQL no disponible'; Duracion = '-'; Carpeta = (Nueva-Carpeta "$($c.Id)_integracion")
                        Log = @('Comprobacion previa: puerto 3306 cerrado. No se llamo a Maven.') }
                $tipo = 'Prueba de integracion (Spring + JPA + MySQL)'
                break
            }
            $r = Caso-Maven $c.Id 'AvanceIntegrationTests' $c.Metodo $true $c.Ok; $tipo = 'Prueba de integracion (Spring + JPA + MySQL)'
        }
        'H' {
            $r = Caso-Http $c.Id ([bool]$c.Mysql)
            $tipo = switch -Wildcard ($c.Id) { 'CARGA' { 'Prueba de carga basica (Locust)' } 'E01' { 'Prueba adicional de concurrencia' }
                                               'F*' { 'Prueba funcional por HTTP real' } default { 'Prueba de seguridad basica' } }
            $r.Ambiente = if ($SinBD -contains $c.Id) { "$AppUrl (la base no interviene en este caso)" } else { "$AppUrl (app con perfil mysql) - $EtiquetaBD" }
            if (-not $r.Esperado) { $r.Esperado = $c.Esperado }
        }
    }
    if (-not $r.Esperado) { $r.Esperado = $c.Esperado }
    $r.Caso = "$($c.Id) - $tipo"; $r.Que = $c.Que; $r.Referencia = $c.Ref
    return $r
}

function Linea-Menu($n) { $c = $Catalogo | Where-Object { $_.N -eq $n }; Write-Host ('  {0,3}. {1}' -f $c.N, $c.Menu) }

# ---------------- menu ----------------
if ($Preparar) { Preparar; Pausa; exit }

$env:PYTHONIOENCODING = 'utf-8'
:menu while ($true) {
    Clear-Host
    Write-Host 'APF2 - DEMOSTRACION EN VIVO SOBRE MYSQL' -ForegroundColor Cyan
    Write-Host "App: $AppUrl   Base: $EtiquetaBD   (localhost:8080 / H2 no se usa)"
    Write-Host 'Cada ejecucion es nueva y se guarda en nuevas_evidencias\<fecha-hora>_DEMO_MySQL\'
    $req = Requisitos -Silencioso
    $faltan = @($req.Keys | Where-Object { -not $req[$_] })
    if ($faltan.Count -eq 0) { Write-Host 'Requisitos: todos OK' -ForegroundColor Green }
    else { foreach ($k in $faltan) { Write-Host "  [FALTA] $k" -ForegroundColor Yellow } }
    Linea
    Write-Host ' UNITARIAS (sin base de datos)' -ForegroundColor Cyan; '1', '6' | ForEach-Object { Linea-Menu $_ }
    Write-Host ' INTEGRACION (JUnit + MySQL)' -ForegroundColor Cyan; '2', '7', '8', '9' | ForEach-Object { Linea-Menu $_ }
    Write-Host ' FUNCIONALES (HTTP contra la app)' -ForegroundColor Cyan; '3', '10', '11', '12', '13', '14', '15', '16' | ForEach-Object { Linea-Menu $_ }
    Write-Host ' SEGURIDAD BASICA' -ForegroundColor Cyan; '4', '17', '18', '19', '20', '21' | ForEach-Object { Linea-Menu $_ }
    Write-Host ' CARGA Y CONCURRENCIA (piden confirmacion)' -ForegroundColor Cyan; '5', '22' | ForEach-Object { Linea-Menu $_ }
    Write-Host ' OTRAS' -ForegroundColor Cyan
    Write-Host '    P. Preparar dependencias (antes de exponer)'
    Write-Host '    0. Salir'
    Linea
    $op = (Read-Host 'Elige una opcion').Trim().ToUpper()
    $f = $null; $c = $null
    try {
        if ($op -eq '0') { exit }
        elseif ($op -eq 'P') { Preparar; Pausa; continue menu }
        $c = $Catalogo | Where-Object { $_.N -eq $op -or $_.Id -eq $op } | Select-Object -First 1
        if (-not $c) { continue menu }
        if ($Avisos.ContainsKey($c.Id) -and -not (Confirmar $Avisos[$c.Id])) {
            Write-Host 'Cancelado. No se ejecuto nada.' -ForegroundColor Gray; Pausa; continue menu
        }
        if ($c.Id -eq 'CARGA') { Write-Host 'Duracion aproximada: 35 segundos.' -ForegroundColor Gray }
        $f = Ejecutar-Caso $c
        Mostrar-Ficha $f $f.Carpeta
    } catch {
        $err = $_.Exception.Message
        $idErr = if ($c) { $c.Id } else { $op }
        try {
            $dErr = Nueva-Carpeta "${idErr}_no_ejecutado"
            @("CASO                : $idErr", 'ESTADO              : BLOQUEADO',
              "RESULTADO OBTENIDO  : La prueba no se pudo ejecutar: $err",
              "FECHA               : $(Get-Date -Format s)",
              'Ejecucion de demostracion: nueva y separada de las evidencias historicas.') |
                Set-Content (Join-Path $dErr 'ficha.txt') -Encoding UTF8
        } catch { $dErr = '(no se pudo crear la carpeta de evidencia)' }
        Write-Host ''
        Write-Host "ESTADO: BLOQUEADO - no se pudo ejecutar: $err" -ForegroundColor Yellow
        Write-Host "RUTA DE EVIDENCIA: $dErr" -ForegroundColor Yellow
    }
    Pausa
}

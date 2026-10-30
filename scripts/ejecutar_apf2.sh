#!/usr/bin/env bash
# APF2 - ejecucion completa en Linux/macOS. Requisitos: JDK 17+, Python 3.10+, MySQL 8 local
# con la base y el usuario de proyecto/src/main/resources/db/mysql/user.sql.
# Uso: scripts/ejecutar_apf2.sh [todo|casos|casos-mysql|suite|app|funcionales|seguridad|e01|rendimiento|navegador]
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PROY="$RAIZ/proyecto"
SAL="$RAIZ/nuevas_evidencias/$(date +%Y%m%d-%H%M%S)"
BASE="${BASE:-http://localhost:8080}"
MYSQL_PROPS=(-Ddatabase=mysql -Dspring.datasource.url="${MYSQL_URL:-jdbc:mysql://localhost:3306/petclinic}"
  -Dspring.datasource.username="${MYSQL_USER:-petclinic}" -Dspring.datasource.password="${MYSQL_PASS:-petclinic}"
  -Dspring.sql.init.mode=always)
TESTS='AvanceUnitTests,AvanceIntegrationTests,DiagnosticoFixtureTests'
mkdir -p "$SAL"
export TZ="${TZ:-America/Lima}"

mvnt() { local nombre=$1; shift
  (cd "$PROY" && ./mvnw -B "$@" 2>&1 | tee "$SAL/$nombre.log") || true
  [ -d "$PROY/target/surefire-reports" ] && cp -r "$PROY/target/surefire-reports" "$SAL/$nombre-reportes"
}
py() { python3 "$RAIZ/scripts/$1" "${@:2}"; }

case "${1:-todo}" in
  casos)        mvnt casos_H2 test -Dtest="$TESTS" -Dsurefire.failIfNoSpecifiedTests=false ;;
  casos-mysql)  mvnt casos_MySQL test -Dtest="$TESTS" -Dsurefire.failIfNoSpecifiedTests=false "${MYSQL_PROPS[@]}" ;;
  suite)        mvnt suite_H2 test ;;
  app)          (cd "$PROY" && ./mvnw -B -q package -DskipTests) && \
                java -jar "$PROY"/target/spring-petclinic-*.jar --spring.profiles.active=mysql --spring.docker.compose.enabled=false ;;
  funcionales)  py funcionales_http.py --base "$BASE" --out "$SAL/funcionales" --bd MySQL ;;
  seguridad)    py seguridad_http.py --base "$BASE" --out "$SAL/seguridad" --bd MySQL ;;
  e01)          py exploratorio_duplicado_concurrente.py --base "$BASE" --out "$SAL/e01" --bd MySQL --owners 20 ;;
  rendimiento)  mkdir -p "$SAL/rendimiento"
                locust -f "$RAIZ/scripts/locustfile.py" --headless -H "$BASE" -u 10 -r 2 -t 60s --only-summary --csv "$SAL/rendimiento/calentamiento" > "$SAL/rendimiento/calentamiento.log" 2>&1
                locust -f "$RAIZ/scripts/locustfile.py" --headless -H "$BASE" -u 10 -r 2 -t 180s --only-summary --csv "$SAL/rendimiento/carga10" --html "$SAL/rendimiento/carga10.html" > "$SAL/rendimiento/carga10.log" 2>&1
                locust -f "$RAIZ/scripts/locustfile.py" --headless -H "$BASE" -u 30 -r 3 -t 180s --only-summary --csv "$SAL/rendimiento/carga30" --html "$SAL/rendimiento/carga30.html" > "$SAL/rendimiento/carga30.log" 2>&1 ;;
  navegador)    py navegador_flujos.py --base "$BASE" --out "$SAL/navegador" ;;
  todo)         "$0" casos; "$0" casos-mysql; "$0" suite
                echo "Inicie la aplicacion en otra terminal con: $0 app ; luego pulse Enter"; read -r
                "$0" funcionales; "$0" seguridad; "$0" e01; "$0" navegador; "$0" rendimiento ;;
  *) echo "Accion desconocida: $1"; exit 2 ;;
esac
echo "Salida en: $SAL"

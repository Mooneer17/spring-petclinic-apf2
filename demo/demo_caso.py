"""Ejecutor de demostracion APF2: corre UN caso HTTP (F01 o S12) contra una instancia local.

Por que existe: funcionales_http.py y seguridad_http.py ejecutan su suite completa al
cargarse, asi que no se pueden importar para correr un solo caso.

Equivalencia con los scripts originales:
- S12: mismo GET /, mismas cuatro cabeceras y mismo criterio (todas presentes = Aprobado).
- F01: mismo POST /owners/new, mismos datos (Ana, Av. Central 123, Lima, 9876543210) y
  mismo criterio (302 con id, mensaje 'New Owner Created' y datos visibles en el detalle).
  Unica diferencia: el apellido usa el prefijo 'DemoF01' + sufijo unico, para que el
  registro se reconozca en la base. El original usa 'Fa' + sufijo.
Usa la clase Runner de scripts/apf_common.py (sin cambios).

Resto de casos (F02..F31 y S01..S13 que no son F01 ni S12): se ejecuta el CODIGO ORIGINAL
de funcionales_http.py o seguridad_http.py. El ejecutor lee el script, omite solo el bucle
final que corre toda la suite y llama a la funcion del caso elegido. Mismo codigo, mismos
datos y mismo criterio que la corrida historica.

Carga (CARGA) y concurrencia (E01): versiones cortas que ejecutan sin cambios
scripts/locustfile.py y scripts/exploratorio_duplicado_concurrente.py como procesos aparte.

Uso: python demo_caso.py --caso F01|S12 --base http://localhost:8081 --out DIR --bd "MySQL 8.0.46 (PC Windows)"
"""
import argparse
import datetime as dt
import json
import os
import string
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from apf_common import Runner, wait_up  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--caso", required=True)
ap.add_argument("--base", default="http://localhost:8081")
ap.add_argument("--out", required=True)
ap.add_argument("--bd", required=True)
a = ap.parse_args()

if not wait_up(a.base, seconds=10):
    raise SystemExit(f"La aplicacion no responde en {a.base}")

n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))
started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
extra = {}


def steps(*xs):
    return " ".join(f"{i}) {x}" for i, x in enumerate(xs, 1))


def f01(R):
    F_OWNER_NEW = "New Owner Created"
    last = f"DemoF01{TAG}"
    r = R.post("/owners/new", R.owner_form(lastName=last))
    ev = R.save("F01", "post", r)
    oid = R.owner_id_from(r)
    d = R.follow(r)
    R.save("F01", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    data = d is not None and all(x in d.text for x in (last, "9876543210", "Av. Central 123", "Lima"))
    R.record("F01", "RF01", "Funcional HTTP real", "Registro de propietario con datos validos",
             f"Ana {last}, Av. Central 123, Lima, 9876543210",
             steps("Enviar POST /owners/new con los datos.", "Seguir la redireccion al detalle.",
                   "Verificar mensaje y datos mostrados."),
             f"302 a /owners/{{id}}; mensaje '{F_OWNER_NEW}'; el detalle muestra los datos registrados",
             f"HTTP {r.status_code}, id={oid}; mensaje='{fl}'; datos={'si' if data else 'no'}",
             r.status_code == 302 and oid is not None and fl == F_OWNER_NEW and data, ev)
    extra.update({"owner_id": oid, "apellido": last,
                  "sql": f"SELECT * FROM petclinic.owners WHERE id = {oid};" if oid else
                         f"SELECT * FROM petclinic.owners WHERE last_name = '{last}';"})


def s12(R):
    r = R.get("/")
    ev = R.save("S12", "get", r)
    want = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Cache-Control"]
    present = {h: (h in r.headers) for h in want}
    R.record("S12", "Transversal", "Seguridad basica HTTP", "Cabeceras de seguridad HTTP en la pagina principal",
             "GET /", "Inspeccionar cabeceras de respuesta", "Presencia de cabeceras defensivas basicas",
             "; ".join(f"{k}={v}" for k, v in present.items()), all(present.values()), ev)


def confirmar_en_mysql(oid):
    """Consulta de solo lectura: confirma que la fila creada por F01 esta en MySQL.
    No forma parte del criterio de F01; se informa aparte."""
    import re
    try:
        import pymysql
    except ImportError:
        return "no verificado (falta pymysql; ejecuta la opcion P)"
    m = re.match(r"jdbc:mysql://([^:/]+)(?::(\d+))?/([^?]+)", os.environ.get("MYSQL_URL", ""))
    if not m or not oid:
        return "no verificado (sin MYSQL_URL o sin id)"
    try:
        con = pymysql.connect(host=m.group(1), port=int(m.group(2) or 3306), database=m.group(3),
                              user=os.environ.get("MYSQL_USER", ""), password=os.environ.get("MYSQL_PASS", ""),
                              connect_timeout=5)
        with con.cursor() as c:
            c.execute("SELECT VERSION()")
            ver = c.fetchone()[0]
            c.execute("SELECT id, first_name, last_name, city, telephone FROM owners WHERE id = %s", (oid,))
            row = c.fetchone()
        con.close()
        return f"fila encontrada en MySQL {ver}: {row}" if row else f"fila NO encontrada en MySQL {ver}"
    except Exception as ex:
        return f"no verificado ({type(ex).__name__}: {ex})"


def caso_original(cid):
    """Ejecuta un caso con el codigo original del script (sin el bucle de la suite)."""
    import re
    scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
    if re.fullmatch(r"F\d\d", cid):
        nombre, corte = "funcionales_http.py", "\nIDS = ["
    elif re.fullmatch(r"S\d\d", cid):
        nombre, corte = "seguridad_http.py", "\nfor i, c in enumerate(CASES"
    else:
        raise SystemExit(f"Caso no reconocido: {cid}")
    ruta = os.path.join(scripts, nombre)
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    if corte not in fuente:
        raise SystemExit(f"No se reconoce la estructura de {nombre}")
    sys.argv = [ruta, "--base", a.base, "--out", a.out, "--bd", a.bd]
    ns = {"__name__": "demo_original", "__file__": ruta}
    exec(compile(fuente.split(corte)[0], ruta, "exec"), ns)
    idx = int(cid[1:]) - 1
    if not 0 <= idx < len(ns["CASES"]):
        raise SystemExit(f"{cid} no existe en {nombre}")
    Ro = ns["R"]
    try:
        ns["CASES"][idx]()
    except Exception as ex:
        Ro.blocked(cid, "", "", cid, f"Error de preparacion: {ex}")
    tag = ns.get("TAG", "")
    extra["tag"] = tag
    extra["origen"] = f"codigo original de scripts/{nombre}"
    if tag:
        extra["sql"] = ("SELECT o.id, o.last_name, p.name AS mascota, p.birth_date, v.visit_date, v.description "
                        "FROM petclinic.owners o LEFT JOIN petclinic.pets p ON p.owner_id = o.id "
                        f"LEFT JOIN petclinic.visits v ON v.pet_id = p.id WHERE o.last_name LIKE '%{tag}';")
    return Ro


SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")


def mysql_consulta(sql):
    """Consulta de solo lectura con las credenciales de la sesion. Devuelve (filas, error)."""
    import re
    try:
        import pymysql
    except ImportError:
        return None, "falta pymysql"
    m = re.match(r"jdbc:mysql://([^:/]+)(?::(\d+))?/([^?]+)", os.environ.get("MYSQL_URL", ""))
    if not m:
        return None, "sin MYSQL_URL"
    try:
        con = pymysql.connect(host=m.group(1), port=int(m.group(2) or 3306), database=m.group(3),
                              user=os.environ.get("MYSQL_USER", ""), password=os.environ.get("MYSQL_PASS", ""),
                              connect_timeout=5)
        with con.cursor() as c:
            c.execute(sql)
            filas = c.fetchall()
        con.close()
        return filas, None
    except Exception as ex:
        return None, f"{type(ex).__name__}: {ex}"


def guardar(caso):
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "demo.json"), "w", encoding="utf-8") as f:
        json.dump({"caso": caso, "extra": extra}, f, ensure_ascii=False, indent=2)
    marca = {"Aprobado": "OK ", "Fallido": "FAIL", "Bloqueado": "BLOQ"}[caso["estado"]]
    print(f"[{marca}] {caso['id']} {caso['titulo']} -> {caso['obtenido']}")


def caso_carga():
    import csv
    import subprocess
    usuarios, segundos = 10, 30
    esperado = "p95 < 1000 ms y errores < 1 % (umbral propuesto por el equipo)"
    import importlib.util
    if importlib.util.find_spec("locust") is None:  # no se importa aqui: Locust parchea ssl con gevent
        guardar({"id": "CARGA", "titulo": "Carga basica", "esperado": esperado, "estado": "Bloqueado",
                 "obtenido": "Falta Locust en el entorno Python: ejecuta la opcion P"})
        return
    base_csv = os.path.join(a.out, "carga")
    cmd = [sys.executable, "-m", "locust", "-f", os.path.join(SCRIPTS, "locustfile.py"), "--headless",
           "-H", a.base, "-u", str(usuarios), "-r", "5", "-t", f"{segundos}s", "--only-summary",
           "--csv", base_csv, "--html", os.path.join(a.out, "carga.html")]
    with open(os.path.join(a.out, "locust.log"), "w", encoding="utf-8") as lg:
        subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, timeout=segundos + 120)
    fila = None
    try:
        with open(base_csv + "_stats.csv", encoding="utf-8") as fh:
            fila = next((r for r in csv.DictReader(fh) if r.get("Name") == "Aggregated"), None)
    except OSError:
        pass
    caso = {"id": "CARGA", "titulo": f"Carga basica: {usuarios} usuarios durante {segundos} s", "esperado": esperado}
    if not fila or int(fila["Request Count"]) == 0:
        caso.update(estado="Bloqueado", obtenido="Locust no produjo resultados; ver locust.log")
    else:
        n, fallos = int(fila["Request Count"]), int(fila["Failure Count"])
        p95, med, rps = float(fila["95%"]), float(fila["Median Response Time"]), float(fila["Requests/s"])
        pct = 100.0 * fallos / n
        caso.update(estado="Aprobado" if (p95 < 1000 and pct < 1) else "Fallido",
                    obtenido=f"{n} solicitudes; errores {fallos} ({pct:.2f} %); mediana {med:.0f} ms; "
                             f"p95 {p95:.0f} ms; {rps:.2f} solicitudes/s")
    extra["sql"] = "SELECT COUNT(*) FROM petclinic.owners WHERE last_name LIKE 'Perf%';"
    extra["nota"] = (f"Version corta ({usuarios} usuarios, {segundos} s). El informe uso 10 y 30 usuarios durante "
                     "180 s, asi que las cifras no son comparables una a una.")
    print("Resumen: " + caso["obtenido"])
    guardar(caso)


def caso_e01():
    import subprocess
    propietarios, k = 5, 4
    esperado = "Una mascota por propietario; el resto rechazado con error de validacion; ninguna fila sin propietario; sin HTTP 500"
    sql_h = "SELECT COUNT(*) FROM pets WHERE owner_id IS NULL"
    antes, err1 = mysql_consulta(sql_h)
    cmd = [sys.executable, os.path.join(SCRIPTS, "exploratorio_duplicado_concurrente.py"), "--base", a.base,
           "--out", a.out, "--bd", a.bd, "--owners", str(propietarios), "--k", str(k)]
    with open(os.path.join(a.out, "e01.log"), "w", encoding="utf-8") as lg:
        subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, timeout=300, cwd=SCRIPTS)
    despues, err2 = mysql_consulta(sql_h)
    caso = {"id": "E01", "titulo": f"Concurrencia: {k} altas simultaneas de la misma mascota en {propietarios} propietarios",
            "esperado": esperado}
    try:
        with open(os.path.join(a.out, "resultado.json"), encoding="utf-8") as fh:
            r = json.load(fh)
    except OSError:
        caso.update(estado="Bloqueado", obtenido="El script no produjo resultado.json; ver e01.log")
        guardar(caso)
        return
    conteo = r.get("conteo_respuestas", {})
    n500 = sum(v for kk, v in conteo.items() if kk.startswith("5"))
    multi = r.get("propietarios_con_mas_de_una", 0)
    if antes is not None and despues is not None:
        huer = despues[0][0] - antes[0][0]
        huer_txt = str(huer)
    else:
        huer, huer_txt = None, f"no verificado ({err1 or err2})"
    obt = f"respuestas={conteo}; propietarios con mas de una mascota={multi}; mascotas sin propietario nuevas={huer_txt}"
    if n500 > 0 or multi > 0 or (huer or 0) > 0:
        estado = "Fallido"
    elif huer is None:
        estado = "Bloqueado"
        obt += " (no se pudo comprobar en MySQL; resultado incompleto)"
    else:
        estado = "Aprobado"
    caso.update(estado=estado, obtenido=obt)
    extra["sql"] = "SELECT id, name, owner_id FROM petclinic.pets WHERE owner_id IS NULL;"
    extra["nota"] = (f"Version corta ({propietarios} propietarios x {k} envios). El informe uso 10 y 20 propietarios. "
                     "La concurrencia no es determinista: el defecto puede aparecer o no en una corrida corta.")
    print("Resumen: " + obt)
    guardar(caso)


os.makedirs(a.out, exist_ok=True)
if a.caso == "CARGA":
    caso_carga()
    sys.exit(0)
if a.caso == "E01":
    caso_e01()
    sys.exit(0)

if a.caso in ("F01", "S12"):
    R = Runner(a.base, a.out, f"demo_{a.caso}", a.bd)
    try:
        {"F01": f01, "S12": s12}[a.caso](R)
    except Exception as ex:  # error de ejecucion, no de criterio
        R.blocked(a.caso, "", "", a.caso, f"Error al ejecutar: {ex}")
else:
    R = caso_original(a.caso)
if a.caso == "F01":
    extra["mysql"] = confirmar_en_mysql(extra.get("owner_id"))
    print("Confirmacion en MySQL:", extra["mysql"])
R.finish(started)
with open(os.path.join(a.out, "demo.json"), "w", encoding="utf-8") as f:
    json.dump({"caso": next((x for x in R.results if x["id"] == a.caso), R.results[-1] if R.results else None), "extra": extra}, f, ensure_ascii=False, indent=2)

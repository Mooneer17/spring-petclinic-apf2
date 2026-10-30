"""Pruebas de seguridad basica APF2 (seccion 13). SOLO instancia local propia.

No realiza ataques de fuerza bruta, denegacion de servicio ni escaneos externos.
Uso: python3 seguridad_http.py --base http://localhost:8080 --out DIR --bd MySQL
"""
import argparse
import datetime as dt
import html
import re
import string
import time

from apf_common import Runner, wait_up

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://localhost:8080")
ap.add_argument("--out", required=True)
ap.add_argument("--bd", required=True)
a = ap.parse_args()
if not wait_up(a.base):
    raise SystemExit("La aplicacion no responde")

R = Runner(a.base, a.out, "seguridad_http", a.bd)
started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))
TOMORROW = (dt.date.today() + dt.timedelta(days=1)).isoformat()
LVL = "Seguridad basica HTTP"


def ln(c):
    return f"{c}{TAG}"


def leaks_trace(text):
    return bool(re.search(r"\bat (org|java|jakarta)\.[\w.$]+\(", text)) or "Exception:" in text


# S01 Autenticacion: rutas de lectura y escritura accesibles sin credenciales
def s01():
    paths = ["/", "/owners/find", "/owners?lastName=", "/owners/1", "/owners/1/edit", "/vets.html", "/owners/new"]
    rows = []
    for p in paths:
        r = R.get(p)
        rows.append(f"{p}={r.status_code}")
    ev = R.save("S01", "owners_new", R.get("/owners/new"))
    login = R.get("/login")
    R.save("S01", "login", login)
    anon = all(x.endswith("=200") for x in rows)
    R.record("S01", "Transversal", LVL, "Verificacion de autenticacion existente",
             "Peticiones anonimas sin cookies ni cabecera Authorization", "GET a rutas de consulta y formularios",
             "Determinar si la variante exige autenticacion (no se asume un resultado)",
             f"{'; '.join(rows)}; /login={login.status_code}",
             anon, ev, status="Observacion",
             notes=
             "La variante no implementa autenticacion ni autorizacion (pom.xml sin Spring Security). "
             "Se registra como observacion de alcance, no como aprobado ni como defecto.")


# S02 Exposicion de endpoints de Actuator
def s02():
    res = {}
    for p in ["/actuator", "/actuator/env", "/actuator/configprops", "/actuator/beans", "/actuator/mappings"]:
        r = R.get(p)
        res[p] = r.status_code
        if p in ("/actuator", "/actuator/env"):
            R.save("S02", p.strip("/").replace("/", "_"), r)
    hd = R.s.head(R.base + "/actuator/heapdump", allow_redirects=False, timeout=30)
    res["/actuator/heapdump(HEAD)"] = hd.status_code
    exposed = res["/actuator/env"] == 200
    R.record("S02", "Transversal", LVL, "Exposicion de endpoints de administracion (Actuator)",
             "Peticiones anonimas", "GET /actuator, /actuator/env y otros; HEAD /actuator/heapdump",
             "Endpoints sensibles no accesibles de forma anonima",
             "; ".join(f"{k}={v}" for k, v in res.items()), not exposed, "respuestas/S02_actuator.http.txt",
             "application.properties expone management.endpoints.web.exposure.include=* (indicado como solo para desarrollo).")


# S03 XSS almacenado en datos del propietario y de la mascota
def s03():
    payload = "<script>alert(1)</script>"
    r = R.post("/owners/new", R.owner_form(lastName=ln("Sx"), address=payload, city="<b>Lima</b>"))
    oid = R.owner_id_from(r)
    if not oid:
        R.record("S03", "RF01", LVL, "XSS almacenado", payload, "", "", f"Preparacion fallo HTTP {r.status_code}", False, "")
        return
    d = R.get(f"/owners/{oid}")
    ev = R.save("S03", "detalle", d)
    raw = payload in d.text
    esc = html.escape(payload, quote=False) in d.text or "&lt;script&gt;" in d.text
    R.record("S03", "RF01", LVL, "XSS almacenado en direccion y ciudad",
             f"address='{payload}', city='<b>Lima</b>'", "Registrar propietario; abrir detalle",
             "El contenido se muestra escapado; no aparece una etiqueta <script> ejecutable",
             f"etiqueta sin escapar={raw}; escapada={esc}", (not raw) and esc, ev)


# S04 Inyeccion SQL en la busqueda por apellido
def s04():
    out = []
    ok = True
    for i, p in enumerate(["' OR '1'='1", "x%' OR 1=1 --", "\" ; DROP TABLE owners; --"]):
        r = R.get("/owners", params={"lastName": p})
        R.save("S04", f"p{i}", r)
        nf = "has not been found" in r.text
        out.append(f"[{p}] HTTP {r.status_code} not_found={nf}")
        ok &= r.status_code == 200 and nf and not leaks_trace(r.text)
    after = R.get("/owners?lastName=Davis")
    out.append(f"tabla owners operativa={after.status_code in (200, 302)}")
    R.record("S04", "RF02", LVL, "Inyeccion SQL en lastName", "3 cargas tipicas de inyeccion",
             "GET /owners?lastName=<carga>", "Se tratan como texto: 200 'has not been found', sin trazas ni efectos",
             "; ".join(out), ok and after.status_code in (200, 302), "respuestas/S04_p0.http.txt")


# S05 Asignacion masiva del id al crear propietario
def s05():
    before = R.get("/owners/1").text
    r = R.post("/owners/new", {**R.owner_form(lastName=ln("Sm")), "id": "1"})
    ev = R.save("S05", "post", r)
    new_id = R.owner_id_from(r)
    after = R.get("/owners/1").text
    unchanged = ("George Franklin" in before) == ("George Franklin" in after) and ln("Sm") not in after
    R.record("S05", "RF01", LVL, "Asignacion masiva: id=1 enviado al crear propietario",
             "parametro adicional id=1", "POST /owners/new con id=1; consultar /owners/1",
             "Se crea un propietario nuevo; el propietario 1 no se modifica",
             f"HTTP {r.status_code}; nuevo id={new_id}; propietario 1 sin cambios={unchanged}",
             r.status_code == 302 and new_id not in (None, 1) and unchanged, ev)


# S06 Actualizacion de propietario con id distinto en el formulario
def s06():
    a_id = R.create_owner(ln("Sa"))
    b_id = R.create_owner(ln("Sb"))
    r = R.post(f"/owners/{a_id}/edit", {**R.owner_form(lastName=ln("Sa"), city="Cusco"), "id": str(b_id)})
    ev = R.save("S06", "post", r)
    a_page, b_page = R.owner_page(a_id), R.owner_page(b_id)
    ok = "Cusco" not in b_page
    R.record("S06", "RF03", LVL, "Manipulacion del id en la actualizacion del propietario",
             f"URL propietario A={a_id}; campo id=B={b_id}; ciudad Cusco", "POST /owners/A/edit con id=B",
             "El propietario B no se modifica", f"HTTP {r.status_code} -> {r.headers.get('Location','')}; "
             f"B modificado={'Cusco' in b_page}; A modificado={'Cusco' in a_page}", ok, ev)


# S07 Asociacion propietario-mascota en visitas
def s07():
    a_id = R.create_owner(ln("Sc"))
    b_id = R.create_owner(ln("Sd"))
    pb = R.create_pet(b_id, "Bruno")
    g = R.get(f"/owners/{a_id}/pets/{pb}/visits/new")
    R.save("S07", "get", g)
    r = R.post(f"/owners/{a_id}/pets/{pb}/visits/new", {"date": TOMORROW, "description": f"Cruzada {TAG}"})
    ev = R.save("S07", "post", r)
    leaked = f"Cruzada {TAG}" in R.owner_page(b_id) or f"Cruzada {TAG}" in R.owner_page(a_id)
    trace = leaks_trace(r.text) or leaks_trace(g.text)
    R.record("S07", "RF06", LVL, "Visita a una mascota que no pertenece al propietario de la URL",
             f"propietario A={a_id}; mascota de B={pb}", "GET y POST /owners/A/pets/{mascotaB}/visits/new",
             "Se rechaza la operacion; no se registra la visita; sin traza interna",
             f"GET HTTP {g.status_code}; POST HTTP {r.status_code}; visita registrada={leaked}; traza={trace}",
             (not leaked) and r.status_code >= 400 and not trace, ev,
             "VisitController lanza IllegalArgumentException si la mascota no pertenece al propietario.")


# S08 Edicion de una mascota de otro propietario
def s08():
    a_id = R.create_owner(ln("Se"))
    b_id = R.create_owner(ln("Sf"))
    pb = R.create_pet(b_id, "Bruno")
    g = R.get(f"/owners/{a_id}/pets/{pb}/edit")
    R.save("S08", "get", g)
    r = R.post(f"/owners/{a_id}/pets/{pb}/edit", {"name": "Hackeado", "birthDate": "2020-01-01", "type": "dog"})
    ev = R.save("S08", "post", r)
    b_page, a_page = R.owner_page(b_id), R.owner_page(a_id)
    b_changed = "Hackeado" in b_page or "<dd>Bruno</dd>" not in b_page
    a_gained = "Hackeado" in a_page
    trace = leaks_trace(r.text) or leaks_trace(g.text)
    R.record("S08", "RF05", LVL, "Edicion de una mascota que pertenece a otro propietario",
             f"propietario A={a_id}; mascota de B={pb}", "GET y POST /owners/A/pets/{mascotaB}/edit",
             "Se rechaza con un error controlado; la mascota de B no cambia; no se crean registros",
             f"GET HTTP {g.status_code}; POST HTTP {r.status_code}; mascota B modificada={b_changed}; "
             f"A recibio mascota={a_gained}; traza={trace}",
             (not b_changed) and (not a_gained) and r.status_code >= 400 and not trace, ev)


# S09 Recurso inexistente y divulgacion de informacion
def s09():
    r = R.get("/owners/999999")
    ev = R.save("S09", "get", r)
    trace = leaks_trace(r.text)
    msg = "Owner not found with id" in r.text
    R.record("S09", "RF02", LVL, "Propietario inexistente y divulgacion en la pagina de error",
             "ownerId=999999", "GET /owners/999999",
             "Error controlado sin traza de pila", f"HTTP {r.status_code}; traza={trace}; mensaje interno visible={msg}",
             not trace, ev,
             "Se registra si el mensaje de la excepcion se muestra al usuario (plantilla error.html imprime ${message}).")


# S10 Limites de longitud (entradas sobredimensionadas)
def s10():
    r1 = R.post("/owners/new", R.owner_form(lastName=ln("Sl"), address="A" * 256))
    r2 = R.post("/owners/new", R.owner_form(lastName=ln("Sk"), city="C" * 81))
    r3 = R.post("/owners/new", R.owner_form(lastName=ln("Sj"), address="A" * 20000))
    ev = R.save("S10", "address256", r1)
    R.save("S10", "city81", r2)
    R.save("S10", "address20000", r3)
    e1, e2, e3 = (R.has_field_error(r1.text, "address"), R.has_field_error(r2.text, "city"),
                  R.has_field_error(r3.text, "address"))
    R.record("S10", "RF01", LVL, "Entradas sobredimensionadas", "direccion 256 y 20000 caracteres; ciudad 81",
             "POST /owners/new", "200 con error de validacion; sin error 500 ni almacenamiento",
             f"256 -> {r1.status_code}/{e1}; ciudad 81 -> {r2.status_code}/{e2}; 20000 -> {r3.status_code}/{e3}",
             all(x.status_code == 200 for x in (r1, r2, r3)) and e1 and e2 and e3, ev)


# S11 Proteccion CSRF
def s11():
    f = R.get("/owners/new")
    token = "_csrf" in f.text
    r = R.s.post(R.base + "/owners/new", data=R.owner_form(lastName=ln("Sq")),
                 headers={"Origin": "http://sitio-externo.example", "Referer": "http://sitio-externo.example/"},
                 allow_redirects=False, timeout=30)
    ev = R.save("S11", "post_origen_externo", r)
    R.record("S11", "Transversal", LVL, "Proteccion CSRF en formularios",
             "POST con cabeceras Origin/Referer de otro sitio y sin token", "GET formulario; POST /owners/new",
             "Si la aplicacion protegiera contra CSRF, el POST sin token se rechazaria",
             f"token en formulario={token}; POST HTTP {r.status_code}", r.status_code >= 400, ev,
             "Sin autenticacion ni sesiones de usuario, el impacto se limita a altas o cambios no solicitados.")


# S12 Cabeceras de seguridad
def s12():
    r = R.get("/")
    ev = R.save("S12", "get", r)
    want = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Cache-Control"]
    present = {h: (h in r.headers) for h in want}
    R.record("S12", "Transversal", LVL, "Cabeceras de seguridad HTTP en la pagina principal", "GET /",
             "Inspeccionar cabeceras de respuesta", "Presencia de cabeceras defensivas basicas",
             "; ".join(f"{k}={v}" for k, v in present.items()), all(present.values()), ev)


# S13 Identificador de sesion en la URL (reescritura de URL)
def s13():
    import requests
    fresh = requests.Session()
    fresh.headers["Accept-Language"] = "en"
    r = fresh.post(R.base + "/owners/new", data=R.owner_form(lastName=ln("Sn")), allow_redirects=False, timeout=30)
    ev = R.save("S13", "post_sin_cookie", r)
    loc = r.headers.get("Location", "")
    in_url = ";jsessionid=" in loc.lower()
    R.record("S13", "Transversal", LVL, "Identificador de sesion expuesto en la URL de redireccion",
             "Cliente nuevo sin cookie de sesion", "POST /owners/new; inspeccionar Location",
             "La redireccion no incluye el identificador de sesion",
             f"HTTP {r.status_code}; Location contiene jsessionid={in_url}", not in_url, ev,
             "La sesion no protege cuentas porque no hay autenticacion; riesgo bajo en esta variante.")


CASES = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13]
for i, c in enumerate(CASES, 1):
    try:
        c()
    except Exception as ex:
        R.blocked(f"S{i:02d}", "", LVL, c.__name__, f"Error de preparacion: {ex}")
R.finish(started)

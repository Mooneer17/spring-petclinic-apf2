"""Pruebas funcionales APF2 (seccion 11) por HTTP real contra una instancia local.

Uso: python3 funcionales_http.py --base http://localhost:8080 --out DIR --bd MySQL
Cada caso prepara sus propios datos con un sufijo unico para no depender de otros casos.
"""
import argparse
import datetime as dt
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

R = Runner(a.base, a.out, "funcionales_http", a.bd)
started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
# sufijo alfabetico unico por corrida (los apellidos se buscan por prefijo)
n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))
TODAY = dt.date.today()
TOMORROW = TODAY + dt.timedelta(days=1)
YESTERDAY = TODAY - dt.timedelta(days=1)
LVL = "Funcional HTTP real"


def ln(case):
    return f"{case}{TAG}"


def loc(r):
    return re.sub(r";jsessionid=[^/?#]*", "", r.headers.get("Location", ""))


# ===================== RF01 Registrar propietario =====================
def f01():
    r = R.post("/owners/new", R.owner_form(lastName=ln("Fa")))
    ev = R.save("F01", "post", r)
    oid = R.owner_id_from(r)
    ok = r.status_code == 302 and oid is not None
    detail_ok = False
    if ok:
        d = R.get(f"/owners/{oid}")
        R.save("F01", "detalle", d)
        detail_ok = ln("Fa") in d.text and "9876543210" in d.text and "Av. Central 123" in d.text
    R.record("F01", "RF01", LVL, "Registro de propietario con datos validos",
             "Ana Torres, Av. Central 123, Lima, 9876543210",
             "POST /owners/new; seguir la redireccion y consultar el detalle",
             "302 a /owners/{id}; el detalle muestra los datos registrados",
             f"HTTP {r.status_code} -> {loc(r)}; detalle con datos={detail_ok}", ok and detail_ok, ev)


def phone_case(cid, phone, label):
    before = R.get(f"/owners?lastName={ln(cid)}")
    r = R.post("/owners/new", R.owner_form(lastName=ln(cid), telephone=phone))
    ev = R.save(cid, "post", r)
    err = R.has_field_error(r.text, "telephone")
    after = R.get(f"/owners?lastName={ln(cid)}")
    not_saved = after.status_code == 200 and "has not been found" in after.text
    R.record(cid, "RF01", LVL, f"Registro rechazado: telefono {label}", f"telefono='{phone}'",
             "POST /owners/new; buscar el apellido usado",
             "200 con error en 'telephone'; el propietario no se guarda",
             f"HTTP {r.status_code}; error telephone={err}; no guardado={not_saved}",
             r.status_code == 200 and err and not_saved, ev)


def f05():
    r = R.post("/owners/new", R.owner_form(lastName=ln("Fe"), address="", city="  "))
    ev = R.save("F05", "post", r)
    ea, ec = R.has_field_error(r.text, "address"), R.has_field_error(r.text, "city")
    R.record("F05", "RF01", LVL, "Registro rechazado: direccion vacia y ciudad en blanco",
             "address='', city='  '", "POST /owners/new",
             "200 con error en address y city", f"HTTP {r.status_code}; address={ea}; city={ec}",
             r.status_code == 200 and ea and ec, ev)


def f06():
    # limite: 30 caracteres en apellido (aceptado) y 31 (rechazado)
    ok30 = ("A" * (30 - len(TAG))) + TAG
    r1 = R.post("/owners/new", R.owner_form(lastName=ok30))
    e1 = R.save("F06", "30car", r1)
    r2 = R.post("/owners/new", R.owner_form(lastName="B" * 31))
    e2 = R.save("F06", "31car", r2)
    err31 = R.has_field_error(r2.text, "lastName")
    R.record("F06", "RF01", LVL, "Limite de longitud del apellido (30/31)",
             "apellido de 30 y de 31 caracteres", "POST /owners/new dos veces",
             "30 caracteres: 302; 31 caracteres: 200 con error en lastName",
             f"30 -> HTTP {r1.status_code}; 31 -> HTTP {r2.status_code}, error={err31}",
             r1.status_code == 302 and r2.status_code == 200 and err31, f"{e1}; {e2}")


# ===================== RF02 Buscar por apellido =====================
def f07():
    oid = R.create_owner(ln("Fg"))
    r = R.get(f"/owners?lastName={ln('Fg')}")
    ev = R.save("F07", "get", r)
    R.record("F07", "RF02", LVL, "Busqueda con coincidencia unica", f"apellido={ln('Fg')}",
             "GET /owners?lastName=...", f"302 a /owners/{oid}",
             f"HTTP {r.status_code} -> {loc(r)}", r.status_code == 302 and loc(r).endswith(f"/owners/{oid}"), ev)


def f08():
    R.create_owner(ln("Fh") + "x")
    R.create_owner(ln("Fh") + "y")
    r = R.get(f"/owners?lastName={ln('Fh')}")
    ev = R.save("F08", "get", r)
    both = (ln("Fh") + "x") in r.text and (ln("Fh") + "y") in r.text
    R.record("F08", "RF02", LVL, "Busqueda por prefijo con varias coincidencias",
             f"prefijo={ln('Fh')} (2 propietarios)", "GET /owners?lastName=prefijo",
             "200 con lista que incluye ambos propietarios", f"HTTP {r.status_code}; ambos listados={both}",
             r.status_code == 200 and both, ev)


def f09():
    r = R.get(f"/owners?lastName=Inexistente{TAG}")
    ev = R.save("F09", "get", r)
    nf = "has not been found" in r.text
    R.record("F09", "RF02", LVL, "Busqueda sin resultados", f"apellido=Inexistente{TAG}",
             "GET /owners?lastName=...", "200 con mensaje 'has not been found'",
             f"HTTP {r.status_code}; mensaje={nf}", r.status_code == 200 and nf, ev)


def f10():
    oid = R.create_owner(ln("Fj"))
    r = R.get(f"/owners?lastName=%20%20{ln('Fj')}%20")
    ev = R.save("F10", "get", r)
    R.record("F10", "RF02", LVL, "Busqueda con espacios al inicio y al final",
             f"apellido='  {ln('Fj')} '", "GET /owners?lastName= con espacios",
             f"Se recortan espacios: 302 a /owners/{oid}", f"HTTP {r.status_code} -> {loc(r)}",
             r.status_code == 302 and loc(r).endswith(f"/owners/{oid}"), ev)


def f11():
    r = R.get("/owners?lastName=")
    ev = R.save("F11", "get", r)
    paginated = 'id="owners"' in r.text and 'href="/owners?page=2"' in r.text
    R.record("F11", "RF02", LVL, "Busqueda con apellido vacio (todos)", "lastName=''",
             "GET /owners?lastName=", "200 con listado paginado de propietarios",
             f"HTTP {r.status_code}; listado paginado={paginated}", r.status_code == 200 and paginated, ev)


# ===================== RF03 Actualizar propietario =====================
def f12():
    oid = R.create_owner(ln("Fl"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fl"), telephone="9123456780", city="Arequipa"))
    ev = R.save("F12", "post", r)
    d = R.get(f"/owners/{oid}")
    R.save("F12", "detalle", d)
    persisted = "9123456780" in d.text and "Arequipa" in d.text
    R.record("F12", "RF03", LVL, "Actualizacion valida de telefono y ciudad",
             "telefono 9123456780, ciudad Arequipa", "POST /owners/{id}/edit; consultar detalle",
             "302 al detalle; se muestran los nuevos valores con el mismo id",
             f"HTTP {r.status_code} -> {loc(r)}; persistido={persisted}",
             r.status_code == 302 and loc(r).endswith(f"/owners/{oid}") and persisted, ev)


def f13():
    oid = R.create_owner(ln("Fm"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fm"), telephone="12345"))
    ev = R.save("F13", "post", r)
    err = R.has_field_error(r.text, "telephone")
    d = R.get(f"/owners/{oid}").text
    unchanged = "9876543210" in d and ">12345<" not in d
    R.record("F13", "RF03", LVL, "Actualizacion rechazada: telefono de 5 digitos", "telefono=12345",
             "POST /owners/{id}/edit; consultar detalle",
             "200 con error en telephone; se conserva el telefono anterior",
             f"HTTP {r.status_code}; error={err}; sin cambios={unchanged}",
             r.status_code == 200 and err and unchanged, ev)


def f14():
    oid = R.create_owner(ln("Fn"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fn"), firstName=""))
    ev = R.save("F14", "post", r)
    err = R.has_field_error(r.text, "firstName")
    d = R.get(f"/owners/{oid}").text
    R.record("F14", "RF03", LVL, "Actualizacion rechazada: nombre vacio", "firstName=''",
             "POST /owners/{id}/edit", "200 con error en firstName; datos sin cambios",
             f"HTTP {r.status_code}; error={err}; nombre conservado={'Ana ' + ln('Fn') in d}",
             r.status_code == 200 and err and ("Ana " + ln("Fn")) in d, ev)


# ===================== RF04 Registrar mascota =====================
def f15():
    oid = R.create_owner(ln("Fo"))
    r = R.post(f"/owners/{oid}/pets/new", {"name": "Luna", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F15", "post", r)
    pid = R.pet_id(oid, "Luna")
    d = R.get(f"/owners/{oid}")
    R.save("F15", "detalle", d)
    ok = r.status_code == 302 and pid is not None and "2022-05-10" in d.text
    R.record("F15", "RF04", LVL, "Registro de mascota valida", "Luna, 2022-05-10, cat",
             "POST /owners/{id}/pets/new; consultar detalle del propietario",
             "302; la mascota aparece asociada al propietario con sus datos",
             f"HTTP {r.status_code}; petId={pid}", ok, ev)


def pet_reject(cid, req, title, form, field, data_desc, expected_extra=""):
    oid = R.create_owner(ln(cid))
    r = R.post(f"/owners/{oid}/pets/new", form)
    ev = R.save(cid, "post", r)
    err = R.has_field_error(r.text, field)
    R.record(cid, req, LVL, title, data_desc, "POST /owners/{id}/pets/new",
             f"200 con error en {field}{expected_extra}", f"HTTP {r.status_code}; error {field}={err}",
             r.status_code == 200 and err, ev)


def f17():
    oid = R.create_owner(ln("Fq"))
    R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/new", {"name": "LUNA", "birthDate": "2023-01-01", "type": "dog"})
    ev = R.save("F17", "post", r)
    err = R.has_field_error(r.text, "name")
    count = R.owner_page(oid).lower().count("<dd>luna</dd>")
    R.record("F17", "RF04", LVL, "Registro rechazado: nombre duplicado (distinta capitalizacion)",
             "Luna existente; nueva 'LUNA'", "Crear Luna; POST otra mascota 'LUNA'",
             "200 con error en name; sigue existiendo una sola mascota",
             f"HTTP {r.status_code}; error={err}; mascotas con ese nombre={count}",
             r.status_code == 200 and err and count == 1, ev)


def f19():
    oid = R.create_owner(ln("Fs"))
    r = R.post(f"/owners/{oid}/pets/new", {"name": "Hoy", "birthDate": TODAY.isoformat(), "type": "dog"})
    ev = R.save("F19", "post", r)
    R.record("F19", "RF04", LVL, "Limite: fecha de nacimiento igual a hoy", f"birthDate={TODAY}",
             "POST /owners/{id}/pets/new", "302 (la regla solo rechaza fechas posteriores a hoy)",
             f"HTTP {r.status_code}", r.status_code == 302 and R.pet_id(oid, "Hoy") is not None, ev)


def f20():
    oid = R.create_owner(ln("Ft"))
    n30 = "N" * 30
    r1 = R.post(f"/owners/{oid}/pets/new", {"name": n30, "birthDate": "2022-05-10", "type": "dog"})
    e1 = R.save("F20", "30car", r1)
    r2 = R.post(f"/owners/{oid}/pets/new", {"name": "M" * 31, "birthDate": "2022-05-10", "type": "dog"})
    e2 = R.save("F20", "31car", r2)
    err = R.has_field_error(r2.text, "name")
    R.record("F20", "RF04", LVL, "Limite de longitud del nombre de mascota (30/31)",
             "nombre de 30 y de 31 caracteres", "POST /owners/{id}/pets/new dos veces",
             "30: 302; 31: 200 con error en name", f"30 -> HTTP {r1.status_code}; 31 -> HTTP {r2.status_code}, error={err}",
             r1.status_code == 302 and r2.status_code == 200 and err, f"{e1}; {e2}")


# ===================== RF05 Actualizar mascota =====================
def f22():
    oid = R.create_owner(ln("Fv"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Lunita", "birthDate": "2021-03-15", "type": "dog"})
    ev = R.save("F22", "post", r)
    d = R.get(f"/owners/{oid}")
    R.save("F22", "detalle", d)
    same = R.pet_id(oid, "Lunita") == pid
    ok = r.status_code == 302 and same and "2021-03-15" in d.text and "<dd>dog</dd>" in d.text
    R.record("F22", "RF05", LVL, "Edicion valida de nombre, tipo y fecha", "Luna->Lunita, cat->dog, 2021-03-15",
             "POST /owners/{o}/pets/{p}/edit; consultar detalle",
             "302; la misma mascota (mismo id) muestra los nuevos datos",
             f"HTTP {r.status_code}; mismo id={same}", ok, ev)


def f23():
    oid = R.create_owner(ln("Fw"))
    R.create_pet(oid, "Luna")
    pid = R.create_pet(oid, "Max")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Luna", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F23", "post", r)
    err = R.has_field_error(r.text, "name")
    still = R.pet_id(oid, "Max") == pid
    R.record("F23", "RF05", LVL, "Edicion rechazada: renombrar a un nombre ya usado", "Max -> Luna (existente)",
             "POST /owners/{o}/pets/{p}/edit", "200 con error en name; Max conserva su nombre",
             f"HTTP {r.status_code}; error={err}; Max sin cambios={still}",
             r.status_code == 200 and err and still, ev)


def f24():
    oid = R.create_owner(ln("Fx"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Luna", "birthDate": TOMORROW.isoformat(), "type": "cat"})
    ev = R.save("F24", "post", r)
    err = R.has_field_error(r.text, "birthDate")
    kept = "2022-05-10" in R.owner_page(oid)
    R.record("F24", "RF05", LVL, "Edicion rechazada: fecha de nacimiento futura", f"birthDate={TOMORROW}",
             "POST /owners/{o}/pets/{p}/edit", "200 con error en birthDate; se conserva la fecha anterior",
             f"HTTP {r.status_code}; error={err}; fecha conservada={kept}", r.status_code == 200 and err and kept, ev)


def f25():
    oid = R.create_owner(ln("Fy"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F25", "post", r)
    err = R.has_field_error(r.text, "name")
    kept = R.pet_id(oid, "Luna") == pid
    R.record("F25", "RF05", LVL, "Edicion rechazada: nombre vacio (persistencia, complementa CP05)", "name=''",
             "POST /owners/{o}/pets/{p}/edit; consultar detalle",
             "200 con error en name; la mascota conserva su nombre", f"HTTP {r.status_code}; error={err}; conservado={kept}",
             r.status_code == 200 and err and kept, ev)


# ===================== RF06 Registrar visita =====================
def visit_setup(cid):
    oid = R.create_owner(ln(cid))
    pid = R.create_pet(oid, "Luna")
    return oid, pid


def f26():
    oid, pid = visit_setup("Fz")
    r = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": "Control general"})
    ev = R.save("F26", "post", r)
    d = R.get(f"/owners/{oid}")
    R.save("F26", "detalle", d)
    shown = TOMORROW.isoformat() in d.text and "Control general" in d.text
    R.record("F26", "RF06", LVL, "Registro de visita valida (manana)", f"fecha={TOMORROW}, 'Control general'",
             "POST /owners/{o}/pets/{p}/visits/new; consultar detalle",
             "302 al propietario; la visita aparece en la mascota", f"HTTP {r.status_code}; visita visible={shown}",
             r.status_code == 302 and shown, ev)


def visit_reject(cid, title, date, desc, field, data_desc):
    oid, pid = visit_setup(cid)
    r = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": date, "description": desc})
    ev = R.save(cid, "post", r)
    err = R.has_field_error(r.text, field)
    not_saved = f"<td>{date}</td>" not in R.owner_page(oid)
    R.record(cid, "RF06", LVL, title, data_desc, "POST /owners/{o}/pets/{p}/visits/new; consultar detalle",
             f"200 con error en {field}; no se registra la visita",
             f"HTTP {r.status_code}; error {field}={err}; no registrada={not_saved}",
             r.status_code == 200 and err and not_saved, ev)


def f31():
    oid, pid = visit_setup("Gd")
    d255 = "D" * 255
    r1 = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": d255})
    e1 = R.save("F31", "255car", r1)
    r2 = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": "E" * 256})
    e2 = R.save("F31", "256car", r2)
    err = R.has_field_error(r2.text, "description")
    R.record("F31", "RF06", LVL, "Limite de longitud de la descripcion (255/256)",
             "descripcion de 255 y de 256 caracteres", "POST visita dos veces",
             "255: 302; 256: 200 con error en description",
             f"255 -> HTTP {r1.status_code}; 256 -> HTTP {r2.status_code}, error={err}",
             r1.status_code == 302 and r2.status_code == 200 and err, f"{e1}; {e2}")


CASES = [
    f01,
    lambda: phone_case("F02", "987654321", "de 9 digitos"),
    lambda: phone_case("F03", "98765432101", "de 11 digitos"),
    lambda: phone_case("F04", "98765abcde", "con letras"),
    f05, f06, f07, f08, f09, f10, f11, f12, f13, f14, f15,
    lambda: pet_reject("F16", "RF04", "Registro rechazado: nombre vacio",
                       {"name": "", "birthDate": "2022-05-10", "type": "cat"}, "name", "name=''"),
    f17,
    lambda: pet_reject("F18", "RF04", "Registro rechazado: nacimiento futuro (manana)",
                       {"name": "Futuro", "birthDate": TOMORROW.isoformat(), "type": "cat"}, "birthDate",
                       f"birthDate={TOMORROW}"),
    f19, f20,
    lambda: pet_reject("F21", "RF04", "Registro rechazado: sin fecha de nacimiento",
                       {"name": "SinFecha", "birthDate": "", "type": "cat"}, "birthDate", "birthDate=''"),
    f22, f23, f24, f25, f26,
    lambda: visit_reject("F27", "Visita rechazada: fecha de hoy (limite)", TODAY.isoformat(), "Hoy", "date",
                         f"fecha={TODAY}"),
    lambda: visit_reject("F28", "Visita rechazada: fecha pasada", YESTERDAY.isoformat(), "Ayer", "date",
                         f"fecha={YESTERDAY}"),
    lambda: visit_reject("F29", "Visita rechazada: descripcion vacia", TOMORROW.isoformat(), "", "description",
                         "descripcion=''"),
    lambda: visit_reject("F30", "Visita rechazada: descripcion solo con espacios", TOMORROW.isoformat(), "   ",
                         "description", "descripcion='   '"),
    f31,
]

IDS = [f"F{i:02d}" for i in range(1, len(CASES) + 1)]
for cid, c in zip(IDS, CASES):
    try:
        c()
    except Exception as ex:  # una falla de preparacion bloquea el caso, no lo aprueba
        R.blocked(cid, "", LVL, cid, f"Error de preparacion: {ex}")

R.finish(started)

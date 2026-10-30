"""Pruebas funcionales APF2 (seccion 11) por HTTP real contra una instancia local. Version 2.

Cambios respecto de la version 1 (corridas 1 y 2):
- Verifica el mensaje exacto mostrado (error de campo o mensaje de exito), ademas del
  codigo HTTP y de la persistencia.
- Sigue cada redireccion de inmediato, para que el mensaje de exito de una operacion previa
  no aparezca en la pagina de otro caso.
Los mensajes esperados provienen del codigo evaluado (anotaciones de validacion,
PetValidator, controladores y messages.properties).

Uso: python3 funcionales_http.py --base http://localhost:8080 --out DIR --bd MySQL
"""
import argparse
import datetime as dt
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

R = Runner(a.base, a.out, "funcionales_http_v2", a.bd)
started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))
TODAY = dt.date.today()
TOMORROW = TODAY + dt.timedelta(days=1)
YESTERDAY = TODAY - dt.timedelta(days=1)
LVL = "Funcional HTTP real"

# Mensajes esperados (fuente: codigo del commit evaluado)
M_PHONE = "Telephone must be a 10-digit number"      # Owner @Pattern + telephone.invalid
M_BLANK = "must not be blank"                         # @NotBlank (Bean Validation)
M_SIZE30 = "size must be between 0 and 30"            # Person @Size(max = 30)
M_SIZE255 = "size must be between 0 and 255"          # Visit @Size(max = 255)
M_REQUIRED = "is required"                            # PetValidator / messages.properties
M_DUP = "is already in use"                           # PetController 'duplicate'
M_PETNAME30 = "Name must be no more than 30 characters"  # PetValidator
M_BIRTH = "invalid date"                              # typeMismatch.birthDate
M_VISIT = "Visit date must be in the future"          # typeMismatch.visitDate
F_OWNER_NEW, F_OWNER_UPD = "New Owner Created", "Owner Values Updated"
F_PET_NEW, F_PET_UPD, F_VISIT = "New Pet has been Added", "Pet details has been edited", "Your visit has been booked"


def ln(c):
    return f"{c}{TAG}"


def steps(*xs):
    return " ".join(f"{i}) {x}" for i, x in enumerate(xs, 1))


def reject_check(cid, resp, field, msg):
    got = R.field_error_msg(resp.text, field)
    return got == msg, f"mensaje en {field}='{got}'"


# ===================== RF01 =====================
def f01():
    r = R.post("/owners/new", R.owner_form(lastName=ln("Fa")))
    ev = R.save("F01", "post", r)
    oid = R.owner_id_from(r)
    d = R.follow(r)
    R.save("F01", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    data = d is not None and all(x in d.text for x in (ln("Fa"), "9876543210", "Av. Central 123", "Lima"))
    R.record("F01", "RF01", LVL, "Registro de propietario con datos válidos",
             "Ana Torres, Av. Central 123, Lima, 9876543210",
             steps("Enviar POST /owners/new con los datos.", "Seguir la redirección al detalle.",
                   "Verificar mensaje y datos mostrados."),
             f"302 a /owners/{{id}}; mensaje '{F_OWNER_NEW}'; el detalle muestra los datos registrados",
             f"HTTP {r.status_code}, id={oid}; mensaje='{fl}'; datos={'sí' if data else 'no'}",
             r.status_code == 302 and oid is not None and fl == F_OWNER_NEW and data, ev)


def phone_case(cid, phone, label):
    r = R.post("/owners/new", R.owner_form(lastName=ln(cid), telephone=phone))
    ev = R.save(cid, "post", r)
    ok_msg, txt = reject_check(cid, r, "telephone", M_PHONE)
    after = R.get(f"/owners?lastName={ln(cid)}")
    not_saved = "has not been found" in after.text
    R.record(cid, "RF01", LVL, f"Registro rechazado: teléfono {label}", f"teléfono='{phone}'",
             steps("Enviar POST /owners/new con el teléfono indicado.", "Verificar el mensaje del campo.",
                   "Buscar el apellido usado para confirmar que no se guardó."),
             f"200 con '{M_PHONE}' en telephone; el propietario no se guarda",
             f"HTTP {r.status_code}; {txt}; no guardado={'sí' if not_saved else 'no'}",
             r.status_code == 200 and ok_msg and not_saved, ev)


def f05():
    r = R.post("/owners/new", R.owner_form(lastName=ln("Fe"), address="", city="  "))
    ev = R.save("F05", "post", r)
    a1, t1 = reject_check("F05", r, "address", M_BLANK)
    a2, t2 = reject_check("F05", r, "city", M_BLANK)
    not_saved = "has not been found" in R.get(f"/owners?lastName={ln('Fe')}").text
    R.record("F05", "RF01", LVL, "Registro rechazado: dirección vacía y ciudad en blanco", "address='', city='  '",
             steps("Enviar POST /owners/new con dirección vacía y ciudad con espacios.", "Verificar ambos mensajes.",
                   "Buscar el apellido usado."),
             f"200 con '{M_BLANK}' en address y city; no se guarda",
             f"HTTP {r.status_code}; {t1}; {t2}; no guardado={'sí' if not_saved else 'no'}",
             r.status_code == 200 and a1 and a2 and not_saved, ev)


def f06():
    ok30 = ("A" * (30 - len(TAG))) + TAG
    r1 = R.post("/owners/new", R.owner_form(lastName=ok30))
    e1 = R.save("F06", "30car", r1)
    R.follow(r1)
    b31 = "B" * 26 + TAG
    r2 = R.post("/owners/new", R.owner_form(lastName=b31))
    e2 = R.save("F06", "31car", r2)
    ok_msg, txt = reject_check("F06", r2, "lastName", M_SIZE30)
    R.record("F06", "RF01", LVL, "Límite de longitud del apellido (30/31)", "apellido de 30 y de 31 caracteres",
             steps("Enviar POST /owners/new con apellido de 30 caracteres.", "Repetir con 31 caracteres.",
                   "Verificar respuesta y mensaje."),
             f"30: 302; 31: 200 con '{M_SIZE30}' en lastName",
             f"30 -> HTTP {r1.status_code}; 31 -> HTTP {r2.status_code}, {txt}",
             r1.status_code == 302 and r2.status_code == 200 and ok_msg, f"{e1}; {e2}")


# ===================== RF02 =====================
def f07():
    oid = R.create_owner(ln("Fg"))
    r = R.get(f"/owners?lastName={ln('Fg')}")
    ev = R.save("F07", "get", r)
    d = R.follow(r)
    shown = d is not None and ln("Fg") in d.text
    R.record("F07", "RF02", LVL, "Búsqueda con coincidencia única", f"apellido={ln('Fg')}",
             steps("Crear un propietario con apellido único.", "GET /owners?lastName=<apellido>.",
                   "Seguir la redirección y verificar el propietario mostrado."),
             f"302 al detalle del propietario {{id}}, que muestra su apellido",
             f"HTTP {r.status_code} -> /owners/{R.owner_id_from(r)}; apellido en detalle={'sí' if shown else 'no'}",
             r.status_code == 302 and R.owner_id_from(r) == oid and shown, ev)


def f08():
    R.create_owner(ln("Fh") + "x")
    R.create_owner(ln("Fh") + "y")
    r = R.get(f"/owners?lastName={ln('Fh')}")
    ev = R.save("F08", "get", r)
    both = (ln("Fh") + "x") in r.text and (ln("Fh") + "y") in r.text
    R.record("F08", "RF02", LVL, "Búsqueda por prefijo con varias coincidencias", f"prefijo={ln('Fh')} (2 propietarios)",
             steps("Crear dos propietarios con el mismo prefijo de apellido.", "GET /owners?lastName=<prefijo>.",
                   "Verificar que la lista incluye ambos."),
             "200 con lista que incluye ambos propietarios", f"HTTP {r.status_code}; ambos listados={'sí' if both else 'no'}",
             r.status_code == 200 and both, ev)


def f09():
    r = R.get(f"/owners?lastName=Inexistente{TAG}")
    ev = R.save("F09", "get", r)
    got = R.field_error_msg(r.text, "lastName")
    nf = "has not been found" in r.text
    R.record("F09", "RF02", LVL, "Búsqueda sin resultados", f"apellido=Inexistente{TAG}",
             steps("GET /owners?lastName=<apellido inexistente>.", "Verificar el mensaje mostrado."),
             "200 con mensaje 'has not been found'", f"HTTP {r.status_code}; mensaje presente={'sí' if nf else 'no'}",
             r.status_code == 200 and nf, ev)


def f10():
    oid = R.create_owner(ln("Fj"))
    r = R.get(f"/owners?lastName=%20%20{ln('Fj')}%20")
    ev = R.save("F10", "get", r)
    R.follow(r)
    R.record("F10", "RF02", LVL, "Búsqueda con espacios al inicio y al final", f"apellido='  {ln('Fj')} '",
             steps("Crear un propietario.", "GET /owners?lastName= con espacios alrededor del apellido.",
                   "Verificar la redirección."),
             "Se recortan los espacios: 302 al detalle del propietario creado",
             f"HTTP {r.status_code} -> /owners/{R.owner_id_from(r)}",
             r.status_code == 302 and R.owner_id_from(r) == oid, ev)


def f11():
    r = R.get("/owners?lastName=")
    ev = R.save("F11", "get", r)
    paginated = 'id="owners"' in r.text and 'href="/owners?page=2"' in r.text
    R.record("F11", "RF02", LVL, "Búsqueda con apellido vacío (todos)", "lastName=''",
             steps("GET /owners?lastName= (vacío).", "Verificar tabla de propietarios y enlace a la página 2."),
             "200 con listado paginado de propietarios", f"HTTP {r.status_code}; listado paginado={'sí' if paginated else 'no'}",
             r.status_code == 200 and paginated, ev)


# ===================== RF03 =====================
def f12():
    oid = R.create_owner(ln("Fl"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fl"), telephone="9123456780", city="Arequipa"))
    ev = R.save("F12", "post", r)
    d = R.follow(r)
    R.save("F12", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    persisted = d is not None and "9123456780" in d.text and "Arequipa" in d.text
    R.record("F12", "RF03", LVL, "Actualización válida de teléfono y ciudad", "teléfono 9123456780, ciudad Arequipa",
             steps("Crear un propietario.", "POST /owners/{id}/edit con los nuevos valores.",
                   "Seguir la redirección y verificar mensaje y datos."),
             f"302 al mismo propietario; mensaje '{F_OWNER_UPD}'; se muestran los nuevos valores",
             f"HTTP {r.status_code} -> /owners/{R.owner_id_from(r)}; mensaje='{fl}'; persistido={'sí' if persisted else 'no'}",
             r.status_code == 302 and R.owner_id_from(r) == oid and fl == F_OWNER_UPD and persisted, ev)


def f13():
    oid = R.create_owner(ln("Fm"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fm"), telephone="12345"))
    ev = R.save("F13", "post", r)
    ok_msg, txt = reject_check("F13", r, "telephone", M_PHONE)
    d = R.owner_page(oid)
    unchanged = "9876543210" in d
    R.record("F13", "RF03", LVL, "Actualización rechazada: teléfono de 5 dígitos", "teléfono=12345",
             steps("Crear un propietario.", "POST /owners/{id}/edit con teléfono 12345.", "Verificar el mensaje.",
                   "Consultar el detalle."),
             f"200 con '{M_PHONE}'; se conserva el teléfono anterior",
             f"HTTP {r.status_code}; {txt}; teléfono conservado={'sí' if unchanged else 'no'}",
             r.status_code == 200 and ok_msg and unchanged, ev)


def f14():
    oid = R.create_owner(ln("Fn"))
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln("Fn"), firstName=""))
    ev = R.save("F14", "post", r)
    ok_msg, txt = reject_check("F14", r, "firstName", M_BLANK)
    kept = ("Ana " + ln("Fn")) in R.owner_page(oid)
    R.record("F14", "RF03", LVL, "Actualización rechazada: nombre vacío", "firstName=''",
             steps("Crear un propietario.", "POST /owners/{id}/edit con nombre vacío.", "Verificar el mensaje.",
                   "Consultar el detalle."),
             f"200 con '{M_BLANK}' en firstName; datos sin cambios",
             f"HTTP {r.status_code}; {txt}; nombre conservado={'sí' if kept else 'no'}",
             r.status_code == 200 and ok_msg and kept, ev)


# ===================== RF04 =====================
def f15():
    oid = R.create_owner(ln("Fo"))
    r = R.post(f"/owners/{oid}/pets/new", {"name": "Luna", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F15", "post", r)
    d = R.follow(r)
    R.save("F15", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    pid = R.pet_id(oid, "Luna")
    data = d is not None and "2022-05-10" in d.text and "<dd>cat</dd>" in d.text
    R.record("F15", "RF04", LVL, "Registro de mascota válida", "Luna, 2022-05-10, cat",
             steps("Crear un propietario.", "POST /owners/{id}/pets/new con los datos.",
                   "Seguir la redirección y verificar mensaje y mascota asociada."),
             f"302; mensaje '{F_PET_NEW}'; la mascota aparece asociada con nombre, fecha y tipo",
             f"HTTP {r.status_code}; mensaje='{fl}'; petId={pid}; datos={'sí' if data else 'no'}",
             r.status_code == 302 and fl == F_PET_NEW and pid is not None and data, ev)


def pet_reject(cid, title, form, field, msg, data_desc):
    oid = R.create_owner(ln(cid))
    r = R.post(f"/owners/{oid}/pets/new", form)
    ev = R.save(cid, "post", r)
    ok_msg, txt = reject_check(cid, r, field, msg)
    none = "dl-horizontal" not in R.owner_page(oid)
    R.record(cid, "RF04", LVL, title, data_desc,
             steps("Crear un propietario.", "POST /owners/{id}/pets/new con el dato indicado.", "Verificar el mensaje.",
                   "Consultar el detalle del propietario."),
             f"200 con '{msg}' en {field}; no se registra la mascota",
             f"HTTP {r.status_code}; {txt}; sin mascota registrada={'sí' if none else 'no'}",
             r.status_code == 200 and ok_msg and none, ev)


def f17():
    oid = R.create_owner(ln("Fq"))
    R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/new", {"name": "LUNA", "birthDate": "2023-01-01", "type": "dog"})
    ev = R.save("F17", "post", r)
    ok_msg, txt = reject_check("F17", r, "name", M_DUP)
    count = R.owner_page(oid).lower().count("<dd>luna</dd>")
    R.record("F17", "RF04", LVL, "Registro rechazado: nombre duplicado (distinta capitalización)",
             "Luna existente; nueva 'LUNA'",
             steps("Crear un propietario con la mascota Luna.", "POST otra mascota con nombre 'LUNA'.",
                   "Verificar el mensaje.", "Contar las mascotas con ese nombre."),
             f"200 con '{M_DUP}' en name; sigue existiendo una sola mascota",
             f"HTTP {r.status_code}; {txt}; mascotas con ese nombre={count}",
             r.status_code == 200 and ok_msg and count == 1, ev)


def f19():
    oid = R.create_owner(ln("Fs"))
    r = R.post(f"/owners/{oid}/pets/new", {"name": "Hoy", "birthDate": TODAY.isoformat(), "type": "dog"})
    ev = R.save("F19", "post", r)
    d = R.follow(r)
    fl = R.flash(d.text) if d is not None else None
    R.record("F19", "RF04", LVL, "Límite: fecha de nacimiento igual a hoy", f"birthDate={TODAY}",
             steps("Crear un propietario.", "POST /owners/{id}/pets/new con fecha de hoy.",
                   "Seguir la redirección y verificar mensaje y mascota."),
             f"302 y mensaje '{F_PET_NEW}' (la regla solo rechaza fechas posteriores a hoy)",
             f"HTTP {r.status_code}; mensaje='{fl}'",
             r.status_code == 302 and fl == F_PET_NEW and R.pet_id(oid, "Hoy") is not None, ev)


def f20():
    oid = R.create_owner(ln("Ft"))
    n30 = "N" * 30
    r1 = R.post(f"/owners/{oid}/pets/new", {"name": n30, "birthDate": "2022-05-10", "type": "dog"})
    e1 = R.save("F20", "30car", r1)
    R.follow(r1)
    r2 = R.post(f"/owners/{oid}/pets/new", {"name": "M" * 31, "birthDate": "2022-05-10", "type": "dog"})
    e2 = R.save("F20", "31car", r2)
    ok_msg, txt = reject_check("F20", r2, "name", M_PETNAME30)
    R.record("F20", "RF04", LVL, "Límite de longitud del nombre de mascota (30/31)", "nombre de 30 y de 31 caracteres",
             steps("Crear un propietario.", "POST mascota con nombre de 30 caracteres.", "Repetir con 31 caracteres.",
                   "Verificar respuesta y mensaje."),
             f"30: 302; 31: 200 con '{M_PETNAME30}'",
             f"30 -> HTTP {r1.status_code}; 31 -> HTTP {r2.status_code}, {txt}",
             r1.status_code == 302 and r2.status_code == 200 and ok_msg and R.pet_id(oid, n30) is not None,
             f"{e1}; {e2}")


# ===================== RF05 =====================
def f22():
    oid = R.create_owner(ln("Fv"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Lunita", "birthDate": "2021-03-15", "type": "dog"})
    ev = R.save("F22", "post", r)
    d = R.follow(r)
    R.save("F22", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    same = R.pet_id(oid, "Lunita") == pid
    data = d is not None and "2021-03-15" in d.text and "<dd>dog</dd>" in d.text
    R.record("F22", "RF05", LVL, "Edición válida de nombre, tipo y fecha", "Luna->Lunita, cat->dog, 2021-03-15",
             steps("Crear propietario y mascota Luna.", "POST /owners/{o}/pets/{p}/edit con los nuevos datos.",
                   "Seguir la redirección; verificar mensaje, id y datos."),
             f"302; mensaje '{F_PET_UPD}'; la misma mascota (mismo id) muestra los nuevos datos",
             f"HTTP {r.status_code}; mensaje='{fl}'; mismo id={'sí' if same else 'no'}; datos={'sí' if data else 'no'}",
             r.status_code == 302 and fl == F_PET_UPD and same and data, ev)


def f23():
    oid = R.create_owner(ln("Fw"))
    R.create_pet(oid, "Luna")
    pid = R.create_pet(oid, "Max")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Luna", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F23", "post", r)
    ok_msg, txt = reject_check("F23", r, "name", M_DUP)
    still = R.pet_id(oid, "Max") == pid
    R.record("F23", "RF05", LVL, "Edición rechazada: renombrar a un nombre ya usado", "Max -> Luna (existente)",
             steps("Crear propietario con Luna y Max.", "POST edición de Max con nombre Luna.", "Verificar el mensaje.",
                   "Consultar el detalle."),
             f"200 con '{M_DUP}' en name; Max conserva su nombre",
             f"HTTP {r.status_code}; {txt}; Max sin cambios={'sí' if still else 'no'}",
             r.status_code == 200 and ok_msg and still, ev)


def f24():
    oid = R.create_owner(ln("Fx"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "Luna", "birthDate": TOMORROW.isoformat(), "type": "cat"})
    ev = R.save("F24", "post", r)
    ok_msg, txt = reject_check("F24", r, "birthDate", M_BIRTH)
    kept = "2022-05-10" in R.owner_page(oid)
    R.record("F24", "RF05", LVL, "Edición rechazada: fecha de nacimiento futura", f"birthDate={TOMORROW}",
             steps("Crear propietario y mascota.", "POST edición con fecha de mañana.", "Verificar el mensaje.",
                   "Consultar el detalle."),
             f"200 con '{M_BIRTH}' en birthDate; se conserva la fecha anterior",
             f"HTTP {r.status_code}; {txt}; fecha conservada={'sí' if kept else 'no'}",
             r.status_code == 200 and ok_msg and kept, ev)


def f25():
    oid = R.create_owner(ln("Fy"))
    pid = R.create_pet(oid, "Luna")
    r = R.post(f"/owners/{oid}/pets/{pid}/edit", {"name": "", "birthDate": "2022-05-10", "type": "cat"})
    ev = R.save("F25", "post", r)
    ok_msg, txt = reject_check("F25", r, "name", M_REQUIRED)
    kept = R.pet_id(oid, "Luna") == pid
    R.record("F25", "RF05", LVL, "Edición rechazada: nombre vacío (persistencia, complementa CP05)", "name=''",
             steps("Crear propietario y mascota.", "POST edición con nombre vacío.", "Verificar el mensaje.",
                   "Consultar el detalle."),
             f"200 con '{M_REQUIRED}' en name; la mascota conserva su nombre",
             f"HTTP {r.status_code}; {txt}; nombre conservado={'sí' if kept else 'no'}",
             r.status_code == 200 and ok_msg and kept, ev)


# ===================== RF06 =====================
def visit_setup(cid):
    oid = R.create_owner(ln(cid))
    pid = R.create_pet(oid, "Luna")
    return oid, pid


def f26():
    oid, pid = visit_setup("Fz")
    r = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": "Control general"})
    ev = R.save("F26", "post", r)
    d = R.follow(r)
    R.save("F26", "detalle", d) if d is not None else None
    fl = R.flash(d.text) if d is not None else None
    shown = d is not None and f"<td>{TOMORROW.isoformat()}</td>" in d.text and "Control general" in d.text
    R.record("F26", "RF06", LVL, "Registro de visita válida (mañana)", f"fecha={TOMORROW}, 'Control general'",
             steps("Crear propietario y mascota.", "POST /owners/{o}/pets/{p}/visits/new.",
                   "Seguir la redirección; verificar mensaje y visita."),
             f"302; mensaje '{F_VISIT}'; la visita aparece en la mascota",
             f"HTTP {r.status_code}; mensaje='{fl}'; visita visible={'sí' if shown else 'no'}",
             r.status_code == 302 and fl == F_VISIT and shown, ev)


def visit_reject(cid, title, date, desc, field, msg, data_desc):
    oid, pid = visit_setup(cid)
    r = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": date, "description": desc})
    ev = R.save(cid, "post", r)
    ok_msg, txt = reject_check(cid, r, field, msg)
    not_saved = f"<td>{date}</td>" not in R.owner_page(oid)
    R.record(cid, "RF06", LVL, title, data_desc,
             steps("Crear propietario y mascota.", "POST /owners/{o}/pets/{p}/visits/new con el dato indicado.",
                   "Verificar el mensaje.", "Consultar el detalle."),
             f"200 con '{msg}' en {field}; no se registra la visita",
             f"HTTP {r.status_code}; {txt}; no registrada={'sí' if not_saved else 'no'}",
             r.status_code == 200 and ok_msg and not_saved, ev)


def f31():
    oid, pid = visit_setup("Gd")
    r1 = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": "D" * 255})
    e1 = R.save("F31", "255car", r1)
    d = R.follow(r1)
    fl = R.flash(d.text) if d is not None else None
    r2 = R.post(f"/owners/{oid}/pets/{pid}/visits/new", {"date": TOMORROW.isoformat(), "description": "E" * 256})
    e2 = R.save("F31", "256car", r2)
    ok_msg, txt = reject_check("F31", r2, "description", M_SIZE255)
    R.record("F31", "RF06", LVL, "Límite de longitud de la descripción (255/256)", "descripción de 255 y de 256 caracteres",
             steps("Crear propietario y mascota.", "POST visita con descripción de 255 caracteres.",
                   "Repetir con 256 caracteres.", "Verificar respuestas y mensajes."),
             f"255: 302 y '{F_VISIT}'; 256: 200 con '{M_SIZE255}'",
             f"255 -> HTTP {r1.status_code}, mensaje='{fl}'; 256 -> HTTP {r2.status_code}, {txt}",
             r1.status_code == 302 and fl == F_VISIT and r2.status_code == 200 and ok_msg, f"{e1}; {e2}")


CASES = [
    f01,
    lambda: phone_case("F02", "987654321", "de 9 dígitos"),
    lambda: phone_case("F03", "98765432101", "de 11 dígitos"),
    lambda: phone_case("F04", "98765abcde", "con letras"),
    f05, f06, f07, f08, f09, f10, f11, f12, f13, f14, f15,
    lambda: pet_reject("F16", "Registro rechazado: nombre vacío",
                       {"name": "", "birthDate": "2022-05-10", "type": "cat"}, "name", M_REQUIRED, "name=''"),
    f17,
    lambda: pet_reject("F18", "Registro rechazado: nacimiento futuro (mañana)",
                       {"name": "Futuro", "birthDate": TOMORROW.isoformat(), "type": "cat"}, "birthDate", M_BIRTH,
                       f"birthDate={TOMORROW}"),
    f19, f20,
    lambda: pet_reject("F21", "Registro rechazado: sin fecha de nacimiento",
                       {"name": "SinFecha", "birthDate": "", "type": "cat"}, "birthDate", M_REQUIRED, "birthDate=''"),
    f22, f23, f24, f25, f26,
    lambda: visit_reject("F27", "Visita rechazada: fecha de hoy (límite)", TODAY.isoformat(), "Hoy", "date", M_VISIT,
                         f"fecha={TODAY}"),
    lambda: visit_reject("F28", "Visita rechazada: fecha pasada", YESTERDAY.isoformat(), "Ayer", "date", M_VISIT,
                         f"fecha={YESTERDAY}"),
    lambda: visit_reject("F29", "Visita rechazada: descripción vacía", TOMORROW.isoformat(), "", "description", M_BLANK,
                         "descripción=''"),
    lambda: visit_reject("F30", "Visita rechazada: descripción solo con espacios", TOMORROW.isoformat(), "   ",
                         "description", M_BLANK, "descripción='   '"),
    f31,
]
IDS = [f"F{i:02d}" for i in range(1, len(CASES) + 1)]
for cid, c in zip(IDS, CASES):
    try:
        c()
    except Exception as ex:
        R.blocked(cid, "", LVL, cid, f"Error de preparación: {ex}")
R.finish(started)

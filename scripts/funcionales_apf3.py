"""Casos funcionales añadidos en el APF3 para cerrar los vacíos de cobertura de RF01.

F32: registro de propietario con teléfono vacío.
F33: registro de propietario con nombre vacío.
F34: actualización de propietario con dirección vacía y ciudad en blanco (vacío de RF03).
Los mensajes esperados provienen del código evaluado: Owner.telephone tiene @NotBlank y
@Pattern(\\d{10}) (telephone.invalid); Person.firstName tiene @NotBlank. Con varios errores en un
campo, la plantilla los muestra juntos (th:errors), en orden no garantizado.

Uso: python3 funcionales_apf3.py --base http://localhost:8080 --out DIR --bd MySQL
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

R = Runner(a.base, a.out, "funcionales_http_apf3", a.bd)
started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))
LVL = "Funcional HTTP real"
M_PHONE = "Telephone must be a 10-digit number"
M_BLANK = "must not be blank"


def mensajes(text, field):
    raw = R.field_error_msg(text, field)
    if raw is None:
        return []
    return [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.split(r"<br\s*/?>", raw) if x.strip()]


def steps(*xs):
    return " ".join(f"{i}) {x}" for i, x in enumerate(xs, 1))


def f32():
    ln = f"Fz{TAG}"
    r = R.post("/owners/new", R.owner_form(lastName=ln, telephone=""))
    ev = R.save("F32", "post", r)
    got = mensajes(r.text, "telephone")
    not_saved = "has not been found" in R.get(f"/owners?lastName={ln}").text
    R.record("F32", "RF01", LVL, "Registro rechazado: teléfono vacío", "telephone=''",
             steps("Enviar POST /owners/new con el teléfono vacío.", "Verificar los mensajes del campo.",
                   "Buscar el apellido usado para confirmar que no se guardó."),
             f"200 con '{M_BLANK}' y '{M_PHONE}' en telephone; el propietario no se guarda",
             f"HTTP {r.status_code}; mensajes en telephone={got}; no guardado={'sí' if not_saved else 'no'}",
             r.status_code == 200 and sorted(got) == sorted([M_BLANK, M_PHONE]) and not_saved, ev)


def f33():
    ln = f"Fy{TAG}"
    r = R.post("/owners/new", R.owner_form(lastName=ln, firstName=""))
    ev = R.save("F33", "post", r)
    got = mensajes(r.text, "firstName")
    not_saved = "has not been found" in R.get(f"/owners?lastName={ln}").text
    R.record("F33", "RF01", LVL, "Registro rechazado: nombre vacío", "firstName=''",
             steps("Enviar POST /owners/new con el nombre vacío.", "Verificar el mensaje del campo.",
                   "Buscar el apellido usado para confirmar que no se guardó."),
             f"200 con '{M_BLANK}' en firstName; el propietario no se guarda",
             f"HTTP {r.status_code}; mensajes en firstName={got}; no guardado={'sí' if not_saved else 'no'}",
             r.status_code == 200 and got == [M_BLANK] and not_saved, ev)


def f34():
    ln = f"Fx{TAG}"
    oid = R.create_owner(ln)
    r = R.post(f"/owners/{oid}/edit", R.owner_form(lastName=ln, address="", city="  "))
    ev = R.save("F34", "post", r)
    a1, a2 = mensajes(r.text, "address"), mensajes(r.text, "city")
    page = R.owner_page(oid)
    kept = "Av. Central 123" in page and "Lima" in page
    R.record("F34", "RF03", LVL, "Actualización rechazada: dirección vacía y ciudad en blanco", "address='', city='  '",
             steps("Crear un propietario.", "POST /owners/{id}/edit con dirección vacía y ciudad con espacios.",
                   "Verificar ambos mensajes.", "Consultar el detalle."),
             f"200 con '{M_BLANK}' en address y city; los datos no cambian",
             f"HTTP {r.status_code}; address={a1}; city={a2}; datos conservados={'sí' if kept else 'no'}",
             r.status_code == 200 and a1 == [M_BLANK] and a2 == [M_BLANK] and kept, ev)


for cid, c in (("F32", f32), ("F33", f33), ("F34", f34)):
    try:
        c()
    except Exception as ex:
        R.blocked(cid, "RF01", LVL, cid, f"Error de preparación: {ex}")
R.finish(started)

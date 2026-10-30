"""Escenario de rendimiento basico APF2 (seccion 12) para Locust.

Mezcla de operaciones de los flujos RF02, RF03 (consulta del detalle) y RF06:
- buscar propietarios por apellido (peso 4)
- consultar el detalle de un propietario semilla (peso 4)
- abrir el formulario de busqueda (peso 1)
- registrar una visita en la mascota propia del usuario virtual (peso 1, escritura)
Cada usuario virtual crea su propio propietario y mascota al iniciar, de modo que
las escrituras no dependen de otros usuarios. Tiempo de espera entre acciones: 1 a 2 s.
"""
import datetime as dt
import random
import re

from locust import HttpUser, between, task

LAST_NAMES = ["Davis", "Franklin", "Black", "Escobito", "Schroeder", "Estaban", "McTavish", "Coleman", "Rodriquez"]


class Recepcionista(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.pet_url = None
        sfx = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(8))
        r = self.client.post("/owners/new", name="POST /owners/new (preparacion)", allow_redirects=False,
                             data={"firstName": "Carga", "lastName": "Perf" + sfx, "address": "Av. Test 1",
                                   "city": "Lima", "telephone": "9876543210"})
        m = re.search(r"/owners/(\d+)", r.headers.get("Location", ""))
        if not m:
            return
        self.owner_id = int(m.group(1))
        self.client.post(f"/owners/{self.owner_id}/pets/new", name="POST /pets/new (preparacion)",
                         allow_redirects=False, data={"name": "Perf", "birthDate": "2022-05-10", "type": "dog"})
        page = self.client.get(f"/owners/{self.owner_id}", name="GET /owners/[id] (preparacion)").text
        mp = re.search(r'pets/(\d+)/visits/new', page)
        if mp:
            self.pet_url = f"/owners/{self.owner_id}/pets/{mp.group(1)}/visits/new"

    @task(4)
    def buscar(self):
        self.client.get("/owners", params={"lastName": random.choice(LAST_NAMES)}, name="GET /owners?lastName",
                        allow_redirects=False)

    @task(4)
    def detalle(self):
        self.client.get(f"/owners/{random.randint(1, 10)}", name="GET /owners/[id]")

    @task(1)
    def formulario(self):
        self.client.get("/owners/find", name="GET /owners/find")

    @task(1)
    def visita(self):
        if not self.pet_url:
            return
        fecha = (dt.date.today() + dt.timedelta(days=random.randint(1, 60))).isoformat()
        with self.client.post(self.pet_url, name="POST /visits/new", allow_redirects=False, catch_response=True,
                              data={"date": fecha, "description": "Control de carga"}) as r:
            if r.status_code != 302:
                r.failure(f"esperado 302, obtenido {r.status_code}")

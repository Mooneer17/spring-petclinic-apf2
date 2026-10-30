"""Utilidades compartidas por las pruebas funcionales y de seguridad (APF2).

Solo deben ejecutarse contra una instancia LOCAL de Spring Petclinic.
"""
import datetime as dt
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

ALLOWED_HOSTS = {"localhost", "127.0.0.1"}


class Runner:
    def __init__(self, base_url, out_dir, suite, db_label):
        host = urlparse(base_url).hostname
        if host not in ALLOWED_HOSTS:
            sys.exit(f"Rechazado: {base_url} no es una instancia local")
        self.base = base_url.rstrip("/")
        self.out = out_dir
        self.suite = suite
        self.db = db_label
        self.s = requests.Session()
        self.s.headers["Accept-Language"] = "en"
        self.results = []
        os.makedirs(os.path.join(out_dir, "respuestas"), exist_ok=True)

    # ---------- HTTP ----------
    def get(self, path, **kw):
        return self.s.get(self.base + path, allow_redirects=False, timeout=30, **kw)

    def post(self, path, data, **kw):
        return self.s.post(self.base + path, data=data, allow_redirects=False, timeout=30, **kw)

    def save(self, case_id, tag, resp):
        name = f"{case_id}_{tag}.http.txt"
        path = os.path.join(self.out, "respuestas", name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{resp.request.method} {resp.request.url}\n")
            if resp.request.body:
                body = resp.request.body
                f.write("BODY: " + (body.decode() if isinstance(body, bytes) else str(body)) + "\n")
            f.write(f"\nHTTP {resp.status_code}\n")
            for k, v in resp.headers.items():
                f.write(f"{k}: {v}\n")
            f.write("\n")
            f.write(resp.text)
        return f"respuestas/{name}"

    # ---------- helpers de dominio ----------
    @staticmethod
    def owner_form(**over):
        d = {"firstName": "Ana", "lastName": "Torres", "address": "Av. Central 123",
             "city": "Lima", "telephone": "9876543210"}
        d.update(over)
        return d

    @staticmethod
    def owner_id_from(resp):
        """Extrae el id de la redireccion; admite ';jsessionid=...' (reescritura de URL)."""
        m = re.search(r"/owners/(\d+)(?:;jsessionid=[^/?#]*)?$", resp.headers.get("Location", ""))
        return int(m.group(1)) if m else None

    def create_owner(self, last_name):
        r = self.post("/owners/new", self.owner_form(lastName=last_name))
        m = self.owner_id_from(r)
        if r.status_code != 302 or not m:
            raise RuntimeError(f"No se pudo preparar propietario {last_name}: {r.status_code}")
        return m

    def create_pet(self, owner_id, name, birth="2022-05-10", ptype="cat"):
        r = self.post(f"/owners/{owner_id}/pets/new", {"name": name, "birthDate": birth, "type": ptype})
        if r.status_code != 302:
            raise RuntimeError(f"No se pudo preparar mascota {name}: {r.status_code}")
        return self.pet_id(owner_id, name)

    def owner_page(self, owner_id):
        return self.get(f"/owners/{owner_id}").text

    def pet_id(self, owner_id, name):
        html = self.owner_page(owner_id)
        # enlace de edicion: /owners/{o}/pets/{p}/edit precedido por el bloque de la mascota
        blocks = re.split(r'<dl class="dl-horizontal">', html)
        for b in blocks[1:]:
            mname = re.search(r"<dd>(.*?)</dd>", b, re.S)
            mid = re.search(rf'href="(?:/owners/)?{owner_id}/pets/(\d+)/edit"', b)
            if mname and mid and mname.group(1).strip() == name:
                return int(mid.group(1))
        return None

    @staticmethod
    def has_field_error(html, field):
        # El fragmento inputField marca el grupo con 'has-error' y muestra span.help-inline
        pat = rf'has-error[^>]*>\s*<label[^>]*for="{re.escape(field)}"'
        return re.search(pat, html) is not None

    # ---------- registro ----------
    def record(self, case_id, req, level, title, data, steps, expected, obtained, passed, evidence, notes="", status=None):
        self.results.append({
            "id": case_id, "requisito": req, "nivel": level, "titulo": title,
            "datos": data, "pasos": steps, "esperado": expected, "obtenido": obtained,
            "estado": status or ("Aprobado" if passed else "Fallido"), "evidencia": evidence,
            "notas": notes, "bd": self.db, "suite": self.suite,
        })
        mark = status or ("OK " if passed else "FAIL")
        print(f"[{mark}] {case_id} {title} -> {obtained}")

    def blocked(self, case_id, req, level, title, reason):
        self.results.append({"id": case_id, "requisito": req, "nivel": level, "titulo": title,
                             "datos": "", "pasos": "", "esperado": "", "obtenido": reason,
                             "estado": "Bloqueado", "evidencia": "", "notas": "", "bd": self.db,
                             "suite": self.suite})
        print(f"[BLOQ] {case_id} {title} -> {reason}")

    def finish(self, started):
        meta = {"suite": self.suite, "base_url": self.base, "bd": self.db,
                "inicio": started, "fin": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
        summary = {s: sum(1 for r in self.results if r["estado"] == s)
                   for s in ("Aprobado", "Fallido", "Bloqueado", "Observacion")}
        summary["Total"] = len(self.results)
        with open(os.path.join(self.out, "resultados.json"), "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "resumen": summary, "casos": self.results}, f, ensure_ascii=False, indent=2)
        print(json.dumps(summary, ensure_ascii=False))
        return summary


def wait_up(base, seconds=120):
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            if requests.get(base + "/", timeout=3).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False

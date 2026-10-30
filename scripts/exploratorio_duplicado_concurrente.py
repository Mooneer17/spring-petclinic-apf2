"""Prueba exploratoria: registro concurrente de mascotas con el mismo nombre (RF04/RN04).

Para N propietarios nuevos, envia simultaneamente K solicitudes de alta con el mismo nombre.
Esperado: una sola mascota por propietario; las demas solicitudes se rechazan con un
error de validacion controlado (HTTP 200 con error en 'name'), nunca HTTP 500.
Uso: python3 exploratorio_duplicado_concurrente.py --base URL --out DIR --bd ETIQUETA
"""
import argparse
import collections
import concurrent.futures as cf
import json
import os
import string
import time

import requests

from apf_common import Runner, wait_up

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://localhost:8080")
ap.add_argument("--out", required=True)
ap.add_argument("--bd", required=True)
ap.add_argument("--owners", type=int, default=10)
ap.add_argument("--k", type=int, default=4)
a = ap.parse_args()
assert wait_up(a.base)
os.makedirs(a.out, exist_ok=True)
R = Runner(a.base, a.out, "exploratorio", a.bd)
n = int(time.time())
TAG = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(5))


def post(owner_id):
    s = requests.Session()
    r = s.post(f"{a.base}/owners/{owner_id}/pets/new",
               data={"name": "Gemela", "birthDate": "2022-05-10", "type": "cat"},
               allow_redirects=False, timeout=30)
    kind = "302" if r.status_code == 302 else (
        "200_error_name" if r.status_code == 200 and R.has_field_error(r.text, "name") else str(r.status_code))
    return kind


counts = collections.Counter()
per_owner = []
for i in range(a.owners):
    oid = R.create_owner(f"Cc{TAG}{i:02d}")
    with cf.ThreadPoolExecutor(max_workers=a.k) as ex:
        kinds = list(ex.map(lambda _: post(oid), range(a.k)))
    stored = R.owner_page(oid).count("<dd>Gemela</dd>")
    counts.update(kinds)
    per_owner.append({"owner": oid, "respuestas": kinds, "mascotas_guardadas": stored})

summary = {"bd": a.bd, "propietarios": a.owners, "solicitudes_por_propietario": a.k,
           "conteo_respuestas": dict(counts),
           "propietarios_con_mas_de_una": sum(1 for p in per_owner if p["mascotas_guardadas"] > 1),
           "detalle": per_owner}
with open(os.path.join(a.out, "resultado.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in summary.items() if k != "detalle"}, ensure_ascii=False))

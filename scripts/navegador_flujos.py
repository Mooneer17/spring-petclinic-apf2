"""Recorrido de los seis flujos en navegador automatizado (Chromium + Playwright).

No sustituye una prueba manual: reproduce las acciones de un usuario sobre la interfaz
y guarda capturas como evidencia. Uso: python3 navegador_flujos.py --base URL --out DIR
"""
import argparse
import datetime as dt
import json
import os
import random
import string

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://localhost:8080")
ap.add_argument("--out", required=True)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
SFX = "".join(random.choice(string.ascii_uppercase) for _ in range(5))
LAST = "Navegador" + SFX
TOMORROW = (dt.date.today() + dt.timedelta(days=1)).isoformat()
log = []


def shot(page, name, note):
    path = os.path.join(a.out, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    log.append({"captura": f"{name}.png", "url": page.url, "nota": note})
    print(name, page.url)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 900}, locale="en-US")

    # RF01 invalido y valido
    page.goto(a.base + "/owners/new")
    page.fill("#firstName", "Ana"); page.fill("#lastName", LAST)
    page.fill("#address", "Av. Central 123"); page.fill("#city", "Lima"); page.fill("#telephone", "987654321")
    page.click("button[type=submit]")
    shot(page, "N01_RF01_telefono_9_digitos_rechazado", "Formulario devuelto con error en telefono")
    page.fill("#telephone", "9876543210")
    page.click("button[type=submit]")
    page.wait_for_url("**/owners/*")
    shot(page, "N02_RF01_propietario_registrado", "Detalle del propietario recien creado")
    owner_url = page.url.split(";")[0]

    # RF02 busqueda
    page.goto(a.base + "/owners/find")
    page.fill("#lastName", LAST)
    page.click("button[type=submit]")
    page.wait_for_load_state()
    shot(page, "N03_RF02_busqueda_por_apellido", "Busqueda con coincidencia unica redirige al detalle")

    # RF03 edicion
    page.goto(owner_url + "/edit")
    page.fill("#telephone", "9123456780")
    page.click("button[type=submit]")
    page.wait_for_load_state()
    shot(page, "N04_RF03_propietario_actualizado", "Telefono actualizado a 9123456780")

    # RF04 mascota
    page.goto(owner_url + "/pets/new")
    page.fill("#name", "Luna"); page.fill("#birthDate", "2022-05-10"); page.select_option("#type", "cat")
    page.click("button[type=submit]")
    page.wait_for_load_state()
    shot(page, "N05_RF04_mascota_registrada", "Mascota Luna asociada al propietario")

    # RF05 edicion de mascota (invalida y valida)
    page.click("text=Edit Pet")
    page.fill("#birthDate", TOMORROW)
    page.click("button[type=submit]")
    shot(page, "N06_RF05_fecha_futura_rechazada", "Error en fecha de nacimiento futura")
    page.fill("#name", "Lunita"); page.fill("#birthDate", "2021-03-15"); page.select_option("#type", "dog")
    page.click("button[type=submit]")
    page.wait_for_load_state()
    shot(page, "N07_RF05_mascota_actualizada", "Mascota renombrada a Lunita, tipo dog")

    # RF06 visita
    page.click("text=Add Visit")
    page.fill("#date", TOMORROW); page.fill("#description", "Control general")
    page.click("button[type=submit]")
    page.wait_for_load_state()
    shot(page, "N08_RF06_visita_registrada", "Visita de manana registrada para la mascota")
    b.close()

with open(os.path.join(a.out, "recorrido.json"), "w", encoding="utf-8") as f:
    json.dump({"fecha": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "apellido": LAST,
               "capturas": log}, f, ensure_ascii=False, indent=2)

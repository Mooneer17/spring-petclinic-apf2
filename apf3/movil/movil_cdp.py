"""APF3 - Medición automática en el Chrome de un celular o del emulador de Android Studio.

Se conecta por el protocolo de depuración de Chrome (CDP) al navegador del dispositivo, recorre las
nueve páginas de la prueba de compatibilidad y, en cada una, guarda una captura y mide: código HTTP,
desborde horizontal, tamaño mínimo de fuente, controles menores de 24 x 24 px y errores de consola.
También prueba el menú hamburguesa y, si se pide, registra un propietario.

Preparación (ver GUIA_PRUEBA_MOVIL.md):
  1) Depuración USB activada en el celular, o emulador encendido.
  2) Chrome abierto en el dispositivo con cualquier página.
  3) adb forward tcp:9222 localabstract:chrome_devtools_remote

Uso:
  python movil_cdp.py --base http://10.0.2.2:8080 --dispositivo "AVD Pixel 7 API 35" --orientacion vertical --out resultados_movil/M1_vertical
  python movil_cdp.py --base http://192.168.1.20:8080 --dispositivo "Samsung A15 (real)" --orientacion vertical --out ... --registro

--base es la dirección de la aplicación VISTA DESDE EL DISPOSITIVO (10.0.2.2 en el emulador; la IP de
la PC en un celular real). --cdp es la dirección de la PC donde quedó redirigido el puerto (por defecto
http://localhost:9222).
"""
import argparse
import datetime
import json
import os
import time

from playwright.sync_api import sync_playwright

PAGINAS = [
    ("inicio", "/"),
    ("buscar_propietario", "/owners/find"),
    ("lista_propietarios", "/owners?lastName="),
    ("detalle_propietario", "/owners/1"),
    ("nuevo_propietario", "/owners/new"),
    ("nueva_mascota", "/owners/1/pets/new"),
    ("nueva_visita", "/owners/1/pets/1/visits/new"),
    ("veterinarios", "/vets.html"),
    ("error", "/oups"),
]

MEDIR_JS = r"""
() => {
  const de = document.documentElement;
  const visibles = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea')]
    .filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
                   return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; });
  const pequenos = visibles.map(e => { const r = e.getBoundingClientRect();
      return {tag: e.tagName.toLowerCase(), texto: (e.innerText || e.value || e.name || e.getAttribute('href') || '').trim().slice(0, 40),
              w: Math.round(r.width), h: Math.round(r.height)}; })
    .filter(o => o.w < 24 || o.h < 24);
  let minFuente = 999;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; if (el.getBoundingClientRect().width === 0) continue;
    minFuente = Math.min(minFuente, parseFloat(getComputedStyle(el).fontSize));
  }
  const toggler = document.querySelector('.navbar-toggler');
  return {
    viewport: window.innerWidth + 'x' + window.innerHeight, dpr: window.devicePixelRatio,
    orientacion_real: (screen.orientation && screen.orientation.type) || '',
    ancho_documento: de.scrollWidth, desborde_horizontal: de.scrollWidth > de.clientWidth + 1,
    interactivos: visibles.length, objetivos_menores_24px: pequenos.length, ejemplos_pequenos: pequenos.slice(0, 6),
    fuente_minima_px: minFuente, toggler_visible: !!toggler && toggler.getBoundingClientRect().width > 0,
    titulo: document.title, lang: de.getAttribute('lang') || ''
  };
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="URL de la app vista desde el dispositivo")
    ap.add_argument("--cdp", default="http://localhost:9222", help="Endpoint CDP redirigido con adb forward")
    ap.add_argument("--dispositivo", required=True, help="Modelo y tipo, p. ej. 'AVD Pixel 7 API 35' o 'Moto G (real)'")
    ap.add_argument("--orientacion", choices=["vertical", "horizontal"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--registro", action="store_true", help="Registrar además un propietario (CO-M03, parte automática)")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "capturas"), exist_ok=True)
    res = {"fecha": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "base": a.base,
           "dispositivo": a.dispositivo, "orientacion": a.orientacion, "paginas": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(a.cdp)
        res["navegador"] = browser.version
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        res["user_agent"] = page.evaluate("navigator.userAgent")
        consola = []
        page.on("console", lambda m: consola.append(m.text[:300]) if m.type == "error" else None)
        page.on("pageerror", lambda e: consola.append(str(e)[:300]))
        for nombre, ruta in PAGINAS:
            consola.clear()
            resp = page.goto(a.base + ruta, wait_until="load", timeout=60000)
            page.wait_for_timeout(500)
            m = page.evaluate(MEDIR_JS)
            m.update({"pagina": nombre, "ruta": ruta, "http": resp.status if resp else None, "errores_consola": list(consola)})
            cap = f"{nombre}.png"
            page.screenshot(path=os.path.join(a.out, "capturas", cap), full_page=True, timeout=60000)
            m["captura"] = cap
            res["paginas"].append(m)
            print(f"{nombre:<22} HTTP {m['http']}  {m['viewport']:<9} desborde={m['desborde_horizontal']}  "
                  f"obj<24px={m['objetivos_menores_24px']}  fuente_min={m['fuente_minima_px']}  consola={len(consola)}")
        # Menú hamburguesa (CO-M02, parte automática)
        page.goto(a.base + "/", wait_until="load")
        menu = {"aplica": False}
        tog = page.locator(".navbar-toggler")
        if tog.count() and tog.first.is_visible():
            antes = page.locator("#main-navbar a.nav-link:visible").count()
            tog.first.click()
            page.wait_for_timeout(800)
            despues = page.locator("#main-navbar a.nav-link:visible").count()
            page.screenshot(path=os.path.join(a.out, "capturas", "menu_abierto.png"))
            tog.first.click()
            page.wait_for_timeout(800)
            cerrado = page.locator("#main-navbar a.nav-link:visible").count()
            menu = {"aplica": True, "visibles_antes": antes, "visibles_abierto": despues, "visibles_cerrado": cerrado,
                    "funciona": despues >= 4 and cerrado == antes}
        res["menu"] = menu
        print("menu:", menu)
        if a.registro:
            t0 = time.time()
            page.goto(a.base + "/owners/new", wait_until="load")
            apellido = "Movil" + datetime.datetime.now().strftime("%H%M%S")
            for campo, valor in [("firstName", "Prueba"), ("lastName", apellido), ("address", "Av. Movil 100"),
                                 ("city", "Lima"), ("telephone", "9876543210")]:
                page.locator(f"#{campo}").click()
                page.keyboard.type(valor)
            with page.expect_navigation(timeout=60000):
                page.locator("button[type=submit]").click()
            ok = apellido in page.content() and "/owners/new" not in page.url
            res["registro"] = {"exito": ok, "url_final": page.url.replace(a.base, ""), "segundos": round(time.time() - t0, 1)}
            page.screenshot(path=os.path.join(a.out, "capturas", "registro_final.png"), full_page=True)
            print("registro:", res["registro"])
        page.close()
    pags = res["paginas"]
    res["resumen"] = {"paginas": len(pags), "http_200": sum(1 for x in pags if x["http"] == 200),
                      "con_desborde": sum(1 for x in pags if x["desborde_horizontal"]),
                      "errores_consola": sum(len(x["errores_consola"]) for x in pags if x["pagina"] != "error"),
                      "fuente_minima_px": min(x["fuente_minima_px"] for x in pags)}
    with open(os.path.join(a.out, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("resumen:", res["resumen"])


if __name__ == "__main__":
    main()

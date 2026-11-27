"""APF3 - Pruebas de compatibilidad y responsive por emulacion (Playwright).

Recorre las paginas principales de Petclinic en varios perfiles de dispositivo
y navegador, mide desborde horizontal, menu, objetivos tactiles, tamano de
fuente y errores de consola (incluidas violaciones de CSP). Guarda capturas y
un resultados.json.

Uso: python3 responsive_playwright.py --base http://localhost:8082 --out DIR --etiqueta corregida
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

# (id, motor, dispositivo de Playwright o None, viewport si no hay dispositivo)
PERFILES = [
    ("D1_escritorio_chrome", "chromium", None, {"width": 1366, "height": 768}),
    ("D2_escritorio_firefox", "firefox", None, {"width": 1366, "height": 768}),
    ("D3_escritorio_safari_webkit", "webkit", None, {"width": 1440, "height": 900}),
    ("M1_iphone_13_webkit", "webkit", "iPhone 13", None),
    ("M2_pixel_7_chromium", "chromium", "Pixel 7", None),
    ("M3_galaxy_s9_chromium", "chromium", "Galaxy S9+", None),
    ("T1_ipad_gen7_webkit", "webkit", "iPad (gen 7)", None),
    ("T2_ipad_gen7_horizontal_webkit", "webkit", "iPad (gen 7) landscape", None),
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
  let minFuente = 999, nodoMin = '';
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; const r = el.getBoundingClientRect(); if (r.width === 0) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < minFuente) { minFuente = fs; nodoMin = t.textContent.trim().slice(0, 30); }
  }
  const anchos = [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > de.clientWidth + 1)
    .slice(0, 5).map(e => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : ''));
  const toggler = document.querySelector('.navbar-toggler');
  const tablas = [...document.querySelectorAll('table')].map(t => ({ancho: Math.round(t.scrollWidth), contenedor: Math.round(t.parentElement.clientWidth)}));
  return {
    viewport_meta: !!document.querySelector('meta[name=viewport]'),
    ancho_ventana: de.clientWidth, ancho_documento: de.scrollWidth,
    desborde_horizontal: de.scrollWidth > de.clientWidth + 1, elementos_que_desbordan: anchos,
    interactivos: visibles.length, objetivos_menores_24px: pequenos.length, ejemplos_pequenos: pequenos.slice(0, 5),
    fuente_minima_px: minFuente, texto_fuente_minima: nodoMin,
    toggler_visible: !!toggler && toggler.getBoundingClientRect().width > 0,
    tablas: tablas,
    titulo: document.title, lang: de.getAttribute('lang') || ''
  };
}
"""


def probar_menu(page, tactil):
    """En pantallas angostas abre el menu hamburguesa y cuenta enlaces visibles."""
    toggler = page.locator(".navbar-toggler")
    if toggler.count() == 0 or not toggler.first.is_visible():
        return {"aplica": False}
    antes = page.locator("#main-navbar a.nav-link:visible").count()
    toggler.first.tap() if tactil else toggler.first.click()
    page.wait_for_timeout(600)
    despues = page.locator("#main-navbar a.nav-link:visible").count()
    return {"aplica": True, "enlaces_visibles_antes": antes, "enlaces_visibles_despues": despues,
            "funciona": despues > antes}


def flujo_tactil(page, base, etiqueta):
    """Registro de propietario completo usando solo tap y teclado virtual emulado."""
    t0 = time.time()
    page.goto(base + "/owners/new")
    sufijo = datetime.datetime.now().strftime("%H%M%S")
    campos = {"firstName": "Movil", "lastName": "Responsive" + sufijo, "address": "Av. Prueba 123",
              "city": "Lima", "telephone": "9876543210"}
    for nombre, valor in campos.items():
        page.locator(f"#{nombre}").tap()
        page.keyboard.type(valor)
    page.locator("button[type=submit]").tap()
    page.wait_for_load_state("load")
    ok = "/owners/" in page.url and "new" not in page.url and campos["lastName"] in page.content()
    return {"exito": ok, "url_final": page.url.replace(base, ""), "segundos": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--perfiles", default="", help="prefijos de perfil separados por coma, p. ej. D (solo escritorio)")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "capturas"), exist_ok=True)
    resultados = {"base": a.base, "etiqueta": a.etiqueta,
                  "fecha": datetime.datetime.now().isoformat(timespec="seconds"), "perfiles": []}
    with sync_playwright() as p:
        filtro = [x for x in a.perfiles.split(",") if x]
        for pid, motor, disp, vp in PERFILES:
            if filtro and not any(pid.startswith(f) for f in filtro):
                continue
            bt = getattr(p, motor)
            browser = bt.launch()
            opts = dict(p.devices[disp]) if disp else {"viewport": vp}
            if motor == "firefox":
                opts.pop("is_mobile", None)
            ctx = browser.new_context(locale="es-PE", **opts)
            page = ctx.new_page()
            consola = []
            page.on("console", lambda m: consola.append({"tipo": m.type, "texto": m.text[:300]}) if m.type == "error" else None)
            page.on("pageerror", lambda e: consola.append({"tipo": "pageerror", "texto": str(e)[:300]}))
            perfil = {"id": pid, "motor": motor, "version": browser.version, "dispositivo": disp or "escritorio",
                      "viewport": opts.get("viewport"), "tactil": bool(opts.get("has_touch")), "paginas": []}
            for nombre, ruta in PAGINAS:
                consola.clear()
                resp = page.goto(a.base + ruta)
                page.wait_for_load_state("load")
                m = page.evaluate(MEDIR_JS)
                m.update({"pagina": nombre, "ruta": ruta, "http": resp.status if resp else None,
                          "consola": list(consola)})
                cap = f"{pid}__{nombre}.png"
                page.screenshot(path=os.path.join(a.out, "capturas", cap), full_page=True, timeout=60000)
                m["captura"] = cap
                if nombre == "inicio":
                    m["menu"] = probar_menu(page, perfil["tactil"])
                    if m["menu"].get("aplica"):
                        page.screenshot(path=os.path.join(a.out, "capturas", f"{pid}__menu_abierto.png"))
                perfil["paginas"].append(m)
            if perfil["tactil"]:
                perfil["flujo_tactil_registro"] = flujo_tactil(page, a.base, a.etiqueta)
                page.screenshot(path=os.path.join(a.out, "capturas", f"{pid}__flujo_tactil_final.png"), full_page=True)
            resultados["perfiles"].append(perfil)
            ctx.close()
            browser.close()
            pags = perfil["paginas"]
            print(f"{pid:<32} desborde={sum(x['desborde_horizontal'] for x in pags)}/{len(pags)} "
                  f"obj<24px={sum(x['objetivos_menores_24px'] for x in pags)} "
                  f"fuente_min={min(x['fuente_minima_px'] for x in pags)} "
                  f"errores_consola={sum(len(x['consola']) for x in pags)} "
                  f"menu={pags[0].get('menu')} tactil={perfil.get('flujo_tactil_registro')}")
    with open(os.path.join(a.out, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

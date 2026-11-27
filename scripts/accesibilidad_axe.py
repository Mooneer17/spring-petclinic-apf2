"""APF3 - Accesibilidad basica (WCAG 2.1 A/AA) con axe-core y prueba de teclado.

Uso: python3 accesibilidad_axe.py --base http://localhost:8082 --out DIR --axe tools/node_modules/axe-core/axe.min.js
"""
import argparse
import datetime
import json
import os

from playwright.sync_api import sync_playwright

PAGINAS = [
    ("inicio", "/"),
    ("buscar_propietario", "/owners/find"),
    ("lista_propietarios", "/owners?lastName="),
    ("detalle_propietario", "/owners/1"),
    ("nuevo_propietario", "/owners/new"),
    ("nuevo_propietario_con_errores", "POST:/owners/new"),
    ("nueva_mascota", "/owners/1/pets/new"),
    ("nueva_visita", "/owners/1/pets/1/visits/new"),
    ("veterinarios", "/vets.html"),
    ("error", "/oups"),
]

ETIQUETAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

FOCO_JS = r"""
() => { const e = document.activeElement; if (!e || e === document.body) return null;
  const s = getComputedStyle(e); const r = e.getBoundingClientRect();
  return {tag: e.tagName.toLowerCase(), id: e.id || '', texto: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 40),
          foco_visible: (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none',
          en_pantalla: r.width > 0 && r.height > 0}; }
"""

ESTRUCTURA_JS = r"""
() => ({lang: document.documentElement.getAttribute('lang') || '', titulo: document.title,
  h1: document.querySelectorAll('h1').length, h2: document.querySelectorAll('h2').length,
  imagenes_sin_alt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).map(i => i.getAttribute('src')),
  campos_sin_label: [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
     .filter(c => !(c.id && document.querySelector(`label[for="${c.id}"]`)) && !c.getAttribute('aria-label') && !c.closest('label'))
     .map(c => c.name || c.id),
  saltar_al_contenido: !!document.querySelector('a[href^="#"].skip, a.visually-hidden-focusable, a[href="#main"], a[href="#content"]'),
  landmark_main: !!document.querySelector('main, [role=main]')})
"""


def recorrer_teclado(page, maximo=40):
    vistos = []
    for _ in range(maximo):
        page.keyboard.press("Tab")
        f = page.evaluate(FOCO_JS)
        if not f:
            continue
        clave = (f["tag"], f["id"], f["texto"])
        if vistos and clave == (vistos[0]["tag"], vistos[0]["id"], vistos[0]["texto"]):
            break
        vistos.append(f)
    return vistos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--axe", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    axe_src = open(a.axe, encoding="utf-8").read()
    res = {"base": a.base, "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
           "estandar": ETIQUETAS, "paginas": []}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1366, "height": 768}, locale="es-PE")
        page = ctx.new_page()
        res["navegador"] = "Chromium " + b.version
        for nombre, ruta in PAGINAS:
            if ruta.startswith("POST:"):
                page.goto(a.base + ruta[5:])
                page.locator("button[type=submit]").click()
                page.wait_for_load_state("load")
            else:
                page.goto(a.base + ruta)
            # La CSP bloquea scripts inyectados por <script>, por eso se evalua el codigo de axe directamente.
            page.evaluate(axe_src)
            r = page.evaluate("(t) => axe.run(document, {runOnly: {type: 'tag', values: t}})", ETIQUETAS)
            viol = [{"id": v["id"], "impacto": v["impact"], "descripcion": v["help"], "criterio": [t for t in v["tags"] if t.startswith("wcag") and t[4:5].isdigit() and len(t) > 6],
                     "nodos": len(v["nodes"]), "ejemplo": v["nodes"][0]["html"][:160]} for v in r["violations"]]
            est = page.evaluate(ESTRUCTURA_JS)
            page.goto(page.url) if not ruta.startswith("POST:") else None
            tab = recorrer_teclado(page)
            sin_foco = [t for t in tab if not t["foco_visible"]]
            res["paginas"].append({"pagina": nombre, "ruta": ruta, "violaciones": viol,
                                   "reglas_aprobadas": len(r["passes"]), "revisar_manual": len(r["incomplete"]),
                                   "estructura": est, "tab_elementos": len(tab), "tab_sin_foco_visible": len(sin_foco),
                                   "ejemplos_sin_foco": sin_foco[:5], "orden_tab": [t["texto"] or t["id"] or t["tag"] for t in tab][:25]})
            print(f"{nombre:<30} violaciones={len(viol)} ({', '.join(v['id'] + ':' + str(v['nodos']) for v in viol)}) "
                  f"tab={len(tab)} sin_foco={len(sin_foco)} sin_label={est['campos_sin_label']} lang={est['lang']!r}")
        # Flujo completo solo con teclado: registrar propietario
        page.goto(a.base + "/owners/new")
        page.locator("#firstName").focus()
        for valor in ["Teclado", "Accesible", "Av. Teclado 45", "Lima", "9123456789"]:
            page.keyboard.type(valor)
            page.keyboard.press("Tab")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        ok = "Accesible" in page.content() and "/owners/new" not in page.url
        res["flujo_teclado_registro_propietario"] = {"exito": ok, "url_final": page.url.replace(a.base, "")}
        page.screenshot(path=os.path.join(a.out, "flujo_teclado_final.png"))
        print("flujo teclado:", res["flujo_teclado_registro_propietario"])
        b.close()
    with open(os.path.join(a.out, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

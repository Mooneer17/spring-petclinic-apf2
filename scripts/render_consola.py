"""Convierte extractos reales de logs y salidas de consola en imagenes tipo terminal para el informe.

Cada imagen indica en su barra superior el archivo de origen. No se escribe ningun resultado a mano:
todas las lineas se leen de los archivos de evidencia.
"""
import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

# Ruta de las evidencias del APF3 dentro del repositorio (apf3/ev/)
E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apf3", "ev") + os.sep
OUT = E + "10_capturas_informe/"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
FONTB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 15)
VERDE, ROJO, GRIS, BLANCO, AMAR = (120, 220, 120), (240, 110, 110), (150, 150, 150), (230, 230, 230), (230, 200, 90)


def color(line):
    l = line.lower()
    if line.startswith("$") or line.startswith("#"):
        return AMAR
    if re.search(r'"fallido": [1-9]|failures: [1-9]|failure!|"500"|huerfanas_despues=[1-9]|jsessionid=|violaciones=[1-9]', l):
        return ROJO
    if re.search(r'"fallido": 0|failures: 0|violaciones=0|huerfanas_despues=0|nosniff|deny|content-security|referrer|no-cache', l):
        return VERDE
    return BLANCO


def render(nombre, titulo, lineas, ancho=118):
    lineas = [l[:ancho] for l in lineas]
    h = 34 + 20 * len(lineas) + 16
    w = 16 + 9 * ancho + 16
    im = Image.new("RGB", (w, h), (30, 30, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 26], fill=(60, 60, 60))
    d.text((10, 5), titulo[:ancho + 10], font=FONTB, fill=BLANCO)
    for i, l in enumerate(lineas):
        d.text((16, 34 + 20 * i), l, font=FONT, fill=GRIS if l.startswith("  ") and not l.strip() else color(l))
    im.save(OUT + nombre)
    print(nombre, im.size)


def tail(path, n=1):
    return open(E + path, encoding="utf-8").read().strip().splitlines()[-n:]


def mvn_total(path):
    t = open(E + path, encoding="utf-8").read()
    return re.findall(r"^\[(?:INFO|ERROR)\] Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+\s*$", t, re.M)[-1].strip()


# 1. Regresion: resumen de las tres rondas
L = []
for etiqueta, base, junit in [("R0 original (main 5f76e05)", "04_regresion_MySQL/original/", "04_regresion_MySQL/original/junit_mysql.log"),
                              ("R1 corregida (d354bd2)", "04_regresion_MySQL/corregida/", "04_regresion_MySQL/corregida/junit_mysql.log"),
                              ("R2 corregida final (c6ba298 = aea22f6 sin comentarios)", "08_regresion_ronda2_MySQL/", "08_regresion_ronda2_MySQL/junit_mysql.log")]:
    L += [f"# {etiqueta}",
          "funcionales F01-F31: " + tail(base + "funcionales_consola.log")[0],
          "seguridad   S01-S13: " + tail(base + "seguridad_consola.log")[0],
          "JUnit MySQL        : " + mvn_total(junit), ""]
render("consola_regresion.png", "Resumen de rondas R0, R1 y R2 en MySQL 8.0.46 (funcionales_consola.log, seguridad_consola.log, junit_mysql.log)", L[:-1])

# 2. E01
L = []
for v in ("original", "corregida"):
    L.append(f"# {v} - 10 propietarios x 4 altas simultaneas")
    for d in ("E01", "E01_rep2", "E01_rep3"):
        r = json.load(open(E + f"04_regresion_MySQL/{v}/{d}/resultado.json"))
        h = open(E + f"04_regresion_MySQL/{v}/{d}/huerfanas.txt").read().strip()
        L.append(f"{d:<9} respuestas={json.dumps(r['conteo_respuestas'])}  {h}")
r = json.load(open(E + "08_regresion_ronda2_MySQL/E01/resultado.json"))
L += ["# ronda 2 (version final)", f"E01       respuestas={json.dumps(r['conteo_respuestas'])}  " + open(E + "08_regresion_ronda2_MySQL/E01/huerfanas.txt").read().strip()]
render("consola_E01.png", "E01 en MySQL: resultado.json y huerfanas.txt de cada corrida (04_regresion_MySQL, 08_regresion_ronda2_MySQL)", L)

# 3. axe-core antes / despues (solo lineas por pagina)
L = []
for v in ("antes", "despues"):
    L.append(f"# {v}: python3 accesibilidad_axe.py --base http://localhost:8082 ...")
    for l in open(E + f"07_accesibilidad/{v}/consola.log", encoding="utf-8"):
        if "violaciones=" in l:
            L.append(re.sub(r"\s+tab=.*", "", l.rstrip()))
    L.append("")
render("consola_axe.png", "axe-core 4.14.1, WCAG 2.1 A/AA, 10 paginas (07_accesibilidad/antes y despues/consola.log, extracto)", L[:-1])

# 4. REG-01
t = open(E + "06_regresion_CSP/test_antes_del_ajuste.log", encoding="utf-8").read().splitlines()
pick = [l for l in t if "r01PaginasSinEstilos" in l and "FAILURE" in l][:1]
pick += [l.rstrip() for l in t if 'id="main-navbar" style>' in l][:1]
i = next(k for k, l in enumerate(t) if l.startswith("not to contain pattern"))
pick += t[i:i + 2]
L = ["# Antes del ajuste (prueba r01 sobre la version con la CSP de SEC-03)"] + [p.replace("org.springframework.samples.petclinic.", "") for p in pick]
L += ["", "# Despues del ajuste (commit 4061dd6): suite completa", mvn_total("06_regresion_CSP/suite_completa_despues.log")]
render("consola_REG01.png", "REG-01: estilos en linea bloqueados por la CSP (06_regresion_CSP/test_antes_del_ajuste.log y suite_completa_despues.log)", L)

# 5. Cabeceras S12 / S13
L = ["# Version original (puerto 8081)"] + open(OUT + "cabeceras_original.txt").read().strip().splitlines()
L += ["", "# Version corregida (puerto 8082)"] + open(OUT + "cabeceras_corregida.txt").read().strip().splitlines()
render("consola_cabeceras_S12_S13.png", "S12 y S13: cabeceras de respuesta y redireccion tras crear un propietario (cabeceras_original.txt / cabeceras_corregida.txt)",
       [l for l in L if l.strip() or l == ""], ancho=150)

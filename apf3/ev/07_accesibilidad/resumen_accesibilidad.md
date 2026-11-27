# Accesibilidad basica (WCAG 2.1 A/AA) - 2026-11-26
Herramientas: axe-core 4.14.1 sobre Chromium 153 (Playwright), 1366x768, 10 paginas; recorrido con Tab; flujo de registro solo con teclado.

| ID | Criterio WCAG | Hallazgo (antes) | Paginas | Estado despues |
|---|---|---|---|---|
| A11Y-01 | 3.1.1 Idioma de la pagina (A) | <html> sin atributo lang | 10/10 | Corregido: lang segun locale (en) |
| A11Y-02 | 1.4.3 Contraste minimo (AA) | Menu #838789 sobre #34302d = 3.6:1 (min 4.5:1) | 10/10 | Corregido: #a3a7a9 = 5.39:1 |
| A11Y-03 | 2.4.4 / 4.1.2 Nombre de enlace (A) | Enlace del logo sin texto | 10/10 | Corregido: aria-label "Home" |
| A11Y-04 | 1.1.1 Contenido no textual (A) | Imagen pets.png sin alt | 2/10 | Corregido: alt="Welcome" / alt="" decorativa |
| A11Y-05 | 4.1.2 / 1.3.1 Etiquetas (A) | Campo lastName sin label asociado | 1/10 | Corregido: label for="lastName" |
| A11Y-OBS-01 | 2.4.7 Foco visible (AA) | Foco de campos de texto con borde celeste tenue | formularios | Observacion: cumple AA, mejora sugerida |

Resultado axe: antes 33 violaciones (10 paginas); despues 0.
Teclado: todos los controles alcanzables con Tab en orden logico; registro de propietario solo con teclado exitoso (/owners/12).
Pruebas JUnit AccesibilidadBasicaTests: 4/4 fallan en la version previa, 4/4 pasan despues. Suite completa: 101 pruebas, 0 fallos, 2 omitidas.

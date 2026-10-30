# Pendientes y limitaciones del APF2

Lo que sigue NO está hecho o no fue verificado. No debe presentarse como terminado.

## Requiere acción del equipo
1. **Responsables por caso.** Las fuentes recibidas no indican quién ejecutó o revisó cada caso. Registrarlo en la matriz (hoja Casos) y en la sección 8.4 del informe.
2. **Prueba manual en navegador.** Los flujos se recorrieron con Chromium automatizado (Playwright). Si el docente exige una prueba manual, un integrante debe repetir N01-N08 a mano y guardar sus capturas.
3. **Acceso del docente al repositorio.** Publicado en https://github.com/Mooneer17/spring-petclinic-apf2. Si es privado, invitar al docente como colaborador.
4. **Ejecución en Windows.** `herramientas/ejecutar_apf2.ps1` no se probó en Windows: el ambiente de ejecución fue Linux. El script `ejecutar_apf2.sh` sí se probó (acción `casos-mysql`, 7 de 7).
5. **Revisión del texto.** Verificar que el título actualizado de la carátula sea aceptable para el docente.

## Cobertura no alcanzada
6. RF01: teléfono vacío y nombre vacío en el registro (el nombre vacío solo se probó en la actualización).
7. RF03: dirección o ciudad vacías durante la actualización.
8. RF02: navegación de páginas posteriores a la 2.

## Defectos y hallazgos abiertos (código de producción no modificado por alcance)
9. DEF-P01, DEF-P02, DEF-P03, SEC-01 a SEC-04 y OBS-02 siguen abiertos. Si se corrigen, repetir S08, E01 y S02/S11/S12/S13 y registrar la comprobación. Las correcciones descritas son recomendaciones, no cambios implementados.

## Decisiones de la revisión del 30/10/2026 que conviene confirmar
10. S08 se reclasificó a fallido sin nueva ejecución. Si se quiere evidencia nueva, basta repetir `scripts/seguridad_http.py`, cuyo criterio automático para S08 ya se ajustó (exige un rechazo 4xx, no un 500).
11. S09 se mantuvo aprobado. Si el docente interpreta «error controlado» como respuesta 4xx, pasaría a fallido: 43 aprobados, 7 fallidos, 86,0 %.
12. E01 no tiene registro de sesión exploratoria (charter, timebox, bitácora, debrief). Si se quiere presentarla como exploratoria, habría que ejecutar una sesión nueva y registrarla; no se debe reconstruir la anterior.
13. La carga se ejecutó una vez por escenario. Para mayor solidez, repetir cada escenario al menos tres veces en una PC del equipo, con el generador en otra máquina si es posible.

## Diferencias de ambiente que conviene declarar en la defensa
14. JDK: transferencia con Temurin 21.0.13+9 (Windows); ejecución consolidada con OpenJDK 21.0.12.1 (Linux).
15. MySQL 8.0.46 local en lugar de Testcontainers (no había Docker). `MySqlIntegrationTests` del proyecto quedó omitida.
16. La carga se midió con aplicación, base y generador en el mismo equipo de 2 vCPU.

## Fuera del alcance del APF2
17. Secciones 14 (móvil, usabilidad, accesibilidad), 15 (regresión) y 18 (conclusiones finales).

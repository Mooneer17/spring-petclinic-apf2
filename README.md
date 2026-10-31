# Spring Petclinic · APF2 · Pruebas de Software (UTP)

Segundo avance del proyecto final del curso Pruebas de Software. Repositorio de evidencias, pruebas y scripts del Grupo 10.

- Informe: [informe/10_Segundo_Avance_APF2.pdf](informe/10_Segundo_Avance_APF2.pdf) (editable: .docx)
- Presentación para la defensa (51 diapositivas, con evidencias de cada tipo de prueba y conclusiones): [presentacion/APF2_Presentacion_APF2.pptx](presentacion/APF2_Presentacion_APF2.pptx). Versión anterior: [presentacion/10Grupo_Segundo_Avance.pptx](presentacion/10Grupo_Segundo_Avance.pptx)
- Menú de demostración en vivo sobre MySQL: [demo/GUIA_DEMO_MYSQL.md](demo/GUIA_DEMO_MYSQL.md)
- Ejecuciones de demostración del 30/10/2026: [nuevas_evidencias/](nuevas_evidencias/) (informe, sección 17.7)
- Matriz de casos, incidencias y métricas: [matriz/APF2_Matriz_Casos_Incidencias_Metricas.xlsx](matriz/APF2_Matriz_Casos_Incidencias_Metricas.xlsx)
- Cambios de la revisión del 30/10/2026: [CAMBIOS_REVISION.txt](CAMBIOS_REVISION.txt)
- Pendientes declarados: [PENDIENTES.md](PENDIENTES.md)

El código de `proyecto/` corresponde al repositorio oficial [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic), commit `500158f732419217507c7656904b8e6aa1bcc0d6`, distribuido bajo Apache License 2.0 (`proyecto/LICENSE.txt`). Solo se añadieron archivos de prueba; el diff está en `evidencias/CAMBIOS_PRUEBAS.diff`.

Spring Petclinic, commit `500158f732419217507c7656904b8e6aa1bcc0d6` (Spring Boot 4.1.0). Ejecución consolidada: 29/10/2026, America/Lima. Revisión: 30/10/2026 (ver `CAMBIOS_REVISION.txt`).

## 1. Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| `informe/` | Informe APF2 en PDF y DOCX editable (carátula original, secciones 1 a 20) |
| `presentacion/` | PPTX para la defensa (`APF2_Presentacion_APF2.pptx`) y versión anterior |
| `matriz/` | XLSX original de las ejecuciones (no reconstruida): trazabilidad, 51 casos con objetivo, técnica y pasos, históricos, 15 incidencias, métricas con fórmulas y rendimiento |
| `proyecto/` | Código oficial del commit más `AvanceUnitTests`, `AvanceIntegrationTests` (corregido) y `DiagnosticoFixtureTests` |
| `scripts/` | Pruebas HTTP (funcionales v2 y v1, seguridad, E01), navegador, Locust y `ejecutar_apf2.sh` |
| `herramientas/` | `ejecutar.ps1` original, `ejecutar_apf2.ps1` (Windows) con el JDK portátil verificado y `medir_arranque.ps1` (tiempo de arranque con MySQL) |
| `evidencias/` | Logs, reportes y respuestas HTTP por ejecución (ver tabla del punto 4) |
| `documentos_apf1/` | PDF y PPTX del primer avance, sin cambios |
| `demo/` | Menú de demostración (`demo_mysql.ps1`), ejecutor de un caso (`demo_caso.py`) y guion (`GUIA_DEMO_MYSQL.md`) |
| `nuevas_evidencias/` | Ejecuciones del 30/10/2026 con el menú: PC Windows (`*_DEMO_MySQL`) y entorno Linux (`20261030-1907_Linux_entorno_prueba`); registros de arranque con MySQL (`arranque_MySQL_Linux`) |
| `APF2_Programa.code-workspace`, `apf2.ps1`, `Abrir_en_VSCode.bat` | Espacio de trabajo de VS Code con las tareas de H2 y de la demostración MySQL |

Solo cambiaron archivos de prueba. `evidencias/CAMBIOS_PRUEBAS.diff` contiene el diff completo contra el paquete recibido.

## 2. Requisitos

- JDK 17 o superior y acceso a Maven Central (el proyecto usa Maven Wrapper 3.9.16).
- MySQL 8 local. Crear la base y el usuario con `proyecto/src/main/resources/db/mysql/user.sql` (usuario y clave `petclinic`). El esquema y los datos se cargan al iniciar.
- Python 3.10+ con `pip install requests locust playwright` y `python -m playwright install chromium`.

No se necesita Docker. El perfil `mysql` de las pruebas del proyecto intenta usar Testcontainers; por eso las pruebas se dirigen al MySQL local pasando las propiedades de `application-mysql.properties` por línea de comandos.

## 3. Pasos

Linux o macOS, desde esta carpeta:

```bash
scripts/ejecutar_apf2.sh casos         # CP01-CP06 + DIAG01 en H2
scripts/ejecutar_apf2.sh casos-mysql   # lo mismo sobre MySQL
scripts/ejecutar_apf2.sh suite         # suite completa del proyecto (H2)
scripts/ejecutar_apf2.sh app           # en otra terminal: aplicación con perfil mysql en :8080
scripts/ejecutar_apf2.sh funcionales   # F01-F31 (v2: código, mensaje y persistencia)
scripts/ejecutar_apf2.sh seguridad     # S01-S13 (solo acepta localhost)
scripts/ejecutar_apf2.sh e01           # doble envío concurrente
scripts/ejecutar_apf2.sh navegador     # capturas N01-N08
scripts/ejecutar_apf2.sh rendimiento   # 60 s de calentamiento + 10 y 30 usuarios, 180 s cada uno
```

Windows (PowerShell): `./herramientas/ejecutar_apf2.ps1 -Accion preparar`, y luego las mismas acciones (`casos`, `casos-mysql`, `suite`, `app`, `funcionales`, `seguridad`, `e01`, `navegador`, `rendimiento`). La salida queda en `nuevas_evidencias/<fecha>/`.

Resultados esperados: CP01-CP06 y DIAG01 aprobados; F01-F31 aprobados; S01-S13 con 7 aprobados, 5 fallidos (S02, S08, S11, S12, S13) y 1 observación (S01). En la revisión del 30/10, S08 se reclasificó a fallido según su resultado esperado y se ajustó el criterio automático del script (exige un rechazo 4xx, no un 500); el script ajustado no se volvió a ejecutar; E01 con respuestas 302 sobrantes y mascotas con `owner_id` nulo. Los tiempos de carga variarán según el equipo.

Para contar las mascotas huérfanas después de E01 en MySQL:

```sql
SELECT id, name, owner_id FROM petclinic.pets WHERE owner_id IS NULL;
```

## 4. Evidencias por ejecución

| Carpeta | Ejecución | Resultado |
|---|---|---|
| `00_transferencia` | Recibida (Windows, H2) | CP: 4 aprobados, 2 fallidos; 21 pruebas originales aprobadas |
| `01_reproduccion_original` | R1: pruebas originales, Linux, H2 | 4 / 2 |
| `01b_original_en_MySQL` | R1b: pruebas originales, MySQL | 4 / 2 |
| `02_correccion_H2` | R2: fixture corregido + DIAG01 | 7 / 0 |
| `03_correccion_MySQL` | R3: fixture corregido + DIAG01 | 7 / 0 |
| `04_suite_completa_H2` | Suite del proyecto | 86 ejecutadas, 0 fallidas, 2 omitidas |
| `05a_funcionales_MySQL_corrida1` | F01-F31, corrida 1 | 29 / 2 (falla del script, INC-T02) |
| `05b_funcionales_MySQL_corrida2` | F01-F31, corrida 2 (v1) | 31 / 0, sin verificar el texto de los mensajes (INC-T03) |
| `05c_funcionales_MySQL_corrida3_v2` | F01-F31, corrida 3 (v2, 30/10) | 31 / 0, con código, mensaje y persistencia |
| `06_seguridad_MySQL` | S01-S13 (ejecución única) | 8 / 4 / 1 registrados; tras la revisión: 7 / 5 / 1 (S08) |
| `07`, `07b`, `07c`, `07d` | E01, prueba adicional de concurrencia: MySQL (10 y 20 propietarios), H2, traza SQL | Fallido (DEF-P02, DEF-P03) |
| `08_rendimiento_MySQL` | Carga básica local: calentamiento, 10 y 30 VU | 0 errores; p95 21 y 16 ms |
| `09_navegador_MySQL` | N01-N08 | 8 capturas |

### Ejecuciones de demostración (30/10/2026)

| Carpeta | Equipo | Casos | Resultado |
|---|---|---|---|
| `nuevas_evidencias/20261030-151820_DEMO_MySQL`, `20261030-175503_DEMO_MySQL` | PC Windows | CP01 (dos veces) | Aprobado |
| `nuevas_evidencias/20261030-175550_DEMO_MySQL` | PC Windows | CP05 | Aprobado |
| `nuevas_evidencias/20261030-181439_DEMO_MySQL` | PC Windows, MySQL 8.0.46 | F01 (propietario id 12) | Aprobado |
| `nuevas_evidencias/20261030-1907_Linux_entorno_prueba` | Linux, MySQL 8.0.46 | CP02, CP06, F02, F27, S04, S08, S12 | 5 aprobados; S08 y S12 fallidos, como en el informe |

| `nuevas_evidencias/arranque_MySQL_Linux` | Linux, MySQL 8.0.46 | Arranque de la aplicación (evaluación complementaria, informe 12.5) | 7,745 s en la instancia de la prueba de carga; sin criterio de aceptación |

Las ejecuciones se reportan por separado; no se suman a los 51 casos.

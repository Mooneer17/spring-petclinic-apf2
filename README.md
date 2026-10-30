# Spring Petclinic · APF2 · Pruebas de Software (UTP)

Segundo avance del proyecto final del curso Pruebas de Software. Repositorio de evidencias, pruebas y scripts del Grupo 10.

- Informe: [informe/10_Segundo_Avance_APF2.pdf](informe/10_Segundo_Avance_APF2.pdf) (editable: .docx)
- Presentación: [presentacion/10Grupo_Segundo_Avance.pptx](presentacion/10Grupo_Segundo_Avance.pptx)
- Matriz de casos, incidencias y métricas: [matriz/APF2_Matriz_Casos_Incidencias_Metricas.xlsx](matriz/APF2_Matriz_Casos_Incidencias_Metricas.xlsx)
- Pendientes declarados: [PENDIENTES.md](PENDIENTES.md)

El código de `proyecto/` corresponde al repositorio oficial [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic), commit `500158f732419217507c7656904b8e6aa1bcc0d6`, distribuido bajo Apache License 2.0 (`proyecto/LICENSE.txt`). Solo se añadieron archivos de prueba; el diff está en `evidencias/CAMBIOS_PRUEBAS.diff`.

Spring Petclinic, commit `500158f732419217507c7656904b8e6aa1bcc0d6` (Spring Boot 4.1.0). Ejecución consolidada: 29/10/2026, America/Lima.

## 1. Contenido del repositorio

| Carpeta | Contenido |
|---|---|
| `informe/` | Informe APF2 en PDF y DOCX editable (carátula original, secciones 1 a 20) |
| `presentacion/` | PPTX para la defensa, con notas del orador en cada diapositiva |
| `matriz/` | XLSX: trazabilidad, 51 casos, histórico de CP, 14 incidencias, métricas con fórmulas y rendimiento |
| `proyecto/` | Código oficial del commit más `AvanceUnitTests`, `AvanceIntegrationTests` (corregido) y `DiagnosticoFixtureTests` |
| `scripts/` | Pruebas HTTP (funcionales, seguridad, E01), navegador, Locust y `ejecutar_apf2.sh` |
| `herramientas/` | `ejecutar.ps1` original y `ejecutar_apf2.ps1` (Windows) con el JDK portátil verificado |
| `evidencias/` | Logs, reportes y respuestas HTTP por ejecución (ver tabla del punto 4) |
| `documentos_apf1/` | PDF y PPTX del primer avance, sin cambios |

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
scripts/ejecutar_apf2.sh funcionales   # F01-F31
scripts/ejecutar_apf2.sh seguridad     # S01-S13 (solo acepta localhost)
scripts/ejecutar_apf2.sh e01           # doble envío concurrente
scripts/ejecutar_apf2.sh navegador     # capturas N01-N08
scripts/ejecutar_apf2.sh rendimiento   # 60 s de calentamiento + 10 y 30 usuarios, 180 s cada uno
```

Windows (PowerShell): `./herramientas/ejecutar_apf2.ps1 -Accion preparar`, y luego las mismas acciones (`casos`, `casos-mysql`, `suite`, `app`, `funcionales`, `seguridad`, `e01`, `navegador`, `rendimiento`). La salida queda en `nuevas_evidencias/<fecha>/`.

Resultados esperados: CP01-CP06 y DIAG01 aprobados; F01-F31 aprobados; S01-S13 con 8 aprobados, 4 fallidos (S02, S11, S12, S13) y 1 observación (S01); E01 con respuestas 302 sobrantes y mascotas con `owner_id` nulo. Los tiempos de carga variarán según el equipo.

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
| `05b_funcionales_MySQL_corrida2` | F01-F31, corrida 2 | 31 / 0 |
| `06_seguridad_MySQL` | S01-S13 | 8 / 4 / 1 observación |
| `07`, `07b`, `07c`, `07d` | E01 en MySQL (10 y 20 propietarios), H2, traza SQL | Fallido (DEF-P02, DEF-P03) |
| `08_rendimiento_MySQL` | Calentamiento, 10 y 30 usuarios | 0 errores; p95 21 y 16 ms |
| `09_navegador_MySQL` | N01-N08 | 8 capturas |

Las ejecuciones se reportan por separado; no se suman.

## 5. Guion breve para la defensa

1. **Decisión de fondo.** No se modificó Petclinic. Solo se corrigieron instrumentos de prueba, y cada defecto del producto se reporta con una corrección propuesta.
2. **CP04 y CP06.** Fallaban igual en Windows, Linux, H2 y MySQL. El helper `pet()` devolvía la instancia transitoria: `saveAndFlush` sobre un propietario existente ejecuta `merge` y la cascada persiste una copia. DIAG01 lo demuestra. Las aserciones no se tocaron.
3. **Funcionales.** 31 casos con datos válidos, inválidos y límites (9/10/11 dígitos, 30/31 y 255/256 caracteres, hoy/mañana/ayer). Las dos fallas de la primera corrida venían del script.
4. **Hallazgo principal.** Un doble envío del alta de mascota confirma con 302 un registro que queda con `owner_id` nulo (traza: `update pets set owner_id=null ...`). En MySQL, además, el duplicado devuelve HTTP 500.
5. **Rendimiento.** 0 errores en 4 804 solicitudes. Los umbrales son propuesta del equipo, y la prueba es local: no mide capacidad de producción.
6. **Seguridad.** No hay autenticación (no se inventó un login). Funcionan el escape de XSS, el tratamiento de inyección SQL y el bloqueo del id. Faltan protección de Actuator, CSRF y cabeceras.
7. **Límites.** Ver `PENDIENTES.md`.

Preguntas probables:
- *¿Por qué E01 no es un falso positivo?* Porque se contaron las filas con `owner_id` nulo directamente en la base (MySQL y H2) y la traza SQL registra la sentencia que las desvincula.
- *¿Por qué S07 y S08 aparecen aprobados si devuelven 500?* El criterio de seguridad era que no se modifiquen datos ajenos, y eso se cumple. El 500 se registra aparte como defecto (DEF-P01) u observación (OBS-02).
- *¿Por qué el p95 baja con 30 usuarios?* La primera medición incluyó el calentamiento de la JVM y de la caché; no es una mejora por mayor carga.

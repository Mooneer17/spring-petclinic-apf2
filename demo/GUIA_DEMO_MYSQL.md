# Guía de la demostración en vivo (MySQL)

Estas son **ejecuciones nuevas de demostración**. Se guardan en `nuevas_evidencias\<fecha-hora-segundos>_DEMO_MySQL\` y no reemplazan ni modifican las evidencias históricas de `evidencias\`.

## Antes de la exposición (una sola vez, con internet)

1. Comprueba que la app responde en http://localhost:8081 y que MySQL está encendido.
2. En VS Code: `Ctrl+Shift+P` > **Tasks: Run Task** > **APF2: Preparar dependencias de la demo (antes de exponer)**. Si ya la habías ejecutado antes de que existiera la opción de carga, repítela: ahora también instala Locust.
   - Compila una copia aislada del proyecto en `.runtime\demo_build`, para no tocar la carpeta que usa tu app.
   - Crea un entorno Python local en `.runtime\venv` con requests, pymysql, cryptography y locust.
   - Tarda de 1 a 3 minutos. Al terminar debe decir "Listo".
3. Ensaya una vez cada opción del menú.

## Durante la exposición

`Ctrl+Shift+P` > **Tasks: Run Task** > **APF2: Demostración en vivo — MySQL**.

Arriba aparece la lista de requisitos con [OK] o [FALTA]. Si algo sale [FALTA], resuélvelo antes de elegir una opción. La contraseña de MySQL se pide una sola vez, oculta, y solo queda en memoria mientras el menú esté abierto.

| Opción | Qué decir antes | Qué esperar | Qué decir después |
|---|---|---|---|
| 1. CP01 unitaria | "Pruebo solo la regla del teléfono, sin base de datos ni servidor." | APROBADO en unos 15 s | "Con 9 dígitos hay error; con 10 dígitos no. La prueba aísla una sola regla." |
| 2. CP02 integración | "Ahora pruebo varias capas juntas: Spring, JPA y MySQL." | APROBADO en unos 30 s, con "MySQL 8.0.46 confirmado en el log JDBC" | "Guardó y recuperó el propietario en MySQL real. La prueba revierte sus cambios al terminar, por eso no deja datos." |
| 3. F01 funcional | "Registro un propietario como lo haría un usuario, enviando el formulario por HTTP." | APROBADO, el id creado y la consulta SQL | Copia la consulta en Workbench y ejecútala: "Este es el registro que acaba de crear la prueba." |
| 4. S12 seguridad | "Reviso si la app envía cabeceras de seguridad básicas." | **FALLIDO** (las cuatro cabeceras en False) | "Es un fallo esperado y documentado (SEC-03). Lo dejamos como FALLIDO porque no cambiamos el código de producción." |
| 5. Carga | "Ahora pruebo el rendimiento con 10 usuarios simultáneos durante 30 segundos." | Pide escribir SI. APROBADO si p95 < 1000 ms y errores < 1 % | "Es una versión corta; en el informe medimos 180 s con 10 y 30 usuarios." |

## Opciones adicionales (6 a 21)

Las opciones 1 a 5 no cambiaron. Las nuevas siguen el mismo formato de ficha:

| Opción | Caso | Tipo | Resultado esperado según el informe |
|---|---|---|---|
| 6 | CP05 Nombre de mascota obligatorio | Unitaria, sin BD | APROBADO |
| 7 | CP03 Actualizar teléfono y releer | Integración, MySQL | APROBADO |
| 8 | CP04 Guardar mascota con su propietario | Integración, MySQL | APROBADO |
| 9 | CP06 Visita por la web y releer | Integración, MySQL | APROBADO |
| 10 | F02 Teléfono de 9 dígitos | Funcional HTTP | APROBADO |
| 11 | F09 Búsqueda sin resultados | Funcional HTTP | APROBADO |
| 12 | F15 Mascota válida | Funcional HTTP | APROBADO |
| 13 | F17 Mascota duplicada | Funcional HTTP | APROBADO |
| 14 | F18 Nacimiento futuro | Funcional HTTP | APROBADO |
| 15 | F26 Visita válida | Funcional HTTP | APROBADO |
| 16 | F27 Visita con fecha de hoy | Funcional HTTP | APROBADO |
| 17 | S02 Actuator expuesto | Seguridad | **FALLIDO** (SEC-01) |
| 18 | S03 XSS almacenado | Seguridad | APROBADO |
| 19 | S04 Inyección SQL | Seguridad | APROBADO |
| 20 | S08 Mascota de otro propietario | Seguridad | **FALLIDO** (DEF-P01) |
| 21 | S13 Id de sesión en la URL | Seguridad | **FALLIDO** (SEC-04) |

También puedes escribir el código del caso en lugar del número, por ejemplo `S08`.

- Las opciones 10 a 21 ejecutan el **código original** de `funcionales_http.py` o `seguridad_http.py`, solo del caso elegido. Los datos y el criterio son los mismos de la corrida histórica.
- Los casos HTTP que crean datos dejan registros con un apellido terminado en un sufijo de 5 letras (por ejemplo `FoMHLMY`). La ficha trae la consulta lista para Workbench.
- Las de integración (7 a 9) son `@Transactional` y no dejan filas.

## Carga y concurrencia (opciones 5 y 22)

Las dos piden escribir **SI** antes de ejecutarse, porque generan tráfico y dejan datos en MySQL. Cualquier otra respuesta cancela sin ejecutar nada.

| Opción | Qué hace | Datos que deja | Resultado esperado según el informe |
|---|---|---|---|
| 5. Carga | `scripts/locustfile.py` sin cambios: 10 usuarios durante 30 s | Unos 10 propietarios `Perf...` con una mascota y visitas | APROBADO (p95 < 1000 ms y errores < 1 %) |
| 22. E01 | `scripts/exploratorio_duplicado_concurrente.py` sin cambios: 5 propietarios, 4 altas simultáneas de la misma mascota | 5 propietarios `Cc...` y, si aparece el defecto, mascotas sin propietario | **FALLIDO** (DEF-P02, DEF-P03) |

- La carga corta no se compara cifra a cifra con el informe, que midió 180 s. El reporte gráfico queda en `carga.html`, dentro de la carpeta de evidencia.
- E01 cuenta las mascotas con `owner_id` nulo antes y después, con una consulta de solo lectura a MySQL. La concurrencia no es determinista: en una corrida corta el defecto puede no aparecer. Si no aparece, la ficha lo dice y no cambia lo documentado en el informe.
- Qué decir en E01: "Envío cuatro veces la misma mascota en el mismo instante. Lo correcto sería guardar una y rechazar las demás. En MySQL aparecen errores 500 y mascotas sin propietario. Es un defecto real de concurrencia."

## Cómo leer la ficha

- **ESTADO**: APROBADO (obtenido = esperado), FALLIDO (difiere) o BLOQUEADO (algo impidió ejecutar la prueba: app caída, MySQL apagado, contraseña incorrecta o falta preparar). El color solo apoya; el texto manda.
- **AMBIENTE Y URL**: indica la base usada. CP01 dice "sin acceso a base de datos". CP02 solo queda APROBADO si el log JDBC confirma MySQL; si detecta H2, queda BLOQUEADO.
- **DURACIÓN**: el total incluye el arranque de Maven; entre paréntesis va el tiempo del método de prueba.
- **RUTA DE EVIDENCIA**: carpeta con `ficha.txt`, `comando.txt` y el log completo (`maven.log` o `salida.log`), además de `surefire-reports` o las respuestas HTTP.
- **Referencia en el informe**: el resultado documentado de ese caso, para comparar.
- Si el estado no es APROBADO, el menú ofrece ver los detalles en pantalla.

## Datos en MySQL

- CP02 no deja filas, porque la prueba es `@Transactional`. MySQL sí consume un número de AUTO_INCREMENT, así que el siguiente id puede saltar uno.
- F01 deja un propietario ficticio con apellido `DemoF01XXXXX`. Para listarlos: `SELECT * FROM petclinic.owners WHERE last_name LIKE 'DemoF01%';`
- El menú no borra, no reinicia y no altera la base. Tampoco detiene la app, MySQL ni la instancia H2.

## Equivalencia con las pruebas originales

- CP01 y CP02: se ejecuta el mismo método JUnit original (`-Dtest=Clase#metodo`), sin cambios.
- F01 y S12: `demo\demo_caso.py` corre un solo caso con la misma petición y el mismo criterio que `funcionales_http.py` y `seguridad_http.py`. Usa `apf_common.py` sin cambios. Lo único distinto en F01 es el apellido (`DemoF01` + sufijo, en lugar de `Fa` + sufijo). La confirmación directa en MySQL es una consulta de solo lectura que se informa aparte y no cambia el criterio.
- CP02 usa MySQL mediante variables de entorno (`DATABASE=mysql`, `SPRING_DATASOURCE_*`). No activa el perfil `mysql` de pruebas porque ese perfil exige Docker (Testcontainers).

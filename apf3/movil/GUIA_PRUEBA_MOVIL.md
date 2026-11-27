# Guía de la prueba móvil · APF3 (sección 14.2)

Prueba de compatibilidad móvil de la versión corregida (rama `correcciones-apf3`). Se hace en el **emulador de Android Studio** (M1) y, si es posible, en un **celular real** del grupo (M2). Todo se anota en `Registro_Prueba_Movil_APF3.xlsx` y las evidencias quedan en `apf3/ev/12_movil/`.

Tiempo estimado: 15 minutos de preparación la primera vez y unos 30 minutos por dispositivo.

## 0. Requisitos (una sola vez)

| Qué | Cómo comprobarlo |
|---|---|
| Android Studio con **Android SDK Platform-Tools** | SDK Manager > SDK Tools > *Android SDK Platform-Tools* marcado |
| JDK del proyecto | `.\herramientas\ejecutar_apf2.ps1 -Accion preparar` (descarga el JDK portátil si falta) |
| Python con Playwright | `py -m pip install playwright` (no hace falta instalar navegadores: se usa el Chrome del dispositivo) |
| Repositorio actualizado | `git pull` en la rama `main` |

Si PowerShell bloquea los scripts: `Set-ExecutionPolicy -Scope Process Bypass` en esa ventana.

## 1. Crear el emulador (M1)

1. Android Studio > **Device Manager** > **Create Virtual Device**.
2. Elegir **Pixel 7** (o similar) > Next.
3. Elegir una imagen con **Google Play** o **Google APIs**, por ejemplo API 35. Las imágenes "AOSP" no traen Chrome.
4. Finish y encender el emulador con el botón ▶.
5. En el emulador abrir **Chrome** y aceptar la pantalla de bienvenida.

## 2. Levantar la versión corregida en la PC

En una terminal de PowerShell, desde la raíz del repositorio:

```powershell
.\apf3\movil\movil.ps1 -Accion app
```

El script descarga la rama `correcciones-apf3` en una copia aparte (`.runtime\correcciones-apf3`, no cambia tu rama), la compila y la deja corriendo en el puerto 8080 con H2. Deja esa ventana abierta; para detenerla, Ctrl+C.

Comprueba en el Chrome de la PC: `http://localhost:8080` debe mostrar Petclinic.

## 3. Abrir la app en el dispositivo

**Emulador:** en su Chrome, entra a `http://10.0.2.2:8080`. Dentro del emulador, `10.0.2.2` es la PC; `localhost` no funciona.

**Celular real (opcional, M2):**

1. PC y celular en la **misma red Wi-Fi**.
2. En PowerShell **como administrador**: `.\apf3\movil\movil.ps1 -Accion firewall` (abre el puerto 8080 solo en redes privadas).
3. `.\apf3\movil\movil.ps1 -Accion ip` muestra la URL, por ejemplo `http://192.168.1.20:8080`. Ábrela en el Chrome del celular.
4. Para usar las capturas y la medición automática por cable: activa **Opciones de desarrollador > Depuración USB** en el celular, conéctalo por USB y acepta el aviso de depuración.
5. Al terminar: `.\apf3\movil\movil.ps1 -Accion quitar-firewall` (como administrador).

## 4. Registrar el dispositivo

```powershell
.\apf3\movil\movil.ps1 -Accion dispositivos          # debe aparecer el emulador o el celular
.\apf3\movil\movil.ps1 -Accion info -Nombre M1       # guarda modelo, Android, Chrome y pantalla
```

Si hay más de un dispositivo conectado, agrega `-Serial <id>` (el id que muestra `dispositivos`). Copia los datos de `apf3\ev\12_movil\M1\info_dispositivo.txt` a la hoja **Dispositivos** del Excel.

## 5. Medición automática (parte de CO-M01 y CO-M02)

Con Chrome abierto en el dispositivo:

```powershell
.\apf3\movil\movil.ps1 -Accion rotar -Orientacion vertical
.\apf3\movil\movil.ps1 -Accion medir -Nombre M1 -Base http://10.0.2.2:8080 -Dispositivo "AVD Pixel 7 API 35" -Orientacion vertical -Registro
.\apf3\movil\movil.ps1 -Accion rotar -Orientacion horizontal
.\apf3\movil\movil.ps1 -Accion medir -Nombre M1 -Base http://10.0.2.2:8080 -Dispositivo "AVD Pixel 7 API 35" -Orientacion horizontal
.\apf3\movil\movil.ps1 -Accion rotar -Orientacion vertical
```

En un celular real cambia `-Base` por la URL del paso 3 y `-Dispositivo` por el modelo, por ejemplo `"Moto G54 (real)"`. Si el celular no deja fijar la orientación con `rotar`, gíralo a mano antes de cada medición.

La medición recorre las nueve páginas en el Chrome del dispositivo y guarda una captura de cada una, `resultados.json` con el desborde horizontal, la fuente mínima, los controles menores de 24 px y los errores de consola, y la prueba del menú. Si falla la conexión, revisa que Chrome esté abierto en el dispositivo y repite.

## 6. Prueba manual (lo que la medición no cubre)

Haz cada escenario con el dedo (en el emulador, con el ratón como si fuera un dedo) y anota el resultado en la hoja **Registro**. Toma una captura de cada fila:

```powershell
.\apf3\movil\movil.ps1 -Accion captura -Nombre M1 -Id CO-M03_registrar_vertical
```

| Escenario | Qué hacer | Qué mirar |
|---|---|---|
| CO-M01 | Revisar las capturas de la medición en vertical y horizontal | Que nada quede cortado ni encimado y que se lea sin zoom |
| CO-M02 | Tocar el menú ☰, abrir cada opción, cerrar el menú | Que aparezcan las 4 opciones y que se cierre |
| CO-M03 | Registrar un propietario (teléfono de 10 dígitos), agregarle una mascota y registrar una visita | Que el teclado no tape el campo, que el selector de fecha funcione, si aparece teclado numérico en el teléfono y el mensaje de éxito |
| CO-M04 | En *Find Owners* > *Find Owner*, tocar 5 veces los iconos de paginación ⏭ ⏮ | Cuántos toques fallan (relacionado con OBS-04) |

Criterios completos de aprobación: hoja **Escenarios** del Excel.

## 7. Al terminar

1. Revisa la hoja **Resumen** del Excel: cada escenario debe quedar en Aprobado, Aprobado con observaciones o Fallido.
2. Guarda el Excel lleno en `apf3/movil/`.
3. Pasa el Excel y la carpeta `apf3/ev/12_movil/` para actualizar la sección 14.2 del informe, la matriz (hoja Compatibilidad_PC, filas CO-M) y las métricas.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| El emulador no abre `http://10.0.2.2:8080` | Revisa que la ventana de `-Accion app` siga corriendo y que `http://localhost:8080` abra en la PC |
| El celular real no abre la página | Misma Wi-Fi, regla de firewall creada, red de Windows marcada como **Privada**; algunas redes de universidad aíslan los dispositivos: usa el punto de acceso del celular |
| `No se encontró adb` | Instala *Android SDK Platform-Tools* en el SDK Manager |
| `adb devices` muestra *unauthorized* | Acepta el aviso de depuración en el celular |
| `medir` no conecta | Abre Chrome en el dispositivo y repite; en celulares reales, revisa que la depuración USB siga activa |

@echo off
rem Abre APF2_Programa en Visual Studio Code.
rem La primera vez extrae contenido.zip (proyecto, evidencias y scripts).
cd /d "%~dp0"
if not exist "%~dp0proyecto\mvnw.cmd" (
  echo Extrayendo proyecto, evidencias y scripts...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%~dp0contenido.zip' -DestinationPath '%~dp0' -Force"
)
if not exist "%~dp0proyecto\mvnw.cmd" (
  echo No se pudo extraer contenido.zip.
  pause
  exit /b 1
)
where code >nul 2>nul
if %errorlevel%==0 (
  start "" code "%~dp0APF2_Programa.code-workspace"
) else (
  start "" "%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe" "%~dp0APF2_Programa.code-workspace"
)

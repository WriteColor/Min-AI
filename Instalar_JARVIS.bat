@echo off
title Lanzador de Instalador JARVIS AI
cd /d "%~dp0"

:: Comprobar si existe el Python del entorno virtual local primero
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" install.py
    exit
)

:: Si no, intentar con el Python global del sistema
where python >nul 2>&1
if %errorlevel% equ 0 (
    python install.py
    exit
)

echo.
echo =======================================================================
echo [ERROR] No se pudo encontrar una instalacion de Python valida.
echo =======================================================================
echo.
echo Por favor, instala Python 3.12 y asegurate de marcar la opcion
echo "Add Python to PATH" durante la instalacion.
echo.
pause
exit

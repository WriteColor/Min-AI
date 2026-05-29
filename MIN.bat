@echo off
chcp 65001 >nul 2>nul
setlocal enabledelayedexpansion
title MIN AI

:: -- Colores ANSI -------------------------------------------------------------
:: Activar soporte ANSI en Windows 10/11
for /f "tokens=3" %%a in ('reg query "HKCU\Console" /v VirtualTerminalLevel 2^>nul') do set "VT=%%a"
>nul 2>&1 reg add "HKCU\Console" /v VirtualTerminalLevel /t REG_DWORD /d 1 /f

for /f %%a in ('powershell -Command "[char]27"') do set "ESC=%%a"
set "PURPLE=%ESC%[95m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "RED=%ESC%[31m"
set "CYAN=%ESC%[96m"
set "RESET=%ESC%[0m"

:: -- Detectar directorio del script -------------------------------------------
cd /d "%~dp0"

:: -- Detectar Python ----------------------------------------------------------
set "PY="
if exist ".venv\Scripts\pythonw.exe" (
    set "PY=.venv\Scripts\pythonw.exe"
    set "PY_CONSOLE=.venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
    set "PY_CONSOLE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY=python"
        set "PY_CONSOLE=python"
    )
)

:: -- Parsear argumentos -------------------------------------------------------
if "%~1"=="" goto :start
if /i "%~1"=="install" goto :install
if /i "%~1"=="kill" goto :kill
if /i "%~1"=="status" goto :status
if /i "%~1"=="dev" goto :dev
if /i "%~1"=="help" goto :help
if /i "%~1"=="--help" goto :help
if /i "%~1"=="-h" goto :help

echo %RED%[ERROR] Comando desconocido: %~1%RESET%
echo.
goto :help

:: =============================================================================
:: START - Iniciar MIN (por defecto)
:: =============================================================================
:start
call :banner
echo %CYAN%[MIN] Iniciando asistente...%RESET%
echo.

if not defined PY (
    echo %RED%[ERROR] No se encontro Python. Ejecuta: MIN.bat install%RESET%
    pause
    exit /b 1
)

if not exist "main.py" (
    echo %RED%[ERROR] main.py no encontrado. Asegurate de estar en el directorio correcto.%RESET%
    pause
    exit /b 1
)

echo %GREEN%[OK] Lanzando MIN con: %PY%%RESET%
start "" "%PY%" "main.py"
echo %GREEN%[OK] MIN iniciado en segundo plano.%RESET%
timeout /t 2 /nobreak >nul
exit /b 0

:: =============================================================================
:: INSTALL - Ejecutar instalacion completa
:: =============================================================================
:install
call :banner
echo %CYAN%[MIN] Ejecutando instalador...%RESET%
echo.

:: Solicitar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[INFO] Solicitando permisos de administrador...%RESET%
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0' -ArgumentList 'install'"
    exit /b
)

:: Buscar Python en orden de prioridad
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" install.py
    goto :eof
)
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    "%LocalAppData%\Programs\Python\Python313\python.exe" install.py
    goto :eof
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" install.py
    goto :eof
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" install.py
    goto :eof
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    python install.py
    goto :eof
)
if exist "%ProgramFiles%\Python313\python.exe" (
    "%ProgramFiles%\Python313\python.exe" install.py
    goto :eof
)
if exist "%ProgramFiles%\Python312\python.exe" (
    "%ProgramFiles%\Python312\python.exe" install.py
    goto :eof
)

echo.
echo %RED%===========================================================================%RESET%
echo %RED%[ERROR] No se encontro una instalacion de Python valida.%RESET%
echo %RED%===========================================================================%RESET%
echo.
echo Por favor, instala Python 3.11+ y asegurate de marcar "Add Python to PATH".
echo.
pause
exit /b 1

:: =============================================================================
:: KILL - Matar todos los procesos de MIN
:: =============================================================================
:kill
call :banner
echo %YELLOW%[MIN] Cerrando instancias de MIN (selectivo)...%RESET%
echo.

:: Kill selectivo: solo procesos Python que ejecuten main.py de MIN
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'main\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('  Finalizado PID: ' + $_.ProcessId) }" 2>nul
echo.
echo %GREEN%[OK] Instancias de MIN finalizadas (otros procesos Python no fueron afectados).%RESET%
echo %GREEN%[OK] El mutex MIN_AI_SINGLE_INSTANCE_MUTEX ha sido liberado.%RESET%
echo.
echo Ya puedes volver a iniciar MIN con: MIN.bat
echo.
pause
exit /b 0

:: =============================================================================
:: STATUS - Mostrar estado de procesos MIN
:: =============================================================================
:status
call :banner
echo %CYAN%[MIN] Estado de procesos:%RESET%
echo.

echo %PURPLE%--- Procesos Python activos ---%RESET%
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find "python" >nul
if %errorlevel% equ 0 (
    tasklist /FI "IMAGENAME eq python.exe"
) else (
    echo   Ninguno
)
echo.
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find "pythonw" >nul
if %errorlevel% equ 0 (
    tasklist /FI "IMAGENAME eq pythonw.exe"
) else (
    echo   pythonw.exe: Ninguno
)

echo.
echo %PURPLE%--- Verificacion de archivos criticos ---%RESET%
if exist "main.py" (echo   %GREEN%[OK] main.py%RESET%) else (echo   %RED%[!!] main.py NO ENCONTRADO%RESET%)
if exist "ui.py" (echo   %GREEN%[OK] ui.py%RESET%) else (echo   %RED%[!!] ui.py NO ENCONTRADO%RESET%)
if exist "config\config.json" (echo   %GREEN%[OK] config\config.json%RESET%) else (echo   %RED%[!!] config\config.json NO ENCONTRADO%RESET%)
if exist "config\vosk_model" (echo   %GREEN%[OK] config\vosk_model%RESET%) else (echo   %YELLOW%[--] config\vosk_model - opcional%RESET%)
if exist ".venv" (echo   %GREEN%[OK] .venv%RESET%) else (echo   %RED%[!!] .venv - NO ENCONTRADO, ejecuta MIN.bat install%RESET%)
if exist "Min-UI\dist" (echo   %GREEN%[OK] Min-UI\dist%RESET%) else (echo   %YELLOW%[--] Min-UI\dist - compilar con pnpm build%RESET%)
echo.
pause
exit /b 0

:: =============================================================================
:: DEV - Modo desarrollo con hot-reload
:: =============================================================================
:dev
call :banner
echo %CYAN%[MIN] Iniciando en modo desarrollo (hot-reload)...%RESET%
echo.

if not defined PY_CONSOLE (
    if not defined PY (
        echo %RED%[ERROR] No se encontro Python.%RESET%
        pause
        exit /b 1
    )
    set "PY_CONSOLE=%PY%"
)

if not exist "run_debug.py" (
    echo %YELLOW%[WARN] run_debug.py no encontrado. Iniciando main.py directamente...%RESET%
    "%PY_CONSOLE%" main.py
) else (
    "%PY_CONSOLE%" run_debug.py
)
exit /b 0

:: =============================================================================
:: HELP - Mostrar ayuda
:: =============================================================================
:help
call :banner
echo %CYAN%Uso:%RESET%  MIN.bat [comando]
echo.
echo %PURPLE%Comandos disponibles:%RESET%
echo   %GREEN%(sin argumento)%RESET%  Inicia MIN (backend Python en segundo plano)
echo   %GREEN%install%RESET%         Ejecuta la instalacion completa del entorno
echo   %GREEN%kill%RESET%            Cierra todos los procesos de MIN / Python
echo   %GREEN%status%RESET%          Muestra el estado de los procesos y archivos criticos
echo   %GREEN%dev%RESET%             Inicia en modo desarrollo con hot-reload
echo   %GREEN%help%RESET%            Muestra esta ayuda
echo.
exit /b 0

:: =============================================================================
:: BANNER - Arte ASCII de MIN
:: =============================================================================
:banner
echo.
echo %PURPLE%=======================================================================%RESET%
echo %PURPLE%                                                                       %RESET%
echo %PURPLE%             M   M   III   N   N                                     %RESET%
echo %PURPLE%             MM MM    I    NN  N                                     %RESET%
echo %PURPLE%             M M M    I    N N N                                     %RESET%
echo %PURPLE%             M   M    I    N  NN                                     %RESET%
echo %PURPLE%             M   M   III   N   N                                     %RESET%
echo %PURPLE%                                                                       %RESET%
echo %GREEN%               Asistente de Inteligencia Artificial                    %RESET%
echo %PURPLE%=======================================================================%RESET%
echo.
goto :eof

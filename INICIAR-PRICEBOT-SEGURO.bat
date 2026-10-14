@echo off
setlocal
rem Ejecutar normalmente EN LA PC SERVIDOR. No contiene claves ni contrasenas.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TLS_LAN\iniciar-seguro.ps1"
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" (
    echo.
    echo No se pudo iniciar PriceBot. Revisar el mensaje anterior.
    pause
)
endlocal & exit /b %PRICEBOT_EXIT_CODE%

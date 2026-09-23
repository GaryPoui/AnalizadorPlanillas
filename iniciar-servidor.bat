@echo off
setlocal

rem PriceBot - inicio simplificado para el servidor Windows
rem No guardar contrasenas ni claves en este archivo.
cd /d "%~dp0"

rem Configuracion de red para uso HTTP dentro de la LAN.
set "PRICEBOT_BIND_HOST=0.0.0.0"
set "PRICEBOT_REQUIRE_HTTPS=0"
set "PRICEBOT_COOKIE_SECURE=0"
set "PRICEBOT_PUBLIC_URL=http://192.168.190.146:3000"
set "PRICEBOT_ALLOWED_ORIGINS=http://192.168.190.146:3000,http://127.0.0.1:3000,http://localhost:3000"
set "PRICEBOT_CSP_CONNECT_SRC='self' http://192.168.190.146:8000 http://127.0.0.1:8000 http://localhost:8000"

echo.
echo  PriceBot - iniciando servidor
echo  -----------------------------------------
echo  Acceso LAN: http://192.168.190.146:3000
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

if errorlevel 1 (
    echo.
    echo  El servidor no pudo iniciarse. Revisa el mensaje anterior.
    pause
)

endlocal

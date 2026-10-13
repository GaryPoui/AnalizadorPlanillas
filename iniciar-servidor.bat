@echo off
setlocal

rem PriceBot - inicio simplificado para el servidor Windows
rem No guardar contrasenas ni claves en este archivo.
cd /d "%~dp0"

rem Acceso local por HTTP; clientes remotos solo por HTTPS con certificado confiable.
set "PRICEBOT_REQUIRE_HTTPS=1"
set "PRICEBOT_COOKIE_SECURE=1"
set "PRICEBOT_LOCAL_ADMIN_BYPASS=1"
if defined PRICEBOT_TLS_CERTFILE if defined PRICEBOT_TLS_KEYFILE goto :tls_ready
set "PRICEBOT_BIND_HOST=127.0.0.1"
goto :bind_ready
:tls_ready
set "PRICEBOT_BIND_HOST=0.0.0.0"
:bind_ready
if not defined PRICEBOT_PUBLIC_URL set "PRICEBOT_PUBLIC_URL=https://192.168.190.146:3000"
if not defined PRICEBOT_ALLOWED_ORIGINS set "PRICEBOT_ALLOWED_ORIGINS=https://192.168.190.146:3000,http://127.0.0.1:3000,http://localhost:3000"
if not defined PRICEBOT_CSP_CONNECT_SRC set "PRICEBOT_CSP_CONNECT_SRC='self' https://192.168.190.146:8000 http://127.0.0.1:8000 http://localhost:8000"

echo.
echo  PriceBot - iniciando servidor
echo  -----------------------------------------
if defined PRICEBOT_TLS_CERTFILE if defined PRICEBOT_TLS_KEYFILE goto :echo_tls
echo  Sin certificado TLS: acceso limitado a esta PC.
goto :echo_done
:echo_tls
echo  Acceso LAN seguro: %PRICEBOT_PUBLIC_URL% (requiere certificado TLS)
:echo_done
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

if errorlevel 1 (
    echo.
    echo  El servidor no pudo iniciarse. Revisa el mensaje anterior.
    pause
)

endlocal

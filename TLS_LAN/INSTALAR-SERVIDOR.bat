@echo off
setlocal
cd /d "%~dp0"
echo Ejecutar este archivo como administrador EN LA PC SERVIDOR.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-servidor.ps1" %*
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" echo No se completo la instalacion. Revisa el error anterior.
pause
endlocal & exit /b %PRICEBOT_EXIT_CODE%

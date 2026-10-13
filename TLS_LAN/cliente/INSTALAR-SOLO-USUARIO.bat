@echo off
setlocal
echo Instalar confianza solo para este usuario de Windows. No ejecutar como otro usuario.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-cliente.ps1" -Scope CurrentUser
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" echo No se instalo la confianza. Revisa el error anterior.
pause
endlocal & exit /b %PRICEBOT_EXIT_CODE%

@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar-clientes.ps1"
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" echo No se preparo el paquete. Revisar el error anterior.
pause
endlocal & exit /b %PRICEBOT_EXIT_CODE%

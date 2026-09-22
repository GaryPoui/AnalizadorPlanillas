@echo off
setlocal
cd /d "%~dp0"
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set "PRICEBOT_INSTALL_EXIT=%ERRORLEVEL%"
echo.
if not "%PRICEBOT_INSTALL_EXIT%"=="0" (
    echo La instalacion no pudo completarse. Revisa el mensaje anterior.
) else (
    echo Ya puedes ejecutar start.bat.
)
pause
exit /b %PRICEBOT_INSTALL_EXIT%

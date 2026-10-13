[CmdletBinding()]
param([string]$ServerIP = "192.168.190.146", [switch]$LocalAdmin)
$ErrorActionPreference = "Stop"
try {
    if ($LocalAdmin) { $ServerIP = "127.0.0.1" }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $web = Invoke-WebRequest -UseBasicParsing -Uri "https://${ServerIP}:3000/" -TimeoutSec 15
    $api = Invoke-RestMethod -Uri "https://${ServerIP}:8000/health" -TimeoutSec 15
    if ($web.StatusCode -ne 200 -or $api.status -ne "ok") { throw "Respuesta inesperada del sitio o de la API." }
    Write-Host "HTTPS y confianza verificados: sitio y API responden correctamente." -ForegroundColor Green
    Write-Host "Abrir https://${ServerIP}:3000/ en el navegador y probar inicio de sesion."
} catch {
    Write-Error "Fallo la verificacion HTTPS: $($_.Exception.Message). Revisar confianza de CA, fecha, IP y firewall." -ErrorAction Continue
    exit 1
}

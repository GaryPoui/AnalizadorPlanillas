[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [switch]$ValidateOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
try {
    $tlsRoot = Join-Path ([Environment]::GetFolderPath("CommonApplicationData")) "PriceBotTLS"
    if (-not $ConfigPath) { $ConfigPath = Join-Path $tlsRoot "launch-config.json" }
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Falta la configuracion HTTPS del servidor: $ConfigPath. Este archivo se ejecuta SOLO en la PC servidor. Si nunca se instalo HTTPS, ejecutar TLS_LAN\INSTALAR-SERVIDOR.bat como administrador con Soporte. Si ya se instalo, pedir a Soporte que revise la configuracion; no regenerar certificados ni usar HTTP."
    }
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $launcher = Join-Path $config.project_path "iniciar-servidor.bat"
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
        throw "No se encuentra el proyecto en la ruta guardada: $($config.project_path). Soporte debe revisar project_path en launch-config.json."
    }
    foreach ($name in @("PRICEBOT_REQUIRE_HTTPS", "PRICEBOT_COOKIE_SECURE", "PRICEBOT_AUTH_REQUIRED")) {
        if ([string]$config.environment.$name -ne "1") { throw "La configuracion segura requiere ${name}=1. Pedir revision a Soporte." }
    }
    foreach ($name in @("PRICEBOT_TLS_CERTFILE", "PRICEBOT_TLS_KEYFILE")) {
        $file = [string]$config.environment.$name
        if (-not $file -or -not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "No se encuentra el archivo HTTPS indicado en $name. Pedir revision a Soporte."
        }
    }
    if ([string]$config.environment.PRICEBOT_PUBLIC_URL -notmatch '^https://') {
        throw "La direccion de PriceBot debe comenzar con https://. No se iniciara por HTTP."
    }
    if ($ValidateOnly) { Write-Host "Configuracion HTTPS y rutas verificadas. No se iniciaron servicios ni se modifico Windows."; exit 0 }
    foreach ($property in $config.environment.PSObject.Properties) {
        [Environment]::SetEnvironmentVariable($property.Name, [string]$property.Value, "Process")
    }
    Write-Host "Iniciando PriceBot con la configuracion HTTPS instalada."
    & $launcher
    exit $LASTEXITCODE
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

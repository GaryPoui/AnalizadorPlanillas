Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
try {
    $tlsRoot = Join-Path ([Environment]::GetFolderPath("CommonApplicationData")) "PriceBotTLS"
    $config = Get-Content -LiteralPath (Join-Path $tlsRoot "launch-config.json") -Raw | ConvertFrom-Json
    $metadata = Get-Content -LiteralPath (Join-Path $tlsRoot "certificates.json") -Raw | ConvertFrom-Json
    $python = Join-Path $config.project_path ".venv\Scripts\python.exe"
    $builder = Join-Path $config.project_path "TLS_LAN\crear_zip.py"
    & $python $builder --client-cert (Join-Path $tlsRoot "PriceBot-CA.cer") --expected-sha256 $metadata.ca_sha256 --server-ip $metadata.server_ip
    if ($LASTEXITCODE -ne 0) { throw "No se preparo el paquete. Verificar git pull, dependencia cryptography y CA publica." }
    Write-Host "Distribuir SOLO el archivo CONFIGURAR-PRICEBOT-LAN.bat de la carpeta dist del repo." -ForegroundColor Green
    Write-Host "Esta operacion no renueva certificados, no lee claves privadas ni modifica el servidor."
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

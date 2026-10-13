Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
try {
    $tlsRoot = Join-Path ([Environment]::GetFolderPath("CommonApplicationData")) "PriceBotTLS"
    $config = Get-Content -LiteralPath (Join-Path $tlsRoot "launch-config.json") -Raw | ConvertFrom-Json
    foreach ($property in $config.environment.PSObject.Properties) {
        [Environment]::SetEnvironmentVariable($property.Name, [string]$property.Value, "Process")
    }
    & (Join-Path $config.project_path "iniciar-servidor.bat")
    exit $LASTEXITCODE
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

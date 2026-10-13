[CmdletBinding()]
param(
    [string]$CertificatePath = "",
    [string]$ExpectedSha256 = "",
    [switch]$ValidateOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
try {
    if (-not $CertificatePath) { $CertificatePath = Join-Path $PSScriptRoot "PriceBot-CA.cer" }
    $CertificatePath = (Resolve-Path -LiteralPath $CertificatePath).Path
    $cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new($CertificatePath)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $actual = ([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace("-", "") }
    finally { $sha.Dispose() }
    Write-Host "Huella SHA-256 del certificado recibido: $actual"
    if (-not $ExpectedSha256) {
        $ExpectedSha256 = Read-Host "Pega la huella obtenida directamente del servidor o del responsable TI"
    }
    $expected = ($ExpectedSha256 -replace '[:\s-]', '').ToUpperInvariant()
    if ($expected -notmatch '^[A-F0-9]{64}$' -or $expected -ne $actual) {
        throw "La huella no coincide. No se instalara ningun certificado."
    }
    $bcRaw = @($cert.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.19" })
    if ($bcRaw.Count -ne 1) { throw "Falta la restriccion de autoridad certificadora." }
    $bc = [Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($bcRaw[0], $bcRaw[0].Critical)
    if (-not $bc.CertificateAuthority -or -not $bc.HasPathLengthConstraint -or $bc.PathLengthConstraint -ne 0) {
        throw "El archivo no es la CA prevista por este kit."
    }
    if ($cert.HasPrivateKey -or $cert.NotAfter -le (Get-Date) -or $cert.NotBefore -gt (Get-Date)) {
        throw "El certificado esta fuera de vigencia o contiene una clave privada."
    }
    if ($ValidateOnly) { Write-Host "Validacion correcta. No se modifico Windows."; return }
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Clic derecho en INSTALAR-CLIENTE.bat -> Ejecutar como administrador."
    }
    if (-not (Test-Path -LiteralPath "Cert:\LocalMachine\Root\$($cert.Thumbprint)")) {
        Import-Certificate -FilePath $CertificatePath -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
    }
    Write-Host "Confianza instalada. Cerrar y abrir el navegador; ingresar a la URL HTTPS de la LAN." -ForegroundColor Green
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

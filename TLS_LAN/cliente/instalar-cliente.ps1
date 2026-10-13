[CmdletBinding()]
param(
    [string]$CertificatePath = "",
    [string]$ExpectedSha256 = "",
    [ValidateSet("CurrentUser", "LocalMachine")]
    [string]$Scope = "LocalMachine",
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
    $storeLocation = "Cert:\$Scope\Root"
    if ($ValidateOnly) { Write-Host "Validacion correcta para $storeLocation. No se modifico Windows."; return }
    if ($Scope -eq "LocalMachine") {
        $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            throw "Para toda la PC se necesita administrador. Sin esos permisos, ejecutar INSTALAR-SOLO-USUARIO.bat normalmente."
        }
    }
    $store = [Security.Cryptography.X509Certificates.X509Store]::new("Root", [Security.Cryptography.X509Certificates.StoreLocation]::$Scope)
    try {
        $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $existing = $store.Certificates.Find([Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint, $cert.Thumbprint, $false)
        if ($existing.Count -eq 0) { $store.Add($cert) }
    } finally { $store.Close() }
    $scopeLabel = if ($Scope -eq "CurrentUser") { "solo para tu usuario de Windows" } else { "para toda la PC" }
    Write-Host "Confianza instalada $scopeLabel. Cerrar y abrir el navegador; ingresar a la URL HTTPS de la LAN." -ForegroundColor Green
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

@echo off
setlocal
rem PriceBot LAN - certificado publico incorporado; no contiene claves privadas.
rem Ejecutar normalmente, con el usuario Windows que usara PriceBot.
set "PRICEBOT_SETUP_FILE=%~f0"
set "PRICEBOT_VALIDATE_ONLY="
set "PRICEBOT_NO_BROWSER="
if /I "%~1"=="--comprobar" set "PRICEBOT_VALIDATE_ONLY=1"
if /I "%~1"=="--sin-abrir" set "PRICEBOT_NO_BROWSER=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:PRICEBOT_SETUP_FILE); $m='# PRICEBOT_POWERSHELL_START'; $i=$t.LastIndexOf($m); if($i -lt 0){exit 1}; & ([ScriptBlock]::Create($t.Substring($i+$m.Length)))"
set "PRICEBOT_EXIT_CODE=%ERRORLEVEL%"
if not "%PRICEBOT_EXIT_CODE%"=="0" echo No se completo la configuracion. Revisar el error anterior.
if not defined PRICEBOT_VALIDATE_ONLY if not defined PRICEBOT_NO_BROWSER pause
endlocal & exit /b %PRICEBOT_EXIT_CODE%
# PRICEBOT_POWERSHELL_START
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$expectedSha256 = "E9A752ABC8A20E7E347ADE114A5BFCB3BD585AAD5EED4D2ED984C3BF27997DF3"
$serverIP = "192.168.190.146"
$certificateBase64 = "MIIENTCCAp2gAwIBAgIUXaeC29YVtnpjdGburf/uwCDdu94wDQYJKoZIhvcNAQELBQAwMTEVMBMGA1UECgwMUHJpY2VCb3QgTEFOMRgwFgYDVQQDDA9QcmljZUJvdCBMQU4gQ0EwHhcNMjYxMDEzMTgwOTE3WhcNMzExMDEyMTgxNDE3WjAxMRUwEwYDVQQKDAxQcmljZUJvdCBMQU4xGDAWBgNVBAMMD1ByaWNlQm90IExBTiBDQTCCAaIwDQYJKoZIhvcNAQEBBQADggGPADCCAYoCggGBALGJwP/Iq7zlujQWc2979iSG4DYDGD3lBVWuk5+Ujdh1eR0z7Cw3/RasCQlpJ3X8hAWZtCG7a9IX/WVpLXQYFxVbr0WEbnka94DrhPnT7AX/17ldDg/ImGubHosf4oLYlhC+4gubuqjkYBhFuVVv4IyyjrgHse/Sn+EsT+EqPx9xXRKHtkMcA2XOUbXLgDLNkgsQbZ05EmlRY3GNOiw6TnsPtEr8Nu4mmLlTptfnsEvgJHAn2hSBbPOVjc/2CbxZ7IvE3qJvpjXEJsGatkOWOjQwps5CHZx+ecCh3TVMLhoIKHGu+onrPPi1kldhIht1ULxLLXPDy1x64Z1+RvsTja5kv7GknQxXammAstIVhRKOrW+LIkf72ihPjOILVz7RIKaGW6o6CH7Bu77XVclIRHZnHo5S0aWqmqUKSEzS0WXruVD61+pRywk9zu+HkCIemcCo270yR823Im3m3erUReuwe+18bb5aiZQEswie84jzrAuwhrrgn68uL7o2mihqQwIDAQABo0UwQzASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjAdBgNVHQ4EFgQUpG29uxYi8UvdlpDzzLNHpwgBkjEwDQYJKoZIhvcNAQELBQADggGBAGGxpBN+X2pu85jmhvwRRAdic3MriXjladh/JOxA86XAQ7CjbfEGDf7w5R6FuZfNsXpoH5VtTwJV385xM7jar3Swx8vJVrYkuMqX20ylKFrPh3orcpq1KOSfEOkkJoOFuszI6RKA35lcAd+G+NYTtudlaGAj1fE7JmEWmdW/lYactWWd5+dmJYPAQOA8WJOMkZdhtA3ylIX+YWnwHsXSOUPiuqs25JTBPiREJ2t5rR2SboJPwlLUJJWNXnLqW8L01u2imc/tIQ1+iV4ACykEH1StZ73nltc/G7SFoK7T2aG9g52ffp/WLlNpwjz6ShDfbhzL8RzuAgbJhbPvWJb2S0RxqSkjeIX23D9LlQqmgdgjEre9yw4t69yD/dl8v/RVSfLEzqETo+4Jn0bFdvlw8LZ+qGZy01bK0ojsbkNpIbe0Rf2Y2fR/hkTRRNYMGa9ubL5oh/hoRuNelyBecC2LXcKTsKYfNxdet0Y75XKHfdZCiOrGJFzUDqOwQSFFNf/dcA=="
$validateOnly = $env:PRICEBOT_VALIDATE_ONLY -eq "1"
$temporaryCertificate = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName() + ".cer")
try {
    [IO.File]::WriteAllBytes($temporaryCertificate, [Convert]::FromBase64String($certificateBase64))
    & {
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

    } -CertificatePath $temporaryCertificate -ExpectedSha256 $expectedSha256 -Scope CurrentUser -ValidateOnly:$validateOnly
    if ($validateOnly) {
        Write-Host "Comprobacion completa. No se instalo confianza ni se abrio el navegador."
    } else {
        & {
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

        } -ServerIP $serverIP
        Write-Host "ACCESO CONFIGURADO para este usuario. URL: https://${serverIP}:3000/" -ForegroundColor Green
        if ($env:PRICEBOT_NO_BROWSER -ne "1") { Start-Process "https://${serverIP}:3000/" }
    }
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally {
    if (Test-Path -LiteralPath $temporaryCertificate) { Remove-Item -LiteralPath $temporaryCertificate }
}
exit 0

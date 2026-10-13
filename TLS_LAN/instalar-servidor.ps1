[CmdletBinding()]
param(
    [string]$ProjectPath = "",
    [string]$ServerIP = "192.168.190.146",
    [string]$AllowedSubnet = "192.168.190.0/24",
    [string]$ServiceAccount = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Clic derecho en INSTALAR-SERVIDOR.bat -> Ejecutar como administrador."
    }
    if (-not $ProjectPath) { $ProjectPath = Read-Host "Ruta del repo en esta PC (sin comillas)" }
    $ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
    if ($ProjectPath.Contains("'")) { throw "La ruta del proyecto no puede contener apostrofes para este lanzador." }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath "iniciar-servidor.bat"))) {
        throw "No se encontro el lanzador en esa carpeta."
    }
    $python = Join-Path $ProjectPath ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) { throw "Primero ejecuta instalar.bat en el repo para instalar las dependencias." }
    $appText = Get-Content -LiteralPath (Join-Path $ProjectPath "pricebot\frontend\app.js") -Raw
    if ($appText.Contains("? 'http://127.0.0.1:8000'")) { throw "El repo necesita git pull antes de instalar HTTPS." }
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq $ServerIP)
    if ($addresses.Count -eq 0) {
        throw "Esta PC no tiene la IP $ServerIP. Ejecuta el instalador en el servidor correcto."
    }
    $profiles = @(Get-NetConnectionProfile | Where-Object { $_.InterfaceIndex -in $addresses.InterfaceIndex })
    if (-not @($profiles | Where-Object NetworkCategory -eq "Private").Count) {
        throw "La interfaz del servidor debe tener perfil de red Privado. Configuralo en Windows antes de continuar."
    }
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in @(3000, 8000))
    if ($listeners.Count) { throw "Cierra las ventanas de PriceBot (puertos 3000 y 8000) antes de instalar o renovar. No se detienen procesos automaticamente." }
    if (-not $ServiceAccount) {
        $ServiceAccount = Read-Host "Cuenta Windows que inicia PriceBot (Enter para $($identity.Name))"
        if (-not $ServiceAccount) { $ServiceAccount = $identity.Name }
    }
    $serviceSid = (New-Object Security.Principal.NTAccount($ServiceAccount)).Translate([Security.Principal.SecurityIdentifier])
    Write-Host "Cuenta con permiso de lectura sobre la clave del servidor: $ServiceAccount"

    # No value of a secret is printed or modified by this preflight.
    $authCheck = @'
import os, sys
from pathlib import Path
from dotenv import load_dotenv
root = Path(sys.argv[1])
load_dotenv(root / 'pricebot' / 'api' / '.env', override=False)
load_dotenv(root / 'pricebot' / '.env', override=False)
if not os.getenv('PRICEBOT_SESSION_SECRET', '').strip():
    raise SystemExit('Falta PRICEBOT_SESSION_SECRET en la configuracion existente del servidor.')
'@
    & $python -c $authCheck $ProjectPath
    if ($LASTEXITCODE -ne 0) { throw "Configura el secreto de sesiones segun SETUP.md y vuelve a ejecutar." }
    & $python -c "import importlib.util, sys; s=importlib.util.find_spec('cryptography'); v=tuple(int(x) for x in __import__('cryptography').__version__.split('.')) if s else (0,); sys.exit(0 if (46,0,5) <= v < (51,) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Instalando dependencia de certificados en la .venv del proyecto..."
        & $python -m pip install --only-binary=:all: -r (Join-Path $PSScriptRoot "requirements-tls.txt")
        if ($LASTEXITCODE -ne 0) { throw "No se instalo cryptography. Se necesita Internet para esta dependencia." }
    }

    $tlsRoot = Join-Path ([Environment]::GetFolderPath("CommonApplicationData")) "PriceBotTLS"
    $marker = Join-Path $tlsRoot "managed-by-pricebot-tls.txt"
    if ((Test-Path -LiteralPath $tlsRoot) -and -not (Test-Path -LiteralPath $marker)) {
        throw "La carpeta $tlsRoot ya existe sin marca de este instalador. No se modificara."
    }
    if (-not (Test-Path -LiteralPath $tlsRoot)) { New-Item -ItemType Directory -Path $tlsRoot | Out-Null }

    function Protect-TlsDirectory([string]$Path, [bool]$ServiceRead) {
        $acl = Get-Acl -LiteralPath $Path
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleAll($rule) }
        $inheritance = [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
        foreach ($sid in @("S-1-5-18", "S-1-5-32-544")) {
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                [Security.Principal.SecurityIdentifier]::new($sid), "FullControl", $inheritance, "None", "Allow"
            ))
        }
        if ($ServiceRead -and $serviceSid.Value -notin @("S-1-5-18", "S-1-5-32-544")) {
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                $serviceSid, "ReadAndExecute", $inheritance, "None", "Allow"
            ))
        }
        Set-Acl -LiteralPath $Path -AclObject $acl
    }
    Protect-TlsDirectory $tlsRoot $true
    Set-Content -LiteralPath $marker -Value "PriceBot TLS LAN v1" -Encoding ASCII
    $caDirectory = Join-Path $tlsRoot "ca"
    if (-not (Test-Path -LiteralPath $caDirectory)) { New-Item -ItemType Directory -Path $caDirectory | Out-Null }
    Protect-TlsDirectory $caDirectory $false

    & $python (Join-Path $PSScriptRoot "generar_certificados.py") --directory $tlsRoot --server-ip $ServerIP --subnet $AllowedSubnet
    if ($LASTEXITCODE -ne 0) { throw "No se genero el certificado; no se cambio la configuracion de arranque." }
    $metadata = Get-Content -LiteralPath (Join-Path $tlsRoot "certificates.json") -Raw | ConvertFrom-Json
    & (Join-Path $PSScriptRoot "cliente\instalar-cliente.ps1") -CertificatePath (Join-Path $tlsRoot "PriceBot-CA.cer") -ExpectedSha256 $metadata.ca_sha256 -Scope LocalMachine
    if ($LASTEXITCODE -ne 0) { throw "No se instalo la confianza de la CA en el servidor." }

    $settings = [ordered]@{
        PRICEBOT_TLS_CERTFILE = (Join-Path $tlsRoot "server-cert.pem")
        PRICEBOT_TLS_KEYFILE = (Join-Path $tlsRoot "server-key.pem")
        PRICEBOT_REQUIRE_HTTPS = "1"
        PRICEBOT_COOKIE_SECURE = "1"
        PRICEBOT_AUTH_REQUIRED = "1"
        PRICEBOT_LOCAL_ADMIN_BYPASS = "1"
        PRICEBOT_BIND_HOST = "0.0.0.0"
        PRICEBOT_PUBLIC_URL = "https://${ServerIP}:3000"
        PRICEBOT_ALLOWED_ORIGINS = "https://${ServerIP}:3000,https://127.0.0.1:3000,https://localhost:3000"
        PRICEBOT_CSP_CONNECT_SRC = "'self' https://${ServerIP}:8000 https://127.0.0.1:8000 https://localhost:8000"
    }
    $previousFile = Join-Path $tlsRoot "environment-before-install.json"
    if (-not (Test-Path -LiteralPath $previousFile)) {
        $previous = [ordered]@{}
        foreach ($name in $settings.Keys) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Machine") }
        $previous | ConvertTo-Json | Set-Content -LiteralPath $previousFile -Encoding UTF8
    }
    foreach ($name in $settings.Keys) {
        [Environment]::SetEnvironmentVariable($name, $settings[$name], "Machine")
    }
    $config = [ordered]@{ project_path = $ProjectPath; service_account = $ServiceAccount; environment = $settings }
    $config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $tlsRoot "launch-config.json") -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "iniciar-seguro.ps1") -Destination $tlsRoot -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "INICIAR-PRICEBOT-SEGURO.bat") -Destination $tlsRoot -Force

    foreach ($rule in @(@{Name="PriceBot Web LAN"; Port=3000}, @{Name="PriceBot API LAN"; Port=8000})) {
        $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
        if ($existing) {
            $existing | Set-NetFirewallRule -Enabled True -Profile Private -Direction Inbound -Action Allow
            $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $rule.Port
            $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $AllowedSubnet -LocalAddress $ServerIP
        } else {
            New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Protocol TCP -LocalPort $rule.Port -LocalAddress $ServerIP -RemoteAddress $AllowedSubnet -Profile Private -Action Allow | Out-Null
        }
    }
    $clientFolder = Join-Path $tlsRoot "Clientes"
    if (-not (Test-Path -LiteralPath $clientFolder)) { New-Item -ItemType Directory -Path $clientFolder | Out-Null }
    foreach ($name in @("INSTALAR-CLIENTE.bat", "INSTALAR-SOLO-USUARIO.bat", "instalar-cliente.ps1", "verificar-conexion.ps1", "LEEME.md")) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot "cliente\$name") -Destination $clientFolder -Force
    }
    Copy-Item -LiteralPath (Join-Path $tlsRoot "PriceBot-CA.cer") -Destination $clientFolder -Force
    Compress-Archive -LiteralPath @(
        (Join-Path $clientFolder "INSTALAR-CLIENTE.bat"), (Join-Path $clientFolder "instalar-cliente.ps1"),
        (Join-Path $clientFolder "INSTALAR-SOLO-USUARIO.bat"),
        (Join-Path $clientFolder "verificar-conexion.ps1"), (Join-Path $clientFolder "LEEME.md"),
        (Join-Path $clientFolder "PriceBot-CA.cer")
    ) -DestinationPath (Join-Path $tlsRoot "Clientes-PriceBot.zip") -Force

    Write-Host "INSTALACION TERMINADA. Certificado del servidor vence: $($metadata.certificate_expires)" -ForegroundColor Green
    Write-Host "Iniciar: $tlsRoot\INICIAR-PRICEBOT-SEGURO.bat"
    Write-Host "Enviar a las PCs clientes SOLO: $tlsRoot\Clientes-PriceBot.zip"
    Write-Host "Comunicar por un canal confiable esta huella SHA-256: $($metadata.ca_sha256)"
    Write-Host "Administracion: https://127.0.0.1:3000 | Usuarios: https://${ServerIP}:3000"
    Write-Host "No copiar la carpeta ca ni server-key.pem. Guardar la frase de la CA en el gestor corporativo."
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

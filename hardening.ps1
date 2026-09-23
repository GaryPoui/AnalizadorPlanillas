# PriceBot - endurecimiento local para ejecutar como administrador en el servidor.
[CmdletBinding()]
param(
    [string]$AllowedSubnet = "192.168.190.0/24"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ejecuta hardening.ps1 desde PowerShell como administrador."
}

$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$envFile = Join-Path $projectRoot "pricebot\.env"
$dataDirectory = Join-Path $projectRoot "pricebot\api\data"
$costLog = Join-Path $projectRoot "costs_log.jsonl"

if (-not (Test-Path -LiteralPath $dataDirectory)) {
    New-Item -ItemType Directory -Path $dataDirectory | Out-Null
}

function Protect-PriceBotPath {
    param([Parameter(Mandatory)][string]$LiteralPath)
    if (-not (Test-Path -LiteralPath $LiteralPath)) { return }

    $resolved = (Resolve-Path -LiteralPath $LiteralPath).Path
    if (-not $resolved.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta fuera del proyecto: $resolved"
    }

    $acl = Get-Acl -LiteralPath $resolved
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        [void]$acl.RemoveAccessRuleAll($rule)
    }

    $rights = [Security.AccessControl.FileSystemRights]::FullControl
    $inheritance = if ((Get-Item -LiteralPath $resolved).PSIsContainer) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else {
        [Security.AccessControl.InheritanceFlags]::None
    }
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $identities = @(
        [Security.Principal.WindowsIdentity]::GetCurrent().User,
        [Security.Principal.SecurityIdentifier]::new("S-1-5-18"),
        [Security.Principal.SecurityIdentifier]::new("S-1-5-32-544")
    )
    foreach ($identity in $identities) {
        $accessRule = [Security.AccessControl.FileSystemAccessRule]::new(
            $identity, $rights, $inheritance, $propagation, $allow
        )
        $acl.AddAccessRule($accessRule)
    }
    Set-Acl -LiteralPath $resolved -AclObject $acl
}

Protect-PriceBotPath -LiteralPath $envFile
Protect-PriceBotPath -LiteralPath $dataDirectory
Protect-PriceBotPath -LiteralPath $costLog

$rules = @(
    @{ Name = "PriceBot Web LAN"; Port = 3000 },
    @{ Name = "PriceBot API LAN"; Port = 8000 }
)
foreach ($definition in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $definition.Name -ErrorAction SilentlyContinue
    if ($existing) {
        $existing | Set-NetFirewallRule -Enabled True -Profile Private -Direction Inbound -Action Allow
        $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $definition.Port
        $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $AllowedSubnet
    } else {
        New-NetFirewallRule `
            -DisplayName $definition.Name `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $definition.Port `
            -RemoteAddress $AllowedSubnet `
            -Profile Private `
            -Action Allow | Out-Null
    }
}

Write-Host "PriceBot endurecido para la subred $AllowedSubnet." -ForegroundColor Green
Write-Host "Los permisos de .env/data y las reglas de firewall fueron restringidos." -ForegroundColor Green
Write-Host "No se configuró TLS: instala un certificado antes de habilitar acceso remoto." -ForegroundColor Yellow

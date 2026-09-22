# PriceBot - instalador de dependencias para Windows
# Uso recomendado: ejecutar instalar.bat desde la raiz del repositorio.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$requirementsFile = Join-Path $projectRoot "pricebot\api\requirements.txt"
$virtualEnvDir = Join-Path $projectRoot ".venv"
$virtualEnvPython = Join-Path $virtualEnvDir "Scripts\python.exe"
$exampleEnv = Join-Path $projectRoot "pricebot\.env.example"
$localEnv = Join-Path $projectRoot "pricebot\.env"

Write-Host ""
Write-Host "  PriceBot - instalacion automatica" -ForegroundColor Cyan
Write-Host "  ----------------------------------------" -ForegroundColor DarkGray

if (-not (Test-Path -LiteralPath $requirementsFile)) {
    Write-Host "  ERROR: no se encontro $requirementsFile" -ForegroundColor Red
    exit 1
}

$bootstrapPython = $null
$bootstrapArgs = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $bootstrapPython = (Get-Command py).Source
        $bootstrapArgs = @("-3")
    }
}

if (-not $bootstrapPython -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $bootstrapPython = (Get-Command python).Source
    }
}

if (-not $bootstrapPython) {
    Write-Host ""
    Write-Host "  ERROR: se necesita Python 3.11 o superior." -ForegroundColor Red
    Write-Host "  Instalalo desde https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Write-Host "  Durante la instalacion activa la opcion 'Add Python to PATH'." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path -LiteralPath $virtualEnvPython)) {
    Write-Host "  Creando entorno virtual .venv..." -ForegroundColor Cyan
    & $bootstrapPython @bootstrapArgs -m venv $virtualEnvDir
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el entorno virtual."
    }
} else {
    Write-Host "  Entorno virtual existente: .venv" -ForegroundColor Green
}

Write-Host "  Actualizando instalador de paquetes..." -ForegroundColor Cyan
& $virtualEnvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo actualizar pip."
}

Write-Host "  Instalando todas las dependencias de PriceBot..." -ForegroundColor Cyan
& $virtualEnvPython -m pip install -r $requirementsFile
if ($LASTEXITCODE -ne 0) {
    throw "Fallo la instalacion de dependencias."
}

Write-Host "  Verificando librerias principales..." -ForegroundColor Cyan
& $virtualEnvPython -c "import a2wsgi, aiofiles, fastapi, httpx, markitdown, multipart, openpyxl, pandas, pdfplumber, PIL, pytesseract, uvicorn, xlrd, xlwt; from docx import Document; print('  Librerias Python verificadas correctamente')"
if ($LASTEXITCODE -ne 0) {
    throw "La verificacion de librerias no fue satisfactoria."
}

if (-not (Test-Path -LiteralPath $localEnv) -and (Test-Path -LiteralPath $exampleEnv)) {
    Copy-Item -LiteralPath $exampleEnv -Destination $localEnv
    Write-Host "  Se creo pricebot\.env desde el ejemplo." -ForegroundColor Yellow
    Write-Host "  Editalo y completa ANTHROPIC_API_KEY y los usuarios antes de publicar." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Instalacion terminada correctamente." -ForegroundColor Green
Write-Host "  Para iniciar el sistema ejecuta: start.bat" -ForegroundColor Cyan

if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "  Aviso: Tesseract OCR no esta instalado." -ForegroundColor Yellow
    Write-Host "  Solo es necesario para PDFs escaneados sin texto seleccionable." -ForegroundColor Yellow
}

Write-Host ""

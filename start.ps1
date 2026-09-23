# PriceBot — script de inicio
# Uso: .\start.ps1
# Levanta el backend en una nueva ventana y abre el frontend en el navegador.

$ROOT     = $PSScriptRoot
$PYTHON   = Join-Path $ROOT ".venv\Scripts\python.exe"
$API_DIR  = Join-Path $ROOT "pricebot\api"
$FRONTEND_DIR = Join-Path $ROOT "pricebot\frontend"
$FRONTEND_SERVER = Join-Path $ROOT "pricebot\frontend_server.py"
$PORT     = 8000
$BIND_HOST = if ($env:PRICEBOT_BIND_HOST) { $env:PRICEBOT_BIND_HOST } else { "127.0.0.1" }
$TLS_CERT = if ($env:PRICEBOT_TLS_CERTFILE) { $env:PRICEBOT_TLS_CERTFILE } else { "" }
$TLS_KEY = if ($env:PRICEBOT_TLS_KEYFILE) { $env:PRICEBOT_TLS_KEYFILE } else { "" }

if ([bool]$TLS_CERT -ne [bool]$TLS_KEY) {
    Write-Host "  ERROR: TLS requiere PRICEBOT_TLS_CERTFILE y PRICEBOT_TLS_KEYFILE." -ForegroundColor Red
    exit 1
}
if ($TLS_CERT -and (-not (Test-Path -LiteralPath $TLS_CERT) -or -not (Test-Path -LiteralPath $TLS_KEY))) {
    Write-Host "  ERROR: no se encontraron el certificado o la clave TLS." -ForegroundColor Red
    exit 1
}

$SCHEME = if ($TLS_CERT) { "https" } else { "http" }
$FRONTEND_URL = "$SCHEME`://127.0.0.1:3000"

if (-not (Test-Path -LiteralPath $PYTHON)) {
    Write-Host ""
    Write-Host "  ERROR: faltan las dependencias del proyecto." -ForegroundColor Red
    Write-Host "  Ejecuta instalar.bat y vuelve a intentar." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "  PriceBot - iniciando" -ForegroundColor Cyan
Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

# Verificar si ya hay algo corriendo en el puerto
$busy = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("localhost", $PORT)
    $conn.Close()
    $busy = $true
} catch {}

if ($busy) {
    Write-Host "  El backend ya está corriendo en :$PORT" -ForegroundColor Yellow
} else {
    # Levantar uvicorn en una nueva ventana de consola
    $reloadArg = if ($env:PRICEBOT_RELOAD -eq "1") { " --reload" } else { "" }
    $tlsArgs = if ($TLS_CERT) { " --ssl-certfile '$TLS_CERT' --ssl-keyfile '$TLS_KEY'" } else { "" }
    $cmd = "& '$PYTHON' -m uvicorn main:app --host $BIND_HOST --port $PORT$reloadArg$tlsArgs --app-dir '$API_DIR'; pause"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd -WindowStyle Normal
    Write-Host "  Backend iniciado en nueva ventana" -ForegroundColor Green

    # Esperar a que el servidor responda
    Write-Host "  Esperando que el servidor arranque..." -ForegroundColor DarkGray
    $tries = 0
    $ready = $false

    while ($tries -lt 15 -and -not $ready) {
        Start-Sleep -Milliseconds 600
        $tries++

        try {
            $readyConn = New-Object System.Net.Sockets.TcpClient
            $readyConn.Connect("localhost", $PORT)
            $readyConn.Close()
            $ready = $true
        } catch {}
    }

    if ($ready) {
        Write-Host "  Servidor listo" -ForegroundColor Green
    } else {
        Write-Host "  Advertencia: el servidor tardó más de lo esperado" -ForegroundColor Yellow
    }
}

# Servir el frontend en el puerto 3000
$frontendBusy = $false

try {
    $frontendConn = New-Object System.Net.Sockets.TcpClient
    $frontendConn.Connect("localhost", 3000)
    $frontendConn.Close()
    $frontendBusy = $true
} catch {}

if (-not $frontendBusy) {
    $frontendTlsArgs = if ($TLS_CERT) { " --ssl-certfile '$TLS_CERT' --ssl-keyfile '$TLS_KEY'" } else { "" }
    $frontendCmd = "& '$PYTHON' '$FRONTEND_SERVER' --port 3000 --bind '$BIND_HOST' --directory '$FRONTEND_DIR'$frontendTlsArgs; pause"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
}

Start-Process $FRONTEND_URL

Write-Host ""
Write-Host "  Backend:  $SCHEME`://$BIND_HOST`:$PORT" -ForegroundColor Cyan
if ($env:PRICEBOT_ENABLE_API_DOCS -eq "1") {
    Write-Host "  Docs API: $SCHEME`://localhost:$PORT/docs" -ForegroundColor Cyan
}
Write-Host "  Frontend: $FRONTEND_URL" -ForegroundColor Cyan
if (-not $TLS_CERT -and $BIND_HOST -ne "127.0.0.1") {
    Write-Host "  SEGURIDAD: sin TLS, la API rechazara conexiones remotas por defecto." -ForegroundColor Yellow
}
Write-Host ""


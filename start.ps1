# PriceBot — script de inicio
# Uso: .\start.ps1
# Levanta el backend en una nueva ventana y abre el frontend en el navegador.

$PYTHON   = "C:\Users\Pasante\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$ROOT     = $PSScriptRoot
$API_DIR  = Join-Path $ROOT "pricebot\api"
$FRONTEND_DIR = Join-Path $ROOT "pricebot\frontend"
$FRONTEND_URL = "http://127.0.0.1:3000"
$PORT     = 8000
$BIND_HOST = if ($env:PRICEBOT_BIND_HOST) { $env:PRICEBOT_BIND_HOST } else { "127.0.0.1" }

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
    $cmd = "& '$PYTHON' -m uvicorn main:app --host $BIND_HOST --port $PORT --reload --app-dir '$API_DIR'; pause"
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
            $r = Invoke-WebRequest -Uri "http://localhost:$PORT/" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            $ready = $true
        } catch {}
    }

    if ($ready) {
        Write-Host "  Servidor listo" -ForegroundColor Green
    } else {
        Write-Host "  Advertencia: el servidor tardó más de lo esperado" -ForegroundColor Yellow
    }
}

# Serve the frontend on a fixed local origin so CORS can remain restricted.
$frontendBusy = $false
try {
    $frontendConn = New-Object System.Net.Sockets.TcpClient
    $frontendConn.Connect("localhost", 3000)
    $frontendConn.Close()
    $frontendBusy = $true
} catch {}

if (-not $frontendBusy) {
    $frontendCmd = "& '$PYTHON' -m http.server 3000 --bind $BIND_HOST --directory '$FRONTEND_DIR'; pause"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
}

Start-Process $FRONTEND_URL

Write-Host ""
Write-Host "  Backend:  http://$BIND_HOST`:$PORT" -ForegroundColor Cyan
Write-Host "  Docs API: http://localhost:$PORT/docs" -ForegroundColor Cyan
Write-Host "  Frontend: $FRONTEND_URL" -ForegroundColor Cyan
Write-Host ""

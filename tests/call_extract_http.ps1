# Llama al endpoint /extract via HTTP con lista95.pdf y guarda métricas básicas.
# Requiere que la API esté corriendo en localhost:8000.
# Uso: powershell -File tests\call_extract_http.ps1

$ErrorActionPreference = 'Stop'

$pdf = Join-Path $PSScriptRoot 'samples\lista95.pdf'
if (-not (Test-Path $pdf)) {
    throw "PDF no encontrado: $pdf"
}

Add-Type -AssemblyName System.Net.Http
$client = [System.Net.Http.HttpClient]::new()
$multi  = [System.Net.Http.MultipartFormDataContent]::new()
$bytes  = [System.IO.File]::ReadAllBytes($pdf)
$fc     = [System.Net.Http.ByteArrayContent]::new($bytes)
$fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
$multi.Add($fc, 'file', 'lista95.pdf')

$resp   = $client.PostAsync('http://127.0.0.1:8000/extract', $multi).GetAwaiter().GetResult()
$status = [int]$resp.StatusCode
$body   = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()
$obj    = $body | ConvertFrom-Json

$result = [ordered]@{
    status_code   = $status
    total_rows    = $obj.report.total_rows
    quality_score = $obj.report.quality_score
}

$outPath = Join-Path $PSScriptRoot 'outputs\extract_metrics.json'
$result | ConvertTo-Json | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Guardado en $outPath"
$result | ConvertTo-Json

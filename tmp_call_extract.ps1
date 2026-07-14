$ErrorActionPreference = 'Stop'

$pdf = 'lista95.pdf'
if (-not (Test-Path $pdf)) {
  $alt = Get-ChildItem -File -Filter '*.pdf' | Where-Object { $_.Name -like 'Lista de Precios*95*' } | Select-Object -First 1
  if ($alt) {
    Copy-Item -Path $alt.FullName -Destination $pdf -Force
  }
}

if (-not (Test-Path $pdf)) {
  throw 'PDF not found'
}

Add-Type -AssemblyName System.Net.Http
$client = [System.Net.Http.HttpClient]::new()
$multi = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $pdf))
$fc = [System.Net.Http.ByteArrayContent]::new($bytes)
$fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
$multi.Add($fc, 'file', 'lista95.pdf')

$resp = $client.PostAsync('http://127.0.0.1:8000/extract', $multi).GetAwaiter().GetResult()
$status = [int]$resp.StatusCode
$body = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()
$obj = $body | ConvertFrom-Json

$result = [ordered]@{
  status_code = $status
  total_rows = $obj.report.total_rows
  quality_score = $obj.report.quality_score
}

$result | ConvertTo-Json | Set-Content -Path 'tmp_extract_metrics.json' -Encoding UTF8

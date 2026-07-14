$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Net.Http

$pdf = 'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'
if (-not (Test-Path $pdf)) {
    throw "PDF not found: $pdf"
}

$client = [System.Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromMinutes(10)
$multi = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes($pdf)
$fc = [System.Net.Http.ByteArrayContent]::new($bytes)
$fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
$multi.Add($fc, 'file', 'LCT Lista de Precios 02-2026 (3).pdf')

$resp = $client.PostAsync('http://127.0.0.1:8000/extract', $multi).GetAwaiter().GetResult()
$status = [int]$resp.StatusCode
$body = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()
$obj = $body | ConvertFrom-Json

$codes = @()
if ($obj.rows) {
    $codes = @(
        $obj.rows |
            ForEach-Object { $_.'Cód. Artículo' } |
            Where-Object { $_ -and $_.ToString().Trim().Length -gt 0 } |
            Select-Object -First 20
    )
}

$summary = [ordered]@{
    status_code = $status
    total_rows = $obj.report.total_rows
    valid_rows = $obj.report.valid_rows
    quality_score = $obj.report.quality_score
    first_20_codes = $codes
    extraction_method = $obj.extraction_method
    has_adaptive_recovery = ($obj.PSObject.Properties.Name -contains 'adaptive_recovery')
}

if ($obj.PSObject.Properties.Name -contains 'ai_fallback') {
    $summary.ai_fallback = $obj.ai_fallback
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path 'c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_extract_summary.json' -Encoding UTF8
Write-Output 'DONE'

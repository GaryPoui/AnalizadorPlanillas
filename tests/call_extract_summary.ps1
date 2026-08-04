# Llama al endpoint /extract via HTTP con lct_02_2026.pdf y muestra resumen detallado.
# Requiere que la API esté corriendo en localhost:8000.
# Uso: powershell -File tests\call_extract_summary.ps1

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$pdf = Join-Path $PSScriptRoot 'samples\lct_02_2026.pdf'
if (-not (Test-Path $pdf)) {
    throw "PDF no encontrado: $pdf"
}

$client = [System.Net.Http.HttpClient]::new()
$multi  = [System.Net.Http.MultipartFormDataContent]::new()
$bytes  = [System.IO.File]::ReadAllBytes($pdf)
$fc     = [System.Net.Http.ByteArrayContent]::new($bytes)
$fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
$multi.Add($fc, 'file', 'lct_02_2026.pdf')

$resp   = $client.PostAsync('http://127.0.0.1:8000/extract', $multi).GetAwaiter().GetResult()
$status = [int]$resp.StatusCode
$raw    = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()

$obj = $null
try { $obj = $raw | ConvertFrom-Json } catch { $obj = $null }

$codes = @()
if ($obj -and $obj.rows) {
    foreach ($r in $obj.rows) {
        if ($r.'Cód. Artículo') { $codes += [string]$r.'Cód. Artículo' }
    }
    $codes = @($codes | Select-Object -First 20)
}

$aiFallback  = if ($obj -and ($obj.PSObject.Properties.Name -contains 'ai_fallback')) { $obj.ai_fallback } else { $null }
$errorDetail = if ($obj -and ($obj.PSObject.Properties.Name -contains 'detail')) { $obj.detail }
               elseif ($obj -and ($obj.PSObject.Properties.Name -contains 'error')) { $obj.error }
               elseif (-not $obj) { $raw } else { $null }

$summary = [ordered]@{
    status      = $status
    report      = [ordered]@{
        total_rows    = if ($obj -and $obj.report) { $obj.report.total_rows }    else { $null }
        valid_rows    = if ($obj -and $obj.report) { $obj.report.valid_rows }    else { $null }
        quality_score = if ($obj -and $obj.report) { $obj.report.quality_score } else { $null }
    }
    ai_fallback     = $aiFallback
    first_20_codes  = $codes
    error_detail    = $errorDetail
}

$summary | ConvertTo-Json -Depth 10

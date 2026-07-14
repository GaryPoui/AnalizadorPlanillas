$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$pdf = 'c:\Users\Pasante\Desktop\AnalizadorPlanillas\LCT Lista de Precios 02-2026 (3).pdf'

$client = [System.Net.Http.HttpClient]::new()
$multi = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes($pdf)
$fc = [System.Net.Http.ByteArrayContent]::new($bytes)
$fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/pdf')
$multi.Add($fc, 'file', 'LCT Lista de Precios 02-2026 (3).pdf')

$resp = $client.PostAsync('http://127.0.0.1:8000/extract', $multi).GetAwaiter().GetResult()
$status = [int]$resp.StatusCode
$raw = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()

[System.IO.File]::WriteAllText('c:\Users\Pasante\Desktop\AnalizadorPlanillas\tmp_extract_response.json', $raw)

$obj = $null
try {
    $obj = $raw | ConvertFrom-Json
} catch {
    $obj = $null
}

$codes = @()
if ($obj -and $obj.rows) {
    foreach ($r in $obj.rows) {
        if ($r.'Cód. Artículo') {
            $codes += [string]$r.'Cód. Artículo'
        }
    }
    $codes = @($codes | Select-Object -First 20)
}

$aiFallback = $null
if ($obj -and ($obj.PSObject.Properties.Name -contains 'ai_fallback')) {
    $aiFallback = $obj.ai_fallback
}

$errorDetail = $null
if ($obj -and ($obj.PSObject.Properties.Name -contains 'detail')) {
    $errorDetail = $obj.detail
} elseif ($obj -and ($obj.PSObject.Properties.Name -contains 'error')) {
    $errorDetail = $obj.error
} elseif (-not $obj) {
    $errorDetail = $raw
}

$summary = [ordered]@{
    status = $status
    report = [ordered]@{
        total_rows = if ($obj -and $obj.report) { $obj.report.total_rows } else { $null }
        valid_rows = if ($obj -and $obj.report) { $obj.report.valid_rows } else { $null }
        quality_score = if ($obj -and $obj.report) { $obj.report.quality_score } else { $null }
    }
    ai_fallback = $aiFallback
    first_20_codes = $codes
    error_detail = $errorDetail
}

$summary | ConvertTo-Json -Depth 10

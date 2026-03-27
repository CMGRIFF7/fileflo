$file = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json'
$raw = Get-Content $file -Raw
Write-Host "File size: $($raw.Length) chars"
Write-Host "First 500 chars:"
Write-Host $raw.Substring(0, [Math]::Min(500, $raw.Length))
Write-Host "..."

# Try to parse
try {
    $parsed = $raw | ConvertFrom-Json
    Write-Host "Type: $($parsed.GetType().Name)"
    if ($parsed -is [System.Array]) {
        Write-Host "Array length: $($parsed.Count)"
        Write-Host "First element type: $($parsed[0].GetType().Name)"
        Write-Host "First element keys: $($parsed[0].PSObject.Properties.Name -join ', ')"
    } else {
        Write-Host "Object keys: $($parsed.PSObject.Properties.Name -join ', ')"
    }
} catch {
    Write-Host "Parse error: $_"
    # Try as array of tool result blocks
    Write-Host "Raw start: $($raw.Substring(0,[Math]::Min(200,$raw.Length)))"
}

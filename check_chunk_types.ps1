# Check headers across chunks to separate inspection vs violation files
# Also sample the FMCSA file structure

$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$files = Get-ChildItem $dir -Filter '*.csv' | Sort-Object Name

$inspHeaders  = $null
$violHeaders  = $null
$inspChunks   = 0
$violChunks   = 0
$otherChunks  = 0

Write-Host "Scanning headers across all $($files.Count) chunks..."

foreach ($f in $files) {
    $header = (Get-Content $f.FullName -TotalCount 1).Trim()

    if ($header -match 'ACTIVITY_NR.*ESTAB_NAME.*NAICS_CODE.*OPEN_DATE') {
        $inspChunks++
        if (-not $inspHeaders) { $inspHeaders = $header }
    }
    elseif ($header -match 'ACTIVITY_NR.*STANDARD_CITED|PENALTY_ISSUED|ISSUEDESCRIPTION') {
        $violChunks++
        if (-not $violHeaders) { $violHeaders = $header }
    }
    else {
        $otherChunks++
        Write-Host "UNKNOWN HEADER in $($f.Name): $($header.Substring(0, [Math]::Min(120, $header.Length)))"
    }
}

Write-Host "`nInspection chunks: $inspChunks"
Write-Host "Violation chunks:  $violChunks"
Write-Host "Other chunks:      $otherChunks"

if ($violHeaders) {
    Write-Host "`nViolation headers:"
    Write-Host $violHeaders
} else {
    Write-Host "`nNO VIOLATION CHUNKS FOUND - checking if same file has both..."
    Write-Host "`nSample inspection headers:"
    Write-Host $inspHeaders

    # Check if OSHA_violation.zip extracted differently - look for any penalty-related column
    Write-Host "`nSearching for PENALTY columns in any chunk header..."
    foreach ($f in ($files | Select-Object -First 20)) {
        $h = Get-Content $f.FullName -TotalCount 1
        if ($h -match 'PENALTY|VIOLATION|STANDARD|CITATION') {
            Write-Host "Found in $($f.Name): $h"
        }
    }
}

# FMCSA structure deep dive
Write-Host "`n=== FMCSA STRUCTURE ==="
$fmcsa = 'C:\Users\ChadGriffith\Downloads\rbkj-cgst_version_108.csv'
$headers = (Get-Content $fmcsa -TotalCount 1) -split ','
Write-Host "Column count: $($headers.Count)"
Write-Host "All columns:"
$headers | ForEach-Object { Write-Host "  $_" }

Write-Host "`nSample rows (2-4):"
Get-Content $fmcsa -TotalCount 4 | Select-Object -Skip 1

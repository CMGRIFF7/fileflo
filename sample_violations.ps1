$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$violFiles = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' | Sort-Object Name | Select-Object -First 3

# Print headers
$headers = Get-Content $violFiles[0].FullName -TotalCount 1
Write-Host "VIOLATION HEADERS:"
Write-Host $headers

Write-Host ""
Write-Host "=== SAMPLE VIOLATION ROWS (first 20 from each of 3 chunks) ==="
foreach ($f in $violFiles) {
    Write-Host "--- $($f.Name) ---"
    Get-Content $f.FullName -TotalCount 21 | Select-Object -Skip 1
    Write-Host ""
}

# Also find rows where CURRENT_PENALTY > 0 in first chunk
Write-Host "=== ROWS WITH PENALTY > 0 (first 20 found) ==="
$reader = [System.IO.StreamReader]::new($violFiles[0].FullName)
$hdr = $reader.ReadLine() -split ','
$idxPenalty = [Array]::IndexOf($hdr, 'CURRENT_PENALTY')
$idxStd = [Array]::IndexOf($hdr, 'STANDARD')
$idxVt = [Array]::IndexOf($hdr, 'VIOL_TYPE')
Write-Host "CURRENT_PENALTY index: $idxPenalty"
Write-Host "STANDARD index: $idxStd"
$found = 0
while ($null -ne ($line = $reader.ReadLine()) -and $found -lt 20) {
    $cols = $line -split ','
    $pen = $cols[$idxPenalty].Trim().Trim('"')
    if ($pen -ne '' -and $pen -ne '0' -and $pen -ne 'null') {
        Write-Host "STANDARD='$($cols[$idxStd])' | VIOL_TYPE='$($cols[$idxVt])' | PENALTY='$pen'"
        $found++
    }
}
$reader.Close()

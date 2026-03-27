# Verify: do inspections from 2010-2016 have ACTIVITY_NRs that match violation data?
$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$targetStates = @('TX','CA','FL','GA','IL','NY','OH')
$targetNaics = @('238','484')

$sampleIds = @()
$inspFiles = Get-ChildItem $dir -Filter '*04-17-12*chunk*.csv' |
    Sort-Object { [int]($_.Name -replace '.*chunk_(\d+)\.csv$','$1') } |
    Select-Object -First 15   # scan first 15 numerical chunks

Write-Host "Scanning first 15 chunks for 2008-2016 qualifying inspections..."
foreach ($f in $inspFiles) {
    if ($sampleIds.Count -ge 30) { break }
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct   = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxState = [Array]::IndexOf($headers, 'SITE_STATE')
    $idxNaics = [Array]::IndexOf($headers, 'NAICS_CODE')
    $idxDate  = [Array]::IndexOf($headers, 'OPEN_DATE')
    $idxName  = [Array]::IndexOf($headers, 'ESTAB_NAME')

    while ($null -ne ($line = $reader.ReadLine()) -and $sampleIds.Count -lt 30) {
        $cols  = $line -split ','
        $state = $cols[$idxState].Trim().Trim('"')
        $naics = $cols[$idxNaics].Trim().Trim('"')
        $date  = $cols[$idxDate].Trim().Trim('"')
        $actNr = $cols[$idxAct].Trim().Trim('"')

        $naicsMatch = $false
        foreach ($p in $targetNaics) { if ($naics.StartsWith($p)) { $naicsMatch = $true; break } }

        # 2008-2016 range — overlaps with violation data
        if ($targetStates -contains $state -and $naicsMatch -and $date -match '^201[0-6]|^200[89]') {
            $name = $cols[$idxName].Trim().Trim('"')
            $sampleIds += $actNr
            if ($sampleIds.Count -le 5) {
                Write-Host "  Found: $actNr | $name | $state | $naics | $date"
            }
        }
    }
    $reader.Close()
}
Write-Host "Total 2008-2016 qualifying IDs found: $($sampleIds.Count)"
Write-Host "Sample IDs: $($sampleIds[0..4] -join ', ')"

Write-Host ""
Write-Host "=== CHECKING IF THESE APPEAR IN VIOLATION DATA ==="
# Check first 20 violation chunks numerically (should cover ~300M-313M range)
$violFiles = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' |
    Sort-Object { [int]($_.Name -replace '.*chunk_(\d+)\.csv$','$1') } -Descending |
    Select-Object -First 30

$foundCount = 0
foreach ($f in $violFiles) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct  = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    while ($null -ne ($line = $reader.ReadLine())) {
        $cols  = $line -split ','
        $actNr = $cols[$idxAct].Trim().Trim('"')
        if ($sampleIds -contains $actNr) {
            $foundCount++
            if ($foundCount -le 5) { Write-Host "  MATCH: $actNr in $($f.Name)" }
        }
    }
    $reader.Close()
    if ($foundCount -ge 10) { break }
}
Write-Host "Total matches found: $foundCount"

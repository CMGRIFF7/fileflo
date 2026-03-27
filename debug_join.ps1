$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'

# Get a small sample of qualifying inspection ACTIVITY_NRs (2022+, target states, construction/trucking)
Write-Host "=== SAMPLING QUALIFYING INSPECTION ACTIVITY_NRs ==="
$inspFiles = Get-ChildItem $dir -Filter '*04-17-12*chunk*.csv' | Sort-Object Name
$sampleIds = @()
$targetStates = @('TX','CA','FL','GA','IL','NY','OH')
$targetNaics = @('238','484')

foreach ($f in $inspFiles) {
    if ($sampleIds.Count -ge 20) { break }
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxState = [Array]::IndexOf($headers, 'SITE_STATE')
    $idxNaics = [Array]::IndexOf($headers, 'NAICS_CODE')
    $idxDate = [Array]::IndexOf($headers, 'OPEN_DATE')

    while ($null -ne ($line = $reader.ReadLine()) -and $sampleIds.Count -lt 20) {
        $cols = $line -split ','
        $state = $cols[$idxState].Trim().Trim('"')
        $naics = $cols[$idxNaics].Trim().Trim('"')
        $date = $cols[$idxDate].Trim().Trim('"')
        $naicsMatch = $false
        foreach ($p in $targetNaics) { if ($naics.StartsWith($p)) { $naicsMatch = $true; break } }
        if ($targetStates -contains $state -and $naicsMatch -and $date -match '^202') {
            $sampleIds += $cols[$idxAct].Trim().Trim('"')
            Write-Host "  ACTIVITY_NR='$($cols[$idxAct].Trim().Trim('"'))' | state=$state | naics=$naics | date=$date"
        }
    }
    $reader.Close()
}

Write-Host ""
Write-Host "=== CHECKING IF ANY OF THESE IDs APPEAR IN VIOLATION DATA ==="
$violFiles = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' | Sort-Object Name | Select-Object -Last 10

Write-Host "Checking last 10 violation chunks (likely most recent data)..."
$foundCount = 0
foreach ($f in $violFiles) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxDate = [Array]::IndexOf($headers, 'ISSUANCE_DATE')

    $chunkSample = 0
    while ($null -ne ($line = $reader.ReadLine())) {
        $cols = $line -split ','
        $actNr = $cols[$idxAct].Trim().Trim('"')
        if ($sampleIds -contains $actNr) {
            Write-Host "  MATCH FOUND: $actNr in $($f.Name)"
            $foundCount++
        }
        $chunkSample++
        if ($chunkSample -le 3) {
            $iDate = $cols[$idxDate].Trim().Trim('"')
            Write-Host "  Sample from $($f.Name): ACTIVITY_NR=$actNr | ISSUANCE_DATE=$iDate"
        }
    }
    $reader.Close()
    if ($foundCount -gt 5) { break }
}

Write-Host ""
Write-Host "Total matches found: $foundCount"
Write-Host ""

# Check what year range is in the violation data
Write-Host "=== ISSUANCE_DATE RANGE IN VIOLATION DATA ==="
$lastChunk = $violFiles | Select-Object -Last 1
$reader = [System.IO.StreamReader]::new($lastChunk.FullName)
$headers = ($reader.ReadLine()) -split ','
$idxDate = [Array]::IndexOf($headers, 'ISSUANCE_DATE')
$dates = @()
$count = 0
while ($null -ne ($line = $reader.ReadLine()) -and $count -lt 1000) {
    $cols = $line -split ','
    $d = $cols[$idxDate].Trim().Trim('"')
    if ($d -match '^\d{4}') { $dates += $d.Substring(0,4) }
    $count++
}
$reader.Close()
$dates | Group-Object | Sort-Object Name | Select-Object Name, Count | Format-Table

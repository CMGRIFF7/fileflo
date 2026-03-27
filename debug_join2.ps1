$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'

# Sort NUMERICALLY by chunk number (not alphabetically)
$violFiles = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' |
    Sort-Object { [int]($_.Name -replace '.*chunk_(\d+)\.csv$','$1') } -Descending |
    Select-Object -First 15

Write-Host "Last 15 violation chunks by chunk NUMBER:"
foreach ($f in $violFiles) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxDate = [Array]::IndexOf($headers, 'ISSUANCE_DATE')
    $line = $reader.ReadLine()
    $reader.Close()
    if ($line) {
        $cols = $line -split ','
        $actNr = $cols[$idxAct].Trim().Trim('"')
        $iDate = $cols[$idxDate].Trim().Trim('"')
        Write-Host "  $($f.Name): ACTIVITY_NR=$actNr | ISSUANCE_DATE=$iDate"
    }
}

Write-Host ""
Write-Host "=== NOW CHECKING IF QUALIFYING INSPECTION IDs APPEAR IN RECENT VIOLATION CHUNKS ==="

# Sample inspection ACTIVITY_NRs
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
        }
    }
    $reader.Close()
}
Write-Host "Sampled $($sampleIds.Count) qualifying inspection ACTIVITY_NRs: $($sampleIds[0..4] -join ', ')..."

# Check the NUMERICALLY LAST 20 violation chunks for those IDs
$recentViolChunks = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' |
    Sort-Object { [int]($_.Name -replace '.*chunk_(\d+)\.csv$','$1') } -Descending |
    Select-Object -First 20

$foundCount = 0
foreach ($f in $recentViolChunks) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxDate = [Array]::IndexOf($headers, 'ISSUANCE_DATE')

    $firstRow = $reader.ReadLine()
    if ($firstRow) {
        $cols = $firstRow -split ','
        $firstActNr = $cols[$idxAct].Trim().Trim('"')
        $firstDate = $cols[$idxDate].Trim().Trim('"')
        Write-Host "  Chunk $($f.Name): first ACTIVITY_NR=$firstActNr ($firstDate)"
    }

    while ($null -ne ($line = $reader.ReadLine())) {
        $cols = $line -split ','
        $actNr = $cols[$idxAct].Trim().Trim('"')
        if ($sampleIds -contains $actNr) {
            Write-Host "  *** MATCH: $actNr in $($f.Name)"
            $foundCount++
        }
    }
    $reader.Close()
}

Write-Host ""
Write-Host "Total matches found in last 20 (by number) violation chunks: $foundCount"

# Also check ISSUANCE_DATE range in the numerically LAST chunk
Write-Host ""
Write-Host "=== ISSUANCE_DATE YEAR RANGE IN NUMERICALLY LAST VIOLATION CHUNK ==="
$lastChunk = $recentViolChunks[0]
Write-Host "Checking: $($lastChunk.Name)"
$reader = [System.IO.StreamReader]::new($lastChunk.FullName)
$headers = ($reader.ReadLine()) -split ','
$idxDate = [Array]::IndexOf($headers, 'ISSUANCE_DATE')
$dates = @()
$count = 0
while ($null -ne ($line = $reader.ReadLine()) -and $count -lt 2000) {
    $cols = $line -split ','
    $d = $cols[$idxDate].Trim().Trim('"')
    if ($d -match '^\d{4}') { $dates += $d.Substring(0,4) }
    $count++
}
$reader.Close()
$dates | Group-Object | Sort-Object Name | Select-Object Name, Count | Format-Table

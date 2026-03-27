# Check ACTIVITY_NR range across all inspection chunks
# to see if any overlap with violation data (max ~313M)
$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$inspFiles = Get-ChildItem $dir -Filter '*04-17-12*chunk*.csv' |
    Sort-Object { [int]($_.Name -replace '.*chunk_(\d+)\.csv$','$1') }

Write-Host "Checking first 10 and last 5 inspection chunks for ACTIVITY_NR ranges..."
$checkChunks = ($inspFiles | Select-Object -First 10) + ($inspFiles | Select-Object -Last 5)

foreach ($f in $checkChunks) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headers = ($reader.ReadLine()) -split ','
    $idxAct = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxDate = [Array]::IndexOf($headers, 'OPEN_DATE')

    $firstLine = $reader.ReadLine()
    # Read 100 lines to find min/max
    $actNrs = @()
    $line = $firstLine
    $count = 0
    while ($null -ne $line -and $count -lt 100) {
        $cols = $line -split ','
        $a = [long]($cols[$idxAct].Trim().Trim('"') -replace '[^0-9]','0')
        if ($a -gt 0) { $actNrs += $a }
        $count++
        $line = $reader.ReadLine()
    }
    $reader.Close()

    if ($actNrs.Count -gt 0) {
        $min = ($actNrs | Measure-Object -Minimum).Minimum
        $max = ($actNrs | Measure-Object -Maximum).Maximum
        Write-Host "  $($f.Name): ACTIVITY_NR range $min - $max"
    }
}

Write-Host ""
Write-Host "Max ACTIVITY_NR in violation data: ~313,000,000 (2009)"
Write-Host "Inspection ACTIVITY_NRs that overlap: would need to be < 313M"

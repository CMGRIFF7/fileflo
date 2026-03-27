# ============================================================
# FileFlo -- FMCSA Violation Processor
# Input:  rbkj-cgst_version_108.csv (FMCSA roadside inspection data)
# Step 1: Extract DOT numbers with dr_fitness or vh_maint violations in target states (2022+)
# Step 2: Look up carrier names via FMCSA SAFER API
# Output: fmcsa_violation_leads.csv
# ============================================================

$inputFile  = 'C:\Users\ChadGriffith\Downloads\rbkj-cgst_version_108.csv'
$outputFile = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\fmcsa_violation_leads.csv'

$targetStates = @('TX','CA','FL','GA','IL','NY','OH')
$cutoffDate   = [datetime]'2022-01-01'

$fmcsaFeatureMap = @{
    'driver_fitness' = @{
        vt = 'Driver Qualification File Violations'
        ff = 'FileFlo organizes every driver qualification file -- medical certs, MVR reports, employment history, road test certs, annual reviews -- with 30-day expiration alerts so nothing lapses before an auditor asks.'
    }
    'vehicle_maint' = @{
        vt = 'Vehicle Inspection and Maintenance Records'
        ff = 'FileFlo tracks annual inspection certificates, DVIR records, and maintenance logs for every vehicle in your fleet with automatic renewal alerts.'
    }
    'combined' = @{
        vt = 'Driver and Vehicle Compliance Documentation'
        ff = 'FileFlo tracks driver qualification files, medical certificates, vehicle inspection records, and maintenance logs -- everything an FMCSA auditor looks for, organized and current.'
    }
}

function Get-TdValueAfter($html, $marker) {
    # Case-insensitive search for marker, then extract next TD content
    $ic = [System.StringComparison]::OrdinalIgnoreCase
    $mIdx = $html.IndexOf($marker, $ic)
    if ($mIdx -lt 0) { return '' }
    $seg = $html.Substring($mIdx + $marker.Length)
    $tdOpen = $seg.IndexOf('<TD', $ic)
    if ($tdOpen -lt 0) { return '' }
    $tdSeg = $seg.Substring($tdOpen)
    $gtPos = $tdSeg.IndexOf('>')
    if ($gtPos -lt 0) { return '' }
    $inner = $tdSeg.Substring($gtPos + 1)
    $closeAt = $inner.IndexOf('</TD>', $ic)
    if ($closeAt -lt 0) { return '' }
    $raw = $inner.Substring(0, $closeAt)
    # Strip HTML tags
    $raw = [System.Text.RegularExpressions.Regex]::Replace($raw, '<[^>]+>', '')
    # Decode HTML entities
    $raw = $raw.Replace('&nbsp;', ' ').Replace('&amp;', '&').Replace('&lt;', '<').Replace('&gt;', '>').Replace('&#160;', ' ')
    return $raw.Trim()
}

# ============================================================
# PASS 1: Stream CSV -- already have 217,134 DOT numbers in memory if re-running
# Skip if output already exists and we just need to re-do API lookups
# ============================================================
$dotViolations = @{}

if (Test-Path ($outputFile -replace '\.csv$','_dots.json')) {
    Write-Host "Loading cached DOT violations from previous run..."
    # Can't easily load hashtable from JSON in PS, so just re-scan
}

Write-Host "=== PASS 1: Processing FMCSA inspection data ==="
Write-Host "This will take a few minutes -- file is 1GB+"

$rowsScanned = 0
$rowsKept    = 0

$reader     = [System.IO.StreamReader]::new($inputFile)
$headerLine = $reader.ReadLine()
$headers    = $headerLine -split ','

$idxDot     = [Array]::IndexOf($headers, 'dot_number')
$idxState   = [Array]::IndexOf($headers, 'report_state')
$idxDrFit   = [Array]::IndexOf($headers, 'dr_fitness_viol')
$idxVhMaint = [Array]::IndexOf($headers, 'vh_maint_viol')
$idxDate    = [Array]::IndexOf($headers, 'insp_date')

while ($null -ne ($line = $reader.ReadLine())) {
    $rowsScanned++
    if ($rowsScanned % 500000 -eq 0) { Write-Host "  Scanned $rowsScanned rows, kept $rowsKept..." }

    $cols = $line -split ','

    $state = $cols[$idxState].Trim().Trim('"')
    if ($targetStates -notcontains $state) { continue }

    $drViolRaw = $cols[$idxDrFit].Trim().Trim('"')  -replace '[^0-9]',''
    $vmViolRaw = $cols[$idxVhMaint].Trim().Trim('"') -replace '[^0-9]',''
    if ($drViolRaw -eq '') { $drViolRaw = '0' }
    if ($vmViolRaw -eq '') { $vmViolRaw = '0' }
    $drViol = [int]$drViolRaw
    $vmViol = [int]$vmViolRaw
    if ($drViol -eq 0 -and $vmViol -eq 0) { continue }

    $dateRaw  = $cols[$idxDate].Trim().Trim('"')
    $inspDate = $null
    try { $inspDate = [datetime]::ParseExact($dateRaw, 'dd-MMM-yy', $null) } catch {}
    if (-not $inspDate -or $inspDate -lt $cutoffDate) { continue }

    $dot = $cols[$idxDot].Trim().Trim('"')
    if ($dot -eq '' -or $dot -eq '0') { continue }

    $rowsKept++

    if (-not $dotViolations.ContainsKey($dot)) {
        $dotViolations[$dot] = @{ state=$state; drViol=0; vmViol=0; count=0; lastDate=$inspDate }
    }
    $dotViolations[$dot].drViol += $drViol
    $dotViolations[$dot].vmViol += $vmViol
    $dotViolations[$dot].count  += 1
    if ($inspDate -gt $dotViolations[$dot].lastDate) {
        $dotViolations[$dot].lastDate = $inspDate
        $dotViolations[$dot].state    = $state
    }
}
$reader.Close()

Write-Host "Scanned $rowsScanned rows total"
Write-Host "Rows with violations in target states 2022+: $rowsKept"
Write-Host "Unique DOT numbers with violations: $($dotViolations.Count)"

# ============================================================
# PASS 2: FMCSA SAFER API lookup -- top 500 by violation count
# ============================================================
Write-Host ""
Write-Host "=== PASS 2: Looking up carrier names via FMCSA SAFER API ==="

$sortedDots  = $dotViolations.GetEnumerator() |
    Sort-Object { $_.Value.drViol + $_.Value.vmViol } -Descending |
    Select-Object -First 500

$carriers    = @()
$apiErrors   = 0
$apiSuccess  = 0
$lookupCount = 0

foreach ($entry in $sortedDots) {
    $dot   = $entry.Key
    $vdata = $entry.Value
    $lookupCount++

    if ($lookupCount % 50 -eq 0) {
        Write-Host "  API lookups: $lookupCount / $($sortedDots.Count) (success:$apiSuccess errors:$apiErrors)"
    }

    $url = "https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string=$dot"

    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 10 -UseBasicParsing
        $html = $response.Content

        # Extract carrier legal name -- HTML is uppercase tags e.g. <TD>
        $carrierName  = Get-TdValueAfter $html 'Legal Name:'
        $carrierState = $vdata.state

        # Parse state from Physical Address block
        $paIdx = $html.IndexOf('Physical Address', [System.StringComparison]::OrdinalIgnoreCase)
        if ($paIdx -ge 0) {
            $seg   = $html.Substring($paIdx, [Math]::Min(600, $html.Length - $paIdx))
            $stPat = [System.Text.RegularExpressions.Regex]::new('\b([A-Z]{2})\s+\d{5}')
            $stHit = $stPat.Match($seg)
            if ($stHit.Success) { $carrierState = $stHit.Groups[1].Value }
        }

        if ($carrierName -ne '' -and $carrierName -ne '&#160;') {
            $apiSuccess++

            $violCategory = if ($vdata.drViol -gt 0 -and $vdata.vmViol -gt 0) { 'combined' }
                           elseif ($vdata.drViol -gt $vdata.vmViol) { 'driver_fitness' }
                           else { 'vehicle_maint' }

            $feature = $fmcsaFeatureMap[$violCategory]

            $carriers += [PSCustomObject]@{
                dot_number        = $dot
                company_name      = $carrierName
                state             = $carrierState
                citation_year     = $vdata.lastDate.Year.ToString()
                dr_fitness_viols  = $vdata.drViol
                vh_maint_viols    = $vdata.vmViol
                total_inspections = $vdata.count
                violation_type    = $feature.vt
                violation_feature = $feature.ff
            }
        } else {
            $apiErrors++
        }
    } catch {
        $apiErrors++
    }

    Start-Sleep -Milliseconds 200
}

Write-Host "API lookups complete. Success:$apiSuccess Errors:$apiErrors"

$sorted = $carriers | Sort-Object @{Expression={$_.dr_fitness_viols + $_.vh_maint_viols}; Descending=$true}
$sorted | Export-Csv -Path $outputFile -NoTypeInformation

Write-Host "Output written to: $outputFile"
Write-Host ""
Write-Host "TOP 20 CARRIERS:"
$sorted | Select-Object -First 20 | ForEach-Object {
    Write-Host "  DOT:$($_.dot_number) | $($_.company_name) | $($_.state) | DrFit:$($_.dr_fitness_viols) VhMaint:$($_.vh_maint_viols) | $($_.citation_year)"
}

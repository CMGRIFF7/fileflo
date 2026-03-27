# ============================================================
# FileFlo — OSHA Violation Processor (Streaming, 3GB+ safe)
# Joins inspection + violation chunks efficiently
# Only keeps violations FileFlo directly addresses
# Output: osha_violation_leads.csv with {{violationFeature}} pre-populated
# ============================================================

$dir        = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$outputFile = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\osha_violation_leads.csv'

$targetStates   = @('TX','CA','FL','GA','IL','NY','OH')
$targetNaics    = @('238','484')   # Construction + Trucking/Freight
$minPenalty     = 500
$cutoffYear     = 2021             # Citations from 2022 onwards

# ============================================================
# STANDARD CODE → { ViolationType, FileFlo Feature }
# Standard column format: "19101200 A01" = 1910.1200(a)(1)
# Match on first 8 chars (4-digit part + 4-digit section)
# ============================================================
$standardMap = @{
    # Hazard Communication / SDS
    '19101200' = @{ vt = 'Hazard Communication (SDS)';             ff = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable with automatic update alerts.' }
    '19260059' = @{ vt = 'Hazard Communication (SDS)';             ff = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable with automatic update alerts.' }

    # Fall Protection — training records
    '19260503' = @{ vt = 'Fall Protection Training Records';        ff = 'FileFlo tracks every employee fall protection training record and certification expiration with 30-day alerts.' }

    # Respiratory Protection — fit tests + program docs
    '19100134' = @{ vt = 'Respiratory Protection Records';          ff = 'FileFlo tracks respirator fit test records, medical evaluations, and written program documentation.' }

    # Lockout/Tagout — program + training
    '19100147' = @{ vt = 'Lockout/Tagout Program Documentation';   ff = 'FileFlo organizes LOTO program documentation, energy control procedures, and employee training records.' }

    # Scaffolding — inspection certs
    '19260451' = @{ vt = 'Scaffolding Inspection Records';          ff = 'FileFlo manages scaffold inspection certifications and competent person documentation.' }
    '19260454' = @{ vt = 'Scaffolding Training Records';            ff = 'FileFlo tracks scaffold erection/dismantling training records and competent person certifications.' }

    # Ladders — inspection logs
    '19261053' = @{ vt = 'Ladder Inspection Records';               ff = 'FileFlo tracks ladder inspection logs and employee training certifications.' }

    # Powered Industrial Trucks — operator certs
    '19100178' = @{ vt = 'Forklift Operator Certification';         ff = 'FileFlo tracks forklift operator certifications and 3-year recertification schedules with expiration alerts.' }

    # Bloodborne Pathogens — training + exposure control
    '19101030' = @{ vt = 'Bloodborne Pathogen Training Records';    ff = 'FileFlo tracks bloodborne pathogen training records, vaccination documentation, and exposure control plan version history.' }

    # PPE — hazard assessment + training
    '19100132' = @{ vt = 'PPE Training & Hazard Assessment';        ff = 'FileFlo tracks PPE hazard assessments, employee training records, and equipment inspection documentation.' }

    # Cranes — inspection + operator certs
    '19261412' = @{ vt = 'Crane Inspection Records';                ff = 'FileFlo tracks crane inspection records, operator certifications, and annual certification renewals.' }
    '19261427' = @{ vt = 'Crane Operator Certification';            ff = 'FileFlo tracks crane operator certification documents and qualification records.' }

    # OSHA 300 Recordkeeping
    '19040029' = @{ vt = 'OSHA 300 Log Recordkeeping';              ff = 'FileFlo maintains OSHA 300, 300A, and 301 logs with automated annual summary generation and 5-year retention tracking.' }
    '19040032' = @{ vt = 'OSHA 300A Annual Summary';                ff = 'FileFlo generates and stores OSHA 300A annual summaries with posting reminders and electronic submission support.' }
    '19040041' = @{ vt = 'OSHA Recordkeeping (Electronic)';         ff = 'FileFlo maintains OSHA recordkeeping logs and generates electronic submission-ready 300A summaries.' }

    # Safety Training
    '19260021' = @{ vt = 'Safety Training Records';                 ff = 'FileFlo organizes all employee safety training records and certification expirations in one searchable dashboard.' }

    # Emergency Action Plans
    '19100038' = @{ vt = 'Emergency Action Plan Documentation';     ff = 'FileFlo stores and version-controls emergency action plans with employee acknowledgment tracking.' }

    # Process Safety Management
    '19100119' = @{ vt = 'Process Safety Management Records';       ff = 'FileFlo organizes PSM documentation — process hazard analyses, operating procedures, training records, and mechanical integrity logs.' }
}

function Get-StandardMatch($standardRaw) {
    if (-not $standardRaw) { return $null }
    $cleaned = ($standardRaw -replace '\s.*$','').Trim()   # strip paragraph, keep code only
    $key = $cleaned.Substring(0, [Math]::Min(8, $cleaned.Length)).PadRight(8,'0')
    if ($standardMap.ContainsKey($key)) { return $standardMap[$key] }
    return $null
}

# ============================================================
# PASS 1: Build qualifying inspection index
# Stream inspection chunks, filter by state + NAICS + date
# ============================================================
Write-Host "=== PASS 1: Scanning inspection chunks ==="
$inspFiles = Get-ChildItem $dir -Filter '*04-17-12*chunk*.csv' | Sort-Object Name
Write-Host "Inspection chunks to scan: $($inspFiles.Count)"

$qualifyingInsp = @{}  # ACTIVITY_NR -> {name, city, state, naics, year}
$inspScanned = 0
$inspKept = 0

foreach ($f in $inspFiles) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headerLine = $reader.ReadLine()   # skip header
    $headers = $headerLine -split ','

    # Column index lookup
    $idxAct   = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxName  = [Array]::IndexOf($headers, 'ESTAB_NAME')
    $idxCity  = [Array]::IndexOf($headers, 'SITE_CITY')
    $idxState = [Array]::IndexOf($headers, 'SITE_STATE')
    $idxNaics = [Array]::IndexOf($headers, 'NAICS_CODE')
    $idxDate  = [Array]::IndexOf($headers, 'OPEN_DATE')

    while ($null -ne ($line = $reader.ReadLine())) {
        $inspScanned++
        $cols = $line -split ','

        # State filter
        $state = $cols[$idxState].Trim().Trim('"')
        if ($targetStates -notcontains $state) { continue }

        # NAICS filter
        $naics = $cols[$idxNaics].Trim().Trim('"')
        $naicsMatch = $false
        foreach ($prefix in $targetNaics) {
            if ($naics.StartsWith($prefix)) { $naicsMatch = $true; break }
        }
        if (-not $naicsMatch) { continue }

        # Date filter
        $dateStr = $cols[$idxDate].Trim().Trim('"')
        $year = 0
        if ($dateStr -match '^(\d{4})') { $year = [int]$matches[1] }
        if ($year -le $cutoffYear) { continue }

        $actNr = $cols[$idxAct].Trim().Trim('"')
        if ($actNr -eq '') { continue }

        $qualifyingInsp[$actNr] = @{
            name  = $cols[$idxName].Trim().Trim('"')
            city  = $city = $cols[$idxCity].Trim().Trim('"')
            state = $state
            naics = $naics
            year  = $year.ToString()
        }
        $inspKept++
    }
    $reader.Close()
}

Write-Host "Scanned $inspScanned inspection rows"
Write-Host "Qualifying inspections (target state + NAICS + 2022+): $inspKept"

# ============================================================
# PASS 2: Match violations to qualifying inspections
# ============================================================
Write-Host ""
Write-Host "=== PASS 2: Scanning violation chunks ==="
$violFiles = Get-ChildItem $dir -Filter '*04-27-29*chunk*.csv' | Sort-Object Name
Write-Host "Violation chunks to scan: $($violFiles.Count)"

# For each qualifying inspection, track best FileFlo-addressable violation
$violData = @{}   # ACTIVITY_NR -> {violationType, fileFlo, totalPenalty}
$violScanned = 0
$violMatched = 0

foreach ($f in $violFiles) {
    $reader = [System.IO.StreamReader]::new($f.FullName)
    $headerLine = $reader.ReadLine()
    $headers = $headerLine -split ','

    $idxAct      = [Array]::IndexOf($headers, 'ACTIVITY_NR')
    $idxStd      = [Array]::IndexOf($headers, 'STANDARD')
    $idxPenalty  = [Array]::IndexOf($headers, 'CURRENT_PENALTY')
    $idxInit     = [Array]::IndexOf($headers, 'INITIAL_PENALTY')
    $idxDelete   = [Array]::IndexOf($headers, 'DELETE_FLAG')

    while ($null -ne ($line = $reader.ReadLine())) {
        $violScanned++
        $cols = $line -split ','

        $actNr = $cols[$idxAct].Trim().Trim('"')
        if (-not $qualifyingInsp.ContainsKey($actNr)) { continue }

        # Skip deleted/withdrawn violations
        $delFlag = $cols[$idxDelete].Trim().Trim('"')
        if ($delFlag -eq 'X') { continue }

        # Get penalty (use initial if current is empty)
        $penStr = $cols[$idxPenalty].Trim().Trim('"')
        if ($penStr -eq '' -or $penStr -eq 'null') { $penStr = $cols[$idxInit].Trim().Trim('"') }
        $penalty = 0
        if ($penStr -match '[\d.]+') { $penalty = [double]($penStr -replace '[^0-9.]','') }

        $stdRaw = $cols[$idxStd].Trim().Trim('"')
        $match  = Get-StandardMatch $stdRaw

        # Only process violations FileFlo addresses
        if (-not $match) { continue }

        $violMatched++

        if (-not $violData.ContainsKey($actNr)) {
            $violData[$actNr] = @{ penalty = 0; vt = ''; ff = '' }
        }

        $violData[$actNr].penalty += $penalty

        # Keep the violation type/feature for the highest individual penalty
        if ($penalty -ge $violData[$actNr].penalty - $penalty) {
            $violData[$actNr].vt = $match.vt
            $violData[$actNr].ff = $match.ff
        }
    }
    $reader.Close()
}

Write-Host "Scanned $violScanned violation rows"
Write-Host "FileFlo-addressable violation rows matched: $violMatched"

# ============================================================
# COMBINE + OUTPUT
# ============================================================
Write-Host ""
Write-Host "=== BUILDING OUTPUT ==="
$results = @()

foreach ($actNr in $violData.Keys) {
    $vd = $violData[$actNr]
    if ($vd.penalty -lt $minPenalty) { continue }
    if (-not $qualifyingInsp.ContainsKey($actNr)) { continue }

    $insp = $qualifyingInsp[$actNr]
    $results += [PSCustomObject]@{
        company_name      = $insp.name
        city              = $insp.city
        state             = $insp.state
        naics             = $insp.naics
        citation_year     = $insp.year
        violation_type    = $vd.vt
        fine_amount       = '$' + [math]::Round($vd.penalty).ToString('N0')
        total_penalty     = $vd.penalty
        violation_feature = $vd.ff
    }
}

# Deduplicate by company name + state (keep highest penalty)
$deduped = $results |
    Sort-Object company_name, state, @{Expression='total_penalty';Descending=$true} |
    Group-Object company_name, state |
    ForEach-Object { $_.Group[0] }

$sorted = $deduped | Sort-Object total_penalty -Descending

Write-Host "Unique companies with FileFlo-addressable violations: $($sorted.Count)"

$sorted | Select-Object company_name, city, state, naics, citation_year, violation_type, fine_amount, violation_feature |
    Export-Csv -Path $outputFile -NoTypeInformation

Write-Host "Output written to: $outputFile"
Write-Host ""
Write-Host "=== TOP 30 HIGHEST-PENALTY COMPANIES ==="
$sorted | Select-Object -First 30 | ForEach-Object {
    Write-Host "  [$($_.fine_amount)] $($_.company_name) | $($_.city), $($_.state) | $($_.violation_type) | $($_.citation_year)"
}

Write-Host ""
Write-Host "=== BREAKDOWN BY STATE ==="
$sorted | Group-Object state | Sort-Object Count -Descending | ForEach-Object {
    Write-Host "  $($_.Name): $($_.Count) companies"
}

Write-Host ""
Write-Host "=== BREAKDOWN BY VIOLATION TYPE ==="
$sorted | Group-Object violation_type | Sort-Object Count -Descending | ForEach-Object {
    Write-Host "  $($_.Name): $($_.Count) companies"
}

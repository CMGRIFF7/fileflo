# ============================================================
# FileFlo — Violation Lead Processor
# Filters OSHA/FMCSA violations to ONLY those FileFlo directly addresses
# (documentation failures — not equipment or actual safety failures)
# Adds {{violationFeature}} mapping for personalized Instantly sequences
#
# Input:  osha_inspection.csv + osha_violation.csv (from enforcedata.dol.gov)
# Output: osha_violation_leads.csv
# ============================================================

$scriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$inspectionFile = Join-Path $scriptDir "osha_inspection.csv"
$violationFile  = Join-Path $scriptDir "osha_violation.csv"
$outputFile     = Join-Path $scriptDir "osha_violation_leads.csv"

$targetStates = @('TX','CA','FL','GA','IL','NY','OH')
$targetNaics  = @('238','484','4841','4842','2381','2382','2383','2389')
$minPenalty   = 1000

# ============================================================
# FILEFLO CAPABILITY MAP
# Maps OSHA standard codes to the specific FileFlo feature that fixes it.
# ONLY include standards that are documentation violations FileFlo addresses.
# Exclude actual equipment/safety failures FileFlo cannot fix.
# ============================================================
$fileFloMap = @{
    # Hazard Communication — FileFlo maintains SDS library
    '1910.1200' = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable with automatic update alerts.'
    '1926.59'   = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable with automatic update alerts.'

    # Fall protection — training records only
    '1926.503'  = 'FileFlo tracks every employee fall protection training record and certification expiration with 30-day alerts.'

    # Respiratory protection — fit tests and program docs
    '1910.134'  = 'FileFlo tracks respirator fit test records, medical evaluations, and written program documentation with expiration alerts.'

    # Lockout/tagout — program and training records
    '1910.147'  = 'FileFlo organizes LOTO program documentation, energy control procedures, and employee training records.'

    # Scaffolding — inspection and competent person certs
    '1926.451'  = 'FileFlo manages scaffold inspection certifications and competent person documentation.'
    '1926.454'  = 'FileFlo tracks scaffold erection/dismantling training records and competent person certs.'

    # Ladders — inspection logs and training
    '1926.1053' = 'FileFlo tracks ladder inspection logs and employee training certifications.'

    # Powered industrial trucks — operator certs
    '1910.178'  = 'FileFlo tracks forklift operator certifications and 3-year recertification schedules with expiration alerts.'

    # Bloodborne pathogens — training and exposure control plan
    '1910.1030' = 'FileFlo tracks bloodborne pathogen training records, vaccination documentation, and exposure control plan version history.'

    # General safety training records
    '1926.21'   = 'FileFlo organizes all employee safety training records and certification expirations in one searchable dashboard.'

    # PPE — hazard assessment and training
    '1910.132'  = 'FileFlo tracks PPE hazard assessments, training records, and equipment inspection logs.'

    # Crane/rigging certifications
    '1926.1412' = 'FileFlo tracks crane inspection records, operator certifications, and annual certification renewals.'
    '1926.1427' = 'FileFlo tracks crane operator certification documents and qualification records.'

    # Process safety management
    '1910.119'  = 'FileFlo organizes PSM documentation — process hazard analyses, operating procedures, training records, and mechanical integrity logs.'

    # Emergency action plans
    '1910.38'   = 'FileFlo stores and version-controls emergency action plans with employee acknowledgment records.'

    # Fire prevention plans
    '1910.39'   = 'FileFlo maintains fire prevention plan documentation and inspection records.'

    # OSHA 300 logs (recordkeeping)
    '1904.29'   = 'FileFlo maintains OSHA 300, 300A, and 301 logs with automated annual summary generation and 5-year retention tracking.'
    '1904.32'   = 'FileFlo maintains OSHA 300, 300A, and 301 logs with automated annual summary generation.'
    '1904.41'   = 'FileFlo maintains OSHA recordkeeping logs and generates electronic submission-ready 300A summaries.'
}

# Generic fallback by keyword
$keywordMap = @{
    'hazard communication'   = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable.'
    'sds'                    = 'FileFlo maintains your SDS library — every chemical, every location, organized and searchable.'
    'training'               = 'FileFlo tracks all employee training records and certification expirations with 30-day alerts.'
    'recordkeeping'          = 'FileFlo maintains OSHA 300/300A/301 logs with automated summaries and 5-year retention tracking.'
    'fall protection'        = 'FileFlo tracks fall protection training records and equipment inspection logs.'
    'respiratory'            = 'FileFlo tracks respirator fit test records and written program documentation.'
    'lockout'                = 'FileFlo organizes LOTO program documentation and employee training records.'
    'forklift'               = 'FileFlo tracks forklift operator certifications and 3-year recertification schedules.'
    'certification'          = 'FileFlo tracks all certifications and licenses with automatic expiration alerts.'
    'inspection'             = 'FileFlo organizes equipment inspection records and maintenance logs.'
    'scaffold'               = 'FileFlo manages scaffold inspection certs and competent person documentation.'
    'crane'                  = 'FileFlo tracks crane inspection records and operator certifications.'
}

# Standards to EXCLUDE — actual equipment/safety failures FileFlo cannot fix
$excludedStandards = @(
    '1926.502',  # Fall protection systems (actual guardrails/equipment)
    '1910.212',  # Machine guarding (physical equipment)
    '1926.100',  # Hard hats (physical equipment)
    '1926.102',  # Eye protection (physical equipment)
    '1910.303',  # Electrical wiring (physical)
    '1926.404',  # Electrical installations (physical)
    '1910.215',  # Abrasive wheel machinery (physical)
    '1910.217',  # Mechanical power presses (physical)
    '1910.219'   # Mechanical power transmission (physical)
)

function Get-FileFloFeature($standardCited, $description) {
    # Check excluded standards first
    foreach ($excl in $excludedStandards) {
        if ($standardCited -like "$excl*") { return $null }
    }

    # Check exact/prefix match in capability map
    foreach ($key in $fileFloMap.Keys) {
        if ($standardCited -like "$key*") {
            return $fileFloMap[$key]
        }
    }

    # Fall back to keyword matching on description
    $descLower = $description.ToLower()
    foreach ($kw in $keywordMap.Keys) {
        if ($descLower -match $kw) {
            return $keywordMap[$kw]
        }
    }

    # If we can't map it, it might not be something FileFlo addresses — skip
    return $null
}

# ============================================================
# MAIN PROCESSING
# ============================================================
Write-Host "Loading data..."
$inspections = Import-Csv $inspectionFile
$violations  = Import-Csv $violationFile

Write-Host "Indexing $($violations.Count) violations..."
$violationIndex = @{}
foreach ($v in $violations) {
    $id = $v.activity_nr
    if (-not $violationIndex.ContainsKey($id)) { $violationIndex[$id] = @() }
    $violationIndex[$id] += $v
}

Write-Host "Processing $($inspections.Count) inspections..."
$results = @()

foreach ($insp in $inspections) {
    if ($targetStates -notcontains $insp.site_state) { continue }

    $naicsMatch = $false
    foreach ($prefix in $targetNaics) {
        if ($insp.naics_code -like "$prefix*") { $naicsMatch = $true; break }
    }
    if (-not $naicsMatch) { continue }

    $actId = $insp.activity_nr
    if (-not $violationIndex.ContainsKey($actId)) { continue }

    $totalPenalty   = 0
    $bestFeature    = $null
    $bestViolType   = ''
    $bestPenalty    = 0

    foreach ($v in $violationIndex[$actId]) {
        $p = [double]($v.penalty_issued -replace '[^0-9.]','')
        $totalPenalty += $p

        # Map this specific violation to a FileFlo feature
        $std     = if ($v.standard_cited) { $v.standard_cited.Trim() } else { '' }
        $desc    = if ($v.issuedescription) { $v.issuedescription.Trim() } else { '' }
        $feature = Get-FileFloFeature $std $desc

        # Keep the highest-penalty violation that FileFlo can address
        if ($feature -and $p -ge $bestPenalty) {
            $bestPenalty  = $p
            $bestFeature  = $feature
            $bestViolType = if ($desc -ne '') { $desc } else { $std }
        }
    }

    # Only include if FileFlo can actually address at least one violation
    if (-not $bestFeature) { continue }
    if ($totalPenalty -lt $minPenalty) { continue }

    $citationYear = ''
    if ($insp.open_date -match '(\d{4})') { $citationYear = $matches[1] }

    $results += [PSCustomObject]@{
        company_name      = $insp.estab_name.Trim()
        city              = $insp.site_city.Trim()
        state             = $insp.site_state.Trim()
        naics             = $insp.naics_code
        activity_nr       = $actId
        citation_year     = $citationYear
        violation_type    = $bestViolType
        fine_amount       = '$' + [math]::Round($totalPenalty).ToString('N0')
        total_penalty     = $totalPenalty
        violation_feature = $bestFeature
    }
}

Write-Host "Found $($results.Count) matching records. Deduplicating..."

$deduped = $results |
    Sort-Object company_name, state, @{Expression='total_penalty';Descending=$true} |
    Group-Object company_name, state |
    ForEach-Object { $_.Group[0] }

$sorted = $deduped | Sort-Object total_penalty -Descending

Write-Host "Writing $($sorted.Count) companies to $outputFile"
$sorted | Select-Object company_name, city, state, naics, citation_year, violation_type, fine_amount, violation_feature |
    Export-Csv -Path $outputFile -NoTypeInformation

Write-Host ""
Write-Host "TOP 20 FINED COMPANIES (FileFlo-addressable violations only):"
$sorted | Select-Object -First 20 | ForEach-Object {
    Write-Host "  $($_.company_name) | $($_.city), $($_.state) | $($_.violation_type) | $($_.fine_amount) | $($_.citation_year)"
}
Write-Host ""
Write-Host "Output: $outputFile"
Write-Host "Next: search company names in Apollo, add contact info, run format_for_instantly.ps1"

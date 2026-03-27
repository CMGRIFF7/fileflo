# ============================================================
# FileFlo — Format Enriched Violation Leads for Instantly Import
#
# Input:  enriched_violation_leads.csv
#   Required columns: first_name, last_name, email, company_name, website,
#                     citation_year, violation_type, fine_amount, violation_feature
#
# Output: instantly_import_violation_leads.csv  (ready for bulk import)
#         Custom variables available in sequences:
#           {{violationType}}     — what they were cited for
#           {{fineAmount}}        — e.g. $24,500
#           {{citationYear}}      — e.g. 2023
#           {{violationFeature}}  — specific FileFlo capability that addresses it
# ============================================================

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputFile  = Join-Path $scriptDir "enriched_violation_leads.csv"
$outputFile = Join-Path $scriptDir "instantly_import_violation_leads.csv"

if (-not (Test-Path $inputFile)) {
    Write-Error "File not found: $inputFile"
    Write-Host "Required columns: first_name, last_name, email, company_name, website,"
    Write-Host "                  citation_year, violation_type, fine_amount, violation_feature"
    exit 1
}

$leads = Import-Csv $inputFile
Write-Host "Processing $($leads.Count) leads..."

$output  = @()
$skipped = 0

foreach ($lead in $leads) {
    if (-not $lead.email -or $lead.email.Trim() -eq '') { $skipped++; continue }

    # Truncate violation type if very long
    $violType = $lead.violation_type.Trim()
    if ($violType.Length -gt 60) { $violType = $violType.Substring(0, 57) + '...' }

    $output += [PSCustomObject]@{
        email            = $lead.email.Trim().ToLower()
        first_name       = $lead.first_name.Trim()
        last_name        = $lead.last_name.Trim()
        company_name     = $lead.company_name.Trim()
        website          = $lead.website.Trim()
        # Instantly custom variables — must match {{variable}} exactly in sequences
        violationType    = $violType
        fineAmount       = $lead.fine_amount.Trim()
        citationYear     = $lead.citation_year.Trim()
        violationFeature = $lead.violation_feature.Trim()
    }
}

$output | Export-Csv -Path $outputFile -NoTypeInformation
Write-Host "Wrote $($output.Count) leads ($skipped skipped - no email)"
Write-Host ""
Write-Host "Custom variables available in Instantly sequences:"
Write-Host "  {{violationType}}     — e.g. 'Hazard Communication / SDS not updated'"
Write-Host "  {{fineAmount}}        — e.g. '`$24,500'"
Write-Host "  {{citationYear}}      — e.g. '2023'"
Write-Host "  {{violationFeature}}  — e.g. 'FileFlo maintains your SDS library...'"
Write-Host ""
Write-Host "Output: $outputFile"

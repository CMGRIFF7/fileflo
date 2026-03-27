# Filter FMCSA leads to US mid-size carriers only
# Exclude: Mexican carriers, mega-carriers, very small operators
$inputFile  = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\fmcsa_violation_leads.csv'
$outputFile = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\fmcsa_leads_filtered.csv'

# Known mega-carriers to exclude (they have full compliance depts)
$megaCarriers = @(
    'FEDERAL EXPRESS','FEDEX','UNITED PARCEL SERVICE','UPS','SWIFT TRANSPORTATION',
    'J B HUNT','WERNER','SCHNEIDER','KNIGHT','LANDSTAR','RYDER','PENSKE',
    'OLD DOMINION','XPO','ESTES','ABF','SAIA','R+L','YRC','AVERITT',
    'AMAZON','WALMART','DOLLAR GENERAL','DOLLAR TREE','SYSCO','US FOODS'
)

# Mexican carrier indicators (cross-border, different compliance needs)
$mexicanIndicators = @('SA DE CV','S DE RL','DE CV','TRANSPORTES ','TRANSPORTE ',
    'AUTOTRANSPORTES','OPERADORA','SERVICIO INTERNACIONAL')

$leads = Import-Csv $inputFile

$filtered = @()
foreach ($lead in $leads) {
    $name = $lead.company_name.ToUpper()

    # Skip Mexican carriers
    $isMexican = $false
    foreach ($ind in $mexicanIndicators) {
        if ($name.Contains($ind.ToUpper())) { $isMexican = $true; break }
    }
    if ($isMexican) { continue }

    # Skip mega-carriers
    $isMega = $false
    foreach ($mega in $megaCarriers) {
        if ($name.Contains($mega.ToUpper())) { $isMega = $true; break }
    }
    if ($isMega) { continue }

    # Skip individual sole proprietors (single person names are too small)
    # Keep if name has LLC, INC, CORP, CO, TRANSPORT, TRUCKING, FREIGHT, LOGISTICS
    $hasBusinessIndicator = ($name -match 'LLC|INC|CORP|\bCO\b|TRANSPORT|TRUCKING|FREIGHT|LOGISTICS|CARRIER|HAULING|EXPRESS|DELIVERY')
    if (-not $hasBusinessIndicator) { continue }

    # Skip if state is not US target states (catches Mexican companies with US addresses)
    $usStates = @('TX','CA','FL','GA','IL','NY','OH','CO','AZ','WA','OR','NV','UT','NM','MO','IN','MI','MN','WI','KY','TN','NC','SC','VA','PA','NJ','MD')
    if ($usStates -notcontains $lead.state) { continue }

    $filtered += $lead
}

Write-Host "Original leads: $($leads.Count)"
Write-Host "After filtering: $($filtered.Count)"
Write-Host ""
Write-Host "TOP 40 FILTERED CARRIERS:"
$filtered | Select-Object -First 40 | ForEach-Object {
    $total = [int]$_.dr_fitness_viols + [int]$_.vh_maint_viols
    Write-Host "  $($_.company_name) | $($_.state) | Total viols: $total | $($_.violation_type)"
}

$filtered | Export-Csv $outputFile -NoTypeInformation
Write-Host ""
Write-Host "Saved to: $outputFile"

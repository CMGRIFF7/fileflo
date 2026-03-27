# Extract top 20 people with first_name + org name for bulk_match enrichment
$truckingFile  = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json'
$constructFile = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01NpsDW3BpdmBZQL68WFijsf.json'
$topTruckIds   = Get-Content 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\top_trucking_ids.txt'
$topConstIds   = Get-Content 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\top_construction_ids.txt'

function Load-People($file) {
    $outer = Get-Content $file -Raw | ConvertFrom-Json
    $inner = ($outer[0].text | ConvertFrom-Json)
    return $inner.people
}

function Get-EnrichPayload($people, $topIds) {
    $result = @()
    foreach ($id in $topIds) {
        $p = $people | Where-Object { $_.id -eq $id } | Select-Object -First 1
        if ($p) {
            $result += [PSCustomObject]@{
                apollo_id  = $id
                first_name = $p.first_name
                org_name   = if ($p.organization) { $p.organization.name } else { '' }
                title      = $p.title
            }
        }
    }
    return $result
}

$truckPeople = Load-People $truckingFile
$constPeople = Load-People $constructFile

$truckPayload = Get-EnrichPayload $truckPeople $topTruckIds
$constPayload = Get-EnrichPayload $constPeople $topConstIds

Write-Host "=== TRUCKING ENRICH PAYLOAD (top 20) ==="
$truckPayload | ForEach-Object { Write-Host "  $($_.first_name) | $($_.org_name) | $($_.title)" }

Write-Host ""
Write-Host "=== CONSTRUCTION ENRICH PAYLOAD (top 20) ==="
$constPayload | ForEach-Object { Write-Host "  $($_.first_name) | $($_.org_name) | $($_.title)" }

# Save as JSON for reference
$truckPayload | ConvertTo-Json | Set-Content 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\truck_enrich_list.json'
$constPayload | ConvertTo-Json | Set-Content 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\const_enrich_list.json'
Write-Host ""
Write-Host "Saved enrich lists to truck_enrich_list.json and const_enrich_list.json"

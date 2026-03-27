$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773838421863.txt'
$f2  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773838429058.txt'
$f3  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773838433504.txt'
$files = $f1,$f2,$f3

$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'
$count = 0

foreach ($f in $files) {
    if (-not [System.IO.File]::Exists($f)) { Write-Host ('MISSING: ' + $f); continue }
    $raw = [System.IO.File]::ReadAllText($f)
    $arr = $raw | ConvertFrom-Json
    $inner = $arr[0].text | ConvertFrom-Json
    for ($i = 0; $i -lt $inner.matches.Count; $i++) {
        $m = $inner.matches[$i]
        $em = $m.email; $es = $m.email_status
        if ($em -and ($es -eq 'verified' -or $es -eq 'likely to engage')) {
            $rows += $nl + $m.first_name + ',' + $m.last_name + ',' + $em + ',' + $m.organization.name + ',' + $m.title
            $count++
        }
    }
}

# Inline results (p43b - returned directly)
$rows += $nl + 'Janeanne,Bischke,jbischke@ccfs.com,CrossCountry Freight Solutions,Owner'
$rows += $nl + 'Marc,Davis,marc.davis@blueeaglelogistics.com,Blue Eagle Logistics,Chief Executive Officer'
$rows += $nl + 'Brenda,Kraft,brenda@kottke-trucking.com,Kottke Trucking Inc.,VP of Safety and HR'
$rows += $nl + 'Joseph,Maguire,jmaguire@mawsonandmawson.com,Mawson & Mawson Inc,Director of Safety'
$count += 4

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch18.csv', $rows)
Write-Host ('Done. Leads: ' + $count)

$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'toulu_01ShNTufCsSjJrda4tFKGhJ2.json'
$f2  = $b + 'toulu_017x2DPu5yUscnyBUrzUAYZR.json'
$f3  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836311799.txt'
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

# Inline results (p17-batch2 and p19-batch3 - returned directly)
$rows += $nl + 'Charlene,Dufresne-Achatz,cdufresne@mysticlogistics.com,Mystic Logistics,CEO'
$rows += $nl + 'Jeff,Foster,jeff@jefffostertrucking.com,Jeff Foster Trucking Inc,CEO'
$rows += $nl + 'Jeff,Dickinson,jeffd@rgtxlogistics.com,RGTX Logistics Solutions,President & CEO'
$rows += $nl + 'Donny,Strother,donnys@valuedfreight.com,Valued Freight Services,CEO'
$count += 4

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch7.csv', $rows)
Write-Host ('Done. Leads: ' + $count)

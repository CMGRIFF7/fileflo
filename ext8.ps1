$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'toulu_01Q4HT1Cgc6dhvEMQ8vfzSSD.json'
$f2  = $b + 'toulu_015kGMxXYMobZfhwv6wdFT7D.json'
$f3  = $b + 'toulu_013361qqovDyq8GEdDHakTRu.json'
$f4  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836440413.txt'
$files = $f1,$f2,$f3,$f4

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

# Inline results (p20-batch3 - returned directly)
$rows += $nl + 'Paul,Klimovich,paul@uscommercialfreight.com,US Commercial Freight,Owner & CEO'
$count += 1

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch8.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
